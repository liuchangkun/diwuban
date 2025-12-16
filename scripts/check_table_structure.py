"""检查表结构"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, get_connection, cleanup_database


def main():
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 查看dim_metric_config表结构
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = 'dim_metric_config'
                    ORDER BY ordinal_position
                """)
                cols = cur.fetchall()
                print("\ndim_metric_config表结构:")
                for col in cols:
                    print(f"  {col[0]}: {col[1]}")
                
                # 查看fact_measurements表结构
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = 'fact_measurements'
                    ORDER BY ordinal_position
                """)
                cols = cur.fetchall()
                print("\nfact_measurements表结构:")
                for col in cols:
                    print(f"  {col[0]}: {col[1]}")
                
                # 查看pump_speed的metric_id
                cur.execute("""
                    SELECT id, metric_key, metric_name
                    FROM dim_metric_config
                    WHERE metric_key IN ('pump_flow_rate', 'pump_inlet_pressure', 'pump_head', 'pump_efficiency', 'pump_speed')
                    ORDER BY metric_key
                """)
                metrics = cur.fetchall()
                print("\n指标ID映射:")
                for metric in metrics:
                    print(f"  {metric[1]}: ID={metric[0]}, 名称={metric[2]}")
                
    finally:
        cleanup_database()


if __name__ == "__main__":
    main()

