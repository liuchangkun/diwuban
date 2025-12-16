"""
数据库全面调研脚本
用于收集数据库版本、配置、表结构、数据量、质量及性能指标。
不依赖任何非标准库（psycopg除外，这是项目依赖）。
"""
import os
import sys
import psycopg
from pathlib import Path
from datetime import datetime

def print_section(title):
    print(f"\n{'='*80}")
    print(f" {title}")
    print(f"{'='*80}")

def print_table(headers, data, title=""):
    if title:
        print(f"\n--- {title} ---")
    
    if not data:
        print("无数据")
        return

    # 简单列宽自适应
    cols = len(headers)
    col_widths = [len(str(h)) for h in headers]
    
    # 转换为字符串以便计算宽度
    str_data = []
    for row in data:
        str_row = [str(cell) if cell is not None else "NULL" for cell in row]
        str_data.append(str_row)
        for i, cell in enumerate(str_row):
            # 处理中文宽字符（简单估算，非精确）
            width = 0
            for char in cell:
                width += 2 if '\u4e00' <= char <= '\u9fff' else 1
            col_widths[i] = max(col_widths[i], width)
    
    # 增加padding
    col_widths = [w + 2 for w in col_widths]
    
    # 构建格式化字符串
    def format_row(row):
        return "".join(str(cell).ljust(w) for cell, w in zip(row, col_widths))

    header_str = "".join(str(h).ljust(w) for h, w in zip(headers, col_widths))
    separator = "-" * len(header_str)
    
    print(separator)
    print(header_str)
    print(separator)
    for row in str_data:
        print(format_row(row))
    print(separator)

def get_conn():
    # 尝试从配置文件加载
    dsn = "host=localhost dbname=pump_station_optimization user=postgres"
    try:
        sys.path.append(os.getcwd())
        try:
            from app.core.config.loader_new import load_settings
            settings = load_settings(Path("configs"))
            if settings.db.dsn_read:
                dsn = settings.db.dsn_read
            elif settings.db.dsn_write:
                dsn = settings.db.dsn_write
            else:
                dsn = f"host={settings.db.host} dbname={settings.db.name} user={settings.db.user}"
                if settings.db.password:
                    dsn += f" password={settings.db.password}"
        except ImportError:
            import yaml
            with open("configs/database.yaml", "r", encoding="utf-8") as f:
                db_conf = yaml.safe_load(f)
                if db_conf:
                    dsn = f"host={db_conf.get('host', 'localhost')} dbname={db_conf.get('dbname', 'pump_station_optimization')} user={db_conf.get('user', 'postgres')}"
                    if db_conf.get('password'):
                        dsn += f" password={db_conf.get('password')}"
    except Exception as e:
        print(f"Warning: Failed to load settings, using default/fallback DSN. Error: {e}")
    
    return psycopg.connect(dsn)

def survey_version_config(conn):
    print_section("1. 数据库版本与配置")
    try:
        with conn.cursor() as cur:
            # 版本
            cur.execute("SELECT version()")
            print(f"Version: {cur.fetchone()[0]}")
            
            # 关键配置
            params = [
                'max_connections', 'shared_buffers', 'work_mem', 'effective_cache_size', 
                'maintenance_work_mem', 'synchronous_commit', 'wal_level', 'max_wal_size', 
                'checkpoint_timeout', 'random_page_cost', 'effective_io_concurrency',
                'timescaledb.max_background_workers'
            ]
            cur.execute(f"SELECT name, setting, unit, short_desc FROM pg_settings WHERE name = ANY(%s) ORDER BY name", (params,))
            rows = cur.fetchall()
            print_table(['Parameter', 'Value', 'Unit', 'Description'], rows, "关键配置参数")
    except Exception as e:
        conn.rollback()
        print(f"Error in survey_version_config: {e}")

