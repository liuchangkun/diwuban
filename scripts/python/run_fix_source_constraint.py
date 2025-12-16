"""
修复pump_characteristic_curves表的source约束
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings
from app.core.logging.setup import init_logging


def main():
    """主函数"""
    print("="*80)
    print("修复pump_characteristic_curves表的source约束")
    print("="*80)
    
    # 初始化
    init_logging()
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    
    # 读取SQL文件
    sql_file = project_root / "scripts" / "sql" / "optimization" / "fix_source_constraint.sql"
    
    print(f"\n读取SQL文件: {sql_file}")
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 执行SQL
    print("\n执行SQL...")
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_content)
                conn.commit()
                
                print("\n✅ 约束修复成功！")
                
    except Exception as e:
        print(f"\n❌ 执行失败：{e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "="*80)
    print("完成")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    exit(main())

