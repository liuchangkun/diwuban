#!/usr/bin/env python3
"""
使用新架构运行 pump_flow_rate 计算

这是真正的入口点，使用：
1. Scheduler - 任务调度和编排
2. SharedServices - 共用服务管理
3. pump_flow_rate Pipeline - 完整的6阶段流水线

执行策略：
- 指标间串行（目前只有 pump_flow_rate）
- 设备间并行（可配置并发数）
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import time

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database
from app.core.logging.setup import init_logging

# 导入共用模块
from app.services.calculation.shared.shared_services import SharedServices
from app.services.calculation.shared.scheduler import Scheduler

# 导入 pump_flow_rate 流水线
from app.services.calculation.metrics.pump_flow_rate.pipeline import PumpFlowRatePipeline

TZ_SH = timezone(timedelta(hours=8))


def main():
    """主函数"""
    print("=" * 80)
    print("pump_flow_rate 新架构完整计算")
    print("=" * 80)
    
    # 步骤1: 初始化应用
    print("\n📋 步骤1: 初始化应用")
    config_dir = Path("configs")
    settings = load_settings(config_dir)
    init_logging(config_dir, settings.system.timezone.default)
    init_database(settings)
    print("✅ 应用初始化成功")
    
    # 步骤2: 初始化共用服务
    print("\n📋 步骤2: 初始化共用服务（SharedServices）")
    shared_services = SharedServices()

    # 清除参数缓存（确保使用最新的参数）
    shared_services.parameter_manager.cache.clear()

    print("✅ 共用服务初始化成功")
    print(f"   - Scheduler: {shared_services.scheduler}")
    print(f"   - DataWriter: {shared_services.data_writer}")
    print(f"   - ParameterManager: {shared_services.parameter_manager}")
    print("✅ 清除参数缓存")
    
    # 步骤3: 配置计算参数
    print("\n📋 步骤3: 配置计算参数")
    station_id = 1
    device_ids = [1, 2, 3, 4, 5, 6]  # 所有设备
    start_time = datetime(2025, 10, 22, 16, 0, 0, tzinfo=TZ_SH)  # 2025-10-22 16:00:00 (UTC+8)
    end_time = datetime(2025, 10, 23, 15, 0, 0, tzinfo=TZ_SH)    # 2025-10-23 15:00:00 (UTC+8)
    time_chunk_hours = 1  # 每小时一个任务
    
    print(f"   - 泵站ID: {station_id}")
    print(f"   - 设备ID: {device_ids}")
    print(f"   - 时间范围: {start_time} ~ {end_time}")
    print(f"   - 时间分片: {time_chunk_hours}小时")
    
    # 步骤4: 使用 Scheduler 调度计算
    print("\n📋 步骤4: 使用 Scheduler 调度计算")
    print("=" * 80)

    start = time.time()

    result = shared_services.scheduler.schedule_single_metric(
        metric_key='pump_flow_rate',
        device_ids=device_ids,
        start_time=start_time,
        end_time=end_time,
        time_chunk_hours=time_chunk_hours
    )

    duration = time.time() - start

    # 步骤5: 显示结果
    print("\n" + "=" * 80)
    print("📊 计算结果汇总")
    print("=" * 80)
    print(f"✅ 成功任务数: {result['success_count']}")
    print(f"❌ 失败任务数: {result['failure_count']}")
    print(f"⏱️  总耗时: {duration:.2f}秒")
    print(f"📝 写入记录数: {result.get('total_points', 0)}条")

    # 打印失败任务的详细错误信息
    if result['failure_count'] > 0:
        print("\n" + "=" * 80)
        print("❌ 失败任务详情")
        print("=" * 80)
        for task_result in result['results']:
            if not task_result.success:
                print(f"\n任务ID: {task_result.task_id}")
                print(f"设备ID: {task_result.device_id}")
                print(f"错误信息:\n{task_result.error_message}")

    print("\n" + "=" * 80)
    print(f"结果: {'✅ 成功' if result['failure_count'] == 0 else '❌ 失败'}")
    print("=" * 80)


if __name__ == "__main__":
    main()

