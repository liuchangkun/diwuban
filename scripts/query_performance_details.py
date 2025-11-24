#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询最新的性能数据详情
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.adapters.db import get_conn
from app.core.config.loader import load_settings

# 加载配置
settings = load_settings(Path("configs"))


def main():
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 查询最新执行的性能数据
            cur.execute('''
                SELECT created_at, window_start, window_end
                FROM public.quality_profile_log
                ORDER BY created_at DESC
                LIMIT 1
            ''')
            latest = cur.fetchone()
            
            if not latest:
                print('⚠️ 未找到性能日志')
                return
            
            print(f'最新执行时间: {latest[0]}')
            print(f'窗口: {latest[1]} ~ {latest[2]}')
            print()
            
            # 查询该执行的所有阶段性能数据
            cur.execute('''
                SELECT 
                    stage,
                    duration_ms,
                    rows_affected,
                    CASE WHEN rows_affected > 0 
                         THEN duration_ms::numeric / rows_affected 
                         ELSE 0 
                    END AS ms_per_row
                FROM public.quality_profile_log
                WHERE created_at = %s
                ORDER BY duration_ms DESC
            ''', (latest[0],))
            
            print('性能数据（按耗时降序）:')
            print('=' * 80)
            print(f'{"阶段":<20} {"耗时(ms)":>12} {"影响行数":>12} {"ms/行":>12}')
            print('-' * 80)
            
            total_ms = 0
            stages = []
            for row in cur.fetchall():
                stage, duration_ms, rows_affected, ms_per_row = row
                total_ms += duration_ms
                stages.append((stage, duration_ms, rows_affected, ms_per_row))
                print(f'{stage:<20} {duration_ms:>12.2f} {rows_affected:>12} {ms_per_row:>12.4f}')
            
            print('-' * 80)
            print(f'{"总计":<20} {total_ms:>12.2f} ms ({total_ms/1000:.2f} 秒)')
            print('=' * 80)
            print()
            
            # 计算各阶段占比
            print('各阶段占比:')
            print('=' * 80)
            for stage, duration_ms, rows_affected, ms_per_row in stages[:15]:
                pct = (duration_ms / total_ms * 100) if total_ms > 0 else 0
                print(f'{stage:<20} {duration_ms:>10.2f} ms ({pct:>5.1f}%)')
            print('=' * 80)


if __name__ == '__main__':
    main()

