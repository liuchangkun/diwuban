# -*- coding: utf-8 -*-
"""
检查硬编码常量分析脚本

分析数据库表结构和现有参数数据
"""
import psycopg
import yaml
from pathlib import Path

# 读取数据库配置
config_path = Path("configs/database.yaml")
with open(config_path, 'r', encoding='utf-8') as f:
    db_config = yaml.safe_load(f)

# 连接数据库
conn_str = f"host={db_config['host']} port={db_config['port']} dbname={db_config['dbname']} user={db_config['user']} password={db_config['password']}"

with psycopg.connect(conn_str) as conn:
    with conn.cursor() as cur:
        print("=" * 80)
        print("1. dim_devices 表结构")
        print("=" * 80)
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'dim_devices'
            ORDER BY ordinal_position
        """)
        for row in cur.fetchall():
            print(f"  {row[0]:<20} {row[1]:<30} NULL={row[2]}")
        
        print("\n" + "=" * 80)
        print("2. device_rated_params 表结构")
        print("=" * 80)
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'device_rated_params'
            ORDER BY ordinal_position
        """)
        for row in cur.fetchall():
            print(f"  {row[0]:<20} {row[1]:<30} NULL={row[2]}")
        
        print("\n" + "=" * 80)
        print("3. device_rated_params 数据示例")
        print("=" * 80)
        cur.execute("SELECT * FROM device_rated_params LIMIT 5")
        rows = cur.fetchall()
        if rows:
            for row in rows:
                print(f"  {row}")
        else:
            print("  ⚠️  表为空")
        
        print("\n" + "=" * 80)
        print("4. calculation_parameters 表结构")
        print("=" * 80)
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'calculation_parameters'
            ORDER BY ordinal_position
        """)
        for row in cur.fetchall():
            print(f"  {row[0]:<20} {row[1]:<30} NULL={row[2]}")
        
        print("\n" + "=" * 80)
        print("5. calculation_parameters 数据示例（全局参数）")
        print("=" * 80)
        cur.execute("""
            SELECT method_id, param_name, param_value, param_type
            FROM calculation_parameters
            WHERE device_id IS NULL AND station_id IS NULL
            LIMIT 10
        """)
        rows = cur.fetchall()
        if rows:
            for row in rows:
                print(f"  {row}")
        else:
            print("  ⚠️  无全局参数")
        
        print("\n" + "=" * 80)
        print("6. global_default_rated_params 表结构")
        print("=" * 80)
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'global_default_rated_params'
            ORDER BY ordinal_position
        """)
        rows = cur.fetchall()
        if rows:
            for row in rows:
                print(f"  {row[0]:<20} {row[1]:<30} NULL={row[2]}")
        else:
            print("  ⚠️  表不存在")
        
        print("\n" + "=" * 80)
        print("7. global_default_rated_params 数据")
        print("=" * 80)
        try:
            cur.execute("SELECT * FROM global_default_rated_params")
            rows = cur.fetchall()
            if rows:
                for row in rows:
                    print(f"  {row}")
            else:
                print("  ⚠️  表为空")
        except Exception as e:
            print(f"  ⚠️  查询失败: {e}")

print("\n✅ 分析完成")

