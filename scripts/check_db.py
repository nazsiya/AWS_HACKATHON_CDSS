import sys
import os

# Add src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from cdss.db.session import get_session
import sqlalchemy

def check_db():
    print("Connecting to Aurora database...")
    try:
        with get_session("cdss-dev/rds-config") as session:
            engine = session.get_bind()
            
            # Use inspector to get table names
            inspector = sqlalchemy.inspect(engine)
            tables = inspector.get_table_names()
            
            print(f"\nFound {len(tables)} tables:\n" + "-"*30)
            
            for table in tables:
                print(f"\n--- Table: {table} ---")
                try:
                    result = session.execute(sqlalchemy.text(f"SELECT * FROM {table} LIMIT 5"))
                    rows = result.fetchall()
                    if not rows:
                        print("  (Empty table)")
                    else:
                        for row in rows:
                            print(f"  {row}")
                    
                    # Also get the total count
                    count_result = session.execute(sqlalchemy.text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_result.scalar()
                    print(f"  Total records: {count}")
                except Exception as e:
                    print(f"  Error querying table: {e}")
                    
    except Exception as e:
        print(f"Failed to connect or query database: {e}")

if __name__ == "__main__":
    check_db()
