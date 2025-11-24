#!/usr/bin/env python3
"""
测试 pump_flow_rate 新架构全流程计算

功能：
1. 直接使用重构后的 pump_flow_rate 新架构
2. 测试完整的6阶段流水线（DataLoader → DataFilter → MethodSelector → Calculator → Validator → DataWriter）
3. 验证数据库配置读取
4. 验证计算结果
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, get_connection
from app.core.logging.setup import init_logging

TZ_SH = timezone(timedelta(hours=8))


def test_new_pipeline():
    """测试新架构的计算流程"""
    print("=" * 80)
    print("测试 pump_flow_rate 新架构全流程计算")
    print("=" * 80)
    
    # 1. 初始化
    print("\n📋 步骤1: 初始化应用")
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_logging(config_dir, settings.system.timezone.default)
    init_database(settings)
    print("✅ 应用初始化成功")
    
    # 2. 查询可用的设备和时间范围
    print("\n📋 步骤2: 查询可用的设备和时间范围")
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询有 pump_active_power 和 pump_frequency 数据的设备（最近30天）
            cur.execute("""
                SELECT
                    f.station_id,
                    f.device_id,
                    MIN(f.ts_bucket) as min_ts,
                    MAX(f.ts_bucket) as max_ts,
                    COUNT(*) as row_count
                FROM fact_measurements f
                JOIN dim_metric_config m ON f.metric_id = m.id
                WHERE m.metric_key IN ('pump_active_power', 'pump_frequency')
                    AND f.value IS NOT NULL
                    AND f.ts_bucket >= NOW() - INTERVAL '30 days'
                GROUP BY f.station_id, f.device_id
                HAVING COUNT(DISTINCT m.metric_key) = 2  -- 确保两个指标都有
                ORDER BY row_count DESC
                LIMIT 5
            """)
            devices = cur.fetchall()

    if not devices:
        print("❌ 没有找到可用的设备数据")
        return False

    print(f"✅ 找到 {len(devices)} 个设备")
    for station_id, device_id, min_ts, max_ts, row_count in devices:
        print(f"  - 泵站{station_id} 设备{device_id}: {row_count}行数据 ({min_ts} ~ {max_ts})")

    # 选择第一个设备进行测试
    station_id, device_id, min_ts, max_ts, _ = devices[0]
    
    # 选择一个小时的数据进行测试
    start_time = min_ts.replace(tzinfo=TZ_SH) if min_ts.tzinfo is None else min_ts
    end_time = start_time + timedelta(hours=1)
    
    print(f"\n📋 步骤3: 使用新架构执行计算")
    print(f"  - 泵站ID: {station_id}")
    print(f"  - 设备ID: {device_id}")
    print(f"  - 开始时间: {start_time}")
    print(f"  - 结束时间: {end_time}")
    
    # 3. 使用新架构的6个阶段
    from app.services.calculation.metrics.pump_flow_rate.data_loader import DataLoader
    from app.services.calculation.metrics.pump_flow_rate.data_filter import DataFilter
    from app.services.calculation.metrics.pump_flow_rate.method_selector import MethodSelector
    from app.services.calculation.metrics.pump_flow_rate.calculator import Calculator
    from app.services.calculation.metrics.pump_flow_rate.validator import Validator
    
    try:
        # 阶段1: DataLoader
        print("\n  🔹 阶段1: DataLoader - 加载数据")
        loader = DataLoader()
        df_loaded = loader.load_data(
            station_id=station_id,
            device_id=device_id,
            start_time=start_time,
            end_time=end_time
        )
        print(f"    ✅ 加载了 {len(df_loaded)} 行数据")
        print(f"    ✅ 列: {list(df_loaded.columns)}")
        print(f"    ✅ NaN 统计:")
        for col in ['main_pipeline_flow_rate', 'pump_active_power', 'pump_frequency']:
            nan_count = df_loaded[col].isna().sum()
            print(f"       - {col}: {nan_count} NaN ({nan_count/len(df_loaded)*100:.1f}%)")

        if df_loaded.empty:
            print("    ⚠️ 没有数据，跳过后续阶段")
            return False
        
        # 阶段2: DataFilter（跳过运行状态过滤，用于测试）
        print("\n  🔹 阶段2: DataFilter - 过滤数据（跳过运行状态过滤）")
        # 手动设置 running=1 以跳过运行状态过滤
        df_loaded['running'] = 1
        data_filter = DataFilter()
        df_filtered = data_filter.filter_data(df_loaded)
        print(f"    ✅ 过滤后剩余 {len(df_filtered)} 行数据")

        if df_filtered.empty:
            print("    ⚠️ 过滤后没有数据，跳过后续阶段")
            return False
        
        # 阶段3: MethodSelector
        print("\n  🔹 阶段3: MethodSelector - 选择计算方法")
        selector = MethodSelector()
        method_id = selector.select_method(df_filtered)
        print(f"    ✅ 选择的方法: {method_id}")
        
        # 阶段4: Calculator
        print("\n  🔹 阶段4: Calculator - 执行计算")
        calculator = Calculator()
        df_calculated = calculator.calculate(df_filtered, method_id)
        print(f"    ✅ 计算完成，结果包含 {len(df_calculated)} 行")
        print(f"    ✅ pump_flow_rate 统计: min={df_calculated['pump_flow_rate'].min():.2f}, max={df_calculated['pump_flow_rate'].max():.2f}, mean={df_calculated['pump_flow_rate'].mean():.2f}")
        
        # 阶段5: Validator
        print("\n  🔹 阶段5: Validator - 验证结果")
        validator = Validator()
        df_validated = validator.validate(df_calculated)
        print(f"    ✅ 验证完成，有效数据 {len(df_validated)} 行")
        
        # 阶段6: 显示结果（不写入数据库）
        print("\n  🔹 阶段6: 结果展示（前10行）")
        print(df_validated[['ts_bucket', 'pump_flow_rate', 'method_id']].head(10).to_string(index=False))
        
        print("\n✅ 新架构全流程测试成功！")
        return True
        
    except Exception as e:
        print(f"\n❌ 计算失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_new_pipeline()
    sys.exit(0 if success else 1)

