"""Merge plans and payment heads

Revision ID: 3bc3800a9168
Revises: 535156ee94d5, add_company_subscriptions
Create Date: 2026-03-04 00:55:30.444181

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3bc3800a9168'
down_revision: Union[str, Sequence[str], None] = ('535156ee94d5', 'add_company_subscriptions')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
