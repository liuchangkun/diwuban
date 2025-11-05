# [弃用/占位][方案A-标注] 本模块当前未在仓库中被引用（扫描于 2025-09-24）。保留作结构/示例用途；不在生产路径使用。
# 如需启用，请补充调用/测试并移除此标注；若长期未启用，建议按方案B归档或方案C删除。

"""
基于物理机理的水泵系统参数计算模块
包含流体力学、热力学、电机学等物理原理的计算方法
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math

@dataclass
class FluidProperties:
    """流体物性参数"""
    density: float = 1000.0  # 水的密度 kg/m³
    viscosity: float = 1.002e-3  # 动力粘度 Pa·s (20°C)
    temperature: float = 20.0  # 温度 °C

    def update_properties_by_temperature(self, temp: float):
        """根据温度更新水的物性参数"""
        self.temperature = temp
        # 水的密度随温度变化 (使用经验公式，0-100°C范围)
        # 参考：CRC Handbook of Chemistry and Physics
        # ρ(T) ≈ 1000 - 0.0178×|T-4| - 0.0058×(T-4)²
        # 简化为多项式拟合，在0-100°C范围内误差<0.1%
        if 0 <= temp <= 100:
            # 使用三次多项式拟合（更准确）
            self.density = (999.83952 + 16.945176 * temp
                          - 7.9870401e-3 * temp**2
                          - 46.170461e-6 * temp**3
                          + 105.56302e-9 * temp**4
                          - 280.54253e-12 * temp**5)
            self.density = self.density / (1 + 16.879850e-3 * temp)
        else:
            # 超出范围使用简单线性近似
            self.density = 1000.0 - 0.2 * abs(temp - 4)

        # 水的动力粘度随温度变化 (Vogel方程)
        self.viscosity = 1.002e-3 * math.exp(1.3272 * (20 - temp) / (109.5 + temp))

@dataclass
class PumpGeometry:
    """水泵几何参数"""
    impeller_diameter: float  # 叶轮直径 m
    pipe_diameter: float  # 管道直径 m
    pipe_length: float  # 管道长度 m
    pipe_roughness: float = 0.00015  # 管道粗糙度 m (钢管)
    elevation_difference: float = 0.0  # 高程差 m
    pole_pairs: int = 2  # 电机极对数

class PhysicsBasedCalculator:
    """基于物理原理的计算器"""

    def __init__(self, fluid_props: FluidProperties, pump_geometry: PumpGeometry):
        self.fluid = fluid_props
        self.geometry = pump_geometry
        self.g = 9.81  # 重力加速度 m/s²

    def calculate_pump_speed(self, frequency: float) -> float:
        """
        计算泵转速 (基于电机学原理)
        n = 60f/p
        """
        return 60 * frequency / self.geometry.pole_pairs

    def calculate_flow_velocity(self, flow_rate: float) -> float:
        """
        计算管道流速 (连续性方程)
        v = Q/A = Q/(π*D²/4)
        """
        area = math.pi * (self.geometry.pipe_diameter ** 2) / 4
        return flow_rate / area

    def calculate_reynolds_number(self, flow_rate: float) -> float:
        """
        计算雷诺数 (流体力学基本参数)
        Re = ρvD/μ
        """
        velocity = self.calculate_flow_velocity(flow_rate)
        return (self.fluid.density * velocity * self.geometry.pipe_diameter) / self.fluid.viscosity

    def calculate_friction_factor(self, flow_rate: float) -> float:
        """
        计算摩擦系数 (Colebrook-White方程的近似解)
        适用于湍流区域
        """
        re = self.calculate_reynolds_number(flow_rate)
        relative_roughness = self.geometry.pipe_roughness / self.geometry.pipe_diameter

        # 处理零流量或极小雷诺数的情况
        if re <= 0:
            return 0.0

        if re < 2300:  # 层流
            return 64 / re
        else:  # 湍流 - Swamee-Jain方程
            term1 = relative_roughness / 3.7
            term2 = 5.74 / (re ** 0.9)
            return 0.25 / (math.log10(term1 + term2) ** 2)

    def calculate_pipe_head_loss(self, flow_rate: float) -> float:
        """
        计算管道水头损失 (Darcy-Weisbach方程)
        hf = f * (L/D) * (v²/2g)
        """
        velocity = self.calculate_flow_velocity(flow_rate)
        friction_factor = self.calculate_friction_factor(flow_rate)

        return friction_factor * (self.geometry.pipe_length / self.geometry.pipe_diameter) * \
               (velocity ** 2) / (2 * self.g)

    def calculate_pump_head(self, outlet_pressure: float, inlet_pressure: float,
                           flow_rate: float) -> float:
        """
        计算泵扬程 (伯努利方程)
        H = (P_out - P_in)/(ρg) + Δz + hf
        """
        pressure_head = (outlet_pressure - inlet_pressure) / (self.fluid.density * self.g)
        elevation_head = self.geometry.elevation_difference
        friction_head = self.calculate_pipe_head_loss(flow_rate)

        return pressure_head + elevation_head + friction_head

    def calculate_hydraulic_power(self, flow_rate: float, head: float) -> float:
        """
        计算水力功率 (流体力学基本公式)
        P_h = ρgQH
        """
        return self.fluid.density * self.g * flow_rate * head

    def calculate_pump_efficiency(self, hydraulic_power: float, shaft_power: float) -> float:
        """
        计算泵效率
        η = P_h / P_shaft
        """
        if shaft_power <= 0:
            return 0.0
        return hydraulic_power / shaft_power

    def calculate_motor_efficiency(self, mechanical_power: float, electrical_power: float) -> float:
        """
        计算电机效率
        η_motor = P_mech / P_elec
        """
        if electrical_power <= 0:
            return 0.0
        return mechanical_power / electrical_power

    def calculate_overall_efficiency(self, hydraulic_power: float, electrical_power: float) -> float:
        """
        计算总效率
        η_total = P_h / P_elec
        """
        if electrical_power <= 0:
            return 0.0
        return hydraulic_power / electrical_power

    def calculate_specific_speed(self, speed: float, flow_rate: float, head: float) -> float:
        """
        计算比转速 (相似理论)
        ns = n√Q / H^(3/4)
        """
        if head <= 0:
            return 0.0
        return speed * math.sqrt(flow_rate) / (head ** 0.75)

    def calculate_affinity_laws(self, n1: float, n2: float, q1: float, h1: float, p1: float) -> Tuple[float, float, float]:
        """
        相似定律计算 (泵的相似理论)
        Q2/Q1 = n2/n1
        H2/H1 = (n2/n1)²
        P2/P1 = (n2/n1)³
        """
        ratio = n2 / n1
        q2 = q1 * ratio
        h2 = h1 * (ratio ** 2)
        p2 = p1 * (ratio ** 3)
        return q2, h2, p2

    def calculate_npsh_available(self, suction_pressure: float, vapor_pressure: float,
                                suction_velocity: float, suction_elevation: float) -> float:
        """
        计算有效汽蚀余量 NPSH_a (汽蚀理论)
        NPSH_a = (P_s - P_v)/(ρg) + v²/(2g) - z_s
        """
        pressure_term = (suction_pressure - vapor_pressure) / (self.fluid.density * self.g)
        velocity_term = (suction_velocity ** 2) / (2 * self.g)
        elevation_term = suction_elevation

        return pressure_term + velocity_term - elevation_term

    def calculate_power_from_electrical_params(self, voltage_a: float, voltage_b: float, voltage_c: float,
                                             current_a: float, current_b: float, current_c: float,
                                             power_factor: float) -> Dict[str, float]:
        """
        基于电气参数计算功率 (电机学原理)
        """
        # 线电压有效值
        u_line = math.sqrt((voltage_a**2 + voltage_b**2 + voltage_c**2) / 3)
        # 线电流有效值
        i_line = math.sqrt((current_a**2 + current_b**2 + current_c**2) / 3)

        # 三相功率计算
        apparent_power = math.sqrt(3) * u_line * i_line  # 视在功率
        active_power = apparent_power * power_factor  # 有功功率
        reactive_power = apparent_power * math.sqrt(1 - power_factor**2)  # 无功功率

        return {
            'apparent_power': apparent_power,
            'active_power': active_power,
            'reactive_power': reactive_power,
            'line_voltage': u_line,
            'line_current': i_line
        }

    def calculate_motor_torque(self, power: float, speed: float) -> float:
        """
        计算电机扭矩 (机械学基本公式)
        T = P / ω = P / (2πn/60)
        """
        if speed <= 0:
            return 0.0
        angular_velocity = 2 * math.pi * speed / 60  # rad/s
        return power / angular_velocity

    def calculate_pump_characteristic_curve(self, flow_rates: List[float],
                                          base_head: float, base_flow: float) -> List[float]:
        """
        计算泵特性曲线 (基于二次多项式拟合)
        H = H0 - a*Q - b*Q²
        """
        heads = []
        # 典型的离心泵特性系数
        a = 0.1 * base_head / base_flow  # 线性系数
        b = 0.9 * base_head / (base_flow ** 2)  # 二次系数

        for q in flow_rates:
            h = base_head - a * q - b * (q ** 2)
            heads.append(max(0, h))  # 确保扬程非负

        return heads

    def calculate_system_operating_point(self, pump_curve_params: Dict,
                                       system_curve_params: Dict) -> Tuple[float, float]:
        """
        计算系统工作点 (泵特性曲线与系统特性曲线交点)
        泵曲线: H_pump = H0 - a*Q - b*Q²
        系统曲线: H_system = H_static + k*Q²
        """
        h0 = pump_curve_params['base_head']
        a = pump_curve_params['linear_coeff']
        b = pump_curve_params['quadratic_coeff']

        h_static = system_curve_params['static_head']
        k = system_curve_params['resistance_coeff']

        # 求解方程: H0 - a*Q - b*Q² = H_static + k*Q²
        # 整理得: (b + k)*Q² + a*Q + (H_static - H0) = 0
        A = b + k
        B = a
        C = h_static - h0

        discriminant = B**2 - 4*A*C
        if discriminant < 0:
            return 0.0, h_static  # 无解，返回静扬程点

        q1 = (-B + math.sqrt(discriminant)) / (2*A)
        q2 = (-B - math.sqrt(discriminant)) / (2*A)

        # 选择正的流量值
        q_operating = max(q1, q2) if max(q1, q2) > 0 else 0
        h_operating = h_static + k * (q_operating ** 2)

        return q_operating, h_operating

class VibrationAnalyzer:
    """振动分析器 (基于振动力学原理)"""

    @staticmethod
    def calculate_rms_vibration(vibration_data: List[float]) -> float:
        """计算振动有效值"""
        return math.sqrt(sum(x**2 for x in vibration_data) / len(vibration_data))

    @staticmethod
    def calculate_peak_to_peak(vibration_data: List[float]) -> float:
        """计算峰峰值"""
        return max(vibration_data) - min(vibration_data)

    @staticmethod
    def calculate_crest_factor(vibration_data: List[float]) -> float:
        """计算波峰因子"""
        rms = VibrationAnalyzer.calculate_rms_vibration(vibration_data)
        peak = max(abs(x) for x in vibration_data)
        return peak / rms if rms > 0 else 0

    @staticmethod
    def diagnose_bearing_condition(vibration_rms: float, frequency: float) -> str:
        """基于振动诊断轴承状态"""
        # ISO 10816标准的简化版本
        if vibration_rms < 1.8:
            return "良好"
        elif vibration_rms < 4.5:
            return "可接受"
        elif vibration_rms < 11.2:
            return "不满意"
        else:
            return "不可接受"

class ThermalAnalyzer:
    """热力学分析器"""

    @staticmethod
    def calculate_temperature_rise(power_loss: float, thermal_resistance: float) -> float:
        """
        计算温升 (热力学第一定律)
        ΔT = P_loss * R_th
        """
        return power_loss * thermal_resistance

    @staticmethod
    def calculate_bearing_temperature_limit(ambient_temp: float,
                                          bearing_type: str = "rolling") -> float:
        """计算轴承温度限值"""
        if bearing_type == "rolling":
            return ambient_temp + 80  # 滚动轴承
        else:
            return ambient_temp + 65  # 滑动轴承

    @staticmethod
    def calculate_motor_efficiency_by_temperature(base_efficiency: float,
                                                temp_rise: float) -> float:
        """根据温度计算电机效率修正"""
        # 温度每升高10°C，效率约下降1%
        efficiency_loss = temp_rise * 0.001
        return base_efficiency * (1 - efficiency_loss)

# 使用示例和测试函数
def example_usage():
    """使用示例"""
    # 初始化参数
    fluid = FluidProperties(density=1000.0, viscosity=1.002e-3, temperature=20.0)
    geometry = PumpGeometry(
        impeller_diameter=0.3,
        pipe_diameter=0.2,
        pipe_length=100.0,
        pipe_roughness=0.00015,
        elevation_difference=10.0,
        pole_pairs=2
    )

    # 创建计算器
    calculator = PhysicsBasedCalculator(fluid, geometry)

    # 示例计算
    frequency = 50.0  # Hz
    flow_rate = 0.05  # m³/s
    outlet_pressure = 500000  # Pa
    inlet_pressure = 100000  # Pa

    # 计算各种参数
    speed = calculator.calculate_pump_speed(frequency)
    head = calculator.calculate_pump_head(outlet_pressure, inlet_pressure, flow_rate)
    hydraulic_power = calculator.calculate_hydraulic_power(flow_rate, head)

    print(f"泵转速: {speed:.1f} rpm")
    print(f"泵扬程: {head:.2f} m")
    print(f"水力功率: {hydraulic_power:.2f} W")

if __name__ == "__main__":
    example_usage()
