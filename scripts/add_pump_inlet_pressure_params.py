#!/usr/bin/env python3
"""
为设备1-7添加 pump_inlet_pressure 所需的设备参数
"""
import psycopg2
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings

def main():
    # 加载配置
    config_path = project_root / 'config' / 'config.yaml'
    settings = load_settings(config_path)
    
    # 连接数据库
    conn = psycopg2.connect(
        host=settings.db.host,
        database=settings.db.name,
        user=settings.db.user,
        password=settings.db.password
    )
    
    try:
        cursor = conn.cursor()
        
        print("=" * 80)
        print("为设备1-7添加 pump_inlet_pressure 参数")
        print("=" * 80)
        
        # 为设备1-7添加 L_offset 和 pipe_diameter 参数
        params_to_insert = []
        for device_id in [1, 2, 3, 4, 5, 6, 7]:
            params_to_insert.extend([
                (1, device_id, 'pump_inlet_pressure', 'L_offset', 2.5, 'float', False),
                (1, device_id, 'pump_inlet_pressure', 'pipe_diameter', 0.3, 'float', False)
            ])
        
        cursor.executemany('''
            INSERT INTO calculation_parameters (
                station_id, device_id, metric_key, param_name, param_value, param_type, is_optimizable
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', params_to_insert)
        
        conn.commit()
        
        # 验证插入结果
        cursor.execute('''
            SELECT device_id, param_name, param_value
            FROM calculation_parameters
            WHERE metric_key = 'pump_inlet_pressure'
              AND device_id IN (1, 2, 3, 4, 5, 6, 7)
              AND param_name IN ('L_offset', 'pipe_diameter')
            ORDER BY device_id, param_name
        ''')
        
        print("\n✅ 参数插入成功！")
        print("\n验证结果：")
        for row in cursor.fetchall():
            print(f"  设备{row[0]}: {row[1]} = {row[2]}")
        
        cursor.close()
        
    finally:
        conn.close()

if __name__ == '__main__':
    main()

