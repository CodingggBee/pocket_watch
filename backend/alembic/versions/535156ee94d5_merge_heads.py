"""Merge heads

Revision ID: 535156ee94d5
Revises: add_payment_tables, d1e2f3g4h5i6
Create Date: 2026-03-03 00:28:35.029710

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '535156ee94d5'
down_revision: Union[str, Sequence[str], None] = ('add_payment_tables', 'd1e2f3g4h5i6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
