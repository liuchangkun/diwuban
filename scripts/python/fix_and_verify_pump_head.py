"""
修复并验证 pump_head 计算

步骤：
1. 删除旧的 pump_head 和 pump_outlet_pressure 数据
2. 重新运行计算
3. 验证修复效果
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import pandas as pd
from pathlib import Path
from datetime import datetime
import pytz
from app.core.config.loader import load_settings
from app.adapters.db import init_database, get_connection
from app.services.calculation.shared.scheduler import Scheduler

# 初始化数据库
settings = load_settings(Path('configs'))
init_database(settings)

TZ_SH = pytz.timezone('Asia/Shanghai')

print("="*100)
print("🔧 修复并验证 pump_head 计算")
print("="*100)

# 时间范围
start_time = datetime(2025, 10, 22, 16, 0, 0, tzinfo=TZ_SH)
end_time = datetime(2025, 10, 22, 17, 0, 0, tzinfo=TZ_SH)
devices = [1, 2, 3, 4, 5, 6]

print(f"\n📊 处理范围:")
print(f"  时间: {start_time} ~ {end_time}")
print(f"  设备: {devices}")

# 步骤1：删除旧数据
print("\n" + "="*100)
print("1️⃣ 删除旧数据")
print("="*100)

with get_connection() as conn:
    with conn.cursor() as cur:
        # 删除 pump_head
        cur.execute("""
            DELETE FROM fact_measurements
            WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_head')
              AND device_id = ANY(%s)
              AND ts_raw >= %s
              AND ts_raw < %s
        """, (devices, start_time, end_time))
        deleted_head = cur.rowcount
        
        # 删除 pump_outlet_pressure
        cur.execute("""
            DELETE FROM fact_measurements
            WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_outlet_pressure')
              AND device_id = ANY(%s)
              AND ts_raw >= %s
              AND ts_raw < %s
        """, (devices, start_time, end_time))
        deleted_outlet = cur.rowcount
        
        conn.commit()
        
        print(f"  ✅ 删除 pump_head: {deleted_head} 条")
        print(f"  ✅ 删除 pump_outlet_pressure: {deleted_outlet} 条")

# 步骤2：重新计算
print("\n" + "="*100)
print("2️⃣ 重新计算")
print("="*100)

scheduler = Scheduler()

try:
    results = scheduler.schedule_single_metric(
        metric_key='pump_head',
        device_ids=devices,
        start_time=start_time,
        end_time=end_time
    )

    for device_id, result in results.items():
        status = "✅ 成功" if result.get('success') else f"❌ 失败: {result.get('error', 'Unknown')}"
        records = result.get('records_written', 0)
        print(f"  设备 {device_id}: {status} (写入 {records} 条)")

except Exception as e:
    print(f"  ❌ 计算失败: {e}")
    import traceback
    traceback.print_exc()

# 步骤3：验证修复效果
print("\n" + "="*100)
print("3️⃣ 验证修复效果")
print("="*100)

with get_connection() as conn:
    # 加载实测总管出口压力
    df_main = pd.read_sql("""
        SELECT 
            AVG(value) as avg_value,
            MIN(value) as min_value,
            MAX(value) as max_value
        FROM fact_measurements
        WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'main_pipeline_outlet_pressure')
          AND device_id = 7
          AND ts_raw >= %s
          AND ts_raw < %s
    """, conn, params=(start_time, end_time))
    
    main_avg = df_main['avg_value'].iloc[0]
    
    print(f"\n  实测总管出口压力:")
    print(f"    平均值: {main_avg:.4f} MPa")
    print(f"    范围: {df_main['min_value'].iloc[0]:.4f} ~ {df_main['max_value'].iloc[0]:.4f} MPa")
    
    # 加载计算的泵出口压力和扬程
    df_calc = pd.read_sql("""
        SELECT 
            fm.device_id,
            mc.metric_key,
            AVG(fm.value) as avg_value,
            MIN(fm.value) as min_value,
            MAX(fm.value) as max_value,
            COUNT(*) as record_count
        FROM fact_measurements fm
        JOIN dim_metric_config mc ON mc.id = fm.metric_id
        WHERE mc.metric_key IN ('pump_outlet_pressure', 'pump_head')
          AND fm.device_id = ANY(%s)
          AND fm.ts_raw >= %s
          AND fm.ts_raw < %s
        GROUP BY fm.device_id, mc.metric_key
        ORDER BY fm.device_id, mc.metric_key
    """, conn, params=(devices, start_time, end_time))
    
    print(f"\n  计算结果:")
    for device_id in devices:
        df_dev = df_calc[df_calc['device_id'] == device_id]
        if len(df_dev) == 0:
            print(f"\n    设备 {device_id}: ❌ 无数据")
            continue
        
        print(f"\n    设备 {device_id}:")
        for _, row in df_dev.iterrows():
            metric_key = row['metric_key']
            avg_value = row['avg_value']
            min_value = row['min_value']
            max_value = row['max_value']
            record_count = row['record_count']
            
            if metric_key == 'pump_outlet_pressure':
                error_pct = ((avg_value / main_avg) - 1) * 100
                print(f"      pump_outlet_pressure: {avg_value:.4f} MPa (范围: {min_value:.4f} ~ {max_value:.4f})")
                print(f"        误差: {error_pct:+.2f}% (记录数: {record_count})")
            elif metric_key == 'pump_head':
                print(f"      pump_head: {avg_value:.2f} m (范围: {min_value:.2f} ~ {max_value:.2f})")
                print(f"        记录数: {record_count}")

print("\n" + "="*100)
print("✅ 修复完成！")
print("="*100)

