"""
验证指标计算结果

查询fact_measurements表，验证已计算指标的数据质量
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, get_connection, cleanup_database


def main():
    """主函数"""
    # 初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 查询各指标的记录数和时间范围
                sql = """
                SELECT
                    dmc.metric_key,
                    COUNT(*) as count,
                    MIN(fm.ts_raw) as min_time,
                    MAX(fm.ts_raw) as max_time,
                    COUNT(DISTINCT fm.device_id) as device_count
                FROM fact_measurements fm
                JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
                WHERE dmc.metric_key IN ('pump_flow_rate', 'pump_inlet_pressure', 'pump_head', 'pump_efficiency', 'pump_speed')
                  AND fm.ts_raw >= '2025-10-22 16:00:00'
                  AND fm.ts_raw <= '2025-10-23 17:00:00'
                GROUP BY dmc.metric_key
                ORDER BY dmc.metric_key
                """
                
                cur.execute(sql)
                results = cur.fetchall()
                
                print("\n" + "=" * 100)
                print("指标计算结果验证")
                print("=" * 100)
                print(f"{'指标名称':<30} | {'记录数':>10} | {'设备数':>6} | {'时间范围'}")
                print("-" * 100)
                
                total_records = 0
                for row in results:
                    metric_key, count, min_time, max_time, device_count = row
                    print(f"{metric_key:<30} | {count:>10,} | {device_count:>6} | {min_time} ~ {max_time}")
                    total_records += count
                
                print("-" * 100)
                print(f"{'总计':<30} | {total_records:>10,} |")
                print("=" * 100)
                
                # 查询各指标的数值范围
                print("\n" + "=" * 100)
                print("数值范围统计")
                print("=" * 100)

                sql_value_range = """
                SELECT
                    dmc.metric_key,
                    MIN(fm.value) as min_value,
                    MAX(fm.value) as max_value,
                    AVG(fm.value) as avg_value,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fm.value) as median_value
                FROM fact_measurements fm
                JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
                WHERE dmc.metric_key IN ('pump_flow_rate', 'pump_inlet_pressure', 'pump_head', 'pump_efficiency', 'pump_speed')
                  AND fm.ts_raw >= '2025-10-22 16:00:00'
                  AND fm.ts_raw <= '2025-10-23 17:00:00'
                GROUP BY dmc.metric_key
                ORDER BY dmc.metric_key
                """

                cur.execute(sql_value_range)
                value_results = cur.fetchall()

                print(f"{'指标名称':<30} | {'最小值':>12} | {'最大值':>12} | {'平均值':>12} | {'中位数':>12}")
                print("-" * 100)

                for row in value_results:
                    metric_key, min_val, max_val, avg_val, median_val = row
                    print(f"{metric_key:<30} | {float(min_val):>12.2f} | {float(max_val):>12.2f} | {float(avg_val):>12.2f} | {float(median_val):>12.2f}")

                print("=" * 100)
                
    finally:
        cleanup_database()


if __name__ == "__main__":
    main()

