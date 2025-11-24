"""
测试自适应分片功能

对比测试：
1. 固定分片（24小时）
2. 自适应分片（根据数据量和设备数量动态调整）
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings
from app.core.logging.setup import init_logging
from app.services.calculation.shared.scheduler import Scheduler
from app.services.calculation.shared.data_writer import DataWriter
from app.services.calculation.shared.parameter_manager import ParameterManager

def test_adaptive_chunk():
    """测试自适应分片功能"""
    
    print("=" * 80)
    print("自适应分片测试")
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
    scheduler_adaptive = Scheduler(max_workers=10, enable_adaptive_chunk=True)
    scheduler_fixed = Scheduler(max_workers=10, enable_adaptive_chunk=False)
    data_writer = DataWriter()
    parameter_manager = ParameterManager()
    print("[OK] 共用服务初始化成功")
    
    # 查询所有设备和时间范围
    print("\n[步骤3] 查询所有设备和时间范围")
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 获取泵站ID
            cur.execute("SELECT id FROM dim_stations LIMIT 1")
            station_id = cur.fetchone()[0]
            
            # 获取所有设备
            cur.execute("SELECT id FROM dim_devices WHERE station_id = %s ORDER BY id", (station_id,))
            device_ids = [row[0] for row in cur.fetchall()]
            
            # 获取时间范围
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
    
    # 测试指标
    test_metrics = ['pump_flow_rate']
    
    print("\n[步骤4] 对比测试")
    print("=" * 80)
    
    # 测试1：固定分片（24小时）
    print("\n📊 测试1：固定分片（24小时）")
    print("-" * 80)
    
    tasks_fixed = scheduler_fixed.create_tasks(
        metric_key='pump_flow_rate',
        device_ids=device_ids,
        start_time=start_time,
        end_time=end_time,
        time_chunk_hours=24,
    )
    
    print(f"   - 创建任务数: {len(tasks_fixed)}")
    print(f"   - 分片大小: 24小时（固定）")
    print(f"   - 每设备任务数: {len(tasks_fixed) // len(device_ids)}")
    
    # 测试2：自适应分片
    print("\n📊 测试2：自适应分片")
    print("-" * 80)
    
    tasks_adaptive = scheduler_adaptive.create_tasks(
        metric_key='pump_flow_rate',
        device_ids=device_ids,
        start_time=start_time,
        end_time=end_time,
        time_chunk_hours=None,  # 使用自适应分片
    )
    
    print(f"   - 创建任务数: {len(tasks_adaptive)}")
    print(f"   - 分片大小: 自适应")
    print(f"   - 每设备任务数: {len(tasks_adaptive) // len(device_ids)}")
    
    # 对比分析
    print("\n📈 对比分析")
    print("-" * 80)
    print(f"   - 固定分片任务数: {len(tasks_fixed)}")
    print(f"   - 自适应分片任务数: {len(tasks_adaptive)}")
    print(f"   - 任务数差异: {len(tasks_adaptive) - len(tasks_fixed)} ({(len(tasks_adaptive) - len(tasks_fixed)) / len(tasks_fixed) * 100:.1f}%)")
    
    if len(tasks_adaptive) < len(tasks_fixed):
        print(f"   ✅ 自适应分片减少了 {len(tasks_fixed) - len(tasks_adaptive)} 个任务")
        print(f"   ✅ 预计减少调度开销 {(len(tasks_fixed) - len(tasks_adaptive)) / len(tasks_fixed) * 100:.1f}%")
    elif len(tasks_adaptive) > len(tasks_fixed):
        print(f"   ⚠️ 自适应分片增加了 {len(tasks_adaptive) - len(tasks_fixed)} 个任务")
        print(f"   ⚠️ 可能是为了避免单个任务数据量过大")
    else:
        print(f"   ℹ️ 任务数相同，自适应分片未调整")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成！")
    print("=" * 80)

if __name__ == "__main__":
    test_adaptive_chunk()

