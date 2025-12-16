#!/usr/bin/env python
"""
修复单位"M"的指标的resolution缺失问题
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.core.config.loader import load_settings
from app.adapters.db import get_connection, init_database


def main():
    """主函数"""
    print("=" * 80)
    print("  修复单位'M'的指标的resolution缺失问题")
    print("=" * 80)
    
    # 加载配置
    settings = load_settings(Path("configs"))
    
    # 初始化数据库连接池
    init_database(settings)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 步骤1：检查当前状态
            print("\n步骤1：检查当前状态")
            print("-" * 80)
            cur.execute("""
                SELECT 
                    metric_id,
                    unit,
                    resolution
                FROM dim_metric_metadata
                WHERE UPPER(unit) = 'M'
                ORDER BY metric_id
            """)
            
            for row in cur.fetchall():
                print(f"  指标 {row[0]}: unit={row[1]}, resolution={row[2]}")
            
            # 步骤2：更新resolution
            print("\n步骤2：更新resolution")
            print("-" * 80)
            cur.execute("""
                UPDATE dim_metric_metadata
                SET resolution = 0.01,
                    remark = COALESCE(remark, '') || 
                             CASE 
                                 WHEN COALESCE(remark, '') = '' THEN ''
                                 ELSE ' | '
                             END ||
                             '修复: 添加resolution=0.01m'
                WHERE UPPER(unit) = 'M'
                  AND resolution IS NULL
            """)
            
            updated_count = cur.rowcount
            print(f"  ✓ 更新了 {updated_count} 个指标")
            
            # 步骤3：验证更新结果
            print("\n步骤3：验证更新结果")
            print("-" * 80)
            cur.execute("""
                SELECT 
                    metric_id,
                    unit,
                    resolution,
                    LEFT(remark, 100) as remark_preview
                FROM dim_metric_metadata
                WHERE UPPER(unit) = 'M'
                ORDER BY metric_id
            """)
            
            for row in cur.fetchall():
                print(f"\n  指标 {row[0]}:")
                print(f"    unit: {row[1]}")
                print(f"    resolution: {row[2]}")
                print(f"    remark: {row[3]}")
            
            # 提交事务
            conn.commit()
    
    print("\n" + "=" * 80)
    print("  修复完成")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

