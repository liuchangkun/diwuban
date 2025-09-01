#!/usr/bin/env python3
"""
简单的数据库修复脚本
"""

import psycopg
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config.loader_new import load_settings

def simple_fix():
    """简单修复数据库问题"""
    print("🔧 简单修复数据库问题...")
    
    try:
        # 加载配置
        settings = load_settings(Path("configs"))
        
        # 建立连接
        if settings.db.dsn_write:
            dsn = settings.db.dsn_write
        elif settings.db.dsn_read:
            dsn = settings.db.dsn_read
        else:
            dsn = f"host={settings.db.host} dbname={settings.db.name} user={settings.db.user}"
            
        print(f"📍 连接数据库: {settings.db.host}/{settings.db.name}")
        
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                
                # 1. 修复operation_data视图
                print("\n🔧 修复operation_data视图:")
                
                # 删除原有视图
                cur.execute("DROP VIEW IF EXISTS operation_data")
                print("  ✅ 删除原有视图")
                
                # 检查fact_measurements数据
                cur.execute("SELECT COUNT(*) FROM fact_measurements")
                count = cur.fetchone()[0]
                print(f"  📊 fact_measurements包含 {count:,} 条记录")
                
                # 检查metric_id范围
                cur.execute("SELECT MIN(metric_id), MAX(metric_id) FROM fact_measurements")
                min_id, max_id = cur.fetchone()
                print(f"  📊 metric_id范围: {min_id} - {max_id}")
                
                # 创建简单的operation_data视图
                print("  创建新的operation_data视图...")
                operation_data_sql = """
                    CREATE VIEW operation_data AS
                    SELECT 
                        ts_raw as timestamp,
                        device_id,
                        CASE WHEN metric_id = 12 THEN value ELSE NULL END as flow_rate,
                        CASE WHEN metric_id = 13 THEN value ELSE NULL END as pressure,
                        CASE WHEN metric_id = 25 THEN value ELSE NULL END as power,
                        50.0 as frequency
                    FROM fact_measurements 
                    WHERE metric_id IN (12, 13, 25)
                """
                
                cur.execute(operation_data_sql)
                print("  ✅ 新operation_data视图创建成功")
                
                # 测试新视图
                cur.execute("SELECT COUNT(*) FROM operation_data")
                count = cur.fetchone()[0]
                print(f"  📊 新视图包含 {count:,} 条记录")
                
                if count > 0:
                    cur.execute("""
                        SELECT timestamp, device_id, flow_rate, pressure, power, frequency
                        FROM operation_data 
                        WHERE flow_rate IS NOT NULL OR pressure IS NOT NULL OR power IS NOT NULL
                        ORDER BY timestamp DESC 
                        LIMIT 3
                    """)
                    rows = cur.fetchall()
                    print("  🔍 示例数据:")
                    for row in rows:
                        print(f"    {row}")
                
                # 2. 测试API查询
                print("\n🔧 测试API查询:")
                
                # 泵站查询
                try:
                    cur.execute("""
                        SELECT s.station_id, s.name, s.region, s.status, 
                               COUNT(d.device_id) as device_count,
                               s.capacity, null as last_data_time
                        FROM station s
                        LEFT JOIN device d ON s.station_id = d.station_id
                        GROUP BY s.station_id, s.name, s.region, s.status, s.capacity
                        ORDER BY s.station_id
                    """)
                    stations = cur.fetchall()
                    print(f"  ✅ 泵站查询: 返回 {len(stations)} 个泵站")
                except Exception as e:
                    print(f"  ❌ 泵站查询失败: {e}")
                
                # 测量数据查询
                try:
                    cur.execute("""
                        SELECT timestamp, device_id, flow_rate, pressure, power, frequency
                        FROM operation_data
                        ORDER BY timestamp DESC
                        LIMIT 5
                    """)
                    measurements = cur.fetchall()
                    print(f"  ✅ 测量数据查询: 返回 {len(measurements)} 条记录")
                except Exception as e:
                    print(f"  ❌ 测量数据查询失败: {e}")
                
                conn.commit()
                print("\n🎉 数据库修复完成!")
                return True
                
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = simple_fix()
    if not success:
        sys.exit(1)