"""
检查数据库改造状态
"""

from pathlib import Path
from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings

def check_database_status():
    """检查数据库改造状态"""
    # 初始化连接池
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    with get_connection() as conn:
        with conn.cursor() as cursor:
            print("=" * 80)
            print("数据库改造状态检查")
            print("=" * 80)
            
            # 1. 检查 calculation_logs 表
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'calculation_logs'
                )
            """)
            calculation_logs_exists = cursor.fetchone()[0]
            print(f"\n1. calculation_logs 表: {'✅ 存在' if calculation_logs_exists else '❌ 不存在'}")
            
            if calculation_logs_exists:
                # 检查分区数量
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM pg_inherits 
                    JOIN pg_class parent ON pg_inherits.inhparent = parent.oid 
                    WHERE parent.relname = 'calculation_logs'
                """)
                partition_count = cursor.fetchone()[0]
                print(f"   - 分区数量: {partition_count}")
                
                # 检查索引数量
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM pg_indexes 
                    WHERE tablename = 'calculation_logs'
                """)
                index_count = cursor.fetchone()[0]
                print(f"   - 索引数量: {index_count}")
            
            # 2. 检查 calculation_parameters 表
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'calculation_parameters'
                )
            """)
            calculation_parameters_exists = cursor.fetchone()[0]
            print(f"\n2. calculation_parameters 表: {'✅ 存在' if calculation_parameters_exists else '❌ 不存在'}")
            
            if calculation_parameters_exists:
                # 检查 pump_flow_rate 参数数量
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM calculation_parameters 
                    WHERE metric_key = 'pump_flow_rate'
                """)
                pump_flow_rate_params = cursor.fetchone()[0]
                print(f"   - pump_flow_rate 参数数量: {pump_flow_rate_params}")
                
                # 检查旧参数是否还存在
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM calculation_parameters 
                    WHERE metric_key = 'pump_flow_rate' 
                    AND param_name IN ('f_thr', 'p_thr')
                """)
                old_params_count = cursor.fetchone()[0]
                print(f"   - 旧参数 (f_thr, p_thr): {old_params_count} {'❌ 需要清理' if old_params_count > 0 else '✅ 已清理'}")
            
            # 3. 检查 calculation_methods 表
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'calculation_methods'
                )
            """)
            calculation_methods_exists = cursor.fetchone()[0]
            print(f"\n3. calculation_methods 表: {'✅ 存在' if calculation_methods_exists else '❌ 不存在'}")
            
            if calculation_methods_exists:
                # 检查 pump_flow_rate 方法数量
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM calculation_methods 
                    WHERE metric_key = 'pump_flow_rate'
                """)
                pump_flow_rate_methods = cursor.fetchone()[0]
                print(f"   - pump_flow_rate 方法数量: {pump_flow_rate_methods}")
                
                # 列出所有方法
                cursor.execute("""
                    SELECT method_id, method_name, priority, enabled 
                    FROM calculation_methods 
                    WHERE metric_key = 'pump_flow_rate'
                    ORDER BY priority DESC
                """)
                methods = cursor.fetchall()
                if methods:
                    print("   - 方法列表:")
                    for method_id, method_name, priority, enabled in methods:
                        status = "✅ 启用" if enabled else "❌ 禁用"
                        print(f"     * {method_id}: {method_name} (优先级: {priority}) {status}")
            
            # 4. 检查 fact_measurements 表的 source_hint 字段
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'fact_measurements' 
                AND column_name = 'source_hint'
            """)
            source_hint_column = cursor.fetchone()
            print(f"\n4. fact_measurements.source_hint 字段: {'✅ 存在' if source_hint_column else '❌ 不存在'}")
            if source_hint_column:
                print(f"   - 数据类型: {source_hint_column[1]}")
            
            print("\n" + "=" * 80)

if __name__ == '__main__':
    check_database_status()

