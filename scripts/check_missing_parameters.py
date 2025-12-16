"""
检查数据库中缺失的参数

对比代码中使用的参数和数据库中已配置的参数
"""

import sys
import os
from pathlib import Path

# 设置控制台编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


# 每个指标需要的参数
REQUIRED_PARAMS = {
    'pump_flow_rate': {
        'global': [],
        'device': ['alpha', 'beta', 'smooth_window']
    },
    'pump_inlet_pressure': {
        'global': ['rho', 'g'],
        'device': ['L_offset', 'pipe_diameter', 'max_liquid_level']
    },
    'pump_head': {
        'global': ['rho', 'g'],
        'device': ['max_pump_inlet_pressure', 'max_main_pipeline_outlet_pressure', 'max_n_running']
    },
    'pump_efficiency': {
        'global': [],
        'device': ['eta_min', 'eta_max']
    },
    'pump_speed': {
        'global': [],
        'device': ['min_freq', 'max_freq', 'min_speed', 'max_speed', 'f_ref', 'n_ref', 'pole_pairs', 'slip', 'speed_calibration_k', 'speed_calibration_b']
    },
    'pump_torque': {
        'global': ['rho', 'g'],
        'device': ['max_torque']
    },
    'pump_hydraulic_power': {
        'global': ['rho', 'g'],
        'device': ['min_power', 'max_power']
    },
    'pump_shaft_power': {
        'global': [],
        'device': ['max_power', 'max_shaft_power'],
        'device_rated': ['eta_motor', 'eta_vfd']
    },
    'main_pipeline_inlet_pressure': {
        'global': ['rho', 'g', 'P_atm'],
        'device': ['min_level', 'max_level', 'min_pressure', 'max_pressure', 'max_deviation', 'max_change_rate']
    }
}


def main():
    """主函数"""
    print("="*100)
    print("检查数据库中缺失的参数")
    print("="*100)
    
    # 初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 获取所有已配置的参数
            cur.execute("""
                SELECT station_id, device_id, metric_key, param_name, param_value
                FROM calculation_parameters
                WHERE station_id = 1
                ORDER BY metric_key, device_id, param_name
            """)
            
            existing_params = {}
            for row in cur.fetchall():
                station_id, device_id, metric_key, param_name, param_value = row
                
                key = (metric_key, device_id)
                if key not in existing_params:
                    existing_params[key] = {}
                existing_params[key][param_name] = param_value
            
            # 检查每个指标的缺失参数
            for metric_key, required in REQUIRED_PARAMS.items():
                print(f"\n{'='*100}")
                print(f"指标: {metric_key}")
                print(f"{'='*100}")
                
                # 检查全局参数（device_id=NULL）
                if required.get('global'):
                    print(f"\n全局参数 (device_id=NULL):")
                    print("-"*100)
                    
                    existing = existing_params.get((metric_key, None), {})
                    
                    for param_name in required['global']:
                        if param_name in existing:
                            print(f"  ✅ {param_name}: {existing[param_name]}")
                        else:
                            print(f"  ❌ {param_name}: 缺失")
                
                # 检查设备参数（device_id=1-6或7）
                if required.get('device'):
                    device_ids = [1, 2, 3, 4, 5, 6] if metric_key != 'main_pipeline_inlet_pressure' else [7]
                    
                    for device_id in device_ids:
                        print(f"\n设备 {device_id} 参数:")
                        print("-"*100)
                        
                        existing = existing_params.get((metric_key, device_id), {})
                        
                        for param_name in required['device']:
                            if param_name in existing:
                                print(f"  ✅ {param_name}: {existing[param_name]}")
                            else:
                                print(f"  ❌ {param_name}: 缺失")
                
                # 检查 device_rated_params（仅 pump_shaft_power）
                if required.get('device_rated'):
                    print(f"\n设备额定参数 (device_rated_params):")
                    print("-"*100)
                    
                    cur.execute("""
                        SELECT device_id, param_key, value_numeric
                        FROM device_rated_params
                        WHERE station_id = 1
                          AND device_id IN (1,2,3,4,5,6)
                          AND param_key IN ('eta_motor', 'eta_vfd')
                        ORDER BY device_id, param_key
                    """)
                    
                    device_rated = {}
                    for row in cur.fetchall():
                        dev_id, param_key, value = row
                        if dev_id not in device_rated:
                            device_rated[dev_id] = {}
                        device_rated[dev_id][param_key] = value
                    
                    for device_id in [1, 2, 3, 4, 5, 6]:
                        print(f"\n  设备 {device_id}:")
                        existing = device_rated.get(device_id, {})
                        
                        for param_name in required['device_rated']:
                            if param_name in existing:
                                print(f"    ✅ {param_name}: {existing[param_name]}")
                            else:
                                print(f"    ❌ {param_name}: 缺失")
    
    print("\n✅ 检查完成")


if __name__ == '__main__':
    main()

