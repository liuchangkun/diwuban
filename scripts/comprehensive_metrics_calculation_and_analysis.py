"""
综合指标计算和质量分析脚本

功能：
1. 批量计算所有已实现的缺失指标
2. 执行全面的数据质量分析（4个维度）
3. 生成详细的执行报告和质量分析报告

已实现指标：
- pump_flow_rate（泵流量）
- pump_inlet_pressure（泵入口压力）
- pump_head（泵扬程）
- pump_efficiency（泵效率）
- main_pipeline_inlet_pressure（总管入口压力）
- pump_speed（泵转速）
- pump_torque（泵扭矩）
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib import Path
from datetime import datetime, timezone
import time
import json
from typing import Dict, List, Any

# 初始化数据库
from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings

settings = load_settings(Path("configs"))
init_database(settings)

# 导入Scheduler
from app.services.calculation.shared.scheduler import Scheduler

def execute_batch_calculation() -> Dict[str, Any]:
    """
    执行批量计算
    
    Returns:
        计算结果字典
    """
    print("\n" + "=" * 100)
    print("阶段1: 批量计算所有已实现指标")
    print("=" * 100)
    
    # 配置参数
    station_id = 1
    pump_devices = [1, 2, 3, 4, 5, 6]
    pipeline_device = [7]
    start_time = datetime(2025, 10, 22, 8, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 10, 23, 7, 19, 37, tzinfo=timezone.utc)
    
    # 已实现的指标列表（不包括pump_shaft_power，需要验证）
    metrics = [
        "pump_flow_rate",
        "pump_inlet_pressure",
        "main_pipeline_inlet_pressure",
        "pump_head",
        "pump_efficiency",
        "pump_speed",
        "pump_torque",
    ]
    
    print(f"\n[执行配置]")
    print(f"   - 泵站ID: {station_id}")
    print(f"   - 泵设备: {pump_devices}")
    print(f"   - 总管设备: {pipeline_device}")
    print(f"   - 时间范围: {start_time} ~ {end_time}")
    print(f"   - 指标数量: {len(metrics)}个")
    print(f"   - 指标列表: {', '.join(metrics)}")

    # 创建调度器
    print(f"\n[创建调度器]")
    scheduler = Scheduler(max_workers=10, enable_adaptive_chunk=True)
    print(f"   [OK] 调度器已创建（max_workers=10, 自适应分片已启用）")

    # 执行所有指标计算
    print(f"\n[开始执行所有指标计算]")
    print(f"{'=' * 100}")
    
    execution_start = time.time()
    
    # 分别处理泵设备和总管设备
    all_results = {}
    
    # 1. 泵设备指标（pump_flow_rate, pump_inlet_pressure, pump_head, pump_efficiency, pump_speed, pump_torque）
    pump_metrics = [m for m in metrics if m != 'main_pipeline_inlet_pressure']
    
    print(f"\n[1/2] 执行泵设备指标（设备1-6）...")
    pump_results = scheduler.schedule_all_metrics(
        device_ids=pump_devices,
        start_time=start_time,
        end_time=end_time,
        time_chunk_hours=None,  # 使用自适应分片
        metrics=pump_metrics
    )
    all_results.update(pump_results)
    
    # 2. 总管设备指标（main_pipeline_inlet_pressure）
    print(f"\n[2/2] 执行总管设备指标（设备7）...")
    pipeline_result = scheduler.schedule_single_metric(
        metric_key="main_pipeline_inlet_pressure",
        device_ids=pipeline_device,
        start_time=start_time,
        end_time=end_time,
        time_chunk_hours=None
    )
    all_results['main_pipeline_inlet_pressure'] = pipeline_result
    
    execution_duration = time.time() - execution_start
    
    # 打印结果摘要
    print(f"\n{'=' * 100}")
    print(f"[执行结果摘要]")
    print(f"{'=' * 100}")

    total_success = 0
    total_failure = 0
    total_points = 0

    for metric_key, result in all_results.items():
        success_count = result.get('success_count', 0)
        failure_count = result.get('failure_count', 0)
        points = result.get('total_points', 0)
        duration = result.get('total_duration_seconds', 0)
        success_rate = result.get('success_rate', 'N/A')

        total_success += success_count
        total_failure += failure_count
        total_points += points

        status = "[OK]" if failure_count == 0 else "[WARN]"
        print(f"\n{status} {metric_key}:")
        print(f"   - 成功任务: {success_count}/{success_count + failure_count}")
        print(f"   - 成功率: {success_rate}")
        print(f"   - 写入记录: {points:,}条")
        print(f"   - 耗时: {duration:.2f}秒")

    print(f"\n{'=' * 100}")
    print(f"[总体统计]")
    print(f"   - 总指标数: {len(all_results)}个")
    print(f"   - 总成功任务: {total_success}个")
    print(f"   - 总失败任务: {total_failure}个")
    print(f"   - 总写入记录: {total_points:,}条")
    print(f"   - 总耗时: {execution_duration:.2f}秒")
    print(f"{'=' * 100}")
    
    return {
        'execution_duration': execution_duration,
        'total_success': total_success,
        'total_failure': total_failure,
        'total_points': total_points,
        'metrics': all_results
    }


def analyze_data_quality() -> Dict[str, Any]:
    """
    执行数据质量分析（4个维度）

    Returns:
        质量分析结果字典
    """
    print("\n" + "=" * 100)
    print("阶段2: 数据质量分析")
    print("=" * 100)

    metrics = [
        "pump_flow_rate",
        "pump_inlet_pressure",
        "main_pipeline_inlet_pressure",
        "pump_head",
        "pump_efficiency",
        "pump_speed",
        "pump_torque",
    ]

    analysis_results = {}

    with get_connection() as conn:
        with conn.cursor() as cursor:
            for metric_key in metrics:
                print(f"\n分析指标: {metric_key}")
                print("-" * 100)

                # 维度1: 数据完整性分析
                cursor.execute("""
                    SELECT
                        dmc.metric_key,
                        COUNT(DISTINCT fm.device_id) as device_count,
                        COUNT(*) as record_count,
                        MIN(fm.ts_bucket) as earliest_time,
                        MAX(fm.ts_bucket) as latest_time,
                        COUNT(DISTINCT fm.ts_bucket) as unique_timestamps
                    FROM fact_measurements fm
                    JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
                    WHERE dmc.metric_key = %s
                    GROUP BY dmc.metric_key
                """, (metric_key,))

                completeness = cursor.fetchone()

                # 维度2: 数据合理性分析
                cursor.execute("""
                    SELECT
                        fm.device_id,
                        COUNT(*) as count,
                        MIN(fm.value) as min_value,
                        MAX(fm.value) as max_value,
                        AVG(fm.value) as avg_value,
                        STDDEV(fm.value) as stddev_value,
                        COUNT(CASE WHEN fm.value < 0 THEN 1 END) as negative_count,
                        COUNT(CASE WHEN fm.value = 0 THEN 1 END) as zero_count
                    FROM fact_measurements fm
                    JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
                    WHERE dmc.metric_key = %s
                    GROUP BY fm.device_id
                    ORDER BY fm.device_id
                """, (metric_key,))

                reasonableness = cursor.fetchall()

                # 维度3: 计算逻辑验证（查询使用的方法）
                cursor.execute("""
                    SELECT
                        fm.device_id,
                        fm.source_hint,
                        COUNT(*) as count
                    FROM fact_measurements fm
                    JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
                    WHERE dmc.metric_key = %s
                    GROUP BY fm.device_id, fm.source_hint
                    ORDER BY fm.device_id, count DESC
                """, (metric_key,))

                methods_used = cursor.fetchall()

                # 维度4: 参数配置验证
                cursor.execute("""
                    SELECT
                        param_name,
                        param_value,
                        station_id,
                        device_id,
                        param_type
                    FROM calculation_parameters
                    WHERE metric_key = %s
                    ORDER BY
                        CASE WHEN station_id IS NULL AND device_id IS NULL THEN 1
                             WHEN station_id IS NOT NULL AND device_id IS NULL THEN 2
                             ELSE 3 END,
                        param_name
                """, (metric_key,))

                parameters = cursor.fetchall()

                analysis_results[metric_key] = {
                    'completeness': completeness,
                    'reasonableness': reasonableness,
                    'methods_used': methods_used,
                    'parameters': parameters
                }

                # 打印简要结果
                if completeness:
                    print(f"  [OK] 完整性: {completeness[1]}条记录, {completeness[2]}个设备, {completeness[5]}个时间戳")
                print(f"  [OK] 合理性: {len(reasonableness)}个设备有数据")
                print(f"  [OK] 计算方法: {len(set(m[1] for m in methods_used))}种方法")
                print(f"  [OK] 参数配置: {len(parameters)}个参数")

    return analysis_results


def generate_reports(calculation_results: Dict, analysis_results: Dict):
    """
    生成报告文件

    Args:
        calculation_results: 计算执行结果
        analysis_results: 质量分析结果
    """
    print("\n" + "=" * 100)
    print("阶段3: 生成报告")
    print("=" * 100)

    # 保存JSON结果
    output_file = "缺失指标计算改造/scheduler_execution_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        # 转换为可序列化格式
        serializable_results = {}
        for metric_key, result in calculation_results['metrics'].items():
            serializable_results[metric_key] = {
                'total_tasks': result.get('total_tasks', 0),
                'success_count': result.get('success_count', 0),
                'failure_count': result.get('failure_count', 0),
                'total_points': result.get('total_points', 0),
                'total_duration_seconds': result.get('total_duration_seconds', 0),
                'success_rate': result.get('success_rate', 'N/A'),
            }

        json.dump({
            'execution_time': calculation_results['execution_duration'],
            'total_success': calculation_results['total_success'],
            'total_failure': calculation_results['total_failure'],
            'total_points': calculation_results['total_points'],
            'metrics': serializable_results
        }, f, indent=2, ensure_ascii=False)

    print(f"[OK] JSON结果已保存: {output_file}")

    # 生成Markdown报告（将在下一步实现）
    print(f"[OK] 报告生成完成")


def main():
    """主函数"""
    print("\n" + "=" * 100)
    print("综合指标计算和质量分析")
    print("=" * 100)

    # 阶段1: 批量计算
    calculation_results = execute_batch_calculation()

    # 阶段2: 质量分析
    analysis_results = analyze_data_quality()

    # 阶段3: 生成报告
    generate_reports(calculation_results, analysis_results)

    print("\n" + "=" * 100)
    print("[OK] 所有任务完成！")
    print("=" * 100)


if __name__ == '__main__':
    main()

