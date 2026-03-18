from cdss.db.session import get_engine
from cdss.db.models import Base

def recreate():
    print("Recreating database schema (dropping and creating all tables)...")
    try:
        engine = get_engine()
        # Drop all tables in reverse order of dependencies
        Base.metadata.drop_all(bind=engine)
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("Success: Database schema recreated.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    recreate()
