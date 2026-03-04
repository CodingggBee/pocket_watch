# User Setup API Documentation 👥

## Overview

The User Setup screen is the **final step** in the PocketWatch setup wizard. After configuring the plant, departments, production lines, and stations, the admin adds team members who will use the app.

---

## 📋 User Setup Flow

### What Happens on This Screen

1. **Add Team Members**: Admin adds users one by one
2. **Assign Roles**: Each user is either a Manager or Team Member
3. **Configure Access**: Optional offsite permission for remote access
4. **Collect Details**: Name, phone, email (optional), and shift assignment
5. **Generate PIN**: 4-digit PIN auto-generated for each user
6. **Send Welcome**: Automatic SMS/email with PIN and app download link
7. **Complete Setup**: After adding at least 1 user, setup is complete

---

## 🌐 API Endpoints

### Base URL
```
Production: https://your-domain.com/admin/setup
Development: http://localhost:8000/admin/setup
```

### Authentication
All endpoints require admin Bearer token authentication:
```http
Authorization: Bearer <admin_access_token>
```

---

## 📍 Endpoints

### 1. Get Shifts for Dropdown

**GET** `/admin/setup/shifts?plant_id={plant_id}`

Retrieve list of shifts for the shift selection dropdown.

#### Query Parameters
- `plant_id` (required): UUID of the plant (from Screen 1)

#### Response (200 OK)
```json
{
  "plant_id": "abc123-plant-id",
  "shifts": [
    {
      "shift_id": "shift-uuid-1",
      "shift_name": "Morning Shift",
      "start_time": "06:00 AM",
      "end_time": "02:00 PM"
    },
    {
      "shift_id": "shift-uuid-2",
      "shift_name": "Afternoon Shift",
      "start_time": "02:00 PM",
      "end_time": "10:00 PM"
    },
    {
      "shift_id": "shift-uuid-3",
      "shift_name": "Night Shift",
      "start_time": "10:00 PM",
      "end_time": "06:00 AM"
    }
  ]
}
```

#### Example
```bash
curl -X GET "http://localhost:8000/admin/setup/shifts?plant_id=abc123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 2. Add Users and Complete Setup

**POST** `/admin/setup/screen5-users`

Add team members and complete the entire setup wizard.

#### Request Body
```json
{
  "plant_id": "abc123-plant-id",
  "users": [
    {
      "role": "manager",
      "first_name": "John",
      "last_name": "Doe",
      "phone_country_code": "+1",
      "phone_number": "5551234567",
      "email": "john@example.com",
      "shift_id": "shift-uuid-1",
      "offsite_permission": true
    },
    {
      "role": "member",
      "first_name": "Jane",
      "last_name": "Smith",
      "phone_country_code": "+91",
      "phone_number": "9876543210",
      "email": null,
      "shift_id": "shift-uuid-2",
      "offsite_permission": false
    }
  ]
}
```

#### Request Parameters

**plant_id** (required)
- UUID of the plant
- From Screen 1 plant setup

**users** (required, array, min 1 user)
- Array of user objects

**User Object Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role` | string | Yes | `"manager"` or `"member"` |
| `first_name` | string | Yes | 1-100 characters |
| `last_name` | string | Yes | 1-100 characters |
| `phone_country_code` | string | Yes | e.g., `"+1"`, `"+91"` (auto-adds `+` if missing) |
| `phone_number` | string | Yes | 10-15 digits |
| `email` | string | No | Optional email address |
| `shift_id` | string | Yes | UUID from shifts dropdown |
| `offsite_permission` | boolean | No | Default: `false`. Allow offsite access |

#### Response (201 Created)
```json
{
  "message": "Users created successfully! Setup completed.",
  "users_created": 2,
  "users": [
    {
      "user_id": "user-uuid-1",
      "full_name": "John Doe",
      "phone": "+15551234567",
      "email": "john@example.com",
      "role": "manager",
      "shift_id": "shift-uuid-1",
      "offsite_permission": true,
      "pin_sent": true
    },
    {
      "user_id": "user-uuid-2",
      "full_name": "Jane Smith",
      "phone": "+919876543210",
      "email": null,
      "role": "member",
      "shift_id": "shift-uuid-2",
      "offsite_permission": false,
      "pin_sent": true
    }
  ],
  "setup_completed": true,
  "redirect_to": "dashboard"
}
```

