import sys
from pathlib import Path
from sqlalchemy import inspect

# Add src to path
root = Path(__file__).resolve().parent.parent
src = root / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from cdss.db.session import get_engine

def list_tables():
    print("Inspecting Aurora database schema via SSH tunnel (localhost:5433)...")
    try:
        engine = get_engine()
        inspector = inspect(engine)
        
        tables = inspector.get_table_names()
        print(f"\nFound {len(tables)} tables:\n")
        
        for table_name in sorted(tables):
            print(f"Table: {table_name}")
            columns = inspector.get_columns(table_name)
            for column in columns:
                pk = " (PK)" if column.get('primary_key') else ""
                nullable = "" if column.get('nullable') else " NOT NULL"
                print(f"  - {column['name']}: {column['type']}{pk}{nullable}")
            print("-" * 30)
            
    except Exception as e:
        print(f"Error inspecting database: {e}")
        print("\nEnsure the SSH tunnel is running in another terminal:")
        print("powershell -ExecutionPolicy Bypass -File scripts\\start_ssh_tunnel.ps1")

if __name__ == "__main__":
    list_tables()
