"""
物理计算模块单元测试

测试 app/algorithms/physics_based_calculations.py 中的所有函数和类
"""

import pytest
import math
from app.algorithms.physics_based_calculations import (
    FluidProperties,
    PumpGeometry,
    PhysicsBasedCalculator,
    VibrationAnalyzer,
    ThermalAnalyzer,
)


class TestFluidProperties:
    """测试流体物性参数类"""

    def test_default_properties(self):
        """测试默认物性参数"""
        fluid = FluidProperties()
        assert fluid.density == 1000.0
        assert fluid.viscosity == 1.002e-3
        assert fluid.temperature == 20.0

    def test_custom_properties(self):
        """测试自定义物性参数"""
        fluid = FluidProperties(density=998.0, viscosity=1.0e-3, temperature=25.0)
        assert fluid.density == 998.0
        assert fluid.viscosity == 1.0e-3
        assert fluid.temperature == 25.0

    def test_update_properties_by_temperature_at_4_degrees(self):
        """测试4°C时的物性更新（水的最大密度点）"""
        fluid = FluidProperties()
        fluid.update_properties_by_temperature(4.0)
        assert fluid.temperature == 4.0
        # 4°C时水的密度应该接近最大值
        assert fluid.density == pytest.approx(1000.0, rel=0.01)

    def test_update_properties_by_temperature_at_20_degrees(self):
        """测试20°C时的物性更新"""
        fluid = FluidProperties()
        fluid.update_properties_by_temperature(20.0)
        assert fluid.temperature == 20.0
        # 20°C时水的密度约为998.2 kg/m³
        assert fluid.density == pytest.approx(998.2, rel=0.01)  # 允许1%误差
        # 密度应该小于4°C时的密度（水的最大密度点）
        assert fluid.density < 1000.0

    def test_update_properties_by_temperature_viscosity_decreases_with_temp(self):
        """测试粘度随温度升高而降低"""
        fluid = FluidProperties()
        fluid.update_properties_by_temperature(10.0)
        viscosity_10 = fluid.viscosity
        
        fluid.update_properties_by_temperature(30.0)
        viscosity_30 = fluid.viscosity
        
        # 温度升高，粘度应该降低
        assert viscosity_30 < viscosity_10


class TestPumpGeometry:
    """测试水泵几何参数类"""

    def test_pump_geometry_creation(self):
        """测试水泵几何参数创建"""
        geometry = PumpGeometry(
            impeller_diameter=0.3,
            pipe_diameter=0.2,
            pipe_length=100.0
        )
        assert geometry.impeller_diameter == 0.3
        assert geometry.pipe_diameter == 0.2
        assert geometry.pipe_length == 100.0
        assert geometry.pipe_roughness == 0.00015  # 默认值
        assert geometry.elevation_difference == 0.0  # 默认值
        assert geometry.pole_pairs == 2  # 默认值

    def test_pump_geometry_with_custom_values(self):
        """测试自定义几何参数"""
        geometry = PumpGeometry(
            impeller_diameter=0.5,
            pipe_diameter=0.3,
            pipe_length=200.0,
            pipe_roughness=0.0002,
            elevation_difference=15.0,
            pole_pairs=3
        )
        assert geometry.impeller_diameter == 0.5
        assert geometry.pipe_diameter == 0.3
        assert geometry.pipe_length == 200.0
        assert geometry.pipe_roughness == 0.0002
        assert geometry.elevation_difference == 15.0
        assert geometry.pole_pairs == 3


