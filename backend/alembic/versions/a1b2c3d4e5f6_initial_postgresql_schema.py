"""Initial PostgreSQL schema with admin and invitee users

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2026-02-23 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.Enum('ADMIN', 'INVITEE', name='userrole'), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        # Admin fields
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        # Invitee fields
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('pin_hash', sa.String(length=255), nullable=True),
        sa.Column('phone_verified', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_phone_number'), 'users', ['phone_number'], unique=True)
    
    # Create OTPs table
    op.create_table(
        'otps',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('otp_hash', sa.String(length=255), nullable=False),
        sa.Column('purpose', sa.Enum('VERIFICATION', 'PASSWORD_RESET', name='otppurpose'), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_otps_user_id'), 'otps', ['user_id'], unique=False)
    
    # Create refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_index(op.f('ix_otps_user_id'), table_name='otps')
    op.drop_table('otps')
    op.drop_index(op.f('ix_users_phone_number'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
