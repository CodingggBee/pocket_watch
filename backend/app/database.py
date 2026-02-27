from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import Pool
from app.config import get_settings
from typing import Generator

settings = get_settings()

# ──────────────────────────────────────────────
# Engine (PostgreSQL only — no SQLite args)
# ──────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,      # test connection before using it
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,        # recycle connections every 5 min (Railway drops idle ~10 min)
    pool_timeout=30,
    connect_args={"connect_timeout": 10},
    echo=settings.ENVIRONMENT == "development",
)


@event.listens_for(engine, "connect")
def on_connect(dbapi_connection, connection_record):
    """Reset search_path to public on every fresh connection."""
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET search_path TO public")


@event.listens_for(engine, "checkout")
def on_checkout(dbapi_connection, connection_record, connection_proxy):
    """Reset search_path to public every time a connection is checked out from the pool."""
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET search_path TO public")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ──────────────────────────────────────────────
# Declarative bases
# ──────────────────────────────────────────────
# Public schema base — admins, companies, auth tables
PublicBase = declarative_base()

# Tenant schema base — all per-company business tables
# Tables are defined WITHOUT schema; search_path handles routing at runtime.
TenantBase = declarative_base()


# ──────────────────────────────────────────────
# Dependencies
# ──────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """Plain session targeting the public schema (default search_path)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_tenant_db(company_id: str) -> Generator[Session, None, None]:
    """
    Session with search_path set to the company's private schema.

    Usage (in a route dependency):
        from fastapi import Depends
        from functools import partial

        def tenant_db(company_id: str = ...) -> Session:
            yield from get_tenant_db(company_id)

    Or use the helper `tenant_db_dependency(company_id)` below.
    """
    from app.utils.schema import get_schema_name  # avoid circular import
    schema = get_schema_name(company_id)
    db = SessionLocal()
    try:
        # SET LOCAL scopes the path to the current transaction only
        db.execute(text(f"SET LOCAL search_path TO {schema}, public"))
        yield db
    finally:
        db.close()


# ──────────────────────────────────────────────
# Initialise public schema tables on startup
# ──────────────────────────────────────────────
def init_db():
    """Create all public-schema tables (admins, companies, etc.)."""
    PublicBase.metadata.create_all(bind=engine)