class TestPhysicsBasedCalculator:
    """测试基于物理原理的计算器"""

    @pytest.fixture
    def calculator(self):
        """创建标准计算器实例"""
        fluid = FluidProperties(density=1000.0, viscosity=1.002e-3, temperature=20.0)
        geometry = PumpGeometry(
            impeller_diameter=0.3,
            pipe_diameter=0.2,
            pipe_length=100.0,
            pipe_roughness=0.00015,
            elevation_difference=10.0,
            pole_pairs=2
        )
        return PhysicsBasedCalculator(fluid, geometry)

    def test_calculate_pump_speed_50hz(self, calculator):
        """测试50Hz时的泵转速计算"""
        speed = calculator.calculate_pump_speed(50.0)
        # n = 60f/p = 60*50/2 = 1500 rpm
        assert speed == pytest.approx(1500.0, rel=0.001)

    def test_calculate_pump_speed_60hz(self, calculator):
        """测试60Hz时的泵转速计算"""
        speed = calculator.calculate_pump_speed(60.0)
        # n = 60f/p = 60*60/2 = 1800 rpm
        assert speed == pytest.approx(1800.0, rel=0.001)

    def test_calculate_pump_speed_with_4_pole_pairs(self):
        """测试4极电机的转速计算"""
        fluid = FluidProperties()
        geometry = PumpGeometry(
            impeller_diameter=0.3,
            pipe_diameter=0.2,
            pipe_length=100.0,
            pole_pairs=4
        )
        calculator = PhysicsBasedCalculator(fluid, geometry)
        speed = calculator.calculate_pump_speed(50.0)
        # n = 60*50/4 = 750 rpm
        assert speed == pytest.approx(750.0, rel=0.001)

    def test_calculate_flow_velocity(self, calculator):
        """测试流速计算"""
        flow_rate = 0.05  # m³/s
        velocity = calculator.calculate_flow_velocity(flow_rate)
        # v = Q/A = Q/(π*D²/4) = 0.05/(π*0.2²/4) ≈ 1.59 m/s
        expected_velocity = flow_rate / (math.pi * (0.2 ** 2) / 4)
        assert velocity == pytest.approx(expected_velocity, rel=0.001)

    def test_calculate_flow_velocity_zero_flow(self, calculator):
        """测试零流量时的流速"""
        velocity = calculator.calculate_flow_velocity(0.0)
        assert velocity == 0.0

    def test_calculate_reynolds_number_laminar(self, calculator):
        """测试层流区域的雷诺数"""
        # 使用小流量确保层流
        flow_rate = 0.0001  # m³/s
        re = calculator.calculate_reynolds_number(flow_rate)
        # 层流区域 Re < 2300
        assert re < 2300

    def test_calculate_reynolds_number_turbulent(self, calculator):
        """测试湍流区域的雷诺数"""
        # 使用大流量确保湍流
        flow_rate = 0.1  # m³/s
        re = calculator.calculate_reynolds_number(flow_rate)
        # 湍流区域 Re > 2300
        assert re > 2300

    def test_calculate_friction_factor_laminar(self, calculator):
        """测试层流区域的摩擦系数"""
        flow_rate = 0.0001  # m³/s (层流)
        f = calculator.calculate_friction_factor(flow_rate)
        re = calculator.calculate_reynolds_number(flow_rate)
        # 层流: f = 64/Re
        expected_f = 64 / re
        assert f == pytest.approx(expected_f, rel=0.001)

    def test_calculate_friction_factor_turbulent(self, calculator):
        """测试湍流区域的摩擦系数"""
        flow_rate = 0.1  # m³/s (湍流)
        f = calculator.calculate_friction_factor(flow_rate)
        # 湍流区域摩擦系数应该在合理范围内
        assert 0.01 < f < 0.1

    def test_calculate_pipe_head_loss(self, calculator):
        """测试管道水头损失计算"""
        flow_rate = 0.05  # m³/s
        head_loss = calculator.calculate_pipe_head_loss(flow_rate)
        # 水头损失应该为正值
        assert head_loss > 0
        # 水头损失应该在合理范围内（对于100m管道）
        assert head_loss < 50  # m

    def test_calculate_pipe_head_loss_zero_flow(self, calculator):
        """测试零流量时的水头损失"""
        head_loss = calculator.calculate_pipe_head_loss(0.0)
        # 零流量时水头损失应该为0（已修复源代码的除零bug）
        assert head_loss == pytest.approx(0.0, abs=1e-6)

    def test_calculate_pump_head(self, calculator):
        """测试泵扬程计算"""
        outlet_pressure = 500000  # Pa
        inlet_pressure = 100000  # Pa
        flow_rate = 0.05  # m³/s
        
        head = calculator.calculate_pump_head(outlet_pressure, inlet_pressure, flow_rate)
        
        # 扬程应该为正值
        assert head > 0
        # 扬程应该包含压力扬程、高程差和摩擦损失
        pressure_head = (outlet_pressure - inlet_pressure) / (1000.0 * 9.81)
        assert head > pressure_head  # 应该大于压力扬程（因为还有高程差和摩擦损失）

    def test_calculate_hydraulic_power(self, calculator):
        """测试水力功率计算"""
        flow_rate = 0.05  # m³/s
        head = 50.0  # m
        
        power = calculator.calculate_hydraulic_power(flow_rate, head)
        
        # P_h = ρgQH = 1000 * 9.81 * 0.05 * 50 ≈ 24525 W
        expected_power = 1000.0 * 9.81 * flow_rate * head
        assert power == pytest.approx(expected_power, rel=0.001)

    def test_calculate_hydraulic_power_zero_flow(self, calculator):
        """测试零流量时的水力功率"""
        power = calculator.calculate_hydraulic_power(0.0, 50.0)
        assert power == 0.0

    def test_calculate_pump_efficiency(self, calculator):
        """测试泵效率计算"""
        hydraulic_power = 20000.0  # W
        shaft_power = 25000.0  # W
        
        efficiency = calculator.calculate_pump_efficiency(hydraulic_power, shaft_power)
        
        # η = P_h / P_shaft = 20000 / 25000 = 0.8
        assert efficiency == pytest.approx(0.8, rel=0.001)

    def test_calculate_pump_efficiency_zero_shaft_power(self, calculator):
        """测试零轴功率时的泵效率"""
        efficiency = calculator.calculate_pump_efficiency(20000.0, 0.0)
        assert efficiency == 0.0

    def test_calculate_pump_efficiency_negative_shaft_power(self, calculator):
        """测试负轴功率时的泵效率"""
        efficiency = calculator.calculate_pump_efficiency(20000.0, -1000.0)
        assert efficiency == 0.0

    def test_calculate_motor_efficiency(self, calculator):
        """测试电机效率计算"""
        mechanical_power = 24000.0  # W
        electrical_power = 30000.0  # W

        efficiency = calculator.calculate_motor_efficiency(mechanical_power, electrical_power)

        # η_motor = P_mech / P_elec = 24000 / 30000 = 0.8
        assert efficiency == pytest.approx(0.8, rel=0.001)

    def test_calculate_motor_efficiency_zero_electrical_power(self, calculator):
        """测试零电功率时的电机效率"""
        efficiency = calculator.calculate_motor_efficiency(24000.0, 0.0)
        assert efficiency == 0.0

    def test_calculate_overall_efficiency(self, calculator):
        """测试总效率计算"""
        hydraulic_power = 20000.0  # W
        electrical_power = 30000.0  # W

        efficiency = calculator.calculate_overall_efficiency(hydraulic_power, electrical_power)

        # η_total = P_h / P_elec = 20000 / 30000 ≈ 0.667
        assert efficiency == pytest.approx(0.6667, rel=0.001)

    def test_calculate_specific_speed(self, calculator):
        """测试比转速计算"""
        speed = 1500.0  # rpm
        flow_rate = 0.05  # m³/s
        head = 50.0  # m

        ns = calculator.calculate_specific_speed(speed, flow_rate, head)

        # ns = n√Q / H^(3/4)
        expected_ns = speed * math.sqrt(flow_rate) / (head ** 0.75)
        assert ns == pytest.approx(expected_ns, rel=0.001)

    def test_calculate_specific_speed_zero_head(self, calculator):
        """测试零扬程时的比转速"""
        ns = calculator.calculate_specific_speed(1500.0, 0.05, 0.0)
        assert ns == 0.0

    def test_calculate_affinity_laws(self, calculator):
        """测试相似定律计算"""
        n1 = 1500.0  # rpm
        n2 = 1800.0  # rpm
        q1 = 0.05  # m³/s
        h1 = 50.0  # m
        p1 = 25000.0  # W

        q2, h2, p2 = calculator.calculate_affinity_laws(n1, n2, q1, h1, p1)

        ratio = n2 / n1  # 1.2
        # Q2/Q1 = n2/n1
        assert q2 == pytest.approx(q1 * ratio, rel=0.001)
        # H2/H1 = (n2/n1)²
        assert h2 == pytest.approx(h1 * (ratio ** 2), rel=0.001)
        # P2/P1 = (n2/n1)³
        assert p2 == pytest.approx(p1 * (ratio ** 3), rel=0.001)

    def test_calculate_npsh_available(self, calculator):
        """测试有效汽蚀余量计算"""
        suction_pressure = 101325.0  # Pa (大气压)
        vapor_pressure = 2340.0  # Pa (20°C水的饱和蒸汽压)
        suction_velocity = 2.0  # m/s
        suction_elevation = 3.0  # m

        npsh_a = calculator.calculate_npsh_available(
            suction_pressure, vapor_pressure, suction_velocity, suction_elevation
        )

        # NPSH_a应该为正值
        assert npsh_a > 0
        # NPSH_a应该在合理范围内
        assert npsh_a < 20  # m

    def test_calculate_power_from_electrical_params(self, calculator):
        """测试基于电气参数的功率计算"""
        voltage_a = 380.0  # V
        voltage_b = 380.0  # V
        voltage_c = 380.0  # V
        current_a = 50.0  # A
        current_b = 50.0  # A
        current_c = 50.0  # A
        power_factor = 0.85

        result = calculator.calculate_power_from_electrical_params(
            voltage_a, voltage_b, voltage_c,
            current_a, current_b, current_c,
            power_factor
        )

        # 验证返回的字典包含所有必需的键
        assert 'apparent_power' in result
        assert 'active_power' in result
        assert 'reactive_power' in result
        assert 'line_voltage' in result
        assert 'line_current' in result

        # 验证线电压和线电流
        assert result['line_voltage'] == pytest.approx(380.0, rel=0.001)
        assert result['line_current'] == pytest.approx(50.0, rel=0.001)

        # 验证视在功率 S = √3 * U * I
        expected_apparent = math.sqrt(3) * 380.0 * 50.0
        assert result['apparent_power'] == pytest.approx(expected_apparent, rel=0.001)

        # 验证有功功率 P = S * cosφ
        expected_active = expected_apparent * 0.85
        assert result['active_power'] == pytest.approx(expected_active, rel=0.001)

        # 验证无功功率 Q = S * sinφ
        expected_reactive = expected_apparent * math.sqrt(1 - 0.85**2)
        assert result['reactive_power'] == pytest.approx(expected_reactive, rel=0.001)

    def test_calculate_motor_torque(self, calculator):
        """测试电机扭矩计算"""
        power = 25000.0  # W
        speed = 1500.0  # rpm

        torque = calculator.calculate_motor_torque(power, speed)

        # T = P / ω = P / (2πn/60)
        angular_velocity = 2 * math.pi * speed / 60
        expected_torque = power / angular_velocity
        assert torque == pytest.approx(expected_torque, rel=0.001)

    def test_calculate_motor_torque_zero_speed(self, calculator):
        """测试零转速时的电机扭矩"""
        torque = calculator.calculate_motor_torque(25000.0, 0.0)
        assert torque == 0.0

    def test_calculate_pump_characteristic_curve(self, calculator):
        """测试泵特性曲线计算"""
        flow_rates = [0.0, 0.025, 0.05, 0.075, 0.1]
        base_head = 60.0  # m
        base_flow = 0.1  # m³/s

        heads = calculator.calculate_pump_characteristic_curve(flow_rates, base_head, base_flow)

        # 验证返回的扬程列表长度正确
        assert len(heads) == len(flow_rates)

        # 验证零流量时扬程最大
        assert heads[0] == max(heads)

        # 验证扬程随流量增加而减小（离心泵特性）
        for i in range(len(heads) - 1):
            assert heads[i] >= heads[i + 1]

        # 验证所有扬程非负
        for h in heads:
            assert h >= 0

    def test_calculate_system_operating_point(self, calculator):
        """测试系统工作点计算"""
        pump_curve_params = {
            'base_head': 60.0,
            'linear_coeff': 0.1,
            'quadratic_coeff': 5.0
        }
        system_curve_params = {
            'static_head': 20.0,
            'resistance_coeff': 10.0
        }

        q_op, h_op = calculator.calculate_system_operating_point(
            pump_curve_params, system_curve_params
        )

        # 工作点流量应该为正值
        assert q_op >= 0
        # 工作点扬程应该大于静扬程
        assert h_op >= system_curve_params['static_head']

    def test_calculate_system_operating_point_no_solution(self, calculator):
        """测试无解情况的系统工作点"""
        pump_curve_params = {
            'base_head': 10.0,  # 泵扬程太低
            'linear_coeff': 0.1,
            'quadratic_coeff': 5.0
        }
        system_curve_params = {
            'static_head': 50.0,  # 静扬程太高
            'resistance_coeff': 10.0
        }

        q_op, h_op = calculator.calculate_system_operating_point(
            pump_curve_params, system_curve_params
        )

        # 无解时应该返回零流量和静扬程
        assert q_op == 0.0
        assert h_op == system_curve_params['static_head']


