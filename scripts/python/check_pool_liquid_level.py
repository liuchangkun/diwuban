"""检查pool_liquid_level数据是否存在"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.logging.setup import init_logging
from app.core.config.loader_new import load_settings

def check_pool_liquid_level():
    """检查pool_liquid_level数据"""

    # 先获取pool_liquid_level的metric_id
    from app.services.calculation.metric_mapper import metric_mapper
    metric_mapper.load_from_db()
    pool_level_id = metric_mapper.key_to_id('pool_liquid_level')

    if pool_level_id is None:
        print('❌ 无法找到pool_liquid_level的metric_id！')
        return

    print(f'pool_liquid_level的metric_id: {pool_level_id}')
    print()

    # 查询pool_liquid_level数据
    query = """
    SELECT
        station_id,
        device_id,
        COUNT(*) as count,
        MIN(ts_bucket) as min_ts,
        MAX(ts_bucket) as max_ts
    FROM fact_measurements
    WHERE metric_id = %s
      AND station_id = 17
      AND ts_bucket >= '2025-06-01 02:00:00+08'::timestamptz
      AND ts_bucket < '2025-06-01 04:00:00+08'::timestamptz
    GROUP BY station_id, device_id
    ORDER BY device_id NULLS FIRST;
    """
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (pool_level_id,))
            results = cur.fetchall()
            
            print('=' * 100)
            print('pool_liquid_level数据分布：')
            print('=' * 100)
            print(f"{'station_id':<15} {'device_id':<15} {'count':<10} {'min_ts':<30} {'max_ts':<30}")
            print('-' * 100)
            for row in results:
                device_str = str(row[1]) if row[1] is not None else 'NULL'
                print(f"{row[0]:<15} {device_str:<15} {row[2]:<10} {str(row[3]):<30} {str(row[4]):<30}")
            
            if not results:
                print('❌ 没有找到pool_liquid_level数据！')
            else:
                print(f'\n✅ 找到 {len(results)} 条记录')
                
                # 检查device_id是否为NULL
                null_device_count = sum(1 for row in results if row[1] is None)
                if null_device_count > 0:
                    print(f'⚠️  其中 {null_device_count} 条记录的device_id为NULL（泵站级别数据）')

if __name__ == '__main__':
    # 初始化日志和数据库
    init_logging(project_root / 'configs')
    settings = load_settings(project_root / 'configs')
    init_database(settings)

    check_pool_liquid_level()

