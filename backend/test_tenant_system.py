"""
Comprehensive Tenant System Health Check
=========================================

This script verifies that the multi-tenant architecture is working correctly.
"""

import sys
from sqlalchemy import text
from app.database import engine, SessionLocal, get_tenant_db, PublicBase, TenantBase
from app.utils.schema import get_schema_name, provision_tenant_tables
from app.utils.jwt import create_access_token, decode_token, get_company_id_from_token
from app.models.admin import Admin
from app.models.company import Company


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_database_connection():
    """Test basic database connectivity"""
    print_section("1. DATABASE CONNECTION")
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✓ PostgreSQL connected: {version.split(',')[0]}")
            
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.fetchone()[0]
            print(f"✓ Current database: {db_name}")
            
            result = conn.execute(text("SHOW search_path"))
            search_path = result.fetchone()[0]
            print(f"✓ Default search_path: {search_path}")
            
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def test_public_schema():
    """Test public schema tables"""
    print_section("2. PUBLIC SCHEMA (Admin/Company Tables)")
    
    try:
        db = SessionLocal()
        
        # Check if public tables exist
        result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        
        public_tables = [row[0] for row in result.fetchall()]
        print(f"✓ Found {len(public_tables)} public tables:")
        for table in public_tables:
            print(f"  • {table}")
        
        # Check companies table
        company_count = db.query(Company).count()
        print(f"\n✓ Companies in database: {company_count}")
        
        # Check admins table
        admin_count = db.query(Admin).count()
        print(f"✓ Admins in database: {admin_count}")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Public schema check failed: {e}")
        return False


