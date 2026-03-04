# Payment System Documentation 💳

## Overview

PocketWatch uses a **secure, PCI-compliant payment system** powered by Stripe for company-level billing. All payment functionality is restricted to authenticated company administrators.

---

## 🔒 Security & Compliance

### ✅ Legal & Ethical Standards

1. **PCI-DSS Compliance**
   - ✅ Card data tokenized on frontend using Stripe SDK
   - ✅ **No raw card numbers ever reach our servers**
   - ✅ Only store Stripe payment method IDs (tokens) and last 4 digits
   - ✅ CVV/CVC never stored anywhere

2. **Data Privacy (GDPR/CCPA)**
   - ✅ Company-level billing (not individual users)
   - ✅ Proper access control - admins only access their company's data
   - ✅ Cascade deletion when company is removed
   - ✅ Audit trails with timestamps

3. **Authentication & Authorization**
   - ✅ JWT bearer token authentication required
   - ✅ Company ownership verification on every request
   - ✅ Active admin account verification

4. **Data Security**
   - ⚠️ **HTTPS REQUIRED** - Must use SSL/TLS in production
   - ✅ Stripe API keys stored in environment variables
   - ✅ No sensitive data in logs or error messages
   - ✅ SQL injection protection via SQLAlchemy ORM

---

## 📋 Architecture

### Data Model

```
companies
├── stripe_customer_id (Stripe Customer ID)
└── payment_methods (1:many)
    ├── stripe_payment_method_id (Token)
    ├── brand (visa, mastercard, etc.)
    ├── last4 (Last 4 digits only)
    ├── exp_month
    ├── exp_year
    ├── cardholder_name
    ├── billing_postal_code
    ├── billing_country
    ├── is_default
    └── timestamps
```

### Payment Flow

```
React Native App                  Backend API                    Stripe
      |                                |                             |
      | 1. User enters card details    |                             |
      |---------------------------->   |                             |
      | 2. Stripe SDK tokenizes card   |                             |
      |-------------------------------------------------------------->|
      |                                | 3. Receive payment_method_id |
      |<--------------------------------------------------------------|
      | 4. POST /admin/payment/save-card with token                  |
      |---------------------------->   |                             |
      |                                | 5. Attach to Stripe Customer|
      |                                |---------------------------->|
      |                                | 6. Save to database         |
      |                                | 7. Return success           |
      |<----------------------------   |                             |
```

---

## 🌐 API Endpoints

### Base URL
```
Production: https://your-domain.com/admin/payment
Development: http://localhost:8000/admin/payment
```

### Authentication
All endpoints require Bearer token authentication:
```http
Authorization: Bearer <access_token>
```

---

### 1. Save Payment Method

**POST** `/admin/payment/save-card`

Save a tokenized payment method (created by frontend Stripe SDK) to the company's account.

#### Request Body
```json
{
  "payment_method_id": "pm_1234567890abcdef",
  "billing_details": {
    "set_as_default": true
  }
}
```

#### Response (200 OK)
```json
{
  "success": true,
  "message": "Card saved successfully",
  "payment_method_id": "pm_1234567890abcdef"
}
```

#### Error Responses
- **400 Bad Request**: Invalid payment method or Stripe error
- **401 Unauthorized**: Missing or invalid token
- **403 Forbidden**: Inactive admin account
- **404 Not Found**: Company not found
- **500 Internal Server Error**: Database or server error

---

### 2. List Payment Methods

**GET** `/admin/payment/payment-methods`

Retrieve all saved payment methods for the authenticated admin's company.

#### Response (200 OK)
```json
[
  {
    "id": "pm_1234567890abcdef",
    "brand": "visa",
    "last4": "4242",
    "exp_month": 12,
    "exp_year": 2027,
    "cardholder_name": "John Doe",
    "billing_postal_code": "12345",
    "billing_country": "US",
    "is_default": true
  },
  {
    "id": "pm_0987654321fedcba",
    "brand": "mastercard",
    "last4": "5555",
    "exp_month": 6,
    "exp_year": 2028,
    "cardholder_name": "Jane Smith",
    "billing_postal_code": "67890",
    "billing_country": "US",
    "is_default": false
  }
]
```

