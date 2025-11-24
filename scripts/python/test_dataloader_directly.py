#!/usr/bin/env python3
"""
直接测试 DataLoader
"""
import sys
from pathlib import Path
from datetime import datetime
import pytz

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 强制重新加载模块
import importlib
if 'app.services.calculation.metrics.pump_inlet_pressure.data_loader' in sys.modules:
    importlib.reload(sys.modules['app.services.calculation.metrics.pump_inlet_pressure.data_loader'])

from app.adapters.db import init_database
from app.core.config.loader_new import load_settings
from app.services.calculation.metrics.pump_inlet_pressure.data_loader import DataLoader


def test_dataloader():
    """测试 DataLoader"""
    print("\n" + "=" * 100)
    print("🔍 测试 DataLoader")
    print("=" * 100)
    
    # 创建 DataLoader 实例
    loader = DataLoader(trace_id="test-trace-id")
    
    # 设置参数
    station_id = 1
    device_id = 1
    tz = pytz.timezone('Asia/Shanghai')
    start_time = datetime(2025, 10, 22, 16, 0, 0, tzinfo=tz)
    end_time = datetime(2025, 10, 22, 16, 10, 0, tzinfo=tz)  # 只测试10分钟
    
    print(f"\n参数:")
    print(f"  - station_id: {station_id}")
    print(f"  - device_id: {device_id}")
    print(f"  - start_time: {start_time}")
    print(f"  - end_time: {end_time}")
    
    # 加载数据
    print(f"\n加载数据...")
    df = loader.load_data(
        station_id=station_id,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time
    )
    
    print(f"\n加载结果:")
    print(f"  - 总行数: {len(df)}")
    
    if len(df) > 0:
        print(f"  - 列: {df.columns.tolist()}")
        print(f"  - pool_liquid_level 缺失: {df['pool_liquid_level'].isna().sum()}")
        print(f"  - pool_liquid_level 覆盖率: {(1 - df['pool_liquid_level'].isna().sum() / len(df)) * 100:.2f}%")
        print(f"\n前10行数据:")
        print(df.head(10))
        
        # 检查 pool_liquid_level 的值
        if df['pool_liquid_level'].isna().all():
            print(f"\n❌ 问题确认：所有 pool_liquid_level 都是 NaN！")
        else:
            print(f"\n✅ pool_liquid_level 数据正常")
            print(f"  - 最小值: {df['pool_liquid_level'].min():.6f}")
            print(f"  - 最大值: {df['pool_liquid_level'].max():.6f}")
            print(f"  - 平均值: {df['pool_liquid_level'].mean():.6f}")
    else:
        print(f"\n❌ 没有加载到数据！")


if __name__ == "__main__":
    try:
        # 初始化
        config_dir = project_root / "configs"
        settings = load_settings(config_dir)
        init_database(settings)
        
        # 测试 DataLoader
        test_dataloader()
        
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

