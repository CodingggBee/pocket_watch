"""
Add model_ids JSONB column to the stations table in all existing tenant schemas.

Usage:
    python scripts/add_model_ids_to_stations.py
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


def column_exists(conn, schema: str, table: str, column: str) -> bool:
    result = conn.execute(
        text(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :table AND column_name = :column"
            ")"
        ),
        {"schema": schema, "table": table, "column": column},
    )
    return result.scalar()


def main():
    print("=" * 60)
    print("Adding model_ids column to stations in all tenant schemas")
    print("=" * 60)

    with engine.begin() as conn:
        schemas = get_all_tenant_schemas(conn)

        if not schemas:
            print("\n[WARNING] No tenant schemas found.")
            return

        print(f"\nFound {len(schemas)} tenant schema(s)")
        success = skip = error = 0

        for schema in schemas:
            try:
                if column_exists(conn, schema, "stations", "model_ids"):
                    print(f"  [SKIP] {schema}: model_ids already exists")
                    skip += 1
                else:
                    conn.execute(
                        text(
                            f'ALTER TABLE "{schema}".stations '
                            f"ADD COLUMN model_ids JSONB"
                        )
                    )
                    print(f"  [OK]   {schema}: model_ids column added")
                    success += 1
            except Exception as e:
                print(f"  [ERROR] {schema}: {e}")
                error += 1

        print("\n" + "=" * 60)
        print(f"Added:   {success}")
        print(f"Skipped: {skip}")
        print(f"Errors:  {error}")
        print("=" * 60)


if __name__ == "__main__":
    main()
