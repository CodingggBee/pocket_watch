# Pocketwatch.ai API Reference

Complete API endpoint documentation with request/response examples.

**Base URL**: `https://api.pocketwatch.ai` (production) or `http://localhost:8000` (local)

---

## Authentication

All authenticated endpoints require a JWT token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

---

## Admin API

### Auth Endpoints

#### 1. Admin Signup

Create a new company and admin account.

**Endpoint**: `POST /admin/auth/signup`

**Request**:
```json
{
  "email": "admin@company.com",
  "password": "SecurePassword123!",
  "full_name": "John Doe",
  "company_name": "Acme Manufacturing"
}
```

**Response** (201 Created):
```json
{
  "admin": {
    "id": "abc123",
    "email": "admin@company.com",
    "full_name": "John Doe",
    "company_id": "comp_xyz789",
    "is_verified": false,
    "is_active": true,
    "created_at": "2026-03-03T10:00:00Z"
  },
  "company": {
    "company_id": "comp_xyz789",
    "company_name": "Acme Manufacturing",
    "is_active": true
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors**:
- `400 Bad Request`: Email already exists
- `422 Unprocessable Entity`: Validation error

---

#### 2. Admin Login

Login with email and password.

**Endpoint**: `POST /admin/auth/login`

**Request**:
```json
{
  "email": "admin@company.com",
  "password": "SecurePassword123!"
}
```

**Response** (200 OK):
```json
{
  "admin": {
    "id": "abc123",
    "email": "admin@company.com",
    "full_name": "John Doe",
    "company_id": "comp_xyz789",
    "is_verified": true,
    "is_active": true
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Errors**:
- `401 Unauthorized`: Invalid credentials
- `403 Forbidden`: Account not verified or inactive

---

#### 3. Request Email OTP

Request an OTP for email verification or password reset.

**Endpoint**: `POST /admin/auth/request-otp`

**Request**:
```json
{
  "email": "admin@company.com",
  "purpose": "verification"  // or "password_reset"
}
```

**Response** (200 OK):
```json
{
  "message": "OTP sent to admin@company.com",
  "expires_in": 600
}
```

---

#### 4. Verify Email OTP

Verify the OTP code sent via email.

**Endpoint**: `POST /admin/auth/verify-otp`

**Request**:
```json
{
  "email": "admin@company.com",
  "otp": "123456"
}
```

**Response** (200 OK):
```json
{
  "message": "Email verified successfully",
  "admin": {
    "id": "abc123",
    "email": "admin@company.com",
    "is_verified": true
  }
}
```

**Errors**:
- `400 Bad Request`: Invalid or expired OTP
- `404 Not Found`: Admin not found

---

#### 5. Refresh Access Token

Get a new access token using refresh token.

**Endpoint**: `POST /admin/auth/refresh`

**Headers**:
```
Authorization: Bearer <refresh_token>
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Errors**:
- `401 Unauthorized`: Invalid or expired refresh token

---

#### 6. Logout

Revoke the refresh token.

**Endpoint**: `POST /admin/auth/logout`

**Headers**:
```
Authorization: Bearer <refresh_token>
```

**Response** (200 OK):
```json
{
  "message": "Logged out successfully"
}
```

---

### Plant Management

#### 1. List All Plants

Get all plants for the admin's company.

**Endpoint**: `GET /admin/plants`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Query Parameters**:
- `is_active` (optional): Filter by active status (true/false)
- `limit` (optional): Number of results (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Response** (200 OK):
```json
{
  "plants": [
    {
      "plant_id": "plant_123",
      "plant_name": "Detroit Plant",
      "location": "Detroit, MI",
      "is_active": true,
      "created_at": "2026-01-15T10:00:00Z",
      "updated_at": "2026-03-01T14:30:00Z"
    },
    {
      "plant_id": "plant_456",
      "plant_name": "Chicago Plant",
      "location": "Chicago, IL",
      "is_active": true,
      "created_at": "2026-02-01T09:00:00Z",
      "updated_at": "2026-02-01T09:00:00Z"
    }
  ],
  "total": 2
}
```

---

#### 2. Create Plant

Create a new plant for the company.

**Endpoint**: `POST /admin/plants`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Request**:
```json
{
  "plant_name": "Austin Plant",
  "location": "Austin, TX"
}
```

**Response** (201 Created):
```json
{
  "plant_id": "plant_789",
  "plant_name": "Austin Plant",
  "location": "Austin, TX",
  "is_active": true,
  "created_at": "2026-03-03T10:00:00Z",
  "updated_at": "2026-03-03T10:00:00Z"
}
```

---

#### 3. Get Plant Details

Get details of a specific plant.

**Endpoint**: `GET /admin/plants/{plant_id}`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "plant_id": "plant_123",
  "plant_name": "Detroit Plant",
  "location": "Detroit, MI",
  "is_active": true,
  "created_at": "2026-01-15T10:00:00Z",
  "updated_at": "2026-03-01T14:30:00Z",
  "production_lines": [
    {
      "line_id": "line_1",
      "line_name": "Assembly Line 1",
      "is_active": true
    }
  ],
  "user_count": 25,
  "station_count": 12
}
```

**Errors**:
- `404 Not Found`: Plant not found

---

#### 4. Update Plant

Update plant details.

**Endpoint**: `PUT /admin/plants/{plant_id}`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Request**:
```json
{
  "plant_name": "Detroit Manufacturing Plant",
  "location": "Detroit, MI 48201",
  "is_active": true
}
```

**Response** (200 OK):
```json
{
  "plant_id": "plant_123",
  "plant_name": "Detroit Manufacturing Plant",
  "location": "Detroit, MI 48201",
  "is_active": true,
  "updated_at": "2026-03-03T10:30:00Z"
}
```

---

#### 5. Delete Plant

Soft delete a plant (sets is_active to false).

**Endpoint**: `DELETE /admin/plants/{plant_id}`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (204 No Content)

---

### User Management

#### 1. List All Users

Get all users (plant workers) in the company.

**Endpoint**: `GET /admin/users`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Query Parameters**:
- `plant_id` (optional): Filter by plant
- `is_active` (optional): Filter by active status
- `search` (optional): Search by name or phone
- `limit` (optional): Results per page (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Response** (200 OK):
```json
{
  "users": [
    {
      "user_id": "user_123",
      "phone_number": "+15551234567",
      "full_name": "Jane Smith",
      "email": "jane@acme.com",
      "is_active": true,
      "phone_verified": true,
      "last_login": "2026-03-03T08:00:00Z",
      "plants": [
        {
          "plant_id": "plant_123",
          "plant_name": "Detroit Plant",
          "role": "operator"
        }
      ]
    }
  ],
  "total": 25
}
```

---

#### 2. Invite New User

Invite a new user to join a plant.

**Endpoint**: `POST /admin/users`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Request**:
```json
{
  "phone_number": "+15559876543",
  "full_name": "Bob Johnson",
  "email": "bob@acme.com",
  "plant_id": "plant_123",
  "role": "operator"  // operator | manager | admin
}
```

**Response** (201 Created):
```json
{
  "user_id": "user_456",
  "phone_number": "+15559876543",
  "full_name": "Bob Johnson",
  "email": "bob@acme.com",
  "is_active": true,
  "phone_verified": false,
  "membership": {
    "plant_id": "plant_123",
    "role": "operator"
  },
  "invitation_sent": true
}
```

---

#### 3. Get User Details

Get details of a specific user.

**Endpoint**: `GET /admin/users/{user_id}`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "user_id": "user_123",
  "phone_number": "+15551234567",
  "full_name": "Jane Smith",
  "email": "jane@acme.com",
  "is_active": true,
  "phone_verified": true,
  "last_login": "2026-03-03T08:00:00Z",
  "created_at": "2026-01-20T10:00:00Z",
  "plants": [
    {
      "plant_id": "plant_123",
      "plant_name": "Detroit Plant",
      "role": "operator",
      "joined_at": "2026-01-20T10:00:00Z"
    }
  ],
  "recent_samples": 15,
  "recent_measurements": 45
}
```

---

#### 4. Update User

Update user information.

**Endpoint**: `PUT /admin/users/{user_id}`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Request**:
```json
{
  "full_name": "Jane Smith-Johnson",
  "email": "jane.johnson@acme.com",
  "is_active": true
}
```

**Response** (200 OK):
```json
{
  "user_id": "user_123",
  "full_name": "Jane Smith-Johnson",
  "email": "jane.johnson@acme.com",
  "updated_at": "2026-03-03T10:45:00Z"
}
```

---

#### 5. Remove User

Remove a user from the company (soft delete).

**Endpoint**: `DELETE /admin/users/{user_id}`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (204 No Content)

---

## Payment API (Admin)

### Add Credit Card

Add a credit card to the company account using raw card details from the payment form.

**Endpoint**: `POST /admin/payment/add-credit-card`

**Authentication**: Required (Admin Bearer token)

**Request**:
```json
{
  "card_number": "4242424242424242",
  "exp_month": 12,
  "exp_year": 2028,
  "cvc": "123",
  "name_on_card": "John Doe",
  "zip_code": "12345",
  "country": "US"
}
```

**Field Specifications**:
- `card_number`: 13-19 digits (spaces and dashes will be removed)
- `exp_month`: 1-12 (expiration month)
- `exp_year`: 4-digit year (e.g., 2028)
- `cvc`: 3-4 digit security code
- `name_on_card`: Cardholder name as it appears on card
- `zip_code`: Billing postal/zip code (3-10 characters)
- `country`: 2-letter ISO country code (e.g., US, CA, GB)

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Credit card added successfully",
  "payment_method_id": "pm_1234567890abcdef"
}
```

**Errors**:
- `400 Bad Request`: Card declined or invalid card details
- `401 Unauthorized`: Missing or invalid token
- `404 Not Found`: Company not found
- `500 Internal Server Error`: Server error

**Example Error Responses**:
```json
{
  "detail": "Card declined: Your card was declined"
}
```

```json
{
  "detail": "Invalid card details: The card number is invalid"
}
```

**Test Cards** (Stripe):
- `4242424242424242` - Visa (Success)
- `5555555555554444` - Mastercard (Success)
- `378282246310005` - American Express (Success)
- `4000000000000002` - Card declined

---

### Get Payment Methods

List all saved payment methods for the company.

**Endpoint**: `GET /admin/payment/methods`

**Authentication**: Required (Admin Bearer token)

**Response** (200 OK):
```json
{
  "payment_methods": [
    {
      "id": "pm_1234567890",
      "brand": "visa",
      "last4": "4242",
      "exp_month": 12,
      "exp_year": 2028,
      "cardholder_name": "John Doe",
      "billing_postal_code": "12345",
      "billing_country": "US",
      "is_default": true
    }
  ]
}
```

---

### Create Payment Intent

Create a payment intent for one-time purchases.

**Endpoint**: `POST /admin/payment/create-payment-intent`

**Authentication**: Required (Admin Bearer token)

**Request**:
```json
{
  "amount": 5000,
  "currency": "usd",
  "description": "Premium subscription - Annual",
  "product_id": "prod_premium_annual"
}
```

**Field Specifications**:
- `amount`: Amount in cents (5000 = $50.00)
- `currency`: 3-letter ISO currency code (default: "usd")
- `description`: Optional payment description
- `product_id`: Optional product identifier

**Response** (200 OK):
```json
{
  "success": true,
  "client_secret": "pi_1234567890_secret_abcdefghij",
  "payment_intent_id": "pi_1234567890"
}
```

---

### Charge Saved Card

Charge the company's default payment method.

**Endpoint**: `POST /admin/payment/charge-saved-card`

**Authentication**: Required (Admin Bearer token)

**Request**:
```json
{
  "amount": 2999,
  "currency": "usd",
  "description": "Monthly subscription"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "payment_intent_id": "pi_1234567890",
  "status": "succeeded"
}
```

**Errors**:
- `400 Bad Request`: No payment method on file or charge failed
- `401 Unauthorized`: Invalid token

---

### Create Subscription

Create a recurring subscription using Stripe.

**Endpoint**: `POST /admin/payment/create-subscription`

**Authentication**: Required (Admin Bearer token)

**Request**:
```json
{
  "price_id": "price_1234567890abcdef"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "subscription_id": "sub_1234567890",
  "client_secret": "seti_1234567890_secret_abcdefghij"
}
```

---

## User API

### Auth Endpoints

#### 1. Request SMS OTP

Request an OTP code via SMS.

**Endpoint**: `POST /users/auth/request-otp`

**Request**:
```json
{
  "phone_number": "+15551234567"
}
```

**Response** (200 OK):
```json
{
  "message": "OTP sent to +15551234567",
  "expires_in": 600
}
```

**Notes**:
- System searches all tenant schemas to find which company the phone belongs to
- If phone not found, returns generic success (security best practice)

---

#### 2. Verify OTP & Login

Verify OTP and login.

**Endpoint**: `POST /users/auth/verify-otp`

**Request**:
```json
{
  "phone_number": "+15551234567",
  "otp": "123456"
}
```

**Response** (200 OK):
```json
{
  "user": {
    "user_id": "user_123",
    "phone_number": "+15551234567",
    "full_name": "Jane Smith",
    "email": "jane@acme.com",
    "company_id": "comp_xyz789",
    "company_name": "Acme Manufacturing"
  },
  "plants": [
    {
      "plant_id": "plant_123",
      "plant_name": "Detroit Plant",
      "role": "operator"
    }
  ],
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "has_pin": false
}
```

**Errors**:
- `400 Bad Request`: Invalid or expired OTP
- `404 Not Found`: Phone number not found

---

#### 3. Set PIN

Set a 4-digit PIN for faster login.

**Endpoint**: `POST /users/auth/set-pin`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Request**:
```json
{
  "pin": "1234"
}
```

**Response** (200 OK):
```json
{
  "message": "PIN set successfully"
}
```

**Validation**:
- PIN must be exactly 4 digits
- Cannot be sequential (1234, 4321)
- Cannot be repeated (1111, 2222)

---

#### 4. Login with PIN

Quick login using phone + PIN.

**Endpoint**: `POST /users/auth/login-with-pin`

**Request**:
```json
{
  "phone_number": "+15551234567",
  "pin": "1234"
}
```

**Response** (200 OK):
```json
{
  "user": {
    "user_id": "user_123",
    "phone_number": "+15551234567",
    "full_name": "Jane Smith",
    "company_id": "comp_xyz789"
  },
  "plants": [...],
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors**:
- `401 Unauthorized`: Invalid PIN
- `404 Not Found`: Phone number not found

---

#### 5. Refresh Token

Get a new access token.

**Endpoint**: `POST /users/auth/refresh`

**Headers**:
```
Authorization: Bearer <refresh_token>
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

## Error Responses

All error responses follow this structure:

```json
{
  "detail": "Error message"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful deletion) |
| 400 | Bad Request (validation error or invalid input) |
| 401 | Unauthorized (missing or invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found (resource doesn't exist) |
| 422 | Unprocessable Entity (Pydantic validation error) |
| 500 | Internal Server Error |

### Example Error Response

```json
{
  "detail": "email: Invalid email format"
}
```

Or for multiple validation errors:

```json
{
  "detail": [
    "email: Invalid email format",
    "password: Must be at least 8 characters"
  ]
}
```

---

## Rate Limiting

**Current Status**: Not implemented

**Future Implementation**:
- Admin API: 100 requests/minute per company
- User API: 60 requests/minute per user
- Auth endpoints: 10 requests/minute per IP

---

## Pagination

List endpoints support pagination:

**Query Parameters**:
- `limit`: Number of results per page (default: 50, max: 100)
- `offset`: Number of results to skip (default: 0)

**Example**:
```
GET /admin/users?limit=20&offset=40
```

**Response**:
```json
{
  "users": [...],
  "total": 125,
  "limit": 20,
  "offset": 40,
  "has_more": true
}
```

---

## Webhooks (Future)

Planned webhook events:

- `company.created`
- `admin.verified`
- `user.invited`
- `plant.created`
- `subscription.created`
- `subscription.updated`
- `subscription.canceled`
- `payment.succeeded`
- `payment.failed`

---

## SDK Examples

### Python

```python
import requests

BASE_URL = "https://api.pocketwatch.ai"

# Login
response = requests.post(f"{BASE_URL}/admin/auth/login", json={
    "email": "admin@company.com",
    "password": "password123"
})
data = response.json()
access_token = data["access_token"]

# Get plants
headers = {"Authorization": f"Bearer {access_token}"}
plants = requests.get(f"{BASE_URL}/admin/plants", headers=headers).json()
```

### JavaScript/TypeScript

```typescript
const BASE_URL = 'https://api.pocketwatch.ai';

// Login
const loginResponse = await fetch(`${BASE_URL}/admin/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'admin@company.com',
    password: 'password123'
  })
});
const { access_token } = await loginResponse.json();

// Get plants
const plantsResponse = await fetch(`${BASE_URL}/admin/plants`, {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
const plants = await plantsResponse.json();
```

### cURL

```bash
# Login
TOKEN=$(curl -X POST https://api.pocketwatch.ai/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@company.com","password":"password123"}' \
  | jq -r '.access_token')

# Get plants
curl https://api.pocketwatch.ai/admin/plants \
  -H "Authorization: Bearer $TOKEN"
```

---

## Testing Endpoints

### Postman Collection

Import this collection into Postman:

[Download Postman Collection](./postman_collection.json) *(to be created)*

### Example Test Script

```python
import pytest
import requests

BASE_URL = "http://localhost:8000"

def test_health():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_admin_signup():
    response = requests.post(f"{BASE_URL}/admin/auth/signup", json={
        "email": f"test_{uuid.uuid4()}@example.com",
        "password": "SecurePass123!",
        "full_name": "Test Admin",
        "company_name": "Test Company"
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "company" in data
```

---

**Last Updated**: March 3, 2026
**API Version**: 2.0.0
