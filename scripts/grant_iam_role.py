import os
import sqlalchemy

# Do not commit real passwords. Use DATABASE_URL or CDSS_DB_PASSWORD from env.
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    pwd = os.environ.get("CDSS_DB_PASSWORD")
    if not pwd:
        print("Set DATABASE_URL or CDSS_DB_PASSWORD (do not commit credentials).")
        exit(1)
    db_url = f"postgresql+psycopg2://cdssadmin:{pwd}@localhost:5433/cdssdb"

def grant_iam_role():
    print(f"Connecting (host from URL)...")
    try:
        engine = sqlalchemy.create_engine(db_url, connect_args={"connect_timeout": 3})
        with engine.connect() as conn:
            print("Connection successful! Executing: GRANT rds_iam TO cdssadmin;")
            conn.execute(sqlalchemy.text("GRANT rds_iam TO cdssadmin;"))
            conn.commit()
            print("Successfully granted rds_iam role to cdssadmin!")
    except Exception as e:
        print(f"Failed: {e}")
        exit(1)

if __name__ == "__main__":
    grant_iam_role()
