#!/usr/bin/env python3
"""
检查数据库视图数据
"""

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import make_dsn
from pathlib import Path
import psycopg

def check_database_view():
    """检查数据库视图中的数据"""
    print("🔍 检查数据库视图数据...")
    
    try:
        # 加载配置并连接数据库
        settings = load_settings(Path('configs'))
        dsn = make_dsn(settings)
        print(f"✅ 数据库连接信息: {dsn}")
        
        conn = psycopg.connect(dsn)
        cur = conn.cursor()
        
        # 检查视图中的记录数量
        cur.execute('SELECT COUNT(*) FROM v_fully_adaptive_data')
        count = cur.fetchone()[0]
        print(f"📊 v_fully_adaptive_data 视图中有 {count} 条记录")
        
        # 检查视图中的数据示例
        cur.execute('SELECT station_name, device_name, metric_key, value, unit FROM v_fully_adaptive_data LIMIT 5')
        rows = cur.fetchall()
        print("\n📋 v_fully_adaptive_data 视图数据示例:")
        for i, row in enumerate(rows, 1):
            print(f"  {i}. 站点: {row[0]}")
            print(f"     设备: {row[1]}")
            print(f"     指标: {row[2]}")
            print(f"     值: {row[3]}")
            print(f"     单位: {row[4]}")
            print()
        
        # 检查特定指标的数据
        print("🔍 检查流量和压力数据:")
        cur.execute("""
            SELECT station_name, device_name, metric_key, value, unit, timestamp 
            FROM v_fully_adaptive_data 
            WHERE metric_key IN ('main_pipeline_flow_rate', 'main_pipeline_outlet_pressure')
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        rows = cur.fetchall()
        for i, row in enumerate(rows, 1):
            print(f"  {i}. 时间: {row[5]}")
            print(f"     站点: {row[0]}, 设备: {row[1]}")
            print(f"     指标: {row[2]}, 值: {row[3]}, 单位: {row[4]}")
            print()
        
        # 检查泵站信息
        cur.execute('SELECT DISTINCT station_name FROM v_fully_adaptive_data LIMIT 5')
        stations = cur.fetchall()
        print("🏢 泵站信息:")
        for i, (station_name,) in enumerate(stations, 1):
            print(f"  {i}. {station_name}")
        
        cur.close()
        conn.close()
        print("✅ 数据库视图检查完成")
        
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database_view()