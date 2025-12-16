"""
检查 calculation_parameters 表的实际结构
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def check_schema():
    """检查表结构"""
    print("="*80)
    print("检查 calculation_parameters 表结构")
    print("="*80)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询表结构
            cur.execute("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = 'calculation_parameters'
                ORDER BY ordinal_position
            """)
            
            rows = cur.fetchall()
            print(f"\n找到 {len(rows)} 个列:")
            print(f"\n{'列名':<30} {'类型':<20} {'可空':<10} {'默认值':<30}")
            print(f"{'-'*100}")
            for row in rows:
                column_name, data_type, is_nullable, column_default = row
                default_str = str(column_default)[:28] if column_default else ''
                print(f"{column_name:<30} {data_type:<20} {is_nullable:<10} {default_str:<30}")

            # 查询唯一约束
            print(f"\n唯一约束:")
            cur.execute("""
                SELECT
                    conname AS constraint_name,
                    pg_get_constraintdef(c.oid) AS constraint_definition
                FROM pg_constraint c
                JOIN pg_namespace n ON n.oid = c.connamespace
                WHERE contype = 'u'
                  AND n.nspname = 'public'
                  AND conrelid::regclass::text = 'calculation_parameters'
            """)
            
            rows = cur.fetchall()
            for row in rows:
                print(f"  - {row[0]}: {row[1]}")

            # 查询示例数据
            print(f"\n示例数据（前5行）:")
            cur.execute("""
                SELECT *
                FROM calculation_parameters
                LIMIT 5
            """)
            
            rows = cur.fetchall()
            if rows:
                # 获取列名
                colnames = [desc[0] for desc in cur.description]
                print(f"\n列名: {colnames}")
                for i, row in enumerate(rows, 1):
                    print(f"\n行{i}:")
                    for col, val in zip(colnames, row):
                        print(f"  {col}: {val}")


if __name__ == '__main__':
    # 初始化数据库连接
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 检查表结构
    check_schema()

