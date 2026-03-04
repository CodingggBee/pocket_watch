# Setup Wizard API Documentation

## Overview
4-screen mobile app setup wizard with resumable progress tracking and subscription-based station quota enforcement.

---

## Architecture

### Models Created
1. **Shift Model** (`app/models/tenant/shift.py`)
   - Tracks work shifts for each plant
   - Fields: `shift_id`, `plant_id` (FK CASCADE), `shift_name`, `start_time` (Time), `end_time` (Time)
   - Cascade delete: when plant is deleted, all shifts are deleted

2. **SetupProgress Model** (`app/models/tenant/setup_progress.py`)
   - Tracks wizard completion state per plant
   - Fields: `progress_id`, `plant_id` (FK CASCADE, UNIQUE), `current_step` (enum), completion flags for each step, `wizard_metadata` (JSONB), timestamps
   - SetupStep enum: `PLANT_SETUP`, `DEPARTMENTS`, `LINES_MODELS`, `STATIONS`, `COMPLETED`

### Subscription Plans
- **FREE**: 1 station limit, basic features
- **PREMIUM**: Unlimited stations (up to `stations_count`), $99/station/month

---

## API Endpoints

Base path: `/admin/setup`

### 1. Get Setup Status
**GET** `/admin/setup/status`

Returns current setup progress and subscription info.

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Response:**
```json
{
  "setup_required": true,
  "current_step": "plant_setup",
  "completed": false,
  "plant_id": "uuid-or-null",
  "plant_setup_completed": false,
  "departments_completed": false,
  "lines_models_completed": false,
  "stations_completed": false,
  "plan_type": "free",
  "stations_limit": 1
}
```

---

### 2. Screen 1: Plant Setup
**POST** `/admin/setup/screen1-plant`

Creates plant with company name, address, and multiple shifts.

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Request Body:**
```json
{
  "company_name": "Acme Manufacturing",
  "plant_name": "Main Plant",
  "address": "123 Industrial Blvd, Detroit, MI 48201",
  "shifts": [
    {
      "start_time": "06:00 AM",
      "end_time": "02:00 PM",
      "shift_name": "Day Shift"
    },
    {
      "start_time": "02:00 PM",
      "end_time": "10:00 PM",
      "shift_name": "Evening Shift"
    },
    {
      "start_time": "10:00 PM",
      "end_time": "06:00 AM",
      "shift_name": "Night Shift"
    }
  ]
}
```

**Notes:**
- Times must be in `HH:MM AM/PM` format (e.g., `"06:00 AM"`)
- Minimum 1 shift required, no maximum
- Updates company name in public schema
- Creates plant in tenant schema
- Automatically creates SetupProgress tracker

**Response:**
```json
{
  "message": "Plant setup completed",
  "plant_id": "abc-123-...",
  "next_step": "departments"
}
```

---

### 3. Screen 2: Add Departments
**POST** `/admin/setup/screen2-departments?plant_id=<plant_id>`

Creates multiple departments for the plant.

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Request Body:**
```json
[
  {
    "department_name": "Assembly",
    "department_code": "ASM"
  },
  {
    "department_name": "Welding",
    "department_code": "WLD"
  },
  {
    "department_name": "Painting"
  }
]
```

**Notes:**
- `department_code` is optional
- Minimum 1 department required (array must have at least 1 item)
- Updates progress: `departments_completed = true`, `current_step = lines_models`

**Response:**
```json
{
  "message": "Created 3 departments",
  "department_ids": ["dept-1", "dept-2", "dept-3"],
  "next_step": "lines_models"
}
```

---

### 4. Screen 3: Add Lines & Models
**POST** `/admin/setup/screen3-lines-models?plant_id=<plant_id>`

Creates production lines with product models for a department.

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Request Body:**
```json
{
  "department_id": "dept-1",
  "lines": [
    {
      "line_name": "Line A",
      "models": [
        {
          "model_name": "Model X",
          "model_code": "MDL-X"
        },
        {
          "model_name": "Model Y",
          "model_code": "MDL-Y"
        }
      ]
    },
    {
      "line_name": "Line B",
      "models": [
        {
          "model_name": "Model Z",
          "model_code": "MDL-Z"
        }
      ]
    }
  ]
}
```

**Notes:**
- Each line must have at least 1 model
- Minimum 1 line required in array
- Creates lines and models in single transaction
- Updates progress: `lines_models_completed = true`, `current_step = stations`

