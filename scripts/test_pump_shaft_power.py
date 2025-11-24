"""
pump_shaft_power 端到端测试脚本

用途：
- 测试pump_shaft_power完整计算流程
- 验证所有设备（1-6）的计算结果
- 生成数据质量报告

协议：RIPER-5 执行模式
创建日期：2025-11-22
"""

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database
from app.core.config.loader_new import load_settings
from app.services.calculation.shared.shared_services import SharedServices
from app.services.calculation.metrics.pump_shaft_power import PumpShaftPowerPipeline

# 时区设置
TZ_SH = ZoneInfo("Asia/Shanghai")

# 初始化数据库
settings = load_settings(Path("configs"))
init_database(settings)


def test_single_device(device_id: int, start_time: datetime, end_time: datetime):
    """
    测试单个设备
    
    Args:
        device_id: 设备ID
        start_time: 开始时间
        end_time: 结束时间
    """
    print(f"\n{'='*80}")
    print(f"测试设备 {device_id}")
    print(f"{'='*80}")
    
    # 创建Pipeline
    pipeline = PumpShaftPowerPipeline()
    
    # 执行计算
    task_id = f"test_device_{device_id}"
    result = pipeline.execute(
        station_id=1,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
        task_id=task_id
    )
    
    # 输出结果
    print(f"\n结果:")
    print(f"  - 成功: {result.get('success', False)}")
    print(f"  - 跳过: {result.get('skipped', False)}")
    print(f"  - 写入记录数: {result.get('written_count', 0)}")
    
    if result.get('error_message'):
        print(f"  - 错误信息: {result['error_message']}")
    
    return result


def test_all_devices():
    """测试所有设备（1-6）"""
    print("\n" + "="*80)
    print("pump_shaft_power 端到端测试")
    print("="*80)
    
    # 步骤1: 初始化SharedServices
    print("\n📋 步骤1: 初始化SharedServices")
    shared_services = SharedServices()
    print("✅ SharedServices初始化完成")
    
    # 步骤2: 配置测试参数
    print("\n📋 步骤2: 配置测试参数")
    station_id = 1
    device_ids = [1, 2, 3, 4, 5, 6]
    # 数据库中ts_bucket是UTC时间，08:00 UTC = 16:00 上海时间
    # 使用UTC时间范围，测试24小时数据
    from datetime import timezone
    start_time = datetime(2025, 10, 22, 8, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 10, 23, 8, 0, 0, tzinfo=timezone.utc)  # 24小时测试
    
    print(f"   - 泵站ID: {station_id}")
    print(f"   - 设备ID: {device_ids}")
    print(f"   - 时间范围: {start_time} ~ {end_time}")
    
    # 步骤3: 测试ParameterManager
    print("\n📋 步骤3: 测试ParameterManager")
    try:
        params = shared_services.parameter_manager.get_parameters(
            station_id=station_id,
            device_id=1,
            metric_key='pump_shaft_power'
        )
        print(f"✅ 参数加载成功:")
        print(f"   - max_power: {params.get('max_power')}")
        print(f"   - max_change_rate: {params.get('max_change_rate')}")
        print(f"   - device_params: {len(params.get('device_params', {}))} 个设备")
    except Exception as e:
        print(f"❌ 参数加载失败: {e}")
        return
    
    # 步骤4: 测试所有设备
    print("\n📋 步骤4: 测试所有设备")
    results = []
    success_count = 0
    failed_devices = []
    
    for device_id in device_ids:
        try:
            result = test_single_device(device_id, start_time, end_time)
            results.append(result)
            
            if result.get('success'):
                success_count += 1
            else:
                failed_devices.append(device_id)
        except Exception as e:
            print(f"❌ 设备 {device_id} 测试失败: {e}")
            failed_devices.append(device_id)
    
    # 步骤5: 汇总结果
    print("\n" + "="*80)
    print("测试汇总")
    print("="*80)
    print(f"总设备数: {len(device_ids)}")
    print(f"成功设备数: {success_count}")
    print(f"失败设备数: {len(failed_devices)}")
    
    if failed_devices:
        print(f"失败设备: {failed_devices}")
    
    total_written = sum(r.get('written_count', 0) for r in results)
    print(f"总写入记录数: {total_written}")
    
    # 步骤6: 数据质量验证
    print("\n📋 步骤6: 数据质量验证")
    verify_data_quality(station_id, device_ids, start_time, end_time)
    
    print("\n✅ 测试完成")


def verify_data_quality(station_id: int, device_ids: list, start_time: datetime, end_time: datetime):
    """
    验证数据质量
    
    Args:
        station_id: 泵站ID
        device_ids: 设备ID列表
        start_time: 开始时间
        end_time: 结束时间
    """
    from app.adapters.db.pool import get_connection
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询计算结果
            cur.execute("""
                SELECT 
                    device_id,
                    COUNT(*) as record_count,
                    AVG(value::float) as avg_value,
                    MIN(value::float) as min_value,
                    MAX(value::float) as max_value
                FROM fact_measurements
                WHERE station_id = %s
                  AND device_id = ANY(%s)
                  AND metric_id = 66  -- pump_shaft_power
                  AND ts_bucket >= %s
                  AND ts_bucket < %s
                GROUP BY device_id
                ORDER BY device_id
            """, (station_id, device_ids, start_time, end_time))
            
            results = cur.fetchall()
            
            if results:
                print("\n数据质量统计:")
                print(f"{'设备ID':<10} {'记录数':<10} {'平均值':<15} {'最小值':<15} {'最大值':<15}")
                print("-" * 70)
                
                for row in results:
                    device_id, count, avg, min_val, max_val = row
                    print(f"{device_id:<10} {count:<10} {avg:<15.2f} {min_val:<15.2f} {max_val:<15.2f}")
            else:
                print("⚠️  未找到计算结果")


if __name__ == "__main__":
    test_all_devices()

