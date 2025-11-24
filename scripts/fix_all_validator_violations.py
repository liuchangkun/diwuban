"""
批量修复所有 Validator 类中的硬编码默认值
"""

import re
from pathlib import Path

# 需要修复的指标列表（pump_shaft_power 已修复）
METRICS = [
    'pump_flow_rate',
    'pump_inlet_pressure', 
    'pump_head',
    'pump_efficiency',
    'pump_speed',
    'pump_torque',
    'pump_hydraulic_power',
    'main_pipeline_inlet_pressure'
]

# 需要修复的参数映射（指标 -> 参数列表）
VALIDATOR_PARAMS = {
    'pump_flow_rate': [],  # 已正确实现
    'pump_inlet_pressure': [],  # 已正确实现
    'pump_head': [
        ('min_pump_outlet_pressure', '0.0'),
        ('max_pump_outlet_pressure', '2.0'),
        ('min_pump_head', '0.0'),
        ('max_pump_head', '200.0')
    ],
    'pump_efficiency': [
        ('eta_min', '0.30'),
        ('eta_max', '0.95')
    ],
    'pump_speed': [],  # 已正确实现
    'pump_torque': [
        ('max_torque', '10000.0')
    ],
    'pump_hydraulic_power': [
        ('min_power', '0.0'),
        ('max_power', '500.0')
    ],
    'main_pipeline_inlet_pressure': [
        ('P_in_min', '0.0'),
        ('P_in_max', '2.0')
    ]
}


def fix_validator_file(metric: str):
    """修复单个指标的 validator.py 文件"""
    
    validator_path = Path(f'app/services/calculation/metrics/{metric}/validator.py')
    
    if not validator_path.exists():
        print(f"⚠️  {metric}: validator.py 不存在")
        return False
    
    params_to_fix = VALIDATOR_PARAMS.get(metric, [])
    if not params_to_fix:
        print(f"✅ {metric}: 无需修复（已正确实现或无违规）")
        return True
    
    # 读取文件
    with open(validator_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # 查找需要修复的行
    modified = False
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        fixed_line = line
        
        # 检查是否包含需要修复的参数
        for param_name, default_value in params_to_fix:
            # 匹配模式: params.get('param_name') or default_value
            pattern1 = rf"params\.get\(['\"]({param_name})['\"].*?\)\s+or\s+{re.escape(default_value)}"
            # 匹配模式: params.get('param_name', default_value)
            pattern2 = rf"params\.get\(['\"]({param_name})['\"],\s*{re.escape(default_value)}\)"
            
            if re.search(pattern1, line) or re.search(pattern2, line):
                print(f"  🔧 修复参数: {param_name}")
                # 替换为不带默认值的版本
                fixed_line = re.sub(pattern1, rf"params.get('{param_name}')", fixed_line)
                fixed_line = re.sub(pattern2, rf"params.get('{param_name}')", fixed_line)
                modified = True
        
        new_lines.append(fixed_line)
        i += 1
    
    if modified:
        # 写回文件
        with open(validator_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        print(f"✅ {metric}: validator.py 已修复")
        return True
    else:
        print(f"ℹ️  {metric}: validator.py 未发现需要修复的代码")
        return True


def main():
    """主函数"""
    print("="*100)
    print("批量修复 Validator 类的硬编码默认值")
    print("="*100)
    
    success_count = 0
    total_count = len(METRICS)
    
    for metric in METRICS:
        print(f"\n处理指标: {metric}")
        if fix_validator_file(metric):
            success_count += 1
    
    print(f"\n{'='*100}")
    print(f"修复完成: {success_count}/{total_count}")
    print(f"{'='*100}")


if __name__ == '__main__':
    main()

