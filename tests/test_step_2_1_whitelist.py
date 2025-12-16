"""
测试步骤2.1: 验证配置表白名单更新

验证点:
1. metric_calculation_order 已添加到白名单
2. pump_characteristic_curves 已添加到白名单
3. 白名单配置正确
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


def test_whitelist_contains_metric_calculation_order():
    """测试白名单包含 metric_calculation_order 表"""
    
    # 读取cleanup.py文件
    with open('app/services/system/cleanup.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 验证表名在白名单中
    assert 'metric_calculation_order' in content
    assert '"metric_calculation_order"' in content
    
    # 验证注释
    assert '指标计算顺序表' in content


def test_whitelist_contains_pump_characteristic_curves():
    """测试白名单包含 pump_characteristic_curves 表"""
    
    # 读取cleanup.py文件
    with open('app/services/system/cleanup.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 验证表名在白名单中
    assert 'pump_characteristic_curves' in content
    assert '"pump_characteristic_curves"' in content
    
    # 验证注释
    assert '泵特性曲线表' in content


def test_whitelist_structure():
    """测试白名单结构正确"""
    
    # 读取cleanup.py文件
    with open('app/services/system/cleanup.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 验证preserve_by_schema存在
    assert 'preserve_by_schema' in content
    
    # 验证public schema存在
    assert '"public"' in content
    
    # 验证其他关键配置表仍在白名单中
    assert '"calculation_method_registry"' in content
    assert '"calculation_parameters"' in content
    assert '"calculation_validation_config"' in content


def test_whitelist_order():
    """测试白名单中表的顺序正确"""

    # 读取cleanup.py文件
    with open('app/services/system/cleanup.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 找到白名单区域
    whitelist_lines = []
    in_whitelist = False
    for line in lines:
        if 'preserve_by_schema' in line:
            in_whitelist = True
        if in_whitelist:
            whitelist_lines.append(line)
            if '}' in line and 'preserve_by_schema' not in line:
                break

    whitelist_content = ''.join(whitelist_lines)

    # 验证表的位置（实际顺序：dim_metric_config → pump_characteristic_curves → calculation_validation_config → metric_calculation_order）
    dim_metric_pos = whitelist_content.find('dim_metric_config')
    pump_curves_pos = whitelist_content.find('pump_characteristic_curves')
    calc_validation_pos = whitelist_content.find('calculation_validation_config')
    metric_calc_order_pos = whitelist_content.find('metric_calculation_order')

    # 验证所有表都存在
    assert dim_metric_pos > 0, "dim_metric_config not found"
    assert pump_curves_pos > 0, "pump_characteristic_curves not found"
    assert calc_validation_pos > 0, "calculation_validation_config not found"
    assert metric_calc_order_pos > 0, "metric_calculation_order not found"

    # 验证顺序：维度表在前，配置表在后
    assert dim_metric_pos < pump_curves_pos < calc_validation_pos < metric_calc_order_pos


def test_whitelist_completeness():
    """测试白名单完整性（包含所有缺失指标计算相关表）"""
    
    # 读取cleanup.py文件
    with open('app/services/system/cleanup.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 缺失指标计算功能相关的所有配置表
    required_tables = [
        'calculation_method_registry',
        'calculation_parameters',
        'calculation_validation_config',
        'metric_calculation_order',
        'pump_characteristic_curves',
    ]
    
    for table in required_tables:
        assert f'"{table}"' in content, f"表 {table} 未在白名单中"


def test_no_duplicate_entries():
    """测试白名单中无重复条目"""
    
    # 读取cleanup.py文件
    with open('app/services/system/cleanup.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取所有表名
    import re
    table_pattern = r'"([a-z_]+)"'
    matches = re.findall(table_pattern, content)
    
    # 过滤出public schema中的表名（在preserve_by_schema区域）
    preserve_start = content.find('preserve_by_schema')
    preserve_end = content.find('}', preserve_start + 100)
    preserve_section = content[preserve_start:preserve_end]
    
    table_names = re.findall(table_pattern, preserve_section)
    
    # 检查是否有重复
    seen = set()
    duplicates = []
    for name in table_names:
        if name in seen and name != 'public':  # 排除schema名称
            duplicates.append(name)
        seen.add(name)
    
    assert len(duplicates) == 0, f"发现重复的表名: {duplicates}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

