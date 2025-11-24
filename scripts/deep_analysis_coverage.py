"""
深度分析三个指标的覆盖率问题

问题：
1. pump_shaft_power 为什么只有9.4%覆盖率？
2. pump_inlet_pressure 实际覆盖率是多少？
3. main_pipeline_inlet_pressure 实际覆盖率是多少？

分析维度：
1. 数据库实际写入记录数 vs 运行状态记录数
2. 过滤规则分析（每个过滤步骤的数据损失）
3. 参数配置验证
4. 依赖数据可用性
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# 设置控制台编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def analyze_metric_coverage(cur, metric_key, device_ids, start_time, end_time):
    """分析单个指标的覆盖率"""
    print(f"\n{'='*100}")
    print(f"分析指标: {metric_key}")
    print(f"{'='*100}")
    
    # 1. 获取运行状态记录数
    cur.execute("""
        SELECT device_id, COUNT(*) as running_count
        FROM mv_device_running_1s
        WHERE station_id = 1
          AND device_id = ANY(%s)
          AND ts_bucket >= %s
          AND ts_bucket < %s
          AND running = 1
        GROUP BY device_id
        ORDER BY device_id
    """, (device_ids, start_time, end_time))
    
    running_counts = {row[0]: row[1] for row in cur.fetchall()}
    
    # 2. 获取实际写入记录数
    cur.execute("""
        SELECT fm.device_id, COUNT(*) as written_count
        FROM fact_measurements fm
        JOIN dim_metric_config mc ON mc.id = fm.metric_id
        WHERE fm.station_id = 1
          AND fm.device_id = ANY(%s)
          AND mc.metric_key = %s
          AND fm.ts_bucket >= %s
          AND fm.ts_bucket < %s
        GROUP BY fm.device_id
        ORDER BY fm.device_id
    """, (device_ids, metric_key, start_time, end_time))
    
    written_counts = {row[0]: row[1] for row in cur.fetchall()}
    
    # 3. 打印对比
    print(f"\n{'设备':<8} {'运行记录':<15} {'写入记录':<15} {'覆盖率':<10} {'缺失记录':<15}")
    print("-"*100)
    
    total_running = 0
    total_written = 0
    
    for device_id in device_ids:
        running = running_counts.get(device_id, 0)
        written = written_counts.get(device_id, 0)
        coverage = (written / running * 100) if running > 0 else 0
        missing = running - written
        
        total_running += running
        total_written += written
        
        print(f"{device_id:<8} {running:<15,} {written:<15,} {coverage:<9.1f}% {missing:<15,}")
    
    total_coverage = (total_written / total_running * 100) if total_running > 0 else 0
    total_missing = total_running - total_written
    
    print("-"*100)
    print(f"{'总计':<8} {total_running:<15,} {total_written:<15,} {total_coverage:<9.1f}% {total_missing:<15,}")
    
    return total_running, total_written, total_coverage


def analyze_pump_shaft_power_filtering(cur, start_time, end_time):
    """分析 pump_shaft_power 的过滤规则"""
    print(f"\n{'='*100}")
    print("pump_shaft_power 过滤规则分析")
    print(f"{'='*100}")
    
    # 逐步分析数据过滤
    device_ids = [1, 2, 3, 4, 5, 6]
    
    for device_id in device_ids:
        print(f"\n设备 {device_id} 的过滤步骤分析：")
        print("-"*100)
        
        # 步骤1：运行状态记录
        cur.execute("""
            SELECT COUNT(*) FROM mv_device_running_1s
            WHERE station_id = 1 AND device_id = %s
              AND ts_bucket >= %s AND ts_bucket < %s
              AND running = 1
        """, (device_id, start_time, end_time))
        step1_count = cur.fetchone()[0]
        print(f"步骤1 - 运行状态记录 (running=1): {step1_count:,}")
        
        # 步骤2：有 pump_active_power 数据
        cur.execute("""
            SELECT COUNT(*)
            FROM mv_device_running_1s r
            JOIN fact_measurements fm ON fm.ts_bucket = r.ts_bucket 
                AND fm.device_id = r.device_id AND fm.station_id = r.station_id
            JOIN dim_metric_config mc ON mc.id = fm.metric_id
            WHERE r.station_id = 1 AND r.device_id = %s
              AND r.ts_bucket >= %s AND r.ts_bucket < %s
              AND r.running = 1
              AND mc.metric_key = 'pump_active_power'
        """, (device_id, start_time, end_time))
        step2_count = cur.fetchone()[0]
        step2_loss = step1_count - step2_count
        print(f"步骤2 - 有 pump_active_power 数据: {step2_count:,} (损失: {step2_loss:,}, {step2_loss/step1_count*100:.1f}%)")
        
        # 步骤3：pump_active_power > 0
        cur.execute("""
            SELECT COUNT(*)
            FROM mv_device_running_1s r
            JOIN fact_measurements fm ON fm.ts_bucket = r.ts_bucket 
                AND fm.device_id = r.device_id AND fm.station_id = r.station_id
            JOIN dim_metric_config mc ON mc.id = fm.metric_id
            WHERE r.station_id = 1 AND r.device_id = %s
              AND r.ts_bucket >= %s AND r.ts_bucket < %s
              AND r.running = 1
              AND mc.metric_key = 'pump_active_power'
              AND fm.value > 0
        """, (device_id, start_time, end_time))
        step3_count = cur.fetchone()[0]
        step3_loss = step2_count - step3_count
        print(f"步骤3 - pump_active_power > 0: {step3_count:,} (损失: {step3_loss:,}, {step3_loss/step2_count*100:.1f}%)")
        
        # 步骤4：获取参数 eta_motor, eta_vfd
        cur.execute("""
            SELECT param_key, param_value
            FROM calculation_parameters
            WHERE station_id = 1 AND device_id = %s
              AND param_key IN ('eta_motor', 'eta_vfd')
        """, (device_id,))
        params = {row[0]: row[1] for row in cur.fetchall()}
        print(f"步骤4 - 参数配置: eta_motor={params.get('eta_motor', 'MISSING')}, eta_vfd={params.get('eta_vfd', 'MISSING')}")
        
        # 步骤5：实际写入记录
        cur.execute("""
            SELECT COUNT(*)
            FROM fact_measurements fm
            JOIN dim_metric_config mc ON mc.id = fm.metric_id
            WHERE fm.station_id = 1 AND fm.device_id = %s
              AND mc.metric_key = 'pump_shaft_power'
              AND fm.ts_bucket >= %s AND fm.ts_bucket < %s
        """, (device_id, start_time, end_time))
        step5_count = cur.fetchone()[0]
        step5_loss = step3_count - step5_count
        print(f"步骤5 - 实际写入记录: {step5_count:,} (损失: {step5_loss:,}, {step5_loss/step3_count*100:.1f}%)")
        
        # 分析损失原因
        if step5_loss > 0:
            print(f"\n⚠️ 关键损失: 从步骤3到步骤5损失了 {step5_loss:,} 条记录 ({step5_loss/step3_count*100:.1f}%)")
            print("可能原因:")
            print("  1. Validator 过滤掉了不合理的值")
            print("  2. 参数缺失或无效")
            print("  3. 计算结果为0或负值")


def main():
    """主函数"""
    print("="*100)
    print("深度分析三个指标的覆盖率问题")
    print("="*100)
    
    # 初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 时间范围
    start_time = datetime(2025, 10, 22, 8, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 10, 23, 7, 13, 29, tzinfo=timezone.utc)
    
    print(f"\n时间范围: {start_time} ~ {end_time}")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 分析三个指标
            print("\n\n" + "="*100)
            print("第一部分：覆盖率对比分析")
            print("="*100)
            
            # 1. pump_inlet_pressure (设备1-6)
            analyze_metric_coverage(cur, 'pump_inlet_pressure', [1, 2, 3, 4, 5, 6], start_time, end_time)
            
            # 2. main_pipeline_inlet_pressure (设备7)
            analyze_metric_coverage(cur, 'main_pipeline_inlet_pressure', [7], start_time, end_time)
            
            # 3. pump_shaft_power (设备1-6)
            analyze_metric_coverage(cur, 'pump_shaft_power', [1, 2, 3, 4, 5, 6], start_time, end_time)
            
            # 分析 pump_shaft_power 的过滤规则
            print("\n\n" + "="*100)
            print("第二部分：pump_shaft_power 过滤规则详细分析")
            print("="*100)
            
            analyze_pump_shaft_power_filtering(cur, start_time, end_time)
    
    print("\n✅ 分析完成")


if __name__ == '__main__':
    main()

