"""
修复 pump_inlet_pressure 的 L_offset 参数

问题：
- L_offset = 2.0 m 太小，导致静压头不足以克服水头损失
- 计算公式：P_in = P_atm + ρ × g × (h_static - h_loss) / 1e6
- h_static = pool_liquid_level + L_offset
- h_loss = K_eq × v² / (2g)
- 当 h_loss > h_static 时，泵入口产生负压，压力低于物理约束（0.05 MPa）

解决方案：
- 将 L_offset 从 2.0 m 增加到 12.0 m
- 这样 h_static 足够大，可以克服水头损失
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection, cleanup_database
from app.core.config.loader import load_settings


def main():
    """执行参数修复"""
    print("=" * 80)
    print("修复 pump_inlet_pressure 的 L_offset 参数")
    print("=" * 80)

    # 加载配置并初始化数据库
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)

    # 连接数据库
    with get_connection() as conn:
        cursor = conn.cursor()

        try:
            # 1. 查询当前参数值
            print("\n1. 查询当前参数值...")
            cursor.execute("""
                SELECT
                    device_id,
                    param_name,
                    param_value,
                    updated_at
                FROM calculation_parameters
                WHERE device_id IN (1, 2, 3, 4, 5, 6)
                  AND metric_key = 'pump_inlet_pressure'
                  AND param_name = 'L_offset'
                ORDER BY device_id
            """)

            rows = cursor.fetchall()
            print(f"找到 {len(rows)} 条记录：")
            for row in rows:
                print(f"  设备{row[0]}: {row[1]} = {row[2]} (更新时间: {row[3]})")

            # 2. 更新参数值
            print("\n2. 更新参数值...")
            cursor.execute("""
                UPDATE calculation_parameters
                SET param_value = 12.0,
                    updated_at = NOW(),
                    updated_by = 'system_fix_20251118'
                WHERE device_id IN (1, 2, 3, 4, 5, 6)
                  AND metric_key = 'pump_inlet_pressure'
                  AND param_name = 'L_offset'
                  AND param_value = 2.0
            """)

            affected_rows = cursor.rowcount
            print(f"更新了 {affected_rows} 条记录")

            # 3. 验证更新结果
            print("\n3. 验证更新结果...")
            cursor.execute("""
                SELECT
                    device_id,
                    param_name,
                    param_value,
                    updated_at,
                    updated_by
                FROM calculation_parameters
                WHERE device_id IN (1, 2, 3, 4, 5, 6)
                  AND metric_key = 'pump_inlet_pressure'
                  AND param_name = 'L_offset'
                ORDER BY device_id
            """)

            rows = cursor.fetchall()
            print(f"验证结果（{len(rows)} 条记录）：")
            for row in rows:
                print(f"  设备{row[0]}: {row[1]} = {row[2]} (更新时间: {row[3]}, 更新人: {row[4]})")

            # 提交事务
            conn.commit()
            print("\n✅ 参数修复成功！")

        except Exception as e:
            conn.rollback()
            print(f"\n❌ 参数修复失败: {e}")
            raise

        finally:
            cursor.close()

    # 清理数据库连接池
    cleanup_database()
    
    print("\n" + "=" * 80)
    print("下一步：重新运行测试脚本验证修复效果")
    print("  python scripts/test_end_to_end_via_scheduler.py")
    print("=" * 80)


if __name__ == '__main__':
    main()

