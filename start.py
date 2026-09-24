import os
import sys
import time
import subprocess
import django

print("=== Starting Agro ERP Backend ===", flush=True)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
try:
    django.setup()
except Exception as e:
    print(f"Error during django.setup(): {e}", flush=True)
    sys.exit(1)

from django.db import connection
from django.db.utils import OperationalError

db_name = connection.settings_dict.get('NAME')
db_engine = connection.settings_dict.get('ENGINE')
print(f"Configured database engine: {db_engine} (database: {db_name})", flush=True)

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
        print("ERROR: Could not establish database connection after 60 seconds.", flush=True)
        sys.exit(1)
else:
    print("Using local SQLite database.", flush=True)

# Run migrations
print("Running database migrations (python manage.py migrate --noinput)...", flush=True)
migrate_res = subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"])
if migrate_res.returncode != 0:
    print(f"ERROR: Migrations failed with exit code {migrate_res.returncode}", flush=True)
    sys.exit(migrate_res.returncode)

# Collect static files
print("Collecting static files (python manage.py collectstatic --noinput)...", flush=True)
subprocess.run([sys.executable, "manage.py", "collectstatic", "--noinput"])

# Launch Gunicorn
port = os.environ.get('PORT', '8000')
print(f"Starting Gunicorn server on 0.0.0.0:{port}...", flush=True)
sys.stdout.flush()
sys.stderr.flush()

os.execvp("gunicorn", [
    "gunicorn",
    "core.wsgi:application",
    "--bind", f"0.0.0.0:{port}",
    "--workers", "3",
    "--timeout", "120"
])
