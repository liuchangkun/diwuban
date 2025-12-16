"""查找包含metric的表名"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.logging.setup import init_logging
from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, get_connection

init_logging(project_root / 'configs')
settings = load_settings(project_root / 'configs')
init_database(settings)

# 查询所有表名
query = """
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name LIKE '%metric%'
ORDER BY table_name;
"""

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(query)
        results = cur.fetchall()
        print('包含metric的表名：')
        for row in results:
            print(f'  - {row[0]}')

