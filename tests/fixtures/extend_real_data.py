"""
扩展真实数据到30天

将device_id=1-3的真实数据从23小时扩展到30天。
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from tests.fixtures.e2e_data_generator import E2EDataGenerator
from app.adapters.db import init_database
from app.core.config.loader_new import load_settings


def main():
    """扩展真实数据到30天"""
    
    print("=" * 80)
    print("扩展真实数据到30天")
    print("=" * 80)
    
    # 初始化数据库连接池
    settings = load_settings(Path("configs"))
    init_database(settings)
    print("✅ 数据库连接池已初始化\n")
    
    # 目标时间范围
    target_end_time = datetime(2025, 11, 21, 8, 0, 0, tzinfo=timezone.utc)
    
    # 真实数据的结束时间（2025-10-23 07:00:00 UTC，23小时）
    real_end_time = datetime(2025, 10, 23, 7, 0, 0, tzinfo=timezone.utc)
    
    print(f"📅 真实数据结束时间: {real_end_time}")
    print(f"📅 目标结束时间: {target_end_time}")
    print(f"📏 需要扩展: {(target_end_time - real_end_time).days}天\n")
    
    # 设备1-3的额定参数（从数据库查询得到）
    devices = [
        {
            'device_id': 1,
            'rated_power': 75,
            'rated_flow': 400,
            'rated_head': 25,
            'rated_frequency': 50,
            'control_type': 'variable_frequency'
        },
        {
            'device_id': 2,
            'rated_power': 75,
            'rated_flow': 400,
            'rated_head': 25,
            'rated_frequency': 50,
            'control_type': 'variable_frequency'
        },
        {
            'device_id': 3,
            'rated_power': 75,
            'rated_flow': 400,
            'rated_head': 25,
            'rated_frequency': 50,
            'control_type': 'variable_frequency'
        },
    ]
    
    with E2EDataGenerator() as generator:
        for device in devices:
            device_id = device['device_id']
            print(f"\n{'=' * 80}")
            print(f"扩展device_id={device_id}的数据")
            print(f"{'=' * 80}\n")
            
            # 扩展数据
            generator.extend_real_data(
                device_id=device_id,
                real_end_time=real_end_time,
                target_end_time=target_end_time,
                rated_params={
                    'rated_power': device['rated_power'],
                    'rated_flow': device['rated_flow'],
                    'rated_head': device['rated_head'],
                    'rated_frequency': device['rated_frequency']
                },
                control_type=device['control_type']
            )
            
            print(f"✅ device_id={device_id} 数据扩展完成")
        
        # 刷新运行状态视图
        print(f"\n{'=' * 80}")
        print("刷新运行状态物化视图")
        print(f"{'=' * 80}\n")
        generator.refresh_running_state_view()
        print("✅ 运行状态视图已刷新")
    
    print(f"\n{'=' * 80}")
    print("✅ 所有真实数据扩展完成！")
    print(f"{'=' * 80}\n")
    print("📊 数据统计:")
    print(f"  - 设备数量: 3台 (device_id=1-3)")
    print(f"  - 原始数据: 23小时")
    print(f"  - 扩展后: 30天")
    print(f"  - 新增记录数: ~{3 * (30 * 86400 - 23 * 3600) * 5:,}条")
    print()
    print("下一步: 执行任务9（验证数据完整性）")


if __name__ == "__main__":
    main()

