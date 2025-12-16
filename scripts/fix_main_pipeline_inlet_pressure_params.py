"""
修复 main_pipeline_inlet_pressure 的 PIN_COEF_V1 参数配置错误

修复内容：
- b0: 从 101325.0 (Pa单位) 改为 0.101325 (MPa单位)
- b1: 从 1.0 (错误值) 改为 0.00981 (MPa/m单位)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib import Path
from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings

def main():
    print("\n" + "=" * 100)
    print("修复 main_pipeline_inlet_pressure 的 PIN_COEF_V1 参数配置")
    print("=" * 100 + "\n")
    
    # 初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 查询当前参数值
    print("步骤1: 查询当前参数值")
    print("-" * 100)
    
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, param_name, param_value
                FROM calculation_parameters
                WHERE metric_key = 'main_pipeline_inlet_pressure'
                    AND param_name IN ('b0', 'b1')
                ORDER BY param_name
            """)
            rows = cursor.fetchall()
            
            print(f"{'ID':<10} {'参数名':<10} {'当前值':<20}")
            print("-" * 100)
            for row in rows:
                print(f"{row[0]:<10} {row[1]:<10} {row[2]:<20}")
    
    # 执行修复
    print("\n步骤2: 执行参数修复")
    print("-" * 100)
    
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # 修复b0参数
            cursor.execute("""
                UPDATE calculation_parameters 
                SET param_value = 0.101325,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = 'system_fix_unit_error'
                WHERE metric_key = 'main_pipeline_inlet_pressure' 
                    AND param_name = 'b0'
            """)
            b0_updated = cursor.rowcount
            print(f"✅ b0参数已更新: {b0_updated} 行")
            
            # 修复b1参数
            cursor.execute("""
                UPDATE calculation_parameters 
                SET param_value = 0.00981,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = 'system_fix_unit_error'
                WHERE metric_key = 'main_pipeline_inlet_pressure' 
                    AND param_name = 'b1'
            """)
            b1_updated = cursor.rowcount
            print(f"✅ b1参数已更新: {b1_updated} 行")
            
            conn.commit()
    
    # 验证修复结果
    print("\n步骤3: 验证修复结果")
    print("-" * 100)
    
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, param_name, param_value, updated_by
                FROM calculation_parameters
                WHERE metric_key = 'main_pipeline_inlet_pressure'
                    AND param_name IN ('b0', 'b1')
                ORDER BY param_name
            """)
            rows = cursor.fetchall()
            
            print(f"{'ID':<10} {'参数名':<10} {'修复后值':<20} {'更新者':<30}")
            print("-" * 100)
            for row in rows:
                print(f"{row[0]:<10} {row[1]:<10} {row[2]:<20} {row[3]:<30}")
    
    print("\n" + "=" * 100)
    print("✅ 参数修复完成！")
    print("=" * 100 + "\n")

if __name__ == "__main__":
    main()

