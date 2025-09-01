#!/usr/bin/env python3
"""
检查数据库表结构和数据脚本
"""

import psycopg
from pathlib import Path
import sys
import os

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config.loader_new import load_settings

def check_database():
    """检查数据库表结构和数据"""
    print("🔍 检查数据库表结构和数据...")
    
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
                # 检查表是否存在
                print("\n📋 检查表结构:")
                cur.execute("""
                    SELECT table_name, table_type 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name
                """)
                tables = cur.fetchall()
                
                if not tables:
                    print("   ❌ 没有找到任何表")
                    return False
                
                for table_name, table_type in tables:
                    print(f"   ✅ {table_name} ({table_type})")
                
                # 检查关键表
                key_tables = ["station", "device", "operation_data", "fact_measurements"]
                existing_tables = [t[0] for t in tables]
                
                print("\n🎯 检查关键表:")
                for table in key_tables:
                    if table in existing_tables:
                        print(f"   ✅ {table} - 存在")
                        
                        # 检查数据量
                        try:
                            cur.execute(f"SELECT COUNT(*) FROM {table}")
                            count = cur.fetchone()[0]
                            print(f"      📊 记录数: {count:,}")
                            
                            if count > 0:
                                # 显示列结构
                                cur.execute(f"""
                                    SELECT column_name, data_type, is_nullable
                                    FROM information_schema.columns 
                                    WHERE table_name = '{table}' AND table_schema = 'public'
                                    ORDER BY ordinal_position
                                """)
                                columns = cur.fetchall()
                                print(f"      📝 列结构:")
                                for col_name, data_type, nullable in columns:
                                    null_info = "NULL" if nullable == "YES" else "NOT NULL"
                                    print(f"         - {col_name}: {data_type} ({null_info})")
                                
                                # 显示示例数据
                                if table in ["station", "device"]:
                                    cur.execute(f"SELECT * FROM {table} LIMIT 3")
                                    rows = cur.fetchall()
                                    if rows:
                                        print(f"      🔍 示例数据:")
                                        for i, row in enumerate(rows, 1):
                                            print(f"         {i}. {row}")
                        except Exception as e:
                            print(f"      ❌ 查询失败: {e}")
                    else:
                        print(f"   ❌ {table} - 不存在")
                
                # 检查视图
                print("\n👁️ 检查视图:")
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.views 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                views = cur.fetchall()
                
                if views:
                    for view_name, in views:
                        print(f"   ✅ {view_name} (视图)")
                else:
                    print("   ⚠️ 没有找到任何视图")
                
                # 测试API需要的查询
                print("\n🔧 测试API查询:")
                
                # 测试泵站查询
                try:
                    cur.execute("""
                        SELECT station_id, name, region, 'active' as status, 
                               COUNT(d.device_id) as device_count,
                               1000.0 as capacity, null as last_data_time
                        FROM station s
                        LEFT JOIN device d ON s.station_id = d.station_id
                        GROUP BY s.station_id, s.name, s.region
                        LIMIT 5
                    """)
                    stations = cur.fetchall()
                    print(f"   ✅ 泵站查询: 返回 {len(stations)} 个泵站")
                except Exception as e:
                    print(f"   ❌ 泵站查询失败: {e}")
                
                # 测试测量数据查询
                try:
                    cur.execute("""
                        SELECT timestamp, device_id, flow_rate, pressure, power, frequency
                        FROM operation_data
                        WHERE timestamp > NOW() - INTERVAL '24 hours'
                        LIMIT 5
                    """)
                    measurements = cur.fetchall()
                    print(f"   ✅ 测量数据查询: 返回 {len(measurements)} 条记录")
                    if measurements:
                        print("      🔍 示例数据:")
                        for row in measurements:
                            print(f"         {row}")
                except Exception as e:
                    print(f"   ❌ 测量数据查询失败: {e}")
                    
                    # 尝试查看是否有 fact_measurements 表
                    try:
                        cur.execute("SELECT COUNT(*) FROM fact_measurements")
                        count = cur.fetchone()[0]
                        print(f"   📊 fact_measurements 表有 {count:,} 条记录")
                        
                        if count > 0:
                            cur.execute("SELECT * FROM fact_measurements LIMIT 3")
                            rows = cur.fetchall()
                            print("   🔍 fact_measurements 示例数据:")
                            for row in rows:
                                print(f"      {row}")
                    except Exception as e2:
                        print(f"   ❌ fact_measurements 查询也失败: {e2}")
                
                return True
                
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

if __name__ == "__main__":
    success = check_database()
    if not success:
        sys.exit(1)