class TestVibrationAnalyzer:
    """测试振动分析器"""

    def test_calculate_rms_vibration(self):
        """测试振动有效值计算"""
        vibration_data = [1.0, -1.0, 2.0, -2.0, 0.0]
        rms = VibrationAnalyzer.calculate_rms_vibration(vibration_data)

        # RMS = √(Σx²/n) = √((1+1+4+4+0)/5) = √2 ≈ 1.414
        expected_rms = math.sqrt(sum(x**2 for x in vibration_data) / len(vibration_data))
        assert rms == pytest.approx(expected_rms, rel=0.001)

    def test_calculate_peak_to_peak(self):
        """测试峰峰值计算"""
        vibration_data = [1.0, -2.0, 3.0, -1.0, 0.0]
        p2p = VibrationAnalyzer.calculate_peak_to_peak(vibration_data)

        # 峰峰值 = max - min = 3.0 - (-2.0) = 5.0
        assert p2p == pytest.approx(5.0, rel=0.001)

    def test_calculate_crest_factor(self):
        """测试波峰因子计算"""
        vibration_data = [1.0, 1.0, 1.0, 5.0, 1.0]
        cf = VibrationAnalyzer.calculate_crest_factor(vibration_data)

        # 波峰因子 = peak / rms
        rms = VibrationAnalyzer.calculate_rms_vibration(vibration_data)
        peak = max(abs(x) for x in vibration_data)
        expected_cf = peak / rms
        assert cf == pytest.approx(expected_cf, rel=0.001)

    def test_calculate_crest_factor_zero_rms(self):
        """测试零有效值时的波峰因子"""
        vibration_data = [0.0, 0.0, 0.0]
        cf = VibrationAnalyzer.calculate_crest_factor(vibration_data)
        assert cf == 0.0

    def test_diagnose_bearing_condition_good(self):
        """测试良好状态的轴承诊断"""
        condition = VibrationAnalyzer.diagnose_bearing_condition(1.5, 50.0)
        assert condition == "良好"

    def test_diagnose_bearing_condition_acceptable(self):
        """测试可接受状态的轴承诊断"""
        condition = VibrationAnalyzer.diagnose_bearing_condition(3.0, 50.0)
        assert condition == "可接受"

    def test_diagnose_bearing_condition_unsatisfactory(self):
        """测试不满意状态的轴承诊断"""
        condition = VibrationAnalyzer.diagnose_bearing_condition(8.0, 50.0)
        assert condition == "不满意"

    def test_diagnose_bearing_condition_unacceptable(self):
        """测试不可接受状态的轴承诊断"""
        condition = VibrationAnalyzer.diagnose_bearing_condition(15.0, 50.0)
        assert condition == "不可接受"


