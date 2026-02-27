"""Public schema: companies + admins (multi-tenant base)

Revision ID: c1d2e3f4g5h6
Revises: b2c3d4e5f6g7
Create Date: 2026-02-26 22:24:00.000000

This migration:
  1. Creates `companies` table (one row per tenant)
  2. Adds `company_id` FK column to `admins`
  3. Drops the old generic `users`, `otps`, `refresh_tokens` tables
     left from the SQLite era (if they still exist).
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "c1d2e3f4g5h6"
down_revision: Union[str, None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create companies table ─────────────────────────────
    op.create_table(
        "companies",
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("company_id"),
    )

    # ── 2. Add company_id to admins ───────────────────────────
    op.add_column(
        "admins",
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.company_id"), nullable=True),
    )
    op.create_index("ix_admins_company_id", "admins", ["company_id"], unique=False)

    # ── 3. Drop legacy unified tables (if they exist) ─────────
    #    These were created in migration a1b2c3d4e5f6 (old SQLite schema).
    #    Safe to drop since we now use per-tenant schemas.
    with op.get_context().autocommit_block():
        op.execute("""
            DROP TABLE IF EXISTS refresh_tokens CASCADE;
            DROP TABLE IF EXISTS otps CASCADE;
            DROP TABLE IF EXISTS users CASCADE;
        """)


def downgrade() -> None:
    op.drop_index("ix_admins_company_id", table_name="admins")
    op.drop_column("admins", "company_id")
    op.drop_table("companies")
