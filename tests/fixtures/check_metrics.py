"""检查数据库中的指标数据"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings

settings = load_settings(Path("configs"))
init_database(settings)

with get_connection() as conn:
    with conn.cursor() as cur:
        # 检查device_id=1和7的指标数据
        cur.execute("""
            SELECT device_id, metric_id, COUNT(*) as cnt
            FROM fact_measurements
            WHERE device_id IN (1, 7)
            GROUP BY device_id, metric_id
            ORDER BY device_id, metric_id
        """)
        rows = cur.fetchall()
        
        print("=" * 60)
        print("Device ID | Metric ID | Count")
        print("=" * 60)
        for r in rows:
            print(f"{r[0]:9} | {r[1]:9} | {r[2]:10}")
        
        # 检查指标配置
        cur.execute("""
            SELECT id, metric_key
            FROM dim_metric_config
            WHERE id IN (1, 8, 12, 13, 14, 15, 17)
            ORDER BY id
        """)
        rows = cur.fetchall()

        print("\n" + "=" * 60)
        print("Metric ID | Metric Key")
        print("=" * 60)
        for r in rows:
            print(f"{r[0]:9} | {r[1]}")

        # 查找pump_head
        cur.execute("""
            SELECT id, metric_key
            FROM dim_metric_config
            WHERE metric_key LIKE '%head%'
            ORDER BY id
        """)
        rows = cur.fetchall()

        print("\n" + "=" * 60)
        print("Metrics containing 'head':")
        print("=" * 60)
        for r in rows:
            print(f"{r[0]:9} | {r[1]}")

