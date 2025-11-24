"""
测试 pump_head 计算流水线

测试内容：
1. 测试最近1小时的数据
2. 测试设备 4, 5, 6（已配置参数）
3. 验证 pump_outlet_pressure 和 pump_head 都写入数据库
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db.pool import initialize_pool, close_pool, get_connection
from app.services.calculation.metrics.pump_head import calculate_pump_head
from app.services.calculation.shared.scheduler import Task


def test_pump_head():
    """测试 pump_head 计算"""
    
    # 初始化数据库连接
    settings = load_settings(Path("configs"))
    initialize_pool(settings)
    
    try:
        # 测试参数（使用历史数据：2025-10-22 18:43 ~ 18:50 UTC，设备有运行数据）
        # 注意：数据库中的时间戳虽然是 timestamptz 类型，但实际存储的是上海时间被误当作 UTC
        TZ_UTC = pytz.UTC
        start_time = datetime(2025, 10, 22, 18, 43, 0, tzinfo=TZ_UTC)
        end_time = datetime(2025, 10, 22, 18, 50, 0, tzinfo=TZ_UTC)
        
        test_devices = [4, 5, 6]  # 已配置参数的设备
        
        print("=" * 80)
        print("🧪 pump_head 计算流水线测试")
        print("=" * 80)
        print(f"测试时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试设备: {test_devices}")
        print("=" * 80)
        
        # 测试每个设备
        for device_id in test_devices:
            print(f"\n{'='*80}")
            print(f"📊 测试设备 {device_id}")
            print(f"{'='*80}")

            # 创建任务对象
            task = Task(
                task_id=f"test_pump_head_device_{device_id}",
                station_id=1,
                device_id=device_id,
                metric_key="pump_head",
                start_time=start_time,
                end_time=end_time
            )

            # 执行计算
            result = calculate_pump_head(task)

            print(f"\n✅ 计算完成")
            print(f"  - 成功: {result.success}")
            print(f"  - 写入记录数: {result.results_count}")
            print(f"  - 任务ID: {result.task_id}")
            if not result.success:
                print(f"  - 错误信息: {result.error_message}")
            
            # 查询写入的数据
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 查询 pump_outlet_pressure
                    cur.execute("""
                        SELECT COUNT(*), MIN(value), MAX(value), AVG(value)
                        FROM fact_measurements fm
                        JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
                        WHERE fm.device_id = %s
                          AND dmc.metric_key = 'pump_outlet_pressure'
                          AND fm.ts_bucket >= %s
                          AND fm.ts_bucket < %s
                    """, (device_id, start_time, end_time))
                    
                    outlet_stats = cur.fetchone()
                    print(f"\n  📈 pump_outlet_pressure 统计:")
                    print(f"    - 记录数: {outlet_stats[0]}")
                    if outlet_stats[0] > 0:
                        print(f"    - 最小值: {outlet_stats[1]:.4f} MPa")
                        print(f"    - 最大值: {outlet_stats[2]:.4f} MPa")
                        print(f"    - 平均值: {outlet_stats[3]:.4f} MPa")
                    
                    # 查询 pump_head
                    cur.execute("""
                        SELECT COUNT(*), MIN(value), MAX(value), AVG(value)
                        FROM fact_measurements fm
                        JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
                        WHERE fm.device_id = %s
                          AND dmc.metric_key = 'pump_head'
                          AND fm.ts_bucket >= %s
                          AND fm.ts_bucket < %s
                    """, (device_id, start_time, end_time))
                    
                    head_stats = cur.fetchone()
                    print(f"\n  📈 pump_head 统计:")
                    print(f"    - 记录数: {head_stats[0]}")
                    if head_stats[0] > 0:
                        print(f"    - 最小值: {head_stats[1]:.2f} m")
                        print(f"    - 最大值: {head_stats[2]:.2f} m")
                        print(f"    - 平均值: {head_stats[3]:.2f} m")
        
        print(f"\n{'='*80}")
        print("✅ 所有测试完成！")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        close_pool()


if __name__ == "__main__":
    test_pump_head()

