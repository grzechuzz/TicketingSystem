"""add invoice_number generator table"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "44fac9664860"
down_revision: Union[str, Sequence[str], None] = "026bcefdfce4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoice_counters",
        sa.Column("fiscal_year", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("counter", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("invoice_counters")
