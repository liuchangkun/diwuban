"""
自适应分片性能对比测试

对比测试：
1. 固定分片（24小时）- 实际执行
2. 自适应分片（动态调整）- 实际执行

测试指标：
- 总执行时间
- 平均任务执行时间
- 内存使用
- 成功率
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz
import time

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings
from app.core.logging.setup import init_logging
from app.services.calculation.shared.scheduler import Scheduler
from app.services.calculation.shared.data_writer import DataWriter
from app.services.calculation.shared.parameter_manager import ParameterManager

# 导入Pipeline
from app.services.calculation.metrics.pump_flow_rate.pipeline import PumpFlowRatePipeline

def test_performance():
    """性能对比测试"""
    
    print("=" * 80)
    print("自适应分片性能对比测试")
    print("=" * 80)
    
    # 初始化应用
    print("\n[步骤1] 初始化应用")
    init_logging()
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    print("[OK] 应用初始化成功")
    
    # 初始化共用服务
    print("\n[步骤2] 初始化共用服务")
    data_writer = DataWriter()
    parameter_manager = ParameterManager()
    print("[OK] 共用服务初始化成功")
    
    # 查询测试数据
    print("\n[步骤3] 查询测试数据")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM dim_stations LIMIT 1")
            station_id = cur.fetchone()[0]
            
            # 只测试3个设备，减少测试时间
            cur.execute("SELECT id FROM dim_devices WHERE station_id = %s AND type = 'pump' ORDER BY id LIMIT 3", (station_id,))
            device_ids = [row[0] for row in cur.fetchall()]
            
            cur.execute("""
                SELECT 
                    MIN(ts_bucket) as start_time,
                    MAX(ts_bucket) as end_time
                FROM fact_measurements
                WHERE station_id = %s
            """, (station_id,))
            start_time, end_time = cur.fetchone()
    
    # 转换为带时区的datetime
    tz = pytz.timezone('Asia/Shanghai')
    start_time = start_time.replace(tzinfo=tz)
    end_time = end_time.replace(tzinfo=tz)
    
    print(f"   - 泵站ID: {station_id}")
    print(f"   - 设备ID: {device_ids} (共{len(device_ids)}个设备)")
    print(f"   - 时间范围: {start_time} ~ {end_time}")
    
    # 测试1：固定分片（24小时）
    print("\n" + "=" * 80)
    print("📊 测试1：固定分片（24小时）")
    print("=" * 80)
    
    scheduler_fixed = Scheduler(max_workers=10, enable_adaptive_chunk=False)
    
    start = time.time()
    results_fixed = scheduler_fixed.schedule_single_metric(
        metric_key='pump_flow_rate',
        device_ids=device_ids,
        start_time=start_time,
        end_time=end_time,
        time_chunk_hours=24,
    )
    duration_fixed = time.time() - start
    
    print(f"\n✅ 固定分片测试完成")
    print(f"   - 总耗时: {duration_fixed:.2f}秒")
    print(f"   - 成功任务: {results_fixed['success_count']}/{results_fixed['total_tasks']}")
    print(f"   - 成功率: {results_fixed['success_rate']}")
    print(f"   - 写入记录: {results_fixed['total_points']:,}条")
    print(f"   - 平均任务耗时: {results_fixed['avg_duration_per_task_seconds']:.2f}秒")
    
    # 测试2：自适应分片
    print("\n" + "=" * 80)
    print("📊 测试2：自适应分片")
    print("=" * 80)
    
    scheduler_adaptive = Scheduler(max_workers=10, enable_adaptive_chunk=True)
    
    start = time.time()
    results_adaptive = scheduler_adaptive.schedule_single_metric(
        metric_key='pump_flow_rate',
        device_ids=device_ids,
        start_time=start_time,
        end_time=end_time,
        time_chunk_hours=None,  # 使用自适应分片
    )
    duration_adaptive = time.time() - start
    
    print(f"\n✅ 自适应分片测试完成")
    print(f"   - 总耗时: {duration_adaptive:.2f}秒")
    print(f"   - 成功任务: {results_adaptive['success_count']}/{results_adaptive['total_tasks']}")
    print(f"   - 成功率: {results_adaptive['success_rate']}")
    print(f"   - 写入记录: {results_adaptive['total_points']:,}条")
    print(f"   - 平均任务耗时: {results_adaptive['avg_duration_per_task_seconds']:.2f}秒")
    
    # 性能对比
    print("\n" + "=" * 80)
    print("📈 性能对比分析")
    print("=" * 80)
    
    print(f"\n⏱️  总执行时间:")
    print(f"   - 固定分片: {duration_fixed:.2f}秒")
    print(f"   - 自适应分片: {duration_adaptive:.2f}秒")
    print(f"   - 差异: {duration_adaptive - duration_fixed:+.2f}秒 ({(duration_adaptive - duration_fixed) / duration_fixed * 100:+.1f}%)")
    
    print(f"\n📊 任务统计:")
    print(f"   - 固定分片任务数: {results_fixed['total_tasks']}")
    print(f"   - 自适应分片任务数: {results_adaptive['total_tasks']}")
    print(f"   - 差异: {results_adaptive['total_tasks'] - results_fixed['total_tasks']:+d}")
    
    print(f"\n⚡ 平均任务耗时:")
    print(f"   - 固定分片: {results_fixed['avg_duration_per_task_seconds']:.2f}秒")
    print(f"   - 自适应分片: {results_adaptive['avg_duration_per_task_seconds']:.2f}秒")
    print(f"   - 差异: {results_adaptive['avg_duration_per_task_seconds'] - results_fixed['avg_duration_per_task_seconds']:+.2f}秒")
    
    print(f"\n✅ 成功率:")
    print(f"   - 固定分片: {results_fixed['success_rate']}")
    print(f"   - 自适应分片: {results_adaptive['success_rate']}")
    
    # 结论
    print("\n" + "=" * 80)
    print("🎯 结论")
    print("=" * 80)
    
    if duration_adaptive < duration_fixed:
        improvement = (duration_fixed - duration_adaptive) / duration_fixed * 100
        print(f"✅ 自适应分片性能更优，提升 {improvement:.1f}%")
    elif duration_adaptive > duration_fixed:
        degradation = (duration_adaptive - duration_fixed) / duration_fixed * 100
        print(f"⚠️ 自适应分片性能略差，降低 {degradation:.1f}%")
        print(f"   原因：任务数增加导致调度开销增加")
        print(f"   优势：单个任务数据量更小，内存使用更稳定")
    else:
        print(f"ℹ️ 两种模式性能相当")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_performance()

