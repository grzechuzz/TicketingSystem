"""add REQUIRES_ACTION to payment_status

Revision ID: 1f90a27c7d5a
Revises: 1860ae7b1c7d
Create Date: 2025-08-21 13:11:53.007396

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f90a27c7d5a'
down_revision: Union[str, Sequence[str], None] = '1860ae7b1c7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(f"ALTER TYPE payment_status ADD VALUE IF NOT EXISTS 'REQUIRES_ACTION'")
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
