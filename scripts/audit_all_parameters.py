"""
全面审查所有指标的参数配置状态

检查数据库中已配置和缺失的参数
"""

import sys
import os
from pathlib import Path
from collections import defaultdict

# 设置控制台编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


# 定义每个指标需要的参数（使用代码中实际使用的参数名）
REQUIRED_PARAMS = {
    'pump_flow_rate': {
        'global': ['max_flow', 'max_power', 'max_freq'],
        'device': []
    },
    'pump_inlet_pressure': {
        'global': ['min_pressure', 'max_pressure'],
        'device': ['L_offset', 'pipe_diameter']
    },
    'pump_head': {
        'global': ['min_pump_head', 'max_pump_head', 'min_pump_outlet_pressure', 'max_pump_outlet_pressure'],
        'device': []
    },
    'pump_efficiency': {
        'global': ['eta_min', 'eta_max'],
        'device': []
    },
    'pump_speed': {
        'global': ['min_speed', 'max_speed'],
        'device': []
    },
    'pump_torque': {
        'global': ['max_torque'],
        'device': []
    },
    'pump_hydraulic_power': {
        'global': ['min_power', 'max_power'],
        'device': []
    },
    'pump_shaft_power': {
        'global': ['max_power', 'max_shaft_power'],
        'device': ['eta_motor', 'eta_vfd']
    },
    'main_pipeline_inlet_pressure': {
        'global': ['P_in_min', 'P_in_max'],
        'device': []
    }
}


def main():
    """主函数"""
    print("="*120)
    print("所有指标参数配置审查")
    print("="*120)
    
    # 初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    device_ids = [1, 2, 3, 4, 5, 6]
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. 检查calculation_parameters表中的参数
            print(f"\n{'='*120}")
            print("1. calculation_parameters 表中的参数")
            print(f"{'='*120}")
            
            cur.execute("""
                SELECT metric_key, device_id, param_name, param_value, param_type
                FROM calculation_parameters
                WHERE metric_key IN (
                    'pump_flow_rate', 'pump_inlet_pressure', 'pump_head', 
                    'pump_efficiency', 'pump_speed', 'pump_torque',
                    'pump_hydraulic_power', 'pump_shaft_power', 'main_pipeline_inlet_pressure'
                )
                ORDER BY metric_key, device_id, param_name
            """)
            
            existing_params = defaultdict(lambda: defaultdict(set))
            for row in cur.fetchall():
                metric_key, device_id, param_name, param_value, param_type = row
                if device_id is None:
                    existing_params[metric_key]['global'].add(param_name)
                else:
                    existing_params[metric_key][device_id].add(param_name)
            
            # 2. 检查device_rated_params表中的参数
            cur.execute("""
                SELECT device_id, param_key, value_numeric
                FROM device_rated_params
                WHERE device_id IN (1,2,3,4,5,6)
                ORDER BY device_id, param_key
            """)

            device_rated_params = defaultdict(set)
            for row in cur.fetchall():
                device_id, param_key, value_numeric = row
                device_rated_params[device_id].add(param_key)
            
            # 3. 分析每个指标的参数配置状态
            print(f"\n{'='*120}")
            print("2. 各指标参数配置状态")
            print(f"{'='*120}")
            
            total_missing = 0
            
            for metric_key in sorted(REQUIRED_PARAMS.keys()):
                print(f"\n{'='*120}")
                print(f"指标: {metric_key}")
                print(f"{'='*120}")
                
                required = REQUIRED_PARAMS[metric_key]
                existing = existing_params[metric_key]
                
                # 检查全局参数
                if required['global']:
                    print(f"\n全局参数:")
                    print(f"  需要: {', '.join(required['global'])}")
                    print(f"  已配置: {', '.join(existing['global']) if existing['global'] else '无'}")
                    
                    missing_global = set(required['global']) - existing['global']
                    if missing_global:
                        print(f"  ❌ 缺失: {', '.join(missing_global)}")
                        total_missing += len(missing_global)
                    else:
                        print(f"  ✅ 全部已配置")
                
                # 检查设备参数
                if required['device']:
                    print(f"\n设备参数:")
                    print(f"  需要: {', '.join(required['device'])}")
                    
                    for device_id in device_ids:
                        # 检查calculation_parameters
                        calc_params = existing.get(device_id, set())
                        # 检查device_rated_params
                        rated_params = device_rated_params.get(device_id, set())
                        # 合并
                        all_device_params = calc_params | rated_params
                        
                        missing_device = set(required['device']) - all_device_params
                        
                        if missing_device:
                            print(f"  设备{device_id}: ❌ 缺失 {', '.join(missing_device)}")
                            total_missing += len(missing_device)
                        else:
                            print(f"  设备{device_id}: ✅ 全部已配置")
            
            # 4. 总结
            print(f"\n{'='*120}")
            print("3. 总结")
            print(f"{'='*120}")
            
            print(f"\n总缺失参数数: {total_missing}")
            
            if total_missing == 0:
                print(f"\n✅ 所有参数已配置完整！")
            else:
                print(f"\n⚠️ 发现 {total_missing} 个缺失参数，需要补充")


if __name__ == '__main__':
    main()

