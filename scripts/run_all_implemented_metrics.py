"""
执行所有已实现指标的计算
包括：pump_flow_rate, pump_inlet_pressure, pump_head, pump_efficiency, pump_speed, main_pipeline_inlet_pressure
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
    print('执行所有已实现指标的计算')
    print('=' * 80)

    # 已实现的指标列表
    metrics = [
        "pump_flow_rate",
        "pump_inlet_pressure",
        "main_pipeline_inlet_pressure",
        "pump_head",
        "pump_efficiency",
        "pump_speed"
    ]
    
    # 设备列表
    # pump_flow_rate, pump_inlet_pressure, pump_head, pump_efficiency, pump_speed: 设备1-6（泵设备）
    # main_pipeline_inlet_pressure: 设备7（总管设备）
    pump_devices = [1, 2, 3, 4, 5, 6]
    pipeline_device = [7]
    
    # 时间范围（使用全时间范围）
    start_time = datetime(2025, 10, 22, 8, 0, 0)
    end_time = datetime(2025, 10, 23, 7, 13, 29)
    
    print(f'\n计算参数：')
    print(f'  - 指标列表: {", ".join(metrics)}')
    print(f'  - 泵设备: {pump_devices}')
    print(f'  - 总管设备: {pipeline_device}')
    print(f'  - 时间范围: {start_time} ~ {end_time}')
    print(f'  - 时间分片: 24小时')
    
    # 创建调度器
    scheduler = Scheduler()
    
    # 执行计算
    print('\n' + '=' * 80)
    print('开始执行计算...')
    print('=' * 80)
    
    exec_start = time.time()
    
    try:
        # 使用 schedule_all_metrics 按顺序执行所有指标
        # 注意：main_pipeline_inlet_pressure 只有设备7，其他指标是设备1-6
        # 我们需要分别处理
        
        all_results = {}
        
        # 1. 先执行泵设备的指标（设备1-6）
        pump_metrics = [
            "pump_flow_rate",
            "pump_inlet_pressure",
            "pump_head",
            "pump_efficiency",
            "pump_speed"
        ]
        
        print(f'\n[1/2] 执行泵设备指标（设备1-6）...')
        pump_results = scheduler.schedule_all_metrics(
            device_ids=pump_devices,
            start_time=start_time,
            end_time=end_time,
            time_chunk_hours=24,
            metrics=pump_metrics
        )
        all_results.update(pump_results)
        
        # 2. 再执行总管设备的指标（设备7）
        print(f'\n[2/2] 执行总管设备指标（设备7）...')
        pipeline_result = scheduler.schedule_single_metric(
            metric_key="main_pipeline_inlet_pressure",
            device_ids=pipeline_device,
            start_time=start_time,
            end_time=end_time,
            time_chunk_hours=24
        )
        all_results["main_pipeline_inlet_pressure"] = pipeline_result
        
        exec_elapsed = time.time() - exec_start
        
        print('\n' + '=' * 80)
        print('计算完成！')
        print('=' * 80)
        print(f'总执行时间: {exec_elapsed:.2f} 秒')
        
        # 输出结果统计
        print('\n' + '=' * 80)
        print('计算结果统计')
        print('=' * 80)
        
        total_tasks = 0
        total_success = 0
        total_points = 0
        
        for metric_key in metrics:
            result = all_results.get(metric_key, {})
            success_count = result.get('success_count', 0)
            total_tasks_count = result.get('total_tasks', 0)
            points = result.get('total_points', 0)
            duration = result.get('total_duration_seconds', 0)
            
            total_tasks += total_tasks_count
            total_success += success_count
            total_points += points
            
            print(f'\n指标: {metric_key}')
            print(f'  - 成功任务: {success_count}/{total_tasks_count}')
            print(f'  - 写入记录: {points:,} 条')
            print(f'  - 执行时长: {duration:.2f} 秒')
        
        print(f'\n' + '=' * 80)
        print(f'总计:')
        print(f'  - 总任务数: {total_tasks}')
        print(f'  - 成功任务: {total_success}')
        print(f'  - 成功率: {total_success/total_tasks*100:.2f}%' if total_tasks > 0 else '  - 成功率: N/A')
        print(f'  - 总记录数: {total_points:,}')
        print(f'  - 总执行时长: {exec_elapsed:.2f} 秒')
        print('=' * 80)
        
        return True
        
    except Exception as e:
        print(f'\n❌ 执行失败: {e}')
        import traceback
        traceback.print_exc()
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

