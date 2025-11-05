#!/usr/bin/env python
"""
测试从 fact_measurements 计算元数据

目的：验证物理边界和饱和阈值的自动计算功能
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
    print("  测试从 fact_measurements 计算元数据")
    print("=" * 80)
    
    # 加载配置
    settings = load_settings(Path("configs"))
    
    # 初始化数据库连接池
    init_database(settings)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 步骤1：检查当前元数据状态
            print("\n步骤1：检查当前元数据状态")
            print("-" * 80)
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE phys_min IS NOT NULL) as has_phys_min,
                    COUNT(*) FILTER (WHERE phys_max IS NOT NULL) as has_phys_max,
                    COUNT(*) FILTER (WHERE saturation_min IS NOT NULL) as has_saturation_min,
                    COUNT(*) FILTER (WHERE saturation_max IS NOT NULL) as has_saturation_max
                FROM dim_metric_metadata
            """)
            row = cur.fetchone()
            print(f"  总指标数: {row[0]}")
            print(f"  有 phys_min: {row[1]}")
            print(f"  有 phys_max: {row[2]}")
            print(f"  有 saturation_min: {row[3]}")
            print(f"  有 saturation_max: {row[4]}")
            
            # 步骤2：检查 fact_measurements 数据
            print("\n步骤2：检查 fact_measurements 数据")
            print("-" * 80)
            cur.execute("""
                SELECT 
                    COUNT(*) as total_rows,
                    COUNT(DISTINCT metric_id) as metric_count,
                    MIN(ts_bucket) as min_time,
                    MAX(ts_bucket) as max_time
                FROM fact_measurements
            """)
            row = cur.fetchone()
            print(f"  总数据行数: {row[0]}")
            print(f"  指标数: {row[1]}")
            print(f"  时间范围: {row[2]} ~ {row[3]}")
            
            # 步骤3：执行元数据计算
            print("\n步骤3：执行元数据计算")
            print("-" * 80)

            # 读取SQL脚本
            sql_file = project_root / "scripts" / "sql" / "migrations" / "022_update_metadata_from_facts.sql"
            sql_content = sql_file.read_text(encoding="utf-8")

            # 执行UPDATE语句
            cur.execute(sql_content)
            updated_count = cur.rowcount

            # 查询更新结果
            cur.execute("""
                SELECT
                    COUNT(*) AS updated_count,
                    COUNT(*) FILTER (WHERE phys_min IS NOT NULL) AS phys_min_count,
                    COUNT(*) FILTER (WHERE phys_max IS NOT NULL) AS phys_max_count,
                    COUNT(*) FILTER (WHERE saturation_min IS NOT NULL) AS saturation_min_count,
                    COUNT(*) FILTER (WHERE saturation_max IS NOT NULL) AS saturation_max_count
                FROM public.dim_metric_metadata
                WHERE updated_at >= now() - interval '1 minute'
            """)
            result = cur.fetchone()

            print(f"  ✓ 更新完成")
            print(f"    - 更新指标数: {updated_count}")
            print(f"    - phys_min 设置数: {result[1]}")
            print(f"    - phys_max 设置数: {result[2]}")
            print(f"    - saturation_min 设置数: {result[3]}")
            print(f"    - saturation_max 设置数: {result[4]}")
            
            # 步骤4：验证更新后的元数据
            print("\n步骤4：验证更新后的元数据")
            print("-" * 80)
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE phys_min IS NOT NULL) as has_phys_min,
                    COUNT(*) FILTER (WHERE phys_max IS NOT NULL) as has_phys_max,
                    COUNT(*) FILTER (WHERE saturation_min IS NOT NULL) as has_saturation_min,
                    COUNT(*) FILTER (WHERE saturation_max IS NOT NULL) as has_saturation_max
                FROM dim_metric_metadata
            """)
            row = cur.fetchone()
            print(f"  总指标数: {row[0]}")
            print(f"  有 phys_min: {row[1]}")
            print(f"  有 phys_max: {row[2]}")
            print(f"  有 saturation_min: {row[3]}")
            print(f"  有 saturation_max: {row[4]}")
            
            # 步骤5：查看前5个指标的详细数据
            print("\n步骤5：查看前5个指标的详细数据")
            print("-" * 80)
            cur.execute("""
                SELECT 
                    metric_id,
                    unit,
                    resolution,
                    phys_min,
                    phys_max,
                    saturation_min,
                    saturation_max,
                    LEFT(remark, 100) as remark_preview
                FROM dim_metric_metadata
                WHERE phys_min IS NOT NULL
                ORDER BY metric_id
                LIMIT 5
            """)
            
            for row in cur.fetchall():
                print(f"\n  指标 {row[0]} ({row[1]}):")
                print(f"    resolution: {row[2]}")
                print(f"    phys_min: {row[3]:.2f}" if row[3] is not None else "    phys_min: NULL")
                print(f"    phys_max: {row[4]:.2f}" if row[4] is not None else "    phys_max: NULL")
                print(f"    saturation_min: {row[5]:.2f}" if row[5] is not None else "    saturation_min: NULL")
                print(f"    saturation_max: {row[6]:.2f}" if row[6] is not None else "    saturation_max: NULL")
                print(f"    remark: {row[7]}")
            
            # 提交事务
            conn.commit()
    
    print("\n" + "=" * 80)
    print("  测试完成")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

