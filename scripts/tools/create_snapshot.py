#!/usr/bin/env python3
"""创建项目快照数据"""

import datetime
import json
import psycopg


def create_snapshot():
    # 创建数据库快照信息
    snapshot_data = {
        "snapshot_code": "DIWUBAN_SNAPSHOT_20250822_064000",
        "timestamp": datetime.datetime.now().isoformat(),
        "database_state": {},
        "file_checksums": {},
    }

    try:
        # 获取数据库状态
        conn = psycopg.connect(
            "host=localhost dbname=pump_station_optimization user=postgres"
        )
        cur = conn.cursor()

        # 获取表行数
        tables = [
            "dim_stations",
            "dim_devices",
            "dim_metric_config",
            "fact_measurements",
            "staging_raw",
        ]
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            snapshot_data["database_state"][table] = count

        # 获取数据时间范围
        cur.execute(
            "SELECT MIN(ts_bucket), MAX(ts_bucket) FROM fact_measurements WHERE ts_bucket IS NOT NULL"
        )
        time_range = cur.fetchone()
        if time_range[0]:
            snapshot_data["database_state"]["data_time_range"] = {
                "min": time_range[0].isoformat(),
                "max": time_range[1].isoformat(),
            }

        conn.close()
        print("✅ 数据库状态记录完成")

    except Exception as e:
        print(f"⚠️  数据库状态记录失败: {e}")

    # 保存快照数据
    with open("snapshot_data_20250822_064000.json", "w", encoding="utf-8") as f:
        json.dump(snapshot_data, f, ensure_ascii=False, indent=2)

    print("📸 项目快照创建完成！")
    print(f'快照代码: {snapshot_data["snapshot_code"]}')
    print("快照文件: SNAPSHOT_20250822_064000.md")
    print("数据文件: snapshot_data_20250822_064000.json")

    return snapshot_data


if __name__ == "__main__":
    create_snapshot()
