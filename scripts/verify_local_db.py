import os
import psycopg2
import sys

def verify_db():
    # Use env to avoid committing credentials. e.g. DATABASE_URL or CDSS_DB_*.
    url = os.environ.get("DATABASE_URL")
    if url:
        try:
            conn = psycopg2.connect(url)
        except Exception as e:
            print(f"Verification failed: {e}")
            sys.exit(1)
    else:
        host = os.environ.get("CDSS_DB_HOST", "localhost")
        port = int(os.environ.get("CDSS_DB_PORT", "5433"))
        database = os.environ.get("CDSS_DB_NAME", "cdssdb")
        user = os.environ.get("CDSS_DB_USER", "postgres")
        password = os.environ.get("CDSS_DB_PASSWORD", "")
        if not password:
            print("Set DATABASE_URL or CDSS_DB_PASSWORD (and optional CDSS_DB_HOST, CDSS_DB_PORT, CDSS_DB_NAME, CDSS_DB_USER)")
            sys.exit(1)
        try:
            conn = psycopg2.connect(
                host=host,
                database=database,
                user=user,
                password=password,
                port=port
            )
        except Exception as e:
            print(f"Verification failed: {e}")
            sys.exit(1)
    try:
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        tables = [row[0] for row in cur.fetchall()]
        print(f"Tables in cdssdb: {', '.join(tables)}")
        
        cur.execute("SELECT COUNT(*) FROM patients")
        print(f"Patient count: {cur.fetchone()[0]}")
        
        cur.execute("SELECT COUNT(*) FROM inventory")
        print(f"Inventory count: {cur.fetchone()[0]}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Verification failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_db()
