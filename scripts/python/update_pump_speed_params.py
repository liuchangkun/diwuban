"""
更新pump_speed_method_a的参数配置
添加n_ref参数（额定转速）
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings
from app.core.logging.setup import init_logging

def update_pump_speed_params():
    """更新pump_speed_method_a的参数"""
    print("\n" + "="*80)
    print("更新pump_speed_method_a参数配置")
    print("="*80)
    
    # 添加n_ref参数
    insert_query = """
        INSERT INTO calculation_parameters (
            station_id,
            device_id,
            metric_key,
            method_id,
            param_name,
            param_value,
            param_type,
            is_optimizable,
            updated_by
        ) VALUES (
            NULL,
            NULL,
            'pump_speed',
            'pump_speed_method_a',
            'n_ref',
            1500.0,
            'float',
            true,
            'system'
        ) ON CONFLICT (device_id, metric_key, method_id, param_name) 
        DO UPDATE SET
            param_value = EXCLUDED.param_value,
            param_type = EXCLUDED.param_type,
            is_optimizable = EXCLUDED.is_optimizable,
            updated_at = NOW(),
            updated_by = EXCLUDED.updated_by
    """
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 执行插入/更新
                cur.execute(insert_query)
                conn.commit()
                
                print("✅ 成功添加/更新n_ref参数")
                
                # 验证结果
                verify_query = """
                    SELECT 
                        method_id,
                        param_name,
                        param_value,
                        param_type,
                        is_optimizable
                    FROM calculation_parameters
                    WHERE method_id = 'pump_speed_method_a'
                    ORDER BY param_name
                """
                cur.execute(verify_query)
                rows = cur.fetchall()
                
                print("\n当前pump_speed_method_a的参数配置：")
                print("-" * 80)
                print(f"{'参数名':<20} {'参数值':<15} {'类型':<10} {'可优化':<10}")
                print("-" * 80)
                
                for row in rows:
                    method_id, param_name, param_value, param_type, is_optimizable = row
                    print(f"{param_name:<20} {param_value:<15} {param_type:<10} {is_optimizable}")
                
                print("-" * 80)
                print(f"总计：{len(rows)} 个参数")
                
                return True
                
    except Exception as e:
        print(f"❌ 更新失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    # 初始化
    init_logging()
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    
    # 更新参数
    success = update_pump_speed_params()
    
    if success:
        print("\n🎉 参数更新成功！")
        return 0
    else:
        print("\n⚠️ 参数更新失败")
        return 1


if __name__ == "__main__":
    exit(main())

