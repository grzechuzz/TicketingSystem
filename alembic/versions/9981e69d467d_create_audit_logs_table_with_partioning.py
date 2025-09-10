"""create audit_logs table with partitioning

Revision ID: 9981e69d467d
Revises: 35e8bd92c3a0
Create Date: 2025-09-10 14:05:57.434944
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa  # noqa


# revision identifiers, used by Alembic.
revision: str = "9981e69d467d"
down_revision: Union[str, Sequence[str], None] = "35e8bd92c3a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit.audit_logs(
            id BIGINT GENERATED ALWAYS AS IDENTITY,
            ts_utc timestamptz NOT NULL DEFAULT now(),
            request_id text,
            scope text NOT NULL,
            action text NOT NULL,
            actor_user_id bigint,
            actor_roles text[] NOT NULL DEFAULT '{}',
            actor_ip inet,
            route text,
            object_type text,
            object_id bigint,
            organizer_id bigint,
            event_id bigint,
            order_id bigint,
            payment_id bigint,
            invoice_id bigint,
            status text NOT NULL,
            reason text,
            meta jsonb NOT NULL DEFAULT '{}'::jsonb,
            CONSTRAINT chk_audit_status CHECK (status IN ('SUCCESS','FAIL')),
            PRIMARY KEY (ts_utc, id)
        ) PARTITION BY RANGE (ts_utc)
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_ts ON audit.audit_logs (ts_utc DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_ts  ON audit.audit_logs (actor_user_id, ts_utc DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_action_ts ON audit.audit_logs (action, ts_utc DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_obj ON audit.audit_logs (object_type, object_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_order ON audit.audit_logs (order_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_payment ON audit.audit_logs (payment_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_event ON audit.audit_logs (event_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_invoice ON audit.audit_logs (invoice_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_organizer ON audit.audit_logs (organizer_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_meta_gin ON audit.audit_logs USING gin (meta jsonb_path_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_id  ON audit.audit_logs (id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit.audit_logs_2025_09
          PARTITION OF audit.audit_logs
          FOR VALUES FROM (TIMESTAMPTZ '2025-09-01 00:00:00+00') TO (TIMESTAMPTZ '2025-10-01 00:00:00+00')
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit.audit_logs_2025_10
          PARTITION OF audit.audit_logs
          FOR VALUES FROM (TIMESTAMPTZ '2025-10-01 00:00:00+00') TO (TIMESTAMPTZ '2025-11-01 00:00:00+00')
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit.audit_logs_2025_11
          PARTITION OF audit.audit_logs
          FOR VALUES FROM (TIMESTAMPTZ '2025-11-01 00:00:00+00') TO (TIMESTAMPTZ '2025-12-01 00:00:00+00')
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit.audit_logs_2025_12
          PARTITION OF audit.audit_logs
          FOR VALUES FROM (TIMESTAMPTZ '2025-12-01 00:00:00+00') TO (TIMESTAMPTZ '2026-01-01 00:00:00+00')
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit.audit_logs_default
          PARTITION OF audit.audit_logs DEFAULT
        """
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS audit CASCADE")
