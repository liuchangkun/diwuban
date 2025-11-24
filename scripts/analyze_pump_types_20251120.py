"""
分析泵类型（软启泵、变频泵、混合泵组）
"""
import sys
from pathlib import Path
import json

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader import load_settings

# 初始化数据库
settings = load_settings(project_root / 'config')
init_database(settings)

with get_connection() as conn:
    cur = conn.cursor()

    # 查询设备的额定参数和pump_type
    cur.execute('''
        SELECT
            d.id,
            d.name,
            d.pump_type,
            d.extra
        FROM dim_devices d
        WHERE d.station_id = 1 AND d.type = 'pump'
        ORDER BY d.id
    ''')

    print('设备信息:')
    for row in cur.fetchall():
        device_id, name, pump_type, extra = row
        print(f'\n设备{device_id}: {name}')
        print(f'  pump_type: {pump_type}')
        if extra:
            print(f'  extra: {json.dumps(extra, ensure_ascii=False, indent=4)}')

    # 查询设备参数
    cur.execute('''
        SELECT
            device_id,
            param_name,
            param_value
        FROM calculation_parameters
        WHERE device_id IS NOT NULL
        ORDER BY device_id, param_name
    ''')

    print('\n\n设备参数:')
    current_device = None
    for row in cur.fetchall():
        device_id, param_name, param_value = row
        if device_id != current_device:
            print(f'\n设备{device_id}:')
            current_device = device_id
        print(f'  {param_name}: {param_value}')

    # 查询频率分布，判断是否有软启泵
    cur.execute('''
        SELECT
            device_id,
            COUNT(*) as total_points,
            COUNT(DISTINCT ROUND(value::numeric, 0)) as distinct_frequencies,
            MIN(value) as min_freq,
            MAX(value) as max_freq,
            STDDEV(value) as std_freq,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value) as median_freq
        FROM fact_measurements
        WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_frequency')
          AND ts_bucket BETWEEN '2025-10-22 16:00:00' AND '2025-10-23 15:20:00'
          AND value > 0
        GROUP BY device_id
        ORDER BY device_id
    ''')

    print('\n\n频率分布分析（判断泵类型）:')
    print(f"{'设备':<6s} {'数据点':>10s} {'不同频率数':>12s} {'最小频率':>10s} {'最大频率':>10s} {'标准差':>10s} {'中位数':>10s} {'推断类型':20s}")
    print('-' * 110)
    for row in cur.fetchall():
        device_id, total, distinct_freq, min_f, max_f, std_f, median_f = row

        # 判断泵类型
        if std_f < 2:
            pump_type_inferred = '工频泵/软启泵'
        elif std_f < 10:
            pump_type_inferred = '软启+变频泵'
        else:
            pump_type_inferred = '全变频泵'

        print(f'{device_id:<6d} {total:>10,d} {distinct_freq:>12d} {min_f:>10.2f} {max_f:>10.2f} {std_f:>10.2f} {median_f:>10.2f} {pump_type_inferred:20s}')

    # 分析并联运行情况
    cur.execute('''
        WITH running_pumps AS (
            SELECT
                ts_bucket,
                device_id,
                CASE WHEN value > 0 THEN 1 ELSE 0 END as is_running
            FROM fact_measurements
            WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_frequency')
              AND ts_bucket BETWEEN '2025-10-22 16:00:00' AND '2025-10-23 15:20:00'
        ),
        parallel_count AS (
            SELECT
                ts_bucket,
                SUM(is_running) as num_running
            FROM running_pumps
            GROUP BY ts_bucket
        )
        SELECT
            num_running,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
        FROM parallel_count
        GROUP BY num_running
        ORDER BY num_running
    ''')

    print('\n\n并联运行分析:')
    print(f"{'并联台数':<10s} {'时间点数':>12s} {'占比(%)':>10s}")
    print('-' * 35)
    for row in cur.fetchall():
        num_running, count, percentage = row
        print(f'{num_running:<10d} {count:>12,d} {percentage:>10.2f}')

print('\n\n分析完成！')

