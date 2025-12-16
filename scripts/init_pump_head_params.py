"""
pump_head 参数初始化脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db.pool import get_connection, initialize_pool, close_pool


def init_pump_head_parameters():
    """初始化 pump_head 参数"""

    # 初始化连接池
    settings = load_settings(Path("configs"))
    initialize_pool(settings)

    # 直接使用SQL语句
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 注册计算方法
            print("注册计算方法...")
            cur.execute("""
                INSERT INTO calculation_method_registry (
                    method_id, metric_key, method_name, method_code, priority,
                    dependencies, conditions, accuracy_level, is_enabled, allowed_device_types
                ) VALUES (
                    'pipe_loss_multi_pump',
                    'pump_head',
                    '压差法（管道损失+多泵修正）',
                    'A',
                    100,
                    ARRAY['pump_inlet_pressure', 'main_pipeline_outlet_pressure', 'pump_flow_rate', 'N_running']::text[],
                    '{"description": "P_pump_out = P_main_out × correction_factor + delta_P_pipe; H = (P_pump_out - P_pump_in) × 1e6 / (ρ × g)"}'::jsonb,
                    'high',
                    TRUE,
                    ARRAY['pump']::text[]
                )
                ON CONFLICT (method_id) DO NOTHING
            """)

            # 删除已存在的 pump_head 参数
            print("删除已存在的 pump_head 参数...")
            cur.execute("DELETE FROM calculation_parameters WHERE metric_key = 'pump_head'")

            # 插入全局参数（物理常数 + 验证范围）
            print("插入全局参数...")
            cur.execute("""
                INSERT INTO calculation_parameters (metric_key, method_id, param_name, param_value, param_type, station_id, device_id, is_optimizable)
                VALUES
                    ('pump_head', 'pipe_loss_multi_pump', 'rho', 1000.0, 'float', NULL, NULL, FALSE),
                    ('pump_head', 'pipe_loss_multi_pump', 'g', 9.81, 'float', NULL, NULL, FALSE),
                    ('pump_head', 'pipe_loss_multi_pump', 'max_pump_inlet_pressure', 2.0, 'float', NULL, NULL, FALSE),
                    ('pump_head', 'pipe_loss_multi_pump', 'max_main_pipeline_outlet_pressure', 2.0, 'float', NULL, NULL, FALSE),
                    ('pump_head', 'pipe_loss_multi_pump', 'max_pump_flow_rate', 5000.0, 'float', NULL, NULL, FALSE),
                    ('pump_head', 'pipe_loss_multi_pump', 'max_n_running', 10, 'int', NULL, NULL, FALSE),
                    ('pump_head', 'pipe_loss_multi_pump', 'min_pump_outlet_pressure', 0.0, 'float', NULL, NULL, FALSE),
                    ('pump_head', 'pipe_loss_multi_pump', 'max_pump_outlet_pressure', 2.0, 'float', NULL, NULL, FALSE),
                    ('pump_head', 'pipe_loss_multi_pump', 'min_pump_head', 0.0, 'float', NULL, NULL, FALSE),
                    ('pump_head', 'pipe_loss_multi_pump', 'max_pump_head', 200.0, 'float', NULL, NULL, FALSE)
            """)

            # 插入泵站参数
            print("插入泵站参数...")
            cur.execute("""
                INSERT INTO calculation_parameters (metric_key, method_id, param_name, param_value, param_type, station_id, device_id, is_optimizable)
                VALUES ('pump_head', 'pipe_loss_multi_pump', 'N_total_pumps', 6, 'int', 1, NULL, FALSE)
            """)

            # 插入设备参数
            print("插入设备参数...")
            cur.execute("""
                INSERT INTO calculation_parameters (metric_key, method_id, param_name, param_value, param_type, station_id, device_id, is_optimizable)
                VALUES
                    ('pump_head', 'pipe_loss_multi_pump', 'K_pipe_loss', 0.00001, 'float', 1, 1, TRUE),
                    ('pump_head', 'pipe_loss_multi_pump', 'alpha_multi_pump', 0.02, 'float', 1, 1, TRUE),
                    ('pump_head', 'pipe_loss_multi_pump', 'K_pipe_loss', 0.00001, 'float', 1, 2, TRUE),
                    ('pump_head', 'pipe_loss_multi_pump', 'alpha_multi_pump', 0.02, 'float', 1, 2, TRUE),
                    ('pump_head', 'pipe_loss_multi_pump', 'K_pipe_loss', 0.00001, 'float', 1, 3, TRUE),
                    ('pump_head', 'pipe_loss_multi_pump', 'alpha_multi_pump', 0.02, 'float', 1, 3, TRUE),
                    ('pump_head', 'pipe_loss_multi_pump', 'K_pipe_loss', 0.00001, 'float', 1, 4, TRUE),
                    ('pump_head', 'pipe_loss_multi_pump', 'alpha_multi_pump', 0.02, 'float', 1, 4, TRUE),
                    ('pump_head', 'pipe_loss_multi_pump', 'K_pipe_loss', 0.00001, 'float', 1, 5, TRUE),
                    ('pump_head', 'pipe_loss_multi_pump', 'alpha_multi_pump', 0.02, 'float', 1, 5, TRUE),
                    ('pump_head', 'pipe_loss_multi_pump', 'K_pipe_loss', 0.00001, 'float', 1, 6, TRUE),
                    ('pump_head', 'pipe_loss_multi_pump', 'alpha_multi_pump', 0.02, 'float', 1, 6, TRUE)
            """)

        conn.commit()
        print("✅ 参数插入完成")
    
    # 验证
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    metric_key,
                    param_name,
                    param_value,
                    param_type,
                    station_id,
                    device_id,
                    is_optimizable
                FROM calculation_parameters
                WHERE metric_key = 'pump_head'
                ORDER BY
                    COALESCE(station_id, 999),
                    COALESCE(device_id, 999),
                    param_name
            """)
            
            results = cur.fetchall()
            
            print(f"\n✅ 参数初始化完成，共插入 {len(results)} 条记录：\n")

            # 按类型分组显示
            global_params = [r for r in results if r[4] is None and r[5] is None]
            station_params = [r for r in results if r[4] is not None and r[5] is None]
            device_params = [r for r in results if r[5] is not None]

            print("【全局参数】")
            for row in global_params:
                metric_key, param_name, param_value, param_type, station_id, device_id, is_optimizable = row
                print(f"  - {param_name}: {param_value} ({param_type})")

            print("\n【泵站参数】")
            for row in station_params:
                metric_key, param_name, param_value, param_type, station_id, device_id, is_optimizable = row
                print(f"  - {param_name}: {param_value} (station_id={station_id})")

            print(f"\n【设备参数】({len(device_params)}条)")
            for row in device_params[:4]:  # 只显示前4条
                metric_key, param_name, param_value, param_type, station_id, device_id, is_optimizable = row
                print(f"  - device_id={device_id}, {param_name}: {param_value}")
            if len(device_params) > 4:
                print(f"  ... 还有 {len(device_params) - 4} 条设备参数")


if __name__ == '__main__':
    try:
        init_pump_head_parameters()
    finally:
        close_pool()

