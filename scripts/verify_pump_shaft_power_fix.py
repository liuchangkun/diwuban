"""
验证 pump_shaft_power 参数修复效果

步骤：
1. 清除旧的计算数据
2. 重新运行计算
3. 验证修复效果
4. 生成验证报告
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 设置控制台编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings
from app.services.calculation.shared.shared_services import SharedServices


def step1_backup_old_data():
    """步骤1：备份旧数据（可选）"""
    print(f"\n{'='*100}")
    print("步骤1：备份旧数据")
    print(f"{'='*100}")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 统计旧数据
            cur.execute("""
                SELECT
                    device_id,
                    COUNT(*) AS record_count,
                    MIN(value) AS min_value,
                    MAX(value) AS max_value,
                    AVG(value) AS avg_value
                FROM fact_measurements
                WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_shaft_power')
                  AND device_id IN (1,2,3,4,5,6)
                  AND ts_bucket >= '2025-10-22 00:00:00+00'
                  AND ts_bucket < '2025-10-23 08:00:00+00'
                GROUP BY device_id
                ORDER BY device_id
            """)
            
            old_data = cur.fetchall()
            
            print("\n旧数据统计:")
            print("-"*100)
            print(f"{'设备ID':<10} {'记录数':<15} {'最小值':<15} {'最大值':<15} {'平均值':<15}")
            print("-"*100)
            
            total_records = 0
            for row in old_data:
                device_id, count, min_val, max_val, avg_val = row
                print(f"{device_id:<10} {count:<15} {min_val:<15.2f} {max_val:<15.2f} {avg_val:<15.2f}")
                total_records += count
            
            print("-"*100)
            print(f"{'总计':<10} {total_records:<15}")
            
            return total_records


def step2_clear_old_data():
    """步骤2：清除旧数据"""
    print(f"\n{'='*100}")
    print("步骤2：清除旧数据")
    print(f"{'='*100}")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM fact_measurements
                WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_shaft_power')
                  AND device_id IN (1,2,3,4,5,6)
                  AND ts_bucket >= '2025-10-22 00:00:00+00'
                  AND ts_bucket < '2025-10-23 08:00:00+00'
            """)
            
            deleted_count = cur.rowcount
            conn.commit()
            
            print(f"\n✅ 已删除 {deleted_count} 条旧数据")
            
            return deleted_count