**Response:**
```json
{
  "message": "Created 2 lines with 3 models",
  "line_ids": ["line-1", "line-2"],
  "model_ids": ["model-1", "model-2", "model-3"],
  "next_step": "stations"
}
```

---

### 5. Screen 4: Setup Station
**POST** `/admin/setup/screen4-station?plant_id=<plant_id>`

Creates station with quality control characteristics.

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Request Body:**
```json
{
  "station_name": "Final Assembly Station 1",
  "department_id": "dept-1",
  "line_id": "line-1",
  "model_id": "model-1",
  "sampling_frequency_minutes": 30,
  "characteristics": [
    {
      "characteristic_name": "Torque",
      "unit_of_measure": "Nm",
      "target_value": 50.0,
      "usl": 55.0,
      "lsl": 45.0,
      "ucl": 53.0,
      "lcl": 47.0,
      "sample_size": 5,
      "check_frequency_minutes": 30,
      "chart_type": "I-MR"
    },
    {
      "characteristic_name": "Pressure",
      "unit_of_measure": "PSI",
      "target_value": 100.0,
      "usl": 110.0,
      "lsl": 90.0,
      "chart_type": "Xbar-R"
    }
  ]
}
```

**Notes:**
- Minimum 1 characteristic required
- **Quota Enforcement:**
  - FREE plan: Maximum 1 station
  - PREMIUM plan: Maximum `stations_count` stations
  - Returns `403 Forbidden` with upgrade message when limit reached
- All characteristic fields are optional except `characteristic_name`
- Valid `chart_type` values: `"I-MR"`, `"Xbar-R"`, `"P-Chart"` (defaults to `"I-MR"`)

**Response (Success):**
```json
{
  "message": "Station created successfully",
  "station_id": "station-1",
  "characteristics_count": 2
}
```

**Response (Quota Exceeded - FREE):**
```json
{
  "detail": "Free plan limited to 1 station. Upgrade to Premium for unlimited stations."
}
```
Status: `403 Forbidden`

**Response (Quota Exceeded - PREMIUM):**
```json
{
  "detail": "Station limit reached (10). Increase your station count in Plans."
}
```
Status: `403 Forbidden`

---

### 6. Complete Setup
**POST** `/admin/setup/complete?plant_id=<plant_id>`

Marks setup wizard as completed.

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Requirements:**
- At least 1 station must exist in the plant
- Returns `400 Bad Request` if no stations exist

**Response:**
```json
{
  "message": "Setup completed successfully!",
  "setup_completed": true,
  "redirect_to": "dashboard"
}
```

**Notes:**
- Updates progress: `stations_completed = true`, `setup_completed = true`, `current_step = completed`
- Sets `completed_at` timestamp
- User can still add stations after completing setup

---

### 7. Add Station (Post-Setup)
**POST** `/admin/setup/add-station?plant_id=<plant_id>`

Add new station from anywhere in app (after wizard completion).

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Request Body:** Same as Screen 4

**Notes:**
- Identical to screen4-station endpoint
- Same quota enforcement applies
- Can be used after setup is completed

---

## Resumability

The wizard automatically tracks progress:

1. **First visit:** `/admin/setup/status` returns `current_step: "plant_setup"`
2. **After Screen 1:** Returns `current_step: "departments"`, `plant_setup_completed: true`
3. **After Screen 2:** Returns `current_step: "lines_models"`, `departments_completed: true`
4. **After Screen 3:** Returns `current_step: "stations"`, `lines_models_completed: true`
5. **After completion:** Returns `setup_completed: true`, `current_step: "completed"`

Mobile app should call `/admin/setup/status` on app launch to check if setup is required and resume at the correct step.

---

## Database Schema Updates

### For Existing Tenants
Run the migration script once:

```bash
cd backend
python scripts/add_setup_tables_to_tenants.py
```

**Output:**
```
============================================================
Adding shifts and setup_progress tables to tenant schemas
============================================================

Found 9 tenant schema(s)

Processing schema: company_abc123...
  -> Creating shifts table...
  [OK] shifts table created
  -> Creating setup_progress table...
  [OK] setup_progress table created

...

============================================================
SUMMARY
============================================================
[OK] Successfully updated: 9
[SKIP] Skipped (already had tables): 0
[ERROR] Errors: 0
Total schemas processed: 9

[SUCCESS] All schemas processed successfully!
```

**Features:**
- Idempotent: safe to run multiple times
- Checks for existing tables before creating
- Creates only new tables (shifts, setup_progress)
- Processes all company_* schemas automatically
- Detailed progress output

