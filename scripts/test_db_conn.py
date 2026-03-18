import psycopg2
import sys
import os

def test_conn():
    try:
        # Prefer DATABASE_URL; else build from env (no hardcoded credentials)
        url = os.environ.get("DATABASE_URL")
        if url:
            conn = psycopg2.connect(url)
        else:
            host = os.environ.get("CDSS_DB_HOST", "localhost")
            port = int(os.environ.get("CDSS_DB_PORT", "5432"))
            dbname = os.environ.get("CDSS_DB_NAME", "cdssdb")
            user = os.environ.get("CDSS_DB_USER", "cdssadmin")
            password = os.environ.get("CDSS_DB_PASSWORD")
            if not password:
                print("Set DATABASE_URL or CDSS_DB_PASSWORD (and optional CDSS_DB_HOST, CDSS_DB_PORT, CDSS_DB_NAME, CDSS_DB_USER)")
                sys.exit(1)
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=dbname,
                user=user,
                password=password,
            )
        
        print("Connection successful!")
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_conn()
