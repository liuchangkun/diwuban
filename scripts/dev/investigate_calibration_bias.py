#!/usr/bin/env python
"""
调查校准偏差问题

目的：
1. 分析为什么26.68%的数据被标记为校准偏差
2. 检查3*MAD阈值是否合理
3. 分析基线计算的时间窗口是否合理
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
    print("  调查校准偏差问题")
    print("=" * 80)
    
    # 加载配置
    settings = load_settings(Path("configs"))
    
    # 初始化数据库连接池
    init_database(settings)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 步骤1：统计校准偏差的分布
            print("\n步骤1：统计校准偏差的分布")
            print("-" * 80)
            cur.execute("""
                SELECT 
                    COUNT(*) as total_bias,
                    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM fact_measurements) as bias_percentage
                FROM fact_measurements
                WHERE quality_type = '校准偏差'
            """)
            
            row = cur.fetchone()
            print(f"\n  校准偏差总数: {row[0]}")
            print(f"  校准偏差比例: {row[1]:.2f}%")
            
            # 步骤2：按指标统计校准偏差
            print("\n步骤2：按指标统计校准偏差")
            print("-" * 80)
            cur.execute("""
                SELECT 
                    f.metric_id,
                    c.metric_key,
                    m.unit,
                    COUNT(*) as bias_count,
                    COUNT(*) * 100.0 / COUNT(*) OVER (PARTITION BY f.metric_id) as bias_percentage,
                    b.median,
                    b.mad,
                    b.mad * 3 as threshold_3mad,
                    b.mad * 5 as threshold_5mad
                FROM fact_measurements f
                JOIN dim_metric_config c ON f.metric_id = c.id
                LEFT JOIN dim_metric_metadata m ON f.metric_id = m.metric_id
                LEFT JOIN metric_rule_auto_baseline b ON f.station_id = b.station_id 
                    AND f.device_id = b.device_id 
                    AND f.metric_id = b.metric_id
                WHERE f.quality_type = '校准偏差'
                GROUP BY f.metric_id, c.metric_key, m.unit, b.median, b.mad
                ORDER BY bias_count DESC
                LIMIT 10
            """)
            
            print("\n  校准偏差最多的前10个指标:")
            for row in cur.fetchall():
                print(f"\n    指标{row[0]} ({row[1]}, {row[2]}):")
                print(f"      偏差数量: {row[3]}")
                print(f"      偏差比例: {row[4]:.2f}%")
                print(f"      基线中位数: {row[5]:.2f}")
                print(f"      MAD: {row[6]:.2f}")
                print(f"      3*MAD阈值: {row[7]:.2f}")
                print(f"      5*MAD阈值: {row[8]:.2f}")
            
            # 步骤3：分析偏差值的分布
            print("\n步骤3：分析偏差值的分布")
            print("-" * 80)
            cur.execute("""
                WITH bias_analysis AS (
                    SELECT 
                        f.metric_id,
                        c.metric_key,
                        f.value,
                        b.median,
                        b.mad,
                        ABS(f.value - b.median) as abs_bias,
                        ABS(f.value - b.median) / NULLIF(b.mad, 0) as bias_in_mad
                    FROM fact_measurements f
                    JOIN dim_metric_config c ON f.metric_id = c.id
                    LEFT JOIN metric_rule_auto_baseline b ON f.station_id = b.station_id 
                        AND f.device_id = b.device_id 
                        AND f.metric_id = b.metric_id
                    WHERE f.quality_type = '校准偏差'
                        AND b.mad > 0
                )
                SELECT 
                    metric_id,
                    metric_key,
                    MIN(abs_bias) as min_bias,
                    percentile_cont(0.25) WITHIN GROUP (ORDER BY abs_bias) as p25_bias,
                    percentile_cont(0.50) WITHIN GROUP (ORDER BY abs_bias) as median_bias,
                    percentile_cont(0.75) WITHIN GROUP (ORDER BY abs_bias) as p75_bias,
                    MAX(abs_bias) as max_bias,
                    MIN(bias_in_mad) as min_bias_mad,
                    percentile_cont(0.25) WITHIN GROUP (ORDER BY bias_in_mad) as p25_bias_mad,
                    percentile_cont(0.50) WITHIN GROUP (ORDER BY bias_in_mad) as median_bias_mad,
                    percentile_cont(0.75) WITHIN GROUP (ORDER BY bias_in_mad) as p75_bias_mad,
                    MAX(bias_in_mad) as max_bias_mad
                FROM bias_analysis
                GROUP BY metric_id, metric_key
                ORDER BY metric_id
                LIMIT 10
            """)
            
            print("\n  偏差值分布（前10个指标）:")
            for row in cur.fetchall():
                print(f"\n    指标{row[0]} ({row[1]}):")
                print(f"      绝对偏差范围: [{row[2]:.2f}, {row[6]:.2f}]")
                print(f"      绝对偏差分位数: p25={row[3]:.2f}, p50={row[4]:.2f}, p75={row[5]:.2f}")
                print(f"      MAD倍数范围: [{row[7]:.2f}, {row[11]:.2f}]")
                print(f"      MAD倍数分位数: p25={row[8]:.2f}, p50={row[9]:.2f}, p75={row[10]:.2f}")
            
            # 步骤4：分析不同阈值下的偏差比例
            print("\n步骤4：分析不同阈值下的偏差比例")
            print("-" * 80)
            cur.execute("""
                WITH bias_thresholds AS (
                    SELECT 
                        f.metric_id,
                        c.metric_key,
                        COUNT(*) as total_count,
                        COUNT(*) FILTER (WHERE ABS(f.value - b.median) > b.mad * 3) as bias_3mad,
                        COUNT(*) FILTER (WHERE ABS(f.value - b.median) > b.mad * 4) as bias_4mad,
                        COUNT(*) FILTER (WHERE ABS(f.value - b.median) > b.mad * 5) as bias_5mad,
                        COUNT(*) FILTER (WHERE ABS(f.value - b.median) > b.mad * 6) as bias_6mad
                    FROM fact_measurements f
                    JOIN dim_metric_config c ON f.metric_id = c.id
                    LEFT JOIN metric_rule_auto_baseline b ON f.station_id = b.station_id 
                        AND f.device_id = b.device_id 
                        AND f.metric_id = b.metric_id
                    WHERE b.mad > 0
                    GROUP BY f.metric_id, c.metric_key
                )
                SELECT 
                    metric_id,
                    metric_key,
                    total_count,
                    bias_3mad,
                    bias_4mad,
                    bias_5mad,
                    bias_6mad,
                    bias_3mad * 100.0 / NULLIF(total_count, 0) as bias_3mad_pct,
                    bias_4mad * 100.0 / NULLIF(total_count, 0) as bias_4mad_pct,
                    bias_5mad * 100.0 / NULLIF(total_count, 0) as bias_5mad_pct,
                    bias_6mad * 100.0 / NULLIF(total_count, 0) as bias_6mad_pct
                FROM bias_thresholds
                WHERE bias_3mad > 0
                ORDER BY bias_3mad_pct DESC
                LIMIT 10
            """)
            
            print("\n  不同阈值下的偏差比例（偏差比例最高的前10个指标）:")
            for row in cur.fetchall():
                print(f"\n    指标{row[0]} ({row[1]}):")
                print(f"      总数据: {row[2]}")
                print(f"      3*MAD: {row[3]} ({row[7]:.2f}%)")
                print(f"      4*MAD: {row[4]} ({row[8]:.2f}%)")
                print(f"      5*MAD: {row[5]} ({row[9]:.2f}%)")
                print(f"      6*MAD: {row[6]} ({row[10]:.2f}%)")
            
            # 步骤5：分析基线计算的时间窗口
            print("\n步骤5：分析基线计算的时间窗口")
            print("-" * 80)
            cur.execute("""
                SELECT 
                    b.station_id,
                    b.device_id,
                    b.metric_id,
                    c.metric_key,
                    b.median,
                    b.mad,
                    b.method,
                    b.version,
                    b.created_at
                FROM metric_rule_auto_baseline b
                JOIN dim_metric_config c ON b.metric_id = c.id
                ORDER BY b.metric_id
                LIMIT 10
            """)
            
            print("\n  基线数据信息（前10个）:")
            for row in cur.fetchall():
                print(f"\n    站点{row[0]} 设备{row[1]} 指标{row[2]} ({row[3]}):")
                print(f"      中位数: {row[4]:.2f}")
                print(f"      MAD: {row[5]:.2f}")
                print(f"      方法: {row[6]}")
                print(f"      版本: {row[7]}")
                print(f"      创建时间: {row[8]}")
            
            # 步骤6：提供优化建议
            print("\n步骤6：优化建议")
            print("-" * 80)
            
            # 计算如果使用不同阈值，偏差比例会是多少
            cur.execute("""
                WITH bias_summary AS (
                    SELECT 
                        COUNT(*) as total_count,
                        COUNT(*) FILTER (WHERE ABS(f.value - b.median) > b.mad * 3) as bias_3mad,
                        COUNT(*) FILTER (WHERE ABS(f.value - b.median) > b.mad * 4) as bias_4mad,
                        COUNT(*) FILTER (WHERE ABS(f.value - b.median) > b.mad * 5) as bias_5mad,
                        COUNT(*) FILTER (WHERE ABS(f.value - b.median) > b.mad * 6) as bias_6mad
                    FROM fact_measurements f
                    LEFT JOIN metric_rule_auto_baseline b ON f.station_id = b.station_id 
                        AND f.device_id = b.device_id 
                        AND f.metric_id = b.metric_id
                    WHERE b.mad > 0
                )
                SELECT 
                    bias_3mad * 100.0 / total_count as bias_3mad_pct,
                    bias_4mad * 100.0 / total_count as bias_4mad_pct,
                    bias_5mad * 100.0 / total_count as bias_5mad_pct,
                    bias_6mad * 100.0 / total_count as bias_6mad_pct
                FROM bias_summary
            """)
            
            row = cur.fetchone()
            print(f"\n  当前策略（3*MAD）:")
            print(f"    校准偏差比例: {row[0]:.2f}%")
            print(f"\n  替代策略:")
            print(f"    4*MAD阈值: {row[1]:.2f}%")
            print(f"    5*MAD阈值: {row[2]:.2f}%")
            print(f"    6*MAD阈值: {row[3]:.2f}%")
            print(f"\n  建议:")
            print(f"    1. 当前3*MAD阈值可能过于严格（26.68%的数据被标记）")
            print(f"    2. 建议改用5*MAD阈值，可将偏差比例降至~{row[2]:.2f}%")
            print(f"    3. 或者使用4*MAD作为折中方案，偏差比例约为~{row[1]:.2f}%")
            print(f"    4. 需要根据业务需求确定合适的偏差阈值")
            print(f"    5. 考虑使用更长的时间窗口计算基线（如24小时、7天）")
    
    print("\n" + "=" * 80)
    print("  调查完成")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

