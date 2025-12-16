#!/usr/bin/env python3
"""
执行pump_inlet_pressure参数修复脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings


def execute_fix_params():
    """执行参数修复SQL脚本"""
    sql_file = project_root / "scripts" / "fix_pump_inlet_pressure_params.sql"
    
    if not sql_file.exists():
        print(f"❌ SQL文件不存在: {sql_file}")
        return False
    
    print(f"📄 读取SQL文件: {sql_file}")
    sql_content = sql_file.read_text(encoding='utf-8')
    
    # 移除注释中的回滚脚本部分
    sql_lines = []
    in_comment_block = False
    for line in sql_content.split('\n'):
        if line.strip().startswith('/*'):
            in_comment_block = True
        if not in_comment_block:
            sql_lines.append(line)
        if line.strip().endswith('*/'):
            in_comment_block = False
    
    sql_to_execute = '\n'.join(sql_lines)
    
    print(f"🔧 初始化数据库连接...")
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    
    print(f"🔧 执行SQL脚本...")
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 执行SQL
                cur.execute(sql_to_execute)
                conn.commit()
                
                print("✅ SQL脚本执行成功")
                
                # 验证K_eq更新
                print("\n📊 验证K_eq参数更新：")
                cur.execute("""
                    SELECT id, metric_key, param_name, param_value, station_id, device_id, updated_by
                    FROM calculation_parameters
                    WHERE metric_key = 'pump_inlet_pressure' 
                      AND param_name = 'K_eq' 
                      AND station_id IS NULL 
                      AND device_id IS NULL
                """)
                rows = cur.fetchall()
                for row in rows:
                    print(f"  ID={row[0]}, param={row[2]}, value={row[3]}, updated_by={row[6]}")
                
                # 验证L_offset更新
                print("\n📊 验证L_offset参数更新：")
                cur.execute("""
                    SELECT id, metric_key, param_name, param_value, device_id, updated_by
                    FROM calculation_parameters
                    WHERE metric_key = 'pump_inlet_pressure' 
                      AND param_name = 'L_offset' 
                      AND device_id IN (1, 2, 3, 4, 5, 6)
                    ORDER BY device_id
                """)
                rows = cur.fetchall()
                for row in rows:
                    print(f"  ID={row[0]}, device_id={row[4]}, param={row[2]}, value={row[3]}, updated_by={row[5]}")
        
        return True
        
    except Exception as e:
        print(f"❌ SQL脚本执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = execute_fix_params()
    sys.exit(0 if success else 1)

