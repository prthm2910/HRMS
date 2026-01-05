# ⚙️ HRMS Configuration Package

This directory contains the **core configuration layer** of the HRMS Django project.  
It defines global settings, environment configuration, middleware orchestration, and URL routing.

This package is intentionally kept **thin and declarative**, separating configuration concerns from domain business logic (`apps/`).

---

## 📂 Key Files

| File | Purpose |
| :--- | :--- |
| `settings.py` | Primary configuration file. Manages database connections, DRF, authentication, middleware, and installed apps. |
| `urls.py` | Global URL router. Dispatches requests to domain apps (`users`, `organization`, `leaves`, etc.). |
| `wsgi.py` | WSGI entry point for synchronous production servers (e.g., Gunicorn). |
| `asgi.py` | ASGI entry point enabling async features (WebSockets, async views). |

---

## 🔧 Environment Variables

The project uses **`django-environ`** to externalize secrets and environment-specific configuration.

All environment variables are loaded from a `.env` file located at the **project root**.

---

### ✅ Required Variables

```ini
# Security
DEBUG=False
DJANGO_SECRET_KEY=your-secure-secret-key
ALLOWED_HOSTS=api.yourdomain.com,127.0.0.1

# Database (PostgreSQL)
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

# Authentication
AUTH_USER_MODEL=users.User
```

---

### ⚙️ Optional / Production Variables

```ini
# CORS (Frontend Access)
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com
```

These values should be customized per environment (local, staging, production).

---

## 🔌 Middleware Pipeline

The `settings.py` file defines a **strict middleware order** to ensure correctness, security, and full audit coverage.

Middleware execution order (top → bottom):

1. **CorsMiddleware**  
   Handles cross-origin requests (must be first).

2. **SecurityMiddleware**  
   Enforces HTTPS, HSTS, and security headers.

3. **SessionMiddleware**  
   Manages session data.

4. **AuthenticationMiddleware**  
   Resolves and attaches `request.user`.

5. **AuditMiddleware** *(Custom)*  
   Captures request metadata and persists audit logs.  
   > Placed after authentication to ensure the actor is correctly identified.

---

## 🌐 URL Routing

The global `urls.py` aggregates routes from all domain apps and exposes shared infrastructure endpoints.

| Path | Description |
| :--- | :--- |
| `/admin/` | Django Admin interface |
| `/api/users/` | Authentication & user management |
| `/api/leaves/` | Leave requests & balances |
| `/api/org/` | Departments & employee hierarchy |
| `/api/schema/` | OpenAPI schema & documentation |

---

## 🐍 Python Path Configuration

To support a **clean, modular project layout**, the `apps/` directory is explicitly added to the Python path.

This allows concise imports across the project.

```python
APPS_DIR = BASE_DIR / "apps"
sys.path.insert(0, str(APPS_DIR))
```

### Resulting Benefit

```python
# Preferred
from leaves.models import LeaveRequest

# Avoided
from apps.leaves.models import LeaveRequest
```

This improves readability and keeps domain logic decoupled from infrastructure concerns.

---

## ✅ Summary

- Centralized configuration layer for the HRMS backend
- Environment-driven settings with zero hardcoded secrets
- Strict middleware ordering for security and audit integrity
- Clean URL aggregation across domain apps
- Explicit Python path control for scalable modular design
