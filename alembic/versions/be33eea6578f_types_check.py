"""types check

Revision ID: be33eea6578f
Revises: 0277bd44aa62
Create Date: 2025-07-31 14:36:01.063157

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be33eea6578f'
down_revision: Union[str, Sequence[str], None] = '0277bd44aa62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE t.typname = 'event_status' AND e.enumlabel = 'REJECTED'
      ) THEN
        ALTER TYPE event_status ADD VALUE 'REJECTED' BEFORE 'PLANNED';
      END IF;

      IF NOT EXISTS (
        SELECT 1 FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE t.typname = 'event_status' AND e.enumlabel = 'AWAITING_APPROVAL'
      ) THEN
        ALTER TYPE event_status ADD VALUE 'AWAITING_APPROVAL' BEFORE 'REJECTED';
      END IF;
    END$$;
    """)

def downgrade():
    pass
