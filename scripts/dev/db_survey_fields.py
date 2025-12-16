"""
数据库字段与数据样本调研脚本
用于收集核心表的字段定义、数据样本和分布情况。
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

def survey_columns(conn):
    print_section("1. 字段定义")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                table_name, 
                column_name, 
                data_type, 
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name IN ('fact_measurements', 'staging_raw', 'staging_rejects', 'dim_devices', 'dim_stations')
            ORDER BY table_name, ordinal_position
        """)
        rows = cur.fetchall()
        print_table(['Table', 'Column', 'Type', 'Nullable', 'Default'], rows)

def survey_samples(conn):
    print_section("2. 数据样本")
    tables = ['fact_measurements', 'staging_raw', 'staging_rejects']
    
    with conn.cursor() as cur:
        for table in tables:
            try:
                # 获取列名
                cur.execute(f"SELECT * FROM {table} LIMIT 0")
                col_names = [desc[0] for desc in cur.description]
                
                # 获取样本数据
                if table == 'fact_measurements':
                    # 对于 hypertable，尝试按时间倒序取最新的
                    try:
                        cur.execute(f"SELECT * FROM {table} ORDER BY ts_bucket DESC LIMIT 5")
                    except Exception:
                        cur.execute(f"SELECT * FROM {table} LIMIT 5")
                else:
                    cur.execute(f"SELECT * FROM {table} LIMIT 5")
                
                rows = cur.fetchall()
                print_table(col_names, rows, f"{table} 样本")
            except Exception as e:
                conn.rollback()
                print(f"\n获取 {table} 样本失败: {e}")

def survey_distributions(conn):
    print_section("3. 数据分布 (fact_measurements)")
    try:
        with conn.cursor() as cur:
            # 统计指标分布
            cur.execute("""
                SELECT metric_id, count(*) as est_count 
                FROM fact_measurements 
                GROUP BY metric_id 
                ORDER BY est_count DESC 
                LIMIT 10
            """)
            print_table(['Metric ID', 'Count'], cur.fetchall(), "Top 10 活跃指标")
            
            # 统计设备分布
            cur.execute("""
                SELECT device_id, count(*) as est_count 
                FROM fact_measurements 
                GROUP BY device_id 
                ORDER BY est_count DESC 
                LIMIT 10
            """)
            print_table(['Device ID', 'Count'], cur.fetchall(), "Top 10 活跃设备")
            
    except Exception as e:
        conn.rollback()
        print(f"统计分布失败: {e}")

def main():
    try:
        conn = get_conn()
        survey_columns(conn)
        survey_samples(conn)
        survey_distributions(conn)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
