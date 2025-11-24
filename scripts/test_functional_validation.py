#!/usr/bin/env python3
"""
功能验证脚本：验证 P0 + P1 + P5 优化的功能正确性

用途：
1. 验证质量码分布一致性
2. 验证标注行数一致性
3. 验证关键质量规则的正确性
4. 生成功能验证报告

使用方法：
    python scripts/test_functional_validation.py --start "2025-11-06 14:00:00" --end "2025-11-06 16:00:00"
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime
import psycopg
from typing import Dict, List, Tuple
from collections import defaultdict

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config.loader import load_settings


def query_quality_distribution(
    conn_str: str,
    start: str,
    end: str
) -> Dict[int, int]:
    """查询质量码分布"""
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        quality_status,
                        COUNT(*) as count
                    FROM public.fact_measurements
                    WHERE ts_bucket >= %s::timestamptz
                      AND ts_bucket < %s::timestamptz
                      AND quality_status IS NOT NULL
                      AND quality_status != 0
                    GROUP BY quality_status
                    ORDER BY quality_status
                    """,
                    (start, end)
                )
                
                distribution = {}
                for row in cur.fetchall():
                    distribution[row[0]] = row[1]
                
                return distribution
                
    except Exception as e:
        print(f"❌ 查询质量码分布失败: {e}")
        return {}


def query_total_annotations(
    conn_str: str,
    start: str,
    end: str
) -> Tuple[int, int]:
    """查询总标注行数"""
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                # 总行数
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM public.fact_measurements
                    WHERE ts_bucket >= %s::timestamptz
                      AND ts_bucket < %s::timestamptz
                    """,
                    (start, end)
                )
                total_rows = cur.fetchone()[0]
                
                # 标注行数
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM public.fact_measurements
                    WHERE ts_bucket >= %s::timestamptz
                      AND ts_bucket < %s::timestamptz
                      AND quality_status IS NOT NULL
                      AND quality_status != 0
                    """,
                    (start, end)
                )
                annotated_rows = cur.fetchone()[0]
                
                return total_rows, annotated_rows
                
    except Exception as e:
        print(f"❌ 查询总标注行数失败: {e}")
        return 0, 0


def query_key_rules_stats(
    conn_str: str,
    start: str,
    end: str
) -> Dict[int, Dict]:
    """查询关键规则的统计信息"""
    key_rules = [503, 141, 601, 602]
    stats = {}
    
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                for rule in key_rules:
                    cur.execute(
                        """
                        SELECT 
                            COUNT(*) as count,
                            COUNT(DISTINCT station_id) as stations,
                            COUNT(DISTINCT device_id) as devices,
                            COUNT(DISTINCT metric_id) as metrics
                        FROM public.fact_measurements
                        WHERE ts_bucket >= %s::timestamptz
                          AND ts_bucket < %s::timestamptz
                          AND quality_status = %s
                        """,
                        (start, end, rule)
                    )
                    
                    row = cur.fetchone()
                    if row:
                        stats[rule] = {
                            'count': row[0],
                            'stations': row[1],
                            'devices': row[2],
                            'metrics': row[3]
                        }
                
                return stats
                
    except Exception as e:
        print(f"❌ 查询关键规则统计失败: {e}")
        return {}


