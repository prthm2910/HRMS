# 📦 Business Logic (Domain Apps)

This directory contains the core business logic of the HRMS, structured into isolated **Domain Apps**.

Each folder represents a specific feature set of the system. This modular, Domain-Driven Design (DDD) approach ensures that the codebase remains organized, testable, and scalable as the project grows.

---

## 🏗️ Apps Overview

| App Module | Description | Key Models |
| :--- | :--- | :--- |
| **[users](./users)** | Handles Authentication, User Profiles, and Role Management. | `User` (Custom Auth Model) |
| **[organization](./organization)** | Manages company hierarchy, departments, and employee records. | `Employee`, `Department` |
| **[leaves](./leaves)** | Core Leave Management System handling applications, balances, and approvals. | `LeaveRequest`, `LeaveBalance` |
| **[audit](./audit)** | Cross-cutting audit system logging every action for security & compliance. | `AuditLog` |

---

## 🔌 Inter-App Dependencies

While each app is modular, they interact through clearly defined relationships:

### `leaves` → `organization`
- A `LeaveRequest` is linked to an `Employee`.
- Approval workflows rely on the `Employee.manager` hierarchy defined in the organization app.

### `organization` → `users`
- Each `Employee` profile has a **One-to-One** relationship with a `User` account used for authentication.

### `audit` → (All Apps)
- The `AuditMiddleware` is globally applied and monitors traffic across **all apps**, attributing actions to the responsible `User`.

---

## 🛠️ Standard App Structure

All domain apps follow a consistent Django Rest Framework structure:

```text
app_name/
├── models.py       # Database schema
├── serializers.py  # Serialization & validation
├── views.py        # API logic (ViewSets)
├── urls.py         # App-specific routes
├── signals.py      # Event hooks (e.g., auto-create profiles)
├── apps.py         # App configuration
└── tests.py        # Unit & integration tests
```

---

## 💡 API Versioning Strategy

The **organization** app demonstrates a production-grade API versioning approach:

- `views/v1.py`  
  - Legacy / stable endpoints  
  - Uses **Hard Deletes**

- `views/v2.py`  
  - Enhanced functionality  
  - Uses **Soft Deletes**

This strategy allows backward compatibility for existing clients while enabling safe evolution of the API.
