"""
检查 calculation_logs 表是否存在
"""

from pathlib import Path
from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings

def check_calculation_logs_table():
    """检查 calculation_logs 表是否存在"""
    # 初始化连接池
    settings = load_settings(Path("configs"))
    init_database(settings)
    """检查 calculation_logs 表是否存在"""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # 检查表是否存在
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'calculation_logs'
                )
            """)
            table_exists = cursor.fetchone()[0]
            
            print(f"calculation_logs 表存在: {table_exists}")
            
            if table_exists:
                # 检查分区数量
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM pg_inherits 
                    JOIN pg_class parent ON pg_inherits.inhparent = parent.oid 
                    WHERE parent.relname = 'calculation_logs'
                """)
                partition_count = cursor.fetchone()[0]
                print(f"分区数量: {partition_count}")
                
                # 检查索引数量
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM pg_indexes 
                    WHERE tablename = 'calculation_logs'
                """)
                index_count = cursor.fetchone()[0]
                print(f"索引数量: {index_count}")
            
            # 检查 f_thr 和 p_thr 参数是否存在
            cursor.execute("""
                SELECT COUNT(*) 
                FROM calculation_parameters 
                WHERE metric_key = 'pump_flow_rate' 
                AND param_name IN ('f_thr', 'p_thr')
            """)
            old_params_count = cursor.fetchone()[0]
            print(f"f_thr 和 p_thr 参数数量: {old_params_count}")
            
            # 检查新参数数量
            cursor.execute("""
                SELECT COUNT(*) 
                FROM calculation_parameters 
                WHERE metric_key = 'pump_flow_rate'
            """)
            total_params_count = cursor.fetchone()[0]
            print(f"pump_flow_rate 总参数数量: {total_params_count}")

if __name__ == '__main__':
    check_calculation_logs_table()

