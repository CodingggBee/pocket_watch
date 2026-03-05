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
    
    Uses after_transaction_create to set search_path for EVERY transaction.

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
    
    # Event listener fires for EVERY new transaction (including after commits)
    @event.listens_for(db, "after_transaction_create")
    def set_search_path_for_transaction(session, transaction):
        """Set search_path whenever a new transaction is created."""
        if transaction.parent is None:  # Only for top-level transactions
            # Execute SET LOCAL on the connection associated with this transaction
            session.connection().execute(text(f'SET LOCAL search_path TO "{schema}", public'))
    
    try:
        yield db
    finally:
        db.close()


# ──────────────────────────────────────────────
# Cross-tenant phone lookup
# ──────────────────────────────────────────────
def find_company_by_phone(phone_number: str) -> dict | None:
    """
    Search across ALL tenant schemas to find which company a phone number belongs to.

    Returns dict with company_id, company_name, user row, and plant memberships,
    or None if not found.
    """
    from app.utils.schema import get_schema_name  # avoid circular import

    db = SessionLocal()
    try:
        # Get all active companies
        companies = db.execute(
            text("SELECT company_id, company_name FROM companies WHERE is_active = true")
        ).fetchall()

        for company in companies:
            cid = company[0]
            cname = company[1]
            schema = get_schema_name(cid)

            # Check if the schema actually exists
            exists = db.execute(
                text(
                    "SELECT 1 FROM information_schema.schemata WHERE schema_name = :s"
                ),
                {"s": schema},
            ).fetchone()
            if not exists:
                continue

            # Look for the phone number in this tenant's users table
            user_row = db.execute(
                text(
                    f'SELECT user_id, phone_number, full_name, is_active '
                    f'FROM "{schema}".users '
                    f'WHERE phone_number = :phone'
                ),
                {"phone": phone_number},
            ).fetchone()

            if user_row:
                # Fetch plant memberships for this user
                plants = db.execute(
                    text(
                        f'SELECT p.plant_id, p.plant_name, pm.role '
                        f'FROM "{schema}".plant_memberships pm '
                        f'JOIN "{schema}".plants p ON p.plant_id = pm.plant_id '
                        f'WHERE pm.user_id = :uid AND pm.is_active = true AND p.is_active = true'
                    ),
                    {"uid": user_row[0]},
                ).fetchall()

                return {
                    "company_id": cid,
                    "company_name": cname or "Pocketwatch.ai Company",
                    "user_id": user_row[0],
                    "phone_number": user_row[1],
                    "full_name": user_row[2],
                    "is_active": user_row[3],
                    "plants": [
                        {"plant_id": pl[0], "plant_name": pl[1], "role": pl[2]}
                        for pl in plants
                    ],
                }

        return None
    finally:
        db.close()


# ──────────────────────────────────────────────
# Initialise public schema tables on startup
# ──────────────────────────────────────────────
def init_db():
    """Create all public-schema tables (admins, companies, etc.)."""
    PublicBase.metadata.create_all(bind=engine)
