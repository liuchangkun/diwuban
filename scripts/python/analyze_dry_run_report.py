#!/usr/bin/env python3
"""
分析 dry-run 测试报告
生成详细的测试结果分析
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any

def load_report(report_path: str) -> Dict:
    """加载报告文件"""
    with open(report_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_report(report: Dict) -> Dict[str, Any]:
    """分析报告数据"""
    
    # 基本统计
    summary = report['summary']
    results = report['results']
    
    # 设备级统计
    device_stats = []
    total_calculated_points = 0
    total_valid_points = 0
    total_requested_points = 0
    
    # 方法使用统计
    method_usage = defaultdict(int)
    method_success = defaultdict(int)
    method_total_points = defaultdict(int)
    method_valid_points = defaultdict(int)
    
    # 指标级统计
    metric_stats = defaultdict(lambda: {
        'success_devices': 0,
        'failed_devices': 0,
        'total_points': 0,
        'valid_points': 0,
        'methods_used': defaultdict(int)
    })
    
    # 失败原因统计
    failure_reasons = defaultdict(list)
    
    for result in results:
        device_id = result['device_id']
        success = result['success']
        
        if success and 'result' in result:
            res = result['result']
            
            # 设备统计
            device_stat = {
                'device_id': device_id,
                'success': res['success'],
                'metrics_calculated': res['metrics_calculated'],
                'metrics_failed': res['metrics_failed'],
                'total_points': res['total_points'],
                'valid_points': res['valid_points'],
                'throughput': res.get('performance_stats', {}).get('throughput', 0)
            }
            device_stats.append(device_stat)
            
            total_calculated_points += res['total_points']
            total_valid_points += res['valid_points']
            
            # 分析每个指标的详细统计
            if 'stats' in res:
                for key, stat in res['stats'].items():
                    # 解析key: |station_id|device_id|metric_key|start|end
                    parts = key.split('|')
                    if len(parts) >= 3:
                        metric_key = parts[3]
                        method_id = stat.get('method_id', 'unknown')
                        
                        # 方法使用统计
                        method_usage[method_id] += 1
                        if stat.get('finished', False):
                            method_success[method_id] += 1
                        method_total_points[method_id] += stat.get('total_points', 0)
                        method_valid_points[method_id] += stat.get('valid_points', 0)
                        
                        # 指标统计
                        metric_stats[metric_key]['success_devices'] += 1
                        metric_stats[metric_key]['total_points'] += stat.get('total_points', 0)
                        metric_stats[metric_key]['valid_points'] += stat.get('valid_points', 0)
                        metric_stats[metric_key]['methods_used'][method_id] += 1
            
            # 失败的指标
            for metric in res['metrics_failed']:
                metric_stats[metric]['failed_devices'] += 1
                failure_reasons[metric].append(f"设备{device_id}: 无可用方法")
    
    # 计算总请求点数
    total_requested_points = total_calculated_points
    
    return {
        'summary': summary,
        'device_stats': device_stats,
        'metric_stats': dict(metric_stats),
        'method_usage': dict(method_usage),
        'method_success': dict(method_success),
        'method_total_points': dict(method_total_points),
        'method_valid_points': dict(method_valid_points),
        'failure_reasons': dict(failure_reasons),
        'totals': {
            'total_requested_points': total_requested_points,
            'total_calculated_points': total_calculated_points,
            'total_valid_points': total_valid_points,
            'overall_success_rate': (total_valid_points / total_calculated_points * 100) if total_calculated_points > 0 else 0
        }
    }

def print_report(analysis: Dict):
    """打印分析报告"""
    
    print("=" * 80)
    print("缺失指标计算系统 - Dry-Run 测试报告")
    print("=" * 80)
    print()
    
    # 1. 总体统计
    print("【1. 总体统计】")
    print("-" * 80)
    summary = analysis['summary']
    totals = analysis['totals']
    
    print(f"测试时间范围: {summary['dry_run']}")
    print(f"测试设备数量: {summary['devices']} 个")
    print(f"并发度: {summary['concurrency']}")
    print(f"运行状态过滤: {'启用' if summary['filter_running'] else '禁用'}")
    print(f"质量过滤: {'启用' if summary['filter_quality'] else '禁用'}")
    print(f"总耗时: {summary['duration_sec']:.2f} 秒")
    print()
    print(f"总数据点数: {totals['total_calculated_points']:,}")
    print(f"有效数据点数: {totals['total_valid_points']:,}")
    print(f"总体有效率: {totals['overall_success_rate']:.2f}%")
    print()
    
    # 2. 设备级统计
    print("【2. 设备级统计】")
    print("-" * 80)
    print(f"{'设备ID':<10} {'成功指标数':<12} {'失败指标数':<12} {'总点数':<12} {'有效点数':<12} {'有效率':<10} {'吞吐量(点/秒)':<15}")
    print("-" * 80)
    
    for stat in analysis['device_stats']:
        success_count = len(stat['metrics_calculated'])
        failed_count = len(stat['metrics_failed'])
        valid_rate = (stat['valid_points'] / stat['total_points'] * 100) if stat['total_points'] > 0 else 0
        
        print(f"{stat['device_id']:<10} {success_count:<12} {failed_count:<12} {stat['total_points']:<12,} "
              f"{stat['valid_points']:<12,} {valid_rate:<10.2f}% {stat['throughput']:<15.0f}")
    print()
    
    # 3. 指标级统计
    print("【3. 指标级统计】")
    print("-" * 80)
    print(f"{'指标名称':<35} {'成功设备':<10} {'失败设备':<10} {'总点数':<12} {'有效点数':<12} {'有效率':<10}")
    print("-" * 80)
    
    for metric_key, stat in sorted(analysis['metric_stats'].items()):
        valid_rate = (stat['valid_points'] / stat['total_points'] * 100) if stat['total_points'] > 0 else 0
        
        print(f"{metric_key:<35} {stat['success_devices']:<10} {stat['failed_devices']:<10} "
              f"{stat['total_points']:<12,} {stat['valid_points']:<12,} {valid_rate:<10.2f}%")
    print()
    
    # 4. 计算方法使用统计
    print("【4. 计算方法使用统计】")
    print("-" * 80)
    print(f"{'方法ID':<40} {'使用次数':<10} {'成功次数':<10} {'总点数':<12} {'有效点数':<12} {'有效率':<10}")
    print("-" * 80)
    
    for method_id in sorted(analysis['method_usage'].keys()):
        usage = analysis['method_usage'][method_id]
        success = analysis['method_success'].get(method_id, 0)
        total_pts = analysis['method_total_points'].get(method_id, 0)
        valid_pts = analysis['method_valid_points'].get(method_id, 0)
        valid_rate = (valid_pts / total_pts * 100) if total_pts > 0 else 0
        
        print(f"{method_id:<40} {usage:<10} {success:<10} {total_pts:<12,} {valid_pts:<12,} {valid_rate:<10.2f}%")
    print()
    
    # 5. 失败原因分析
    if analysis['failure_reasons']:
        print("【5. 失败原因分析】")
        print("-" * 80)
        for metric, reasons in sorted(analysis['failure_reasons'].items()):
            print(f"\n指标: {metric}")
            for reason in reasons:
                print(f"  - {reason}")
        print()
    
    # 6. pump_inlet_pressure 修复效果验证
    print("【6. pump_inlet_pressure 修复效果验证】")
    print("-" * 80)
    if 'pump_inlet_pressure' in analysis['metric_stats']:
        pin_stat = analysis['metric_stats']['pump_inlet_pressure']
        print(f"✅ pump_inlet_pressure 已成功注册并可计算!")
        print(f"   - 成功设备数: {pin_stat['success_devices']}")
        print(f"   - 失败设备数: {pin_stat['failed_devices']}")
        print(f"   - 总数据点: {pin_stat['total_points']:,}")
        print(f"   - 有效数据点: {pin_stat['valid_points']:,}")
        print(f"   - 有效率: {(pin_stat['valid_points'] / pin_stat['total_points'] * 100) if pin_stat['total_points'] > 0 else 0:.2f}%")
        print(f"   - 使用的方法:")
        for method, count in pin_stat['methods_used'].items():
            print(f"     * {method}: {count} 次")
    else:
        print("❌ pump_inlet_pressure 未在任何设备上成功计算")
    print()
    
    print("=" * 80)
    print("报告结束")
    print("=" * 80)

def main():
    # 查找最新的报告文件
    reports_dir = Path('reports')
    if not reports_dir.exists():
        print("错误: reports 目录不存在")
        sys.exit(1)
    
    # 查找最新的 missing_metrics_full 报告
    report_files = list(reports_dir.glob('missing_metrics_full_*.json'))
    if not report_files:
        print("错误: 未找到报告文件")
        sys.exit(1)
    
    latest_report = max(report_files, key=lambda p: p.stat().st_mtime)
    print(f"正在分析报告: {latest_report}")
    print()
    
    # 加载并分析报告
    report = load_report(latest_report)
    analysis = analyze_report(report)
    
    # 打印报告
    print_report(analysis)

if __name__ == '__main__':
    main()

