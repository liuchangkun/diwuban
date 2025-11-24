"""
修正 pump_inlet_pressure 参数配置

更新内容:
1. pipe_diameter: 0.3 → 0.6 (设备1-6)
2. L_offset: 12.0 → 2.25 (设备1-6)
3. K_eq: 3.0 → 0.65 (全局参数)

执行方式:
    python scripts/fix_pump_inlet_pressure_params_20251119.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db.gateway import get_conn
from app.core.config.loader import load_settings

def main():
    """更新参数配置"""
    print("=" * 100)
    print("开始更新 pump_inlet_pressure 参数配置")
    print("=" * 100)
    
    # 加载配置
    settings = load_settings(Path("configs"))
    
    # 执行更新
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            try:
                # 1. 更新 pipe_diameter (0.3 → 0.6)
                print("\n[1/3] 更新 pipe_diameter: 0.3 → 0.6 (设备1-6)")
                cur.execute("""
                    UPDATE calculation_parameters
                    SET 
                        param_value = %s,
                        updated_at = NOW(),
                        updated_by = %s
                    WHERE 
                        metric_key = %s
                        AND param_name = %s
                        AND device_id = ANY(%s)
                """, ('0.6', 'fix_pump_inlet_pressure_20251119', 'pump_inlet_pressure', 'pipe_diameter', [1, 2, 3, 4, 5, 6]))
                
                updated_count = cur.rowcount
                print(f"   ✓ 更新完成: {updated_count} 个设备")
                
                if updated_count != 6:
                    raise Exception(f"pipe_diameter 更新失败: 期望6个，实际{updated_count}个")
                
                # 2. 更新 L_offset (12.0 → 2.25)
                print("\n[2/3] 更新 L_offset: 12.0 → 2.25 (设备1-6)")
                cur.execute("""
                    UPDATE calculation_parameters
                    SET 
                        param_value = %s,
                        updated_at = NOW(),
                        updated_by = %s
                    WHERE 
                        metric_key = %s
                        AND param_name = %s
                        AND device_id = ANY(%s)
                """, ('2.25', 'fix_pump_inlet_pressure_20251119', 'pump_inlet_pressure', 'L_offset', [1, 2, 3, 4, 5, 6]))
                
                updated_count = cur.rowcount
                print(f"   ✓ 更新完成: {updated_count} 个设备")
                
                if updated_count != 6:
                    raise Exception(f"L_offset 更新失败: 期望6个，实际{updated_count}个")
                
                # 3. 更新 K_eq (3.0 → 0.65)
                print("\n[3/3] 更新 K_eq: 3.0 → 0.65 (全局参数)")
                cur.execute("""
                    UPDATE calculation_parameters
                    SET 
                        param_value = %s,
                        updated_at = NOW(),
                        updated_by = %s
                    WHERE 
                        metric_key = %s
                        AND param_name = %s
                        AND device_id IS NULL
                """, ('0.65', 'fix_pump_inlet_pressure_20251119', 'pump_inlet_pressure', 'K_eq'))
                
                updated_count = cur.rowcount
                print(f"   ✓ 更新完成: {updated_count} 个全局参数")
                
                if updated_count != 1:
                    raise Exception(f"K_eq 更新失败: 期望1个，实际{updated_count}个")
                
                # 提交事务
                conn.commit()
                
                # 验证结果
                print("\n" + "=" * 100)
                print("参数更新结果汇总")
                print("=" * 100)
                
                cur.execute("""
                    SELECT 
                        COALESCE(device_id::text, 'GLOBAL') as device,
                        param_name,
                        param_value,
                        updated_by
                    FROM calculation_parameters
                    WHERE metric_key = 'pump_inlet_pressure'
                      AND param_name IN ('pipe_diameter', 'L_offset', 'K_eq')
                    ORDER BY 
                        CASE WHEN device_id IS NULL THEN 0 ELSE 1 END,
                        device_id,
                        param_name
                """)
                
                for row in cur.fetchall():
                    device, param_name, param_value, updated_by = row
                    print(f"  {device:8s} | {param_name:15s} = {str(param_value):10s} (by: {updated_by})")
                
                print("=" * 100)
                print("\n✅ 所有参数更新成功！")
                
            except Exception as e:
                conn.rollback()
                print(f"\n❌ 参数更新失败: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)

if __name__ == "__main__":
    main()

