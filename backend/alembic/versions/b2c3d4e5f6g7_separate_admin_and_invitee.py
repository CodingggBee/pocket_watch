"""Separate admin and invitee tables

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-23 20:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - separate admin and invitee tables."""

    # Create admins table
    op.create_table(
        "admins",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admins_email"), "admins", ["email"], unique=True)

    # Create invitees table
    op.create_table(
        "invitees",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column("pin_hash", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("phone_verified", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_invitees_phone_number"), "invitees", ["phone_number"], unique=True
    )

    # Create admin_otps table
    op.create_table(
        "admin_otps",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("admin_id", sa.String(length=36), nullable=False),
        sa.Column("otp_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "purpose",
            sa.Enum("VERIFICATION", "PASSWORD_RESET", name="otppurpose"),
            nullable=False,
        ),
        sa.Column("used", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["admins.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_admin_otps_admin_id"), "admin_otps", ["admin_id"], unique=False
    )

    # Create invitee_otps table
    op.create_table(
        "invitee_otps",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("invitee_id", sa.String(length=36), nullable=False),
        sa.Column("otp_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "purpose",
            sa.Enum("VERIFICATION", "PIN_RESET", name="inviteeotppurpose"),
            nullable=False,
        ),
        sa.Column("used", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["invitee_id"],
            ["invitees.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_invitee_otps_invitee_id"), "invitee_otps", ["invitee_id"], unique=False
    )

    # Create admin_refresh_tokens table
    op.create_table(
        "admin_refresh_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("admin_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["admins.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_admin_refresh_tokens_admin_id"),
        "admin_refresh_tokens",
        ["admin_id"],
        unique=False,
    )

    # Create invitee_refresh_tokens table
    op.create_table(
        "invitee_refresh_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("invitee_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["invitee_id"],
            ["invitees.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_invitee_refresh_tokens_invitee_id"),
        "invitee_refresh_tokens",
        ["invitee_id"],
        unique=False,
    )

    # Data migration skipped for fresh database setup

    # Drop old tables
    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index(op.f("ix_otps_user_id"), table_name="otps")
    op.drop_table("otps")
    op.drop_index(op.f("ix_users_phone_number"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")


def downgrade() -> None:
    """Downgrade schema - merge admin and invitee tables back."""

    # Recreate users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.Enum("ADMIN", "INVITEE", name="userrole"), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=True),
        sa.Column("pin_hash", sa.String(length=255), nullable=True),
        sa.Column("phone_verified", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(
        op.f("ix_users_phone_number"), "users", ["phone_number"], unique=True
    )

    # Recreate otps table
    op.create_table(
        "otps",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("otp_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "purpose",
            sa.Enum("VERIFICATION", "PASSWORD_RESET", name="otppurpose"),
            nullable=False,
        ),
        sa.Column("used", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_otps_user_id"), "otps", ["user_id"], unique=False)

    # Recreate refresh_tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False
    )

    # Migrate data back
    # Admins to users
    op.execute(
        """
        INSERT INTO users (id, role, email, password_hash, full_name, is_verified, is_active, created_at, updated_at, phone_number, pin_hash, phone_verified)
        SELECT id, 'ADMIN', email, password_hash, full_name, is_verified, is_active, created_at, updated_at, NULL, NULL, FALSE
        FROM admins
    """
    )

    # Invitees to users
    op.execute(
        """
        INSERT INTO users (id, role, phone_number, pin_hash, full_name, phone_verified, is_active, created_at, updated_at, email, password_hash, is_verified)
        SELECT id, 'INVITEE', phone_number, pin_hash, full_name, phone_verified, is_active, created_at, updated_at, NULL, NULL, FALSE
        FROM invitees
    """
    )

    # Drop new tables
    op.drop_index(
        op.f("ix_invitee_refresh_tokens_invitee_id"),
        table_name="invitee_refresh_tokens",
    )
    op.drop_table("invitee_refresh_tokens")
    op.drop_index(
        op.f("ix_admin_refresh_tokens_admin_id"), table_name="admin_refresh_tokens"
    )
    op.drop_table("admin_refresh_tokens")
    op.drop_index(op.f("ix_invitee_otps_invitee_id"), table_name="invitee_otps")
    op.drop_table("invitee_otps")
    op.drop_index(op.f("ix_admin_otps_admin_id"), table_name="admin_otps")
    op.drop_table("admin_otps")
    op.drop_index(op.f("ix_invitees_phone_number"), table_name="invitees")
    op.drop_table("invitees")
    op.drop_index(op.f("ix_admins_email"), table_name="admins")
    op.drop_table("admins")