def survey_tables_indexes(conn):
    print_section("2. 表结构与索引概览")
    try:
        with conn.cursor() as cur:
            # 核心表列表
            tables = ['fact_measurements', 'staging_raw', 'staging_rejects', 'dim_devices', 'dim_stations', 'dim_metric_config']
            
            table_stats = []
            for table in tables:
                try:
                    cur.execute("""
                        SELECT 
                            pg_size_pretty(pg_total_relation_size(%s::regclass)) as total_size,
                            pg_size_pretty(pg_relation_size(%s::regclass)) as table_size,
                            pg_size_pretty(pg_total_relation_size(%s::regclass) - pg_relation_size(%s::regclass)) as index_size
                    """, (table, table, table, table))
                    size_info = cur.fetchone()
                    if size_info:
                        table_stats.append([table, size_info[0], size_info[1], size_info[2]])
                except Exception:
                    conn.rollback() # 回滚子查询错误
                    table_stats.append([table, "N/A", "N/A", "N/A"])
            
            print_table(['Table', 'Total Size', 'Data Size', 'Index Size'], table_stats, "表大小统计")

            for table in tables:
                 try:
                    cur.execute("""
                        SELECT indexname, indexdef 
                        FROM pg_indexes 
                        WHERE schemaname = 'public' AND tablename = %s
                    """, (table,))
                    indexes = cur.fetchall()
                    if indexes:
                        print(f"\n表 {table} 的索引:")
                        for idx in indexes:
                            print(f"  - {idx[0]}: {idx[1][:100]}...") 
                 except Exception:
                     conn.rollback()
    except Exception as e:
        conn.rollback()
        print(f"Error in survey_tables_indexes: {e}")

def survey_data_stats(conn):
    print_section("3. 数据量统计与分布")
    try:
        with conn.cursor() as cur:
            # Top 10 大表
            cur.execute("""
                SELECT 
                    relname as "Table", 
                    n_live_tup as "Est. Rows", 
                    pg_size_pretty(pg_total_relation_size(relid)) as "Total Size"
                FROM pg_stat_user_tables 
                ORDER BY pg_total_relation_size(relid) DESC 
                LIMIT 10
            """)
            print_table(["Table", "Est. Rows", "Total Size"], cur.fetchall(), "Top 10 表 (按大小)")
            
            # TimescaleDB 信息 (适配新旧视图)
            try:
                # 先检查视图列名
                cur.execute("SELECT * FROM timescaledb_information.hypertables LIMIT 0")
                col_names = [desc[0] for desc in cur.description]
                
                # 构建动态查询
                cols_to_select = ["hypertable_name", "num_chunks", "compression_enabled"]
                if "primary_dimension" in col_names:
                     cols_to_select.append("primary_dimension")
                
                query = f"SELECT {', '.join(cols_to_select)} FROM timescaledb_information.hypertables WHERE hypertable_schema='public'"
                cur.execute(query)
                ht_rows = cur.fetchall()
                
                if ht_rows:
                    print_table(cols_to_select, ht_rows, "TimescaleDB Hypertables")
                    
                    # Chunk 统计
                    cur.execute("""
                        SELECT 
                            hypertable_name, 
                            count(*) as total_chunks,
                            count(*) FILTER (WHERE is_compressed) as compressed_chunks
                        FROM timescaledb_information.chunks
                        GROUP BY hypertable_name
                    """)
                    print_table(["Hypertable", "Total Chunks", "Compressed"], cur.fetchall(), "Chunk 统计")

                else:
                    print("\n未检测到 Hypertables")
            except Exception as e:
                conn.rollback()
                print(f"\n检查 TimescaleDB 信息失败: {e}")

            # fact_measurements 时间范围
            try:
                cur.execute("SELECT reltuples FROM pg_class WHERE relname = 'fact_measurements'")
                row = cur.fetchone()
                est_rows = row[0] if row else 0
                
                if est_rows > 100000000: 
                     print("\nfact_measurements 数据量过大，跳过全表时间范围扫描")
                else:
                    cur.execute("SELECT MIN(ts_bucket), MAX(ts_bucket) FROM fact_measurements")
                    row = cur.fetchone()
                    if row and row[0]:
                        print(f"\nfact_measurements 时间范围: {row[0]} 到 {row[1]}")
                    else:
                        print("\nfact_measurements 无数据或无时间范围")
            except Exception as e:
                conn.rollback()
                print(f"查询 fact_measurements 失败: {e}")
    except Exception as e:
        conn.rollback()
        print(f"Error in survey_data_stats: {e}")