#### Example
```bash
curl -X POST "http://localhost:8000/admin/setup/screen5-users" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plant_id": "abc123",
    "users": [
      {
        "role": "manager",
        "first_name": "John",
        "last_name": "Doe",
        "phone_country_code": "+1",
        "phone_number": "5551234567",
        "email": "john@example.com",
        "shift_id": "shift-uuid-1",
        "offsite_permission": true
      }
    ]
  }'
```

---

## 🔒 Security

### PIN Generation
- **4-digit** numeric PIN (1000-9999)
- Generated using secure random
- **Hashed** with bcrypt before storage
- **Never** stored or returned in plain text after creation
- Only sent once via SMS/email during setup

### PIN Hashing
```python
# PIN is hashed using bcrypt
pin = "1234"  # Generated
pin_hash = bcrypt.hash(pin)  # Stored in database

# Plain PIN never stored:
user.pin_hash = pin_hash  # ✓ Secure
user.pin = pin            # ✗ Never do this
```

---

## 📱 Welcome Notification

When a user is added, they automatically receive:

### SMS Message
```
Welcome to PocketWatch, John!

Your login PIN: 1234

Download the PocketWatch app:
📱 iOS: https://apps.apple.com/pocketwatch
📱 Android: https://play.google.com/store/apps/pocketwatch

You'll need to verify your phone number with an OTP when you first sign in.

Questions? Contact your manager or visit support.pocketwatch.com
```

### Email (if provided)
Same message sent to email address with formatted HTML.

---

## 🚨 Error Handling

### Common Errors

#### No Shifts Found
```json
{
  "detail": "No shifts found. Please complete Plant Setup first."
}
```
**Solution**: Complete Screen 1 (Plant Setup) first with at least 1 shift

#### Duplicate Phone Number
```json
{
  "detail": "User with phone +15551234567 already exists"
}
```
**Solution**: Use a different phone number (phone numbers must be unique)

#### Invalid Shift
```json
{
  "detail": "Shift abc123 not found for this plant"
}
```
**Solution**: Use a valid shift_id from the `/admin/setup/shifts` endpoint

#### Invalid Role
```json
{
  "detail": "Role must be 'manager' or 'member'"
}
```
**Solution**: Use `"manager"` or `"member"` (lowercase)

#### No Users Provided
```json
{
  "detail": "At least one user required"
}
```
**Solution**: Add at least 1 user to complete setup

---

## 🗄️ Database Schema

### users Table (Tenant Schema)

```sql
CREATE TABLE users (
    user_id VARCHAR(36) PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    phone_country_code VARCHAR(5),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(255),
    email VARCHAR(255),
    default_shift_id VARCHAR(36) REFERENCES shifts(shift_id),
    pin_hash VARCHAR(255),
    phone_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_phone ON users(phone_number);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_shift ON users(default_shift_id);
```

### plant_memberships Table (Tenant Schema)

```sql
CREATE TABLE plant_memberships (
    membership_id VARCHAR(36) PRIMARY KEY,
    plant_id VARCHAR(36) REFERENCES plants(plant_id),
    user_id VARCHAR(36) REFERENCES users(user_id),
    role VARCHAR(20) NOT NULL,  -- 'manager' or 'member'
    invited_by VARCHAR(36),
    invited_at TIMESTAMP DEFAULT NOW(),
    accepted_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_memberships_plant ON plant_memberships(plant_id);
CREATE INDEX idx_memberships_user ON plant_memberships(user_id);
```

### offsite_access_grants Table (Tenant Schema)

