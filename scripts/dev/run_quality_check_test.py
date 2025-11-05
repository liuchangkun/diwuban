#!/usr/bin/env python
"""
重新运行质量检查测试

目的：
1. 先生成质量规则（从自动基线）
2. 重置fact_measurements的质量字段
3. 执行质量检查
4. 统计质量检查结果
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.core.config.loader import load_settings
from app.adapters.db import get_connection, init_database
from app.services.rules.metric_quality_rules import compute_metric_quality_rules
from app.services.quality.mark_window import mark_quality_window


def main():
    """主函数"""
    print("=" * 80)
    print("  重新运行质量检查测试")
    print("=" * 80)
    
    # 加载配置
    settings = load_settings(Path("configs"))
    
    # 初始化数据库连接池
    init_database(settings)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 步骤1：检查自动基线数据
            print("\n步骤1：检查自动基线数据")
            print("-" * 80)
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE flatline_eps > 0) as has_flatline_eps,
                    AVG(median) as avg_median,
                    AVG(mad) as avg_mad,
                    AVG(flatline_eps) as avg_flatline_eps
                FROM metric_rule_auto_baseline
            """)
            row = cur.fetchone()
            print(f"  总基线数据: {row[0]}")
            print(f"  有flatline_eps的数据: {row[1]}")
            print(f"  平均median: {row[2]:.2f}" if row[2] else "  平均median: NULL")
            print(f"  平均MAD: {row[3]:.2f}" if row[3] else "  平均MAD: NULL")
            print(f"  平均flatline_eps: {row[4]:.2f}" if row[4] else "  平均flatline_eps: NULL")
            
            # 步骤2：生成质量规则
            print("\n步骤2：生成质量规则（从自动基线）")
            print("-" * 80)

    # 调用Python函数生成质量规则（在事务外执行）
    result = compute_metric_quality_rules(settings, station_id=None, device_id=None)
    print(f"  ✓ 插入了 {result['inserted']} 条新规则")
    print(f"  ✓ 更新了 {result['updated']} 条现有规则")

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询生成的规则数量
            cur.execute("""
                SELECT COUNT(*) FROM metric_quality_rules
            """)
            rule_count = cur.fetchone()[0]
            print(f"  ✓ 总共有 {rule_count} 条质量规则")
            
            # 查看前5条规则
            cur.execute("""
                SELECT 
                    station_id,
                    device_id,
                    metric_id,
                    value_min,
                    value_max,
                    spike_abs,
                    flatline_eps,
                    LEFT(remark, 50) as remark_preview
                FROM metric_quality_rules
                ORDER BY station_id, device_id, metric_id
                LIMIT 5
            """)
            
            print("\n  前5条规则示例:")
            for row in cur.fetchall():
                print(f"    站点{row[0]} 设备{row[1]} 指标{row[2]}:")
                print(f"      value_min: {row[3]:.2f}" if row[3] else "      value_min: NULL")
                print(f"      value_max: {row[4]:.2f}" if row[4] else "      value_max: NULL")
                print(f"      spike_abs: {row[5]:.2f}" if row[5] else "      spike_abs: NULL")
                print(f"      flatline_eps: {row[6]:.2f}" if row[6] else "      flatline_eps: NULL")
                print(f"      remark: {row[7]}")
            
            # 步骤3：重置质量字段（模拟首次检查）
            print("\n步骤3：重置质量字段（模拟首次检查）")
            print("-" * 80)
            cur.execute("""
                UPDATE fact_measurements
                SET quality_status = 0,
                    quality_type = NULL,
                    quality_codes = NULL,
                    quality_meta = NULL
                WHERE quality_status != 0
            """)
            reset_count = cur.rowcount
            print(f"  ✓ 重置了 {reset_count} 行数据的质量字段")
            
    # 步骤4：执行质量检查（在事务外执行）
    print("\n步骤4：执行质量检查")
    print("-" * 80)

    # 调用Python函数执行质量检查
    mark_result = mark_quality_window(
        settings,
        start='2025-06-01T02:00:00+08:00',
        end='2025-06-01T04:00:00+08:00',
        station_id=None,
        device_id=None
    )

    print(f"  ✓ 质量检查完成")
    print(f"    - 耗时: {mark_result.get('elapsed_ms', 0):.2f} ms")

    with get_connection() as conn:
        with conn.cursor() as cur:
            
            # 步骤5：统计质量检查结果
            print("\n步骤5：统计质量检查结果")
            print("-" * 80)
            
            # 总体统计
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE quality_status = 0) as good,
                    COUNT(*) FILTER (WHERE quality_status = 1) as suspect,
                    COUNT(*) FILTER (WHERE quality_status = 2) as bad,
                    COUNT(*) FILTER (WHERE quality_status = 3) as completed,
                    COUNT(*) FILTER (WHERE quality_status = 4) as missing
                FROM fact_measurements
            """)
            row = cur.fetchone()
            print(f"\n  总体统计:")
            print(f"    总数据: {row[0]}")
            print(f"    正常(0): {row[1]} ({row[1]/row[0]*100:.2f}%)")
            print(f"    可疑(1): {row[2]} ({row[2]/row[0]*100:.2f}%)")
            print(f"    异常(2): {row[3]} ({row[3]/row[0]*100:.2f}%)")
            print(f"    已完成(3): {row[4]} ({row[4]/row[0]*100:.2f}%)")
            print(f"    缺失(4): {row[5]} ({row[5]/row[0]*100:.2f}%)")
            
            # 按质量类型统计
            cur.execute("""
                SELECT 
                    quality_type,
                    COUNT(*) as count,
                    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
                FROM fact_measurements
                WHERE quality_type IS NOT NULL
                GROUP BY quality_type
                ORDER BY count DESC
            """)
            
            print(f"\n  按质量类型统计:")
            for row in cur.fetchall():
                print(f"    {row[0]}: {row[1]} ({row[2]:.2f}%)")
            
            # 按质量码统计
            cur.execute("""
                SELECT 
                    unnest(quality_codes) as code,
                    COUNT(*) as count
                FROM fact_measurements
                WHERE quality_codes IS NOT NULL
                GROUP BY code
                ORDER BY count DESC
            """)
            
            print(f"\n  按质量码统计:")
            code_names = {
                101: "物理越界",
                111: "异常跳变",
                121: "平台期",
                401: "状态矛盾",
                701: "功率因数异常",
                702: "三相不平衡",
                711: "液位流量守恒异常",
                751: "计数器单调性异常"
            }
            for row in cur.fetchall():
                code_name = code_names.get(row[0], "未知")
                print(f"    {row[0]} ({code_name}): {row[1]}")
            
            # 查看异常数据示例
            print(f"\n  异常数据示例（前5条）:")
            cur.execute("""
                SELECT 
                    ts_bucket,
                    station_id,
                    device_id,
                    metric_id,
                    value,
                    quality_status,
                    quality_type,
                    quality_codes,
                    quality_meta
                FROM fact_measurements
                WHERE quality_status != 0
                ORDER BY quality_status DESC, ts_bucket
                LIMIT 5
            """)
            
            for row in cur.fetchall():
                print(f"\n    时间: {row[0]}")
                print(f"      站点{row[1]} 设备{row[2]} 指标{row[3]}")
                print(f"      值: {row[4]}")
                print(f"      状态: {row[5]}")
                print(f"      类型: {row[6]}")
                print(f"      质量码: {row[7]}")
                print(f"      元数据: {row[8]}")
            
            # 提交事务
            conn.commit()
    
    print("\n" + "=" * 80)
    print("  质量检查测试完成")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

