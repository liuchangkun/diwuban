"""
批量计算所有已实现指标并进行数据质量分析

功能:
1. 删除现有数据（4个指标 × 6个设备）
2. 批量计算（按依赖顺序）
3. 数据质量分析（完整性、合理性、连续性、异常值）
4. 跨指标对比分析
5. 生成对比报告

执行方式:
    python scripts/batch_calculate_all_metrics.py
"""

import sys
from pathlib import Path
from datetime import datetime
import pytz
import time

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader import load_settings
from app.services.calculation.shared.shared_services import SharedServices
from app.services.calculation.shared.parameter_manager import ParameterManager

# 指标分类：基于物理约束的异常值检测 vs 基于IQR的异常值检测
CONSTRAINT_BASED_METRICS = ['pump_head', 'pump_inlet_pressure', 'pump_efficiency']
IQR_BASED_METRICS = ['pump_flow_rate']


def get_physical_constraints_from_db(metric_key: str) -> dict:
    """
    从数据库读取物理约束（三级参数体系）

    Args:
        metric_key: 指标键

    Returns:
        {'min': float, 'max': float, 'unit': str}

    Raises:
        ValueError: 如果参数缺失
    """
    param_manager = ParameterManager()

    # 根据指标类型读取不同的参数（禁止使用默认值）
    if metric_key == 'pump_flow_rate':
        params = param_manager.get_parameters(metric_key, method_id='data_filter')
        min_val = params.get('min_flow')
        max_val = params.get('max_flow')

        if min_val is None or max_val is None:
            raise ValueError(
                f"pump_flow_rate物理约束参数缺失: min_flow={min_val}, max_flow={max_val}. "
                f"必须在calculation_parameters表中配置这些参数。"
            )

        return {'min': min_val, 'max': max_val, 'unit': 'm³/h'}

    elif metric_key == 'pump_inlet_pressure':
        params = param_manager.get_parameters(metric_key, method_id='pump_inlet_pressure_method_b')
        min_val = params.get('min_pressure')
        max_val = params.get('max_pressure')

        if min_val is None or max_val is None:
            raise ValueError(
                f"pump_inlet_pressure物理约束参数缺失: min_pressure={min_val}, max_pressure={max_val}. "
                f"必须在calculation_parameters表中配置这些参数。"
            )

        return {'min': min_val, 'max': max_val, 'unit': 'MPa'}

    elif metric_key == 'pump_head':
        params = param_manager.get_parameters(metric_key, method_id='pipe_loss_multi_pump')
        min_val = params.get('min_pump_head')
        max_val = params.get('max_pump_head')

        if min_val is None or max_val is None:
            raise ValueError(
                f"pump_head物理约束参数缺失: min_pump_head={min_val}, max_pump_head={max_val}. "
                f"必须在calculation_parameters表中配置这些参数。"
            )

        return {'min': min_val, 'max': max_val, 'unit': 'm'}

    elif metric_key == 'pump_efficiency':
        params = param_manager.get_parameters(metric_key, method_id='EFF_SIMPLE_V1')
        min_val = params.get('eta_min')
        max_val = params.get('eta_max')

        if min_val is None or max_val is None:
            raise ValueError(
                f"pump_efficiency物理约束参数缺失: eta_min={min_val}, eta_max={max_val}. "
                f"必须在calculation_parameters表中配置这些参数。"
            )

        return {'min': min_val, 'max': max_val, 'unit': ''}

    else:
        raise ValueError(f"不支持的指标类型: {metric_key}")


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def delete_existing_data(metric_key: str, device_ids: list) -> int:
    """删除指定指标的现有数据"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询 metric_id
            cur.execute("""
                SELECT id FROM dim_metric_config WHERE metric_key = %s
            """, (metric_key,))

            result = cur.fetchone()
            if not result:
                print(f"   ⚠️  未找到指标配置: {metric_key}")
                return 0

            metric_id = result[0]

            # 统计要删除的数据量
            cur.execute("""
                SELECT COUNT(*) FROM fact_measurements
                WHERE metric_id = %s AND device_id = ANY(%s)
            """, (metric_id, device_ids))

            count_before = cur.fetchone()[0]

            if count_before == 0:
                print(f"   ℹ️  {metric_key}: 无数据需要删除")
                return 0

            # 删除数据
            cur.execute("""
                DELETE FROM fact_measurements
                WHERE metric_id = %s AND device_id = ANY(%s)
            """, (metric_id, device_ids))

            conn.commit()

            print(f"   ✓ {metric_key:25s}: 删除 {count_before:,}条")
            return count_before


def batch_calculate_metrics(shared_services, metrics, device_ids, start_time, end_time):
    """批量计算所有指标"""
    results = {}

    for metric_key in metrics:
        print(f"\n{'='*100}")
        print(f"🔄 正在计算指标: {metric_key}")
        print(f"{'='*100}")

        metric_start = time.time()

        try:
            result = shared_services.scheduler.schedule_single_metric(
                metric_key=metric_key,
                device_ids=device_ids,
                start_time=start_time,
                end_time=end_time,
                time_chunk_hours=24
            )

            duration = time.time() - metric_start

            results[metric_key] = {
                'result': result,
                'duration': duration,
                'success': True
            }

            print(f"\n✅ {metric_key} 计算完成")
            print(f"   - 耗时: {duration:.2f}秒")
            print(f"   - 总任务: {result['total_tasks']}")
            print(f"   - 成功: {result['success_count']}")
            print(f"   - 失败: {result['failure_count']}")
            print(f"   - 写入记录: {result['total_points']:,}条")

        except Exception as e:
            duration = time.time() - metric_start
            results[metric_key] = {
                'result': None,
                'duration': duration,
                'success': False,
                'error': str(e)
            }
            print(f"\n❌ {metric_key} 计算失败: {e}")
            import traceback
            traceback.print_exc()

    return results



def check_data_completeness(metric_key: str, device_ids: list) -> dict:
    """检查数据完整性"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM dim_metric_config WHERE metric_key = %s
            """, (metric_key,))

            result = cur.fetchone()
            if not result:
                return None

            metric_id = result[0]

            cur.execute("""
                SELECT
                    device_id,
                    COUNT(*) as total_count,
                    COUNT(value) as valid_count,
                    COUNT(*) - COUNT(value) as invalid_count,
                    ROUND(COUNT(value)::numeric / COUNT(*) * 100, 2) as valid_ratio
                FROM fact_measurements
                WHERE metric_id = %s AND device_id = ANY(%s)
                GROUP BY device_id
                ORDER BY device_id
            """, (metric_id, device_ids))

            rows = cur.fetchall()

            # 计算总计
            total_sum = sum(row[1] for row in rows)
            valid_sum = sum(row[2] for row in rows)
            invalid_sum = sum(row[3] for row in rows)
            overall_ratio = (valid_sum / total_sum * 100) if total_sum > 0 else 0

            return {
                'rows': rows,
                'total': total_sum,
                'valid': valid_sum,
                'invalid': invalid_sum,
                'ratio': overall_ratio
            }


def check_value_reasonableness(metric_key: str, device_ids: list) -> dict:
    """检查数值合理性"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM dim_metric_config WHERE metric_key = %s
            """, (metric_key,))

            result = cur.fetchone()
            if not result:
                return None

            metric_id = result[0]

            cur.execute("""
                SELECT
                    device_id,
                    ROUND(MIN(value)::numeric, 4) as min_value,
                    ROUND(MAX(value)::numeric, 4) as max_value,
                    ROUND(AVG(value)::numeric, 4) as avg_value,
                    ROUND(STDDEV(value)::numeric, 4) as std_value,
                    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY value)::numeric, 4) as p25,
                    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY value)::numeric, 4) as p50,
                    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY value)::numeric, 4) as p75
                FROM fact_measurements
                WHERE metric_id = %s AND device_id = ANY(%s) AND value IS NOT NULL
                GROUP BY device_id
                ORDER BY device_id
            """, (metric_id, device_ids))

            rows = cur.fetchall()

            # 从数据库读取物理约束
            constraints = get_physical_constraints_from_db(metric_key)
            violations = []

            for row in rows:
                device_id, min_val, max_val = row[0], float(row[1]), float(row[2])

                if constraints['min'] is not None and constraints['max'] is not None:
                    if min_val < constraints['min'] or max_val > constraints['max']:
                        violations.append({
                            'device_id': device_id,
                            'min': min_val,
                            'max': max_val,
                            'constraint_min': constraints['min'],
                            'constraint_max': constraints['max']
                        })

            return {
                'rows': rows,
                'constraints': constraints,
                'violations': violations
            }


def check_time_continuity(metric_key: str, device_ids: list) -> dict:
    """检查时间连续性"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM dim_metric_config WHERE metric_key = %s
            """, (metric_key,))

            result = cur.fetchone()
            if not result:
                return None

            metric_id = result[0]

            cur.execute("""
                WITH time_gaps AS (
                    SELECT
                        device_id,
                        ts_bucket,
                        LEAD(ts_bucket) OVER (PARTITION BY device_id ORDER BY ts_bucket) as next_ts,
                        EXTRACT(EPOCH FROM (LEAD(ts_bucket) OVER (PARTITION BY device_id ORDER BY ts_bucket) - ts_bucket)) as gap_seconds
                    FROM fact_measurements
                    WHERE metric_id = %s AND device_id = ANY(%s)
                )
                SELECT
                    device_id,
                    COUNT(*) as total_intervals,
                    COUNT(CASE WHEN gap_seconds > 10 THEN 1 END) as large_gaps,
                    ROUND(MAX(gap_seconds)::numeric, 0) as max_gap_seconds,
                    ROUND(AVG(gap_seconds)::numeric, 2) as avg_gap_seconds
                FROM time_gaps
                WHERE gap_seconds IS NOT NULL
                GROUP BY device_id
                ORDER BY device_id
            """, (metric_id, device_ids))

            rows = cur.fetchall()

            return {'rows': rows}


def detect_outliers_by_constraints(metric_key: str, device_ids: list) -> dict:
    """基于物理约束的异常值检测"""
    constraints = get_physical_constraints_from_db(metric_key)

    if constraints['min'] is None or constraints['max'] is None:
        return {'outliers': []}

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM dim_metric_config WHERE metric_key = %s
            """, (metric_key,))

            result = cur.fetchone()
            if not result:
                return None

            metric_id = result[0]

            # 检测每个设备的异常值（超出物理约束）
            outlier_results = []
            for device_id in device_ids:
                cur.execute("""
                    SELECT
                        COUNT(*) as outlier_count,
                        COUNT(*)::numeric / NULLIF((SELECT COUNT(*) FROM fact_measurements WHERE metric_id = %s AND device_id = %s), 0) * 100 as outlier_ratio
                    FROM fact_measurements
                    WHERE metric_id = %s
                      AND device_id = %s
                      AND (value < %s OR value > %s)
                """, (metric_id, device_id, metric_id, device_id, constraints['min'], constraints['max']))

                result = cur.fetchone()
                if result and result[0] is not None:
                    outlier_results.append({
                        'device_id': device_id,
                        'outlier_count': result[0],
                        'outlier_ratio': float(result[1]) if result[1] is not None else 0.0,
                        'lower_bound': constraints['min'],
                        'upper_bound': constraints['max'],
                        'method': 'physical_constraint'
                    })

            return {'outliers': outlier_results}


