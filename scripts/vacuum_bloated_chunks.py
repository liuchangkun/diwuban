#!/usr/bin/env python3
"""
手动VACUUM膨胀的TimescaleDB chunks

解决表膨胀导致的性能问题
"""

import sys
from pathlib import Path
import time

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader import load_settings
from app.adapters.db.gateway import get_conn


def main():
    print("\n" + "="*80)
    print("手动VACUUM膨胀的TimescaleDB chunks")
    print("="*80)
    
    settings = load_settings(Path("configs"))

    # 直接使用psycopg连接，不使用连接池
    import psycopg

    db_config = settings.db
    # 使用dsn_write或构建连接字符串
    if db_config.dsn_write:
        conn_str = db_config.dsn_write
    else:
        password_part = f":{db_config.password}" if db_config.password else ""
        conn_str = f"postgresql://{db_config.user}{password_part}@{db_config.host}/{db_config.name}"

    with psycopg.connect(conn_str, autocommit=True) as conn:
        with conn.cursor() as cur:
            # 1. 查询需要VACUUM的chunks
            print("\n1. 查询膨胀的chunks")
            print("-"*80)
            cur.execute("""
                SELECT 
                    schemaname,
                    relname,
                    n_live_tup,
                    n_dead_tup,
                    CASE 
                        WHEN n_live_tup > 0 
                        THEN ROUND(n_dead_tup::numeric / n_live_tup, 2)
                        ELSE 0
                    END AS bloat_ratio
                FROM pg_stat_user_tables
                WHERE relname LIKE '_hyper_3_%'
                  AND n_dead_tup > 100000
                ORDER BY n_dead_tup DESC
            """)
            
            chunks = cur.fetchall()
            
            if not chunks:
                print("✅ 没有发现严重膨胀的chunks")
                return
            
            print(f"发现 {len(chunks)} 个膨胀的chunks:")
            print(f"{'Chunk名称':<30} {'活跃行数':>12} {'死亡行数':>12} {'膨胀比例':>10}")
            print("-"*70)
            for chunk in chunks:
                print(f"{chunk[1]:<30} {chunk[2]:>12,} {chunk[3]:>12,} {chunk[4]:>10.2f}x")
            
            # 2. 执行VACUUM
            print("\n2. 执行VACUUM")
            print("-"*80)
            
            for chunk in chunks:
                schema = chunk[0]
                table = chunk[1]
                full_name = f"{schema}.{table}"
                
                print(f"\n正在VACUUM {full_name}...")
                t0 = time.time()
                
                try:
                    # 使用VACUUM ANALYZE来同时更新统计信息
                    cur.execute(f"VACUUM ANALYZE {full_name}")
                    
                    duration = time.time() - t0
                    print(f"✅ 完成，耗时: {duration:.2f} 秒")
                    
                except Exception as e:
                    duration = time.time() - t0
                    print(f"❌ 失败，耗时: {duration:.2f} 秒")
                    print(f"错误: {e}")
            
            # 3. 验证结果
            print("\n3. 验证VACUUM结果")
            print("-"*80)
            
            cur.execute("""
                SELECT 
                    schemaname,
                    relname,
                    n_live_tup,
                    n_dead_tup,
                    CASE 
                        WHEN n_live_tup > 0 
                        THEN ROUND(n_dead_tup::numeric / n_live_tup, 2)
                        ELSE 0
                    END AS bloat_ratio
                FROM pg_stat_user_tables
                WHERE relname LIKE '_hyper_3_%'
                  AND n_live_tup > 0
                ORDER BY n_dead_tup DESC
                LIMIT 10
            """)
            
            results = cur.fetchall()
            print(f"{'Chunk名称':<30} {'活跃行数':>12} {'死亡行数':>12} {'膨胀比例':>10}")
            print("-"*70)
            for row in results:
                print(f"{row[1]:<30} {row[2]:>12,} {row[3]:>12,} {row[4]:>10.2f}x")
    
    print("\n" + "="*80)
    print("VACUUM完成")
    print("="*80)
    print("\n建议：")
    print("1. 如果膨胀比例仍然很高，可能需要运行 VACUUM FULL（需要锁表）")
    print("2. 考虑调整autovacuum参数，更激进地清理死亡行")
    print("3. 分析UPDATE逻辑，减少不必要的更新操作")
    print("="*80)


if __name__ == "__main__":
    main()

