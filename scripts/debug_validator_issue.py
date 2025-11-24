"""
调试 Validator 问题 - 查看计算出的 pump_inlet_pressure 值
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 设置输出编码为 UTF-8
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime, timezone
import pandas as pd

# 设置 pandas 显示选项
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_rows', 100)

def main():
    # 初始化数据库连接池
    from app.adapters.db import init_database
    from app.core.config.loader_new import load_settings
    from pathlib import Path

    config_dir = Path(__file__).parent.parent / 'config'
    settings = load_settings(config_dir)
    init_database(settings)

    print("=" * 80)
    print("调试 Validator 问题 - 查看计算值")
    print("=" * 80)

    station_id = 1
    device_id = 6
    start_time = datetime(2025, 10, 22, 20, 30, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 10, 22, 20, 31, 0, tzinfo=timezone.utc)
    
    # 加载数据
    from app.services.calculation.metrics.pump_inlet_pressure.data_loader import DataLoader
    from app.services.calculation.metrics.pump_inlet_pressure.data_filter import DataFilter
    from app.services.calculation.metrics.pump_inlet_pressure.method_selector import MethodSelector
    from app.services.calculation.metrics.pump_inlet_pressure.calculator import Calculator
    from app.services.calculation.shared.shared_services import SharedServices
    
    shared_services = SharedServices()
    
    # 加载参数
    params = shared_services.parameter_manager.get_parameters(
        station_id=station_id,
        device_id=device_id,
        metric_key='pump_inlet_pressure',
        method_id='pump_inlet_pressure_method_b'
    )
    
    print(f"\n📋 加载的参数:")
    for key, value in params.items():
        print(f"  - {key}: {value}")
    
    # 加载数据
    loader = DataLoader()
    raw_data = loader.load_data(station_id, device_id, start_time, end_time)
    
    # 过滤数据
    filter = DataFilter()
    filtered_data = filter.filter_data(raw_data)
    
    print(f"\n✅ 过滤后数据: {len(filtered_data)} 行")
    
    # 选择方法
    selector = MethodSelector(device_params=params)
    method_id = selector.select_method(filtered_data)

    print(f"\n✅ 选择的方法: {method_id}")
    
    # 计算
    calculator = Calculator(param_manager=shared_services.parameter_manager)
    results = calculator.calculate(
        data=filtered_data,
        method_id=method_id,
        params=params
    )
    
    print(f"\n✅ 计算结果: {len(results)} 行")
    print(f"\n📊 pump_inlet_pressure 统计:")
    print(f"  - 最小值: {results['pump_inlet_pressure'].min():.6f} MPa")
    print(f"  - 最大值: {results['pump_inlet_pressure'].max():.6f} MPa")
    print(f"  - 平均值: {results['pump_inlet_pressure'].mean():.6f} MPa")
    print(f"  - 中位数: {results['pump_inlet_pressure'].median():.6f} MPa")
    
    print(f"\n📋 前10行计算结果:")
    print(results[['ts_bucket', 'pump_inlet_pressure']].head(10))
    
    # 检查 Validator 参数
    print(f"\n📋 Validator 参数:")
    print(f"  - min_pressure: {params.get('min_pressure', 0.0)} MPa")
    print(f"  - max_pressure: {params.get('max_pressure', 1.0)} MPa")
    
    # 检查有多少值超出范围
    below_min = (results['pump_inlet_pressure'] < params.get('min_pressure', 0.0)).sum()
    above_max = (results['pump_inlet_pressure'] > params.get('max_pressure', 1.0)).sum()
    below_physical = (results['pump_inlet_pressure'] < 0.05).sum()
    
    print(f"\n⚠️ 超出范围的值:")
    print(f"  - 低于 min_pressure ({params.get('min_pressure', 0.0)} MPa): {below_min} 个")
    print(f"  - 高于 max_pressure ({params.get('max_pressure', 1.0)} MPa): {above_max} 个")
    print(f"  - 低于物理下限 (0.05 MPa): {below_physical} 个")

if __name__ == '__main__':
    main()

