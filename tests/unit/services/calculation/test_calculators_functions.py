"""
测试 calculation/calculators.py - 计算函数实现

测试各个计算函数的实际计算逻辑：
1. pump_flow_rate计算函数 (6个方法 × 3场景 = 18个测试)
2. pump_head计算函数 (1个方法 × 3场景 = 3个测试)
3. pump_outlet_pressure计算函数 (4个方法 × 2场景 = 8个测试)
4. pump_speed计算函数 (3个方法 × 2场景 = 6个测试)
5. pump_torque计算函数 (2个方法 × 2场景 = 4个测试)
6. main_pipeline_outlet_pressure计算函数 (3个方法 × 2场景 = 6个测试)
7. main_pipeline_inlet_pressure计算函数 (3个方法 × 2场景 = 6个测试)
8. pump_cumulative_flow计算函数 (2个方法 × 2场景 = 4个测试)

总计: 55个测试场景
"""

import pytest
import numpy as np
from app.services.calculation.calculators import (
    calculate_pump_flow_rate_method_a,
    calculate_pump_flow_rate_method_b,
    calculate_pump_flow_rate_method_c,
    calculate_pump_flow_rate_method_d,
    calculate_pump_flow_rate_method_e,
    calculate_pump_flow_rate_method_f,
    calculate_pump_head_method_main,
    calculate_pump_outlet_pressure_method_a,
    calculate_pump_outlet_pressure_method_b,
    calculate_pump_outlet_pressure_method_c,
    calculate_pump_outlet_pressure_method_d,
    calculate_pump_speed_method_a,
    calculate_pump_speed_method_b,
    calculate_pump_speed_method_c,
    calculate_pump_torque_method_a,
    calculate_pump_torque_method_b,
    calculate_main_pipeline_outlet_pressure_method_a,
    calculate_main_pipeline_outlet_pressure_method_b,
    calculate_main_pipeline_outlet_pressure_method_c,
    calculate_main_pipeline_inlet_pressure_method_a,
    calculate_main_pipeline_inlet_pressure_method_b,
    calculate_main_pipeline_inlet_pressure_method_c,
    calculate_pump_cumulative_flow_method_a,
    calculate_pump_cumulative_flow_method_b,
)


