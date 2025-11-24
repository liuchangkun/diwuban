#!/usr/bin/env python3
"""
测试数据透视逻辑
"""
import sys
from pathlib import Path
from datetime import datetime
import pytz
import pandas as pd

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings


def test_pivot_logic():
    """测试数据透视逻辑"""
    print("\n" + "=" * 100)
    print("🔍 测试数据透视逻辑")
    print("=" * 100)
    
    station_id = 1
    device_id = 1
    # 注意：数据库中的时间是 UTC+8，但查询时需要使用正确的时区
    start_time = '2025-10-22 16:00:00+08:00'
    end_time = '2025-10-22 16:10:00+08:00'  # 测试10分钟
    
    sql = """
        WITH metric_ids AS (
            SELECT id, metric_key
            FROM dim_metric_config
            WHERE metric_key IN (
                'pool_liquid_level',
                'pump_flow_rate'
            )
        )
        SELECT
            fm.ts_bucket,
            fm.device_id,
            mc.metric_key,
            fm.value,
            COALESCE(dr.running, 1) AS running
        FROM fact_measurements fm
        JOIN metric_ids mc ON mc.id = fm.metric_id
        LEFT JOIN mv_device_running_1s dr
            ON dr.station_id = fm.station_id
           AND dr.device_id = fm.device_id
           AND dr.ts_bucket = fm.ts_bucket
        WHERE fm.station_id = %(station_id)s
          AND fm.ts_bucket >= %(start_time)s
          AND fm.ts_bucket < %(end_time)s
          AND (
              (mc.metric_key = 'pump_flow_rate' AND fm.device_id = %(device_id)s)
              OR (mc.metric_key = 'pool_liquid_level')
          )
        ORDER BY fm.ts_bucket, fm.device_id, mc.metric_key
    """
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {
                'station_id': station_id,
                'device_id': device_id,
                'start_time': start_time,
                'end_time': end_time
            })
            
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            df_raw = pd.DataFrame(rows, columns=columns)
    
    print(f"\n原始数据（前20行）：")
    print(df_raw.head(20))
    
    print(f"\n原始数据统计：")
    print(f"  - 总行数: {len(df_raw)}")
    print(f"  - pool_liquid_level: {len(df_raw[df_raw['metric_key'] == 'pool_liquid_level'])}")
    print(f"  - pump_flow_rate: {len(df_raw[df_raw['metric_key'] == 'pump_flow_rate'])}")
    
    # 执行透视逻辑
    print(f"\n执行透视逻辑...")
    
    # 1. 提取 pool_liquid_level
    df_pool = df_raw[df_raw['metric_key'] == 'pool_liquid_level'][['ts_bucket', 'value', 'device_id']].copy()
    df_pool.rename(columns={'value': 'pool_liquid_level'}, inplace=True)
    df_pool = df_pool.drop_duplicates(subset=['ts_bucket'])
    
    print(f"\n提取 pool_liquid_level:")
    print(f"  - 行数: {len(df_pool)}")
    print(f"  - 设备ID: {df_pool['device_id'].unique().tolist()}")
    print(df_pool.head(10))
    
    pool_device_ids = df_pool['device_id'].unique().tolist() if not df_pool.empty else []
    df_pool = df_pool.drop(columns=['device_id'])
    
    # 2. 提取 pump_flow_rate
    df_pump = df_raw[
        (df_raw['metric_key'] == 'pump_flow_rate') &
        (df_raw['device_id'] == device_id)
    ][['ts_bucket', 'value', 'running']].copy()
    df_pump.rename(columns={'value': 'pump_flow_rate'}, inplace=True)
    df_pump = df_pump.drop_duplicates(subset=['ts_bucket'])
    
    print(f"\n提取 pump_flow_rate:")
    print(f"  - 行数: {len(df_pump)}")
    print(df_pump.head(10))
    
    # 3. 合并
    df_final = df_pump.merge(df_pool, on='ts_bucket', how='left')
    df_final['device_id'] = device_id
    
    print(f"\n合并后的数据:")
    print(f"  - 行数: {len(df_final)}")
    print(f"  - pool_liquid_level 缺失: {df_final['pool_liquid_level'].isna().sum()}")
    print(f"  - pool_liquid_level 覆盖率: {(1 - df_final['pool_liquid_level'].isna().sum() / len(df_final)) * 100:.2f}%")
    print(df_final.head(20))
    
    # 检查是否有 pool_liquid_level 数据
    if df_final['pool_liquid_level'].isna().all():
        print(f"\n❌ 问题确认：合并后所有 pool_liquid_level 都是 NaN！")
        print(f"\n调试信息：")
        print(f"  - df_pump 的 ts_bucket 类型: {df_pump['ts_bucket'].dtype}")
        print(f"  - df_pool 的 ts_bucket 类型: {df_pool['ts_bucket'].dtype}")
        print(f"  - df_pump 的前5个时间戳: {df_pump['ts_bucket'].head().tolist()}")
        print(f"  - df_pool 的前5个时间戳: {df_pool['ts_bucket'].head().tolist()}")
    else:
        print(f"\n✅ 合并成功！pool_liquid_level 数据正常")


if __name__ == "__main__":
    try:
        # 初始化
        config_dir = project_root / "configs"
        settings = load_settings(config_dir)
        init_database(settings)
        
        # 测试透视逻辑
        test_pivot_logic()
        
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

