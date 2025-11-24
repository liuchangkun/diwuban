#!/usr/bin/env python3
"""
测试 pump_flow_rate 全流程计算

功能：
1. 使用重构后的 pump_flow_rate 计算流程
2. 测试完整的6阶段流水线
3. 验证数据库配置读取
4. 验证计算结果写入
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, get_connection
from app.core.logging.setup import init_logging

TZ_SH = timezone(timedelta(hours=8))


def test_full_pipeline():
    """测试完整的计算流程"""
    print("=" * 80)
    print("测试 pump_flow_rate 全流程计算")
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
            # 查询有 main_pipeline_flow_rate 数据的设备（最近30天）
            cur.execute("""
                SELECT
                    f.station_id,
                    f.device_id,
                    MIN(f.ts_bucket) as min_ts,
                    MAX(f.ts_bucket) as max_ts,
                    COUNT(*) as row_count
                FROM fact_measurements f
                JOIN dim_metric_config m ON f.metric_id = m.id
                WHERE m.metric_key = 'main_pipeline_flow_rate'
                    AND f.value IS NOT NULL
                    AND f.ts_bucket >= NOW() - INTERVAL '30 days'
                GROUP BY f.station_id, f.device_id
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
    
    print(f"\n📋 步骤3: 执行计算")
    print(f"  - 泵站ID: {station_id}")
    print(f"  - 设备ID: {device_id}")
    print(f"  - 开始时间: {start_time}")
    print(f"  - 结束时间: {end_time}")
    
    # 3. 使用 CalculationOrchestrator 执行计算
    from app.services.calculation.orchestrator import CalculationOrchestrator
    
    orchestrator = CalculationOrchestrator()
    
    try:
        result = orchestrator.calculate_missing_metrics(
            station_id=station_id,
            device_id=device_id,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            metrics=['pump_flow_rate'],
            write_to_db=True,  # 实际写入数据库
            filter_running=True,
            filter_quality=True
        )
        
        print(f"\n✅ 计算完成")
        print(f"  - 成功: {result.get('success', False)}")
        print(f"  - 计算指标数: {result.get('metrics_calculated', 0)}")
        print(f"  - 写入行数: {result.get('rows_written', 0)}")
        print(f"  - 耗时: {result.get('duration_seconds', 0):.2f}秒")
        
        if result.get('errors'):
            print(f"  - 错误: {result['errors']}")
        
        # 4. 验证写入的数据
        print(f"\n📋 步骤4: 验证写入的数据")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        f.ts_bucket,
                        f.value,
                        f.source_hint
                    FROM fact_measurements f
                    JOIN dim_metric_config m ON f.metric_id = m.id
                    WHERE f.station_id = %s
                        AND f.device_id = %s
                        AND m.metric_key = 'pump_flow_rate'
                        AND f.ts_bucket >= %s
                        AND f.ts_bucket < %s
                    ORDER BY f.ts_bucket
                    LIMIT 10
                """, (station_id, device_id, start_time, end_time))
                rows = cur.fetchall()
        
        if rows:
            print(f"✅ 找到 {len(rows)} 行计算结果（显示前10行）:")
            for ts, value, source_hint in rows:
                print(f"  - {ts}: {value:.2f} m³/h (来源={source_hint})")
        else:
            print("⚠️ 没有找到计算结果")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 计算失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_full_pipeline()
    sys.exit(0 if success else 1)