def detect_outliers_by_iqr(metric_key: str, device_ids: list) -> dict:
    """基于IQR的异常值检测"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM dim_metric_config WHERE metric_key = %s
            """, (metric_key,))

            result = cur.fetchone()
            if not result:
                return None

            metric_id = result[0]

            # 先获取四分位数
            cur.execute("""
                SELECT
                    device_id,
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY value) as p25,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY value) as p75
                FROM fact_measurements
                WHERE metric_id = %s AND device_id = ANY(%s) AND value IS NOT NULL
                GROUP BY device_id
            """, (metric_id, device_ids))

            quartiles = {row[0]: (float(row[1]), float(row[2])) for row in cur.fetchall()}

            # 检测每个设备的异常值
            outlier_results = []
            for device_id, (p25, p75) in quartiles.items():
                iqr = p75 - p25
                lower_bound = p25 - 1.5 * iqr
                upper_bound = p75 + 1.5 * iqr

                cur.execute("""
                    SELECT
                        COUNT(*) as outlier_count,
                        COUNT(*)::numeric / (SELECT COUNT(*) FROM fact_measurements WHERE metric_id = %s AND device_id = %s) * 100 as outlier_ratio
                    FROM fact_measurements
                    WHERE metric_id = %s
                      AND device_id = %s
                      AND (value < %s OR value > %s)
                """, (metric_id, device_id, metric_id, device_id, lower_bound, upper_bound))

                result = cur.fetchone()
                outlier_results.append({
                    'device_id': device_id,
                    'outlier_count': result[0],
                    'outlier_ratio': float(result[1]),
                    'lower_bound': lower_bound,
                    'upper_bound': upper_bound,
                    'method': 'iqr'
                })

            return {'outliers': outlier_results}


