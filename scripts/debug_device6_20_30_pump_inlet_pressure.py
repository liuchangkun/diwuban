"""
调试设备6在 20:30:00-20:31:00 时段的 pump_inlet_pressure 计算流程
查看数据在哪个阶段被过滤掉
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
    print("调试设备6在 20:30:00-20:31:00 的 pump_inlet_pressure 计算流程")
    print("=" * 80)

    station_id = 1
    device_id = 6
    start_time = datetime(2025, 10, 22, 20, 30, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 10, 22, 20, 31, 0, tzinfo=timezone.utc)
    
    print(f"\n📋 测试参数:")
    print(f"  - station_id: {station_id}")
    print(f"  - device_id: {device_id}")
    print(f"  - start_time: {start_time}")
    print(f"  - end_time: {end_time}")
    
    # Stage 1: DataLoader
    print(f"\n{'='*80}")
    print("Stage 1: DataLoader")
    print(f"{'='*80}")
    
    from app.services.calculation.metrics.pump_inlet_pressure.data_loader import DataLoader
    
    loader = DataLoader()
    raw_data = loader.load_data(station_id, device_id, start_time, end_time)
    
    print(f"\n✅ DataLoader 完成:")
    print(f"  - 加载行数: {len(raw_data)}")
    
    if len(raw_data) > 0:
        print(f"\n  - 列名: {list(raw_data.columns)}")
        print(f"\n  - 前10行数据:")
        print(raw_data.head(10))
        
        # 检查 pool_liquid_level 是否存在
        if 'pool_liquid_level' in raw_data.columns:
            print(f"\n  - pool_liquid_level 统计:")
            print(f"    - 非空值数量: {raw_data['pool_liquid_level'].notna().sum()}")
            print(f"    - 空值数量: {raw_data['pool_liquid_level'].isna().sum()}")
            print(f"    - 最小值: {raw_data['pool_liquid_level'].min()}")
            print(f"    - 最大值: {raw_data['pool_liquid_level'].max()}")
        else:
            print(f"\n  ⚠️ 缺少 pool_liquid_level 列！")
        
        # 检查 pump_flow_rate 是否存在
        if 'pump_flow_rate' in raw_data.columns:
            print(f"\n  - pump_flow_rate 统计:")
            print(f"    - 非空值数量: {raw_data['pump_flow_rate'].notna().sum()}")
            print(f"    - 空值数量: {raw_data['pump_flow_rate'].isna().sum()}")
            print(f"    - 最小值: {raw_data['pump_flow_rate'].min()}")
            print(f"    - 最大值: {raw_data['pump_flow_rate'].max()}")
            print(f"    - >0 的数量: {(raw_data['pump_flow_rate'] > 0).sum()}")
        else:
            print(f"\n  ⚠️ 缺少 pump_flow_rate 列！")
    else:
        print(f"\n  ❌ DataLoader 返回空数据！")
        return
    
    # Stage 2: DataFilter
    print(f"\n{'='*80}")
    print("Stage 2: DataFilter")
    print(f"{'='*80}")
    
    from app.services.calculation.metrics.pump_inlet_pressure.data_filter import DataFilter

    filter_obj = DataFilter()
    filtered_data = filter_obj.filter_data(raw_data)
    
    print(f"\n✅ DataFilter 完成:")
    print(f"  - 输入行数: {len(raw_data)}")
    print(f"  - 输出行数: {len(filtered_data)}")
    print(f"  - 过滤率: {(1 - len(filtered_data) / len(raw_data)) * 100:.2f}%")
    
    if len(filtered_data) > 0:
        print(f"\n  - 前10行数据:")
        print(filtered_data.head(10))
    else:
        print(f"\n  ❌ DataFilter 过滤后数据为空！")
        print(f"\n  🔍 分析原因:")
        
        # 检查各个过滤条件
        print(f"\n  1. 检查 running 状态:")
        if 'running' in raw_data.columns:
            print(f"     - running=1 的数量: {(raw_data['running'] == 1).sum()}")
            print(f"     - running=0 的数量: {(raw_data['running'] == 0).sum()}")
            print(f"     - running=NULL 的数量: {raw_data['running'].isna().sum()}")
        
        print(f"\n  2. 检查 pool_liquid_level:")
        if 'pool_liquid_level' in raw_data.columns:
            print(f"     - 非空值数量: {raw_data['pool_liquid_level'].notna().sum()}")
            print(f"     - >=0 的数量: {(raw_data['pool_liquid_level'] >= 0).sum()}")
        
        print(f"\n  3. 检查 pump_flow_rate:")
        if 'pump_flow_rate' in raw_data.columns:
            print(f"     - 非空值数量: {raw_data['pump_flow_rate'].notna().sum()}")
            print(f"     - >0 的数量: {(raw_data['pump_flow_rate'] > 0).sum()}")
        
        return
    
    # Stage 3: 完整 Pipeline 测试
    print(f"\n{'='*80}")
    print("Stage 3: 完整 Pipeline 测试")
    print(f"{'='*80}")

    from app.services.calculation.metrics.pump_inlet_pressure.pipeline import PumpInletPressurePipeline

    pipeline = PumpInletPressurePipeline()
    result = pipeline.execute(
        task_id='debug_test',
        station_id=station_id,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time
    )

    print(f"\n✅ Pipeline 完成:")
    print(f"  - 成功: {result.get('success', False)}")
    print(f"  - 计算点数: {result.get('points_calculated', 0)}")
    print(f"  - 写入点数: {result.get('points_written', 0)}")
    print(f"  - 使用方法: {result.get('method_used', None)}")
    print(f"  - 消息: {result.get('message', '')}")

    if result.get('success') and result.get('points_written', 0) > 0:
        print(f"\n🎉 成功！数据已计算并写入数据库。")
    else:
        print(f"\n⚠️ 未写入数据，请检查日志。")

if __name__ == '__main__':
    main()

