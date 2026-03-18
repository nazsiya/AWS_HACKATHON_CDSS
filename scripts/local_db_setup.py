import os
import subprocess
import time
import sys

def run_command(command, shell=True):
    """Executes a shell command and returns the output."""
    try:
        result = subprocess.run(command, shell=shell, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(e.stderr)
        return None

def is_container_running(name):
    """Checks if a Docker container is running."""
    output = run_command(f"docker ps -q -f name={name}")
    return bool(output)

def setup_db():
    container_name = "cdss-pg"
    password = os.environ.get("CDSS_DB_PASSWORD", os.environ.get("POSTGRES_PASSWORD", ""))
    if not password:
        print("Set CDSS_DB_PASSWORD or POSTGRES_PASSWORD for local Docker DB (do not commit).")
        sys.exit(1)
    port = os.environ.get("CDSS_DB_PORT", "5433")

    print(f"--- 1. Checking Docker Container: {container_name} ---")
    if not is_container_running(container_name):
        print(f"Starting new container: {container_name} on port {port}...")
        # Check if container exists but is stopped
        existing = run_command(f"docker ps -aq -f name={container_name}")
        if existing:
            run_command(f"docker start {container_name}")
        else:
            run_command(f"docker run --name {container_name} -e POSTGRES_PASSWORD={password} -p {port}:5432 -d postgres:15")
        
        print("Waiting for database to be ready (10s)...")
        time.sleep(10)
    else:
        print(f"Container {container_name} is already running.")

    print("\n--- 2. Installing psycopg2-binary ---")
    run_command(f"{sys.executable} -m pip install psycopg2-binary")

    import psycopg2
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            password=password,
            port=port
        )
        conn.autocommit = True
        cur = conn.cursor()

        # Drop cdssdb if it exists to ensure a clean state
        cur.execute("SELECT 1 FROM pg_database WHERE datname='cdssdb'")
        if cur.fetchone():
            print("Dropping existing database: cdssdb")
            # Force close other connections before dropping
            cur.execute("SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = 'cdssdb' AND pid <> pg_backend_pid();")
            cur.execute("DROP DATABASE cdssdb")
        
        print("Creating database: cdssdb")
        cur.execute("CREATE DATABASE cdssdb")
        
        conn.close()

        # Connect to cdssdb
        conn = psycopg2.connect(
            host="localhost",
            database="cdssdb",
            user="postgres",
            password=password,
            port=port
        )
        cur = conn.cursor()

        print("\n--- 3. Applying Schema (refined_schema.sql) ---")
        schema_path = os.path.join("backend", "database", "refined_schema.sql")
        with open(schema_path, 'r', encoding='utf-8') as f:
            cur.execute(f.read())
        print("Schema applied successfully.")

        print("\n--- 4. Seeding Data (seed_data.sql) ---")
        seed_path = os.path.join("backend", "database", "seed_data.sql")
        with open(seed_path, 'r', encoding='utf-8') as f:
            cur.execute(f.read())
        print("Seed data applied successfully.")

        conn.commit()
        cur.close()
        conn.close()
        print("\nSUCCESS: Local database is ready at localhost:5432")

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_db()
