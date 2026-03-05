# Subscription Plans API Documentation 📋

## Overview

PocketWatch offers two subscription tiers for companies: **Free Plan** and **Premium Plan**. The plan system controls access to features and limits the number of stations a company can use.

---

## 📊 Available Plans

### Free Plan (FREE)
**Price**: $0/month

**Features**:
- ✅ Access for **1 station only**
- ✅ Realtime dashboard views of process
- ✅ 24/7 Access to Virtual Coach
- ✅ Continuous SPC Monitoring
- ❌ Full administrative control (Premium only)
- ❌ Unlimited data entry (Premium only)

**Use Case**: Perfect for experiencing PocketWatch process control with a single station.

---

### Premium Plan (PREMIUM)
**Price**: $99.00 per station/month

**Features**:
- ✅ **Unlimited stations**
- ✅ Full administrative control
- ✅ Realtime dashboard views of process
- ✅ 24/7 Access to Virtual Coach
- ✅ Continuous SPC Monitoring
- ✅ Unlimited data entry

**Use Case**: Full control over multiple stations and users at your location.

---

## 🌐 API Endpoints

### Base URL
```
Production: https://your-domain.com/admin/plans
Development: http://localhost:8000/admin/plans
```

### Authentication
All endpoints require Bearer token authentication:
```http
Authorization: Bearer <access_token>
```

---

## 📍 Endpoints

### 1. Get Available Plans

**GET** `/admin/plans/available`

Retrieve all available subscription plans with features and pricing.

#### Response (200 OK)
```json
{
  "plans": [
    {
      "plan_type": "free",
      "name": "Free Plan",
      "description": "Access to all features for one station to experience the power of PocketWatch process control.",
      "price_per_station": 0,
      "features": {
        "stations_limit": 1,
        "realtime_dashboard": true,
        "virtual_coach_access": true,
        "spc_monitoring": true,
        "full_admin_control": false,
        "unlimited_data_entry": false
      }
    },
    {
      "plan_type": "premium",
      "name": "Premium Plan",
      "description": "Unlock full administrative control over the number of stations and users at your location",
      "price_per_station": 9900,
      "features": {
        "stations_limit": null,
        "realtime_dashboard": true,
        "virtual_coach_access": true,
        "spc_monitoring": true,
        "full_admin_control": true,
        "unlimited_data_entry": true
      }
    }
  ]
}
```

---

### 2. Get Current Subscription

**GET** `/admin/plans/current`

Get the company's current subscription details.

#### Response (200 OK)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "company_id": "company-123",
  "plan_type": "free",
  "stations_count": 1,
  "monthly_cost": 0,
  "monthly_cost_usd": "$0.00",
  "is_active": true,
  "features": {
    "stations_limit": 1,
    "realtime_dashboard": true,
    "virtual_coach_access": true,
    "spc_monitoring": true,
    "full_admin_control": false,
    "unlimited_data_entry": false
  },
  "plan_started_at": "2026-03-04T10:30:00Z",
  "created_at": "2026-03-04T10:30:00Z"
}
```

#### Notes
- Automatically creates FREE plan subscription if none exists
- Returns current active subscription details

---

### 3. Select/Change Plan

**POST** `/admin/plans/select`

Select or change the company's subscription plan.

#### Request Body
```json
{
  "plan_type": "premium",
  "stations_count": 3
}
```

**Parameters**:
- `plan_type` (required): `"free"` or `"premium"`
- `stations_count` (required): Number of stations (ignored for free plan, set to 1)

#### Response (200 OK)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "company_id": "company-123",
  "plan_type": "premium",
  "stations_count": 3,
  "monthly_cost": 29700,
  "monthly_cost_usd": "$297.00",
  "is_active": true,
  "features": {
    "stations_limit": null,
    "realtime_dashboard": true,
    "virtual_coach_access": true,
    "spc_monitoring": true,
    "full_admin_control": true,
    "unlimited_data_entry": true
  },
  "plan_started_at": "2026-03-04T11:00:00Z",
  "created_at": "2026-03-04T10:30:00Z"
}
```

