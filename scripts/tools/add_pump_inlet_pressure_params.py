"""
为设备4, 5, 6添加pump_inlet_pressure参数
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings
from app.core.logging.setup import init_logging

def add_parameters():
    """为设备4, 5, 6添加pump_inlet_pressure参数"""
    
    print("=" * 80)
    print("为设备4, 5, 6添加pump_inlet_pressure参数")
    print("=" * 80)
    
    # 初始化应用
    print("\n[步骤1] 初始化应用")
    init_logging()
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    print("[OK] 应用初始化成功")
    
    # 参数配置
    params_to_add = [
        # 设备4
        (1, 4, 'pump_inlet_pressure', 'pump_inlet_pressure_method_b', 'L_offset', '2.5', 'float'),
        (1, 4, 'pump_inlet_pressure', 'pump_inlet_pressure_method_b', 'pipe_diameter', '0.3', 'float'),
        # 设备5
        (1, 5, 'pump_inlet_pressure', 'pump_inlet_pressure_method_b', 'L_offset', '2.5', 'float'),
        (1, 5, 'pump_inlet_pressure', 'pump_inlet_pressure_method_b', 'pipe_diameter', '0.3', 'float'),
        # 设备6
        (1, 6, 'pump_inlet_pressure', 'pump_inlet_pressure_method_b', 'L_offset', '2.5', 'float'),
        (1, 6, 'pump_inlet_pressure', 'pump_inlet_pressure_method_b', 'pipe_diameter', '0.3', 'float'),
    ]
    
    print("\n[步骤2] 插入参数")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 检查是否已存在
            cur.execute("""
                SELECT device_id, param_name 
                FROM calculation_parameters 
                WHERE device_id IN (4, 5, 6) 
                  AND metric_key = 'pump_inlet_pressure'
            """)
            existing = cur.fetchall()
            
            if existing:
                print(f"[警告] 发现已存在的参数: {existing}")
                print("[操作] 先删除已存在的参数")
                cur.execute("""
                    DELETE FROM calculation_parameters 
                    WHERE device_id IN (4, 5, 6) 
                      AND metric_key = 'pump_inlet_pressure'
                """)
                print(f"[OK] 删除了 {cur.rowcount} 条记录")
            
            # 插入新参数
            insert_sql = """
                INSERT INTO calculation_parameters (
                    station_id, device_id, metric_key, method_id, 
                    param_name, param_value, param_type, 
                    is_optimizable, confidence_score, updated_by
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, false, 0.5, 'system'
                )
            """
            
            for params in params_to_add:
                cur.execute(insert_sql, params)
                print(f"[OK] 设备{params[1]}: {params[4]} = {params[5]}")
            
            conn.commit()
    
    print("\n[步骤3] 验证插入结果")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    device_id,
                    COUNT(*) as param_count,
                    STRING_AGG(param_name || '=' || param_value, ', ' ORDER BY param_name) as params
                FROM calculation_parameters
                WHERE device_id IN (4, 5, 6)
                  AND metric_key = 'pump_inlet_pressure'
                GROUP BY device_id
                ORDER BY device_id
            """)
            
            results = cur.fetchall()
            
            print("\n验证结果:")
            for row in results:
                print(f"  设备{row[0]}: {row[1]}个参数 - {row[2]}")
    
    print("\n" + "=" * 80)
    print("✅ 参数添加完成！")
    print("=" * 80)

if __name__ == "__main__":
    add_parameters()

