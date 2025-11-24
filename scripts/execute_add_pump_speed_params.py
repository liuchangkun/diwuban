"""
执行 pump_speed 参数添加脚本
"""

import sys
import os
from pathlib import Path

# 设置控制台编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def main():
    """主函数"""
    print("="*100)
    print("添加 pump_speed 缺失参数")
    print("="*100)
    
    # 初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 读取SQL文件
    sql_file = Path(__file__).parent / "add_missing_pump_speed_params.sql"
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 分割SQL语句（按分号分割，忽略注释）
    statements = []
    current_statement = []
    
    for line in sql_content.split('\n'):
        # 跳过注释行
        if line.strip().startswith('--'):
            continue
        
        current_statement.append(line)
        
        # 如果行以分号结尾，表示一个完整的语句
        if line.strip().endswith(';'):
            statement = '\n'.join(current_statement).strip()
            if statement and not statement.startswith('--'):
                statements.append(statement)
            current_statement = []
    
    # 执行SQL语句
    with get_connection() as conn:
        with conn.cursor() as cur:
            for i, statement in enumerate(statements, 1):
                try:
                    print(f"\n执行语句 {i}/{len(statements)}...")
                    cur.execute(statement)
                    
                    # 如果是SELECT语句，显示结果
                    if statement.strip().upper().startswith('SELECT'):
                        results = cur.fetchall()
                        if results:
                            print(f"\n结果:")
                            for row in results:
                                print(f"  {row}")
                    else:
                        print(f"✅ 成功")
                        
                except Exception as e:
                    print(f"❌ 失败: {e}")
            
            # 提交事务
            conn.commit()
            print(f"\n{'='*100}")
            print("✅ 所有参数已成功添加")
            print(f"{'='*100}")


if __name__ == '__main__':
    main()