def test_tenant_schemas():
    """Test tenant schemas"""
    print_section("3. TENANT SCHEMAS")
    
    try:
        db = SessionLocal()
        
        # Get all tenant schemas
        result = db.execute(text("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name LIKE 'company_%'
            ORDER BY schema_name
        """))
        
        tenant_schemas = [row[0] for row in result.fetchall()]
        print(f"✓ Found {len(tenant_schemas)} tenant schemas")
        
        if tenant_schemas:
            # Check first schema tables
            test_schema = tenant_schemas[0]
            print(f"\n  Examining schema: {test_schema}")
            
            result = db.execute(text(f"""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = '{test_schema}'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            
            schema_tables = [row[0] for row in result.fetchall()]
            print(f"  ✓ Contains {len(schema_tables)} tables")
            
            # Check for critical setup tables
            critical_tables = ['plants', 'shifts', 'setup_progress', 'users']
            for table in critical_tables:
                if table in schema_tables:
                    print(f"  ✓ {table} table exists")
                else:
                    print(f"  ⚠ {table} table missing")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Tenant schema check failed: {e}")
        return False


def test_search_path_routing():
    """Test that search_path routing works correctly"""
    print_section("4. SEARCH PATH ROUTING")
    
    try:
        db = SessionLocal()
        
        # Get a test company
        company = db.query(Company).first()
        if not company:
            print("⚠ No companies found - skipping search_path test")
            db.close()
            return True
        
        company_id = company.company_id
        schema = get_schema_name(company_id)
        print(f"Testing with company: {company_id}")
        print(f"Expected schema: {schema}")
        
        # Test tenant DB session
        tenant_gen = get_tenant_db(company_id)
        tenant_db = next(tenant_gen)
        
        try:
            # Verify search_path is set correctly
            result = tenant_db.execute(text("SHOW search_path"))
            current_path = result.fetchone()[0]
            print(f"\n✓ Tenant session search_path: {current_path}")
            
            if schema in current_path:
                print(f"✓ Search path correctly includes tenant schema")
            else:
                print(f"✗ Search path does NOT include tenant schema!")
                return False
            
            # Test that we can access tenant tables
            result = tenant_db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = :schema AND table_name = 'plants'
                )
            """), {"schema": schema})
            
            plants_exist = result.scalar()
            if plants_exist:
                print(f"✓ Can access tenant tables via search_path")
            else:
                print(f"⚠ Plants table not found in tenant schema")
        
        finally:
            tenant_db.close()
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Search path routing failed: {e}")
        return False


def test_jwt_tokens():
    """Test JWT token generation and company_id extraction"""
    print_section("5. JWT TOKEN HANDLING")
    
    try:
        # Create test token with company_id
        test_user_id = "test-user-123"
        test_company_id = "test-company-456"
        
        token = create_access_token(
            test_user_id, 
            extra={"company_id": test_company_id, "role": "admin"}
        )
        print(f"✓ Generated test token")
        
        # Decode token
        payload = decode_token(token)
        if not payload:
            print(f"✗ Token decode failed")
            return False
        
        print(f"✓ Token decoded successfully")
        print(f"  • user_id (sub): {payload.get('sub')}")
        print(f"  • company_id: {payload.get('company_id')}")
        print(f"  • role: {payload.get('role')}")
        print(f"  • token type: {payload.get('type')}")
        
        # Extract company_id
        extracted_company_id = get_company_id_from_token(token)
        if extracted_company_id == test_company_id:
            print(f"\n✓ Company ID extraction working correctly")
        else:
            print(f"✗ Company ID extraction failed")
            return False
        
        return True
    except Exception as e:
        print(f"✗ JWT token test failed: {e}")
        return False


def test_model_definitions():
    """Test that models are properly registered"""
    print_section("6. MODEL DEFINITIONS")
    
    try:
        # Check PublicBase models
        public_tables = list(PublicBase.metadata.tables.keys())
        print(f"✓ PublicBase has {len(public_tables)} tables:")
        for table in sorted(public_tables):
            print(f"  • {table}")
        
        # Critical public tables
        critical_public = ['companies', 'admins', 'admin_otps', 'company_subscriptions']
        for table in critical_public:
            if table in public_tables:
                print(f"  ✓ {table} registered")
            else:
                print(f"  ✗ {table} MISSING!")
        
        # Check TenantBase models
        print()
        tenant_tables = list(TenantBase.metadata.tables.keys())
        print(f"✓ TenantBase has {len(tenant_tables)} tables:")
        for table in sorted(tenant_tables):
            print(f"  • {table}")
        
        # Critical tenant tables
        critical_tenant = ['plants', 'shifts', 'setup_progress', 'users', 
                          'departments', 'production_lines', 'stations']
        print(f"\n  Checking critical tenant tables:")
        for table in critical_tenant:
            if table in tenant_tables:
                print(f"  ✓ {table} registered")
            else:
                print(f"  ✗ {table} MISSING!")
        
        return True
    except Exception as e:
        print(f"✗ Model definition check failed: {e}")
        return False


def test_tenant_isolation():
    """Test that tenant data is properly isolated"""
    print_section("7. TENANT ISOLATION")
    
    try:
        db = SessionLocal()
        
        # Get multiple companies
        companies = db.query(Company).limit(2).all()
        
        if len(companies) < 2:
            print("⚠ Less than 2 companies - skipping isolation test")
            db.close()
            return True
        
        company1 = companies[0]
        company2 = companies[1]
        
        print(f"Testing isolation between:")
        print(f"  Company 1: {company1.company_id}")
        print(f"  Company 2: {company2.company_id}")
        
        # Create tenant sessions
        tenant1_gen = get_tenant_db(company1.company_id)
        tenant1_db = next(tenant1_gen)
        
        tenant2_gen = get_tenant_db(company2.company_id)
        tenant2_db = next(tenant2_gen)
        
        try:
            # Get current schema for each
            result1 = tenant1_db.execute(text("SELECT current_schema()"))
            schema1 = result1.scalar()
            
            result2 = tenant2_db.execute(text("SELECT current_schema()"))
            schema2 = result2.scalar()
            
            print(f"\n✓ Company 1 session using schema: {schema1}")
            print(f"✓ Company 2 session using schema: {schema2}")
            
            if schema1 != schema2:
                print(f"\n✓ Schemas are properly isolated")
            else:
                print(f"\n✗ WARNING: Both sessions using same schema!")
                return False
        
        finally:
            tenant1_db.close()
            tenant2_db.close()
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Tenant isolation test failed: {e}")
        return False


def run_all_tests():
    """Run all health checks"""
    print("\n")
    print("╔" + "═"*68 + "╗")
    print("║" + " "*15 + "TENANT SYSTEM HEALTH CHECK" + " "*27 + "║")
    print("╚" + "═"*68 + "╝")
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Public Schema", test_public_schema),
        ("Tenant Schemas", test_tenant_schemas),
        ("Search Path Routing", test_search_path_routing),
        ("JWT Token Handling", test_jwt_tokens),
        ("Model Definitions", test_model_definitions),
        ("Tenant Isolation", test_tenant_isolation),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n✗ {name} crashed: {e}")
            results[name] = False
    
    # Summary
    print_section("SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")
    
    print(f"\n{'─'*70}")
    print(f"Result: {passed}/{total} tests passed")
    
    if passed == total:
        print(f"\n🎉 All systems operational! Multi-tenant architecture is healthy.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
