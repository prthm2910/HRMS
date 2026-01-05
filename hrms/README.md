### ---

**📄 hrms/README.md (Configuration Documentation)**

Markdown

\# ⚙️ HRMS Configuration Package

This directory contains the core configuration files, settings, and entry points for the HRMS Django project.

\#\# 📂 Key Files

| File | Description |  
| :--- | :--- |  
| **\*\*\`settings.py\`\*\*** | Main configuration file. Handles DB connections, DRF settings, and installed apps. |  
| **\*\*\`urls.py\`\*\*** | Global URL router. Dispatches requests to specific apps (\`users\`, \`leaves\`, etc.). |  
| **\*\*\`wsgi.py\`\*\*** | WSGI entry point for synchronous production servers (e.g., Gunicorn). |  
| **\*\*\`asgi.py\`\*\*** | ASGI entry point for asynchronous capabilities. |

\---

\#\# 🔧 Environment Variables

The \`settings.py\` file uses \`django-environ\` to load secrets. Ensure your \`.env\` file (located in the project root) contains the following keys:

\#\#\# **\*\*Required\*\***  
\`\`\`ini  
\# Security  
DEBUG=False  
DJANGO\_SECRET\_KEY=your-secure-secret-key  
ALLOWED\_HOSTS=api.yourdomain.com,127.0.0.1

\# Database (PostgreSQL)  
DB\_NAME=<DB_NAME>  
DB\_USER=<DB_USER>  
DB\_PASSWORD=<DB_PASSWORD>
DB\_HOST=<DB_HOST>
DB\_PORT=<DB_PORT>

\# Authentication  
AUTH\_USER\_MODEL=<AUTH_USER_MODEL>

### **Optional / Production**


\# CORS (Frontend Access)  
CORS\_ALLOWED\_ORIGINS\=\[https://your-frontend-domain.com\](https://your-frontend-domain.com)


## ---

**🔌 Middleware Pipeline**

The settings.py defines a strict middleware order to ensure security and audit logging:

1. **CorsMiddleware**: Handles Cross-Origin requests (Must be first).  
2. **SecurityMiddleware**: Enforces HTTPS/HSTS.  
3. **SessionMiddleware**: Manages user sessions.  
4. **AuthenticationMiddleware**: Attaches request.user.  
5. **AuditMiddleware**: **(Custom)** Logs the request/response. *Note: Placed after Auth to capture the user.*

## ---

**🌐 URL Routing**

The urls.py aggregates routes from all domain apps:

* /admin/ \-\> Django Admin  
* /api/users/ \-\> User Authentication & Profile  
* /api/leaves/ \-\> Leave Requests & Balances  
* /api/org/ \-\> Departments & Employees  
* /api/schema/ \-\> OpenAPI Documentation

## ---

**🐍 Python Path Configuration**

In settings.py, we explicitly modify the system path to support the modular apps/ directory structure:

Python

APPS\_DIR \= BASE\_DIR / 'apps'  
sys.path.insert(0, str(APPS\_DIR))

This allows clean imports throughout the project (e.g., from leaves.models import ...) instead of from apps.leaves.models....