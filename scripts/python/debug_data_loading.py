"""调试数据加载逻辑"""
import sys
from pathlib import Path
import numpy as np

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.logging.setup import init_logging
from app.core.config.loader_new import load_settings
from app.adapters.db import init_database
from app.services.calculation.orchestrator import CalculationOrchestrator

init_logging(project_root / 'configs')
settings = load_settings(project_root / 'configs')
init_database(settings)

# 创建编排器
orchestrator = CalculationOrchestrator()

# 加载设备129的数据
station_id = 17
device_id = 129
start_time = '2025-06-01 02:00:00+08'
end_time = '2025-06-01 03:59:59+08'
metric_keys = ['pump_inlet_pressure', 'pump_outlet_pressure', 'pump_head', 'pool_liquid_level']

print(f'加载设备{device_id}的数据...')
print(f'请求的指标: {metric_keys}')
print()

data, timestamps = orchestrator.load_data(
    station_id=station_id,
    device_id=device_id,
    start_time=start_time,
    end_time=end_time,
    metric_keys=metric_keys,
    filter_running=True,
    filter_quality=True
)

print('=' * 100)
print('加载结果：')
print('=' * 100)
print(f'时间戳数量: {len(timestamps)}')
print(f'数据字典键: {list(data.keys())}')
print()

for key in metric_keys:
    if key in data:
        arr = data[key]
        valid_count = np.sum(~np.isnan(arr))
        nan_count = np.sum(np.isnan(arr))
        print(f'{key}:')
        print(f'  - 总数: {len(arr)}')
        print(f'  - 有效: {valid_count}')
        print(f'  - NaN: {nan_count}')
        if valid_count > 0:
            print(f'  - 范围: [{np.nanmin(arr):.6f}, {np.nanmax(arr):.6f}]')
        print()
    else:
        print(f'{key}: ❌ 未加载')
        print()

