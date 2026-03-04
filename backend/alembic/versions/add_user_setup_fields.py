"""add user setup fields

Revision ID: e2f3g4h5i6j7
Revises: 3bc3800a9168
Create Date: 2026-03-04 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2f3g4h5i6j7'
down_revision = '3bc3800a9168'
branch_labels = None
depends_on = None


def upgrade():
    """Add user setup fields to users and setup_progress tables in ALL tenant schemas"""
    
    # Get connection
    conn = op.get_bind()
    
    # Get all tenant schemas (company_*)
    result = conn.execute(sa.text("""
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name LIKE 'company_%'
    """))
    
    tenant_schemas = [row[0] for row in result.fetchall()]
    
    print(f"[MIGRATION] Found {len(tenant_schemas)} tenant schemas to upgrade")
    
    for schema in tenant_schemas:
        print(f"[MIGRATION] Upgrading schema: {schema}")
        
        try:
            # Check if users table exists
            users_exists = conn.execute(sa.text(f"""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = '{schema}' AND table_name = 'users'
                )
            """)).scalar()
            
            if users_exists:
                # Add fields to users table
                conn.execute(sa.text(f"""
                    ALTER TABLE "{schema}".users 
                    ADD COLUMN IF NOT EXISTS first_name VARCHAR(100),
                    ADD COLUMN IF NOT EXISTS last_name VARCHAR(100),
                    ADD COLUMN IF NOT EXISTS default_shift_id VARCHAR(36)
                """))
                
                # Add foreign key constraint if shifts table exists
                shifts_exists = conn.execute(sa.text(f"""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = '{schema}' AND table_name = 'shifts'
                    )
                """)).scalar()
                
                if shifts_exists:
                    conn.execute(sa.text(f"""
                        DO $$ BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.table_constraints 
                                WHERE constraint_schema = '{schema}' 
                                AND table_name = 'users' 
                                AND constraint_name = 'users_default_shift_id_fkey'
                            ) THEN
                                ALTER TABLE "{schema}".users 
                                ADD CONSTRAINT users_default_shift_id_fkey 
                                FOREIGN KEY (default_shift_id) REFERENCES "{schema}".shifts(shift_id);
                            END IF;
                        END $$;
                    """))
                
                # Create index on default_shift_id
                conn.execute(sa.text(f"""
                    CREATE INDEX IF NOT EXISTS idx_users_default_shift 
                    ON "{schema}".users(default_shift_id)
                """))
                
                print(f"[MIGRATION]   ✓ Updated users table")
            else:
                print(f"[MIGRATION]   → Skipped users table (doesn't exist yet)")
            
            # Check if setup_progress table exists
            setup_progress_exists = conn.execute(sa.text(f"""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = '{schema}' AND table_name = 'setup_progress'
                )
            """)).scalar()
            
            if setup_progress_exists:
                # Check if setupstep enum exists in this schema
                setupstep_exists = conn.execute(sa.text(f"""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_type t
                        JOIN pg_namespace n ON t.typnamespace = n.oid
                        WHERE n.nspname = '{schema}' AND t.typname = 'setupstep'
                    )
                """)).scalar()
                
                if setupstep_exists:
                    # Check if 'users' enum value already exists
                    users_value_exists = conn.execute(sa.text(f"""
                        SELECT EXISTS (
                            SELECT 1 FROM pg_type t 
                            JOIN pg_namespace n ON t.typnamespace = n.oid
                            JOIN pg_enum e ON t.oid = e.enumtypid 
                            WHERE n.nspname = '{schema}' AND t.typname = 'setupstep' AND e.enumlabel = 'users'
                        )
                    """)).scalar()
                    
                    if not users_value_exists:
                        # Check if 'completed' enum value exists
                        completed_exists = conn.execute(sa.text(f"""
                            SELECT EXISTS (
                                SELECT 1 FROM pg_type t 
                                JOIN pg_namespace n ON t.typnamespace = n.oid
                                JOIN pg_enum e ON t.oid = e.enumtypid 
                                WHERE n.nspname = '{schema}' AND t.typname = 'setupstep' AND e.enumlabel = 'completed'
                            )
                        """)).scalar()
                        
                        if completed_exists:
                            # Add 'users' before 'completed'
                            conn.execute(sa.text(f"""
                                ALTER TYPE "{schema}".setupstep ADD VALUE 'users' BEFORE 'completed'
                            """))
                        else:
                            # Just add 'users' at the end
                            conn.execute(sa.text(f"""
                                ALTER TYPE "{schema}".setupstep ADD VALUE 'users'
                            """))
                    
                    print(f"[MIGRATION]   ✓ Updated setupstep enum")
                else:
                    print(f"[MIGRATION]   → Skipped setupstep enum (doesn't exist yet)")
                
                # Add users_completed field to setup_progress table
                conn.execute(sa.text(f"""
                    ALTER TABLE "{schema}".setup_progress 
                    ADD COLUMN IF NOT EXISTS users_completed BOOLEAN NOT NULL DEFAULT FALSE
                """))
                
                print(f"[MIGRATION]   ✓ Updated setup_progress table")
            else:
                print(f"[MIGRATION]   → Skipped setup_progress table (doesn't exist yet)")
            
            print(f"[MIGRATION] ✓ Schema {schema} upgraded successfully")
            
        except Exception as e:
            print(f"[MIGRATION] ✗ Error upgrading schema {schema}: {e}")
            raise
    
    print(f"[MIGRATION] All {len(tenant_schemas)} tenant schemas upgraded successfully")


def downgrade():
    """Remove user setup fields from users and setup_progress tables in ALL tenant schemas"""
    
    # Get connection
    conn = op.get_bind()
    
    # Get all tenant schemas (company_*)
    result = conn.execute(sa.text("""
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name LIKE 'company_%'
    """))
    
    tenant_schemas = [row[0] for row in result.fetchall()]
    
    print(f"[MIGRATION] Found {len(tenant_schemas)} tenant schemas to downgrade")
    
    for schema in tenant_schemas:
        print(f"[MIGRATION] Downgrading schema: {schema}")
        
        try:
            # Check if users table exists
            users_exists = conn.execute(sa.text(f"""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = '{schema}' AND table_name = 'users'
                )
            """)).scalar()
            
            if users_exists:
                # Remove fields from users table
                conn.execute(sa.text(f"""
                    ALTER TABLE "{schema}".users 
                    DROP COLUMN IF EXISTS first_name,
                    DROP COLUMN IF EXISTS last_name,
                    DROP COLUMN IF EXISTS default_shift_id
                """))
                print(f"[MIGRATION]   ✓ Removed columns from users table")
            else:
                print(f"[MIGRATION]   → Skipped users table (doesn't exist)")
            
            # Check if setup_progress table exists
            setup_progress_exists = conn.execute(sa.text(f"""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = '{schema}' AND table_name = 'setup_progress'
                )
            """)).scalar()
            
            if setup_progress_exists:
                # Remove users_completed field from setup_progress table
                conn.execute(sa.text(f"""
                    ALTER TABLE "{schema}".setup_progress 
                    DROP COLUMN IF EXISTS users_completed
                """))
                print(f"[MIGRATION]   ✓ Removed column from setup_progress table")
            else:
                print(f"[MIGRATION]   → Skipped setup_progress table (doesn't exist)")
            
            print(f"[MIGRATION] ✓ Schema {schema} downgraded successfully")
            
        except Exception as e:
            print(f"[MIGRATION] ✗ Error downgrading schema {schema}: {e}")
            raise
    
    print(f"[MIGRATION] All {len(tenant_schemas)} tenant schemas downgraded successfully")
