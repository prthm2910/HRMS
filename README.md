\# 🏢 HRMS Backend API (Human Resource Management System)

A production-ready, domain-driven Backend API for Human Resource Management built with **\*\*Django 6.0\*\*** and **\*\*Django Rest Framework (DRF)\*\***.

This system handles complex HR workflows including Leave Management, Organization Hierarchies, and Automated Audit Logging, secured via Role-Based Access Control (RBAC) and JWT Authentication.

\---

\#\# 🚀 Key Features

\#\#\# 🔹 Core Modules  
\* **\*\*Leave Management:\*\***  
  \* Automated balance checking against \`LeaveBalance\`.  
  \* Strict validation preventing past dates and overlapping requests.  
  \* Manager approval workflow (Approve/Reject with mandatory reasoning).  
\* **\*\*Organization Structure:\*\***  
  \* Hierarchical management of \`Employees\` and \`Departments\`.  
  \* Supports "Manager \-\> Subordinate" relationships.  
  \* Versioned API design (\`v1\`, \`v2\`) for future-proof scalability.  
\* **\*\*Audit & Compliance:\*\***  
  \* **\*\*Automated Logging:\*\*** Custom Middleware captures every request (User, IP, Path, Method) and stores it for accountability.  
  \* **\*\*Resilient Auth:\*\*** Captures actor details even if the request uses raw JWT headers.

\#\#\# 🔹 Security & Architecture  
\* **\*\*JWT Authentication:\*\*** Secure, stateless token-based auth using \`SimpleJWT\`.  
\* **\*\*RBAC:\*\*** Granular permissions differentiating Admins, Managers, and Employees.  
\* **\*\*UUID Primary Keys:\*\*** Protects against ID enumeration attacks.  
\* **\*\*Environment Isolation:\*\*** Secrets managed via \`.env\` files using \`django-environ\`.

\---

\#\# 🛠️ Tech Stack

\* **\*\*Framework:\*\*** Python 3.13, Django 6.0, Django Rest Framework 3.16  
\* **\*\*Database:\*\*** PostgreSQL  
\* **\*\*Authentication:\*\*** JSON Web Tokens (JWT) via \`djangorestframework-simplejwt\`  
\* **\*\*Documentation:\*\*** OpenAPI 3.0 (Swagger/Redoc) via \`drf-spectacular\`  
\* **\*\*Utilities:\*\*** \`django-filter\`, \`corsheaders\`, \`django-environ\`

\---

\#\# 📂 Project Structure

This project follows a production-grade folder structure separating configuration from business logic.

\`\`\`text  
hrms\_project/  
├── .env                    \# Environment variables (Secrets)  
├── manage.py               \# Django Task Runner  
├── requirements.txt        \# Dependencies  
├── hrms/                   \# ⚙️ Configuration Package (Settings, WSGI, ASGI)  
├── apps/                   \# 📦 Business Logic (Domain Apps)  
│   ├── audit/              \# Audit Logs & Middleware  
│   ├── leaves/             \# Leave Requests & Balances  
│   ├── organization/       \# Employees & Departments  
│   └── users/              \# Authentication & User Models  
├── media/                  \# User Uploads  
├── static/                 \# Development Static Files  
└── staticfiles/            \# Production Static Assets (Collected)

## ---

**⚡ Getting Started**

### **Prerequisites**

* Python 3.13+  
* PostgreSQL  
* Git

### **1\. Clone the Repository**

Bash

git clone \[https://github.com/yourusername/hrms-backend.git\](https://github.com/yourusername/hrms-backend.git)  
cd hrms-backend

### **2\. Create Virtual Environment**

Bash

python \-m venv venv  
\# Windows  
venv\\Scripts\\activate  
\# Mac/Linux  
source venv/bin/activate

### **3\. Install Dependencies**

Bash

pip install \-r requirements.txt

### **4\. Configure Environment**

Create a .env file in the root directory (based on .env.template):

Bash

cp .env.template .env

Update your .env with your local PostgreSQL credentials:

Ini, TOML

DEBUG\=True  
DJANGO\_SECRET\_KEY\=unsafe-secret-key-for-dev  
DB\_NAME\=hrms\_db  
DB\_USER\=postgres  
DB\_PASSWORD\=yourpassword  
DB\_HOST\=localhost  
DB\_PORT\=5432  
ALLOWED\_HOSTS\=localhost,127.0.0.1

### **5\. Run Migrations**

Bash

python manage.py makemigrations  
python manage.py migrate

### **6\. Create Superuser**

Bash

python manage.py createsuperuser

### **7\. Run Server**

Bash

python manage.py runserver

## ---

**📖 API Documentation**

Once the server is running, access the interactive API docs at:

* **Swagger UI:** [http://localhost:8000/api/schema/swagger-ui/](https://www.google.com/search?q=http://localhost:8000/api/schema/swagger-ui/&authuser=2)  
* **Redoc:** [http://localhost:8000/api/schema/redoc/](https://www.google.com/search?q=http://localhost:8000/api/schema/redoc/&authuser=2)

## ---

**🧪 Running Tests**

Run the comprehensive test suite to ensure system stability:

Bash

python manage.py test apps

## ---

**🔒 Security Best Practices**

1. **UUIDs for IDs:** Prevents ID enumeration attacks.  
2. **Environment Isolation:** Secrets are never hardcoded.  
3. **Strict Middleware:** Custom Audit Middleware validates authorization headers manually to ensure no action goes unlogged.

## ---
