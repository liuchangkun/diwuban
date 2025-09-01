#!/usr/bin/env python3
"""
检查数据库中实际存在的main_pipeline指标
"""

import psycopg
from pathlib import Path
import sys

sys.path.insert(0, str(Path('.').absolute()))
from app.core.config.loader_new import load_settings

def check_main_pipeline_metrics():
    """检查数据库中实际存在的main_pipeline指标"""
    try:
        settings = load_settings(Path('configs'))
        from app.adapters.db.gateway import make_dsn
        dsn = make_dsn(settings)
        print('🔍 检查数据库中实际存在的main_pipeline指标...')
        print(f'📍 连接数据库: {settings.db.host}/{settings.db.name}')

        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                # 检查数据库中实际存在的main_pipeline指标
                cur.execute("""
                    SELECT DISTINCT 
                        m.metric_key,
                        COALESCE(NULLIF(m.unit_display, ''), m.unit, 'N/A') as metric_unit,
                        COUNT(f.id) as data_count
                    FROM dim_metric_config m
                    LEFT JOIN fact_measurements f ON m.id = f.metric_id AND f.value IS NOT NULL
                    WHERE m.metric_key LIKE 'main_pipeline%'
                    GROUP BY m.metric_key, m.unit_display, m.unit
                    ORDER BY data_count DESC, m.metric_key
                """)
                
                pipeline_metrics = cur.fetchall()
                print('\n📋 数据库中实际存在的main_pipeline指标:')
                if pipeline_metrics:
                    for metric_key, unit, count in pipeline_metrics:
                        print(f'  - {metric_key:35} ({unit:15}) [{count:,}条数据]')
                else:
                    print('  ❌ 没有找到main_pipeline前缀的指标')
                
                print(f'\n📊 总计找到 {len(pipeline_metrics)} 个main_pipeline指标')
                
                # 也检查一下所有指标前缀
                print('\n🔍 检查所有指标前缀分布:')
                cur.execute("""
                    SELECT 
                        CASE 
                            WHEN metric_key LIKE 'pump%' THEN 'pump'
                            WHEN metric_key LIKE 'main_pipeline%' THEN 'main_pipeline'
                            WHEN metric_key LIKE 'station%' THEN 'station'
                            WHEN metric_key LIKE 'system%' THEN 'system'
                            ELSE SPLIT_PART(metric_key, '_', 1)
                        END as prefix,
                        COUNT(DISTINCT metric_key) as metric_count,
                        COUNT(f.id) as total_data
                    FROM dim_metric_config m
                    LEFT JOIN fact_measurements f ON m.id = f.metric_id AND f.value IS NOT NULL
                    GROUP BY 
                        CASE 
                            WHEN metric_key LIKE 'pump%' THEN 'pump'
                            WHEN metric_key LIKE 'main_pipeline%' THEN 'main_pipeline'
                            WHEN metric_key LIKE 'station%' THEN 'station'
                            WHEN metric_key LIKE 'system%' THEN 'system'
                            ELSE SPLIT_PART(metric_key, '_', 1)
                        END
                    ORDER BY total_data DESC, metric_count DESC
                """)
                
                prefix_stats = cur.fetchall()
                for prefix, metric_count, total_data in prefix_stats:
                    print(f'  {prefix:20}: {metric_count:3}个指标, {total_data:,}条数据')
                
                return pipeline_metrics
                
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    check_main_pipeline_metrics()