import redis.asyncio as redis
from app.core.config import REDIS_URL


async def create_redis() -> redis.Redis:
    return redis.from_url(
        REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        health_check_interval=30,
        retry_on_timeout=True,
        socket_connect_timeout=10,
        socket_timeout=None,
        socket_keepalive=True
    )
