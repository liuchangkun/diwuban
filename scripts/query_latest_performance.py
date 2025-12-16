#!/usr/bin/env python3
"""
查询最新一次执行的性能数据
"""
import sys
from pathlib import Path
import psycopg

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config.loader import load_settings


def main():
    # 加载配置
    config_dir = Path(__file__).parent.parent / "configs"
    settings = load_settings(config_dir)
    db_config = settings.db
    
    # 构建连接字符串
    conn_str = (
        f"host={db_config.host} "
        f"dbname={db_config.name} "
        f"user={db_config.user} "
        f"password={db_config.password}"
    )
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # 获取最新的执行时间
            cur.execute('''
                SELECT MAX(created_at) as latest_time
                FROM public.quality_profile_log
            ''')
            result = cur.fetchone()
            if result and result[0]:
                latest_time = result[0]
                print(f'最新执行时间: {latest_time}')
                print()

                # 查询该时间的性能数据
                cur.execute('''
                    SELECT
                        stage,
                        duration_ms,
                        rows_affected
                    FROM public.quality_profile_log
                    WHERE created_at = %s
                    ORDER BY duration_ms DESC
                ''', (latest_time,))
                
                rows = cur.fetchall()
                total_ms = sum(row[1] for row in rows)
                
                print('=' * 80)
                print('最新一次执行的性能分析')
                print('=' * 80)
                print(f'总执行时间: {total_ms/1000:.2f} 秒 ({total_ms} ms)')
                print()
                print(f"{'阶段':<30} {'耗时(ms)':<12} {'耗时(秒)':<12} {'占比':<10} {'影响行数':<10}")
                print('-' * 80)
                
                for row in rows:
                    stage, duration_ms, affected_rows = row
                    pct = (duration_ms / total_ms * 100) if total_ms > 0 else 0
                    print(f'{stage:<30} {duration_ms:<12} {duration_ms/1000:<12.2f} {pct:<9.1f}% {affected_rows or 0:<10}')
                
                print('=' * 80)
            else:
                print('⚠️ 未找到性能日志')


if __name__ == "__main__":
    main()

