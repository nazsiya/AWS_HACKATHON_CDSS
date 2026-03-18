import psycopg2
import sys
import os

def test_conn(dbname):
    print(f"Testing connection to {dbname}...")
    try:
        url = os.environ.get("DATABASE_URL")
        if url:
            # Use URL but override database name for this test
            from urllib.parse import urlparse, urlunparse
            parsed = list(urlparse(url))
            # path is like /cdssdb -> replace with /{dbname}
            parsed[2] = "/" + dbname
            conn_url = urlunparse(parsed)
            conn = psycopg2.connect(conn_url, connect_timeout=5)
        else:
            host = os.environ.get("CDSS_DB_HOST", "127.0.0.1")
            port = int(os.environ.get("CDSS_DB_PORT", "5433"))
            user = os.environ.get("CDSS_DB_USER", "cdssadmin")
            password = os.environ.get("CDSS_DB_PASSWORD")
            if not password:
                print("Set DATABASE_URL or CDSS_DB_PASSWORD")
                return False
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=dbname,
                user=user,
                password=password,
                connect_timeout=5,
            )
        print(f"Connection to {dbname} successful!")
        conn.close()
        return True
    except Exception as e:
        print(f"Connection to {dbname} failed: {e}")
        return False

if __name__ == "__main__":
    s1 = test_conn("postgres")
    s2 = test_conn("cdssdb")
    if not (s1 or s2):
        sys.exit(1)