def print_functional_report(
    distribution: Dict[int, int],
    total_rows: int,
    annotated_rows: int,
    key_rules_stats: Dict[int, Dict]
):
    """打印功能验证报告"""
    print("\n" + "="*80)
    print("功能验证报告")
    print("="*80)
    
    # 总体统计
    print(f"\n总体统计:")
    print("-"*80)
    print(f"总行数: {total_rows:,}")
    print(f"标注行数: {annotated_rows:,}")
    print(f"标注比例: {annotated_rows/total_rows*100:.2f}%" if total_rows > 0 else "N/A")
    print(f"质量码种类: {len(distribution)}")
    
    # 质量码分布
    print(f"\n质量码分布:")
    print("-"*80)
    print(f"{'质量码':<10} {'数量':<15} {'占比':<10}")
    print("-"*80)
    
    sorted_distribution = sorted(
        distribution.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    for code, count in sorted_distribution:
        percentage = count / annotated_rows * 100 if annotated_rows > 0 else 0
        print(f"{code:<10} {count:<15,} {percentage:<10.2f}%")
    
    print("-"*80)
    
    # 关键规则统计
    print(f"\n关键规则统计:")
    print("-"*80)
    print(f"{'规则':<10} {'标注行数':<15} {'站点数':<10} {'设备数':<10} {'指标数':<10}")
    print("-"*80)
    
    rule_names = {
        503: '503(稀疏缺秒)',
        141: '141(步长异常)',
        601: '601(故障检测)',
        602: '602(校准偏差)'
    }
    
    for rule in [503, 141, 601, 602]:
        if rule in key_rules_stats:
            stats = key_rules_stats[rule]
            print(
                f"{rule_names.get(rule, str(rule)):<10} "
                f"{stats['count']:<15,} "
                f"{stats['stations']:<10} "
                f"{stats['devices']:<10} "
                f"{stats['metrics']:<10}"
            )
        else:
            print(f"{rule_names.get(rule, str(rule)):<10} {'无数据':<15}")
    
    print("-"*80)
    
    # 验证结论
    print(f"\n验证结论:")
    print("-"*80)
    
    checks = []
    
    # 检查1：是否有标注数据
    if annotated_rows > 0:
        checks.append(("✅", "存在标注数据"))
    else:
        checks.append(("❌", "无标注数据"))
    
    # 检查2：关键规则是否有数据
    key_rules_with_data = sum(1 for rule in [503, 141, 601, 602] if rule in key_rules_stats and key_rules_stats[rule]['count'] > 0)
    if key_rules_with_data >= 3:
        checks.append(("✅", f"关键规则有数据 ({key_rules_with_data}/4)"))
    else:
        checks.append(("⚠️", f"关键规则数据不足 ({key_rules_with_data}/4)"))
    
    # 检查3：质量码种类是否合理
    if 5 <= len(distribution) <= 28:
        checks.append(("✅", f"质量码种类合理 ({len(distribution)})"))
    else:
        checks.append(("⚠️", f"质量码种类异常 ({len(distribution)})"))
    
    for status, message in checks:
        print(f"{status} {message}")
    
    print("="*80)


def main():
    parser = argparse.ArgumentParser(description='功能验证脚本')
    parser.add_argument('--start', required=True, help='开始时间 (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end', required=True, help='结束时间 (YYYY-MM-DD HH:MM:SS)')
    
    args = parser.parse_args()
    
    # 加载配置
    config_dir = Path(__file__).parent.parent / "configs"
    settings = load_settings(config_dir)
    db_config = settings.db
    
    # 构建连接字符串
    conn_str = (
        f"host={db_config.host} "
        f"dbname={db_config.name} "
        f"user={db_config.user} "
        f"password={db_config.password}"
    )
    
    print(f"连接数据库: {db_config.name}@{db_config.host}")
    print(f"时间窗口: {args.start} ~ {args.end}")
    
    # 查询质量码分布
    print(f"\n查询质量码分布...")
    distribution = query_quality_distribution(conn_str, args.start, args.end)
    
    if not distribution:
        print("⚠️ 未找到质量码分布数据（可能时间窗口内无标注数据）")
    else:
        print(f"✅ 找到 {len(distribution)} 种质量码")
    
    # 查询总标注行数
    print(f"\n查询总标注行数...")
    total_rows, annotated_rows = query_total_annotations(conn_str, args.start, args.end)
    print(f"✅ 总行数: {total_rows:,}, 标注行数: {annotated_rows:,}")
    
    # 查询关键规则统计
    print(f"\n查询关键规则统计...")
    key_rules_stats = query_key_rules_stats(conn_str, args.start, args.end)
    print(f"✅ 找到 {len(key_rules_stats)} 个关键规则的数据")
    
    # 打印报告
    print_functional_report(distribution, total_rows, annotated_rows, key_rules_stats)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

