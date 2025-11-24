"""调试特定行"""

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
    
    # 查看 18:44:14-18:44:18 的数据
    target_time = datetime(2025, 10, 22, 18, 44, 14, tzinfo=TZ_UTC)
    target_rows = filtered_data[
        (filtered_data['ts_bucket'] >= target_time) &
        (filtered_data['ts_bucket'] <= datetime(2025, 10, 22, 18, 44, 18, tzinfo=TZ_UTC))
    ]
    
    print("\n=== 18:44:14-18:44:18 的数据 ===")
    print(target_rows)
    
    # 手动计算第一行
    if len(target_rows) > 0:
        row = target_rows.iloc[0]
        print(f"\n=== 手动计算第一行 (18:44:14) ===")
        print(f"pump_inlet_pressure: {row['pump_inlet_pressure']}")
        print(f"main_pipeline_outlet_pressure: {row['main_pipeline_outlet_pressure']}")
        print(f"pump_flow_rate: {row['pump_flow_rate']}")
        print(f"n_running: {row['n_running']}")
        
        K_pipe_loss = params['K_pipe_loss']
        alpha_multi_pump = params['alpha_multi_pump']
        N_total_pumps = params['N_total_pumps']
        rho = params['rho']
        g = params['g']
        
        delta_P_pipe = K_pipe_loss * (row['pump_flow_rate'] ** 2)
        correction_factor = 1 + alpha_multi_pump * row['n_running'] / N_total_pumps
        P_pump_out = row['main_pipeline_outlet_pressure'] * correction_factor + delta_P_pipe
        H = (P_pump_out - row['pump_inlet_pressure']) * 1e6 / (rho * g)
        
        print(f"\n计算过程:")
        print(f"  delta_P_pipe = {K_pipe_loss} × {row['pump_flow_rate']}² = {delta_P_pipe}")
        print(f"  correction_factor = 1 + {alpha_multi_pump} × {row['n_running']} / {N_total_pumps} = {correction_factor}")
        print(f"  P_pump_out = {row['main_pipeline_outlet_pressure']} × {correction_factor} + {delta_P_pipe} = {P_pump_out}")
        print(f"  H = ({P_pump_out} - {row['pump_inlet_pressure']}) × 1e6 / ({rho} × {g}) = {H}")
    
finally:
    close_pool()

