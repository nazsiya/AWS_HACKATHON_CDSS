"""
One-time RDS IAM grant so Lambda can connect using IAM auth.
Run after tunnel is up and DATABASE_URL is set (or CDSS_DB_* env vars).
Uses password auth to connect, then runs: GRANT rds_iam TO <db_username>.
"""
import os
import sys

def main():
    try:
        import psycopg2
    except ImportError:
        print("pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)

    db_user = os.environ.get("TF_VAR_db_username") or os.environ.get("CDSS_DB_USER", "cdssadmin")
    url = os.environ.get("DATABASE_URL")
    if not url:
        host = os.environ.get("CDSS_DB_HOST", "localhost")
        port = int(os.environ.get("CDSS_DB_PORT", "5433"))
        dbname = os.environ.get("CDSS_DB_NAME", "cdssdb")
        password = os.environ.get("CDSS_DB_PASSWORD")
        if not password:
            print("Set DATABASE_URL or CDSS_DB_PASSWORD (and optional CDSS_DB_HOST, CDSS_DB_PORT, CDSS_DB_NAME, CDSS_DB_USER)", file=sys.stderr)
            sys.exit(1)
        url = f"postgresql://{db_user}:{password}@{host}:{port}/{dbname}"

    try:
        conn = psycopg2.connect(url)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("GRANT rds_iam TO %s", (db_user,))
        print(f"GRANT rds_iam TO {db_user} succeeded.")
        conn.close()
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
