"""
添加 DataFilter 参数到数据库
移除硬编码，将 max_flow_rate 和 max_liquid_level 存储到 calculation_parameters 表
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings
from pathlib import Path

def main():
    # 初始化数据库连接池
    config_dir = Path(__file__).parent.parent / 'config'
    settings = load_settings(config_dir)
    init_database(settings)
    
    print("=" * 80)
    print("添加 DataFilter 参数到数据库")
    print("=" * 80)
    
    # 要添加的参数
    parameters = [
        {
            'metric_key': 'pump_inlet_pressure',
            'method_id': 'pump_inlet_pressure_method_b',
            'param_name': 'max_liquid_level',
            'param_value': 10.0,
            'param_type': 'float',
            'description': 'DataFilter 液位上限（m）'
        },
        {
            'metric_key': 'pump_inlet_pressure',
            'method_id': 'pump_inlet_pressure_method_b',
            'param_name': 'max_flow_rate',
            'param_value': 3000.0,
            'param_type': 'float',
            'description': 'DataFilter 流量上限（m³/h）'
        }
    ]
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        for param in parameters:
            # 检查参数是否已存在
            cursor.execute("""
                SELECT id, param_value 
                FROM calculation_parameters
                WHERE metric_key = %s
                    AND method_id = %s
                    AND param_name = %s
                    AND station_id IS NULL
                    AND device_id IS NULL
            """, (param['metric_key'], param['method_id'], param['param_name']))
            
            existing = cursor.fetchone()
            
            if existing:
                print(f"\n✅ 参数已存在: {param['param_name']}")
                print(f"   - 当前值: {existing[1]}")
                print(f"   - 建议值: {param['param_value']}")
                
                if float(existing[1]) != param['param_value']:
                    print(f"   ⚠️ 值不一致，是否需要更新？")
            else:
                # 插入新参数
                cursor.execute("""
                    INSERT INTO calculation_parameters 
                        (station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable)
                    VALUES
                        (NULL, NULL, %s, %s, %s, %s, %s, false)
                    RETURNING id
                """, (
                    param['metric_key'],
                    param['method_id'],
                    param['param_name'],
                    param['param_value'],
                    param['param_type']
                ))
                
                new_id = cursor.fetchone()[0]
                print(f"\n✅ 已添加参数: {param['param_name']}")
                print(f"   - ID: {new_id}")
                print(f"   - 值: {param['param_value']}")
                print(f"   - 说明: {param['description']}")
        
        conn.commit()
        cursor.close()
    
    print("\n" + "=" * 80)
    print("✅ 参数添加完成！")
    print("=" * 80)

if __name__ == '__main__':
    main()