class TestThermalAnalyzer:
    """测试热力学分析器"""

    def test_calculate_temperature_rise(self):
        """测试温升计算"""
        power_loss = 1000.0  # W
        thermal_resistance = 0.05  # K/W

        temp_rise = ThermalAnalyzer.calculate_temperature_rise(power_loss, thermal_resistance)

        # ΔT = P_loss * R_th = 1000 * 0.05 = 50 K
        assert temp_rise == pytest.approx(50.0, rel=0.001)

    def test_calculate_bearing_temperature_limit_rolling(self):
        """测试滚动轴承温度限值"""
        ambient_temp = 25.0  # °C
        limit = ThermalAnalyzer.calculate_bearing_temperature_limit(ambient_temp, "rolling")

        # 滚动轴承限值 = 环境温度 + 80
        assert limit == pytest.approx(105.0, rel=0.001)

    def test_calculate_bearing_temperature_limit_sliding(self):
        """测试滑动轴承温度限值"""
        ambient_temp = 25.0  # °C
        limit = ThermalAnalyzer.calculate_bearing_temperature_limit(ambient_temp, "sliding")

        # 滑动轴承限值 = 环境温度 + 65
        assert limit == pytest.approx(90.0, rel=0.001)

    def test_calculate_motor_efficiency_by_temperature(self):
        """测试温度对电机效率的影响"""
        base_efficiency = 0.90
        temp_rise = 30.0  # °C

        efficiency = ThermalAnalyzer.calculate_motor_efficiency_by_temperature(
            base_efficiency, temp_rise
        )

        # 温度每升高10°C，效率约下降1%
        # 30°C温升 → 效率损失 = 30 * 0.001 = 0.03
        # 修正后效率 = 0.90 * (1 - 0.03) = 0.873
        expected_efficiency = base_efficiency * (1 - temp_rise * 0.001)
        assert efficiency == pytest.approx(expected_efficiency, rel=0.001)

    def test_calculate_motor_efficiency_by_temperature_zero_rise(self):
        """测试零温升时的电机效率"""
        base_efficiency = 0.90
        efficiency = ThermalAnalyzer.calculate_motor_efficiency_by_temperature(
            base_efficiency, 0.0
        )
        assert efficiency == pytest.approx(base_efficiency, rel=0.001)