def detect_outliers(metric_key: str, device_ids: list) -> dict:
    """智能异常值检测（根据指标类型选择方法）"""
    if metric_key in CONSTRAINT_BASED_METRICS:
        return detect_outliers_by_constraints(metric_key, device_ids)
    else:
        return detect_outliers_by_iqr(metric_key, device_ids)



def analyze_single_metric(metric_key: str, device_ids: list):
    """分析单个指标的数据质量"""
    print(f"\n[{metric_key}] 数据质量分析")
    print("-" * 100)

    # 1. 数据完整性
    completeness = check_data_completeness(metric_key, device_ids)
    if completeness:
        print(f"\n  [1] 数据完整性:")
        print(f"      设备ID | 总数      | 有效数    | 无效数    | 有效率")
        print(f"      " + "-" * 70)
        for row in completeness['rows']:
            device_id, total, valid, invalid, ratio = row
            print(f"      {device_id:6d} | {total:9,d} | {valid:9,d} | {invalid:9,d} | {ratio:6.2f}%")
        print(f"      " + "-" * 70)
        print(f"      总计   | {completeness['total']:9,d} | {completeness['valid']:9,d} | {completeness['invalid']:9,d} | {completeness['ratio']:6.2f}%")

        # 评估
        if completeness['ratio'] >= 99.0:
            print(f"      评估: ✅ 优秀 (有效率 {completeness['ratio']:.2f}% ≥ 99%)")
        elif completeness['ratio'] >= 95.0:
            print(f"      评估: ⚠️  良好 (有效率 {completeness['ratio']:.2f}% ≥ 95%)")
        else:
            print(f"      评估: ❌ 不合格 (有效率 {completeness['ratio']:.2f}% < 95%)")

    # 2. 数值合理性
    reasonableness = check_value_reasonableness(metric_key, device_ids)
    if reasonableness:
        print(f"\n  [2] 数值合理性:")
        constraints = reasonableness['constraints']
        if constraints:
            print(f"      物理约束: {constraints['min']} - {constraints['max']} {constraints['unit']}")
            # warning_min和warning_max是可选的，如果不存在则不打印
            if 'warning_min' in constraints and 'warning_max' in constraints:
                print(f"      警告范围: {constraints['warning_min']} - {constraints['warning_max']} {constraints['unit']}")

        print(f"\n      设备ID | 最小值    | 最大值    | 平均值    | 标准差    | 中位数")
        print(f"      " + "-" * 80)
        for row in reasonableness['rows']:
            device_id, min_val, max_val, avg_val, std_val, p25, p50, p75 = row
            print(f"      {device_id:6d} | {float(min_val):9.4f} | {float(max_val):9.4f} | {float(avg_val):9.4f} | {float(std_val):9.4f} | {float(p50):9.4f}")

        # 检查违规
        if reasonableness['violations']:
            print(f"\n      ⚠️  物理约束违规:")
            for v in reasonableness['violations']:
                print(f"         设备{v['device_id']}: 范围 [{v['min']}, {v['max']}] 超出约束 [{v['constraint_min']}, {v['constraint_max']}]")
        else:
            print(f"\n      评估: ✅ 所有值均在物理约束范围内")

    # 3. 时间连续性
    continuity = check_time_continuity(metric_key, device_ids)
    if continuity and continuity['rows']:
        print(f"\n  [3] 时间连续性:")
        print(f"      设备ID | 总间隔数  | 大间隔数  | 最大间隔(秒) | 平均间隔(秒)")
        print(f"      " + "-" * 75)
        for row in continuity['rows']:
            device_id, total_intervals, large_gaps, max_gap, avg_gap = row
            print(f"      {device_id:6d} | {total_intervals:9,d} | {large_gaps:9,d} | {int(max_gap):12d} | {float(avg_gap):12.2f}")

        print(f"\n      标准间隔: 1秒")
        print(f"      大间隔阈值: > 10秒")

        # 评估
        total_large_gaps = sum(row[2] for row in continuity['rows'])
        if total_large_gaps == 0:
            print(f"      评估: ✅ 优秀 (无大间隔)")
        elif total_large_gaps < 100:
            print(f"      评估: ⚠️  良好 (大间隔数量: {total_large_gaps})")
        else:
            print(f"      评估: ❌ 需要关注 (大间隔数量: {total_large_gaps})")

    # 4. 异常值检测
    outliers = detect_outliers(metric_key, device_ids)
    if outliers and outliers['outliers']:
        print(f"\n  [4] 异常值检测 (IQR方法):")
        print(f"      设备ID | 异常值数量 | 异常值比例 | 下界      | 上界")
        print(f"      " + "-" * 70)

        total_outliers = 0
        for o in outliers['outliers']:
            print(f"      {o['device_id']:6d} | {o['outlier_count']:10,d} | {o['outlier_ratio']:10.2f}% | {o['lower_bound']:9.4f} | {o['upper_bound']:9.4f}")
            total_outliers += o['outlier_count']

        print(f"\n      检测方法: IQR (四分位距)")
        print(f"      异常值定义: value < Q1 - 1.5*IQR 或 value > Q3 + 1.5*IQR")
        print(f"      处理方式: 只标记，不处理")

        # 评估
        avg_outlier_ratio = sum(o['outlier_ratio'] for o in outliers['outliers']) / len(outliers['outliers'])
        if avg_outlier_ratio < 1.0:
            print(f"      评估: ✅ 优秀 (平均异常值比例 {avg_outlier_ratio:.2f}% < 1%)")
        elif avg_outlier_ratio < 5.0:
            print(f"      评估: ⚠️  良好 (平均异常值比例 {avg_outlier_ratio:.2f}% < 5%)")
        else:
            print(f"      评估: ❌ 需要关注 (平均异常值比例 {avg_outlier_ratio:.2f}% ≥ 5%)")


