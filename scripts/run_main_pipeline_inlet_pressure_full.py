"""
步骤4：全量计算执行 - main_pipeline_inlet_pressure
使用调度器将计算结果写入数据库
"""
import sys
from pathlib import Path
from datetime import datetime
import time

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 初始化数据库和日志
from app.adapters.db import init_database, get_connection
from app.core.logging.setup import init_logging
from app.core.config.loader_new import load_settings

# 加载配置
config_dir = project_root / "configs"
settings = load_settings(config_dir)

# 初始化日志
init_logging(config_dir, settings.system.timezone.default)

# 初始化数据库
init_database(settings)

from app.services.calculation.shared.scheduler import Scheduler


def main():
    print('=' * 80)
    print('步骤4：全量计算执行 - main_pipeline_inlet_pressure')
    print('=' * 80)

    # ========== 4.1 准备阶段 ==========
    print('\n[1/4] 准备阶段：检查现有数据...')
    
    sql_check = """
    SELECT COUNT(*) as count
    FROM fact_measurements
    WHERE metric_id = 61
      AND device_id = 7
    """
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_check)
            result = cur.fetchone()
            existing_count = result[0]
    
    print(f'  - 现有数据量: {existing_count} 条')
    
    if existing_count > 0:
        print(f'  ⚠️  警告：数据库中已存在 {existing_count} 条 main_pipeline_inlet_pressure 数据')
        print(f'  - 调度器将覆盖相同时间范围的数据')
    
    # ========== 4.2 执行阶段 ==========
    print('\n[2/4] 执行阶段：运行调度器...')
    
    # 使用全时间范围
    start_time = datetime(2025, 10, 22, 8, 0, 0)
    end_time = datetime(2025, 10, 23, 7, 13, 29)
    
    print(f'  - 时间范围: {start_time} ~ {end_time}')
    print(f'  - 指标: main_pipeline_inlet_pressure')
    print(f'  - 设备: device_id=7 (总管设备)')
    
    scheduler = Scheduler()

    exec_start = time.time()
    try:
        # main_pipeline_inlet_pressure 只有 device_id=7（总管设备）
        result = scheduler.schedule_single_metric(
            metric_key="main_pipeline_inlet_pressure",
            device_ids=[7],  # 总管设备
            start_time=start_time,
            end_time=end_time,
            time_chunk_hours=24  # 24小时分片
        )
        exec_elapsed = time.time() - exec_start
        print(f'  ✅ 调度器执行成功')
        print(f'  - 执行时间: {exec_elapsed:.2f} 秒')
        print(f'  - 成功任务: {result["success_count"]}/{result["total_tasks"]}')
        print(f'  - 写入记录: {result["total_points"]:,} 条')
    except Exception as e:
        print(f'  ❌ 调度器执行失败: {e}')
        import traceback
        traceback.print_exc()
        return False
    
    # ========== 4.3 验证阶段 ==========
    print('\n[3/4] 验证阶段：检查写入结果...')
    
    sql_verify = """
    SELECT
        COUNT(*) as total_count,
        COUNT(CASE WHEN value IS NOT NULL THEN 1 END) as valid_count,
        MIN(value) as min_value,
        MAX(value) as max_value,
        AVG(value) as avg_value,
        STDDEV(value) as std_value
    FROM fact_measurements
    WHERE metric_id = 61
      AND device_id = 7
      AND ts_bucket >= %s
      AND ts_bucket < %s
    """
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_verify, (start_time, end_time))
            result = cur.fetchone()
    
    total_count = result[0]
    valid_count = result[1]
    min_value = result[2]
    max_value = result[3]
    avg_value = result[4]
    std_value = result[5]
    
    print('\n=== 写入结果统计 ===')
    print(f'总记录数: {total_count}')
    print(f'有效值数量: {valid_count}')
    print(f'覆盖率: {valid_count / total_count * 100:.2f}%' if total_count > 0 else '覆盖率: N/A')
    print(f'数值范围: [{min_value:.6f}, {max_value:.6f}]' if min_value is not None else '数值范围: N/A')
    print(f'平均值: {avg_value:.6f}' if avg_value is not None else '平均值: N/A')
    print(f'标准差: {std_value:.6f}' if std_value is not None else '标准差: N/A')
    
    # ========== 4.4 结果验证 ==========
    print('\n[4/4] 结果验证...')
    
    success = True
    
    # 验证1：写入数量
    if total_count == 0:
        print('❌ 验证失败：未写入任何数据')
        success = False
    else:
        print(f'✅ 写入数量达标: {total_count} > 0')
    
    # 验证2：覆盖率
    if total_count > 0:
        coverage_rate = valid_count / total_count * 100
        if coverage_rate >= 95:
            print(f'✅ 覆盖率达标: {coverage_rate:.2f}% ≥ 95%')
        else:
            print(f'❌ 覆盖率不达标: {coverage_rate:.2f}% < 95%')
            success = False

    # 验证3：数值范围
    if min_value is not None and max_value is not None:
        if min_value >= 0.05 and max_value <= 0.50:
            print(f'✅ 数值范围合理: [{min_value:.6f}, {max_value:.6f}] 在 [0.05, 0.50] MPa 内')
        else:
            print(f'⚠️  数值范围异常: [{min_value:.6f}, {max_value:.6f}] 超出 [0.05, 0.50] MPa')
            # 不标记为失败，仅警告

    # 总结
    print('\n' + '=' * 80)
    if success:
        print('✅ 步骤4：全量计算执行 - 成功完成！')
        print('=' * 80)
        return True
    else:
        print('❌ 步骤4：全量计算执行 - 验证失败！')
        print('=' * 80)
        return False


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f'\n❌ 执行失败: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

