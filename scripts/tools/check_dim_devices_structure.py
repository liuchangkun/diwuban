"""
检查 dim_devices 表结构
"""

from pathlib import Path
from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings

def check_dim_devices_structure():
    """检查 dim_devices 表结构"""
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # 检查表结构
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = 'public'
                AND table_name = 'dim_devices'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            
            print("=" * 80)
            print("dim_devices 表结构")
            print("=" * 80)
            for col_name, data_type, is_nullable in columns:
                nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
                print(f"  {col_name:20s} {data_type:20s} {nullable}")
            
            # 检查是否有 station_id 字段
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public'
                    AND table_name = 'dim_devices'
                    AND column_name = 'station_id'
                )
            """)
            has_station_id = cursor.fetchone()[0]
            print(f"\nstation_id 字段存在: {has_station_id}")
            
            # 查询示例数据
            cursor.execute("""
                SELECT id, station_id, name
                FROM dim_devices
                LIMIT 10
            """)
            rows = cursor.fetchall()
            print(f"\n示例数据 (前10条):")
            print(f"{'ID':>10s} {'Station ID':>12s} {'Device Name':30s}")
            print("-" * 80)
            for row in rows:
                print(f"{row[0]:>10d} {row[1]:>12d} {row[2]:30s}")

if __name__ == '__main__':
    check_dim_devices_structure()