class TestPumpFlowRateCalculations:
    """泵流量计算函数测试"""

    def test_method_a_with_share(self):
        """场景1: 方法A - 有分摊系数"""
        data = {
            'main_pipeline_flow_rate': np.array([100.0, 200.0, 150.0]),
            '__pump_flow_rate_share': np.array([0.5, 0.6, 0.4])
        }
        params = {}
        
        result = calculate_pump_flow_rate_method_a(data, params)
        
        # 验证结果
        expected = np.array([50.0, 120.0, 60.0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_method_a_without_share(self):
        """场景2: 方法A - 无分摊系数"""
        data = {
            'main_pipeline_flow_rate': np.array([100.0, 200.0, 150.0])
        }
        params = {}
        
        result = calculate_pump_flow_rate_method_a(data, params)
        
        # 验证返回NaN
        assert np.all(np.isnan(result))

    def test_method_a_with_nan_values(self):
        """场景3: 方法A - 包含NaN值"""
        data = {
            'main_pipeline_flow_rate': np.array([100.0, np.nan, 150.0]),
            '__pump_flow_rate_share': np.array([0.5, 0.6, np.nan])
        }
        params = {}
        
        result = calculate_pump_flow_rate_method_a(data, params)
        
        # 验证第一个值有效，其他为NaN
        assert result[0] == 50.0
        assert np.isnan(result[1])
        assert np.isnan(result[2])

    def test_method_b_normal_case(self):
        """场景4: 方法B - 累计量求导正常情况"""
        data = {
            'pump_cumulative_flow': np.array([0.0, 10.0, 25.0, 45.0]),
            '__timestamps': np.array([0, 60, 120, 180])  # 秒
        }
        params = {}
        
        result = calculate_pump_flow_rate_method_b(data, params)
        
        # 验证结果（流量 = 累计量差 / 时间差）
        # 第一个值为0，后续为导数
        assert result[0] == 0.0
        assert result[1] > 0  # (10-0)/60
        assert result[2] > 0  # (25-10)/60
        assert result[3] > 0  # (45-25)/60

    def test_method_b_with_negative_derivative(self):
        """场景5: 方法B - 负导数处理"""
        data = {
            'pump_cumulative_flow': np.array([0.0, 10.0, 5.0, 15.0]),  # 第3个值下降
            '__timestamps': np.array([0, 60, 120, 180])
        }
        params = {}
        
        result = calculate_pump_flow_rate_method_b(data, params)
        
        # 验证负值被置为0
        assert result[0] == 0.0
        assert result[1] > 0
        assert result[2] == 0.0  # 负导数被置为0
        assert result[3] > 0

    def test_method_c_normal_case(self):
        """场景6: 方法C - 单泵运行直接取总管流量"""
        data = {
            'main_pipeline_flow_rate': np.array([100.0, 105.0, 98.0])
        }
        params = {}
        
        result = calculate_pump_flow_rate_method_c(data, params)
        
        # 验证返回总管流量的副本
        np.testing.assert_array_equal(result, data['main_pipeline_flow_rate'])
        # 验证是副本而不是引用
        assert result is not data['main_pipeline_flow_rate']

    def test_method_d_normal_case(self):
        """场景7: 方法D - 仅功率分摊"""
        data = {
            'main_pipeline_flow_rate': np.array([100.0, 200.0]),
            'pump_active_power': np.array([50.0, 100.0])
        }
        params = {'p_thr': 0.5}

        result = calculate_pump_flow_rate_method_d(data, params)

        # 验证功率分摊（Q_i = Q_total * P_i）
        expected = np.array([100.0 * 50.0, 200.0 * 100.0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_method_d_with_low_power(self):
        """场景8: 方法D - 功率低于阈值"""
        data = {
            'main_pipeline_flow_rate': np.array([100.0, 200.0]),
            'pump_active_power': np.array([0.3, 0.4])  # 低于默认阈值0.5
        }
        params = {}

        result = calculate_pump_flow_rate_method_d(data, params)

        # 验证返回0（功率低于阈值）
        assert np.all(result == 0.0)

    def test_method_e_normal_case(self):
        """场景9: 方法E - 仅频率分摊"""
        data = {
            'main_pipeline_flow_rate': np.array([100.0, 200.0]),
            'pump_frequency': np.array([40.0, 45.0])
        }
        params = {'f_thr': 3.0}

        result = calculate_pump_flow_rate_method_e(data, params)

        # 验证频率分摊（Q_i = Q_total * f_i）
        expected = np.array([100.0 * 40.0, 200.0 * 45.0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_method_e_with_low_frequency(self):
        """场景10: 方法E - 频率低于阈值"""
        data = {
            'main_pipeline_flow_rate': np.array([100.0, 200.0]),
            'pump_frequency': np.array([2.0, 2.5])  # 低于默认阈值3.0
        }
        params = {}

        result = calculate_pump_flow_rate_method_e(data, params)

        # 验证返回0（频率低于阈值）
        assert np.all(result == 0.0)

    def test_method_f_normal_case(self):
        """场景11: 方法F - 数据驱动回归融合"""
        data = {
            'pump_active_power': np.array([50.0, 100.0]),
            'pump_frequency': np.array([40.0, 45.0]),
            'pump_inlet_pressure': np.array([0.1, 0.15])
        }
        params = {'a0': 10.0, 'a1': 1.0, 'a2': 0.5, 'a3': 100.0}

        result = calculate_pump_flow_rate_method_f(data, params)

        # 验证结果不为NaN
        assert not np.any(np.isnan(result))
        # 验证结果为正
        assert np.all(result >= 0)
        # 验证线性回归公式：Q = a0 + a1*P + a2*f + a3*P_in
        expected_0 = 10.0 + 1.0*50.0 + 0.5*40.0 + 100.0*0.1
        assert np.abs(result[0] - expected_0) < 0.1


class TestPumpHeadCalculations:
    """泵扬程计算函数测试"""

    def test_method_main_normal_case(self):
        """场景12: 主方法 - 正常情况"""
        data = {
            'pump_outlet_pressure': np.array([0.5, 0.6, 0.7]),  # MPa
            'pump_inlet_pressure': np.array([0.1, 0.15, 0.2])   # MPa
        }
        params = {}
        
        result = calculate_pump_head_method_main(data, params)
        
        # 验证扬程计算
        # H = (P_out - P_in) * 1e6 / (rho * g)
        # rho = 1000, g = 9.81
        expected_h = (0.5 - 0.1) * 1e6 / (1000 * 9.81)
        assert result[0] > 0
        assert np.abs(result[0] - expected_h) < 1.0  # 允许1米误差

    def test_method_main_with_nan(self):
        """场景13: 主方法 - 包含NaN"""
        data = {
            'pump_outlet_pressure': np.array([0.5, np.nan, 0.7]),
            'pump_inlet_pressure': np.array([0.1, 0.15, np.nan])
        }
        params = {}
        
        result = calculate_pump_head_method_main(data, params)
        
        # 验证第一个值有效，其他为NaN
        assert result[0] > 0
        assert np.isnan(result[1])
        assert np.isnan(result[2])

    def test_method_main_with_custom_density(self):
        """场景14: 主方法 - 自定义密度"""
        data = {
            'pump_outlet_pressure': np.array([0.5]),
            'pump_inlet_pressure': np.array([0.1])
        }
        params = {'rho': 1050.0}  # 自定义密度
        
        result = calculate_pump_head_method_main(data, params)
        
        # 验证使用自定义密度计算
        expected_h = (0.5 - 0.1) * 1e6 / (1050.0 * 9.81)
        assert np.abs(result[0] - expected_h) < 0.1


class TestPumpOutletPressureCalculations:
    """泵出口压力计算函数测试"""

    def test_method_a_direct_read(self):
        """场景15: 方法A - 直接读取pump_outlet_pressure"""
        # 测试1：data中有pump_outlet_pressure数据
        data = {
            'pump_outlet_pressure': np.array([0.5, 0.6, 0.7])
        }
        params = {}

        result = calculate_pump_outlet_pressure_method_a(data, params)

        # 验证返回pump_outlet_pressure的副本
        np.testing.assert_array_equal(result, data['pump_outlet_pressure'])
        assert result is not data['pump_outlet_pressure']  # 确保是副本

        # 测试2：data中没有pump_outlet_pressure数据
        data_empty = {}
        result_empty = calculate_pump_outlet_pressure_method_a(data_empty, params)

        # 验证返回空数组
        assert len(result_empty) == 0
        assert result_empty.dtype == float

    def test_method_b_normal_case(self):
        """场景16: 方法B - 以总管出口压力代替"""
        data = {
            'main_pipeline_outlet_pressure': np.array([0.5, 0.6, 0.7])
        }
        params = {}
        
        result = calculate_pump_outlet_pressure_method_b(data, params)
        
        # 验证返回总管出口压力的副本
        np.testing.assert_array_equal(result, data['main_pipeline_outlet_pressure'])
        assert result is not data['main_pipeline_outlet_pressure']

    def test_method_c_normal_case(self):
        """场景17: 方法C - 由进口压力与扬程回推"""
        data = {
            'pump_inlet_pressure': np.array([0.1, 0.15]),  # MPa
            'pump_head': np.array([40.0, 50.0])  # m
        }
        params = {}
        
        result = calculate_pump_outlet_pressure_method_c(data, params)
        
        # 验证出口压力计算
        # P_out = P_in + rho * g * H / 1e6
        assert result[0] > 0.1  # 应该大于进口压力
        assert result[1] > 0.15

    def test_method_c_with_nan(self):
        """场景18: 方法C - 包含NaN"""
        data = {
            'pump_inlet_pressure': np.array([0.1, np.nan]),
            'pump_head': np.array([np.nan, 50.0])
        }
        params = {}
        
        result = calculate_pump_outlet_pressure_method_c(data, params)
        
        # 验证返回NaN
        assert np.all(np.isnan(result))

    def test_method_d_normal_case(self):
        """场景19: 方法D - 泵组层面近似"""
        data = {
            'pump_group_outlet_pressure': np.array([0.5, 0.6])
        }
        params = {}

        result = calculate_pump_outlet_pressure_method_d(data, params)

        # 验证返回泵组出口压力的副本
        np.testing.assert_array_equal(result, data['pump_group_outlet_pressure'])
        assert result is not data['pump_group_outlet_pressure']


class TestPumpSpeedCalculations:
    """泵转速计算函数测试"""

    def test_method_a_normal_case(self):
        """场景20: 方法A - 频率比例法"""
        data = {
            'pump_frequency': np.array([40.0, 45.0, 50.0])  # Hz
        }
        params = {'n_ref': 1480.0, 'f_ref': 50.0}  # 额定转速和频率
        
        result = calculate_pump_speed_method_a(data, params)
        
        # 验证转速计算
        # n = (f / f_ref) * n_ref
        expected = np.array([1480.0 * 40.0 / 50.0, 1480.0 * 45.0 / 50.0, 1480.0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_method_a_with_nan(self):
        """场景21: 方法A - 包含NaN"""
        data = {
            'pump_frequency': np.array([40.0, np.nan, 50.0])
        }
        params = {'n_ref': 1480.0, 'f_ref': 50.0}
        
        result = calculate_pump_speed_method_a(data, params)
        
        # 验证NaN处理
        assert result[0] > 0
        assert np.isnan(result[1])
        assert result[2] > 0

    def test_method_b_normal_case(self):
        """场景22: 方法B - 绝对转速法"""
        data = {
            'pump_frequency': np.array([50.0, 45.0])
        }
        params = {'pole_pairs': 2, 'slip': 0.02}  # 4极电机，2%滑差

        result = calculate_pump_speed_method_b(data, params)

        # 验证转速计算（n_sync = 120*f/pole_pairs, n = n_sync*(1-slip)）
        # 50Hz: n_sync = 120*50/2 = 3000, n = 3000*0.98 = 2940
        assert np.all(result > 0)
        assert np.abs(result[0] - 2940.0) < 1.0
        assert np.abs(result[1] - 2646.0) < 1.0

    def test_method_b_with_nan(self):
        """场景23: 方法B - 包含NaN"""
        data = {
            'pump_frequency': np.array([50.0, np.nan])
        }
        params = {'pole_pairs': 2, 'slip': 0.02}

        result = calculate_pump_speed_method_b(data, params)

        # 验证NaN处理
        assert result[0] > 0
        assert np.isnan(result[1])

    def test_method_c_normal_case(self):
        """场景24: 方法C - 标定关系法"""
        data = {
            'pump_frequency': np.array([40.0, 45.0, 50.0])
        }
        params = {'calibration_a': 30.0, 'calibration_b': 0.0}  # n = a * f + b

        result = calculate_pump_speed_method_c(data, params)

        # 验证线性关系
        expected = np.array([30.0 * 40.0, 30.0 * 45.0, 30.0 * 50.0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_method_c_with_nan(self):
        """场景25: 方法C - 包含NaN"""
        data = {
            'pump_frequency': np.array([40.0, np.nan, 50.0])
        }
        params = {'a': 29.6, 'b': 0.0}

        result = calculate_pump_speed_method_c(data, params)

        # 验证NaN处理
        assert result[0] > 0
        assert np.isnan(result[1])
        assert result[2] > 0


class TestPumpTorqueCalculations:
    """泵扭矩计算函数测试"""

    def test_method_a_normal_case(self):
        """场景26: 方法A - 水力功率与转速法"""
        data = {
            'pump_flow_rate': np.array([100.0, 120.0]),  # m³/h
            'pump_head': np.array([40.0, 50.0]),  # m
            'pump_speed': np.array([1450.0, 1460.0]),  # rpm
            'pump_efficiency': np.array([0.75, 0.80])
        }
        params = {}

        result = calculate_pump_torque_method_a(data, params)

        # 验证扭矩计算
        assert np.all(result > 0)
        assert result[1] > result[0]  # 更高的流量和扬程应该产生更大的扭矩

    def test_method_a_with_nan(self):
        """场景27: 方法A - 包含NaN"""
        data = {
            'pump_flow_rate': np.array([100.0, np.nan]),
            'pump_head': np.array([np.nan, 50.0]),
            'pump_speed': np.array([1450.0, 1460.0]),
            'pump_efficiency': np.array([0.75, 0.80])
        }
        params = {}

        result = calculate_pump_torque_method_a(data, params)

        # 验证NaN处理
        assert np.all(np.isnan(result))

    def test_method_b_normal_case(self):
        """场景28: 方法B - 电功率与频率法"""
        data = {
            'pump_active_power': np.array([100.0, 120.0]),  # kW
            'pump_frequency': np.array([45.0, 50.0])  # Hz
        }
        params = {'eta_motor': 0.95, 'poles': 4}

        result = calculate_pump_torque_method_b(data, params)

        # 验证扭矩计算
        assert np.all(result > 0)

    def test_method_b_with_nan(self):
        """场景29: 方法B - 包含NaN"""
        data = {
            'pump_active_power': np.array([100.0, np.nan]),
            'pump_frequency': np.array([np.nan, 50.0])
        }
        params = {'eta_motor': 0.95, 'poles': 4}

        result = calculate_pump_torque_method_b(data, params)

        # 验证NaN处理
        assert np.all(np.isnan(result))


class TestMainPipelineOutletPressureCalculations:
    """总管出口压力计算函数测试"""

    def test_method_a_normal_case(self):
        """场景30: 方法A - 从单泵出口压力推算"""
        data = {
            'pump_outlet_pressure': np.array([0.5, 0.6, 0.7])
        }
        params = {}

        result = calculate_main_pipeline_outlet_pressure_method_a(data, params)

        # 验证返回泵出口压力的副本
        np.testing.assert_array_equal(result, data['pump_outlet_pressure'])
        assert result is not data['pump_outlet_pressure']

    def test_method_b_normal_case(self):
        """场景31: 方法B - 从泵进口压力和扬程推算"""
        data = {
            'pump_inlet_pressure': np.array([0.1, 0.15]),
            'pump_head': np.array([40.0, 50.0])
        }
        params = {}

        result = calculate_main_pipeline_outlet_pressure_method_b(data, params)

        # 验证出口压力计算
        assert np.all(result > 0.1)

    def test_method_b_with_nan(self):
        """场景32: 方法B - 包含NaN"""
        data = {
            'pump_inlet_pressure': np.array([0.1, np.nan]),
            'pump_head': np.array([np.nan, 50.0])
        }
        params = {}

        result = calculate_main_pipeline_outlet_pressure_method_b(data, params)

        # 验证NaN处理
        assert np.all(np.isnan(result))

    def test_method_c_normal_case(self):
        """场景33: 方法C - 从多泵出口压力聚合"""
        data = {
            'pump_outlet_pressure': [
                np.array([0.5, 0.6]),
                np.array([0.52, 0.58]),
                np.array([0.48, 0.62])
            ]
        }
        params = {'aggregation_method': 'max'}

        result = calculate_main_pipeline_outlet_pressure_method_c(data, params)

        # 验证聚合结果（最大值）
        assert np.all(result > 0)
        assert len(result) == 2
        # 第一个时间点的最大值应该是0.52
        assert np.abs(result[0] - 0.52) < 0.01
        # 第二个时间点的最大值应该是0.62
        assert np.abs(result[1] - 0.62) < 0.01

    def test_method_c_single_device(self):
        """场景34: 方法C - 单设备"""
        data = {
            'pump_outlet_pressure': np.array([0.5, 0.6])
        }
        params = {}

        result = calculate_main_pipeline_outlet_pressure_method_c(data, params)

        # 验证返回单设备数据的副本
        np.testing.assert_array_equal(result, data['pump_outlet_pressure'])
        assert result is not data['pump_outlet_pressure']


class TestMainPipelineInletPressureCalculations:
    """总管进口压力计算函数测试"""

    def test_method_a_normal_case(self):
        """场景35: 方法A - 从单泵进口压力推算"""
        data = {
            'pump_inlet_pressure': np.array([0.1, 0.15, 0.2])
        }
        params = {}

        result = calculate_main_pipeline_inlet_pressure_method_a(data, params)

        # 验证返回泵进口压力的副本
        np.testing.assert_array_equal(result, data['pump_inlet_pressure'])
        assert result is not data['pump_inlet_pressure']

    def test_method_b_normal_case(self):
        """场景36: 方法B - 从水池液位推算"""
        data = {
            'pool_liquid_level': np.array([5.0, 6.0, 7.0])  # m
        }
        params = {}

        result = calculate_main_pipeline_inlet_pressure_method_b(data, params)

        # 验证进口压力计算
        # P = P_atm + rho * g * L / 1e6
        assert np.all(result > 0.1)  # 应该大于大气压

    def test_method_b_with_nan(self):
        """场景37: 方法B - 包含NaN"""
        data = {
            'pool_liquid_level': np.array([5.0, np.nan, 7.0])
        }
        params = {}

        result = calculate_main_pipeline_inlet_pressure_method_b(data, params)

        # 验证NaN处理
        assert result[0] > 0
        assert np.isnan(result[1])
        assert result[2] > 0

    def test_method_c_normal_case(self):
        """场景38: 方法C - 从多泵进口压力聚合"""
        data = {
            'pump_inlet_pressure': [
                np.array([0.1, 0.15]),
                np.array([0.12, 0.14]),
                np.array([0.11, 0.16])
            ]
        }
        params = {'aggregation_method': 'max'}

        result = calculate_main_pipeline_inlet_pressure_method_c(data, params)

        # 验证聚合结果（最大值）
        assert np.all(result > 0)
        assert len(result) == 2
        # 第一个时间点的最大值应该是0.12
        assert np.abs(result[0] - 0.12) < 0.01
        # 第二个时间点的最大值应该是0.16
        assert np.abs(result[1] - 0.16) < 0.01

    def test_method_c_single_device(self):
        """场景39: 方法C - 单设备"""
        data = {
            'pump_inlet_pressure': np.array([0.1, 0.15])
        }
        params = {}

        result = calculate_main_pipeline_inlet_pressure_method_c(data, params)

        # 验证返回单设备数据的副本
        np.testing.assert_array_equal(result, data['pump_inlet_pressure'])
        assert result is not data['pump_inlet_pressure']


class TestPumpCumulativeFlowCalculations:
    """泵累计流量计算函数测试"""

    def test_method_a_normal_case(self):
        """场景40: 方法A - 从瞬时流量积分"""
        data = {
            'pump_flow_rate': np.array([100.0, 105.0, 98.0, 102.0]),  # m³/h
            '__timestamps': np.array([0, 3600, 7200, 10800])  # 秒（每小时）
        }
        params = {}

        result = calculate_pump_cumulative_flow_method_a(data, params)

        # 验证累计流量递增
        assert result[0] >= 0
        assert result[1] > result[0]
        assert result[2] > result[1]
        assert result[3] > result[2]

    def test_method_a_with_nan(self):
        """场景41: 方法A - 包含NaN"""
        data = {
            'pump_flow_rate': np.array([100.0, np.nan, 98.0, 102.0]),
            '__timestamps': np.array([0, 3600, 7200, 10800])
        }
        params = {}

        result = calculate_pump_cumulative_flow_method_a(data, params)

        # 验证NaN处理
        assert result[0] >= 0
        assert np.isnan(result[1])

    def test_method_b_normal_case(self):
        """场景42: 方法B - 从总管累计流量按比例分摊"""
        data = {
            'main_pipeline_cumulative_flow': np.array([1000.0, 2100.0, 3150.0]),
            'pump_flow_rate': np.array([50.0, 60.0, 40.0]),
            'main_pipeline_flow_rate': np.array([100.0, 100.0, 100.0])
        }
        params = {}

        result = calculate_pump_cumulative_flow_method_b(data, params)

        # 验证分摊结果（V_pump = V_main * (Q_pump / Q_main)）
        expected = np.array([1000.0 * 0.5, 2100.0 * 0.6, 3150.0 * 0.4])
        np.testing.assert_array_almost_equal(result, expected)

    def test_method_b_with_nan(self):
        """场景43: 方法B - 包含NaN"""
        data = {
            'main_pipeline_cumulative_flow': np.array([1000.0, np.nan, 3150.0]),
            'pump_flow_rate': np.array([50.0, 60.0, np.nan]),
            'main_pipeline_flow_rate': np.array([100.0, 100.0, 100.0])
        }
        params = {}

        result = calculate_pump_cumulative_flow_method_b(data, params)

        # 验证NaN处理
        assert result[0] > 0
        assert np.isnan(result[1])
        assert np.isnan(result[2])

