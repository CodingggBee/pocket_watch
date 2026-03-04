"""Add payment tables

Revision ID: add_payment_tables
Revises: c1d2e3f4g5h6
Create Date: 2026-03-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_payment_tables'
down_revision = 'c1d2e3f4g5h6'  # Previous migration (public schema companies)
branch_labels = None
depends_on = None


def upgrade():
    # Add stripe_customer_id to companies table
    op.add_column('companies', sa.Column('stripe_customer_id', sa.String(255), nullable=True, unique=True))
    op.create_index('ix_companies_stripe_customer_id', 'companies', ['stripe_customer_id'])

    # Create payment_methods table (company-level)
    op.create_table(
        'payment_methods',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', sa.String(36), nullable=False),
        sa.Column('stripe_payment_method_id', sa.String(255), unique=True, nullable=False),
        sa.Column('brand', sa.String(50)),
        sa.Column('last4', sa.String(4)),
        sa.Column('exp_month', sa.Integer()),
        sa.Column('exp_year', sa.Integer()),
        sa.Column('is_default', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ondelete='CASCADE'),
    )
    op.create_index('ix_payment_methods_stripe_id', 'payment_methods', ['stripe_payment_method_id'])
    op.create_index('ix_payment_methods_company_id', 'payment_methods', ['company_id'])

    # Create transactions table (company-level)
    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', sa.String(36), nullable=False),
        sa.Column('stripe_payment_intent_id', sa.String(255), unique=True),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(3), default='usd'),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('description', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ondelete='CASCADE'),
    )
    op.create_index('ix_transactions_stripe_id', 'transactions', ['stripe_payment_intent_id'])
    op.create_index('ix_transactions_company_id', 'transactions', ['company_id'])

    # Create subscriptions table (company-level)
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', sa.String(36), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(255), unique=True),
        sa.Column('stripe_price_id', sa.String(255)),
        sa.Column('status', sa.String(50)),
        sa.Column('current_period_start', sa.DateTime()),
        sa.Column('current_period_end', sa.DateTime()),
        sa.Column('cancel_at_period_end', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('canceled_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ondelete='CASCADE'),
    )
    op.create_index('ix_subscriptions_stripe_id', 'subscriptions', ['stripe_subscription_id'])
    op.create_index('ix_subscriptions_company_id', 'subscriptions', ['company_id'])


def downgrade():
    # Drop tables
    op.drop_index('ix_subscriptions_company_id', 'subscriptions')
    op.drop_index('ix_subscriptions_stripe_id', 'subscriptions')
    op.drop_table('subscriptions')
    
    op.drop_index('ix_transactions_company_id', 'transactions')
    op.drop_index('ix_transactions_stripe_id', 'transactions')
    op.drop_table('transactions')
    
    op.drop_index('ix_payment_methods_company_id', 'payment_methods')
    op.drop_index('ix_payment_methods_stripe_id', 'payment_methods')
    op.drop_table('payment_methods')

    # Remove stripe_customer_id from companies
    op.drop_index('ix_companies_stripe_customer_id', 'companies')
    op.drop_column('companies', 'stripe_customer_id')