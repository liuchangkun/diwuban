"""
调试设备6在 2025-10-22 20:30:11 UTC 的 pump_inlet_pressure 计算问题
"""

import sys
from pathlib import Path
from datetime import datetime
import pytz

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, cleanup_database
from app.services.calculation.metrics.pump_inlet_pressure.data_loader import DataLoader
from app.services.calculation.metrics.pump_inlet_pressure.data_filter import DataFilter
from app.services.calculation.shared.shared_services import SharedServices


def debug_device6():
    """调试设备6的计算"""
    
    # 初始化配置和数据库连接
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    try:
        TZ_UTC = pytz.UTC
        
        # 测试设备6在 20:30:00 ~ 20:31:00 的数据
        device_id = 6
        start_time = datetime(2025, 10, 22, 20, 30, 0, tzinfo=TZ_UTC)
        end_time = datetime(2025, 10, 22, 20, 31, 0, tzinfo=TZ_UTC)
        
        print("=" * 100)
        print(f"调试设备6的 pump_inlet_pressure 计算")
        print("=" * 100)
        print(f"设备ID: {device_id}")
        print(f"时间范围: {start_time} ~ {end_time}")
        print("=" * 100)

        # 步骤1：加载数据
        print(f"\n步骤1：加载数据...")
        loader = DataLoader()
        raw_data = loader.load_data(
            station_id=1,
            device_id=device_id,
            start_time=start_time,
            end_time=end_time
        )
        print(f"加载的原始数据行数: {len(raw_data)}")
        if len(raw_data) > 0:
            print(f"数据列: {list(raw_data.columns)}")
            print(f"前5行数据:")
            print(raw_data.head())

        # 步骤2：过滤数据
        print(f"\n步骤2：过滤数据...")
        shared_services = SharedServices()
        params = shared_services.parameter_manager.get_parameters(
            metric_key='pump_inlet_pressure',
            method_id='pipe_loss',
            station_id=1,
            device_id=device_id
        )
        print(f"参数: {params}")

        data_filter = DataFilter(
            max_liquid_level=params.get('max_liquid_level', 10.0),
            max_flow_rate=params.get('max_flow_rate', 500.0),
            trace_id="debug_device6_20_30_11"
        )
        filtered_data = data_filter.filter_data(raw_data)
        print(f"过滤后的数据行数: {len(filtered_data)}")
        if len(filtered_data) > 0:
            print(f"前5行数据:")
            print(filtered_data.head())

        
    finally:
        # 清理资源
        cleanup_database()


if __name__ == "__main__":
    debug_device6()

