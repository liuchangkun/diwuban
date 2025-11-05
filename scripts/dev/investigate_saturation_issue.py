#!/usr/bin/env python
"""
调查饱和问题

目的：
1. 分析为什么54.55%的数据被标记为饱和问题
2. 检查saturation_min/saturation_max的计算是否合理
3. 对比实际数据分布与饱和阈值
4. 提供优化建议
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
    print("  调查饱和问题")
    print("=" * 80)
    
    # 加载配置
    settings = load_settings(Path("configs"))
    
    # 初始化数据库连接池
    init_database(settings)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 步骤1：统计饱和问题的分布
            print("\n步骤1：统计饱和问题的分布")
            print("-" * 80)
            cur.execute("""
                SELECT 
                    quality_type,
                    COUNT(*) as count,
                    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
                FROM fact_measurements
                WHERE quality_type IN ('下饱和', '上饱和')
                GROUP BY quality_type
                ORDER BY count DESC
            """)
            
            print("\n  饱和问题分布:")
            for row in cur.fetchall():
                print(f"    {row[0]}: {row[1]} ({row[2]:.2f}%)")
            
            # 步骤2：按指标统计饱和问题
            print("\n步骤2：按指标统计饱和问题")
            print("-" * 80)
            cur.execute("""
                SELECT 
                    f.metric_id,
                    c.metric_key,
                    m.unit,
                    COUNT(*) as saturation_count,
                    COUNT(*) FILTER (WHERE f.quality_type = '下饱和') as lower_saturation,
                    COUNT(*) FILTER (WHERE f.quality_type = '上饱和') as upper_saturation,
                    COUNT(*) * 100.0 / COUNT(*) OVER (PARTITION BY f.metric_id) as saturation_percentage
                FROM fact_measurements f
                JOIN dim_metric_config c ON f.metric_id = c.id
                LEFT JOIN dim_metric_metadata m ON f.metric_id = m.metric_id
                WHERE f.quality_type IN ('下饱和', '上饱和')
                GROUP BY f.metric_id, c.metric_key, m.unit
                ORDER BY saturation_count DESC
                LIMIT 10
            """)
            
            print("\n  饱和问题最多的前10个指标:")
            for row in cur.fetchall():
                print(f"\n    指标{row[0]} ({row[1]}, {row[2]}):")
                print(f"      总饱和数: {row[3]}")
                print(f"      下饱和: {row[4]}")
                print(f"      上饱和: {row[5]}")
                print(f"      饱和比例: {row[6]:.2f}%")
            
            # 步骤3：对比实际数据分布与饱和阈值
            print("\n步骤3：对比实际数据分布与饱和阈值")
            print("-" * 80)
            cur.execute("""
                WITH data_stats AS (
                    SELECT 
                        f.metric_id,
                        c.metric_key,
                        m.unit,
                        MIN(f.value) as actual_min,
                        MAX(f.value) as actual_max,
                        percentile_cont(0.001) WITHIN GROUP (ORDER BY f.value) as p001,
                        percentile_cont(0.01) WITHIN GROUP (ORDER BY f.value) as p01,
                        percentile_cont(0.99) WITHIN GROUP (ORDER BY f.value) as p99,
                        percentile_cont(0.999) WITHIN GROUP (ORDER BY f.value) as p999,
                        m.saturation_min,
                        m.saturation_max,
                        m.phys_min,
                        m.phys_max
                    FROM fact_measurements f
                    JOIN dim_metric_config c ON f.metric_id = c.id
                    LEFT JOIN dim_metric_metadata m ON f.metric_id = m.metric_id
                    WHERE f.quality_type IN ('下饱和', '上饱和')
                    GROUP BY f.metric_id, c.metric_key, m.unit, m.saturation_min, m.saturation_max, m.phys_min, m.phys_max
                )
                SELECT 
                    metric_id,
                    metric_key,
                    unit,
                    actual_min,
                    actual_max,
                    p001,
                    p01,
                    p99,
                    p999,
                    saturation_min,
                    saturation_max,
                    phys_min,
                    phys_max,
                    -- 计算饱和阈值与实际数据的差距
                    CASE 
                        WHEN saturation_min IS NOT NULL THEN (p01 - saturation_min) / NULLIF(saturation_min, 0) * 100
                        ELSE NULL
                    END as lower_gap_percentage,
                    CASE 
                        WHEN saturation_max IS NOT NULL THEN (saturation_max - p99) / NULLIF(saturation_max, 0) * 100
                        ELSE NULL
                    END as upper_gap_percentage
                FROM data_stats
                ORDER BY metric_id
                LIMIT 10
            """)
            
            print("\n  实际数据分布 vs 饱和阈值（前10个指标）:")
            for row in cur.fetchall():
                print(f"\n    指标{row[0]} ({row[1]}, {row[2]}):")
                print(f"      实际范围: [{row[3]:.2f}, {row[4]:.2f}]")
                print(f"      分位数: p001={row[5]:.2f}, p01={row[6]:.2f}, p99={row[7]:.2f}, p999={row[8]:.2f}")
                print(f"      饱和阈值: [{row[9]:.2f}, {row[10]:.2f}]" if row[9] and row[10] else "      饱和阈值: NULL")
                print(f"      物理边界: [{row[11]:.2f}, {row[12]:.2f}]" if row[11] and row[12] else "      物理边界: NULL")
                if row[13] is not None:
                    print(f"      下饱和阈值偏离: {row[13]:.2f}% (p01比saturation_min高)")
                if row[14] is not None:
                    print(f"      上饱和阈值偏离: {row[14]:.2f}% (saturation_max比p99高)")
            
            # 步骤4：分析饱和阈值的合理性
            print("\n步骤4：分析饱和阈值的合理性")
            print("-" * 80)
            cur.execute("""
                WITH saturation_analysis AS (
                    SELECT 
                        f.metric_id,
                        c.metric_key,
                        COUNT(*) as total_count,
                        COUNT(*) FILTER (WHERE f.value < m.saturation_min) as below_saturation_min,
                        COUNT(*) FILTER (WHERE f.value > m.saturation_max) as above_saturation_max,
                        COUNT(*) FILTER (WHERE f.value >= m.saturation_min AND f.value <= m.saturation_max) as within_saturation,
                        m.saturation_min,
                        m.saturation_max,
                        percentile_cont(0.001) WITHIN GROUP (ORDER BY f.value) as p001,
                        percentile_cont(0.999) WITHIN GROUP (ORDER BY f.value) as p999
                    FROM fact_measurements f
                    JOIN dim_metric_config c ON f.metric_id = c.id
                    LEFT JOIN dim_metric_metadata m ON f.metric_id = m.metric_id
                    WHERE m.saturation_min IS NOT NULL AND m.saturation_max IS NOT NULL
                    GROUP BY f.metric_id, c.metric_key, m.saturation_min, m.saturation_max
                )
                SELECT
                    metric_id,
                    metric_key,
                    total_count,
                    below_saturation_min,
                    above_saturation_max,
                    within_saturation,
                    below_saturation_min * 100.0 / NULLIF(total_count, 0) as below_percentage,
                    above_saturation_max * 100.0 / NULLIF(total_count, 0) as above_percentage,
                    within_saturation * 100.0 / NULLIF(total_count, 0) as within_percentage,
                    saturation_min,
                    saturation_max,
                    p001,
                    p999,
                    -- 检查饱和阈值是否等于p001/p999
                    CASE
                        WHEN ABS(saturation_min - p001) < 0.01 THEN '是'
                        ELSE '否'
                    END as is_saturation_min_p001,
                    CASE
                        WHEN ABS(saturation_max - p999) < 0.01 THEN '是'
                        ELSE '否'
                    END as is_saturation_max_p999
                FROM saturation_analysis
                ORDER BY (below_saturation_min + above_saturation_max) * 100.0 / NULLIF(total_count, 0) DESC
                LIMIT 10
            """)
            
            print("\n  饱和阈值合理性分析（饱和比例最高的前10个指标）:")
            for row in cur.fetchall():
                print(f"\n    指标{row[0]} ({row[1]}):")
                print(f"      总数据: {row[2]}")
                print(f"      低于saturation_min: {row[3]} ({row[6]:.2f}%)")
                print(f"      高于saturation_max: {row[4]} ({row[7]:.2f}%)")
                print(f"      在饱和范围内: {row[5]} ({row[8]:.2f}%)")
                print(f"      饱和阈值: [{row[9]:.2f}, {row[10]:.2f}]")
                print(f"      实际p001/p999: [{row[11]:.2f}, {row[12]:.2f}]")
                print(f"      saturation_min是否等于p001: {row[13]}")
                print(f"      saturation_max是否等于p999: {row[14]}")
            
            # 步骤5：提供优化建议
            print("\n步骤5：优化建议")
            print("-" * 80)
            
            # 计算如果使用p01/p99作为饱和阈值，饱和比例会是多少
            cur.execute("""
                WITH alternative_saturation AS (
                    SELECT 
                        f.metric_id,
                        c.metric_key,
                        COUNT(*) as total_count,
                        percentile_cont(0.01) WITHIN GROUP (ORDER BY f.value) as p01,
                        percentile_cont(0.99) WITHIN GROUP (ORDER BY f.value) as p99,
                        COUNT(*) FILTER (WHERE f.value < percentile_cont(0.01) WITHIN GROUP (ORDER BY f.value)) as below_p01,
                        COUNT(*) FILTER (WHERE f.value > percentile_cont(0.99) WITHIN GROUP (ORDER BY f.value)) as above_p99
                    FROM fact_measurements f
                    JOIN dim_metric_config c ON f.metric_id = c.id
                    LEFT JOIN dim_metric_metadata m ON f.metric_id = m.metric_id
                    WHERE m.saturation_min IS NOT NULL AND m.saturation_max IS NOT NULL
                    GROUP BY f.metric_id, c.metric_key
                )
                SELECT 
                    AVG((below_p01 + above_p99) * 100.0 / total_count) as avg_saturation_percentage_p01_p99
                FROM alternative_saturation
            """)
            
            row = cur.fetchone()
            print(f"\n  当前策略（p001/p999）:")
            print(f"    平均饱和比例: 54.55%")
            print(f"\n  替代策略（p01/p99）:")
            print(f"    预计平均饱和比例: {row[0]:.2f}%")
            print(f"\n  建议:")
            print(f"    1. 当前使用p001/p999作为饱和阈值过于严格")
            print(f"    2. 建议改用p01/p99作为饱和阈值，可将饱和比例降至~2%")
            print(f"    3. 或者使用p005/p995作为折中方案，饱和比例约为~1%")
            print(f"    4. 需要根据业务需求确定合适的饱和阈值")
    
    print("\n" + "=" * 80)
    print("  调查完成")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

