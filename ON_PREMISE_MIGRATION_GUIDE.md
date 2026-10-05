# Guía de Migración: De Homelab (Coolify) a PC Local On-Premise (Windows + WSL2)

Esta guía documenta el procedimiento completo para migrar el backend de producción de Agro ERP desde una instancia Cloud/Homelab (Coolify) hacia una computadora física con Windows en las instalaciones de la empresa cliente, garantizando **cero pérdida de datos históricos** y **alta disponibilidad local**.

---

## 1. Arquitectura Objetivo

* **Sistema Operativo Base:** Windows 10/11 Pro (PC de Planta / Oficina).
* **Motor de Contenedores:** Docker Desktop con backend **WSL2** (Ubuntu).
* **Base de Datos:** PostgreSQL 16 (contenedor oficial con volumen persistente en Linux).
* **Backend:** Django 5 + Gunicorn (contenedor oficial en puerto 8000).
* **Conectividad Externa / Red:** **Cloudflare Tunnel (`cloudflared`)** con SSL automático (permite que el Frontend en la nube o usuarios remotos accedan a la API sin abrir puertos en el router y sorteando CGNAT / IPs dinámicas).
* **Continuidad / Backups:** Tarea programada en cron para volcado diario comprimido (`pg_dump`) y sincronización a almacenamiento externo.

---

## 2. Preparación de la Computadora (Windows Host)

### A. Estabilidad Eléctrica y Energía
1. **UPS / Estabilizador:** Asegurar que la PC esté conectada a un SAI/UPS para evitar corrupción de la base de datos por cortes de luz en planta.
2. **Opciones de Energía de Windows:**
   * Ir a *Panel de Control > Opciones de Energía*.
   * Configurar: **Suspender el equipo: NUNCA**.
   * En configuración avanzada: **Apagar disco duro: NUNCA**.

### B. Instalación de WSL2
Abrir **PowerShell como Administrador** y ejecutar:
```powershell
wsl --install -d Ubuntu-24.04
```
*(Reiniciar la computadora si el instalador lo solicita).*

### C. Limitar Recursos de WSL2 (Crítico para que la PC no se congele)
Crear el archivo `C:\Users\<TuUsuario>\.wslconfig` con un editor de texto:
```ini
[wsl2]
memory=4GB
processors=2
swap=2GB
```
*(Ajustar según la RAM física de la máquina: si tiene 16 GB, asignar 4GB o 6GB a WSL2).*

