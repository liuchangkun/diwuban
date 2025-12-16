"""检查正确的表名"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings

settings = load_settings(Path("configs"))
init_database(settings)

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public' 
              AND (table_name LIKE '%calculated%' OR table_name LIKE '%metric%')
            ORDER BY table_name
        """)
        
        print("相关表名:")
        for row in cur.fetchall():
            print(f"  - {row[0]}")

