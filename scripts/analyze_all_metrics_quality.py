"""
全面质量分析：所有已实现的缺失指标

分析内容：
1. 数量验证（记录数、覆盖率）
2. 数值合理性（范围、异常值）
3. 物理约束验证（能量守恒、效率范围）
4. 数据质量评级
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# 设置控制台编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def analyze_metric_quality(metric_key: str, device_ids: list, start_time: datetime, end_time: datetime):
    """分析单个指标的数据质量"""
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询指标数据统计
            cur.execute("""
                SELECT 
                    fm.device_id,
                    COUNT(*) as record_count,
                    MIN(fm.value) as min_value,
                    MAX(fm.value) as max_value,
                    AVG(fm.value) as avg_value,
                    STDDEV(fm.value) as stddev_value,
                    SUM(CASE WHEN fm.value < 0 THEN 1 ELSE 0 END) as negative_count,
                    SUM(CASE WHEN fm.value IS NULL THEN 1 ELSE 0 END) as null_count
                FROM fact_measurements fm
                JOIN dim_metric_config mc ON mc.id = fm.metric_id
                WHERE mc.metric_key = %s
                  AND fm.station_id = 1
                  AND fm.device_id = ANY(%s)
                  AND fm.ts_bucket >= %s
                  AND fm.ts_bucket < %s
                GROUP BY fm.device_id
                ORDER BY fm.device_id
            """, (metric_key, device_ids, start_time, end_time))
            
            results = cur.fetchall()
            
            if not results:
                return None
            
            # 计算总统计
            total_records = sum(r[1] for r in results)
            total_negative = sum(r[6] for r in results)
            total_null = sum(r[7] for r in results)
            
            # 计算预期记录数（基于时间范围）
            total_seconds = int((end_time - start_time).total_seconds())
            expected_records_per_device = total_seconds
            expected_total_records = expected_records_per_device * len(device_ids)
            coverage_rate = (total_records / expected_total_records * 100) if expected_total_records > 0 else 0
            
            return {
                'metric_key': metric_key,
                'device_count': len(results),
                'total_records': total_records,
                'expected_records': expected_total_records,
                'coverage_rate': coverage_rate,
                'negative_count': total_negative,
                'null_count': total_null,
                'device_stats': results
            }


def verify_power_relationships():
    """验证功率关系：P_hydraulic < P_shaft < P_active"""
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                WITH power_data AS (
                    SELECT 
                        fm.ts_bucket,
                        fm.device_id,
                        mc.metric_key,
                        fm.value
                    FROM fact_measurements fm
                    JOIN dim_metric_config mc ON mc.id = fm.metric_id
                    WHERE fm.station_id = 1
                      AND fm.device_id IN (1, 2, 3, 4, 5, 6)
                      AND mc.metric_key IN ('pump_active_power', 'pump_shaft_power', 'pump_hydraulic_power')
                      AND fm.ts_bucket >= '2025-10-22 08:00:00+00:00'
                      AND fm.ts_bucket < '2025-10-23 07:13:29+00:00'
                )
                SELECT 
                    p_active.device_id,
                    COUNT(*) as count,
                    AVG(p_active.value) as avg_active,
                    AVG(p_shaft.value) as avg_shaft,
                    AVG(p_hydro.value) as avg_hydro,
                    SUM(CASE WHEN p_hydro.value < p_shaft.value THEN 1 ELSE 0 END) as valid_h_s,
                    SUM(CASE WHEN p_shaft.value < p_active.value THEN 1 ELSE 0 END) as valid_s_a,
                    SUM(CASE WHEN p_hydro.value < p_shaft.value AND p_shaft.value < p_active.value THEN 1 ELSE 0 END) as valid_all
                FROM power_data p_active
                LEFT JOIN power_data p_shaft 
                    ON p_shaft.ts_bucket = p_active.ts_bucket 
                    AND p_shaft.device_id = p_active.device_id
                    AND p_shaft.metric_key = 'pump_shaft_power'
                LEFT JOIN power_data p_hydro 
                    ON p_hydro.ts_bucket = p_active.ts_bucket 
                    AND p_hydro.device_id = p_active.device_id
                    AND p_hydro.metric_key = 'pump_hydraulic_power'
                WHERE p_active.metric_key = 'pump_active_power'
                GROUP BY p_active.device_id
                ORDER BY p_active.device_id
            """)
            
            return cur.fetchall()


