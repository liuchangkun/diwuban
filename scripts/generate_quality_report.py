"""
生成数据质量评价报告

基于数据质量分析结果，生成详细的评价报告，包括：
1. 计算成功率评估
2. 数据完整性评估
3. 数据合理性评估（物理约束范围）
4. 潜在问题识别
5. 改进建议
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime

def generate_quality_report():
    """生成数据质量评价报告"""
    
    # 读取数据质量分析结果
    analysis_file = Path(__file__).parent.parent / "缺失指标计算改造" / "data_quality_analysis.json"
    with open(analysis_file, 'r', encoding='utf-8') as f:
        analysis_data = json.load(f)
    
    # 读取调度器执行结果
    scheduler_file = Path(__file__).parent.parent / "缺失指标计算改造" / "scheduler_execution_results.json"
    with open(scheduler_file, 'r', encoding='utf-8') as f:
        scheduler_data = json.load(f)
    
    # 生成报告
    report_lines = []
    report_lines.append("=" * 100)
    report_lines.append("数据质量评价报告")
    report_lines.append("=" * 100)
    report_lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"分析指标数量: {len(analysis_data)}个")
    report_lines.append(f"设备数量: 6台（设备1-6）")
    report_lines.append(f"时间范围: 2025-10-22 08:00:00 UTC ~ 2025-10-23 07:19:37 UTC（约23小时）")
    
    # 1. 计算成功率评估
    report_lines.append("\n" + "=" * 100)
    report_lines.append("1. 计算成功率评估")
    report_lines.append("=" * 100)

    for metric_key, metric_data in scheduler_data['metrics'].items():
        success_rate_str = metric_data['success_rate']
        success_rate = float(success_rate_str.rstrip('%'))
        total_tasks = metric_data['total_tasks']
        success_tasks = metric_data['success_count']

        status = "✅ 优秀" if success_rate >= 95 else "⚠️ 需改进" if success_rate >= 80 else "❌ 严重问题"

        report_lines.append(f"\n{metric_key}:")
        report_lines.append(f"  - 成功率: {success_rate:.1f}% ({success_tasks}/{total_tasks}任务)")
        report_lines.append(f"  - 评价: {status}")
        report_lines.append(f"  - 写入记录: {metric_data['total_points']:,}条")
        report_lines.append(f"  - 耗时: {metric_data['total_duration_seconds']:.2f}秒")
    
    # 2. 数据完整性评估
    report_lines.append("\n" + "=" * 100)
    report_lines.append("2. 数据完整性评估")
    report_lines.append("=" * 100)
    
    for metric_key, metric_data in analysis_data.items():
        coverage = metric_data['overall_coverage']
        total_records = metric_data['total_records']
        expected_records = metric_data['total_expected']
        
        status = "✅ 优秀" if coverage >= 95 else "⚠️ 良好" if coverage >= 70 else "❌ 较差"
        
        report_lines.append(f"\n{metric_key}:")
        report_lines.append(f"  - 总体覆盖率: {coverage:.2f}%")
        report_lines.append(f"  - 实际记录: {total_records:,}条")
        report_lines.append(f"  - 预期记录: {expected_records:,}条")
        report_lines.append(f"  - 缺失记录: {expected_records - total_records:,}条")
        report_lines.append(f"  - 评价: {status}")
        
        # 设备级覆盖率差异
        device_coverages = [dev['coverage_pct'] for dev in metric_data['devices'].values()]
        min_coverage = min(device_coverages)
        max_coverage = max(device_coverages)
        
        if max_coverage - min_coverage > 20:
            report_lines.append(f"  - ⚠️ 设备间覆盖率差异较大: {min_coverage:.2f}% ~ {max_coverage:.2f}%")
    
    # 3. 数据合理性评估
    report_lines.append("\n" + "=" * 100)
    report_lines.append("3. 数据合理性评估（物理约束范围）")
    report_lines.append("=" * 100)
    
    # 定义物理约束
    physical_constraints = {
        'pump_flow_rate': {'min': 0, 'max': 5000, 'unit': 'm³/h'},
        'pump_inlet_pressure': {'min': 0.05, 'max': 0.5, 'unit': 'MPa'},
        'pump_head': {'min': 0, 'max': 100, 'unit': 'm'},
        'pump_efficiency': {'min': 0.0, 'max': 1.0, 'unit': ''},
        'pump_speed': {'min': 0, 'max': 3000, 'unit': 'rpm'},
        'pump_shaft_power': {'min': 0, 'max': 500, 'unit': 'kW'},
        'pump_torque': {'min': 0, 'max': 10000, 'unit': 'N·m'}
    }
    
    for metric_key, metric_data in analysis_data.items():
        if metric_key not in physical_constraints:
            continue
        
        constraint = physical_constraints[metric_key]
        report_lines.append(f"\n{metric_key}:")
        report_lines.append(f"  - 物理约束: [{constraint['min']}, {constraint['max']}] {constraint['unit']}")
        
        all_in_range = True
        for device_id, device_data in metric_data['devices'].items():
            if device_data['min_value'] is None:
                continue
            
            min_val = device_data['min_value']
            max_val = device_data['max_value']
            avg_val = device_data['avg_value']
            
            if min_val < constraint['min'] or max_val > constraint['max']:
                all_in_range = False
                report_lines.append(f"  - ⚠️ 设备{device_id}: 数据超出范围 [{min_val:.4f}, {max_val:.4f}]")
        
        if all_in_range:
            report_lines.append(f"  - ✅ 所有设备数据均在合理范围内")
    
    # 4. 潜在问题识别
    report_lines.append("\n" + "=" * 100)
    report_lines.append("4. 潜在问题识别")
    report_lines.append("=" * 100)
    
    problems = []
    
    # 检查pump_inlet_pressure覆盖率低的问题
    if 'pump_inlet_pressure' in analysis_data:
        coverage = analysis_data['pump_inlet_pressure']['overall_coverage']
        if coverage < 50:
            problems.append(f"❌ pump_inlet_pressure覆盖率过低({coverage:.2f}%)，可能是pump_active_power数据缺失导致")
    
    # 检查pump_shaft_power覆盖率低的问题
    if 'pump_shaft_power' in analysis_data:
        coverage = analysis_data['pump_shaft_power']['overall_coverage']
        if coverage < 50:
            problems.append(f"❌ pump_shaft_power覆盖率过低({coverage:.2f}%)，可能是pump_active_power数据缺失导致")
    
    # 检查main_pipeline_inlet_pressure无数据的问题
    if 'main_pipeline_inlet_pressure' in analysis_data:
        total_records = analysis_data['main_pipeline_inlet_pressure']['total_records']
        if total_records == 0:
            problems.append(f"❌ main_pipeline_inlet_pressure无数据，设备类型不匹配（需要main_pipeline设备，但执行了pump设备）")
    
    # 检查pump_efficiency依赖问题
    if 'pump_efficiency' in analysis_data:
        coverage = analysis_data['pump_efficiency']['overall_coverage']
        if coverage < 50:
            problems.append(f"⚠️ pump_efficiency覆盖率较低({coverage:.2f}%)，依赖pump_flow_rate和pump_head数据")
    
    if problems:
        for problem in problems:
            report_lines.append(f"\n{problem}")
    else:
        report_lines.append("\n✅ 未发现明显问题")
    
    # 5. 改进建议
    report_lines.append("\n" + "=" * 100)
    report_lines.append("5. 改进建议")
    report_lines.append("=" * 100)
    
    suggestions = []
    
    # 针对pump_inlet_pressure和pump_shaft_power的建议
    if 'pump_inlet_pressure' in analysis_data and analysis_data['pump_inlet_pressure']['overall_coverage'] < 50:
        suggestions.append("1. pump_inlet_pressure覆盖率低：检查pump_active_power原始数据的完整性，确保所有设备都有功率数据")
    
    if 'pump_shaft_power' in analysis_data and analysis_data['pump_shaft_power']['overall_coverage'] < 50:
        suggestions.append("2. pump_shaft_power覆盖率低：检查pump_active_power原始数据的完整性，确保所有设备都有功率数据")
    
    # 针对main_pipeline_inlet_pressure的建议
    if 'main_pipeline_inlet_pressure' in analysis_data and analysis_data['main_pipeline_inlet_pressure']['total_records'] == 0:
        suggestions.append("3. main_pipeline_inlet_pressure无数据：调度器应该只对main_pipeline设备执行此指标，不应对pump设备执行")
    
    # 性能优化建议
    if 'pump_flow_rate' in scheduler_data['metrics'] and scheduler_data['metrics']['pump_flow_rate']['total_duration_seconds'] > 300:
        suggestions.append("4. pump_flow_rate计算耗时较长：考虑优化计算逻辑或增加并行度")
    
    # 数据质量监控建议
    suggestions.append("5. 建立数据质量监控：定期检查各指标的覆盖率和数据范围，及时发现异常")
    suggestions.append("6. 完善告警机制：当覆盖率低于阈值或数据超出合理范围时，及时告警")
    
    for suggestion in suggestions:
        report_lines.append(f"\n{suggestion}")
    
    report_lines.append("\n" + "=" * 100)
    report_lines.append("报告结束")
    report_lines.append("=" * 100)
    
    # 保存报告
    report_content = "\n".join(report_lines)
    output_file = Path(__file__).parent.parent / "缺失指标计算改造" / "data_quality_report.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(report_content)
    print(f"\n✅ 质量评价报告已保存到: {output_file}")

if __name__ == "__main__":
    generate_quality_report()

