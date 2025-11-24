"""
分析被过滤的数据

查询失败任务的数据统计，找出为什么被过滤
"""

from pathlib import Path
from datetime import datetime
import pytz

# 初始化应用
from app.core.config.loader_new import load_settings
from app.adapters.db import init_database
from app.core.logging.setup import init_logging
from app.adapters.db.pool import get_connection

# 初始化
config_dir = Path("configs")
settings = load_settings(config_dir)
init_logging(config_dir, settings.system.timezone.default)
init_database(settings)

TZ_SH = pytz.timezone('Asia/Shanghai')

print("=" * 80)
print("分析被过滤的数据")
print("=" * 80)

# 失败任务列表（从测试结果中提取）
failed_tasks = [
    (4, '2025-10-22 18:00:00', '2025-10-22 19:00:00'),  # 任务ID: 19cc9281-067c-43be-be9c-48bb0fc542e5
    (4, '2025-10-22 19:00:00', '2025-10-22 20:00:00'),  # 任务ID: e6c5d17c-42eb-4d1a-bac4-2c7bef5b213c
    (4, '2025-10-22 20:00:00', '2025-10-22 21:00:00'),  # 任务ID: 2dfe1f71-9f94-4d7d-8010-65506f6c9a01
    (4, '2025-10-22 21:00:00', '2025-10-22 22:00:00'),  # 任务ID: 7b8e0ffa-f633-4112-a1dd-0db9eeb1af05
    (4, '2025-10-22 22:00:00', '2025-10-22 23:00:00'),  # 任务ID: 1e3a7e1a-9d52-4845-84eb-e66916ba151f
    (4, '2025-10-22 23:00:00', '2025-10-23 00:00:00'),  # 任务ID: 6c16f5ca-da32-4442-832b-36100945e260
    (4, '2025-10-23 00:00:00', '2025-10-23 01:00:00'),  # 任务ID: 97316b34-0358-4a6e-9a6b-87b1d54b5737
    (4, '2025-10-23 01:00:00', '2025-10-23 02:00:00'),  # 任务ID: a79f1f2a-7602-422d-8786-6c4a6685c635
    (4, '2025-10-23 02:00:00', '2025-10-23 03:00:00'),  # 任务ID: 4e5af7c6-a106-4872-a75e-c25d7b4e1cdd
    (2, '2025-10-23 04:00:00', '2025-10-23 05:00:00'),  # 任务ID: facfbfe5-717c-40fc-880c-0a832eb94d12
    (4, '2025-10-23 03:00:00', '2025-10-23 04:00:00'),  # 任务ID: 0b9d9f90-3b6f-46d1-8870-87e78fa5a82d
    (1, '2025-10-23 05:00:00', '2025-10-23 06:00:00'),  # 任务ID: 8f9e2708-1ded-408d-b1c5-243148084b5a
    (6, '2025-10-23 05:00:00', '2025-10-23 06:00:00'),  # 任务ID: 0a526478-fb33-46e8-a166-c0fc94d359d0
    (1, '2025-10-23 06:00:00', '2025-10-23 07:00:00'),  # 任务ID: 51404ab3-1a72-4f80-9ed7-3ceca2541ce3
    (6, '2025-10-23 06:00:00', '2025-10-23 07:00:00'),  # 任务ID: fc846495-e3fd-4a60-8e77-7ff8aa6f62c1
    (6, '2025-10-23 09:00:00', '2025-10-23 10:00:00'),  # 任务ID: b7418293-4213-4c0f-9e20-6c6affd07547
    (6, '2025-10-23 12:00:00', '2025-10-23 13:00:00'),  # 任务ID: f25cd5fc-197a-4702-8a4a-0f0962aa4760
    (6, '2025-10-23 13:00:00', '2025-10-23 14:00:00'),  # 任务ID: d7acc989-aea9-4707-8596-1fb4c9204f86
]

# 过滤参数
max_power = 200.0
max_freq = 50.0

print(f"\n过滤参数:")
print(f"  max_power: {max_power} kW")
print(f"  max_freq: {max_freq} Hz")
print()

