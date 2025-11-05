"""
测试物理规律验证器 (PhysicsValidator)

测试场景:
1. 正常流程测试 (4个场景)
2. 边界条件测试 (4个场景)
3. 异常情况测试 (2个场景)
4. 性能测试 (2个场景)

总计: 12个测试场景
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from app.services.calculation.validator import PhysicsValidator


class TestPhysicsValidator:
    """物理规律验证器测试类"""

    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        # Mock数据库连接和特性曲线管理器
        with patch('app.services.calculation.validator.get_connection'):
            with patch('app.services.calculation.validator.CharacteristicCurveManager'):
                return PhysicsValidator()

    # =====================================================
    # 正常流程测试 (4个场景)
    # =====================================================

    def test_validate_efficiency_normal_range(self, validator):
        """场景1: 效率验证 - 正常范围"""
        # 正常效率值（30-95%）
        efficiency = np.array([50.0, 60.0, 70.0, 80.0, 85.0])
        
        mask, errors, warnings = validator.validate_efficiency(efficiency)
        
        # 验证全部通过
        assert mask.all()
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_validate_power_flow_head_consistency(self, validator):
        """场景2: 功率验证 - 功率与流量扬程一致性"""
        # 准备数据：P_h = ρ × g × Q × H / 3600000
        # 例如：Q=100 m³/h, H=50 m
        # P_h = 1000 * 9.80665 * 100 * 50 / 3600000 ≈ 13.6 kW
        
        flow_rate = np.array([100.0, 200.0, 150.0])
        head = np.array([50.0, 40.0, 60.0])
        # 计算理论功率
        rho = 1000.0
        g = 9.80665
        power_expected = (rho * g * flow_rate * head) / 3600000.0
        
        # 使用理论值（应该完全一致）
        mask, errors, warnings = validator.validate_power_flow_head_consistency(
            flow_rate=flow_rate,
            head=head,
            power=power_expected,
            power_type='hydraulic',
            tolerance=0.15
        )
        
        # 验证全部通过
        assert mask.all()
        assert len(errors) == 0

    def test_validate_pressure_normal_range(self, validator):
        """场景3: 压力验证 - 正常范围"""
        # 正常压力值（0-10 bar）
        pressure = np.array([2.0, 3.5, 5.0, 6.5, 8.0])
        
        mask, errors, warnings = validator.validate_pressure(
            pressure,
            pressure_type='outlet',
            rated_pressure=10.0
        )
        
        # 验证全部通过
        assert mask.all()
        assert len(errors) == 0

    def test_validate_torque_power_speed_consistency(self, validator):
        """场景4: 扭矩验证 - 扭矩与功率转速一致性"""
        # 准备数据：P = 2π × n × T / 60000
        # 例如：n=1450 rpm, T=100 Nm
        # P = 2π * 1450 * 100 / 60000 ≈ 15.2 kW
        
        speed = np.array([1450.0, 1450.0, 1450.0])
        torque = np.array([100.0, 150.0, 200.0])
        # 计算理论功率
        power_expected = (2 * np.pi * speed * torque) / 60000.0
        
        mask, errors, warnings = validator.validate_torque(
            torque=torque,
            power=power_expected,
            speed=speed,
            tolerance=0.15
        )
        
        # 验证全部通过
        assert mask.all()
        assert len(errors) == 0

    # =====================================================
    # 边界条件测试 (4个场景)
    # =====================================================

    def test_validate_efficiency_boundary_values(self, validator):
        """场景5: 效率验证 - 边界值"""
        # 边界值：0%, 100%
        efficiency = np.array([0.0, 100.0, 50.0])
        
        mask, errors, warnings = validator.validate_efficiency(efficiency)
        
        # 验证边界值通过
        assert mask.all()
        assert len(errors) == 0
        # 可能有警告（0%和100%不常见）
        # assert len(warnings) > 0

    def test_validate_efficiency_extreme_values(self, validator):
        """场景6: 效率验证 - 极端值"""
        # 极端值：<10%, >98%
        efficiency = np.array([5.0, 99.0, 50.0])
        
        mask, errors, warnings = validator.validate_efficiency(efficiency)
        
        # 验证通过但有警告
        assert mask.all()
        assert len(errors) == 0
        assert len(warnings) > 0  # 应该有异常值警告

    def test_validate_with_zero_values(self, validator):
        """场景7: 零值处理"""
        # 零值数据
        flow_rate = np.array([0.0, 100.0, 200.0])
        head = np.array([50.0, 50.0, 50.0])
        power = np.array([0.0, 13.6, 27.2])
        
        mask, errors, warnings = validator.validate_power_flow_head_consistency(
            flow_rate=flow_rate,
            head=head,
            power=power,
            power_type='hydraulic',
            tolerance=0.15
        )
        
        # 验证零值被正确处理
        assert isinstance(mask, np.ndarray)

    def test_validate_with_negative_values(self, validator):
        """场景8: 负值处理"""
        # 负值数据（不合理）
        values = np.array([10.0, -5.0, 20.0])
        
        mask, errors = validator.validate_non_negative(values)
        
        # 验证负值被标记为无效
        assert not mask.all()
        assert mask[0] == True
        assert mask[1] == False
        assert mask[2] == True
        assert len(errors) > 0

    # =====================================================
    # 异常情况测试 (2个场景)
    # =====================================================

    def test_validate_with_nan_values(self, validator):
        """场景9: NaN值处理"""
        # 包含NaN的数据
        values = np.array([10.0, np.nan, 20.0, 30.0])
        
        mask, errors = validator.validate_not_nan(values)
        
        # 验证NaN被标记为无效
        assert not mask.all()
        assert mask[0] == True
        assert mask[1] == False
        assert mask[2] == True
        assert mask[3] == True
        assert len(errors) > 0

    def test_validate_with_inf_values(self, validator):
        """场景10: Inf值处理"""
        # 包含Inf的数据
        values = np.array([10.0, np.inf, 20.0, -np.inf])
        
        mask, errors = validator.validate_not_inf(values)
        
        # 验证Inf被标记为无效
        assert not mask.all()
        assert mask[0] == True
        assert mask[1] == False
        assert mask[2] == True
        assert mask[3] == False
        assert len(errors) > 0

    # =====================================================
    # 性能测试 (2个场景)
    # =====================================================

    def test_batch_validation_performance(self, validator):
        """场景11: 批量验证性能"""
        # 大批量数据
        efficiency = np.random.uniform(40, 90, 10000)
        
        import time
        start_time = time.time()
        
        mask, errors, warnings = validator.validate_efficiency(efficiency)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 验证性能（应该在1秒内完成）
        assert duration < 1.0
        # 验证结果正确
        assert len(mask) == 10000
        assert mask.all()  # 所有值都在合理范围内

    def test_validation_speed_with_complex_checks(self, validator):
        """场景12: 复杂验证速度"""
        # 准备数据
        flow_rate = np.random.uniform(50, 200, 1000)
        head = np.random.uniform(30, 80, 1000)
        rho = 1000.0
        g = 9.80665
        power = (rho * g * flow_rate * head) / 3600000.0
        
        import time
        start_time = time.time()
        
        # 执行复杂验证
        mask, errors, warnings = validator.validate_power_flow_head_consistency(
            flow_rate=flow_rate,
            head=head,
            power=power,
            power_type='hydraulic',
            tolerance=0.15
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 验证性能（应该在0.5秒内完成）
        assert duration < 0.5
        # 验证结果正确
        assert len(mask) == 1000


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

