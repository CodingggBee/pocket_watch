# Pocketwatch.ai Backend Architecture

**Multi-Tenant SPC & AI Coaching Platform**

This document explains the complete backend architecture, database design, authentication flows, and API structure of the Pocketwatch.ai system.

---

## Table of Contents

1. [Overview](#overview)
2. [Multi-Tenant Architecture](#multi-tenant-architecture)
3. [Database Schema](#database-schema)
4. [Authentication & Authorization](#authentication--authorization)
5. [API Routes](#api-routes)
6. [Services & Utilities](#services--utilities)
7. [Migrations](#migrations)
8. [Deployment](#deployment)

---

## Overview

### Technology Stack

- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with multi-tenant schema-per-company
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Authentication**: JWT (access + refresh tokens)
- **Email**: Resend API / Gmail SMTP
- **SMS**: Twilio
- **Payments**: Stripe
- **Vector DB**: Pinecone (for AI document embeddings)
- **Deployment**: Vercel Serverless Functions

### Project Structure

```
backend/
├── alembic/                    # Database migrations
│   └── versions/               # Migration files
├── api/                        # Vercel serverless entry point
│   └── index.py
├── app/
│   ├── models/                 # Database models
│   │   ├── admin.py           # Public: Admin users
│   │   ├── company.py         # Public: Companies (tenants)
│   │   ├── payment.py         # Public: Stripe billing
│   │   └── tenant/            # Tenant schema models
│   │       ├── user.py        # Tenant: Plant workers
│   │       ├── plant.py       # Tenant: Manufacturing plants
│   │       ├── station.py     # Tenant: Production stations
│   │       └── ...
│   ├── routes/                # API endpoints
│   │   ├── auth.py           # Admin authentication
│   │   ├── users_auth.py     # Invitee/user authentication
│   │   ├── admin_plants.py   # Plant management
│   │   └── ...
│   ├── schemas/              # Pydantic request/response models
│   ├── services/             # Business logic
│   │   ├── email.py         # Email sending
│   │   └── sms.py           # SMS sending
│   ├── utils/               # Utilities
│   │   ├── jwt.py          # JWT token handling
│   │   ├── otp.py          # OTP generation/verification
│   │   ├── crypto.py       # Password hashing
│   │   └── schema.py       # Schema name helpers
│   ├── config.py           # Settings & environment variables
│   └── database.py         # Database engine & session management
├── main.py                 # FastAPI application entry point
└── requirements.txt        # Python dependencies
```

---

## Multi-Tenant Architecture

### Schema-Per-Tenant Pattern

Pocketwatch.ai uses **schema-per-tenant** isolation in PostgreSQL:

```
PostgreSQL Database
├── public schema                    # Shared across all tenants
│   ├── companies                   # One row per tenant
│   ├── admins                      # Company admins
│   ├── admin_otps
│   ├── admin_refresh_tokens
│   ├── payment_methods             # Stripe billing (company-level)
│   ├── transactions
│   └── subscriptions
│
├── company_abc123 schema           # Tenant 1's private data
│   ├── users                      # Plant workers for company 1
│   ├── plants
│   ├── stations
│   ├── measurements
│   └── ...
│
└── company_xyz789 schema           # Tenant 2's private data
    └── ... (same structure)
```

### How It Works

1. **Signup**: When a company signs up, a new schema `company_{id}` is created
2. **Login**: Admin logs in → JWT contains `company_id`
3. **Request**: API extracts `company_id` from JWT
4. **Database Session**: `SET search_path TO company_{id}, public`
5. **Query**: All queries automatically target the tenant's schema

### Key Benefits

- **Data Isolation**: Complete separation between companies
- **Scalability**: Each tenant can be migrated to separate DB if needed
- **Performance**: Smaller tables per tenant, better query performance
- **Compliance**: Easier to delete all data for a tenant (GDPR)

### Implementation Details

**Database Connection** ([app/database.py](app/database.py))

```python
# Two declarative bases
PublicBase = declarative_base()   # For public schema tables
TenantBase = declarative_base()   # For tenant schema tables

def get_tenant_db(company_id: str):
    """Returns a session scoped to the tenant's schema"""
    schema = f"company_{company_id}"
    db = SessionLocal()
    db.execute(text(f"SET LOCAL search_path TO {schema}, public"))
    yield db
    db.close()
```

**Connection Listeners**

The engine has listeners that reset `search_path` to `public` on every connection checkout to prevent cross-tenant data leaks:

```python
@event.listens_for(engine, "checkout")
def on_checkout(dbapi_connection, connection_record, connection_proxy):
    """Reset search_path to public every time."""
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET search_path TO public")
```

---

## Database Schema

### Public Schema (Shared)

#### Companies Table

The central tenant registry:

```sql
CREATE TABLE companies (
    company_id VARCHAR(36) PRIMARY KEY,
    company_name VARCHAR(255),
    stripe_customer_id VARCHAR(255) UNIQUE,  -- Stripe billing
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### Admins Table

Company administrators who manage their tenant:

```sql
CREATE TABLE admins (
    id VARCHAR(36) PRIMARY KEY,
    company_id VARCHAR(36) REFERENCES companies(company_id),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    full_name VARCHAR(255),
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### Payment Tables (Stripe)

Company-level billing:

```sql
CREATE TABLE payment_methods (
    id UUID PRIMARY KEY,
    company_id VARCHAR(36) REFERENCES companies(company_id) ON DELETE CASCADE,
    stripe_payment_method_id VARCHAR(255) UNIQUE,
    brand VARCHAR(50),
    last4 VARCHAR(4),
    exp_month INTEGER,
    exp_year INTEGER,
    is_default BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY,
    company_id VARCHAR(36) REFERENCES companies(company_id) ON DELETE CASCADE,
    stripe_subscription_id VARCHAR(255) UNIQUE,
    stripe_price_id VARCHAR(255),
    status VARCHAR(50),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    canceled_at TIMESTAMP
);

CREATE TABLE transactions (
    id UUID PRIMARY KEY,
    company_id VARCHAR(36) REFERENCES companies(company_id) ON DELETE CASCADE,
    stripe_payment_intent_id VARCHAR(255) UNIQUE,
    amount INTEGER,  -- cents
    currency VARCHAR(3),
    status VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Tenant Schema (Per-Company)

Each tenant schema contains business data:

#### Users Table (Plant Workers)

```sql
CREATE TABLE users (
    user_id VARCHAR(36) PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    phone_country_code VARCHAR(5),
    full_name VARCHAR(255),
    email VARCHAR(255),
    pin_hash VARCHAR(255),
    phone_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### Plants Table

```sql
CREATE TABLE plants (
    plant_id VARCHAR(36) PRIMARY KEY,
    plant_name VARCHAR(255) NOT NULL,
    location TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### Plant Memberships

Links users to plants with roles:

```sql
CREATE TABLE plant_memberships (
    membership_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(user_id),
    plant_id VARCHAR(36) REFERENCES plants(plant_id),
    role VARCHAR(50),  -- 'admin', 'manager', 'operator'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### Production Lines & Stations

```sql
CREATE TABLE production_lines (
    line_id VARCHAR(36) PRIMARY KEY,
    plant_id VARCHAR(36) REFERENCES plants(plant_id),
    line_name VARCHAR(255),
    is_active BOOLEAN,
    created_at TIMESTAMP
);

CREATE TABLE stations (
    station_id VARCHAR(36) PRIMARY KEY,
    line_id VARCHAR(36) REFERENCES production_lines(line_id),
    station_name VARCHAR(255),
    station_type VARCHAR(100),
    is_active BOOLEAN,
    created_at TIMESTAMP
);
```

#### SPC Data (Measurements, Samples, Characteristics)

```sql
CREATE TABLE characteristics (
    characteristic_id VARCHAR(36) PRIMARY KEY,
    station_id VARCHAR(36) REFERENCES stations(station_id),
    characteristic_name VARCHAR(255),
    unit_of_measure VARCHAR(50),
    target_value NUMERIC,
    upper_spec_limit NUMERIC,
    lower_spec_limit NUMERIC,
    created_at TIMESTAMP
);

CREATE TABLE samples (
    sample_id VARCHAR(36) PRIMARY KEY,
    station_id VARCHAR(36) REFERENCES stations(station_id),
    user_id VARCHAR(36) REFERENCES users(user_id),
    sample_timestamp TIMESTAMP,
    created_at TIMESTAMP
);

CREATE TABLE measurements (
    measurement_id VARCHAR(36) PRIMARY KEY,
    sample_id VARCHAR(36) REFERENCES samples(sample_id),
    characteristic_id VARCHAR(36) REFERENCES characteristics(characteristic_id),
    measured_value NUMERIC,
    is_within_spec BOOLEAN,
    created_at TIMESTAMP
);
```

#### Plant Subscriptions (In-App Purchases)

For mobile app subscriptions (Apple/Google):

```sql
CREATE TABLE plant_subscriptions (
    subscription_id VARCHAR(36) PRIMARY KEY,
    plant_id VARCHAR(36) REFERENCES plants(plant_id),
    platform VARCHAR(50),  -- 'apple' | 'google'
    product_id VARCHAR(255),
    sku VARCHAR(100),
    transaction_id VARCHAR(500) UNIQUE,
    purchase_date TIMESTAMP,
    expiration_date TIMESTAMP,
    status VARCHAR(50),
    auto_renew_status BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## Authentication & Authorization

### Two Authentication Systems

The platform has **two separate auth systems**:

1. **Admin Auth** (Email + OTP) - for company administrators
2. **User Auth** (Phone/SMS + OTP) - for plant workers

### Admin Authentication Flow

**Models**: `Admin`, `AdminOTP`, `AdminRefreshToken` (public schema)
**Routes**: `/admin/auth/*`

#### 1. Signup

```
POST /admin/auth/signup
{
  "email": "admin@company.com",
  "password": "secure123",
  "full_name": "John Admin",
  "company_name": "Acme Corp"
}
```

**Process**:
1. Create `companies` row → new company_id
2. Create tenant schema `company_{id}`
3. Run tenant schema migrations
4. Create `admins` row linked to company
5. Send verification email with OTP
6. Return JWT tokens

#### 2. Login

```
POST /admin/auth/login
{
  "email": "admin@company.com",
  "password": "secure123"
}
```

**Process**:
1. Verify email + password
2. Check `is_verified` and `is_active`
3. Generate access token (15 min) + refresh token (30 days)
4. Return tokens

#### 3. Token Structure

**Access Token Payload**:
```json
{
  "sub": "admin_id",
  "company_id": "abc123",
  "role": "admin",
  "email": "admin@company.com",
  "exp": 1234567890,
  "iat": 1234567000,
  "iss": "pocketwatch-api",
  "aud": "pocketwatch-app"
}
```

**Refresh Token Payload**:
```json
{
  "sub": "admin_id",
  "type": "refresh",
  "exp": 1237248000,
  "iat": 1234567000,
  "jti": "unique_token_id"
}
```

### User (Invitee) Authentication Flow

**Models**: Tenant schema `User` (phone-based)
**Routes**: `/users/auth/*`

#### 1. Request OTP

```
POST /users/auth/request-otp
{
  "phone_number": "+15551234567"
}
```

**Process**:
1. Search ALL tenant schemas for phone number (see `find_company_by_phone()`)
2. Find user's company and plants
3. Generate 6-digit OTP, hash it
4. Send SMS via Twilio
5. Return `{ "message": "OTP sent" }`

#### 2. Verify OTP & Login

```
POST /users/auth/verify-otp
{
  "phone_number": "+15551234567",
  "otp": "123456"
}
```

**Process**:
1. Find user and company via phone lookup
2. Verify OTP hash in tenant schema
3. Generate JWT with company_id and user_id
4. Return tokens + user info + plant memberships

#### 3. PIN Setup (Optional)

After first login, users can set a 4-digit PIN:

```
POST /users/auth/set-pin
Authorization: Bearer <access_token>
{
  "pin": "1234"
}
```

**PIN Login**:
```
POST /users/auth/login-with-pin
{
  "phone_number": "+15551234567",
  "pin": "1234"
}
```

### JWT Utilities ([app/utils/jwt.py](app/utils/jwt.py))

```python
def create_access_token(data: dict, expires_delta: timedelta) -> str:
    """Generate signed JWT access token"""
    
def create_refresh_token(admin_id: str) -> str:
    """Generate signed JWT refresh token"""
    
def decode_token(token: str) -> dict:
    """Verify and decode JWT"""
    
def get_current_admin(token: str = Depends(oauth2_scheme)) -> Admin:
    """Dependency: extract admin from JWT"""
```

### OTP Utilities ([app/utils/otp.py](app/utils/otp.py))

```python
def generate_otp(length: int = 6) -> str:
    """Generate random numeric OTP"""
    
def hash_otp(otp: str) -> str:
    """Hash OTP with bcrypt"""
    
def verify_otp(otp: str, hashed: str) -> bool:
    """Verify OTP against hash"""
```

---

## API Routes

### Admin Routes

#### Auth ([app/routes/auth.py](app/routes/auth.py))

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/admin/auth/signup` | Create admin account + company |
| POST | `/admin/auth/login` | Email/password login |
| POST | `/admin/auth/request-otp` | Request email OTP |
| POST | `/admin/auth/verify-otp` | Verify email OTP |
| POST | `/admin/auth/refresh` | Get new access token |
| POST | `/admin/auth/logout` | Revoke refresh token |
| POST | `/admin/auth/reset-password` | Request password reset |

#### Plants ([app/routes/admin_plants.py](app/routes/admin_plants.py))

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/plants` | List all plants for company |
| POST | `/admin/plants` | Create new plant |
| GET | `/admin/plants/{plant_id}` | Get plant details |
| PUT | `/admin/plants/{plant_id}` | Update plant |
| DELETE | `/admin/plants/{plant_id}` | Delete plant |

#### Users ([app/routes/admin_users.py](app/routes/admin_users.py))

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/users` | List all users in company |
| POST | `/admin/users` | Invite new user |
| GET | `/admin/users/{user_id}` | Get user details |
| PUT | `/admin/users/{user_id}` | Update user |
| DELETE | `/admin/users/{user_id}` | Remove user |

### User Routes

#### Auth ([app/routes/users_auth.py](app/routes/users_auth.py))

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/users/auth/request-otp` | Request SMS OTP |
| POST | `/users/auth/verify-otp` | Verify SMS OTP & login |
| POST | `/users/auth/set-pin` | Set 4-digit PIN |
| POST | `/users/auth/login-with-pin` | Login with phone + PIN |
| POST | `/users/auth/refresh` | Refresh access token |

### Health & Docs

| Endpoint | Description |
|----------|-------------|
| `GET /` | Health check |
| `GET /health` | Health check |
| `GET /docs` | Swagger UI |
| `GET /redoc` | ReDoc documentation |

---

## Services & Utilities

### Email Service ([app/services/email.py](app/services/email.py))

Sends emails using Resend API or Gmail SMTP fallback:

```python
async def send_otp_email(to_email: str, otp: str):
    """Send OTP verification email"""
    
async def send_password_reset_email(to_email: str, reset_link: str):
    """Send password reset email"""
```

### SMS Service ([app/services/sms.py](app/services/sms.py))

Sends SMS using Twilio:

```python
async def send_otp_sms(phone_number: str, otp: str):
    """Send OTP via SMS"""
```

### Schema Utilities ([app/utils/schema.py](app/utils/schema.py))

Helpers for tenant schema management:

```python
def get_schema_name(company_id: str) -> str:
    """Get tenant schema name: company_{id}"""
    
def create_tenant_schema(company_id: str, db: Session):
    """Create new tenant schema and run migrations"""
    
def drop_tenant_schema(company_id: str, db: Session):
    """Drop tenant schema (use with caution!)"""
```

### Crypto Utilities ([app/utils/crypto.py](app/utils/crypto.py))

Password hashing with bcrypt:

```python
def hash_password(password: str) -> str:
    """Hash password with bcrypt"""
    
def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
```

---

## Migrations

### Alembic Configuration

**Two migration targets**:
1. **Public schema** migrations (default)
2. **Tenant schema** migrations (applied to each tenant on creation)

### Migration Commands

```bash
# Generate new migration
alembic revision --autogenerate -m "Description"

# Apply all migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

### Migration Files

Located in `alembic/versions/`:

| Migration | Description |
|-----------|-------------|
| `a1b2c3d4e5f6_initial_postgresql_schema.py` | Initial unified users table |
| `b2c3d4e5f6g7_separate_admin_and_invitee.py` | Split into admins/invitees |
| `c1d2e3f4g5h6_public_schema_companies.py` | Add companies + multi-tenant |
| `d1e2f3g4h5i6_admin_profile_fields.py` | Add admin profile fields |
| `add_payment_tables.py` | Add Stripe payment tables |

### How Tenant Migrations Work

When a new company signs up:

1. Create company row in public schema
2. Create new PostgreSQL schema `company_{id}`
3. Set `search_path` to new schema
4. Run `TenantBase.metadata.create_all()` to create all tenant tables
5. Insert default data (optional)

This happens in the signup endpoint:

```python
# Create company
company = Company(company_id=company_id, company_name=company_name)
db.add(company)
db.commit()

# Create tenant schema
schema = f"company_{company_id}"
db.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
db.execute(text(f"SET search_path TO {schema}, public"))

# Create all tenant tables
TenantBase.metadata.create_all(bind=engine)
```

---

## Deployment

### Vercel Configuration

**Entry Point**: `api/index.py`

```python
# Vercel expects 'app' variable for ASGI applications
from main import app
```

**vercel.json**:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ]
}
```

### Environment Variables (.env)

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# JWT
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Email (Resend)
RESEND_API_KEY=re_xxxxx
FROM_EMAIL=noreply@yourdomain.com

# Email (Gmail fallback)
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password

# SMS (Twilio)
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=your-token
TWILIO_PHONE_NUMBER=+15551234567

# Stripe
STRIPE_SECRET_KEY=sk_test_xxxxx

# Pinecone (AI)
PINECONE_API_KEY=xxxxx
PINECONE_INDEX_NAME=pocketwatch-docs

# App
APP_NAME=Pocketwatch.ai
APP_URL=https://yourdomain.com
API_URL=https://api.yourdomain.com
ENVIRONMENT=production
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up .env file
cp .env.example .env
# Edit .env with your values

# Run migrations
alembic upgrade head

# Start development server
uvicorn main:app --reload --port 8000
```

### Testing

```bash
# Run tests (when implemented)
pytest

# Test specific endpoint
curl http://localhost:8000/health
```

---

## Common Patterns

### Protected Routes (Admin)

```python
from app.utils.jwt import get_current_admin

@router.get("/admin/plants")
async def list_plants(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    # current_admin has company_id
    # Query tenant schema automatically via search_path
    ...
```

### Tenant Database Access

```python
from app.database import get_tenant_db

@router.get("/admin/users")
async def list_users(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_tenant_db_dependency(current_admin.company_id))
):
    # db session is scoped to company's schema
    users = db.query(User).all()
    return users
```

### Cross-Tenant Phone Lookup

```python
from app.database import find_company_by_phone

result = find_company_by_phone("+15551234567")
if result:
    company_id = result["company_id"]
    user_id = result["user_id"]
    plants = result["plants"]
```

---

## Troubleshooting

### Common Issues

**1. Migration Error: "table does not exist"**

If you see errors about missing tables, check which schema the migration is targeting:

- Public schema migrations: should reference `companies`, `admins`, etc.
- Tenant schema migrations: should reference `users`, `plants`, etc.

**2. "relation users does not exist" in public schema**

The `users` table only exists in tenant schemas. Use `admins` table for public schema.

**3. Cross-tenant data leak**

Always ensure `search_path` is properly set. The connection listeners in `database.py` reset it on every checkout.

**4. JWT expired**

Access tokens expire in 15 minutes. Use the refresh token to get a new access token:

```
POST /admin/auth/refresh
Authorization: Bearer <refresh_token>
```

---

## Future Enhancements

- [ ] Add Redis for caching & session management
- [ ] Implement rate limiting (per-tenant)
- [ ] Add WebSocket support for real-time SPC monitoring
- [ ] Implement comprehensive test suite
- [ ] Add OpenAPI schema validation
- [ ] Implement tenant data export (GDPR compliance)
- [ ] Add audit logging for all tenant data changes
- [ ] Implement tenant resource quotas/limits
- [ ] Add background job system (Celery/RQ)
- [ ] Implement tenant-specific feature flags

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [Multi-Tenant Architecture Patterns](https://docs.microsoft.com/en-us/azure/architecture/guide/multitenant/overview)

---

**Last Updated**: March 3, 2026
**Version**: 2.0.0