```sql
CREATE TABLE offsite_access_grants (
    grant_id VARCHAR(36) PRIMARY KEY,
    plant_id VARCHAR(36) REFERENCES plants(plant_id),
    user_id VARCHAR(36) REFERENCES users(user_id),
    granted_by VARCHAR(36),
    granted_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    revoked_at TIMESTAMP,
    revoked_by VARCHAR(36),
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_offsite_plant ON offsite_access_grants(plant_id);
CREATE INDEX idx_offsite_user ON offsite_access_grants(user_id);
```

---

## 📱 Frontend Integration

### TypeScript Example

```typescript
import { useState } from 'react';

interface User {
  role: 'manager' | 'member';
  firstName: string;
  lastName: string;
  phoneCountryCode: string;
  phoneNumber: string;
  email?: string;
  shiftId: string;
  offsitePermission: boolean;
}

const UserSetupScreen = ({ plantId, accessToken }) => {
  const [users, setUsers] = useState<User[]>([]);
  const [shifts, setShifts] = useState([]);

  // Fetch shifts on mount
  useEffect(() => {
    const fetchShifts = async () => {
      const response = await fetch(
        `https://api.example.com/admin/setup/shifts?plant_id=${plantId}`,
        {
          headers: { Authorization: `Bearer ${accessToken}` },
        }
      );
      const data = await response.json();
      setShifts(data.shifts);
    };
    fetchShifts();
  }, [plantId]);

  // Submit users
  const handleSubmit = async () => {
    if (users.length === 0) {
      alert('Please add at least one user');
      return;
    }

    const response = await fetch(
      'https://api.example.com/admin/setup/screen5-users',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          plant_id: plantId,
          users: users.map(user => ({
            role: user.role,
            first_name: user.firstName,
            last_name: user.lastName,
            phone_country_code: user.phoneCountryCode,
            phone_number: user.phoneNumber,
            email: user.email || null,
            shift_id: user.shiftId,
            offsite_permission: user.offsitePermission,
          })),
        }),
      }
    );

    const result = await response.json();
    
    if (result.setup_completed) {
      // Redirect to dashboard
      navigation.navigate('Dashboard');
    }
  };

  return (
    <View>
      <Text>Add Team Members</Text>
      
      {/* Form to add users */}
      {/* ... */}
      
      <Button onPress={handleSubmit} title="Complete Setup" />
    </View>
  );
};
```

---

## 🔄 Migration

### Running the Migration

```bash
# Navigate to backend directory
cd backend

# Run migration
alembic upgrade head

# Verify
alembic current
```

### Migration Details
- **File**: `add_user_setup_fields.py`
- **Adds**: `first_name`, `last_name`, `default_shift_id` to users table
- **Adds**: `users_completed` to setup_progress table
- **Adds**: `'users'` to SetupStep enum
- **Applies to**: ALL tenant schemas automatically

---

## ✅ Validation Rules

### Required Fields
- ✓ At least **1 user** required
- ✓ Every user must have a **role** (`manager` or `member`)
- ✓ First name, last name, phone required
- ✓ Shift must be valid for the plant

### Phone Number Rules
- Must be **unique** across all users in the tenant
- 10-15 digits
- Country code auto-prefixed with `+` if missing
- Format: `+<country_code><number>` (e.g., `+15551234567`)

### Email Rules
- Optional
- Must be valid email format if provided
- Not enforced as unique

---

## 🎯 Complete Setup Flow

### All 5 Screens

1. **Screen 1**: Plant Setup + Shifts
2. **Screen 2**: Add Departments
3. **Screen 3**: Production Lines + Models
4. **Screen 4**: Create Stations + Characteristics
5. **Screen 5**: Add Users → **Setup Complete!**

### What Happens After Completion

✅ `setup_completed = true`  
✅ Current step set to `COMPLETED`  
✅ Users receive welcome notifications  
✅ Redirect to dashboard  
✅ Users can download app and login with PIN  

---

**Last Updated**: March 4, 2026  
**Version**: 1.0.0  
**Maintained By**: PocketWatch Development Team
