"""
约束计算器 (app.services.characteristic_curves.constraints.constraint_calculator)

计算曲线拟合的约束参数。

版本: v1.0
参考: 设计文档 3.8.4节
"""

import logging
from typing import Any, Dict

import pandas as pd

from app.services.characteristic_curves.core.data_structures import ConstraintResult


logger = logging.getLogger(__name__)


class ConstraintCalculator:
    """约束计算器
    
    计算曲线拟合的约束参数。
    
    计算内容:
    - QH: H0, Q_max, K, 单调性, 凸性
    - QP: P0, P_max, 能量守恒
    - QEta: Q_BEP, eta_max, 单峰性
    """
    
    def __init__(self, config: Dict = None):
        """初始化约束计算器
        
        Args:
            config: 配置参数,可选
        """
        self._config = config or {}
        
        # 容差参数
        self._monotonicity_tolerance = self._config.get('monotonicity_tolerance', 0.01)
        self._boundary_tolerance = self._config.get('boundary_tolerance', 0.05)
        
        logger.info(
            "[约束计算器] 初始化",
            extra={"extra_data": {
                "monotonicity_tolerance": self._monotonicity_tolerance,
                "boundary_tolerance": self._boundary_tolerance,
            }}
        )
    
    def calculate(
        self,
        curve_type: str,
        data: pd.DataFrame,
        device_params: Dict,
        config: Dict
    ) -> ConstraintResult:
        """计算约束参数
        
        Args:
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            data: 数据DataFrame
            device_params: 设备参数字典
            config: 配置参数(包含constraints配置)
        
        Returns:
            ConstraintResult: 约束计算结果
        
        Raises:
            ValueError: 参数缺失或无效时
        """
        curve_type_lower = curve_type.lower()
        
        # 提取容差配置
        constraints_config = config.get('constraints', {})
        monotonicity_tol = constraints_config.get('monotonicity_tolerance', self._monotonicity_tolerance)
        boundary_tol = constraints_config.get('boundary_tolerance', self._boundary_tolerance)
        
        # 验证必需的device_params
        required_params = ['rated_flow', 'rated_head', 'rated_power']
        missing = [p for p in required_params if p not in device_params]
        if missing:
            raise ValueError(f"设备参数缺失: {missing}")
        
        # 根据曲线类型计算
        if curve_type_lower == 'qh':
            result = self._calculate_qh_constraints(
                data, device_params, monotonicity_tol, boundary_tol
            )
        elif curve_type_lower == 'qp':
            result = self._calculate_qp_constraints(
                data, device_params, monotonicity_tol, boundary_tol
            )
        elif curve_type_lower == 'qeta':
            result = self._calculate_qeta_constraints(
                data, device_params, monotonicity_tol, boundary_tol
            )
        else:
            raise ValueError(f"不支持的曲线类型: {curve_type}")
        
        logger.info(
            f"[约束计算] curve_type={curve_type}, "
            f"bounds_count={len(result.bounds)}, "
            f"monotonicity_type={result.monotonicity_type}"
        )
        
        return result
    
    def _calculate_qh_constraints(
        self,
        data: pd.DataFrame,
        device_params: Dict,
        monotonicity_tol: float,
        boundary_tol: float
    ) -> ConstraintResult:
        """计算QH曲线约束"""
        rated_flow = device_params['rated_flow']
        rated_head = device_params['rated_head']
        
        # 边界值
        H0 = rated_head * 1.2  # H0约为1.1~1.3倍额定扬程
        Q_max = data['flow'].max() if len(data) > 0 else rated_flow * 1.2
        
        # 参数边界范围(简化版)
        bounds = {
            'a': (-10.0, 0.0),  # 二次项系数,应为负
            'b': (-10.0, 10.0),  # 一次项系数
            'c': (H0 * 0.8, H0 * 1.2),  # 常数项,接近H0
        }
        
        # 边界值字典
        boundary_values = {
            'H0': H0,
            'Q_max': Q_max,
            'K_range': (0.0, 0.1),  # K值范围
        }
        
        return ConstraintResult(
            curve_type='qh',
            bounds=bounds,
            monotonicity_type='decreasing',  # QH单调递减
            boundary_values=boundary_values,
            additional_constraints=[
                {'type': 'monotonicity', 'direction': 'decreasing', 'tolerance': monotonicity_tol},
                {'type': 'boundary', 'name': 'H0', 'tolerance': boundary_tol},
            ]
        )
    
    def _calculate_qp_constraints(
        self,
        data: pd.DataFrame,
        device_params: Dict,
        monotonicity_tol: float,
        boundary_tol: float
    ) -> ConstraintResult:
        """计算QP曲线约束"""
        rated_power = device_params['rated_power']
        rated_flow = device_params['rated_flow']
        
        # 边界值
        P0 = rated_power * 0.4  # P0约为0.3~0.5倍额定功率
        P_max = data['power'].max() if 'power' in data.columns and len(data) > 0 else rated_power * 1.2
        Q_max = data['flow'].max() if len(data) > 0 else rated_flow * 1.2
        
        # 参数边界范围
        bounds = {
            'a': (0.0, 1.0),  # 二次项系数,应为正
            'b': (0.0, 10.0),  # 一次项系数
            'c': (P0 * 0.5, P0 * 1.5),  # 常数项,接近P0
        }
        
        # 边界值字典
        boundary_values = {
            'P0': P0,
            'P_max': P_max,
            'Q_max': Q_max,
        }
        
        return ConstraintResult(
            curve_type='qp',
            bounds=bounds,
            monotonicity_type='increasing',  # QP单调递增
            boundary_values=boundary_values,
            additional_constraints=[
                {'type': 'monotonicity', 'direction': 'increasing', 'tolerance': monotonicity_tol},
                {'type': 'boundary', 'name': 'P0', 'tolerance': boundary_tol},
                {'type': 'energy_conservation'},  # 能量守恒
            ]
        )
    
    def _calculate_qeta_constraints(
        self,
        data: pd.DataFrame,
        device_params: Dict,
        monotonicity_tol: float,
        boundary_tol: float
    ) -> ConstraintResult:
        """计算QEta曲线约束"""
        rated_flow = device_params['rated_flow']
        
        # 边界值
        Q_BEP = rated_flow  # 最佳效率点流量约为额定流量
        eta_max = 0.85  # 最大效率假设值
        
        if 'efficiency' in data.columns and len(data) > 0:
            eta_max = data['efficiency'].max()
        
        # 参数边界范围(抛物线型)
        bounds = {
            'a': (-1.0, 0.0),  # 二次项系数,应为负(单峰)
            'b': (0.0, 1.0),  # 一次项系数
            'c': (0.0, 0.3),  # 常数项
        }
        
        # 边界值字典
        boundary_values = {
            'Q_BEP': Q_BEP,
            'eta_max': eta_max,
        }
        
        return ConstraintResult(
            curve_type='qeta',
            bounds=bounds,
            monotonicity_type='single_peak',  # QEta单峰
            boundary_values=boundary_values,
            additional_constraints=[
                {'type': 'single_peak', 'tolerance': monotonicity_tol},
                {'type': 'boundary', 'name': 'eta_max', 'tolerance': boundary_tol},
                {'type': 'eta_range', 'min': 0.0, 'max': 1.0},  # 效率范围0-1
            ]
        )
