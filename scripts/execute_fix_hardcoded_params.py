"""
执行SQL脚本：添加缺失的全局级参数
"""

from app.adapters.db import init_database, get_connection
from app.core.config.loader import load_settings

def main():
    # 初始化数据库
    from pathlib import Path
    config_dir = Path(__file__).parent.parent / 'configs'
    settings = load_settings(config_dir)
    init_database(settings)
    
    # 读取SQL脚本
    with open('scripts/fix_hardcoded_params_20251119.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    # 执行SQL
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 直接执行整个脚本
            print("执行SQL脚本...")
            try:
                cur.execute(sql_script)

                # 获取最后一个SELECT的结果
                try:
                    rows = cur.fetchall()
                    if rows:
                        print(f"\n查询结果（{len(rows)}行）:")
                        for row in rows:
                            print(f"  {row}")
                except Exception:
                    pass

                conn.commit()
                print("\n✅ SQL脚本执行成功！")
            except Exception as e:
                print(f"\n❌ SQL执行失败: {e}")
                conn.rollback()
                raise

if __name__ == '__main__':
    main()

