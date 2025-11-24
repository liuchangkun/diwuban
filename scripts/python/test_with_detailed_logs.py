#!/usr/bin/env python3
"""
测试并查看详细日志
"""
import sys
from pathlib import Path
from datetime import datetime
import pytz

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings
from app.services.calculation.shared.shared_services import SharedServices


def delete_old_data():
    """删除旧数据"""
    print("\n🗑️  删除旧数据...")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM dim_metric_config WHERE metric_key = 'pump_inlet_pressure'")
            metric_id = cur.fetchone()[0]

            cur.execute("""
                DELETE FROM fact_measurements
                WHERE metric_id = %s
                  AND device_id = 1
                  AND ts_raw >= '2025-10-22 18:00:00+08:00'
                  AND ts_raw < '2025-10-22 19:00:00+08:00'
            """, (metric_id,))

            conn.commit()
            print(f"✅ 旧数据已删除")


def run_calculation():
    """运行计算（只测试设备1，18:00-19:00，这个时间段有无效值）"""
    print("\n🔧 运行计算（设备1，18:00-19:00）...")

    shared_services = SharedServices()

    tz = pytz.timezone('Asia/Shanghai')
    start_time = datetime(2025, 10, 22, 18, 0, 0, tzinfo=tz)
    end_time = datetime(2025, 10, 22, 19, 0, 0, tzinfo=tz)
    
    result = shared_services.scheduler.schedule_single_metric(
        metric_key='pump_inlet_pressure',
        device_ids=[1],
        start_time=start_time,
        end_time=end_time,
        time_chunk_hours=24
    )
    
    print(f"✅ 计算完成: {result['success_count']}/{result['total_tasks']} 任务成功")
    return result


def main():
    print("=" * 100)
    print("🔍 测试并查看详细日志")
    print("=" * 100)
    
    # 初始化
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    
    # 1. 删除旧数据
    delete_old_data()
    
    # 2. 运行计算
    calc_result = run_calculation()
    
    print("\n" + "=" * 100)
    print("📋 请查看上方日志，重点关注：")
    print("=" * 100)
    print("1. [数据加载] 数据透视完成 - 查看 pool_liquid_level_rows 和 sample_rows")
    print("2. [结果验证] 发现无效值 - 查看输入数据和失败原因")
    print("=" * 100)


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