def step3_verify_parameters():
    """步骤3：验证参数已正确配置"""
    print(f"\n{'='*100}")
    print("步骤3：验证参数配置")
    print(f"{'='*100}")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    device_id,
                    param_name,
                    param_value
                FROM calculation_parameters
                WHERE station_id = 1
                  AND metric_key = 'pump_shaft_power'
                  AND device_id IN (1,2,3,4,5,6)
                ORDER BY device_id, param_name
            """)
            
            params = cur.fetchall()
            
            print("\n参数配置:")
            print("-"*100)
            print(f"{'设备ID':<10} {'参数名':<25} {'参数值':<15}")
            print("-"*100)
            
            for row in params:
                device_id, param_name, param_value = row
                print(f"{device_id:<10} {param_name:<25} {param_value:<15}")
            
            # 验证关键参数
            max_power_values = [row[2] for row in params if row[1] == 'max_power']
            max_shaft_power_values = [row[2] for row in params if row[1] == 'max_shaft_power']
            
            print("\n验证结果:")
            print("-"*100)
            
            if len(max_power_values) == 6 and all(float(v) == 350.0 for v in max_power_values):
                print("✅ max_power 参数正确（350.0 kW，6个设备）")
            else:
                print(f"❌ max_power 参数错误：{max_power_values}")
            
            if len(max_shaft_power_values) == 6 and all(float(v) == 312.0 for v in max_shaft_power_values):
                print("✅ max_shaft_power 参数正确（312.0 kW，6个设备）")
            else:
                print(f"❌ max_shaft_power 参数错误：{max_shaft_power_values}")


def step4_clear_cache():
    """步骤4：清除 ParameterManager 缓存"""
    print(f"\n{'='*100}")
    print("步骤4：清除 ParameterManager 缓存")
    print(f"{'='*100}")
    
    # 重新初始化 SharedServices 以清除缓存
    SharedServices._instance = None
    SharedServices._initialized = False
    
    print("✅ ParameterManager 缓存已清除")


def step5_run_calculation():
    """步骤5：重新运行计算"""
    print(f"\n{'='*100}")
    print("步骤5：重新运行 pump_shaft_power 计算")
    print(f"{'='*100}")
    
    print("\n请手动执行以下命令：")
    print("-"*100)
    print("python scripts/run_single_metric.py pump_shaft_power")
    print("-"*100)
    print("\n或者使用 Scheduler：")
    print("-"*100)
    print("python scripts/run_scheduler_single_metric.py pump_shaft_power")
    print("-"*100)


def step6_verify_results():
    """步骤6：验证修复效果"""
    print(f"\n{'='*100}")
    print("步骤6：验证修复效果")
    print(f"{'='*100}")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 统计新数据
            cur.execute("""
                SELECT
                    device_id,
                    COUNT(*) AS record_count,
                    MIN(value) AS min_value,
                    MAX(value) AS max_value,
                    AVG(value) AS avg_value
                FROM fact_measurements
                WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_shaft_power')
                  AND device_id IN (1,2,3,4,5,6)
                  AND ts_bucket >= '2025-10-22 00:00:00+00'
                  AND ts_bucket < '2025-10-23 08:00:00+00'
                GROUP BY device_id
                ORDER BY device_id
            """)
            
            new_data = cur.fetchall()
            
            if not new_data:
                print("\n⚠️ 未找到新数据，请先运行计算！")
                return None
            
            print("\n新数据统计:")
            print("-"*100)
            print(f"{'设备ID':<10} {'记录数':<15} {'最小值':<15} {'最大值':<15} {'平均值':<15}")
            print("-"*100)
            
            total_records = 0
            max_shaft_power = 0
            
            for row in new_data:
                device_id, count, min_val, max_val, avg_val = row
                print(f"{device_id:<10} {count:<15} {min_val:<15.2f} {max_val:<15.2f} {avg_val:<15.2f}")
                total_records += count
                max_shaft_power = max(max_shaft_power, max_val)
            
            print("-"*100)
            print(f"{'总计':<10} {total_records:<15}")
            
            # 计算覆盖率
            cur.execute("""
                SELECT COUNT(*) 
                FROM mv_device_running_1s
                WHERE device_id IN (1,2,3,4,5,6)
                  AND running = 1
                  AND ts_bucket >= '2025-10-22 00:00:00+00'
                  AND ts_bucket < '2025-10-23 08:00:00+00'
            """)
            
            total_running = cur.fetchone()[0]
            coverage_rate = (total_records / total_running * 100) if total_running > 0 else 0
            
            print(f"\n覆盖率统计:")
            print("-"*100)
            print(f"运行状态记录数: {total_running}")
            print(f"计算结果记录数: {total_records}")
            print(f"覆盖率: {coverage_rate:.2f}%")
            print(f"最大轴功率: {max_shaft_power:.2f} kW")
            
            return {
                'total_records': total_records,
                'total_running': total_running,
                'coverage_rate': coverage_rate,
                'max_shaft_power': max_shaft_power
            }


def main():
    """主函数"""
    print("="*100)
    print("pump_shaft_power 参数修复验证")
    print("="*100)
    
    # 初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 执行步骤
    old_count = step1_backup_old_data()
    deleted_count = step2_clear_old_data()
    step3_verify_parameters()
    step4_clear_cache()
    step5_run_calculation()
    
    print(f"\n{'='*100}")
    print("准备工作已完成")
    print(f"{'='*100}")
    print(f"\n旧数据记录数: {old_count}")
    print(f"已删除记录数: {deleted_count}")
    print(f"\n下一步：运行计算后，再次执行此脚本的 step6_verify_results() 验证结果")


if __name__ == '__main__':
    main()

