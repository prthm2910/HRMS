# 👤 Users & Authentication Module

The **Users App** acts as the **central identity and authorization backbone** of the HRMS platform.  
It is responsible for authentication, user identity management, and providing foundational abstractions that are reused across all other domain apps.

This module is intentionally designed as a **core dependency**—every other app (Organization, Leaves, Audit) either directly or indirectly relies on it.

---

## 🎯 Responsibilities at a Glance

- Provide a **custom authentication system** using email-based login
- Act as the **single source of truth** for user identities
- Define shared **base models** to enforce consistency across the database
- Integrate with **JWT authentication** and **RBAC (Role-Based Access Control)**

---

## ✨ Key Features

### 1️⃣ Custom User Model
- Replaces Django’s default `User` model
- Uses **email-first identity** (while retaining username compatibility)
- Easily extensible for future profile attributes

### 2️⃣ UUID-Based Primary Keys
- All models use **UUIDs** instead of sequential integers
- Prevents ID enumeration and improves security in public APIs

### 3️⃣ Global Base Model (`BaseTemplateModel`)
- Abstract base class inherited by **almost every model** in the system
- Enforces consistent fields such as timestamps and soft-delete flags

### 4️⃣ Role & Permission Integration
- Works seamlessly with Django’s permission framework
- Supports logical roles such as **Admin**, **Manager**, and **Employee**
- Enables fine-grained access control at the API layer

---

## 🗄️ Database Models

### 🧑 `User` — Custom Authentication Model

The primary authentication entity for the HRMS.

- **Table Name:** `users`
- **Inherits From:** `AbstractUser`, `BaseTemplateModel`

#### Key Fields
- `username` → Unique identifier (required)
- `email` → Unique, used for communication & login
- `phone_number` → Optional contact detail
- `bio` → Free-form user profile description
- `is_active` → Controls account availability

This model is referenced throughout the system using `AUTH_USER_MODEL`.

---

### 🧩 `BaseTemplateModel` — Global Abstract Base Class

An **abstract utility model** designed to standardize database behavior across all apps.

```python
class BaseTemplateModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)  # Soft delete support
```

#### Why this matters:
- Guarantees **consistent auditing fields**
- Enables **soft deletes** without data loss
- Eliminates repetitive boilerplate across domain apps

---

## 🔐 Authentication & JWT Flow

The Users app underpins the system’s **JWT-based authentication** using `SimpleJWT`.

### Token Endpoints
- **POST** `/api/token/`  
  → Returns `access` and `refresh` tokens
- **POST** `/api/token/refresh/`  
  → Issues a new access token using a refresh token

> ⚠️ Note  
> URL routing for these endpoints is typically centralized in `hrms/urls.py`,  
> but the authentication logic is entirely dependent on the `User` model defined here.

---

## 🔄 Integration Guidelines

### ✅ Linking Any Model to a User

Always reference the user model via `settings.AUTH_USER_MODEL`  
This prevents circular imports and ensures long-term flexibility.

```python
from django.conf import settings
from django.db import models

class SomeModel(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
```

---

### ✅ Using the Global Base Model

All domain models should inherit from `BaseTemplateModel` to maintain consistency.

```python
from users.models import BaseTemplateModel

class Department(BaseTemplateModel):
    name = models.CharField(max_length=100)
```

This automatically provides:
- UUID primary key
- Creation & update timestamps
- Soft-delete capability

---

## 🧠 Architectural Importance

The **Users App is intentionally foundational**:
- Changes here impact the entire system
- Strong conventions reduce bugs and improve maintainability
- Encourages clean boundaries and Domain-Driven Design

Because of this, modifications to this module should be **carefully reviewed** and accompanied by migrations and tests.

---

## ✅ Summary

- Central identity provider for HRMS
- Defines authentication, authorization, and shared base models
- Enforces security, consistency, and scalability across all apps
- Designed to be stable, reusable, and future-proof
