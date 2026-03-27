import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL')
engine = create_engine(db_url)

with engine.connect() as conn:
    query = text('SELECT id, image_path, detection_date FROM plant_detections ORDER BY detection_date DESC LIMIT 20')
    result = conn.execute(query)
    print(f"{'ID':<15} | {'Date':<20} | {'Image Path':<50} | {'Exists'}")
    print("-" * 100)
    for row in result:
        path = row[1] if row[1] else ""
        exists = os.path.exists(path) if path else False
        print(f"{row[0][:12]:<15} | {str(row[2]):<20} | {path:<50} | {exists}")
