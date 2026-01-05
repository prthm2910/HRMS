# 🏢 Organization & Employee Module

The **Organization App** models the structural and hierarchical foundation of the HRMS.  
It is responsible for managing **departments**, **employee profiles**, and the **reporting hierarchy** that defines how authority and accountability flow within the company.

This module is architecturally significant because it introduces **recursive relationships** and demonstrates a **production-grade API versioning strategy**.

---

## 🎯 Core Responsibilities

- Represent the company’s organizational structure
- Maintain employee-to-manager reporting relationships
- Associate employees with departments and roles
- Provide backward-compatible APIs through explicit versioning

---

## ✨ Key Features

### 1️⃣ Hierarchical Reporting Structure
- Supports **infinite depth** management hierarchies
- Implemented using a **self-referential foreign key**
- Enables queries like:
  - “Who reports to this manager?”
  - “What is the full reporting tree?”

### 2️⃣ Human-Readable Employee IDs
- Automatically generates unique employee identifiers  
  Example: `EMP9A2B3C`
- Improves usability for HR teams and audit logs
- Decouples internal UUIDs from business-facing identifiers

### 3️⃣ API Versioning (v1 / v2)
- Clean separation of stable and evolving logic
- Allows new features to be introduced **without breaking existing clients**
- Encourages long-term maintainability and safe refactoring

---

## 🗄️ Database Models

### 🏢 `Department`

Represents a functional unit within the organization.

**Examples:** Engineering, Human Resources, Finance

- **Key Fields**
  - `name` → Department name (unique)
  - `description` → Optional description

---

### 🧑 `Employee`

Represents an employee’s organizational identity and reporting context.

- **Relationship**
  - One-to-One with `users.User`
- **Key Fields**
  - `employee_id` → Auto-generated, human-readable ID
  - `designation` → Job title
  - `department` → ForeignKey to `Department`
  - `manager` → Self-referential ForeignKey

---

### 🔁 Manager–Subordinate Relationship

The reporting hierarchy is modeled using a **self-referential relationship**:

```python
class Employee(BaseTemplateModel):
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        related_name='subordinates'
    )
```

#### Why this design works:
- Enables recursive tree traversal
- Allows managers to have unlimited subordinates
- Keeps the schema simple and expressive

---

## 📡 API Versioning Strategy

Instead of a monolithic `views.py`, this app adopts a **package-based view architecture**, which scales better as APIs evolve.

```text
organization/
└── views/
    ├── __init__.py   # Exposes versioned views
    ├── v1.py         # Stable / legacy endpoints (with HARD Delete)
    └── v2.py         # New feature (with SOFT Delete)
```

### Version Semantics

- **V1 API**
  - Standard CRUD endpoints
  - Flat response structures
  - Designed for stability

- **V2 API**
  - Enhanced or experimental features
  - Example: Nested organization trees instead of flat lists
  - May introduce soft deletes or optimized queries

---

### URL Routing

API versions are explicitly exposed via URL paths:

```text
GET /api/org/v1/employees/
GET /api/org/v2/employees/
```

This allows clients (web, mobile, integrations) to **opt-in** to newer behavior safely.

---

## 🧠 Business Rules & Data Integrity

### 1️⃣ Employee ID Generation
- Implemented in the `save()` method
- If `employee_id` is missing:
  - Generates a random 6-character hexadecimal suffix
  - Prefixes it with `EMP`

**Example:** `EMP` + `A1B2C3`

---

### 2️⃣ Deletion Semantics

The system prioritizes **data integrity over hard deletion**:

- **Department Deletion**
  - Employees are preserved
  - Their `department` field is set to `NULL`

- **Manager Deletion**
  - Subordinates are preserved
  - Their `manager` field is set to `NULL` (orphaned)

This ensures:
- No accidental cascade deletions
- Historical data remains intact
- Audit logs remain meaningful

---

## 🧩 Architectural Significance

- Introduces recursive domain modeling
- Demonstrates clean API versioning practices
- Serves as the backbone for workflows like:
  - Leave approvals
  - Manager-based permissions
  - Organization-wide reporting

Because many other modules depend on organizational hierarchy, this app should be treated as **high-impact and carefully versioned**.

---

## ✅ Summary

- Models departments and employees
- Supports infinite management hierarchies
- Uses human-friendly employee IDs
- Demonstrates production-ready API versioning
- Designed for scalability, safety, and clarity
