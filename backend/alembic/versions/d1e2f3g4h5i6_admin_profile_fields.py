"""Admin profile fields: first_name, last_name, phone, profile_completed

Revision ID: d1e2f3g4h5i6
Revises: c1d2e3f4g5h6
Create Date: 2026-02-28 15:30:00.000000

This migration:
  1. Makes password_hash nullable (set during create-account-info, not signup)
  2. Adds first_name, last_name, phone_number, phone_country_code columns
  3. Adds profile_completed boolean column
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3g4h5i6"
down_revision: Union[str, None] = "c1d2e3f4g5h6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make password_hash nullable (not required at signup anymore)
    op.alter_column(
        "admins",
        "password_hash",
        existing_type=sa.String(255),
        nullable=True,
    )

    # Add new profile columns
    op.add_column("admins", sa.Column("first_name", sa.String(255), nullable=True))
    op.add_column("admins", sa.Column("last_name", sa.String(255), nullable=True))
    op.add_column("admins", sa.Column("phone_number", sa.String(20), nullable=True))
    op.add_column("admins", sa.Column("phone_country_code", sa.String(5), nullable=True))
    op.add_column(
        "admins",
        sa.Column("profile_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    # Mark existing admins who already have a password as profile_completed
    op.execute("UPDATE admins SET profile_completed = true WHERE password_hash IS NOT NULL")


def downgrade() -> None:
    op.drop_column("admins", "profile_completed")
    op.drop_column("admins", "phone_country_code")
    op.drop_column("admins", "phone_number")
    op.drop_column("admins", "last_name")
    op.drop_column("admins", "first_name")

    op.alter_column(
        "admins",
        "password_hash",
        existing_type=sa.String(255),
        nullable=False,
    )
