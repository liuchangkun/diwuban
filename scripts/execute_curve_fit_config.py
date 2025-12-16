"""
执行curve_fit_config表创建和数据初始化脚本
"""
from app.core.config.loader_new import load_settings
from app.adapters.db import get_connection, init_database
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """执行SQL脚本"""
    print("=" * 80)
    print("执行curve_fit_config表创建脚本")
    print("=" * 80)

    # 初始化数据库连接
    settings = load_settings(Path("configs"))
    init_database(settings)
    print("✓ 数据库连接池初始化成功")

    # 读取SQL脚本
    sql_file = project_root / "scripts" / "sql" / \
        "characteristic_curves" / "001_create_curve_fit_config.sql"
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # 执行SQL
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 移除BEGIN和COMMIT（手动控制事务）
            sql_statements = sql_content.replace(
                'BEGIN;', '').replace('COMMIT;', '')

            try:
                cur.execute(sql_statements)
                conn.commit()
                print("✓ SQL脚本执行成功")

                # 验证数据
                cur.execute("""
                    SELECT config_key, description 
                    FROM curve_fit_config 
                    WHERE config_key = 'recommended_methods'
                """)
                row = cur.fetchone()
                if row:
                    print(f"\n✓ 验证成功：找到配置 '{row[0]}'")
                    print(f"  描述：{row[1]}")

                    # 查询配置值
                    cur.execute("""
                        SELECT config_value 
                        FROM curve_fit_config 
                        WHERE config_key = 'recommended_methods'
                    """)
                    config = cur.fetchone()[0]
                    print(f"\n配置内容：")
                    for curve_type in ['qh', 'qp', 'qeta']:
                        if curve_type in config:
                            print(
                                f"  {curve_type}: {list(config[curve_type].keys())}")
                else:
                    print("⚠ 警告：未找到推荐方法配置")

            except Exception as e:
                conn.rollback()
                print(f"✗ SQL执行失败：{e}")
                raise

    print("\n" + "=" * 80)
    print("执行完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
