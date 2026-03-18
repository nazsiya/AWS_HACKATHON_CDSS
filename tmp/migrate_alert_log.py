
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'src'))
import boto3
import json
import os
import sys
from urllib.parse import quote_plus
from cdss.db.migrations.run import run

def main():
    try:
        sm = boto3.client("secretsmanager", region_name="ap-south-1")
        secret = sm.get_secret_value(SecretId="cdss-dev/rds-config")
        host = json.loads(secret["SecretString"])["host"]
        
        rds = boto3.client("rds", region_name="ap-south-1")
        token = rds.generate_db_auth_token(DBHostname=host, Port=5432, DBUsername="cdssadmin")
        
        os.environ["DATABASE_URL"] = f"postgresql+psycopg2://cdssadmin:{quote_plus(token)}@localhost:5433/cdssdb?sslmode=require"
        os.environ["PYTHONPATH"] = "src"
        
        print(f"Connecting to {host} via localhost:5433...")
        exit_code = run()
        sys.exit(exit_code)
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
