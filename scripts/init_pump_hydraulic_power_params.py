"""
pump_hydraulic_power 参数初始化脚本（Python版本）

用途：初始化pump_hydraulic_power计算所需的所有参数
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def init_parameters():
    """初始化pump_hydraulic_power参数"""
    print("="*80)
    print("pump_hydraulic_power 参数初始化")
    print("="*80)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. 插入计算参数
            print("\n1. 插入计算参数...")
            
            params = [
                # 计算参数（全局）
                (None, None, 'pump_hydraulic_power', 'rho', 1000.0, 'float', False),
                (None, None, 'pump_hydraulic_power', 'g', 9.81, 'float', False),

                # 验证参数（全局）
                (None, None, 'pump_hydraulic_power', 'min_power', 0.0, 'float', True),
                (None, None, 'pump_hydraulic_power', 'max_power', 500.0, 'float', True),
            ]

            for station_id, device_id, metric_key, param_name, param_value, param_type, is_optimizable in params:
                # 先检查是否存在
                cur.execute("""
                    SELECT id FROM calculation_parameters
                    WHERE COALESCE(station_id, -1) = COALESCE(%s, -1)
                      AND COALESCE(device_id, -1) = COALESCE(%s, -1)
                      AND metric_key = %s
                      AND param_name = %s
                """, (station_id, device_id, metric_key, param_name))

                existing = cur.fetchone()

                if existing:
                    # 更新
                    cur.execute("""
                        UPDATE calculation_parameters
                        SET param_value = %s,
                            param_type = %s,
                            is_optimizable = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (param_value, param_type, is_optimizable, existing[0]))
                    print(f"  ✅ 更新 {param_name} = {param_value} ({param_type})")
                else:
                    # 插入
                    cur.execute("""
                        INSERT INTO calculation_parameters (
                            station_id,
                            device_id,
                            metric_key,
                            param_name,
                            param_value,
                            param_type,
                            is_optimizable
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (station_id, device_id, metric_key, param_name, param_value, param_type, is_optimizable))
                    print(f"  ✅ 插入 {param_name} = {param_value} ({param_type})")
                
                print(f"  ✅ {param_name} = {param_value} ({param_type})")
            
            conn.commit()
            print(f"\n  ✅ 成功插入/更新 {len(params)} 个参数")

            # 2. 验证参数
            print("\n2. 验证参数...")
            cur.execute("""
                SELECT
                    param_name,
                    param_value,
                    param_type,
                    is_optimizable,
                    station_id,
                    device_id
                FROM calculation_parameters
                WHERE metric_key = 'pump_hydraulic_power'
                ORDER BY param_name
            """)

            rows = cur.fetchall()
            print(f"\n  找到 {len(rows)} 个参数:")
            print(f"\n  {'参数名':<20} {'值':<15} {'类型':<10} {'可优化':<10} {'站点':<8} {'设备':<8}")
            print(f"  {'-'*80}")
            for row in rows:
                param_name, param_value, param_type, is_optimizable, station_id, device_id = row
                station_str = str(station_id) if station_id is not None else 'NULL'
                device_str = str(device_id) if device_id is not None else 'NULL'
                opt_str = 'Yes' if is_optimizable else 'No'
                print(f"  {param_name:<20} {param_value:<15} {param_type:<10} {opt_str:<10} {station_str:<8} {device_str:<8}")

    print("\n" + "="*80)
    print("参数初始化完成！")
    print("="*80)
    
    print("\n参数说明:")
    print("  计算参数:")
    print("    - rho: 液体密度（kg/m³），默认1000.0（水）")
    print("    - g: 重力加速度（m/s²），默认9.81")
    print("\n  验证参数:")
    print("    - min_power: 水力功率最小值（kW），默认0.0")
    print("    - max_power: 水力功率最大值（kW），默认500.0")
    print("\n  计算公式:")
    print("    P_h = ρ × g × Q × H / 3600000 (kW)")
    print("    其中：Q为泵流量（m³/h），H为泵扬程（m）")


if __name__ == '__main__':
    # 初始化数据库连接
    settings = load_settings(Path("configs"))
    init_database(settings)

    # 执行参数初始化
    init_parameters()

