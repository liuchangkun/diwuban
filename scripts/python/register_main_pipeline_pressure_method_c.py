"""
注册main_pipeline压力指标的方法C（泵站级聚合方法）
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings
from app.core.logging.setup import init_logging

def register_methods():
    """注册方法C到数据库"""
    print("\n" + "="*80)
    print("注册main_pipeline压力指标的方法C（泵站级聚合方法）")
    print("="*80)
    
    # 读取SQL文件
    sql_file = project_root / "scripts" / "sql" / "calculation" / "add_main_pipeline_pressure_method_c.sql"
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 执行SQL
                cur.execute(sql_content)
                conn.commit()
                
                print("✅ SQL执行成功")
                
    except Exception as e:
        print(f"❌ 注册失败：{e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def main():
    """主函数"""
    # 初始化
    init_logging()
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    
    # 注册方法
    success = register_methods()
    
    if success:
        print("\n🎉 方法注册成功！")
        return 0
    else:
        print("\n⚠️ 方法注册失败")
        return 1


if __name__ == "__main__":
    exit(main())

