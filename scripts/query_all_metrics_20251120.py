#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查询所有可用指标（包括未导入数据的）"""

import sys
from pathlib import Path

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
    
    # 查询所有指标配置
    cur.execute('''
        SELECT
            id,
            metric_key,
            unit,
            unit_display,
            value_type,
            valid_min,
            valid_max
        FROM dim_metric_config
        ORDER BY id
    ''')

    print('所有可用指标（包括未导入数据的）:')
    print(f"{'ID':<4s} {'指标键':<40s} {'显示名称':<30s} {'单位':<10s} {'类型':<10s} {'最小值':<10s} {'最大值':<10s}")
    print('-' * 130)

    for row in cur.fetchall():
        id, key, unit, unit_display, value_type, valid_min, valid_max = row
        print(f'{id:<4d} {key:<40s} {(unit_display or ""):<30s} {(unit or ""):<10s} {(value_type or ""):<10s} {str(valid_min or ""):<10s} {str(valid_max or ""):<10s}')
    
    # 查询每个指标的数据量
    cur.execute('''
        SELECT
            mc.id,
            mc.metric_key,
            mc.unit_display,
            mc.unit,
            COUNT(fm.id) as data_count
        FROM dim_metric_config mc
        LEFT JOIN fact_measurements fm ON mc.id = fm.metric_id
        GROUP BY mc.id, mc.metric_key, mc.unit_display, mc.unit
        ORDER BY mc.id
    ''')

    print('\n\n指标数据量统计:')
    print(f"{'ID':<4s} {'指标键':<40s} {'显示名称':<30s} {'单位':<10s} {'数据量':>12s}")
    print('-' * 110)

    for row in cur.fetchall():
        id, key, unit_display, unit, count = row
        count_str = f'{count:,}' if count > 0 else '无数据'
        print(f'{id:<4d} {key:<40s} {unit_display or "":<30s} {unit or "":<10s} {count_str:>12s}')

print('\n\n查询完成！')

