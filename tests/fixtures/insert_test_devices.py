#!/usr/bin/env python3
"""
插入测试设备到数据库

功能：
1. 插入12台测试设备（device_id=7-18）
2. 插入额定参数到device_rated_params
3. 插入运行阈值到device_running_thresholds
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from tests.fixtures.e2e_data_generator import E2EDataGenerator
from app.adapters.db import init_database
from app.core.config.loader_new import load_settings


def main():
    """主函数"""
    print("="*80)
    print("插入测试设备到数据库")
    print("="*80)

    # 初始化数据库连接池
    settings = load_settings(Path("configs"))
    init_database(settings)
    print("✅ 数据库连接池已初始化\n")
    
    # 定义设备配置
    device_configs = [
        # 设备7-9: 同构软启泵组
        {'device_id': 7, 'name': '测试泵7#（软启）', 'pump_type': 'soft_start',
         'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50},
        {'device_id': 8, 'name': '测试泵8#（软启）', 'pump_type': 'soft_start',
         'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50},
        {'device_id': 9, 'name': '测试泵9#（软启）', 'pump_type': 'soft_start',
         'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50},
        
        # 设备10-12: 异构变频泵组
        {'device_id': 10, 'name': '测试泵10#（变频-75kW）', 'pump_type': 'variable_frequency',
         'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50},
        {'device_id': 11, 'name': '测试泵11#（变频-90kW）', 'pump_type': 'variable_frequency',
         'rated_power': 90, 'rated_flow': 480, 'rated_head': 25, 'rated_frequency': 50},
        {'device_id': 12, 'name': '测试泵12#（变频-110kW）', 'pump_type': 'variable_frequency',
         'rated_power': 110, 'rated_flow': 550, 'rated_head': 25, 'rated_frequency': 50},
        
        # 设备13-15: 异构软启泵组
        {'device_id': 13, 'name': '测试泵13#（软启-75kW）', 'pump_type': 'soft_start',
         'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50},
        {'device_id': 14, 'name': '测试泵14#（软启-90kW）', 'pump_type': 'soft_start',
         'rated_power': 90, 'rated_flow': 480, 'rated_head': 25, 'rated_frequency': 50},
        {'device_id': 15, 'name': '测试泵15#（软启-110kW）', 'pump_type': 'soft_start',
         'rated_power': 110, 'rated_flow': 550, 'rated_head': 25, 'rated_frequency': 50},
        
        # 设备16-18: 混合泵组
        {'device_id': 16, 'name': '测试泵16#（变频-75kW）', 'pump_type': 'variable_frequency',
         'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50},
        {'device_id': 17, 'name': '测试泵17#（变频-90kW）', 'pump_type': 'variable_frequency',
         'rated_power': 90, 'rated_flow': 480, 'rated_head': 25, 'rated_frequency': 50},
        {'device_id': 18, 'name': '测试泵18#（软启-75kW）', 'pump_type': 'soft_start',
         'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50},
    ]
    
    # 创建设备
    with E2EDataGenerator() as generator:
        generator.create_test_devices(device_configs)
    
    print("\n" + "="*80)
    print("✅ 测试设备插入完成！")
    print("="*80)
    print("\n设备清单:")
    print("-"*80)
    for config in device_configs:
        print(f"  设备ID: {config['device_id']:2d} | "
              f"名称: {config['name']:25s} | "
              f"类型: {config['pump_type']:20s} | "
              f"功率: {config['rated_power']:3d}kW")
    print("-"*80)


if __name__ == '__main__':
    main()

