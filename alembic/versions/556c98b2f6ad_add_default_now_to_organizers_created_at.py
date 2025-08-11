"""add default now to organizers.created_at

Revision ID: 556c98b2f6ad
Revises: fc9c45003118
Create Date: 2025-08-11 17:18:42.994434

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '556c98b2f6ad'
down_revision: Union[str, Sequence[str], None] = 'fc9c45003118'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "organizers",
        "created_at",
        server_default=sa.text("now()"),
        existing_type=sa.TIMESTAMP(timezone=True),
        existing_nullable=False
    )


def downgrade() -> None:
    op.alter_column(
        "organizers",
        "created_at",
        server_default=None,
        existing_type=sa.TIMESTAMP(timezone=True),
        existing_nullable=False
    )