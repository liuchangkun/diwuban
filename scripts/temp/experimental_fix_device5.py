#!/usr/bin/env python3
"""
实验性验证脚本：强制修改运行状态并重新计算
目的：验证"运行状态阈值配置不准确"是否是设备5计算失败的根本原因
日期：2025-11-03
⚠️ 警告：此脚本会修改数据库数据，仅在测试环境中执行
"""

import psycopg
from datetime import datetime

# 数据库连接配置
DSN = "postgresql://postgres:q5707073@localhost:5432/pump_station_optimization"

def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60 + "\n")

def execute_query(conn, sql, params=None, fetch=True):
    """执行SQL查询"""
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        if fetch:
            return cur.fetchall()
        conn.commit()
        return None

def main():
    print_section("🔬 开始实验验证")
    print(f"开始时间: {datetime.now()}")
    
    # 连接数据库
    print("连接数据库...")
    conn = psycopg.connect(DSN)
    print("✅ 数据库连接成功\n")
    
    try:
        # ========================================
        # 第1步：备份当前数据
        # ========================================
        print_section("第1步：备份当前数据")
        
        # 1.1 创建备份表
        print("1.1 创建备份表...")
        execute_query(conn, "DROP TABLE IF EXISTS mv_device_running_1s_backup_20251103", fetch=False)
        execute_query(conn, """
            CREATE TABLE mv_device_running_1s_backup_20251103 AS
            SELECT * FROM mv_device_running_1s
            WHERE ts_bucket >= '2025-06-01 02:00:00+08'
              AND ts_bucket < '2025-06-01 04:00:00+08'
        """, fetch=False)
        
        # 验证备份
        result = execute_query(conn, "SELECT COUNT(*) FROM mv_device_running_1s_backup_20251103")
        backup_count = result[0][0]
        print(f"✅ 备份完成！备份了 {backup_count} 行数据\n")
        
        # 1.2 记录修改前的数据点数量
        print("1.2 记录修改前的数据点数量...")
        result = execute_query(conn, """
            SELECT 
                dmc.metric_key,
                COUNT(*) as current_count
            FROM fact_measurements fm
            JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
            WHERE fm.device_id = 5
              AND dmc.metric_key IN ('pump_flow_rate', 'pump_efficiency', 'pump_speed', 'pump_torque', 'pump_cumulative_flow')
              AND fm.ts_bucket >= '2025-06-01 02:00:00+08'
              AND fm.ts_bucket < '2025-06-01 04:00:00+08'
            GROUP BY dmc.metric_key
            ORDER BY dmc.metric_key
        """)
        
        print("修改前的数据点数量：")
        for row in result:
            print(f"  - {row[0]}: {row[1]} 个数据点")
        print()
        
        # ========================================
        # 第2步：强制修改运行状态
        # ========================================
        print_section("第2步：强制修改运行状态")
        
        # 2.1 将所有设备的运行状态改为1（运行中）
        print("2.1 将所有设备的运行状态改为1（运行中）...")
        execute_query(conn, """
            UPDATE mv_device_running_1s
            SET running = 1
            WHERE station_id = 1
              AND ts_bucket >= '2025-06-01 02:00:00+08'
              AND ts_bucket < '2025-06-01 04:00:00+08'
        """, fetch=False)
        print("✅ 运行状态已强制修改为1（运行中）\n")
        
        # 2.2 验证修改结果
        print("2.2 验证修改结果...")
        result = execute_query(conn, """
            SELECT 
                COUNT(*) as total_records,
                COUNT(*) FILTER (WHERE running = 1) as running_count,
                COUNT(*) FILTER (WHERE running = 0) as stopped_count
            FROM mv_device_running_1s
            WHERE device_id = 5
              AND ts_bucket >= '2025-06-01 02:00:00+08'
              AND ts_bucket < '2025-06-01 04:00:00+08'
        """)
        
        total, running, stopped = result[0]
        print(f"设备5的运行状态：")
        print(f"  - 总记录数: {total}")
        print(f"  - 运行中: {running}")
        print(f"  - 停机: {stopped}")
        
        if running == 7200 and stopped == 0:
            print("✅ 验证通过！所有记录都已标记为运行中\n")
        else:
            print("⚠️ 警告：运行状态修改可能不完整\n")
        
        # ========================================
        # 第3步：删除设备5的旧计算数据
        # ========================================
        print_section("第3步：删除设备5的旧计算数据")
        
        # 3.1 删除设备5的5个失败指标的数据
        print("3.1 删除设备5的5个失败指标的数据...")
        execute_query(conn, """
            DELETE FROM fact_measurements
            WHERE device_id = 5
              AND metric_id IN (
                SELECT id FROM dim_metric_config 
                WHERE metric_key IN ('pump_flow_rate', 'pump_efficiency', 'pump_speed', 'pump_torque', 'pump_cumulative_flow')
              )
              AND ts_bucket >= '2025-06-01 02:00:00+08'
              AND ts_bucket < '2025-06-01 04:00:00+08'
        """, fetch=False)
        print("✅ 旧数据已删除\n")
        
        # 3.2 验证删除结果
        print("3.2 验证删除结果...")
        result = execute_query(conn, """
            SELECT 
                dmc.metric_key,
                COUNT(*) as remaining_count
            FROM fact_measurements fm
            JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
            WHERE fm.device_id = 5
              AND dmc.metric_key IN ('pump_flow_rate', 'pump_efficiency', 'pump_speed', 'pump_torque', 'pump_cumulative_flow')
              AND fm.ts_bucket >= '2025-06-01 02:00:00+08'
              AND fm.ts_bucket < '2025-06-01 04:00:00+08'
            GROUP BY dmc.metric_key
        """)
        
        if len(result) == 0:
            print("✅ 验证通过！所有旧数据已删除\n")
        else:
            print("⚠️ 警告：仍有残留数据：")
            for row in result:
                print(f"  - {row[0]}: {row[1]} 个数据点")
            print()
        
        # ========================================
        # 完成
        # ========================================
        print_section("✅ 准备工作完成！")
        print("现在可以运行计算命令：")
        print("  python -m app.cli.main run-all configs/data_mapping.v2.json")
        print()
        print("验证修复效果的SQL查询：")
        print("""
  SELECT 
      dmc.metric_key,
      COUNT(*) as success_count,
      7200 as expected_count,
      ROUND(COUNT(*) * 100.0 / 7200, 2) as success_rate
  FROM fact_measurements fm
  JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
  WHERE fm.device_id = 5
    AND dmc.metric_key IN ('pump_flow_rate', 'pump_efficiency', 'pump_speed', 'pump_torque', 'pump_cumulative_flow')
    AND fm.ts_bucket >= '2025-06-01 02:00:00+08'
    AND fm.ts_bucket < '2025-06-01 04:00:00+08'
  GROUP BY dmc.metric_key
  ORDER BY dmc.metric_key;
        """)
        
    except Exception as e:
        print(f"\n❌ 错误：{e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        conn.close()
        print(f"\n结束时间: {datetime.now()}")
    
    return 0

if __name__ == "__main__":
    exit(main())