#### Notes
- Results sorted by default card first, then by creation date (newest first)
- Returns empty array `[]` if no payment methods exist

---

### 3. Delete Payment Method

**DELETE** `/admin/payment/payment-methods/{payment_method_id}`

Remove a payment method from the company's account.

#### Path Parameters
- `payment_method_id`: Stripe payment method ID (e.g., `pm_1234567890abcdef`)

#### Response (200 OK)
```json
{
  "success": true,
  "message": "Payment method removed"
}
```

#### Error Responses
- **404 Not Found**: Payment method doesn't exist or doesn't belong to company
- **400 Bad Request**: Stripe API error
- **500 Internal Server Error**: Failed to delete

---

## 📱 Frontend Integration (React Native)

### Step 1: Install Stripe SDK
```bash
npm install @stripe/stripe-react-native
```

### Step 2: Initialize Stripe
```typescript
import { StripeProvider, useStripe } from '@stripe/stripe-react-native';

const STRIPE_PUBLISHABLE_KEY = 'pk_test_...';

export default function App() {
  return (
    <StripeProvider publishableKey={STRIPE_PUBLISHABLE_KEY}>
      <PaymentScreen />
    </StripeProvider>
  );
}
```

### Step 3: Collect Card Details & Create Token
```typescript
import { CardField, useStripe } from '@stripe/stripe-react-native';

function PaymentScreen() {
  const { createPaymentMethod } = useStripe();
  const [loading, setLoading] = useState(false);

  const handleSaveCard = async (cardDetails) => {
    try {
      setLoading(true);

      // Create payment method using Stripe SDK (tokenizes card)
      const { paymentMethod, error } = await createPaymentMethod({
        paymentMethodType: 'Card',
        card: cardDetails,
        billingDetails: {
          name: cardholderName,
          address: {
            postalCode: zipCode,
            country: countryCode,
          },
        },
      });

      if (error) {
        console.error('Stripe error:', error);
        return;
      }

      // Send token to backend
      const response = await fetch('https://api.your-domain.com/admin/payment/save-card', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          payment_method_id: paymentMethod.id,
          billing_details: { set_as_default: true },
        }),
      });

      const result = await response.json();
      
      if (result.success) {
        console.log('Card saved successfully!');
      }
    } catch (err) {
      console.error('Error saving card:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View>
      <CardField
        postalCodeEnabled={true}
        onCardChange={(cardDetails) => {
          if (cardDetails.complete) {
            handleSaveCard(cardDetails);
          }
        }}
      />
    </View>
  );
}
```

### Step 4: Display Saved Cards
```typescript
const fetchPaymentMethods = async () => {
  const response = await fetch('https://api.your-domain.com/admin/payment/payment-methods', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });
  
  const cards = await response.json();
  setPaymentMethods(cards);
};
```

### Step 5: Delete Card
```typescript
const deleteCard = async (paymentMethodId: string) => {
  await fetch(`https://api.your-domain.com/admin/payment/payment-methods/${paymentMethodId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });
};
```

---

## 🔧 Environment Variables

Required in `.env` file:

```bash
# Stripe API Keys (get from https://dashboard.stripe.com/apikeys)
STRIPE_SECRET_KEY=sk_test_51AbCd...  # Backend only
STRIPE_PUBLISHABLE_KEY=pk_test_51XyZ...  # Frontend only

# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname

