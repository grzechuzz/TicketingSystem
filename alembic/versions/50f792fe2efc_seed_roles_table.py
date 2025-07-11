"""seed roles table

Revision ID: 50f792fe2efc
Revises: 5d55a7bc9497
Create Date: 2025-07-11 02:22:36.632929

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50f792fe2efc'
down_revision: Union[str, Sequence[str], None] = '5d55a7bc9497'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        INSERT INTO roles (name) 
        VALUES ('CUSTOMER'), ('ORGANIZER'), ('ADMIN') 
        ON CONFLICT (name) DO NOTHING     
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
