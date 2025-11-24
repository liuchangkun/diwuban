"""检查pool_liquid_level数据"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.adapters.db import init_database, get_connection, cleanup_database
from app.core.config.loader_new import load_settings

settings = load_settings(Path('configs'))
init_database(settings)

with get_connection() as conn:
    with conn.cursor() as cur:
        # 检查pool_liquid_level的metric_id
        cur.execute("""
        SELECT id, metric_key FROM dim_metric_config WHERE metric_key='pool_liquid_level'
        """)
        row = cur.fetchone()
        print(f'pool_liquid_level metric_id: {row}')

        # 检查pool_liquid_level数据
        cur.execute("""
        SELECT COUNT(*), MIN(ts_bucket), MAX(ts_bucket)
        FROM fact_measurements
        WHERE metric_id=5 AND device_id=8
        """)
        row = cur.fetchone()
        print(f'pool_liquid_level (metric_id=5, device_id=8): {row[0]} records, {row[1]} ~ {row[2]}')

        # 检查设备8的所有指标
        cur.execute("""
        SELECT mc.metric_key, COUNT(*), MIN(fm.ts_bucket), MAX(fm.ts_bucket)
        FROM fact_measurements fm
        JOIN dim_metric_config mc ON mc.id = fm.metric_id
        WHERE fm.device_id = 8
        GROUP BY mc.metric_key
        ORDER BY mc.metric_key
        """)
        rows = cur.fetchall()
        print(f'\n设备8的所有指标:')
        for row in rows:
            print(f'  {row[0]}: {row[1]} records, {row[2]} ~ {row[3]}')

        # 检查所有设备的pool_liquid_level
        cur.execute("""
        SELECT fm.device_id, COUNT(*), MIN(fm.ts_bucket), MAX(fm.ts_bucket)
        FROM fact_measurements fm
        WHERE fm.metric_id = 5
        GROUP BY fm.device_id
        ORDER BY fm.device_id
        """)
        rows = cur.fetchall()
        print(f'\n所有设备的pool_liquid_level (metric_id=5):')
        for row in rows:
            print(f'  设备{row[0]}: {row[1]} records, {row[2]} ~ {row[3]}')

cleanup_database()

