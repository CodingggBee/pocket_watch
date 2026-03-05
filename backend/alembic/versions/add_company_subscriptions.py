"""Add company subscriptions and plans

Revision ID: add_company_subscriptions
Revises: add_billing_details
Create Date: 2026-03-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_company_subscriptions'
down_revision = 'add_billing_details'
branch_labels = None
depends_on = None


def upgrade():
    # Create plan_type enum only if it doesn't exist
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_type WHERE typname = 'plantype'
        );
    """))
    enum_exists = result.scalar()
    
    if not enum_exists:
        plan_type_enum = postgresql.ENUM('free', 'premium', name='plantype', create_type=True)
        plan_type_enum.create(op.get_bind(), checkfirst=True)
    else:
        # Enum already exists, just reference it
        plan_type_enum = postgresql.ENUM('free', 'premium', name='plantype', create_type=False)
    
    # Check if table already exists
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'company_subscriptions'
        );
    """))
    table_exists = result.scalar()
    
    if not table_exists:
        # Create company_subscriptions table
        op.create_table(
            'company_subscriptions',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('company_id', sa.String(36), nullable=False),
            sa.Column('plan_type', plan_type_enum, nullable=False, server_default='free'),
            sa.Column('stations_count', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('monthly_cost', sa.Integer(), server_default='0'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('trial_ends_at', sa.DateTime(), nullable=True),
            sa.Column('plan_started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ondelete='CASCADE'),
            sa.UniqueConstraint('company_id', name='uq_company_subscriptions_company_id')
        )
        
        # Create indexes
        op.create_index('ix_company_subscriptions_company_id', 'company_subscriptions', ['company_id'])
        op.create_index('ix_company_subscriptions_plan_type', 'company_subscriptions', ['plan_type'])
        op.create_index('ix_company_subscriptions_is_active', 'company_subscriptions', ['is_active'])
        
        # Create default FREE subscriptions for existing companies
        op.execute("""
            INSERT INTO company_subscriptions (company_id, plan_type, stations_count, monthly_cost, is_active, plan_started_at, created_at, updated_at)
            SELECT 
                company_id,
                'free'::plantype,
                1,
                0,
                true,
                created_at,
                created_at,
                created_at
            FROM companies
            WHERE company_id NOT IN (SELECT company_id FROM company_subscriptions)
        """)


def downgrade():
    # Drop indexes
    op.drop_index('ix_company_subscriptions_is_active', 'company_subscriptions')
    op.drop_index('ix_company_subscriptions_plan_type', 'company_subscriptions')
    op.drop_index('ix_company_subscriptions_company_id', 'company_subscriptions')
    
    # Drop table
    op.drop_table('company_subscriptions')
    
    # Drop enum type
    plan_type_enum = postgresql.ENUM('free', 'premium', name='plantype')
    plan_type_enum.drop(op.get_bind(), checkfirst=True)
