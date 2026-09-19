# Agro ERP - Backend API

Robust, multi-tenant REST API backend for the **Agro ERP** agricultural processing and packing plant management system, built with **Django 5** and **Django REST Framework (DRF)**.

---

## 🏛️ Architecture Overview

The backend is engineered around a secure multi-tenant architecture designed to manage multiple agricultural packing plants (tenants), operational facilities, and central platform operations.

- **Framework**: Django 5.x & Django REST Framework (DRF)
- **Multi-Tenancy**: Data isolation across plants using scoped models linked to the `Tenant` entity.
- **Role Hierarchy & RBAC**:
  - `SUPERADMIN`: Platform-wide administrative authority across all plants and global configuration.
  - `ADMIN`: Plant-level administrator managing plant operations, users, and masters.
  - `OPERATOR`: Plant floor operator conducting day-to-day intake, weighing, and traceability.
- **Authentication & Security**: Stateless JWT authentication (`rest_framework_simplejwt`), strict scoped object permissions (`IsTenantUser`, `IsSuperAdminUser`), and CORS headers for secure Next.js frontend integration.
- **Domain Modules**:
  - **Tenants (`tenants/`)**: Plant registry, operational parameters, and tenant lifecycle.
  - **Users & Auth (`users/`)**: Custom user model, role assignment, JWT authentication endpoints, and tenant scoping.
  - **Traceability (`trazabilidad/`)**: Batch reception, processing lots, and agricultural lifecycle tracking.
  - **Reports & Intake (`reports/`)**: Real-time intake slips, net weight calculations, tare management, and reception records.
  - **Producers (`producers/`)**: Agricultural grower database, CLP certification codes, and field associations.
  - **Transport (`transporte/`)**: Carriers, drivers, vehicle license plates, and logistics dispatch.
  - **Inventory (`inventory/`)**: Finished goods, packaging materials, and warehouse stock tracking.

---

## 📋 System Requirements

- **Python**: `3.12+` (or compatible 3.11+)
- **Database**: PostgreSQL (production) or SQLite (development/local testing)
- **Git**

---

## 🚀 Getting Started

### 1. Clone & Navigate
```bash
git clone <repository-url>
cd backend
```

### 2. Virtual Environment Setup

Create and activate an isolated Python virtual environment:

**On Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the `backend/` root directory (see `.env.example` if available, or use the template below):

```env
SECRET_KEY=your-secure-django-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Optional PostgreSQL configuration (falls back to db.sqlite3 if omitted)
DB_NAME=agro_erp
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

### 5. Apply Database Migrations
Initialize database schemas:
```bash
python manage.py migrate
```

### 6. Seed Platform & Demo Data
Populate default tenants (e.g. Ica, Casma), roles, default admin accounts, and master data:
```bash
python manage.py seed_platform
```

> **Default Seeded Credentials:**
> - Superadmin: `superadmin` / `admin123`
> - Plant Admin (Ica): `admin_ica` / `admin123`
> - Operator: `operador_ica` / `operador123`

---

## 💻 Running the Development Server

Start the Django ASGI/WSGI development server listening on all local interfaces:

```bash
python manage.py runserver 0.0.0.0:8000
```

The API will be available at `http://localhost:8000`.

---

## 📖 API Documentation

Interactive Swagger and ReDoc documentation are enabled out of the box:

- **Swagger UI**: [http://localhost:8000/swagger/](http://localhost:8000/swagger/)
- **ReDoc UI**: [http://localhost:8000/redoc/](http://localhost:8000/redoc/)
- **OpenAPI JSON Schema**: [http://localhost:8000/swagger.json](http://localhost:8000/swagger.json)

### Core Endpoints

| Resource | Path | Description |
|---|---|---|
| **JWT Token** | `POST /api/v1/auth/token/` | Obtain access & refresh token pair |
| **JWT Refresh** | `POST /api/v1/auth/token/refresh/` | Refresh access token |
| **Current Profile** | `GET /api/v1/auth/users/me/` | Authenticated user profile & tenant |
| **Tenants** | `GET/POST /api/v1/tenants/` | Plant and tenant management |
| **Producers** | `GET/POST /api/v1/producers/` | Scoped agricultural producer records |
| **Transport** | `GET/POST /api/v1/transporte/` | Vehicles, drivers, and transport carriers |
| **Intake Reports** | `GET/POST /api/v1/reports/` | Weighing reports, intake tickets, and tare |
| **Traceability** | `GET/POST /api/v1/trazabilidad/` | Lot traceability and batch processing |
| **Inventory** | `GET/POST /api/v1/inventory/` | Product inventory and packaging items |

---

## 🧪 Automated Testing

Execute the automated test suite across all apps:

```bash
python manage.py test
```

To run tests for a specific module:
```bash
python manage.py test users
python manage.py test tenants
python manage.py test transporte
python manage.py test reports
```

---

## 🛡️ License & Confidentiality

Proprietary software. All rights reserved.
