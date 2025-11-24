"""
数据质量分析脚本 - 分析所有已完成指标的计算结果

分析内容：
1. 统计每个指标的计算结果数量
2. 分析数据覆盖率（有效记录数 / 预期记录数）
3. 检查数据范围（最小值、最大值、平均值、标准差）
4. 识别异常值和缺失值
5. 对比不同设备的数据质量差异
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone
from app.adapters.db.pool import get_connection
from app.adapters.db import init_database
from app.core.config.loader_new import load_settings
import json

# 初始化数据库
settings = load_settings(Path("configs"))
init_database(settings)

def analyze_data_quality():
    """分析所有已完成指标的数据质量"""

    # 配置
    station_id = 1
    device_ids = [1, 2, 3, 4, 5, 6]
    start_time = datetime(2025, 10, 22, 8, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 10, 23, 7, 19, 37, tzinfo=timezone.utc)
    
    metrics = [
        "pump_flow_rate",
        "pump_inlet_pressure",
        "main_pipeline_inlet_pressure",
        "pump_head",
        "pump_efficiency",
        "pump_speed",
        "pump_shaft_power",
        "pump_torque",
    ]
    
    print("=" * 100)
    print("数据质量分析 - 所有已完成指标")
    print("=" * 100)
    print(f"\n📋 分析配置:")
    print(f"   - 泵站ID: {station_id}")
    print(f"   - 设备ID: {device_ids}")
    print(f"   - 时间范围: {start_time} ~ {end_time}")
    print(f"   - 指标数量: {len(metrics)}个")
    print(f"   - 指标列表: {', '.join(metrics)}")
    print()
    
    # 计算预期记录数（基于时间范围）
    time_diff = (end_time - start_time).total_seconds()
    expected_records_per_device = int(time_diff)  # 1秒1条记录
    
    results = {}
    
    with get_connection() as conn:
        with conn.cursor() as cursor:
            for metric_key in metrics:
                print(f"\n{'=' * 100}")
                print(f"📊 分析指标: {metric_key}")
                print(f"{'=' * 100}")
                
                metric_results = {
                    'metric_key': metric_key,
                    'devices': {},
                    'total_records': 0,
                    'total_expected': expected_records_per_device * len(device_ids),
                    'overall_coverage': 0.0
                }
                
                for device_id in device_ids:
                    # 获取metric_id
                    cursor.execute("""
                        SELECT id FROM dim_metric_config WHERE metric_key = %s
                    """, [metric_key])

                    metric_row = cursor.fetchone()
                    if not metric_row:
                        print(f"  ⚠️ 设备 {device_id}: 未找到metric_id，跳过")
                        continue

                    metric_id = metric_row[0]

                    # 1. 统计记录数
                    cursor.execute("""
                        SELECT COUNT(*) as total_count
                        FROM fact_measurements
                        WHERE station_id = %s
                          AND device_id = %s
                          AND metric_id = %s
                          AND ts_bucket >= %s
                          AND ts_bucket < %s
                    """, [station_id, device_id, metric_id, start_time, end_time])
                    
                    total_count = cursor.fetchone()[0]
                    
                    # 2. 统计有效记录数（value IS NOT NULL）
                    cursor.execute("""
                        SELECT COUNT(*) as valid_count
                        FROM fact_measurements
                        WHERE station_id = %s
                          AND device_id = %s
                          AND metric_id = %s
                          AND ts_bucket >= %s
                          AND ts_bucket < %s
                          AND value IS NOT NULL
                    """, [station_id, device_id, metric_id, start_time, end_time])
                    
                    valid_count = cursor.fetchone()[0]
                    
                    # 3. 统计数据范围
                    cursor.execute("""
                        SELECT
                            MIN(value) as min_value,
                            MAX(value) as max_value,
                            AVG(value) as avg_value,
                            STDDEV(value) as stddev_value
                        FROM fact_measurements
                        WHERE station_id = %s
                          AND device_id = %s
                          AND metric_id = %s
                          AND ts_bucket >= %s
                          AND ts_bucket < %s
                          AND value IS NOT NULL
                    """, [station_id, device_id, metric_id, start_time, end_time])
                    
                    stats = cursor.fetchone()
                    
                    # 4. 计算覆盖率
                    coverage = (valid_count / expected_records_per_device * 100) if expected_records_per_device > 0 else 0
                    
                    device_result = {
                        'device_id': device_id,
                        'total_records': total_count,
                        'valid_records': valid_count,
                        'invalid_records': total_count - valid_count,
                        'expected_records': expected_records_per_device,
                        'coverage_pct': round(coverage, 2),
                        'min_value': float(stats[0]) if stats[0] is not None else None,
                        'max_value': float(stats[1]) if stats[1] is not None else None,
                        'avg_value': float(stats[2]) if stats[2] is not None else None,
                        'stddev_value': float(stats[3]) if stats[3] is not None else None
                    }
                    
                    metric_results['devices'][device_id] = device_result
                    metric_results['total_records'] += total_count
                    
                    # 打印设备结果
                    print(f"\n  设备 {device_id}:")
                    print(f"    - 总记录数: {total_count:,}")
                    print(f"    - 有效记录数: {valid_count:,}")
                    print(f"    - 无效记录数: {total_count - valid_count:,}")
                    print(f"    - 预期记录数: {expected_records_per_device:,}")
                    print(f"    - 覆盖率: {coverage:.2f}%")
                    if stats[0] is not None:
                        print(f"    - 数据范围: [{stats[0]:.4f}, {stats[1]:.4f}]")
                        print(f"    - 平均值: {stats[2]:.4f}")
                        print(f"    - 标准差: {stats[3]:.4f}")
                    else:
                        print(f"    - 数据范围: 无数据")
                
                # 计算总体覆盖率
                metric_results['overall_coverage'] = round(
                    (metric_results['total_records'] / metric_results['total_expected'] * 100) 
                    if metric_results['total_expected'] > 0 else 0, 
                    2
                )
                
                results[metric_key] = metric_results
                
                print(f"\n  总体统计:")
                print(f"    - 总记录数: {metric_results['total_records']:,}")
                print(f"    - 预期记录数: {metric_results['total_expected']:,}")
                print(f"    - 总体覆盖率: {metric_results['overall_coverage']:.2f}%")
    
    # 保存结果
    output_file = Path(__file__).parent.parent / "缺失指标计算改造" / "data_quality_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 100}")
    print(f"✅ 数据质量分析完成！结果已保存到: {output_file}")
    print(f"{'=' * 100}\n")
    
    return results

if __name__ == "__main__":
    analyze_data_quality()

