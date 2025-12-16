"""
系统曲线提供器 (app.services.characteristic_curves.pump_group.system_curve_provider)

提供管网系统阻力曲线（H-Q关系）。

核心功能：
- 生成系统阻力曲线
- 拟合历史数据
- 支持多种管网模型
- 与泵曲线交点计算

物理原理：
H_system = H_static + K * Q^n
其中：
- H_static: 静扬程（水位差）
- K: 管网阻力系数
- n: 通常取2（紊流区）

版本: v1.0
创建日期: 2025-12-14
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class SystemCurveParams:
    """系统曲线参数"""
    H_static: float  # 静扬程 (m)
    K: float  # 阻力系数
    n: float = 2.0  # 阻力指数（紊流区通常为2）


class SystemCurveProvider:
    """系统曲线提供器

    提供管网系统的H-Q特性曲线，用于：
    1. 确定泵组工作点
    2. 变工况分析
    3. 能耗优化

    系统曲线物理模型：
    H_system = H_static + K * Q^n

    其中：
    - H_static: 静扬程（吸水池与出水口的水位差）
    - K: 管网综合阻力系数
    - n: 阻力指数（层流n=1，紊流n=2）
    """

    def __init__(
        self,
        H_static: float = 0.0,
        K: float = 0.00001,
        n: float = 2.0
    ):
        """
        Args:
            H_static: 静扬程 (m)
            K: 阻力系数 (m/(m³/h)^n)
            n: 阻力指数
        """
        self._H_static = H_static
        self._K = K
        self._n = n

    def get_curve_func(self) -> Callable[[float], float]:
        """获取系统曲线函数 H = f(Q)"""
        def curve(Q: float) -> float:
            return self._H_static + self._K * (abs(Q) ** self._n)
        return curve

    def calculate_H(self, Q: float) -> float:
        """计算给定流量下的系统扬程"""
        return self._H_static + self._K * (abs(Q) ** self._n)

    def calculate_Q_at_H(self, H: float) -> Optional[float]:
        """反算给定扬程下的流量"""
        if H <= self._H_static:
            return 0.0

        delta_H = H - self._H_static
        if delta_H < 0 or self._K <= 0:
            return None

        Q = (delta_H / self._K) ** (1.0 / self._n)
        return Q

    def fit_from_data(
        self,
        Q_data: List[float],
        H_data: List[float],
        H_static: Optional[float] = None
    ) -> SystemCurveParams:
        """
        从历史数据拟合系统曲线

        Args:
            Q_data: 流量数据 (m³/h)
            H_data: 扬程数据 (m)
            H_static: 已知静扬程（若未知则自动拟合）

        Returns:
            拟合的系统曲线参数
        """
        import numpy as np
        from scipy.optimize import curve_fit

        Q_arr = np.array(Q_data)
        H_arr = np.array(H_data)

        if H_static is not None:
            # 已知静扬程，只拟合K和n
            self._H_static = H_static

            def model(Q, K, n):
                return H_static + K * np.power(np.abs(Q), n)

            try:
                popt, _ = curve_fit(model, Q_arr, H_arr, p0=[0.00001, 2.0],
                                    bounds=([0, 1.5], [0.01, 2.5]))
                self._K = popt[0]
                self._n = popt[1]
            except Exception as e:
                logger.warning(f"拟合失败，使用默认值: {e}")
                self._K = 0.00001
                self._n = 2.0
        else:
            # 同时拟合H_static, K, n
            def model(Q, H_static, K, n):
                return H_static + K * np.power(np.abs(Q), n)

            try:
                popt, _ = curve_fit(model, Q_arr, H_arr,
                                    p0=[min(H_arr), 0.00001, 2.0],
                                    bounds=([0, 0, 1.5], [max(H_arr), 0.01, 2.5]))
                self._H_static = popt[0]
                self._K = popt[1]
                self._n = popt[2]
            except Exception as e:
                logger.warning(f"拟合失败，使用默认值: {e}")
                self._H_static = min(H_arr) if H_arr.size > 0 else 0
                self._K = 0.00001
                self._n = 2.0

        return SystemCurveParams(
            H_static=self._H_static,
            K=self._K,
            n=self._n
        )

    def find_operating_point(
        self,
        pump_curve_func: Callable[[float], float],
        Q_range: Tuple[float, float] = (0, 2000),
        tolerance: float = 0.1
    ) -> Optional[Dict[str, float]]:
        """
        找泵曲线与系统曲线的交点（工作点）

        Args:
            pump_curve_func: 泵曲线函数 H = f(Q)
            Q_range: 流量搜索范围
            tolerance: 扬程容差 (m)

        Returns:
            {'Q': float, 'H': float} 或 None
        """
        import numpy as np

        Q_values = np.linspace(Q_range[0], Q_range[1], 1000)

        min_diff = float('inf')
        best_point = None

        for Q in Q_values:
            H_pump = pump_curve_func(Q)
            H_system = self.calculate_H(Q)
            diff = abs(H_pump - H_system)

            if diff < min_diff:
                min_diff = diff
                best_point = {'Q': float(Q), 'H': float(
                    (H_pump + H_system) / 2)}

        if min_diff <= tolerance and best_point:
            return best_point

        return None

    def generate_curve_data(
        self,
        Q_range: Tuple[float, float] = (0, 2000),
        n_points: int = 100
    ) -> List[Dict[str, float]]:
        """
        生成系统曲线数据点

        Args:
            Q_range: 流量范围
            n_points: 数据点数

        Returns:
            [{'Q': float, 'H': float}, ...]
        """
        import numpy as np

        Q_values = np.linspace(Q_range[0], Q_range[1], n_points)

        return [
            {'Q': round(float(Q), 1), 'H': round(self.calculate_H(Q), 2)}
            for Q in Q_values
        ]

    def update_params(
        self,
        H_static: Optional[float] = None,
        K: Optional[float] = None,
        n: Optional[float] = None
    ) -> None:
        """更新系统曲线参数"""
        if H_static is not None:
            self._H_static = H_static
        if K is not None:
            self._K = K
        if n is not None:
            self._n = n

    def get_params(self) -> SystemCurveParams:
        """获取当前参数"""
        return SystemCurveParams(
            H_static=self._H_static,
            K=self._K,
            n=self._n
        )

    def analyze_sensitivity(
        self,
        Q_operating: float,
        param_variations: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        参数敏感性分析

        Args:
            Q_operating: 工作点流量
            param_variations: 参数变化范围 {'H_static': 0.1, 'K': 0.2}

        Returns:
            敏感性分析结果
        """
        if param_variations is None:
            param_variations = {'H_static': 0.1, 'K': 0.2, 'n': 0.1}

        H_base = self.calculate_H(Q_operating)
        sensitivities = {}

        # H_static敏感性
        delta_H_static = self._H_static * param_variations.get('H_static', 0.1)
        H_plus = (self._H_static + delta_H_static) + \
            self._K * (Q_operating ** self._n)
        sensitivities['H_static'] = {
            'delta_param': delta_H_static,
            'delta_H': H_plus - H_base,
            'sensitivity': (H_plus - H_base) / delta_H_static if delta_H_static != 0 else 0
        }

        # K敏感性
        delta_K = self._K * param_variations.get('K', 0.2)
        H_plus = self._H_static + (self._K + delta_K) * \
            (Q_operating ** self._n)
        sensitivities['K'] = {
            'delta_param': delta_K,
            'delta_H': H_plus - H_base,
            'sensitivity': (H_plus - H_base) / delta_K if delta_K != 0 else 0
        }

        return {
            'Q_operating': Q_operating,
            'H_base': H_base,
            'sensitivities': sensitivities,
            'generated_at': datetime.now().isoformat()
        }

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            'H_static': self._H_static,
            'K': self._K,
            'n': self._n,
            'formula': f'H = {self._H_static:.2f} + {self._K:.8f} * Q^{self._n:.2f}'
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemCurveProvider':
        """从字典创建"""
        return cls(
            H_static=data.get('H_static', 0.0),
            K=data.get('K', 0.00001),
            n=data.get('n', 2.0)
        )