# JWT Authentication
JWT_SECRET=your-secure-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
```

### ⚠️ Security Notes
- **NEVER** commit `.env` to version control
- Use different keys for test/production environments
- Rotate keys periodically
- Use Stripe test keys (prefix `sk_test_`, `pk_test_`) during development

---

## 🧪 Testing

### Test Cards (Stripe Test Mode)

| Card Number           | Brand      | Result          |
|-----------------------|------------|-----------------|
| 4242 4242 4242 4242  | Visa       | Success         |
| 5555 5555 5555 4444  | Mastercard | Success         |
| 4000 0000 0000 0002  | Visa       | Card declined   |
| 4000 0000 0000 9995  | Visa       | Insufficient funds |

- **Expiry**: Any future date (e.g., 12/27)
- **CVV**: Any 3 digits (e.g., 123)
- **ZIP**: Any valid postal code (e.g., 12345)

### Manual Testing Flow

1. **Save Card**
   ```bash
   curl -X POST http://localhost:8000/admin/payment/save-card \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "payment_method_id": "pm_test_1234567890abcdef",
       "billing_details": {"set_as_default": true}
     }'
   ```

2. **List Cards**
   ```bash
   curl -X GET http://localhost:8000/admin/payment/payment-methods \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. **Delete Card**
   ```bash
   curl -X DELETE http://localhost:8000/admin/payment/payment-methods/pm_test_1234567890abcdef \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

---

## 🚨 Error Handling

### Common Errors

#### 1. Card Declined
```json
{
  "detail": "Your card was declined."
}
```
**Solution**: Try different test card or check with card issuer

#### 2. Invalid Payment Method
```json
{
  "detail": "No such payment_method: 'pm_invalid'"
}
```
**Solution**: Verify payment method ID from Stripe SDK

#### 3. Company Not Found
```json
{
  "detail": "Company not found"
}
```
**Solution**: Ensure admin is associated with a company

#### 4. Unauthorized
```json
{
  "detail": "Invalid or expired token"
}
```
**Solution**: Refresh access token or re-authenticate

---

## 📊 Database Schema

### Payment Methods Table
```sql
CREATE TABLE payment_methods (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id VARCHAR(36) NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    stripe_payment_method_id VARCHAR(255) UNIQUE NOT NULL,
    brand VARCHAR(50),
    last4 VARCHAR(4),
    exp_month INTEGER,
    exp_year INTEGER,
    cardholder_name VARCHAR(255),
    billing_postal_code VARCHAR(20),
    billing_country VARCHAR(2),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_payment_methods_company_id ON payment_methods(company_id);
CREATE INDEX idx_payment_methods_stripe_id ON payment_methods(stripe_payment_method_id);
```

---

## 🔄 Migration Guide

### Applying Database Migrations

```bash
# Navigate to backend directory
cd backend

# Apply migrations
alembic upgrade head

# Verify migration
alembic current
```

### Migration Files
- `add_payment_tables.py` - Creates payment_methods, transactions, subscriptions tables
- `add_billing_details_to_payment_methods.py` - Adds cardholder_name, billing_postal_code, billing_country

---

## 🛡️ Best Practices

### Security
1. ✅ Always use HTTPS in production
2. ✅ Validate all inputs on backend
3. ✅ Never log sensitive payment data
4. ✅ Implement rate limiting for payment endpoints
5. ✅ Use environment variables for API keys
6. ✅ Rotate Stripe API keys periodically

### Development
1. ✅ Use Stripe test mode during development
2. ✅ Test card decline scenarios
3. ✅ Handle network errors gracefully
4. ✅ Show user-friendly error messages
5. ✅ Implement retry logic for failed requests

### Production
1. ✅ Use Stripe production API keys
2. ✅ Set up Stripe webhook endpoints (if adding charges/subscriptions)
3. ✅ Monitor Stripe dashboard for issues
4. ✅ Implement logging and alerting
5. ✅ Have rollback plan for schema changes

---

## 📞 Support & Resources

### Official Documentation
- **Stripe API**: https://stripe.com/docs/api
- **Stripe React Native**: https://stripe.com/docs/payments/accept-a-payment?platform=react-native
- **FastAPI**: https://fastapi.tiangolo.com/

### Troubleshooting
- Check Stripe Dashboard logs: https://dashboard.stripe.com/test/logs
- Review API errors in backend logs
- Verify environment variables are set correctly
- Ensure database migrations are up to date

---

## 📝 Changelog

### v1.0.0 (March 2026)
- ✅ Initial payment system implementation
- ✅ Company-level billing
- ✅ Save, list, and delete payment methods
- ✅ PCI-compliant tokenization via Stripe SDK
- ✅ JWT authentication for all endpoints
- ✅ Frontend integration guide

---

**Last Updated**: March 3, 2026  
**Maintained By**: PocketWatch Development Team  
**License**: Proprietary