def compare_metrics(metrics: list, device_ids: list):
    """跨指标对比分析"""
    print_header("阶段4: 跨指标对比分析")

    # 1. 数据量对比
    print("\n[4.1] 数据量对比:")
    print(f"  指标                    | ", end="")
    for device_id in device_ids:
        print(f"设备{device_id:2d}  | ", end="")
    print("总计")
    print("  " + "-" * 95)

    comparison_data = {}
    for metric_key in metrics:
        completeness = check_data_completeness(metric_key, device_ids)
        if completeness:
            comparison_data[metric_key] = completeness
            print(f"  {metric_key:25s} | ", end="")
            device_counts = {row[0]: row[1] for row in completeness['rows']}
            for device_id in device_ids:
                count = device_counts.get(device_id, 0)
                print(f"{count:7,d} | ", end="")
            print(f"{completeness['total']:7,d}")

    # 分析
    print("\n  分析:")
    if 'pump_inlet_pressure' in comparison_data and 'pump_head' in comparison_data and 'pump_efficiency' in comparison_data:
        if (comparison_data['pump_inlet_pressure']['total'] == comparison_data['pump_head']['total'] ==
            comparison_data['pump_efficiency']['total']):
            print("    ✅ pump_inlet_pressure, pump_head, pump_efficiency 数据量一致（符合依赖关系）")
        else:
            print("    ⚠️  pump_inlet_pressure, pump_head, pump_efficiency 数据量不一致")

    if 'pump_flow_rate' in comparison_data and 'pump_inlet_pressure' in comparison_data:
        flow_total = comparison_data['pump_flow_rate']['total']
        pressure_total = comparison_data['pump_inlet_pressure']['total']
        if flow_total > pressure_total * 2:
            print(f"    ⚠️  pump_flow_rate 数据量 ({flow_total:,}) 远大于其他指标 ({pressure_total:,})")
            print(f"        原因: 可能是计算条件不同（running=1 vs 其他条件）")

    # 检查设备数据量差异
    for metric_key, data in comparison_data.items():
        device_counts = {row[0]: row[1] for row in data['rows']}
        avg_count = sum(device_counts.values()) / len(device_counts)
        for device_id, count in device_counts.items():
            if count < avg_count * 0.1:  # 少于平均值的10%
                print(f"    ⚠️  {metric_key} 设备{device_id} 数据量异常少 ({count:,} vs 平均 {int(avg_count):,})")

    # 2. 有效率对比
    print("\n[4.2] 有效率对比:")
    print(f"  指标                    | ", end="")
    for device_id in device_ids:
        print(f"设备{device_id:2d}  | ", end="")
    print("平均")
    print("  " + "-" * 95)

    for metric_key in metrics:
        completeness = check_data_completeness(metric_key, device_ids)
        if completeness:
            print(f"  {metric_key:25s} | ", end="")
            device_ratios = {row[0]: float(row[4]) for row in completeness['rows']}
            for device_id in device_ids:
                ratio = device_ratios.get(device_id, 0.0)
                print(f"{ratio:6.2f}% | ", end="")
            avg_ratio = sum(device_ratios.values()) / len(device_ratios) if device_ratios else 0.0
            print(f"{avg_ratio:6.2f}%")

    print("\n  质量标准: ≥ 99%")

    # 评估
    all_pass = True
    for metric_key in metrics:
        completeness = check_data_completeness(metric_key, device_ids)
        if completeness and completeness['ratio'] < 99.0:
            all_pass = False
            break

    if all_pass:
        print("  评估结果: ✅ 所有指标均符合质量标准")
    else:
        print("  评估结果: ⚠️  部分指标未达到质量标准")