### For New Tenants
New company signups automatically provision all tenant tables including shifts and setup_progress via `provision_tenant_tables()`.

---

## Error Handling

### Common Errors

**404 Not Found**
- Plant ID doesn't exist
- Department/Line/Model ID doesn't exist

**403 Forbidden**
- Station quota exceeded (FREE or PREMIUM limit reached)

**422 Unprocessable Entity**
- Invalid time format (must be `HH:MM AM/PM`)
- Missing required fields
- Array constraints violated (e.g., empty shifts array)

**500 Internal Server Error**
- Database connection issues
- Tenant schema not provisioned (auto-recovery attempted)

---

## Testing Guide

### 1. Check Setup Status
```bash
curl -X GET http://localhost:8000/admin/setup/status \
  -H "Authorization: Bearer <admin_token>"
```

### 2. Complete Full Wizard Flow

**Screen 1:**
```bash
curl -X POST http://localhost:8000/admin/setup/screen1-plant \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Co",
    "plant_name": "Plant 1",
    "address": "123 Main St",
    "shifts": [{"start_time": "08:00 AM", "end_time": "04:00 PM"}]
  }'
```

**Screen 2:**
```bash
curl -X POST "http://localhost:8000/admin/setup/screen2-departments?plant_id=<plant_id>" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '[{"department_name": "Assembly"}]'
```

**Screen 3:**
```bash
curl -X POST "http://localhost:8000/admin/setup/screen3-lines-models?plant_id=<plant_id>" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "department_id": "<dept_id>",
    "lines": [{
      "line_name": "Line A",
      "models": [{"model_name": "Model X", "model_code": "MDL-X"}]
    }]
  }'
```

**Screen 4:**
```bash
curl -X POST "http://localhost:8000/admin/setup/screen4-station?plant_id=<plant_id>" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "station_name": "Station 1",
    "department_id": "<dept_id>",
    "line_id": "<line_id>",
    "model_id": "<model_id>",
    "characteristics": [{
      "characteristic_name": "Torque",
      "target_value": 50.0
    }]
  }'
```

**Complete:**
```bash
curl -X POST "http://localhost:8000/admin/setup/complete?plant_id=<plant_id>" \
  -H "Authorization: Bearer <admin_token>"
```

### 3. Test Quota Enforcement

**FREE Plan - Try creating 2nd station (should fail):**
```bash
# First station succeeds
curl -X POST "http://localhost:8000/admin/setup/screen4-station?plant_id=<plant_id>" ...

# Second station fails with 403
curl -X POST "http://localhost:8000/admin/setup/screen4-station?plant_id=<plant_id>" ...
# Response: {"detail": "Free plan limited to 1 station. Upgrade to Premium for unlimited stations."}
```

---

## Implementation Summary

### Files Created/Modified

**Created:**
1. `app/models/tenant/shift.py` - Shift model
2. `app/models/tenant/setup_progress.py` - SetupProgress model with SetupStep enum
3. `app/routes/setup_wizard.py` - Complete 4-screen API
4. `scripts/add_setup_tables_to_tenants.py` - Schema migration utility
5. `SETUP_WIZARD_API.md` - This documentation

**Modified:**
1. `app/models/tenant/__init__.py` - Registered new models
2. `backend/main.py` - Added setup_wizard_router

### Key Features Implemented

✅ 4-screen wizard flow with sequential steps
✅ Resumable progress tracking (SetupProgress model)
✅ Subscription plan enforcement (FREE vs PREMIUM)
✅ Station quota validation
✅ Time format validation (HH:MM AM/PM)
✅ Automatic tenant schema provisioning
✅ Cascade delete for data integrity
✅ JSONB metadata field for extensibility
✅ Comprehensive error handling
✅ Idempotent schema migration script
✅ Complete API documentation

---

## Next Steps

1. **Mobile App Integration:**
   - Call `/admin/setup/status` on app launch
   - Redirect to appropriate screen based on `current_step`
   - Show progress indicator (4 screens)

2. **Frontend Enhancements:**
   - Google Places API integration for address autocomplete
   - Time picker component (12-hour format with AM/PM)
   - Multi-select for departments/lines
   - Quota warning banner for FREE users

3. **Future Enhancements:**
   - Bulk station import via CSV
   - Station templates (copy from existing)
   - Setup wizard skip option for advanced users
   - Analytics dashboard for setup completion rates

---

## Support

For issues or questions:
- Check `/docs` endpoint for interactive Swagger UI
- Review error messages (422 validation errors are detailed)
- Verify subscription plan in database
- Check tenant schema provisioning in logs
