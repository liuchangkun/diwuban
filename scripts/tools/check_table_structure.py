#!/usr/bin/env python3
"""
检查数据库表结构
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def check_table_structure():
    """检查数据库表结构"""
    try:
        print("开始检查数据库表结构...")
        
        from app.core.config.loader_new import load_settings
        from app.adapters.db.gateway import get_conn
        
        settings = load_settings(Path("configs"))
        
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 检查operation_data表的列信息
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'operation_data' 
                    ORDER BY ordinal_position
                """)
                columns = cur.fetchall()
                print("operation_data表结构:")
                for column_name, data_type in columns:
                    print(f"  {column_name}: {data_type}")
                
                print()
                
                # 检查是否有类似的字段名
                flow_columns = [col for col in columns if 'flow' in col[0].lower()]
                pressure_columns = [col for col in columns if 'pressure' in col[0].lower()]
                power_columns = [col for col in columns if 'power' in col[0].lower()]
                frequency_columns = [col for col in columns if 'frequency' in col[0].lower()]
                
                print("可能的流量字段:", [col[0] for col in flow_columns])
                print("可能的压力字段:", [col[0] for col in pressure_columns])
                print("可能的功率字段:", [col[0] for col in power_columns])
                print("可能的频率字段:", [col[0] for col in frequency_columns])
        
        return True
        
    except Exception as e:
        print(f"检查表结构失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_table_structure()