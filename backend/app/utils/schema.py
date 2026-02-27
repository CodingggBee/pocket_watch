"""
Tenant schema management utilities.

Schema naming:  company_{company_id without dashes}
Example:        company_id = "a1b2-c3d4-..."  →  company_a1b2c3d4...
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import engine, TenantBase


def get_schema_name(company_id: str) -> str:
    """Return the PostgreSQL schema name for a given company UUID."""
    return f"company_{company_id.replace('-', '')}"


def create_tenant_schema(company_id: str, db: Session) -> None:
    """
    Create the PostgreSQL schema for a tenant (idempotent).
    Does NOT create the tables — call provision_tenant_tables for that.
    """
    schema = get_schema_name(company_id)
    db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    db.commit()


def provision_tenant_tables(company_id: str) -> None:
    """
    Create all tenant-schema tables for a new company.
    Uses a raw connection so search_path can be set before create_all.

    Called once when a company signs up.
    """
    # Import here to trigger model registration on TenantBase
    import app.models.tenant  # noqa: F401

    schema = get_schema_name(company_id)
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        conn.execute(text(f'SET search_path TO "{schema}"'))
        TenantBase.metadata.create_all(conn)
        conn.execute(text('SET search_path TO public'))


def drop_tenant_schema(company_id: str) -> None:
    """
    Permanently delete a tenant's schema and all its data.
    USE WITH EXTREME CAUTION.
    """
    schema = get_schema_name(company_id)
    with engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