#### Business Logic

**Upgrading to Premium**:
- ✅ Requires payment method on file
- ✅ Can specify number of stations (1+)
- ✅ Cost calculated as: `$99.00 × stations_count`

**Downgrading to Free**:
- ✅ Automatically sets to 1 station
- ⚠️ Cannot downgrade if currently using >1 station
- ✅ Must reduce stations first

#### Error Responses

**400 Bad Request** - No payment method for premium:
```json
{
  "detail": "Premium plan requires a payment method. Please add a payment method first."
}
```

**400 Bad Request** - Cannot downgrade with multiple stations:
```json
{
  "detail": "Cannot downgrade to free plan with more than 1 station. Please reduce stations first."
}
```

---

### 4. Update Station Count

**PUT** `/admin/plans/stations`

Update the number of stations (Premium plan only).

#### Request Body
```json
{
  "stations_count": 5
}
```

#### Response (200 OK)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "company_id": "company-123",
  "plan_type": "premium",
  "stations_count": 5,
  "monthly_cost": 49500,
  "monthly_cost_usd": "$495.00",
  "is_active": true,
  "features": { ... },
  "plan_started_at": "2026-03-04T11:00:00Z",
  "created_at": "2026-03-04T10:30:00Z"
}
```

#### Error Responses

**403 Forbidden** - Not on premium plan:
```json
{
  "detail": "Station count can only be modified on Premium plan. Please upgrade first."
}
```

---

### 5. Check Feature Access

**GET** `/admin/plans/features/{feature_name}`

Check if the company's current plan has access to a specific feature.

#### Path Parameters
- `feature_name`: One of:
  - `realtime_dashboard`
  - `virtual_coach_access`
  - `spc_monitoring`
  - `full_admin_control` ← Premium only
  - `unlimited_data_entry` ← Premium only

#### Example Request
```http
GET /admin/plans/features/full_admin_control
Authorization: Bearer <token>
```

#### Response (200 OK) - Has Access
```json
{
  "has_access": true,
  "feature": "full_admin_control",
  "current_plan": "premium",
  "message": null
}
```

#### Response (200 OK) - No Access
```json
{
  "has_access": false,
  "feature": "full_admin_control",
  "current_plan": "free",
  "message": "This feature requires an upgrade to Premium plan."
}
```

---

## 🔐 Feature Access Control

### Using Feature Gates in Your Code

The system provides `FeatureGate` utilities for enforcing feature access in other endpoints.

#### Example 1: Require Admin Control Feature
```python
from app.utils.feature_gate import require_admin_control

@router.post("/admin-only-action")
async def admin_action(
    admin: Admin = Depends(get_current_admin),
    _: None = Depends(require_admin_control)
):
    # Only accessible to Premium plan users
    return {"message": "Admin action performed"}
```

#### Example 2: Require Unlimited Data Entry
```python
from app.utils.feature_gate import require_unlimited_data

@router.post("/bulk-data-entry")
async def bulk_entry(
    data: list[DataEntry],
    admin: Admin = Depends(get_current_admin),
    _: None = Depends(require_unlimited_data)
):
    # Only accessible to Premium plan users
    return {"entries": len(data)}
```

#### Example 3: Check Station Quota
```python
from app.utils.feature_gate import check_station_quota

@router.post("/add-station")
async def add_station(
    station_data: StationCreate,
    admin: Admin = Depends(get_current_admin),
    limits: dict = Depends(check_station_quota)
):
    # Automatically checks if company can add more stations
    # Returns 403 if limit reached on Free plan
    return {"station": "created", "limits": limits}
```

#### Manual Feature Check
```python
from app.utils.feature_gate import FeatureGate

