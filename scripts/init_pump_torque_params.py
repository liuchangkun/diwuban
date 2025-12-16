"""
pump_torque 参数初始化脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db.pool import get_connection, initialize_pool, close_pool


def init_pump_torque_parameters():
    """初始化 pump_torque 参数"""

    # 初始化连接池
    settings = load_settings(Path("configs"))
    initialize_pool(settings)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 删除旧参数
                cur.execute("""
                    DELETE FROM calculation_parameters
                    WHERE metric_key = 'pump_torque'
                """)

                # 插入新参数
                params = [
                    # data_filter 参数（使用 pump_torque_method_a 作为 method_id）
                    ('pump_torque', 'pump_torque_method_a', 'max_power', '500.0', 'float'),
                    ('pump_torque', 'pump_torque_method_a', 'max_speed', '3000.0', 'float'),
                    ('pump_torque', 'pump_torque_method_a', 'max_flow', '3000.0', 'float'),
                    ('pump_torque', 'pump_torque_method_a', 'max_head', '100.0', 'float'),
                    ('pump_torque', 'pump_torque_method_a', 'max_torque', '10000.0', 'float'),

                    # method_b 参数（水力功率法）
                    ('pump_torque', 'pump_torque_method_b', 'rho', '1000.0', 'float'),
                    ('pump_torque', 'pump_torque_method_b', 'g', '9.81', 'float'),
                    ('pump_torque', 'pump_torque_method_b', 'max_power', '500.0', 'float'),
                    ('pump_torque', 'pump_torque_method_b', 'max_speed', '3000.0', 'float'),
                    ('pump_torque', 'pump_torque_method_b', 'max_flow', '3000.0', 'float'),
                    ('pump_torque', 'pump_torque_method_b', 'max_head', '100.0', 'float'),
                    ('pump_torque', 'pump_torque_method_b', 'max_torque', '10000.0', 'float'),
                ]

                for metric_key, method_id, param_name, param_value, param_type in params:
                    cur.execute("""
                        INSERT INTO calculation_parameters (metric_key, method_id, param_name, param_value, param_type)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (metric_key, method_id, param_name, param_value, param_type))

                conn.commit()

                print("✅ pump_torque 参数初始化成功！")
                print()
                print("已配置参数：")
                
                # 查询并显示参数
                cur.execute("""
                    SELECT method_id, param_name, param_value, param_type
                    FROM calculation_parameters
                    WHERE metric_key = 'pump_torque'
                    ORDER BY method_id, param_name
                """)
                
                current_method = None
                for row in cur.fetchall():
                    method_id, param_name, param_value, param_type = row
                    if method_id != current_method:
                        print(f"\n[{method_id}]")
                        current_method = method_id
                    print(f"  {param_name} = {param_value} ({param_type})")

    finally:
        close_pool()


if __name__ == '__main__':
    init_pump_torque_parameters()

