import os
import sys
import time
import traceback
import subprocess

def sanitize_url(url):
    if not url:
        return 'None'
    import re
    return re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', str(url))

print("=== Starting Agro ERP Backend ===", flush=True)

# Diagnostic environment info
db_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
print(f"DATABASE_URL present: {bool(db_url)} ({sanitize_url(db_url)})", flush=True)
print(f"PORT: {os.environ.get('PORT', '8000')}", flush=True)
print(f"ALLOWED_HOSTS: {os.environ.get('ALLOWED_HOSTS', '*')}", flush=True)

try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    import django
    django.setup()

    from django.db import connection
    from django.db.utils import OperationalError

    db_name = connection.settings_dict.get('NAME')
    db_engine = connection.settings_dict.get('ENGINE')
    db_host = connection.settings_dict.get('HOST')
    db_port = connection.settings_dict.get('PORT')
    print(f"Configured database engine: {db_engine}, db: {db_name}, host: {db_host}:{db_port}", flush=True)

    # If using PostgreSQL or another network DB, poll until reachable
    if 'sqlite' not in str(db_engine).lower():
        connected = False
        for attempt in range(1, 31):
            try:
                connection.ensure_connection()
                print("Database connection established successfully!", flush=True)
                connected = True
                break
            except OperationalError as err:
                print(f"Waiting for database to be ready (attempt {attempt}/30): {err}", flush=True)
                time.sleep(2)
            except Exception as err:
                print(f"Unexpected error connecting to database (attempt {attempt}/30): {err}", flush=True)
                time.sleep(2)
        if not connected:
            raise RuntimeError("Database connection timed out after 60 seconds.")
    else:
        print("Using local SQLite database.", flush=True)

    # Run migrations
    print("Running database migrations (python manage.py migrate --noinput)...", flush=True)
    migrate_res = subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"])
    if migrate_res.returncode != 0:
        raise RuntimeError(f"Migrations failed with exit code {migrate_res.returncode}")

    # Collect static files
    print("Collecting static files (python manage.py collectstatic --noinput)...", flush=True)
    subprocess.run([sys.executable, "manage.py", "collectstatic", "--noinput"])

    # Launch Gunicorn
    port = os.environ.get('PORT', '8000')
    print(f"Starting Gunicorn server on 0.0.0.0:{port}...", flush=True)
    sys.stdout.flush()
    sys.stderr.flush()

    os.execvp(sys.executable, [
        sys.executable,
        "-m", "gunicorn",
        "core.wsgi:application",
        "--bind", f"0.0.0.0:{port}",
        "--workers", "3",
        "--timeout", "120"
    ])

except Exception as e:
    print(f"\nFATAL STARTUP ERROR: {e}", flush=True)
    traceback.print_exc()
    print("\nKeeping container alive for 300 seconds so you can inspect terminal / logs...", flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    time.sleep(300)
    sys.exit(1)
