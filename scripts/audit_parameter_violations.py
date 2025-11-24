"""
参数管理规范审查脚本

目标：
1. 扫描所有9个指标的代码，查找硬编码默认值
2. 生成详细的违规清单
3. 检查数据库中的参数配置情况
"""

import sys
import os
import re
from pathlib import Path

# 设置控制台编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# 需要审查的指标列表
METRICS = [
    'pump_flow_rate',
    'pump_inlet_pressure',
    'pump_head',
    'pump_efficiency',
    'pump_speed',
    'pump_torque',
    'pump_hydraulic_power',
    'pump_shaft_power',
    'main_pipeline_inlet_pressure'
]

# 需要审查的文件列表
FILES_TO_AUDIT = [
    'pipeline.py',
    'data_filter.py',
    'validator.py',
    'calculator.py',
    'methods/method_a.py',
    'methods/method_b.py',
    'methods/method_c.py'
]


def find_violations_in_file(file_path: Path) -> list:
    """
    在单个文件中查找违规代码
    
    违规模式：
    1. params.get('xxx', default_value) - 带默认值的参数获取
    2. 硬编码的数值常量（如 rho=1000.0, g=9.81）
    """
    violations = []
    
    if not file_path.exists():
        return violations
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line_num, line in enumerate(lines, start=1):
        # 模式1: params.get('xxx', default_value)
        # 匹配 .get('xxx', yyy) 或 .get("xxx", yyy)
        pattern1 = r"\.get\(['\"]([^'\"]+)['\"],\s*([^)]+)\)"
        matches = re.finditer(pattern1, line)
        
        for match in matches:
            param_name = match.group(1)
            default_value = match.group(2)
            
            violations.append({
                'line_num': line_num,
                'line_content': line.strip(),
                'violation_type': 'params.get_with_default',
                'param_name': param_name,
                'default_value': default_value,
                'severity': 'HIGH'
            })
        
        # 模式2: 硬编码的物理常量（在赋值语句中）
        # 例如: rho = 1000.0, g = 9.81
        pattern2 = r"(rho|g|eta_motor|eta_vfd|max_power|min_level|max_level)\s*=\s*(\d+\.?\d*)"
        matches = re.finditer(pattern2, line)
        
        for match in matches:
            var_name = match.group(1)
            value = match.group(2)
            
            # 排除从params获取的情况
            if 'params.get' not in line and 'self.params' not in line:
                violations.append({
                    'line_num': line_num,
                    'line_content': line.strip(),
                    'violation_type': 'hardcoded_constant',
                    'param_name': var_name,
                    'default_value': value,
                    'severity': 'MEDIUM'
                })
    
    return violations


def audit_all_metrics():
    """审查所有指标"""
    print("="*100)
    print("参数管理规范审查")
    print("="*100)
    
    all_violations = {}
    total_violations = 0
    
    for metric in METRICS:
        print(f"\n{'='*100}")
        print(f"审查指标: {metric}")
        print(f"{'='*100}")
        
        metric_violations = []
        metric_path = project_root / 'app' / 'services' / 'calculation' / 'metrics' / metric
        
        for file_name in FILES_TO_AUDIT:
            file_path = metric_path / file_name
            
            if not file_path.exists():
                continue
            
            violations = find_violations_in_file(file_path)
            
            if violations:
                print(f"\n文件: {file_name}")
                print("-"*100)
                
                for v in violations:
                    print(f"  行 {v['line_num']}: [{v['severity']}] {v['violation_type']}")
                    print(f"    参数: {v['param_name']} = {v['default_value']}")
                    print(f"    代码: {v['line_content']}")
                    print()
                    
                    metric_violations.append({
                        'file': file_name,
                        **v
                    })
        
        if metric_violations:
            all_violations[metric] = metric_violations
            total_violations += len(metric_violations)
            print(f"\n⚠️ 发现 {len(metric_violations)} 个违规")
        else:
            print(f"\n✅ 未发现违规")
    
    # 生成汇总报告
    print(f"\n\n{'='*100}")
    print("审查汇总")
    print(f"{'='*100}")
    print(f"审查指标数: {len(METRICS)}")
    print(f"发现违规指标数: {len(all_violations)}")
    print(f"总违规数: {total_violations}")
    
    # 按严重程度统计
    high_count = sum(1 for metric_vios in all_violations.values() 
                     for v in metric_vios if v['severity'] == 'HIGH')
    medium_count = sum(1 for metric_vios in all_violations.values() 
                       for v in metric_vios if v['severity'] == 'MEDIUM')
    
    print(f"\n严重程度分布:")
    print(f"  HIGH (带默认值的params.get): {high_count}")
    print(f"  MEDIUM (硬编码常量): {medium_count}")
    
    return all_violations


if __name__ == '__main__':
    violations = audit_all_metrics()
    
    # 保存详细报告
    report_path = project_root / '缺失指标计算改造' / '13-参数管理违规清单.md'
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 参数管理规范违规清单\n\n")
        f.write(f"**生成时间**: {Path(__file__).stat().st_mtime}\n\n")
        f.write("---\n\n")
        
        for metric, metric_violations in violations.items():
            f.write(f"## {metric}\n\n")
            
            for v in metric_violations:
                f.write(f"### 违规 #{metric_violations.index(v)+1}\n\n")
                f.write(f"- **文件**: `{v['file']}`\n")
                f.write(f"- **行号**: {v['line_num']}\n")
                f.write(f"- **严重程度**: {v['severity']}\n")
                f.write(f"- **违规类型**: {v['violation_type']}\n")
                f.write(f"- **参数名称**: `{v['param_name']}`\n")
                f.write(f"- **默认值**: `{v['default_value']}`\n")
                f.write(f"- **违规代码**:\n")
                f.write(f"  ```python\n")
                f.write(f"  {v['line_content']}\n")
                f.write(f"  ```\n\n")
            
            f.write("---\n\n")
    
    print(f"\n✅ 详细报告已保存到: {report_path}")

