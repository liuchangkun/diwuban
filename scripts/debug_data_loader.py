"""调试 data_loader"""

import sys
from pathlib import Path
from datetime import datetime
import pytz

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db.pool import initialize_pool, close_pool
from app.services.calculation.metrics.pump_head.data_loader import DataLoader

# 初始化数据库
settings = load_settings(Path("configs"))
initialize_pool(settings)

try:
    # 创建 DataLoader
    loader = DataLoader()
    
    # 测试参数
    TZ_UTC = pytz.UTC
    start_time = datetime(2025, 10, 22, 18, 43, 0, tzinfo=TZ_UTC)
    end_time = datetime(2025, 10, 22, 18, 50, 0, tzinfo=TZ_UTC)
    
    # 加载数据
    df = loader.load(
        station_id=1,
        device_id=5,
        start_time=start_time,
        end_time=end_time
    )
    
    print(f"\n返回的 DataFrame:")
    print(f"  - 行数: {len(df)}")
    print(f"  - 列名: {list(df.columns)}")
    if len(df) > 0:
        print(f"\n前5行:")
        print(df.head())
    
finally:
    close_pool()