def main():
    """主函数"""
    print("="*100)
    print("全面质量分析：所有已实现的缺失指标")
    print("="*100)
    
    # 初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 定义分析范围
    start_time = datetime(2025, 10, 22, 8, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 10, 23, 7, 13, 29, tzinfo=timezone.utc)
    
    # 定义要分析的指标
    metrics_config = [
        {'metric_key': 'pump_flow_rate', 'devices': [1, 2, 3, 4, 5, 6]},
        {'metric_key': 'pump_inlet_pressure', 'devices': [1, 2, 3, 4, 5, 6]},
        {'metric_key': 'pump_head', 'devices': [1, 2, 3, 4, 5, 6]},
        {'metric_key': 'pump_efficiency', 'devices': [1, 2, 3, 4, 5, 6]},
        {'metric_key': 'pump_speed', 'devices': [1, 2, 3, 4, 5, 6]},
        {'metric_key': 'pump_shaft_power', 'devices': [1, 2, 3, 4, 5, 6]},
        {'metric_key': 'pump_torque', 'devices': [1, 2, 3, 4, 5, 6]},
        {'metric_key': 'pump_hydraulic_power', 'devices': [1, 2, 3, 4, 5, 6]},
        {'metric_key': 'main_pipeline_inlet_pressure', 'devices': [7]},
    ]
    
    print(f"\n分析配置:")
    print(f"  - 时间范围: {start_time} ~ {end_time}")
    print(f"  - 时间跨度: {(end_time - start_time).total_seconds() / 3600:.1f} 小时")
    print(f"  - 指标数量: {len(metrics_config)}")
    
    # 分析各指标
    print(f"\n{'='*100}")
    print("1. 数量和覆盖率分析")
    print(f"{'='*100}")
    
    all_results = []
    
    for config in metrics_config:
        result = analyze_metric_quality(
            config['metric_key'],
            config['devices'],
            start_time,
            end_time
        )
        if result:
            all_results.append(result)
    
    # 打印汇总表格
    print(f"\n{'指标':<35} {'设备数':<8} {'记录数':<12} {'覆盖率':<10} {'负值':<8} {'空值':<8}")
    print("-"*100)
    
    for result in all_results:
        print(f"{result['metric_key']:<35} "
              f"{result['device_count']:<8} "
              f"{result['total_records']:<12,} "
              f"{result['coverage_rate']:<9.1f}% "
              f"{result['negative_count']:<8} "
              f"{result['null_count']:<8}")
    
    # 2. 物理约束验证
    print(f"\n{'='*100}")
    print("2. 物理约束验证：P_hydraulic < P_shaft < P_active")
    print(f"{'='*100}")

    power_results = verify_power_relationships()

    if power_results:
        print(f"\n{'设备':<8} {'记录数':<10} {'P_active':<12} {'P_shaft':<12} {'P_hydro':<12} {'P_h<P_s':<10} {'P_s<P_a':<10} {'全部满足':<10}")
        print("-"*100)

        total_count = 0
        total_valid = 0

        for row in power_results:
            device_id, count, avg_active, avg_shaft, avg_hydro, valid_h_s, valid_s_a, valid_all = row
            total_count += count if count else 0
            total_valid += valid_all if valid_all else 0

            h_s_pct = (valid_h_s / count * 100) if count and valid_h_s else 0
            s_a_pct = (valid_s_a / count * 100) if count and valid_s_a else 0
            all_pct = (valid_all / count * 100) if count and valid_all else 0

            avg_active_str = f"{avg_active:.2f}" if avg_active else "N/A"
            avg_shaft_str = f"{avg_shaft:.2f}" if avg_shaft else "N/A"
            avg_hydro_str = f"{avg_hydro:.2f}" if avg_hydro else "N/A"

            print(f"{device_id:<8} {count if count else 0:<10} {avg_active_str:<12} {avg_shaft_str:<12} {avg_hydro_str:<12} "
                  f"{h_s_pct:<9.1f}% {s_a_pct:<9.1f}% {all_pct:<9.1f}%")

        print("-"*100)
        if total_count > 0:
            print(f"总计: {total_count} 条记录, {total_valid} 条满足约束 ({total_valid/total_count*100:.1f}%)")

            if total_valid == total_count:
                print("\n✅ 所有数据都满足物理约束")
            else:
                print(f"\n⚠️ 有 {total_count - total_valid} 条数据不满足物理约束")
    else:
        print("\n⚠️ 未找到功率数据进行验证")

    # 3. 数据质量评级
    print(f"\n{'='*100}")
    print("3. 数据质量评级")
    print(f"{'='*100}")

    print(f"\n{'指标':<35} {'覆盖率':<12} {'数据完整性':<15} {'质量评级':<10}")
    print("-"*100)

    for result in all_results:
        coverage = result['coverage_rate']
        has_issues = result['negative_count'] > 0 or result['null_count'] > 0

        # 评级逻辑
        if coverage >= 95 and not has_issues:
            rating = "⭐⭐⭐⭐⭐"
            quality = "优秀"
        elif coverage >= 80 and not has_issues:
            rating = "⭐⭐⭐⭐"
            quality = "良好"
        elif coverage >= 50:
            rating = "⭐⭐⭐"
            quality = "一般"
        elif coverage >= 20:
            rating = "⭐⭐"
            quality = "较差"
        else:
            rating = "⭐"
            quality = "差"

        completeness = "完整" if not has_issues else f"有问题({result['negative_count']}负值,{result['null_count']}空值)"

        print(f"{result['metric_key']:<35} {coverage:<11.1f}% {completeness:<15} {rating} {quality}")

    # 4. 问题诊断
    print(f"\n{'='*100}")
    print("4. 问题诊断和建议")
    print(f"{'='*100}")

    issues = []

    for result in all_results:
        if result['coverage_rate'] < 50:
            issues.append({
                'severity': 'HIGH',
                'metric': result['metric_key'],
                'issue': f"覆盖率过低 ({result['coverage_rate']:.1f}%)",
                'suggestion': "检查数据过滤逻辑，可能过滤条件过严"
            })
        elif result['coverage_rate'] < 95:
            issues.append({
                'severity': 'MEDIUM',
                'metric': result['metric_key'],
                'issue': f"覆盖率偏低 ({result['coverage_rate']:.1f}%)",
                'suggestion': "检查依赖数据的可用性"
            })

    if issues:
        print(f"\n发现 {len(issues)} 个问题：\n")
        for idx, issue in enumerate(issues, 1):
            print(f"{idx}. [{issue['severity']}] {issue['metric']}")
            print(f"   问题: {issue['issue']}")
            print(f"   建议: {issue['suggestion']}\n")
    else:
        print("\n✅ 未发现明显问题")

    # 5. 总结
    print(f"\n{'='*100}")
    print("5. 总体总结")
    print(f"{'='*100}")

    total_metrics = len(all_results)
    excellent_metrics = sum(1 for r in all_results if r['coverage_rate'] >= 95 and r['negative_count'] == 0 and r['null_count'] == 0)
    good_metrics = sum(1 for r in all_results if 80 <= r['coverage_rate'] < 95 and r['negative_count'] == 0 and r['null_count'] == 0)
    total_records = sum(r['total_records'] for r in all_results)

    print(f"\n指标统计:")
    print(f"  - 总指标数: {total_metrics}")
    print(f"  - 优秀指标: {excellent_metrics} ({excellent_metrics/total_metrics*100:.1f}%)")
    print(f"  - 良好指标: {good_metrics} ({good_metrics/total_metrics*100:.1f}%)")
    print(f"  - 总记录数: {total_records:,}")

    print(f"\n✅ 质量分析完成")


if __name__ == '__main__':
    main()

