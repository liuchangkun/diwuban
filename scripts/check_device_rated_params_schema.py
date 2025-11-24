"""检查 device_rated_params 表结构"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings

settings = load_settings(Path("configs"))
init_database(settings)

with get_connection() as conn:
    with conn.cursor() as cur:
        # 检查表结构
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'device_rated_params' 
            ORDER BY ordinal_position
        """)
        
        print("device_rated_params 表结构:")
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]}")
        
        # 查看数据示例
        cur.execute("SELECT * FROM device_rated_params LIMIT 5")
        print("\n数据示例:")
        print(cur.fetchall())

