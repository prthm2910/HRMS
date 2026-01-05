# 🍃 Leave Management Module

The **Leaves App** is responsible for managing the complete lifecycle of employee time-off requests.  
It is designed as a **rule-driven, defensive domain module** that proactively prevents invalid leave applications before they ever reach the database.

This app plays a critical role in enforcing **organizational policy**, **managerial authority**, and **data integrity**.

---

## 🎯 Core Responsibilities

- Handle employee leave applications from creation to resolution
- Enforce strict business validations (dates, overlaps, balances)
- Maintain accurate leave balances per employee and leave type
- Support a structured, auditable approval workflow

---

## ✨ Key Features

### 1️⃣ Smart Validation Engine

All critical checks are performed **before persistence**, ensuring invalid requests are rejected early.

- **Overlap Prevention**  
  Prevents multiple leave requests covering the same date range.

- **Past Date Blocking**  
  Disallows leave requests for dates in the past.

- **Balance Enforcement**  
  Automatically rejects requests when available leave balance is insufficient.

---

### 2️⃣ Structured Approval Workflow

Leave requests move through a clearly defined lifecycle:

- **PENDING** → Created by Employee  
- **APPROVED / REJECTED** → Actioned by Manager or Admin  
- **CANCELLED** → Optional future state (employee-initiated)

#### Enforcement Rules
- Status changes are permission-restricted
- `rejection_reason` is **mandatory** when rejecting a request
- Every action is attributable to a specific user (`action_by`)

---

### 3️⃣ Accurate Leave Balance Tracking

- Tracks allocated vs consumed leave per employee
- Prevents negative balances by design
- Removes reliance on frontend calculations

---

## 🗄️ Database Models

### 📝 `LeaveRequest`

Represents a single application for time off.

**Key Fields**
- `employee` → Applicant (FK to Employee)
- `start_date` / `end_date` → Leave duration
- `status` → Enum: `PENDING`, `APPROVED`, `REJECTED`, `CANCELLED`
- `action_by` → Manager/Admin who processed the request
- `rejection_reason` → Required if status is `REJECTED`

---

### 📊 `LeaveBalance`

Tracks leave quota per employee and leave type.

**Key Characteristics**
- **Unique Constraint:** `(employee, leave_type)`  
  → Ensures one balance record per leave type per employee
- **Fields**
  - `total_allocated`
  - `used_leaves`
- **Derived Property**
  - `remaining_leaves = total_allocated - used_leaves`

This model acts as the **single source of truth** for leave availability.

---

## 🛡️ Security & Role-Based Access Control

The `LeaveRequestViewSet` enforces strict RBAC rules aligned with organizational authority.

| Role | Capabilities |
| :--- | :--- |
| **Employee** | Create leave requests, view only their own requests |
| **Manager** | View own + subordinates’ requests, approve or reject team requests |
| **Admin** | Full read/write access across all leave records |

Unauthorized status changes are explicitly blocked at the serializer and view level.

---

## 📡 API Endpoints

### 📝 Leave Requests  
`/api/leaves/requests/`

- **GET /**  
  List leave requests (scope filtered by role)

- **POST /**  
  Apply for new leave  
  ```json
  {
    "leave_type": "SICK",
    "start_date": "2024-01-01",
    "end_date": "2024-01-02",
    "reason": "Flu"
  }
  ```

- **PATCH /{id}/** *(Manager/Admin only)*  
  Approve or reject a request  
  ```json
  {
    "status": "APPROVED"
  }
  ```

---

### 📊 Leave Balances  
`/api/leaves/balance/`

- **GET /**  
  View leave balances and remaining quotas  
  > Read-only for most users.  
  > Admins may adjust balances via Django Admin.

---

## 🧠 Business Logic Highlights

### 🔁 Overlap Detection Algorithm

To prevent conflicting leave periods, the serializer checks for intersecting date ranges:

```python
# Overlap condition:
# (Start A <= End B) and (End A >= Start B)
overlapping = LeaveRequest.objects.filter(
    start_date__lte=request_end_date,
    end_date__gte=request_start_date
)
```

This ensures **no two approved or pending leaves overlap** for the same employee.

---

### ⏱️ Automatic Duration Calculation

The `duration` property computes the total number of leave days (inclusive):

- Eliminates frontend miscalculations
- Ensures consistency across reports, balances, and audits

---

## 🧩 Architectural Significance

- Enforces complex domain rules at the backend
- Integrates tightly with:
  - **Organization App** (manager hierarchy)
  - **Users App** (identity & permissions)
  - **Audit App** (action traceability)
- Designed to be deterministic, auditable, and resistant to misuse

---

## ✅ Summary

- Full lifecycle management of employee leave
- Defensive validation to prevent invalid data
- Clear approval authority and auditability
- Accurate, backend-controlled balance calculations
- Production-ready RBAC enforcement
