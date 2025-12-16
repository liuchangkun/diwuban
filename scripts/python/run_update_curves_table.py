"""
执行更新pump_characteristic_curves表的SQL脚本
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
    print("更新pump_characteristic_curves表")
    print("="*80)
    
    # 初始化
    init_logging()
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    
    # 读取SQL文件
    sql_file = project_root / "scripts" / "sql" / "optimization" / "update_pump_characteristic_curves.sql"
    
    print(f"\n读取SQL文件: {sql_file}")
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 执行SQL
    print("\n执行SQL...")
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 执行更新语句（不获取结果）
                cur.execute(sql_content)
                conn.commit()
                
                print("\n✅ 表更新成功！")
                
                # 单独查询验证结果
                cur.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_name = 'pump_characteristic_curves'
                      AND column_name IN (
                          'curve_version', 
                          'quality_score', 
                          'sample_count',
                          'last_optimized_at',
                          'optimization_method'
                      )
                    ORDER BY column_name
                """)
                
                results = cur.fetchall()
                
                print("\n新增/更新的字段：")
                print("-"*80)
                print(f"{'字段名':<25} {'数据类型':<20} {'可空':<10} {'默认值':<20}")
                print("-"*80)
                
                for row in results:
                    column_name, data_type, is_nullable, column_default = row
                    nullable = "YES" if is_nullable == "YES" else "NO"
                    default = str(column_default)[:20] if column_default else "NULL"
                    print(f"{column_name:<25} {data_type:<20} {nullable:<10} {default:<20}")
                
                print("-"*80)
                print(f"\n总计：{len(results)} 个字段")
                
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

