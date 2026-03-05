"""Add billing details to payment_methods

Revision ID: add_billing_details
Revises: add_payment_tables
Create Date: 2026-03-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_billing_details'
down_revision = 'add_payment_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Add billing details columns to payment_methods table"""
    op.add_column('payment_methods', sa.Column('cardholder_name', sa.String(255), nullable=True))
    op.add_column('payment_methods', sa.Column('billing_postal_code', sa.String(20), nullable=True))
    op.add_column('payment_methods', sa.Column('billing_country', sa.String(2), nullable=True))


def downgrade():
    """Remove billing details columns from payment_methods table"""
    op.drop_column('payment_methods', 'billing_country')
    op.drop_column('payment_methods', 'billing_postal_code')
    op.drop_column('payment_methods', 'cardholder_name')
