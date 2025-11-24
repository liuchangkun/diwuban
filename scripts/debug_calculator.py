"""调试计算器输出"""

import sys
from pathlib import Path
from datetime import datetime
import pytz

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db.pool import initialize_pool, close_pool
from app.services.calculation.metrics.pump_head.data_loader import DataLoader
from app.services.calculation.metrics.pump_head.data_filter import DataFilter
from app.services.calculation.metrics.pump_head.methods.pipe_loss_multi_pump import calculate_pipe_loss_multi_pump
from app.services.calculation.shared.parameter_manager import ParameterManager

# 初始化数据库
settings = load_settings(Path("configs"))
initialize_pool(settings)

try:
    # 测试参数
    TZ_UTC = pytz.UTC
    start_time = datetime(2025, 10, 22, 18, 43, 0, tzinfo=TZ_UTC)
    end_time = datetime(2025, 10, 22, 18, 50, 0, tzinfo=TZ_UTC)
    
    # 加载参数
    param_manager = ParameterManager()
    params = param_manager.get_parameters(
        station_id=1,
        device_id=5,
        metric_key='pump_head',
        method_id='pipe_loss_multi_pump'
    )
    
    print(f"\n参数:")
    for key, value in params.items():
        print(f"  - {key}: {value}")
    
    # 加载数据
    loader = DataLoader()
    data = loader.load(
        station_id=1,
        device_id=5,
        start_time=start_time,
        end_time=end_time
    )
    
    print(f"\n加载的数据: {len(data)} 行")
    
    # 过滤数据
    data_filter = DataFilter(params=params)
    filtered_data = data_filter.filter(data)
    
    print(f"过滤后的数据: {len(filtered_data)} 行")
    
    if len(filtered_data) > 0:
        # 计算
        pump_outlet_pressure_result, pump_head_result = calculate_pipe_loss_multi_pump(filtered_data, params)
        
        print(f"\npump_outlet_pressure 结果: {len(pump_outlet_pressure_result)} 行")
        if len(pump_outlet_pressure_result) > 0:
            print(f"  - 最小值: {pump_outlet_pressure_result['pump_outlet_pressure'].min()}")
            print(f"  - 最大值: {pump_outlet_pressure_result['pump_outlet_pressure'].max()}")
            print(f"  - 平均值: {pump_outlet_pressure_result['pump_outlet_pressure'].mean()}")
            print(f"\n前5行:")
            print(pump_outlet_pressure_result[['ts_bucket', 'pump_outlet_pressure']].head())
        
        print(f"\npump_head 结果: {len(pump_head_result)} 行")
        if len(pump_head_result) > 0:
            print(f"  - 最小值: {pump_head_result['pump_head'].min()}")
            print(f"  - 最大值: {pump_head_result['pump_head'].max()}")
            print(f"  - 平均值: {pump_head_result['pump_head'].mean()}")
            print(f"\n前5行:")
            print(pump_head_result[['ts_bucket', 'pump_head']].head())
    
finally:
    close_pool()

