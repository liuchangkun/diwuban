"""
执行验证配置表迁移和初始化
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings
from app.core.logging.setup import init_logging


def run_sql_file(filepath: Path, description: str):
    """执行SQL文件"""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 执行SQL
                cur.execute(sql)
                
                # 获取所有结果
                if cur.description:
                    results = cur.fetchall()
                    if results:
                        # 打印结果
                        for row in results:
                            if len(row) == 1:
                                print(row[0])
                            else:
                                print(' | '.join(str(v) for v in row))
                
                conn.commit()
        
        print(f"\n✅ {description} 完成")
        return True
        
    except Exception as e:
        print(f"\n❌ {description} 失败")
        print(f"错误信息：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "="*80)
    print("验证配置表迁移和初始化")
    print("="*80)
    
    # 初始化
    init_logging()
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    
    # SQL文件路径
    migrate_sql = project_root / "scripts/sql/validation/migrate_validation_config.sql"
    init_sql = project_root / "scripts/sql/validation/init_validation_config.sql"
    
    # 执行迁移
    success1 = run_sql_file(migrate_sql, "步骤1：迁移表结构")
    if not success1:
        print("\n⚠️ 迁移失败，停止执行")
        return 1
    
    # 执行初始化
    success2 = run_sql_file(init_sql, "步骤2：初始化验证配置")
    if not success2:
        print("\n⚠️ 初始化失败")
        return 1
    
    # 验证结果
    print("\n" + "="*80)
    print("验证结果")
    print("="*80)
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 统计配置数量
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_configs,
                        COUNT(DISTINCT metric_key) as total_metrics,
                        COUNT(DISTINCT validator_type) as total_validator_types
                    FROM calculation_validation_config
                """)
                row = cur.fetchone()
                print(f"总配置数：{row[0]}")
                print(f"总指标数：{row[1]}")
                print(f"总验证器类型数：{row[2]}")
                
                # 显示每个指标的验证器
                cur.execute("""
                    SELECT 
                        metric_key,
                        COUNT(*) as validator_count,
                        STRING_AGG(validator_type, ', ' ORDER BY priority) as validators
                    FROM calculation_validation_config
                    WHERE station_id IS NULL AND device_id IS NULL
                    GROUP BY metric_key
                    ORDER BY metric_key
                """)
                
                print("\n指标验证配置：")
                print("-" * 80)
                for row in cur.fetchall():
                    metric_key, count, validators = row
                    print(f"{metric_key:40s} | {count} 个验证器 | {validators}")
        
        print("\n🎉 所有操作完成！")
        return 0
        
    except Exception as e:
        print(f"\n❌ 验证失败：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

