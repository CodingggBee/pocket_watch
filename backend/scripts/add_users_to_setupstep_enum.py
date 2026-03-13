"""
Add 'USERS' value to the setupstep enum in all existing tenant schemas.

SQLAlchemy stores Python enum *names* (uppercase) in PostgreSQL.
The 'USERS' step was added to the Python SetupStep enum but the DB enum
was never updated, causing: invalid input value for enum setupstep: "USERS"

Usage:
    python scripts/add_users_to_setupstep_enum.py
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import engine
from sqlalchemy import text


def get_all_tenant_schemas(conn) -> list:
    result = conn.execute(
        text(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name LIKE 'company_%'"
        )
    )
    return [row[0] for row in result.fetchall()]


def enum_value_exists(conn, schema: str, enum_name: str, value: str) -> bool:
    result = conn.execute(
        text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM pg_type t"
            "  JOIN pg_namespace n ON t.typnamespace = n.oid"
            "  JOIN pg_enum e ON t.oid = e.enumtypid"
            "  WHERE n.nspname = :schema AND t.typname = :enum_name AND e.enumlabel = :value"
            ")"
        ),
        {"schema": schema, "enum_name": enum_name, "value": value},
    )
    return result.scalar()


def main():
    print("=" * 60)
    print("Adding 'USERS' to setupstep enum in all tenant schemas")
    print("=" * 60)

    with engine.begin() as conn:
        schemas = get_all_tenant_schemas(conn)

        if not schemas:
            print("\n[WARNING] No tenant schemas found.")
            return

        print(f"\nFound {len(schemas)} tenant schema(s)")
        added = skip = error = 0

        for schema in schemas:
            try:
                if enum_value_exists(conn, schema, "setupstep", "USERS"):
                    print(f"  [SKIP]  {schema}: 'USERS' already in setupstep enum")
                    skip += 1
                    continue

                # Add 'USERS' before 'COMPLETED' if COMPLETED exists, else append
                if enum_value_exists(conn, schema, "setupstep", "COMPLETED"):
                    conn.execute(
                        text(f'ALTER TYPE "{schema}".setupstep ADD VALUE \'USERS\' BEFORE \'COMPLETED\'')
                    )
                else:
                    conn.execute(
                        text(f'ALTER TYPE "{schema}".setupstep ADD VALUE \'USERS\'')
                    )

                print(f"  [OK]    {schema}: added 'USERS' to setupstep enum")
                added += 1

            except Exception as e:
                print(f"  [ERROR] {schema}: {e}")
                error += 1

    print("\n" + "=" * 60)
    print(f"Done — Added: {added}, Skipped: {skip}, Errors: {error}")
    print("=" * 60)


if __name__ == "__main__":
    main()
