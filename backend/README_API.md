# PocketWatch Backend API 🕐

FastAPI backend with complete authentication system using:
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **Alembic** - Database migrations
- **Argon2** - Secure password/OTP hashing
- **JWT** - Token-based authentication
- **Resend** - Beautiful email delivery

---

## 🚀 Quick Start

### 1. Set up environment

```bash
# Install UV (if not already installed)
pip install uv

# Navigate to backend directory
cd backend

# Create virtual environment (already done)
uv venv --python 3.11

# Activate virtual environment
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
uv sync
```

### 2. Configure environment variables

```bash
# Edit .env and add your Resend API key
# RESEND_API_KEY=re_your_api_key_here
# FROM_EMAIL=noreply@yourdomain.com
```

### 3. Run database migrations (already done)

```bash
# Apply migrations
alembic upgrade head
```

### 4. Start the server

```bash
# Development mode (with auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc

---

## 🔐 Complete Authentication Flows

### FLOW 1: User Signup → Email Verification

#### Step 1: Signup
```http
POST /auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securePassword123",
  "full_name": "John Doe"
}
```

**Response:**
```json
{
  "message": "Signup successful! Please check your email for verification code.",
  "email": "user@example.com",
  "user_id": "uuid"
}
```

**Backend Process:**
✅ Validates email and password
✅ Hashes password with Argon2
✅ Creates user (not verified)
✅ Generates 6-digit OTP
✅ Hashes OTP with Argon2
✅ Sends themed email via Resend

#### Step 2: Verify OTP
```http
POST /auth/verify-otp
Content-Type: application/json

{
  "email": "user@example.com",
  "otp": "123456"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_verified": true
  }
}
```

**Sets HTTP-only cookie:** `refresh_token` (30 days)

---

### FLOW 2: Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response:** Same as verify-otp (access_token + refresh_token cookie)

---

### FLOW 3: Access Protected Resources

```http
GET /auth/me
Authorization: Bearer eyJhbGc...
```

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_verified": true,
  "is_active": true,
  "created_at": "2026-02-23T..."
}
```

---

### FLOW 4: Refresh Access Token

```http
POST /auth/refresh
Cookie: refresh_token=eyJhbGc...
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

---

### FLOW 5: Password Reset

#### Step 1: Request Reset
```http
POST /auth/forgot-password
Content-Type: application/json

{
  "email": "user@example.com"
}
```

#### Step 2: Reset Password
```http
POST /auth/reset-password
Content-Type: application/json

{
  "email": "user@example.com",
  "otp": "456789",
  "new_password": "newSecurePassword123"
}
```

**Security:** All refresh tokens are revoked (logs out all devices)

---

### FLOW 6: Resend OTP

```http
POST /auth/resend-otp
Content-Type: application/json

{
  "email": "user@example.com",
  "purpose": "VERIFICATION"
}
```

---

### FLOW 7: Logout

```http
POST /auth/logout
Cookie: refresh_token=eyJhbGc...
```

**Revokes the specific refresh token** (single device logout)

---

## 🔒 Security Features

### Password Security
✅ **Argon2id** hashing (memory-hard, GPU-resistant)
✅ Time cost: 2, Memory: 64 MB
✅ 32-byte hash with 16-byte salt

### OTP Security
✅ Cryptographically random 6-digit codes
✅ Hashed with Argon2
✅ 10-minute expiration
✅ Single-use (marked as used)

### JWT Tokens
✅ **Access Token**: 15 minutes
✅ **Refresh Token**: 30 days
✅ HTTP-only cookies (XSS protection)
✅ Signature verification

---

## 📧 Email Templates

Beautiful themed emails (red/black):
- Verification Email
- Password Reset Email

---

## 🛠️ Development

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Testing

```bash
# Start server
uvicorn main:app --reload

# Test signup
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123456"}'
```

---

## 📦 Project Structure

```
backend/
├── app/
│   ├── models/          # Database models
│   ├── routes/          # API endpoints
│   ├── schemas/         # Request/response schemas
│   ├── services/        # Email service
│   ├── utils/           # JWT, crypto, OTP
│   ├── config.py
│   └── database.py
├── alembic/             # Migrations
├── main.py              # FastAPI app
├── .env                 # Environment variables
└── pyproject.toml       # Dependencies
```

---

**Built with ❤️ using FastAPI + Argon2 + JWT**