# 查询每个失败任务的数据统计
with get_connection() as conn:
    with conn.cursor() as cur:
        for device_id, start_time, end_time in failed_tasks:
            # 查询数据统计（从 fact_measurements 表）
            cur.execute('''
                WITH metric_ids AS (
                    SELECT id, metric_key
                    FROM dim_metric_config
                    WHERE metric_key IN ('pump_active_power', 'pump_frequency')
                ),
                power_data AS (
                    SELECT
                        fm.ts_bucket,
                        fm.value as power_value
                    FROM fact_measurements fm
                    JOIN metric_ids mc ON mc.id = fm.metric_id AND mc.metric_key = 'pump_active_power'
                    LEFT JOIN mv_device_running_1s dr
                        ON dr.station_id = fm.station_id
                       AND dr.device_id = fm.device_id
                       AND dr.ts_bucket = fm.ts_bucket
                    WHERE fm.station_id = 1
                      AND fm.device_id = %s
                      AND fm.ts_bucket >= %s
                      AND fm.ts_bucket < %s
                      AND dr.running = 1
                ),
                freq_data AS (
                    SELECT
                        fm.ts_bucket,
                        fm.value as freq_value
                    FROM fact_measurements fm
                    JOIN metric_ids mc ON mc.id = fm.metric_id AND mc.metric_key = 'pump_frequency'
                    LEFT JOIN mv_device_running_1s dr
                        ON dr.station_id = fm.station_id
                       AND dr.device_id = fm.device_id
                       AND dr.ts_bucket = fm.ts_bucket
                    WHERE fm.station_id = 1
                      AND fm.device_id = %s
                      AND fm.ts_bucket >= %s
                      AND fm.ts_bucket < %s
                      AND dr.running = 1
                )
                SELECT
                    (SELECT COUNT(*) FROM power_data) as total_count,
                    (SELECT MIN(power_value) FROM power_data) as min_power,
                    (SELECT MAX(power_value) FROM power_data) as max_power,
                    (SELECT AVG(power_value) FROM power_data) as avg_power,
                    (SELECT MIN(freq_value) FROM freq_data) as min_freq,
                    (SELECT MAX(freq_value) FROM freq_data) as max_freq,
                    (SELECT AVG(freq_value) FROM freq_data) as avg_freq,
                    (SELECT COUNT(*) FROM power_data WHERE power_value > %s) as power_outliers,
                    (SELECT COUNT(*) FROM freq_data WHERE freq_value > %s) as freq_outliers
            ''', (device_id, start_time, end_time, device_id, start_time, end_time, max_power, max_freq))
            
            result = cur.fetchone()
            if result and result[0] > 0:
                total_count = result[0]
                min_power = result[1]
                max_power_val = result[2]
                avg_power = result[3]
                min_freq = result[4]
                max_freq_val = result[5]
                avg_freq = result[6]
                power_outliers = result[7]
                freq_outliers = result[8]
                
                print(f"设备{device_id} [{start_time} ~ {end_time}]:")
                print(f"  总记录数: {total_count}")
                print(f"  功率范围: {min_power:.2f} ~ {max_power_val:.2f} kW (平均: {avg_power:.2f})")
                print(f"  频率范围: {min_freq:.2f} ~ {max_freq_val:.2f} Hz (平均: {avg_freq:.2f})")
                print(f"  功率异常值: {power_outliers} 条 ({power_outliers/total_count*100:.2f}%)")
                print(f"  频率异常值: {freq_outliers} 条 ({freq_outliers/total_count*100:.2f}%)")
                
                # 判断过滤原因
                if power_outliers == total_count:
                    print(f"  ❌ 过滤原因: 所有数据的功率都超过 {max_power} kW")
                elif freq_outliers == total_count:
                    print(f"  ❌ 过滤原因: 所有数据的频率都超过 {max_freq} Hz")
                elif power_outliers + freq_outliers == total_count:
                    print(f"  ❌ 过滤原因: 所有数据的功率或频率都超过阈值")
                else:
                    print(f"  ⚠️ 部分数据被过滤")
                print()
            else:
                print(f"设备{device_id} [{start_time} ~ {end_time}]: 无运行数据")
                print()

print("=" * 80)
print("分析完成")
print("=" * 80)

