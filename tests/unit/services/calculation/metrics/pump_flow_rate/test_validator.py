"""
Validator 单元测试

测试范围：
- NaN/Inf 验证
- 非负验证
- 范围验证
- 物理约束验证
- 质量代码计算
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from app.services.calculation.metrics.pump_flow_rate.validator import Validator


class TestValidator:
    """Validator 单元测试"""

    @pytest.fixture
    def validator(self, test_config):
        """创建 Validator 实例"""
        return Validator(params=test_config)

    def test_validate_all_valid(self, validator):
        """测试：所有数据有效"""
        # 准备数据（所有值有效）
        results = pd.DataFrame({
            'pump_flow_rate': [50.0, 60.0, 70.0, 80.0, 90.0]
        })
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [100.0, 120.0, 140.0, 160.0, 180.0]
        })

        # 执行验证
        validation_result = validator.validate(results, data)

        # 断言
        assert validation_result['valid_count'] == 5
        assert validation_result['invalid_count'] == 0
        assert validation_result['valid_ratio'] == 1.0
        assert validation_result['quality_code'] == 0  # 优秀

    def test_validate_nan_values(self, validator):
        """测试：NaN 值验证"""
        # 准备数据（包含 NaN）
        results = pd.DataFrame({
            'pump_flow_rate': [50.0, np.nan, 70.0, np.nan, 90.0]
        })

        # 执行验证
        validation_result = validator.validate(results)

        # 断言
        assert validation_result['valid_count'] == 3
        assert validation_result['invalid_count'] == 2
        assert validation_result['valid_ratio'] == 0.6
        assert validation_result['quality_code'] == 2  # 可用

    def test_validate_inf_values(self, validator):
        """测试：Inf 值验证"""
        # 准备数据（包含 Inf）
        results = pd.DataFrame({
            'pump_flow_rate': [50.0, np.inf, 70.0, -np.inf, 90.0]
        })

        # 执行验证
        validation_result = validator.validate(results)

        # 断言
        assert validation_result['valid_count'] == 3
        assert validation_result['invalid_count'] == 2

    def test_validate_negative_values(self, validator):
        """测试：负值验证"""
        # 准备数据（包含负值）
        results = pd.DataFrame({
            'pump_flow_rate': [50.0, -10.0, 70.0, -20.0, 90.0]
        })

        # 执行验证
        validation_result = validator.validate(results)

        # 断言
        assert validation_result['valid_count'] == 3
        assert validation_result['invalid_count'] == 2

    def test_validate_range(self, validator):
        """测试：范围验证"""
        # 准备数据（包含超出范围的值）
        results = pd.DataFrame({
            'pump_flow_rate': [50.0, 600.0, 70.0, 700.0, 90.0]  # 600, 700 > max_flow(500)
        })

        # 执行验证
        validation_result = validator.validate(results)

        # 断言
        assert validation_result['valid_count'] == 3
        assert validation_result['invalid_count'] == 2

    def test_validate_physical_constraint(self, validator):
        """测试：物理约束验证（单泵流量不应超过总管流量）"""
        # 准备数据（单泵流量超过总管流量）
        results = pd.DataFrame({
            'pump_flow_rate': [50.0, 150.0, 70.0, 200.0, 90.0]  # 150, 200 > main_flow * 1.1
        })
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [100.0, 100.0, 100.0, 100.0, 100.0]  # max allowed = 110
        })

        # 执行验证
        validation_result = validator.validate(results, data)

        # 断言
        assert validation_result['valid_count'] == 3
        assert validation_result['invalid_count'] == 2

    def test_quality_code_excellent(self, validator):
        """测试：质量代码 - 优秀（≥95%）"""
        # 准备数据（96%有效）
        results = pd.DataFrame({
            'pump_flow_rate': [50.0] * 96 + [np.nan] * 4
        })

        # 执行验证
        validation_result = validator.validate(results)

        # 断言
        assert validation_result['quality_code'] == 0  # 优秀

    def test_quality_code_good(self, validator):
        """测试：质量代码 - 良好（≥80%）"""
        # 准备数据（85%有效）
        results = pd.DataFrame({
            'pump_flow_rate': [50.0] * 85 + [np.nan] * 15
        })

        # 执行验证
        validation_result = validator.validate(results)

        # 断言
        assert validation_result['quality_code'] == 1  # 良好

    def test_quality_code_acceptable(self, validator):
        """测试：质量代码 - 可用（≥60%）"""
        # 准备数据（70%有效）
        results = pd.DataFrame({
            'pump_flow_rate': [50.0] * 70 + [np.nan] * 30
        })

        # 执行验证
        validation_result = validator.validate(results)

        # 断言
        assert validation_result['quality_code'] == 2  # 可用

    def test_quality_code_poor(self, validator):
        """测试：质量代码 - 差（<60%）"""
        # 准备数据（50%有效）
        results = pd.DataFrame({
            'pump_flow_rate': [50.0] * 50 + [np.nan] * 50
        })

        # 执行验证
        validation_result = validator.validate(results)

        # 断言
        assert validation_result['quality_code'] == 3  # 差

    def test_validate_combined(self, validator):
        """测试：组合验证（多种无效值）"""
        # 准备数据（包含多种无效值）
        results = pd.DataFrame({
            'pump_flow_rate': [
                50.0,      # 有效
                np.nan,    # NaN
                -10.0,     # 负值
                600.0,     # 超出范围
                np.inf,    # Inf
                70.0,      # 有效
                80.0,      # 有效
                -20.0,     # 负值
                700.0,     # 超出范围
                90.0       # 有效
            ]
        })

        # 执行验证
        validation_result = validator.validate(results)

        # 断言
        assert validation_result['valid_count'] == 4
        assert validation_result['invalid_count'] == 6
        assert validation_result['valid_ratio'] == 0.4

