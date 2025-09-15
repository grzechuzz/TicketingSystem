import os
import json
import asyncio
import signal
import socket
import logging
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text, bindparam, Text
from sqlalchemy.dialects.postgresql import JSONB, INET, ARRAY
from sqlalchemy.exc import SQLAlchemyError, DBAPIError
from app.core.config import DATABASE_URL, AUDIT_STREAM, AUDIT_GROUP, AUDIT_BATCH, AUDIT_BLOCK_MS
from app.core.redis import create_redis


logger = logging.getLogger("audit.worker")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

INSERT_AUDIT = text("""
    INSERT INTO audit.audit_logs
    (request_id, scope, action, actor_user_id, actor_roles, actor_ip, route,
     object_type, object_id, organizer_id, event_id, order_id, payment_id,
     invoice_id, status, reason, meta)
    VALUES
    (:request_id, :scope, :action, :actor_user_id, :actor_roles, :actor_ip, :route,
     :object_type, :object_id, :organizer_id, :event_id, :order_id, :payment_id,
     :invoice_id, :status, :reason, :meta)
""").bindparams(
    bindparam("actor_roles", type_=ARRAY(Text())),
    bindparam("actor_ip", type_=INET),
    bindparam("meta", type_=JSONB),
)


def _params_from_payload(payload: dict) -> dict:
    status = (payload.get("status") or "SUCCESS").upper()
    return {
        "request_id": payload.get("request_id"),
        "scope": payload["scope"],
        "action": payload["action"],
        "actor_user_id": payload.get("actor_user_id"),
        "actor_roles": list(payload.get("actor_roles") or []),
        "actor_ip": payload.get("actor_ip"),
        "route": payload.get("route"),
        "object_type": payload.get("object_type"),
        "object_id": payload.get("object_id"),
        "organizer_id": payload.get("organizer_id"),
        "event_id": payload.get("event_id"),
        "order_id": payload.get("order_id"),
        "payment_id": payload.get("payment_id"),
        "invoice_id": payload.get("invoice_id"),
        "status": "SUCCESS" if status == "SUCCESS" else "FAIL",
        "reason": payload.get("reason"),
        "meta": dict(payload.get("meta") or {}),
    }


async def _ensure_group(r: redis.Redis) -> None:
    try:
        await r.xgroup_create(
            name=AUDIT_STREAM,
            groupname=AUDIT_GROUP,
            id="$",
            mkstream=True,
        )
        logger.info("XGROUP created stream=%s group=%s", AUDIT_STREAM, AUDIT_GROUP)
    except redis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.info("XGROUP already exists stream=%s group=%s", AUDIT_STREAM, AUDIT_GROUP)
        else:
            raise


async def run() -> None:
    r = await create_redis()
    await _ensure_group(r)

    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session = async_sessionmaker(bind=engine, expire_on_commit=False)

    stop = asyncio.Event()

    def _graceful(*_):
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _graceful)
        except NotImplementedError:
            pass

    consumer = f"{socket.gethostname()}-{os.getpid()}"
    logger.info(
        "Audit worker started | stream=%s group=%s consumer=%s batch=%d block_ms=%d",
        AUDIT_STREAM, AUDIT_GROUP, consumer, AUDIT_BATCH, AUDIT_BLOCK_MS,
    )

    last_retry = loop.time()

    try:
        while not stop.is_set():
            resp = await r.xreadgroup(
                groupname=AUDIT_GROUP,
                consumername=consumer,
                streams={AUDIT_STREAM: ">"},
                count=AUDIT_BATCH,
                block=AUDIT_BLOCK_MS,
            )
            if resp:
                entries = resp[0][1]
                async with session() as db:
                    async with db.begin():
                        for msg_id, fields in entries:
                            raw_json = fields.get("json")
                            try:
                                payload = json.loads(raw_json) if raw_json else {}
                                if not isinstance(payload, dict):
                                    raise ValueError("payload is not a JSON object")
                                if not payload.get("scope") or not payload.get("action"):
                                    raise ValueError("missing required fields: scope/action")

                                params = _params_from_payload(payload)
                                await db.execute(INSERT_AUDIT, params)

                                await r.xack(AUDIT_STREAM, AUDIT_GROUP, msg_id)
                            except (DBAPIError, SQLAlchemyError):
                                logger.exception("DB insert failed; keeping id=%s in PEL", msg_id)
                            except Exception as e:
                                logger.warning("Invalid payload; dropping id=%s err=%s", msg_id, e)
                                try:
                                    await r.xack(AUDIT_STREAM, AUDIT_GROUP, msg_id)
                                except Exception:
                                    logger.exception("XACK failed id=%s", msg_id)
            now = loop.time()
            if now - last_retry > 30:
                last_retry = now
                try:
                    next_cursor, msgs, _ = await r.xautoclaim(
                        name=AUDIT_STREAM,
                        groupname=AUDIT_GROUP,
                        consumername=consumer,
                        min_idle_time=60000,
                        start_id="0",
                        count=100,
                    )
                    if msgs:
                        logger.info("XAUTOCLAIM: retrying %d pending messages", len(msgs))
                        async with session() as db:
                            async with db.begin():
                                for msg_id, fields in msgs:
                                    raw_json = fields.get("json")
                                    try:
                                        payload = json.loads(raw_json) if raw_json else {}
                                        if not isinstance(payload, dict):
                                            raise ValueError("payload is not a JSON object")
                                        if not payload.get("scope") or not payload.get("action"):
                                            raise ValueError("missing required fields: scope/action")

                                        params = _params_from_payload(payload)
                                        await db.execute(INSERT_AUDIT, params)
                                        await r.xack(AUDIT_STREAM, AUDIT_GROUP, msg_id)

                                    except (DBAPIError, SQLAlchemyError):
                                        logger.exception("DB insert failed (XAUTOCLAIM); keeping id=%s", msg_id)
                                    except Exception as e:
                                        logger.warning("Invalid payload (XAUTOCLAIM); dropping id=%s err=%s", msg_id, e)
                                        try:
                                            await r.xack(AUDIT_STREAM, AUDIT_GROUP, msg_id)
                                        except Exception:
                                            logger.exception("XACK failed id=%s", msg_id)

                except Exception:
                    logger.exception("XAUTOCLAIM failed")
    finally:
        logger.info("Shutting down audit worker...")
        try:
            await r.aclose()
        except Exception:
            logger.exception("Redis close failed")
        try:
            await engine.dispose()
        except Exception:
            logger.exception("Engine dispose failed")
        logger.info("Audit worker stopped.")


if __name__ == "__main__":
    asyncio.run(run())
