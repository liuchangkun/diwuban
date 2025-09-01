#!/usr/bin/env python3
"""
调试脚本：检查测量数据的实际分布
"""

import psycopg2
from datetime import datetime, timedelta
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config.loader_new import load_settings


def check_measurement_data():
    """检查测量数据分布"""

    settings = load_settings(Path("configs"))

    conn_config = {
        "host": settings.database.host,
        "port": settings.database.port,
        "database": settings.database.name,
        "user": settings.database.username,
        "password": settings.database.password,
    }

    try:
        with psycopg2.connect(**conn_config) as conn:
            with conn.cursor() as cur:
                print("🔍 检查数据库中的测量数据分布...")

                # 1. 检查operation_data表的总记录数
                cur.execute("SELECT COUNT(*) FROM operation_data")
                total_records = cur.fetchone()[0]
                print(f"📊 operation_data表总记录数: {total_records:,}")

                # 2. 检查时间范围
                cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM operation_data")
                min_time, max_time = cur.fetchone()
                print(f"⏰ 数据时间范围: {min_time} 到 {max_time}")

                # 3. 检查每个设备的记录数
                cur.execute(
                    """
                    SELECT device_id, device_name, COUNT(*) as record_count
                    FROM operation_data
                    GROUP BY device_id, device_name
                    ORDER BY record_count DESC
                """
                )
                devices = cur.fetchall()
                print("\n📱 各设备记录数分布:")
                for device_id, device_name, count in devices[:10]:  # 显示前10个
                    print(f"  设备 {device_id} ({device_name}): {count:,} 条记录")

                # 4. 检查最近24小时的数据
                yesterday = datetime.now() - timedelta(hours=24)
                cur.execute(
                    """
                    SELECT COUNT(*) FROM operation_data
                    WHERE timestamp >= %s
                """,
                    (yesterday,),
                )
                recent_count = cur.fetchone()[0]
                print(f"\n⏰ 最近24小时记录数: {recent_count:,}")

                # 5. 使用API相同的透视查询检查数据
                print("\n🔍 测试API透视查询...")
                test_query = """
                    SELECT
                        timestamp,
                        device_id,
                        device_name,
                        MAX(CASE WHEN metric_key = 'main_pipeline_flow_rate' THEN value END) as flow_rate,
                        MAX(CASE WHEN metric_key = 'main_pipeline_outlet_pressure' THEN value END) as pressure,
                        MAX(CASE WHEN metric_key = 'pump_active_power' THEN value END) as power,
                        MAX(CASE WHEN metric_key = 'pump_frequency' THEN value END) as frequency
                    FROM operation_data
                    WHERE timestamp >= %s
                    GROUP BY timestamp, device_id, device_name
                    ORDER BY timestamp DESC
                    LIMIT 10
                """

                cur.execute(test_query, (yesterday,))
                test_results = cur.fetchall()
                print(f"📊 透视查询结果数量: {len(test_results)}")

                if test_results:
                    print("📝 前几条透视查询结果:")
                    for i, row in enumerate(test_results[:5]):
                        (
                            timestamp,
                            device_id,
                            device_name,
                            flow_rate,
                            pressure,
                            power,
                            frequency,
                        ) = row
                        print(
                            f"  {i+1}. 时间: {timestamp}, 设备: {device_id}, 流量: {flow_rate}, 压力: {pressure}, 功率: {power}, 频率: {frequency}"
                        )

                # 6. 检查计数查询
                count_query = """
                    SELECT COUNT(*) FROM (
                        SELECT DISTINCT timestamp, device_id
                        FROM operation_data
                        WHERE timestamp >= %s
                    ) as grouped_data
                """
                cur.execute(count_query, (yesterday,))
                grouped_count = cur.fetchone()[0]
                print(f"\n📊 按时间戳和设备分组后的记录数: {grouped_count:,}")

                # 7. 检查不同metric_key的分布
                cur.execute(
                    """
                    SELECT metric_key, COUNT(*) as count
                    FROM operation_data
                    GROUP BY metric_key
                    ORDER BY count DESC
                """
                )
                metrics = cur.fetchall()
                print("\n📊 各metric_key分布:")
                for metric_key, count in metrics:
                    print(f"  {metric_key}: {count:,} 条记录")

                # 8. 测试当前API默认参数的查询
                print("\n🧪 测试API默认查询 (2025-02-28)...")
                api_start = datetime(2025, 2, 28, 0, 0, 0)
                api_end = datetime(2025, 2, 28, 23, 59, 59)

                api_test_query = """
                    SELECT
                        timestamp,
                        device_id,
                        device_name,
                        MAX(CASE WHEN metric_key = 'main_pipeline_flow_rate' THEN value END) as flow_rate,
                        MAX(CASE WHEN metric_key = 'main_pipeline_outlet_pressure' THEN value END) as pressure,
                        MAX(CASE WHEN metric_key = 'pump_active_power' THEN value END) as power,
                        MAX(CASE WHEN metric_key = 'pump_frequency' THEN value END) as frequency
                    FROM operation_data
                    WHERE timestamp BETWEEN %s AND %s
                    GROUP BY timestamp, device_id, device_name
                    ORDER BY timestamp DESC
                    LIMIT 20
                """

                cur.execute(api_test_query, (api_start, api_end))
                api_results = cur.fetchall()
                print(f"📊 API默认时间范围查询结果数: {len(api_results)}")

                # 计数查询
                api_count_query = """
                    SELECT COUNT(*) FROM (
                        SELECT DISTINCT timestamp, device_id
                        FROM operation_data
                        WHERE timestamp BETWEEN %s AND %s
                    ) as grouped_data
                """
                cur.execute(api_count_query, (api_start, api_end))
                api_total = cur.fetchone()[0]
                print(f"📊 API默认时间范围总记录数: {api_total:,}")

                if api_results:
                    print("📝 API默认查询结果示例:")
                    for i, row in enumerate(api_results[:5]):
                        (
                            timestamp,
                            device_id,
                            device_name,
                            flow_rate,
                            pressure,
                            power,
                            frequency,
                        ) = row
                        print(
                            f"  {i+1}. 时间: {timestamp}, 设备: {device_id}, 流量: {flow_rate}, 压力: {pressure}, 功率: {power}, 频率: {frequency}"
                        )

    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    check_measurement_data()
