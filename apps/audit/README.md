# 🛡️ Audit Logging Module

The **Audit App** is the system’s **forensic black box**.  
It operates silently in the background, capturing **who did what, when, where, and how**—without requiring any explicit logging code inside business modules.

Unlike traditional text-based logs, this module persists **structured, queryable audit data** in the database, making it suitable for compliance, investigations, and security reviews.

---

## 🎯 Core Responsibilities

- Provide **system-wide accountability** without polluting domain logic
- Capture user actions across all apps automatically
- Persist structured audit trails for querying and reporting
- Ensure no authenticated action goes untracked—even in edge cases

---

## ✨ Key Features

### 1️⃣ Zero‑Touch Integration
- Domain apps (`users`, `organization`, `leaves`) do **not** manually log events
- Logging is fully automatic via **Django Signals**
- New models are audited by default without additional code

---

### 2️⃣ Thread‑Local Request Context
- Uses custom middleware to capture request metadata
- Makes request-level data available to the model layer
- Solves Django’s classic “models don’t know the user” problem

---

### 3️⃣ Resilient Authentication Capture
- Manually inspects raw JWT headers when needed
- Ensures user identity is captured even if:
  - DRF authentication hasn’t executed yet
  - A request fails mid‑pipeline
- Prevents silent or anonymous database mutations

---

## ⚙️ Architectural Design

### ❌ The Core Problem

Django model methods (`save()`, `delete()`) execute **outside** the request lifecycle and therefore have **no access to `request.user`**.

---

### ✅ The Solution: Middleware + Signals + Thread‑Local Storage

This module bridges that gap using a three‑stage pipeline.

---

### 🧩 Step 1: Capture Request Context (Middleware)

**Location:** `middleware.py`

- Intercepts every incoming HTTP request
- Extracts:
  - Authenticated user (or attempts JWT fallback)
  - IP address
  - Request path
  - User agent
- Stores this data in **thread‑local storage**

This context is now accessible anywhere during the request lifecycle.

---

### 🧩 Step 2: Detect Model Changes (Signals)

**Location:** `signals.py`

- Hooks into:
  - `post_save`
  - `post_delete`
- Applies globally across registered models
- Triggers automatically whenever any model changes

---

### 🧩 Step 3: Persist the Audit Log (Model)

**Location:** `models.py`

- Retrieves context from thread‑local storage
- Determines the action type (`CREATE`, `UPDATE`, `DELETE`)
- Saves a structured `AuditLog` record linking:
  - Actor
  - Action
  - Target object
  - Request metadata

---

## 🗄️ Database Model

### 🧾 `AuditLog`

Stores immutable records of system activity.

| Field | Description |
| :--- | :--- |
| `actor` | User who performed the action |
| `action` | Enum: `CREATE`, `UPDATE`, `DELETE`, `LOGIN`, `LOGOUT` |
| `table_name` | Affected database table |
| `object_id` | Primary key of the modified record |
| `path` | API endpoint accessed |
| `ip_address` | Source IP |
| `user_agent` | Browser / device metadata |
| `changes` | JSON snapshot of **before & after** state |
| `created_at` | Timestamp of the action |

This structure enables forensic queries such as:
- “Who changed this employee’s manager?”
- “Show all updates made by a user last week.”

---

## 🔌 Integration Guide

### ✅ Enabling Global Auditing

Register the middleware in `settings.py`.

> ⚠️ Placement matters  
> It must be **after** `AuthenticationMiddleware`.

```python
MIDDLEWARE = [
    # ...
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.audit.middleware.AuditMiddleware',
]
```

Once enabled, **all model changes are audited automatically**.

---

### 🚫 Excluding Specific Models

For noisy or irrelevant tables (e.g., `Session`):

- Add a flag on the model:
  ```python
  skip_audit = True
  ```
- Or configure exclusions directly in `signals.py`

This keeps the audit log meaningful and focused.

---

## 🛡️ Security & Resilience

### JWT Fallback Authentication

The middleware includes a defensive fallback mechanism:

```python
def get_api_user(self, request):
    """Attempts JWT-based user resolution because
    DRF authentication runs after middleware."""
```

This ensures:
- Actor identity is captured even if DRF auth is bypassed
- No database mutation occurs without an attribution attempt
- Audit coverage remains complete under failure scenarios

---

## 🧠 Architectural Significance

- Operates as a **cross-cutting concern**
- Requires zero coupling with business logic
- Enables:
  - Compliance audits
  - Security investigations
  - Historical reconstruction of system state
- Strengthens trust and accountability across the platform

---

## ✅ Summary

- System-wide, automatic audit logging
- No manual instrumentation required in domain apps
- Structured, queryable audit data
- Resilient to authentication edge cases
- Designed for compliance, security, and forensics
