import os
import psycopg2
from psycopg2.extras import RealDictCursor

def check():
    url = os.environ.get("DATABASE_URL")
    if not url:
        pwd = os.environ.get("CDSS_DB_PASSWORD")
        if not pwd:
            print("Set DATABASE_URL or CDSS_DB_PASSWORD (do not commit credentials).")
            return
        url = f"postgresql://postgres:{pwd}@localhost:5433/cdssdb"
    conn = psycopg2.connect(url)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("SELECT count(*) FROM patients")
    count = cur.fetchone()['count']
    print(f"Total Patients in DB: {count}")
    
    cur.execute("SELECT full_name, patient_id FROM patients ORDER BY created_at DESC LIMIT 5")
    print("\nRecent 5 Patients:")
    for row in cur.fetchall():
        print(f"- {row['full_name']} (ID: {row['patient_id']})")
        
    cur.close()
    conn.close()

if __name__ == "__main__": check()