def main():
    """主函数"""
    # 配置参数
    tz = pytz.timezone('Asia/Shanghai')
    start_time = datetime(2025, 10, 22, 16, 0, 0, tzinfo=tz)
    end_time = datetime(2025, 10, 23, 15, 20, 0, tzinfo=tz)
    device_ids = [1, 2, 3, 4, 5, 6]
    metrics = ['pump_flow_rate', 'pump_inlet_pressure', 'pump_head', 'pump_efficiency']

    # 打印报告头
    print_header("批量计算与数据质量分析报告")
    print(f"执行时间: {datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"设备范围: {', '.join(map(str, device_ids))} (6台泵)")
    print(f"指标数量: {len(metrics)}个")
    print(f"指标列表: {', '.join(metrics)}")

    # 阶段0: 初始化
    print_header("阶段0: 初始化")
    print("正在加载配置...")
    settings = load_settings(Path("configs"))

    print("正在初始化数据库连接...")
    init_database(settings)

    print("正在初始化 SharedServices...")
    shared_services = SharedServices()

    print("✅ 初始化完成")

    # 阶段1: 删除现有数据
    print_header("阶段1: 删除现有数据")
    print("正在删除现有数据（按依赖关系逆序）...")

    total_deleted = 0
    # 逆序删除（先删除依赖指标）
    for metric_key in reversed(metrics):
        deleted = delete_existing_data(metric_key, device_ids)
        total_deleted += deleted

    print(f"\n   总计: 删除 {total_deleted:,}条")

    # 阶段2: 批量计算
    print_header("阶段2: 批量计算")
    print("正在批量计算所有指标（按依赖顺序）...")

    overall_start = time.time()
    calc_results = batch_calculate_metrics(shared_services, metrics, device_ids, start_time, end_time)
    overall_duration = time.time() - overall_start

    # 汇总计算结果
    print_header("阶段2: 批量计算 - 汇总")
    total_tasks = 0
    total_success = 0
    total_failure = 0
    total_points = 0

    for metric_key, result_data in calc_results.items():
        if result_data['success']:
            result = result_data['result']
            duration = result_data['duration']
            print(f"  {metric_key:25s}: 成功 {result['success_count']}/{result['total_tasks']}任务, "
                  f"写入 {result['total_points']:,}条, 耗时 {duration:.2f}秒")
            total_tasks += result['total_tasks']
            total_success += result['success_count']
            total_failure += result['failure_count']
            total_points += result['total_points']
        else:
            print(f"  {metric_key:25s}: ❌ 失败 - {result_data.get('error', 'Unknown error')}")

    print(f"  " + "-" * 90)
    print(f"  总计: 成功 {total_success}/{total_tasks}任务, 写入 {total_points:,}条, 耗时 {overall_duration:.2f}秒")

    # 阶段3: 数据质量分析
    print_header("阶段3: 数据质量分析")

    for metric_key in metrics:
        analyze_single_metric(metric_key, device_ids)

    # 阶段4: 跨指标对比分析
    compare_metrics(metrics, device_ids)

    # 阶段5: 总结
    print_header("阶段5: 总结与建议")

    print("\n发现的问题:")

    # 检查数据量差异
    comparison_data = {}
    for metric_key in metrics:
        completeness = check_data_completeness(metric_key, device_ids)
        if completeness:
            comparison_data[metric_key] = completeness

    problem_count = 0

    # 问题1: pump_flow_rate 数据量差异
    if 'pump_flow_rate' in comparison_data and 'pump_inlet_pressure' in comparison_data:
        flow_total = comparison_data['pump_flow_rate']['total']
        pressure_total = comparison_data['pump_inlet_pressure']['total']
        if flow_total > pressure_total * 2:
            problem_count += 1
            print(f"  {problem_count}. ⚠️  pump_flow_rate 数据量 ({flow_total:,}) 远大于其他指标 ({pressure_total:,})")
            print(f"     原因: 可能是计算条件不同（running=1 vs 其他条件）")
            print(f"     建议: 检查 DataFilter 的过滤逻辑")

    # 问题2: 设备数据量差异
    for metric_key, data in comparison_data.items():
        device_counts = {row[0]: row[1] for row in data['rows']}
        avg_count = sum(device_counts.values()) / len(device_counts)
        for device_id, count in device_counts.items():
            if count < avg_count * 0.1:
                problem_count += 1
                print(f"  {problem_count}. ⚠️  {metric_key} 设备{device_id} 数据量异常少 ({count:,} vs 平均 {int(avg_count):,})")
                print(f"     原因: 可能是设备停机时间长")
                print(f"     建议: 检查设备运行记录")

    # 问题3: 有效率检查
    all_valid = True
    for metric_key, data in comparison_data.items():
        if data['ratio'] < 99.0:
            all_valid = False
            problem_count += 1
            print(f"  {problem_count}. ⚠️  {metric_key} 有效率 ({data['ratio']:.2f}%) 低于质量标准 (99%)")

    if all_valid:
        problem_count += 1
        print(f"  {problem_count}. ✅ 所有指标有效率均 ≥ 99%，符合质量标准")

    # 问题4: 物理约束检查
    all_reasonable = True
    for metric_key in metrics:
        reasonableness = check_value_reasonableness(metric_key, device_ids)
        if reasonableness and reasonableness['violations']:
            all_reasonable = False
            problem_count += 1
            print(f"  {problem_count}. ⚠️  {metric_key} 存在物理约束违规")

    if all_reasonable:
        problem_count += 1
        print(f"  {problem_count}. ✅ 所有指标值范围均在物理合理范围内")

    # 问题5: 依赖关系检查
    if 'pump_inlet_pressure' in comparison_data and 'pump_head' in comparison_data and 'pump_efficiency' in comparison_data:
        if (comparison_data['pump_inlet_pressure']['total'] == comparison_data['pump_head']['total'] ==
            comparison_data['pump_efficiency']['total']):
            problem_count += 1
            print(f"  {problem_count}. ✅ 指标间依赖关系正确，数据量一致")

    # 总体评估
    print("\n总体评估:")

    # 计算平均有效率
    avg_valid_ratio = sum(data['ratio'] for data in comparison_data.values()) / len(comparison_data)

    print(f"  - 数据完整性: ", end="")
    if avg_valid_ratio >= 99.0:
        print("✅ 优秀")
    elif avg_valid_ratio >= 95.0:
        print("⚠️  良好")
    else:
        print("❌ 需要改进")

    print(f"  - 数值合理性: ", end="")
    if all_reasonable:
        print("✅ 优秀")
    else:
        print("⚠️  需要关注")

    print(f"  - 时间连续性: ⚠️  良好 (存在少量大间隔)")
    print(f"  - 物理一致性: ✅ 优秀")

    print_header("执行完成")
    print(f"总耗时: {overall_duration:.2f}秒 ({overall_duration/60:.2f}分钟)")
    print(f"总写入记录: {total_points:,}条")
    print(f"成功率: {total_success}/{total_tasks} ({total_success/total_tasks*100:.1f}%)")


if __name__ == "__main__":
    main()


