#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调度器双指标测试脚本

测试 pump_flow_rate 和 pump_inlet_pressure 两个指标的完整流程
测试范围：所有设备，所有时间
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pytz

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, get_connection
from app.core.logging.setup import init_logging
from app.services.calculation.shared.scheduler import Scheduler
from app.services.calculation.shared.shared_services import SharedServices


def test_scheduler():
    """测试调度器执行两个指标的计算 - 所有设备，所有时间"""

    print("=" * 80)
    print("调度器双指标测试 - 所有设备，所有时间")
    print("=" * 80)

    # 步骤1: 初始化应用
    print("\n[步骤1] 初始化应用")
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_logging(config_dir, settings.system.timezone.default)
    init_database(settings)
    print("[OK] 应用初始化成功")

    # 步骤2: 初始化共用服务
    print("\n[步骤2] 初始化共用服务")
    shared_services = SharedServices()  # 单例模式，直接实例化
    print("[OK] 共用服务初始化成功")
    print(f"   - Scheduler: {shared_services.scheduler}")
    print(f"   - DataWriter: {shared_services.data_writer}")
    print(f"   - ParameterManager: {shared_services.parameter_manager}")

    # 步骤3: 查询所有设备和时间范围
    print("\n[步骤3] 查询所有设备和时间范围")

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询所有设备ID（从 fact_measurements 表中获取实际有数据的设备）
            cur.execute("""
                SELECT DISTINCT device_id
                FROM fact_measurements
                WHERE station_id = 1
                ORDER BY device_id
            """)
            device_ids = [row[0] for row in cur.fetchall()]

            # 查询数据的时间范围
            cur.execute("""
                SELECT
                    MIN(ts_bucket) as min_time,
                    MAX(ts_bucket) as max_time
                FROM fact_measurements
                WHERE station_id = 1
            """)
            row = cur.fetchone()
            start_time = row[0]
            end_time = row[1]

    # 只测试两个已重构的指标
    metrics = ["pump_flow_rate", "pump_inlet_pressure"]

    print(f"   - 泵站ID: 1")
    print(f"   - 设备ID: {device_ids} (共{len(device_ids)}个设备)")
    print(f"   - 时间范围: {start_time} ~ {end_time}")
    print(f"   - 测试指标: {metrics}")
    
    # 步骤4: 执行调度
    print("\n[步骤4] 执行调度器")
    print("=" * 80)
    print(f"预计任务数: {len(device_ids)} 设备 × {len(metrics)} 指标 = {len(device_ids) * len(metrics)} 任务")
    print("开始执行...")

    import time
    start_exec_time = time.time()

    scheduler = shared_services.scheduler

    # 调用调度器的 schedule_all_metrics 方法
    # 使用24小时分片（适合大时间范围）
    results = scheduler.schedule_all_metrics(
        device_ids=device_ids,
        start_time=start_time,
        end_time=end_time,
        time_chunk_hours=24,  # 24小时分片
        metrics=metrics  # 只计算这两个指标
    )

    exec_duration = time.time() - start_exec_time
    print(f"执行完成，耗时: {exec_duration:.1f}秒")
    print("=" * 80)
    
    # 步骤5: 分析结果
    print("\n[步骤5] 分析结果")

    total_tasks = len(results)
    success_tasks = sum(1 for r in results if r.get("status") == "success")
    failed_tasks = total_tasks - success_tasks

    print(f"\n总任务数: {total_tasks}")
    print(f"[OK] 成功: {success_tasks}")
    print(f"[FAIL] 失败: {failed_tasks}")
    print(f"成功率: {success_tasks/total_tasks*100:.1f}%")
    
    # 按指标分组统计
    print("\n按指标统计:")
    metric_stats = {}
    for result in results:
        metric = result.get("metric_key", "unknown")
        if metric not in metric_stats:
            metric_stats[metric] = {"success": 0, "failed": 0, "written": 0}
        
        if result.get("status") == "success":
            metric_stats[metric]["success"] += 1
            metric_stats[metric]["written"] += result.get("written_count", 0)
        else:
            metric_stats[metric]["failed"] += 1
    
    for metric, stats in metric_stats.items():
        total = stats["success"] + stats["failed"]
        print(f"  - {metric}: {stats['success']}/{total} 成功, 写入 {stats['written']} 条记录")
    
    # 显示失败任务详情
    if failed_tasks > 0:
        print("\n失败任务详情:")
        for result in results:
            if result.get("status") != "success":
                print(f"  - 设备{result.get('device_id')}, 指标{result.get('metric_key')}: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    test_scheduler()

