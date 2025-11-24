"""
生成端到端测试数据

任务3-8: 生成30天模拟数据
- 任务3: device_id=7 (单泵SS)
- 任务4: device_id=8-9 (同构SS泵组)
- 任务5: device_id=10-12 (异构VFD泵组)
- 任务6: device_id=13-15 (异构SS泵组)
- 任务7: device_id=16-18 (混合泵组)
- 任务8: device_id=1-3 (扩展真实数据到30天)
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from tests.fixtures.e2e_data_generator import E2EDataGenerator
from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings

def main():
    """主函数"""
    print("="*80)
    print("生成端到端测试数据（30天）")
    print("="*80)
    
    # 初始化数据库连接池
    settings = load_settings(Path("configs"))
    init_database(settings)
    print("✅ 数据库连接池已初始化\n")
    
    # 时间范围：30天
    start_time = datetime(2025, 10, 22, 8, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 11, 21, 8, 0, 0, tzinfo=timezone.utc)
    
    print(f"📅 时间范围: {start_time} ~ {end_time}")
    print(f"📏 时间跨度: 30天 (2,592,000秒)\n")
    
    with E2EDataGenerator() as generator:
        # 任务3: 生成device_id=7的数据（单泵SS）
        print("="*80)
        print("任务3: 生成device_id=7的数据（单泵SS）")
        print("="*80)
        
        rated_params_7 = {
            'rated_power': 75,
            'rated_flow': 400,
            'rated_head': 25,
            'rated_frequency': 50
        }
        
        data_7 = generator.generate_pump_data(
            device_id=7,
            start_time=start_time,
            end_time=end_time,
            rated_params=rated_params_7,
            control_type='soft_start',
            noise_level=0.02,
            running_ratio=0.8
        )
        
        print(f"✅ 生成数据: {len(data_7)} 条记录")
        generator.insert_to_database(data_7, batch_size=10000)
        print("✅ 数据已插入数据库\n")
        
        # 任务4: 生成device_id=8-9的数据（同构SS泵组）
        print("="*80)
        print("任务4: 生成device_id=8-9的数据（同构SS泵组）")
        print("="*80)
        
        for device_id in [8, 9]:
            print(f"\n生成device_id={device_id}的数据...")
            data = generator.generate_pump_data(
                device_id=device_id,
                start_time=start_time,
                end_time=end_time,
                rated_params=rated_params_7,  # 同构：相同参数
                control_type='soft_start',
                noise_level=0.02,
                running_ratio=0.8
            )
            print(f"✅ 生成数据: {len(data)} 条记录")
            generator.insert_to_database(data, batch_size=10000)
            print(f"✅ device_id={device_id} 数据已插入")
        
        print("\n✅ 同构SS泵组数据生成完成\n")
        
        # 任务5: 生成device_id=10-12的数据（异构VFD泵组）
        print("="*80)
        print("任务5: 生成device_id=10-12的数据（异构VFD泵组）")
        print("="*80)
        
        heterogeneous_vfd_params = [
            {'device_id': 10, 'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50},
            {'device_id': 11, 'rated_power': 90, 'rated_flow': 480, 'rated_head': 25, 'rated_frequency': 50},
            {'device_id': 12, 'rated_power': 110, 'rated_flow': 550, 'rated_head': 25, 'rated_frequency': 50},
        ]
        
        for params in heterogeneous_vfd_params:
            device_id = params['device_id']
            print(f"\n生成device_id={device_id}的数据 (功率={params['rated_power']}kW)...")
            data = generator.generate_pump_data(
                device_id=device_id,
                start_time=start_time,
                end_time=end_time,
                rated_params=params,
                control_type='variable_frequency',
                noise_level=0.02,
                running_ratio=0.8
            )
            print(f"✅ 生成数据: {len(data)} 条记录")
            generator.insert_to_database(data, batch_size=10000)
            print(f"✅ device_id={device_id} 数据已插入")
        
        print("\n✅ 异构VFD泵组数据生成完成\n")

        # ========================================================================
        # 任务6: 生成device_id=13-15的数据（异构SS泵组）
        # ========================================================================
        print("=" * 80)
        print("任务6: 生成device_id=13-15的数据（异构SS泵组）")
        print("=" * 80)
        print()

        heterogeneous_ss_params = [
            {'device_id': 13, 'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50},
            {'device_id': 14, 'rated_power': 90, 'rated_flow': 480, 'rated_head': 25, 'rated_frequency': 50},
            {'device_id': 15, 'rated_power': 110, 'rated_flow': 550, 'rated_head': 25, 'rated_frequency': 50},
        ]

        for params in heterogeneous_ss_params:
            device_id = params['device_id']
            print(f"\n生成device_id={device_id}的数据 (功率={params['rated_power']}kW)...")
            data = generator.generate_pump_data(
                device_id=device_id,
                start_time=start_time,
                end_time=end_time,
                rated_params=params,
                control_type='soft_start',
                noise_level=0.02,
                running_ratio=0.8
            )
            print(f"✅ 生成数据: {len(data)} 条记录")
            generator.insert_to_database(data, batch_size=30000)
            print(f"✅ device_id={device_id} 数据已插入")

        print("\n✅ 异构SS泵组数据生成完成\n")

        # ========================================================================
        # 任务7: 生成device_id=16-18的数据（混合泵组）
        # ========================================================================
        print("=" * 80)
        print("任务7: 生成device_id=16-18的数据（混合泵组）")
        print("=" * 80)
        print()

        mixed_group_params = [
            {'device_id': 16, 'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50, 'control_type': 'variable_frequency'},
            {'device_id': 17, 'rated_power': 90, 'rated_flow': 480, 'rated_head': 25, 'rated_frequency': 50, 'control_type': 'variable_frequency'},
            {'device_id': 18, 'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50, 'control_type': 'soft_start'},
        ]

        for params in mixed_group_params:
            device_id = params['device_id']
            control_type = params.pop('control_type')
            print(f"\n生成device_id={device_id}的数据 (功率={params['rated_power']}kW, 类型={control_type})...")
            data = generator.generate_pump_data(
                device_id=device_id,
                start_time=start_time,
                end_time=end_time,
                rated_params=params,
                control_type=control_type,
                noise_level=0.02,
                running_ratio=0.8
            )
            print(f"✅ 生成数据: {len(data)} 条记录")
            generator.insert_to_database(data, batch_size=30000)
            print(f"✅ device_id={device_id} 数据已插入")

        print("\n✅ 混合泵组数据生成完成\n")

        # ========================================================================
        # 完成
        # ========================================================================
        print("=" * 80)
        print("✅ 所有模拟数据生成完成！")
        print("=" * 80)
        print()
        print("📊 数据统计:")
        print(f"  - 设备数量: 12台 (device_id=7-18)")
        print(f"  - 时间范围: 30天 (2025-10-22 ~ 2025-11-21)")
        print(f"  - 总记录数: ~155,520,000条 (12设备 × 2,592,000秒 × 5指标)")
        print()
        print("下一步: 执行任务8（扩展真实数据）")

if __name__ == "__main__":
    main()