def my_endpoint(admin: Admin, db: Session):
    # Manual check
    if FeatureGate.check_feature_access(admin, FeatureGate.ADMIN_CONTROL, db):
        # Has access
        pass
    else:
        # No access - handle accordingly
        raise HTTPException(403, detail="Premium required")
```

---

## 📱 Frontend Integration Flow

### Step 1: Display Pricing Screen

Fetch available plans on pricing screen load:

```typescript
const fetchPlans = async () => {
  const response = await fetch('https://api.your-domain.com/admin/plans/available', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });
  
  const data = await response.json();
  setPlans(data.plans);
};
```

### Step 2: Select Free Plan

When user clicks "Select this plan" on Free Plan:

```typescript
const selectFreePlan = async () => {
  const response = await fetch('https://api.your-domain.com/admin/plans/select', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      plan_type: 'free',
      stations_count: 1,
    }),
  });
  
  const subscription = await response.json();
  console.log('Activated Free Plan:', subscription);
  
  // Navigate to dashboard
  navigation.navigate('Dashboard');
};
```

### Step 3: Select Premium Plan

When user clicks "Select this plan" on Premium Plan:

```typescript
const selectPremiumPlan = async (stationsCount: number) => {
  try {
    const response = await fetch('https://api.your-domain.com/admin/plans/select', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        plan_type: 'premium',
        stations_count: stationsCount,
      }),
    });
    
    if (response.status === 400) {
      const error = await response.json();
      if (error.detail.includes('payment method')) {
        // No payment method - redirect to add payment
        navigation.navigate('AddPaymentMethod', {
          returnTo: 'Pricing',
          planType: 'premium',
          stations: stationsCount,
        });
        return;
      }
    }
    
    const subscription = await response.json();
    console.log('Activated Premium Plan:', subscription);
    
    // Navigate to dashboard
    navigation.navigate('Dashboard');
  } catch (err) {
    console.error('Error selecting premium plan:', err);
  }
};
```

### Step 4: Check Current Plan

Display current plan on settings/profile screen:

```typescript
const fetchCurrentPlan = async () => {
  const response = await fetch('https://api.your-domain.com/admin/plans/current', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });
  
  const subscription = await response.json();
  setCurrentPlan(subscription.plan_type);
  setStationsCount(subscription.stations_count);
  setMonthlyCost(subscription.monthly_cost_usd);
};
```

### Step 5: Feature Gating in Frontend

Lock features based on plan:

```typescript
const canAccessFeature = async (feature: string): Promise<boolean> => {
  const response = await fetch(
    `https://api.your-domain.com/admin/plans/features/${feature}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    }
  );
  
  const result = await response.json();
  return result.has_access;
};

// Usage
const handleAdminAction = async () => {
  const hasAccess = await canAccessFeature('full_admin_control');
  
  if (!hasAccess) {
    // Show upgrade prompt
    Alert.alert(
      'Premium Required',
      'This feature requires Premium plan. Upgrade now?',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Upgrade', onPress: () => navigation.navigate('Pricing') }
      ]
    );
    return;
  }
  
  // Proceed with admin action
};
```

---

## 🗄️ Database Schema

### company_subscriptions Table

```sql
CREATE TABLE company_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id VARCHAR(36) NOT NULL UNIQUE REFERENCES companies(company_id) ON DELETE CASCADE,
    plan_type plantype NOT NULL DEFAULT 'free',
    stations_count INTEGER NOT NULL DEFAULT 1,
    monthly_cost INTEGER DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    trial_ends_at TIMESTAMP,
    plan_started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_company_subscriptions_company_id ON company_subscriptions(company_id);
CREATE INDEX idx_company_subscriptions_plan_type ON company_subscriptions(plan_type);
CREATE INDEX idx_company_subscriptions_is_active ON company_subscriptions(is_active);
```

### Plan Type Enum
```sql
CREATE TYPE plantype AS ENUM ('free', 'premium');
```

---

## 🔄 Migration Guide

### Running the Migration

```bash
# Navigate to backend directory
cd backend

# Run migration to create company_subscriptions table
alembic upgrade head

# Verify migration
alembic current
```

### Migration Details
- **File**: `add_company_subscriptions.py`
- **Creates**: `company_subscriptions` table, `plantype` enum
- **Auto-provisions**: FREE plan for all existing companies
- **Dependencies**: Requires `add_billing_details_to_payment_methods` migration

---

## 💰 Billing Logic

### Cost Calculation

```python
# Free Plan
monthly_cost = $0

# Premium Plan
monthly_cost = $99.00 × stations_count

# Examples:
1 station  = $99.00/month
3 stations = $297.00/month
5 stations = $495.00/month
```

### Billing Cycle
- Monthly billing automatically calculated
- Pro-rated charges for mid-cycle upgrades (future enhancement)
- Payment processed via Stripe (integration with existing payment system)

---

## 🧪 Testing

### Test Scenarios

#### 1. Default Free Plan
```bash
# When company is created, gets FREE plan automatically
curl -X GET http://localhost:8000/admin/plans/current \
  -H "Authorization: Bearer TOKEN"
  
# Expected: plan_type=free, stations_count=1, monthly_cost=0
```

#### 2. Upgrade to Premium Without Payment
```bash
curl -X POST http://localhost:8000/admin/plans/select \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_type": "premium", "stations_count": 2}'
  
# Expected: 400 error - requires payment method
```

#### 3. Upgrade to Premium With Payment
```bash
# First add payment method, then:
curl -X POST http://localhost:8000/admin/plans/select \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_type": "premium", "stations_count": 3}'
  
# Expected: Success, monthly_cost=29700 ($297.00)
```

#### 4. Downgrade to Free
```bash
curl -X POST http://localhost:8000/admin/plans/select \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_type": "free", "stations_count": 1}'
  
# Expected: Success if stations_count<=1, error otherwise
```

#### 5. Check Feature Access
```bash
curl -X GET http://localhost:8000/admin/plans/features/full_admin_control \
  -H "Authorization: Bearer TOKEN"
  
# Expected: has_access=false for FREE, has_access=true for PREMIUM
```

---

## 🚨 Error Handling

### Common Errors

#### No Payment Method for Premium
```json
{
  "detail": "Premium plan requires a payment method. Please add a payment method first."
}
```
**Solution**: Redirect user to add payment method

#### Cannot Downgrade with Multiple Stations
```json
{
  "detail": "Cannot downgrade to free plan with more than 1 station. Please reduce stations first."
}
```
**Solution**: Show station management interface, reduce to 1 station

#### Feature Not Available
```json
{
  "detail": "Your current plan (free) does not have access to this feature. Please upgrade to Premium."
}
```
**Solution**: Show upgrade prompt with pricing details

---

## 📊 Feature Matrix

| Feature                          | FREE | PREMIUM |
|----------------------------------|------|---------|
| Realtime Dashboard               | ✅   | ✅      |
| 24/7 Virtual Coach               | ✅   | ✅      |
| Continuous SPC Monitoring        | ✅   | ✅      |
| Full Administrative Control      | ❌   | ✅      |
| Unlimited Data Entry             | ❌   | ✅      |
| Maximum Stations                 | 1    | ∞       |
| Monthly Cost                     | $0   | $99/station |

---

## 🔮 Future Enhancements

1. **Trial Periods**: 14-day free trial of Premium features
2. **Annual Billing**: Discount for annual subscriptions
3. **Usage Analytics**: Track feature usage per plan
4. **Custom Plans**: Enterprise plans with custom pricing
5. **Team Management**: User limits per plan
6. **API Rate Limits**: Different limits per plan tier

---

**Last Updated**: March 4, 2026  
**Version**: 1.0.0  
**Maintained By**: PocketWatch Development Team
