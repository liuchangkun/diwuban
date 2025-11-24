"""验证main_pipeline_inlet_pressure计算结果"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, get_connection, cleanup_database
from app.core.logging.setup import init_logging

def main():
    # 初始化配置
    settings = load_settings(Path("configs"))
    init_logging(Path("configs"))
    init_database(settings)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询main_pipeline_inlet_pressure数据
            cur.execute("""
                SELECT
                    COUNT(*) as count,
                    MIN(value) as min_value,
                    MAX(value) as max_value,
                    AVG(value) as avg_value,
                    MIN(ts_bucket) as min_time,
                    MAX(ts_bucket) as max_time
                FROM fact_measurements
                WHERE metric_id = 61 AND device_id = 7
            """)

            row = cur.fetchone()

            print("=" * 80)
            print("main_pipeline_inlet_pressure 数据验证")
            print("=" * 80)
            print(f"记录数: {row[0]}")
            print(f"数值范围: {row[1]:.4f} ~ {row[2]:.4f} MPa")
            print(f"平均值: {row[3]:.4f} MPa")
            print(f"时间范围: {row[4]} ~ {row[5]}")
            print("=" * 80)

    cleanup_database()

if __name__ == "__main__":
    main()

