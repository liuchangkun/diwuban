"""
创建缺失指标计算功能的数据库表

用途: 执行scripts/sql/calculation/create_tables.sql文件，创建6个核心数据库表
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
    """执行SQL文件创建表"""
    # 初始化日志
    init_logging()

    # 加载配置
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)

    # 初始化数据库连接池
    init_database(settings)
    print("✅ 数据库连接池初始化成功")

    # 读取SQL文件
    sql_file = project_root / "scripts" / "sql" / "calculation" / "create_tables.sql"
    if not sql_file.exists():
        print(f"❌ SQL文件不存在: {sql_file}")
        return 1
    
    sql_content = sql_file.read_text(encoding="utf-8")
    print(f"📄 读取SQL文件: {sql_file}")
    print(f"📏 SQL文件大小: {len(sql_content)} 字符")
    
    # 执行SQL
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                print("🔄 开始执行SQL...")
                cur.execute(sql_content)
                conn.commit()
                print("✅ SQL执行成功！")
                
                # 验证表是否创建成功
                print("\n🔍 验证表是否创建成功...")
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN (
                        'metric_calculation_order',
                        'calculation_method_registry',
                        'calculation_parameters',
                        'calculation_validation_config',
                        'calculation_failures_log',
                        'optimization_history'
                    )
                    ORDER BY table_name
                """)
                tables = cur.fetchall()
                
                if len(tables) == 6:
                    print(f"✅ 成功创建 {len(tables)} 个表:")
                    for table in tables:
                        print(f"   - {table[0]}")
                    return 0
                else:
                    print(f"⚠️  只创建了 {len(tables)} 个表（预期6个）:")
                    for table in tables:
                        print(f"   - {table[0]}")
                    return 1
                    
    except Exception as e:
        print(f"❌ 执行SQL失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