def survey_data_quality(conn):
    print_section("4. 数据质量概览")
    try:
        with conn.cursor() as cur:
            # staging_rejects 统计
            try:
                cur.execute("SELECT COUNT(*) FROM staging_rejects")
                reject_count = cur.fetchone()[0]
                print(f"staging_rejects 行数: {reject_count}")
                if reject_count > 0:
                    cur.execute("SELECT error_msg, COUNT(*) FROM staging_rejects GROUP BY error_msg ORDER BY 2 DESC LIMIT 5")
                    print_table(["Error Message", "Count"], cur.fetchall(), "Top 5 拒绝原因")
            except Exception:
                conn.rollback()
                print("staging_rejects 表不存在或查询失败")

            # 维度完整性
            try:
                cur.execute("SELECT COUNT(*) FROM dim_devices")
                dev_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM dim_devices WHERE is_active = true")
                active_dev = cur.fetchone()[0]
                print(f"\n设备总数: {dev_count}, 活跃设备: {active_dev}")
            except Exception:
                conn.rollback()
                pass
    except Exception as e:
        conn.rollback()
        print(f"Error in survey_data_quality: {e}")

def survey_performance(conn):
    print_section("5. 性能瓶颈分析")
    try:
        with conn.cursor() as cur:
            # 缓存命中率
            try:
                cur.execute("""
                    SELECT 
                        sum(heap_blks_hit) / nullif(sum(heap_blks_hit) + sum(heap_blks_read), 0) * 100 as cache_hit_ratio
                    FROM pg_statio_user_tables
                """)
                row = cur.fetchone()
                if row and row[0]:
                    print(f"整体缓存命中率: {row[0]:.2f}%")
            except Exception:
                conn.rollback()

            # 死元组分析
            try:
                cur.execute("""
                    SELECT 
                        relname, n_live_tup, n_dead_tup, 
                        round((n_dead_tup::numeric / nullif(n_live_tup, 0) * 100), 2) as dead_ratio
                    FROM pg_stat_user_tables 
                    WHERE n_live_tup > 1000
                    ORDER BY dead_ratio DESC 
                    LIMIT 5
                """)
                print_table(["Table", "Live", "Dead", "Ratio(%)"], cur.fetchall(), "死元组比例 Top 5 (Rows > 1000)")
            except Exception:
                conn.rollback()

            # 索引使用率低的大表
            try:
                cur.execute("""
                    SELECT 
                        relname, 
                        seq_scan, 
                        idx_scan, 
                        round((idx_scan::numeric / nullif(seq_scan + idx_scan, 0) * 100), 2) as idx_usage
                    FROM pg_stat_user_tables 
                    WHERE n_live_tup > 10000
                    ORDER BY idx_usage ASC 
                    LIMIT 5
                """)
                print_table(["Table", "Seq Scan", "Idx Scan", "Usage(%)"], cur.fetchall(), "索引使用率最低 Top 5 (Rows > 10000)")
            except Exception:
                conn.rollback()
    except Exception as e:
        conn.rollback()
        print(f"Error in survey_performance: {e}")

def main():
    try:
        conn = get_conn()
        print(f"Connected to {conn.info.dbname} as {conn.info.user}")
        
        survey_version_config(conn)
        survey_tables_indexes(conn)
        survey_data_stats(conn)
        survey_data_quality(conn)
        survey_performance(conn)
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
