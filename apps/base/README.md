# Base App - Core Foundation for HRMS

The `base` app serves as the **foundational layer** for the entire HRMS project, providing reusable components, utilities, and base classes that are shared across all other apps.

## 📁 File Structure

```
base/
├── __init__.py
├── admin.py          # Admin configurations
├── apps.py           # App configuration
├── models.py         # Base model classes
├── serializers.py    # Base serializer classes
├── utils.py          # Common utility functions
├── views.py          # Base view classes (if any)
├── tests.py          # Unit tests
└── migrations/       # Database migrations
```

---

## 📄 File Descriptions

### `models.py` - Base Model Classes

**Purpose:** Provides abstract base models that other apps inherit from to ensure consistency.

**Key Components:**

#### `BaseTemplateModel`
An abstract base class that all models in the HRMS inherit from.

**Fields:**
- `id` (UUIDField) - Primary key using UUID for better security
- `created_at` (DateTimeField) - Automatically set when record is created
- `updated_at` (DateTimeField) - Automatically updated on every save
- `is_active` (BooleanField) - Soft delete flag (default: True)
- `is_deleted` (BooleanField) - Additional soft delete flag (default: False)

**Benefits:**
- ✅ Consistent ID format across all tables
- ✅ Automatic timestamp tracking
- ✅ Built-in soft delete support
- ✅ Reduces code duplication

**Usage Example:**
```python
from base.models import BaseTemplateModel

class Employee(BaseTemplateModel):
    name = models.CharField(max_length=100)
    # Inherits: id, created_at, updated_at, is_active, is_deleted
```

---

### `serializers.py` - Base Serializer Classes

**Purpose:** Provides base serializers that automatically include common fields.

**Key Components:**

#### `BaseTemplateSerializer`
A base serializer that all other serializers inherit from.

**Fields:**
- `id` (read-only)
- `created_at` (read-only)
- `updated_at` (read-only)
- `is_active` (read-only)
- `is_deleted` (read-only)

**Benefits:**
- ✅ Consistent API responses
- ✅ Reduces serializer boilerplate
- ✅ Ensures common fields are always included

**Usage Example:**
```python
from base.serializers import BaseTemplateSerializer

class EmployeeSerializer(BaseTemplateSerializer):
    class Meta:
        model = Employee
        fields = BaseTemplateSerializer.Meta.fields + ['name', 'email']
        # Automatically includes: id, created_at, updated_at, is_active, is_deleted
```

---

### `utils.py` - Common Utility Functions

**Purpose:** Centralized location for reusable helper functions used across the project.

**Key Functions:**

#### `calculate_working_days(start_date, end_date)`
Calculates the number of working days (Monday-Friday) between two dates.

**Parameters:**
- `start_date` (date) - Start date
- `end_date` (date) - End date

**Returns:** `int` - Number of working days

**Example:**
```python
from base.utils import calculate_working_days
from datetime import date

days = calculate_working_days(date(2026, 2, 20), date(2026, 2, 23))
# Returns: 2 (Friday and Monday, skips Sat/Sun)
```

**Used in:**
- `leaves/models.py` - Leave duration calculation
- `leaves/serializers.py` - Leave balance validation

---

#### `is_weekend(check_date)`
Checks if a given date falls on a weekend (Saturday or Sunday).

**Parameters:**
- `check_date` (date) - Date to check

**Returns:** `bool` - True if weekend, False otherwise

**Example:**
```python
from base.utils import is_weekend
from datetime import date

is_weekend(date(2026, 1, 10))  # Saturday -> True
is_weekend(date(2026, 1, 12))  # Monday -> False
```

**Used in:**
- `leaves/serializers.py` - Weekend validation for leave requests

---

#### `get_employee_profile(user)`
Retrieves the employee profile associated with a user object.

**Parameters:**
- `user` (User) - Django User object

**Returns:** `Employee` instance or `None`

**Why it exists:**
Different parts of the codebase use different attribute names (`employee_profile` vs `employee`). This utility handles both cases.

**Example:**
```python
from base.utils import get_employee_profile

employee = get_employee_profile(request.user)
if employee:
    print(employee.employee_id)
```

**Used in:**
- `leaves/views.py` (8 occurrences)
- `leaves/serializers.py`
- `organization/views/v1.py`
- `organization/views/v2.py`

---

## 🎯 Why the Base App Exists

### 1. **Code Reusability**
Write once, use everywhere. Common logic is centralized instead of duplicated.

### 2. **Consistency**
All models and serializers follow the same structure and patterns.

### 3. **Maintainability**
Bug fixes and improvements in one place benefit the entire project.

### 4. **Testability**
Utility functions can be unit tested independently.

### 5. **Clean Architecture**
Separates core functionality from business logic.

---

## 🔧 How Other Apps Use Base

### Leaves App
- **Models:** Inherits `BaseTemplateModel` for `LeaveRequest` and `LeaveBalance`
- **Serializers:** Inherits `BaseTemplateSerializer` for all serializers
- **Utils:** Uses `calculate_working_days`, `is_weekend`, `get_employee_profile`

### Organization App
- **Models:** Inherits `BaseTemplateModel` for `Employee`, `Department`, `Designation`
- **Serializers:** Inherits `BaseTemplateSerializer`
- **Utils:** Uses `get_employee_profile`

### Audit App
- **Models:** Does NOT inherit `BaseTemplateModel` (audit logs don't need soft delete)
- **Serializers:** Uses custom serializer (audit logs need different fields)

### Users App
- **Models:** Inherits `BaseTemplateModel` for custom user model
- **Serializers:** Inherits `BaseTemplateSerializer`

---

## 📝 Best Practices

### When to Add to Base App

✅ **DO add to base:**
- Functions used in 2+ apps
- Common validation logic
- Shared calculations
- Base model/serializer classes

❌ **DON'T add to base:**
- Business logic specific to one app
- App-specific validations
- One-off helper functions

### Naming Conventions

- **Models:** Use `Base` prefix (e.g., `BaseTemplateModel`)
- **Serializers:** Use `Base` prefix (e.g., `BaseTemplateSerializer`)
- **Utils:** Use descriptive verb names (e.g., `calculate_working_days`, `get_employee_profile`)

---

## 🚀 Future Enhancements

Potential additions to the base app:

- **Date utilities:** `get_fiscal_year()`, `get_quarter()`
- **Validation utilities:** `validate_phone_number()`, `validate_employee_id()`
- **Permission utilities:** `is_manager()`, `has_subordinates()`
- **Email utilities:** `send_notification_email()`

---


