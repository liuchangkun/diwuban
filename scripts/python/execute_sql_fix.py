#!/usr/bin/env python3
"""
执行SQL修复脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings


def execute_sql_file(sql_file_path: str):
    """执行SQL文件"""
    sql_path = Path(sql_file_path)

    if not sql_path.exists():
        print(f"❌ SQL文件不存在: {sql_path}")
        return False

    print(f"📄 读取SQL文件: {sql_path}")
    sql_content = sql_path.read_text(encoding='utf-8')

    print(f"🔧 执行SQL脚本...")

    # 初始化数据库
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)

    try:
        with get_connection() as conn:
            # 执行SQL
            conn.execute(sql_content)
            conn.commit()
            print("✅ SQL脚本执行成功")

            # 验证结果
            cursor = conn.execute("""
                SELECT method_id, metric_key, method_name, priority, dependencies, accuracy_level
                FROM calculation_method_registry
                WHERE metric_key = 'pump_inlet_pressure'
                ORDER BY priority DESC
            """)

            rows = cursor.fetchall()
            print(f"\n📊 验证结果：找到 {len(rows)} 个方法")
            for row in rows:
                print(f"  - {row[0]}: {row[2]} (优先级={row[3]}, 依赖={row[4]})")

        return True

    except Exception as e:
        print(f"❌ SQL执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python execute_sql_fix.py <sql_file_path>")
        sys.exit(1)
    
    sql_file = sys.argv[1]
    success = execute_sql_file(sql_file)
    sys.exit(0 if success else 1)

