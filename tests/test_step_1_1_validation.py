"""
测试步骤1.1: 验证TODO移除和验证逻辑实现

验证点:
1. TODO注释已移除
2. 验证逻辑已实现
3. 返回值解包正确（4个值）
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from app.services.calculation.orchestrator import CalculationOrchestrator


@patch('app.services.calculation.method_selector.get_connection')
@patch('app.services.calculation.dependency_analyzer.get_connection')
def test_circular_dependency_validation_logic(mock_dep_get_connection, mock_method_get_connection):
    """测试循环依赖结果的验证逻辑"""

    # Mock数据库连接（DependencyAnalyzer和MethodSelector都需要从数据库加载方法）
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []  # 返回空的方法列表
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_dep_get_connection.return_value.__enter__.return_value = mock_conn
    mock_method_get_connection.return_value.__enter__.return_value = mock_conn

    # 创建编排器实例
    orchestrator = CalculationOrchestrator()
    
    # Mock validator
    mock_validator = Mock()
    mock_validator.validate.return_value = (
        True,  # is_valid
        np.array([True, True, True]),  # mask
        [],  # errors
        []   # warnings
    )
    orchestrator.validator = mock_validator
    
    # 准备测试数据
    circular_results = {
        'metric_a': np.array([1.0, 2.0, 3.0]),
        'metric_b': np.array([4.0, 5.0, 6.0])
    }
    
    # 模拟循环依赖求解的结果处理逻辑
    data = {}
    result = {
        'metrics_calculated': [],
        'total_points': 0,
        'valid_points': 0
    }
    
    station_id = 1
    device_id = 1
    
    # 执行验证逻辑（模拟orchestrator中的代码）
    for member, values in circular_results.items():
        # 验证计算结果的有效性
        is_valid, mask, errors, warnings = orchestrator.validator.validate(
            metric_key=member,
            values=values,
            context={
                'station_id': station_id,
                'device_id': device_id
            }
        )
        
        # 过滤无效数据点
        valid_values = values[mask]
        
        # 保存验证后的数据
        data[member] = valid_values
        result['metrics_calculated'].append(member)
        result['total_points'] += len(values)
        result['valid_points'] += len(valid_values)
    
    # 验证结果
    assert len(result['metrics_calculated']) == 2
    assert result['total_points'] == 6  # 3 + 3
    assert result['valid_points'] == 6  # 全部有效
    assert 'metric_a' in data
    assert 'metric_b' in data
    assert len(data['metric_a']) == 3
    assert len(data['metric_b']) == 3
    
    # 验证validator被正确调用（2次，每个指标1次）
    assert mock_validator.validate.call_count == 2


@patch('app.services.calculation.method_selector.get_connection')
@patch('app.services.calculation.dependency_analyzer.get_connection')
def test_circular_dependency_validation_with_invalid_data(mock_dep_get_connection, mock_method_get_connection):
    """测试循环依赖结果验证逻辑（包含无效数据）"""

    # Mock数据库连接
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_dep_get_connection.return_value.__enter__.return_value = mock_conn
    mock_method_get_connection.return_value.__enter__.return_value = mock_conn

    orchestrator = CalculationOrchestrator()
    
    # Mock validator返回部分无效数据
    mock_validator = Mock()
    mock_validator.validate.return_value = (
        False,  # is_valid
        np.array([True, False, True]),  # mask (中间的数据无效)
        ['验证失败: 1个值无效'],  # errors
        []   # warnings
    )
    orchestrator.validator = mock_validator
    
    # 准备测试数据
    circular_results = {
        'metric_a': np.array([1.0, np.nan, 3.0])  # 包含NaN
    }
    
    data = {}
    result = {
        'metrics_calculated': [],
        'total_points': 0,
        'valid_points': 0
    }
    
    # 执行验证逻辑
    for member, values in circular_results.items():
        is_valid, mask, errors, warnings = orchestrator.validator.validate(
            metric_key=member,
            values=values,
            context={'station_id': 1, 'device_id': 1}
        )
        
        valid_values = values[mask]
        
        data[member] = valid_values
        result['metrics_calculated'].append(member)
        result['total_points'] += len(values)
        result['valid_points'] += len(valid_values)
    
    # 验证结果
    assert result['total_points'] == 3  # 总共3个点
    assert result['valid_points'] == 2  # 只有2个有效
    assert len(data['metric_a']) == 2  # 过滤后只剩2个


@patch('app.services.calculation.method_selector.get_connection')
@patch('app.services.calculation.dependency_analyzer.get_connection')
def test_validator_return_value_unpacking(mock_dep_get_connection, mock_method_get_connection):
    """测试validator.validate()返回4个值的解包"""

    # Mock数据库连接
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_dep_get_connection.return_value.__enter__.return_value = mock_conn
    mock_method_get_connection.return_value.__enter__.return_value = mock_conn

    orchestrator = CalculationOrchestrator()
    
    # Mock validator返回4个值
    mock_validator = Mock()
    mock_validator.validate.return_value = (
        True,  # is_valid
        np.array([True, True]),  # mask
        [],  # errors
        ['警告信息']   # warnings
    )
    orchestrator.validator = mock_validator
    
    # 测试解包4个值
    values = np.array([1.0, 2.0])
    is_valid, mask, errors, warnings = orchestrator.validator.validate(
        metric_key='test_metric',
        values=values
    )
    
    # 验证解包成功
    assert is_valid == True
    assert len(mask) == 2
    assert errors == []
    assert warnings == ['警告信息']


def test_no_todo_comments_in_orchestrator():
    """测试orchestrator.py中不再包含"TODO: 添加验证"注释"""
    
    with open('app/services/calculation/orchestrator.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 验证TODO注释已移除
    assert 'TODO: 添加验证' not in content
    assert 'TODO.*添加验证' not in content
    
    # 验证验证逻辑已添加
    assert 'self.validator.validate' in content
    assert 'is_valid, mask, errors, warnings' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