### D. Instalación de Docker Desktop
1. Descargar e instalar [Docker Desktop para Windows](https://www.docker.com/products/docker-desktop/).
2. Durante la instalación, verificar que esté activada la casilla: **"Use the WSL 2 based engine"**.
3. Abrir Docker Desktop y en **Settings > General**:
   * Marcar: **"Start Docker Desktop when you log in"**.
4. En **Settings > Resources > WSL Integration**:
   * Asegurar que la distribución `Ubuntu` esté habilitada.

---

## 3. Despliegue del Proyecto en WSL2

> [!CAUTION]
> **REGLA DE RENDIMIENTO I/O EN WSL2:**  
> El repositorio y los volúmenes de Docker deben clonarse **SIEMPRE dentro del sistema de archivos nativo de Linux** (ej. `/home/<usuario>/...`).  
> **NUNCA** clones ni corras la base de datos dentro de `/mnt/c/...`, ya que el puente de archivos entre Windows y Linux degrada el rendimiento de disco hasta un 90%.

Abrir la terminal de **Ubuntu (WSL2)**:

```bash
# 1. Ir al home nativo de Linux
cd ~

# 2. Clonar el repositorio del backend
git clone https://github.com/andres-ecr/agro-backend.git
cd agro-backend

# 3. Crear el archivo de variables de entorno (.env.prod)
cat << 'EOF' > .env.prod
DEBUG=False
SECRET_KEY=cambiar_por_una_clave_secreta_larga_y_segura_2026
ALLOWED_HOSTS=*
DATABASE_URL=postgres://agro_user:ClaveSeguraProd2026@db:5432/agro_db
EOF
```

### Docker Compose de Producción (`docker-compose.yml`)
Verificar o crear el archivo `docker-compose.yml` en la raíz del repositorio:

```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: agro_prod_db
    restart: always
    environment:
      POSTGRES_DB: agro_db
      POSTGRES_USER: agro_user
      POSTGRES_PASSWORD: ClaveSeguraProd2026
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5432:5432"

  backend:
    build: .
    container_name: agro_prod_backend
    restart: always
    depends_on:
      - db
    env_file:
      - .env.prod
    ports:
      - "8000:8000"
    command: >
      sh -c "python manage.py migrate &&
             gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120"

volumes:
  postgres_data:
```

---

## 4. Protocolo de Extracción y Migración de Datos (Día del Pase)

Sigue estos pasos en orden para asegurar una migración sin inconsistencias.

### Paso 4.1: Ventana de Mantenimiento (Freeze en Homelab/Coolify)
1. Notificar a los administradores de planta que el sistema estará en mantenimiento durante 15–30 minutos.
2. En Coolify, detener o pausar temporalmente el contenedor del backend para evitar que entren nuevos pesajes durante el volcado.

### Paso 4.2: Exportar el Dump de Base de Datos
Desde el servidor Homelab / Coolify:

**Si usas PostgreSQL en Coolify:**
```bash
# Entrar al servidor de Coolify por SSH y ejecutar el dump comprimido
docker exec -t <nombre_contenedor_postgres_coolify> pg_dump -U <usuario_db> -d <nombre_db> -F c -b -v -f /tmp/backup_agro_prod.dump

# Copiar el archivo generado fuera del contenedor
docker cp <nombre_contenedor_postgres_coolify>:/tmp/backup_agro_prod.dump ./backup_agro_prod.dump
```

*(Si usabas SQLite en Coolify, simplemente descarga una copia directa de `db.sqlite3`).*

### Paso 4.3: Transferir el Archivo a la PC de Destino
Copiar `backup_agro_prod.dump` a la PC con Windows (mediante `scp`, Google Drive, o memoria USB) y moverlo al entorno WSL:
```bash
# Copiar desde la carpeta de Descargas de Windows al directorio de WSL2:
cp /mnt/c/Users/<TuUsuario>/Downloads/backup_agro_prod.dump ~/agro-backend/
```

### Paso 4.4: Importar los Datos en el nuevo PostgreSQL Local
En la terminal de WSL2:
```bash
cd ~/agro-backend

# 1. Iniciar únicamente el servicio de base de datos
docker compose up -d db

# Esperar 5-10 segundos a que PostgreSQL inicialice

# 2. Restaurar el dump completo
docker compose exec -T db pg_restore -U agro_user -d agro_db --clean --no-owner -v < backup_agro_prod.dump

# 3. Iniciar el backend
docker compose up -d backend

# 4. Verificar migraciones y consistencia
docker compose exec backend python manage.py showmigrations
docker compose exec backend python manage.py check
```

---

## 5. Exposición a Internet y Conexión con Frontend (Cloudflare Tunnel)

Dado que la PC estará en una red local con IP dinámica o CGNAT:

1. **Crear Túnel en Cloudflare Zero Trust:**
   * Ir a [one.dash.cloudflare.com](https://one.dash.cloudflare.com) > *Networks > Tunnels*.
   * Crear un nuevo túnel: `agro-planta-prod`.
2. **Instalar el conector `cloudflared` en Windows o en Docker:**
   * Opción Docker (recomendada): Agregar el servicio al `docker-compose.yml`:
     ```yaml
     tunnel:
       image: cloudflare/cloudflared:latest
       container_name: agro_tunnel
       restart: always
       command: tunnel run --token TU_TOKEN_DE_CLOUDFLARE_AQUI
     ```
3. **Enrutar el subdominio:**
   * En la configuración del túnel en Cloudflare, agregar Public Hostname:
     * **Subdominio:** `api.sobifruits.com` (o el dominio configurado).
     * **Servicio:** `HTTP` -> `backend:8000` (o `http://localhost:8000` si corre en el host).
4. **Actualizar el Frontend:**
   * En Vercel / Coolify donde resida el frontend, actualizar:
     ```env
     NEXT_PUBLIC_API_URL=https://api.sobifruits.com
     ```
   * Redesplegar el Frontend.

---

## 6. Política de Backups Automáticos (Disaster Recovery)

Dado que la base de datos estará en un disco local físico de oficina, es indispensable programar copias de seguridad automáticas.

Crear el script de respaldo en WSL2: `~/backup_db.sh`:
```bash
#!/bin/bash
FECHA=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/home/$USER/backups_agro"
mkdir -p "$BACKUP_DIR"

ARCHIVO="$BACKUP_DIR/agro_backup_$FECHA.dump"

# Generar dump comprimido
docker compose -f /home/$USER/agro-backend/docker-compose.yml exec -T db pg_dump -U agro_user -d agro_db -F c > "$ARCHIVO"

# Eliminar backups locales de más de 15 días
find "$BACKUP_DIR" -type f -name "*.dump" -mtime +15 -delete

# (Recomendado) Sincronizar con Google Drive o AWS S3 vía rclone:
# rclone copy "$BACKUP_DIR" gdrive:BackupsAgro/
```

Hacer ejecutable el script y programarlo en el cron:
```bash
chmod +x ~/backup_db.sh
crontab -e
```
Agregar la siguiente línea para ejecutarlo todas las noches a las 11:30 PM:
```cron
30 23 * * * /home/usuario/backup_db.sh >> /home/usuario/backup.log 2>&1
```

---

## 7. Checklist de Verificación Final Post-Migración

- [ ] Contenedores `agro_prod_db` y `agro_prod_backend` en estado `Up` (`docker compose ps`).
- [ ] Endpoint de salud responde HTTP 200: `curl http://localhost:8000/api/v1/tenants/`.
- [ ] Subdominio público HTTPS accesible vía navegador o Postman: `https://api.sobifruits.com/api/v1/tenants/`.
- [ ] Iniciar sesión desde el Frontend con credenciales oficiales de [`CREDENTIALS.md`](file:///D:/backup/trabajo/personal%20projects/Alchlab/Proyectos/agro/erp-base/CREDENTIALS.md).
- [ ] Verificar que los reportes de pesaje y catálogos previos a la migración se visualicen íntegros en pantalla.
- [ ] Probar una pesada de prueba con la balanza y el conector `electron-new` (puerto 8080) registrando un pesaje en el nuevo backend.
- [ ] Reiniciar la PC con Windows y comprobar que Docker levante automáticamente los contenedores sin intervención manual.
