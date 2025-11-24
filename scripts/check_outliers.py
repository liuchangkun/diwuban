"""检查异常值"""

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
    
    # 加载数据
    loader = DataLoader()
    data = loader.load(
        station_id=1,
        device_id=5,
        start_time=start_time,
        end_time=end_time
    )
    
    # 过滤数据
    data_filter = DataFilter(params=params)
    filtered_data = data_filter.filter(data)
    
    # 计算
    pump_outlet_pressure_result, pump_head_result = calculate_pipe_loss_multi_pump(filtered_data, params)
    
    # 查找异常值
    print("\n=== pump_outlet_pressure 超过 2.0 MPa 的记录 ===")
    outliers_pressure = pump_outlet_pressure_result[pump_outlet_pressure_result['pump_outlet_pressure'] > 2.0]
    if len(outliers_pressure) > 0:
        print(f"共 {len(outliers_pressure)} 条记录")
        print(f"列名: {list(outliers_pressure.columns)}")
        print(outliers_pressure.head(10))
    else:
        print("没有超过 2.0 MPa 的记录")

    print("\n=== pump_head 超过 200 m 的记录 ===")
    outliers_head = pump_head_result[pump_head_result['pump_head'] > 200]
    if len(outliers_head) > 0:
        print(f"共 {len(outliers_head)} 条记录")
        print(f"列名: {list(outliers_head.columns)}")
        print(outliers_head.head(10))
    else:
        print("没有超过 200 m 的记录")
    
finally:
    close_pool()

