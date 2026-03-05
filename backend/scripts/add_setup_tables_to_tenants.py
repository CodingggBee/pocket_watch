"""
Add shifts and setup_progress tables to existing tenant schemas.

This script is run once to add the new shifts and setup_progress tables
to existing company schemas that were created before these tables existed.

Usage:
    python scripts/add_setup_tables_to_tenants.py
"""

import sys
from pathlib import Path

# Add backend directory to path so we can import app modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text, inspect
from app.database import engine, TenantBase
from app.models.tenant.shift import Shift
from app.models.tenant.setup_progress import SetupProgress
from app.utils.schema import get_schema_name


def table_exists(conn, schema: str, table_name: str) -> bool:
    """Check if a table exists in the given schema"""
    result = conn.execute(text(
        "SELECT EXISTS ("
        "SELECT FROM information_schema.tables "
        "WHERE table_schema = :schema AND table_name = :table"
        ")"
    ), {"schema": schema, "table": table_name})
    return result.scalar()


def get_all_tenant_schemas(conn) -> list[str]:
    """Get all company_* schemas"""
    result = conn.execute(text(
        "SELECT schema_name FROM information_schema.schemata "
        "WHERE schema_name LIKE 'company_%'"
    ))
    return [row[0] for row in result.fetchall()]


def add_new_tables_to_schema(conn, schema: str):
    """Add shifts and setup_progress tables to a specific schema"""
    print(f"\nProcessing schema: {schema}")
    
    # Check if tables already exist
    shifts_exists = table_exists(conn, schema, "shifts")
    progress_exists = table_exists(conn, schema, "setup_progress")
    
    if shifts_exists and progress_exists:
        print(f"  [OK] Both tables already exist, skipping")
        return "skipped"
    
    # Set search path to this tenant schema
    conn.execute(text(f'SET search_path TO "{schema}"'))
    
    # Create only the new tables (not all tenant tables)
    if not shifts_exists:
        print(f"  -> Creating shifts table...")
        Shift.__table__.create(conn, checkfirst=True)
        print(f"  [OK] shifts table created")
    else:
        print(f"  [OK] shifts table already exists")
    
    if not progress_exists:
        print(f"  -> Creating setup_progress table...")
        SetupProgress.__table__.create(conn, checkfirst=True)
        print(f"  [OK] setup_progress table created")
    else:
        print(f"  [OK] setup_progress table already exists")
    
    # Reset search path
    conn.execute(text('SET search_path TO public'))
    
    return "success"


def main():
    """Main execution"""
    print("=" * 60)
    print("Adding shifts and setup_progress tables to tenant schemas")
    print("=" * 60)
    
    # Import tenant models to register them
    import app.models.tenant  # noqa: F401
    
    with engine.begin() as conn:
        # Get all tenant schemas
        schemas = get_all_tenant_schemas(conn)
        
        if not schemas:
            print("\n[WARNING] No tenant schemas found (no company_* schemas exist)")
            return
        
        print(f"\nFound {len(schemas)} tenant schema(s)")
        
        # Process each schema
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for schema in schemas:
            try:
                result = add_new_tables_to_schema(conn, schema)
                if result == "success":
                    success_count += 1
                elif result == "skipped":
                    skip_count += 1
            except Exception as e:
                print(f"  [ERROR] Error: {e}")
                error_count += 1
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"[OK] Successfully updated: {success_count}")
        print(f"[SKIP] Skipped (already had tables): {skip_count}")
        print(f"[ERROR] Errors: {error_count}")
        print(f"Total schemas processed: {len(schemas)}")
        
        if error_count == 0:
            print("\n[SUCCESS] All schemas processed successfully!")
        else:
            print(f"\n[WARNING] {error_count} schema(s) had errors")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARNING] Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
