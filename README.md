# ERP Agroindustrial - Backend

Backend API para el sistema ERP Agroindustrial, desarrollado con Django y Django REST Framework.

## Características

- API RESTful completa
- Autenticación con JWT
- Gestión de usuarios y permisos
- Módulos de trazabilidad, reportes e inventario
- Documentación de API con Swagger

## Requisitos

- Python 3.11+
- PostgreSQL

## Instalación

1. Clonar el repositorio
2. Crear un entorno virtual: `python -m venv venv`
3. Activar el entorno virtual:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Instalar dependencias: `pip install -r requirements.txt`
5. Configurar variables de entorno (ver sección de configuración)
6. Ejecutar migraciones: `python manage.py migrate`
7. Crear superusuario: `python manage.py createsuperuser`
8. Iniciar servidor: `python manage.py runserver`

## Configuración

El proyecto utiliza variables de entorno para la configuración. Puedes crear un archivo `.env` en la raíz del proyecto con las siguientes variables:

\`\`\`
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend-domain.com

DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_PORT=5432
\`\`\`

## Despliegue en Railway

1. Crear una cuenta en Railway (https://railway.app/)
2. Crear un nuevo proyecto
3. Agregar un servicio de PostgreSQL
4. Agregar un servicio de GitHub (conectar con el repositorio)
5. Configurar las variables de entorno en Railway
6. Railway detectará automáticamente el Procfile y desplegará la aplicación

## Endpoints de API

La documentación completa de la API está disponible en:

- `/swagger/` - Documentación Swagger UI
- `/redoc/` - Documentación ReDoc

### Principales endpoints:

- `/api/v1/auth/token/` - Obtener token JWT
- `/api/v1/auth/token/refresh/` - Refrescar token JWT
- `/api/v1/auth/users/` - Gestión de usuarios
- `/api/v1/reports/` - Gestión de reportes
- `/api/v1/trazabilidad/lotes/` - Gestión de lotes
- `/api/v1/inventory/products/` - Gestión de productos

## Licencia

Este proyecto es privado y confidencial.
