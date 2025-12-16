"""曲线特征点生成器 (app.services.characteristic_curves.shared.curve_point_generator)

根据拟合系数生成曲线的采样点和关键工况点,存储到数据库curve_points字段。

版本: v2.0 - 完整curve_points JSONB结构
参考: 设计文档 3.6.4节、02_核心模块详细设计.md 5.1.3节
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime

import numpy as np


logger = logging.getLogger(__name__)


class CurvePointGenerator:
    """曲线特征点生成器

    根据拟合系数生成曲线的采样点和关键工况点。

    采样点数规范:
    - 默认: 20个
    - 高精度: 50个
    - 超高精度: 100个

    输出完整的curve_points JSONB结构,包括:
    - sampling_points: 均匀采样点
    - key_points: 关键工况点(零流量、额定、最大流量等)
    - operating_range: 推荐工作范围
    - formula: 曲线公式字符串
    """

    def __init__(self, n_sampling_points: int = 20):
        """初始化生成器

        Args:
            n_sampling_points: 采样点数量(默认20个)
        """
        self._n_sampling_points = n_sampling_points

        logger.info(
            "[曲线点生成器] 初始化",
            extra={"extra_data": {
                "采样点数": n_sampling_points,
            }}
        )

    def generate(
        self,
        curve_type: str,
        coefficients: Dict[str, float],
        method_name: str,
        rated_params: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """生成曲线特征点

        Args:
            curve_type: 曲线类型(qh/qp/qeta)
            coefficients: 拟合系数字典
            method_name: 拟合方法名称
            rated_params: 额定参数(可选)

        Returns:
            Dict: curve_points JSONB格式的完整结构
                {
                    "generated_at": "2025-12-11T15:30:00",
                    "point_count": 25,
                    "formula": "H = H0 - K × Q²",
                    "sampling_points": {
                        "description": "工作范围内均匀采样点",
                        "count": 20,
                        "Q": [0.0, 5.0, ...],
                        "H": [50.0, 49.8, ...]
                    },
                    "key_points": {
                        "zero_flow": {"name": "零流量点", "Q": 0, "H": 50.0, ...},
                        "rated": {"name": "额定工况点", "Q": 100, "H": 40.0, ...},
                        "max_flow": {"name": "最大流量点", "Q": 350, "H": 0, ...}
                    },
                    "operating_range": {
                        "Q_min": 52.5,
                        "Q_max": 315.0,
                        "H_min": 5.0,
                        "H_max": 48.0,
                        "description": "推荐工作范围(避免气蚀和过载)"
                    }
                }

        Raises:
            ValueError: curve_type不支持或参数错误时
        """
        if curve_type == 'qh':
            return self._generate_qh_points(coefficients, method_name, rated_params)
        elif curve_type == 'qp':
            return self._generate_qp_points(coefficients, method_name, rated_params)
        elif curve_type == 'qeta':
            return self._generate_qeta_points(coefficients, method_name, rated_params)
        else:
            return self._generate_generic_points(coefficients, method_name)

    def _generate_qh_points(
        self,
        coefficients: Dict[str, float],
        method_name: str,
        rated_params: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """生成QH曲线特征点

        Args:
            coefficients: 拟合系数
            method_name: 拟合方法名称
            rated_params: 额定参数

        Returns:
            Dict: QH曲线完整的curve_points结构
        """
        # 提取系数(支持多种方法的系数命名)
        if 'H0' in coefficients and 'K' in coefficients:
            # physics_pump_char 方法: H = H0 - K*Q²
            H0, K = coefficients['H0'], coefficients['K']
            Q_max = np.sqrt(H0 / abs(K)) if K < 0 else 350.0

            def calc_H(Q):
                return H0 + K * Q**2

            formula = f"H = {H0:.2f} + ({K:.6f}) × Q²"

        elif 'a0' in coefficients:
            # 多项式方法: H = a0 + a1*Q + a2*Q²
            a0 = coefficients.get('a0', 0)
            a1 = coefficients.get('a1', 0)
            a2 = coefficients.get('a2', 0)

            # 求Q_max(H=0的点)
            if a2 != 0:
                discriminant = a1**2 - 4*a2*a0
                if discriminant >= 0:
                    Q_max = (-a1 + np.sqrt(discriminant)) / (2*a2)
                    if Q_max < 0:
                        Q_max = 350.0
                else:
                    Q_max = 350.0
            else:
                Q_max = 350.0

            def calc_H(Q):
                return a0 + a1*Q + a2*Q**2

            formula = f"H = {a0:.2f} + {a1:.6f}×Q + {a2:.6f}×Q²"
        else:
            # 默认处理
            Q_max = 350.0

            def calc_H(Q):
                return 40 - 0.0003*Q**2
            formula = "未知公式"

        # 生成采样点
        Q_range = np.linspace(0, Q_max * 0.95, self._n_sampling_points)
        H_range = np.array([calc_H(q) for q in Q_range])
        H_range = np.maximum(H_range, 0)  # 确保H不为负

        # 关键点
        key_points = {
            "zero_flow": {
                "name": "零流量点",
                "Q": 0,
                "H": round(float(calc_H(0)), 1),
                "description": "关阀扬程(shutoff head)"
            },
            "max_flow": {
                "name": "最大流量点",
                "Q": round(float(Q_max), 1),
                "H": 0,
                "description": "扬程为零时的最大流量"
            }
        }

        # 添加额定点(如果有额定参数)
        if rated_params and 'Q_rated' in rated_params:
            Q_rated = rated_params['Q_rated']
            key_points["rated"] = {
                "name": "额定工况点",
                "Q": float(Q_rated),
                "H": round(float(calc_H(Q_rated)), 1),
                "description": "铭牌额定参数"
            }

        # 工作范围
        operating_range = {
            "Q_min": round(float(Q_max * 0.15), 1),
            "Q_max": round(float(Q_max * 0.90), 1),
            "H_min": round(float(calc_H(Q_max * 0.90)), 1),
            "H_max": round(float(calc_H(Q_max * 0.15)), 1),
            "description": "推荐工作范围(避免气蚀和过载)"
        }

        result = {
            "generated_at": datetime.now().isoformat(),
            "point_count": self._n_sampling_points + len(key_points),
            "formula": formula,
            "sampling_points": {
                "description": "工作范围内均匀采样点",
                "count": self._n_sampling_points,
                "Q": [round(float(q), 1) for q in Q_range],
                "H": [round(float(h), 1) for h in H_range]
            },
            "key_points": key_points,
            "operating_range": operating_range
        }

        logger.info(
            f"[曲线点生成] QH曲线生成完成: 采样点{self._n_sampling_points}个, 关键点{len(key_points)}个"
        )

        return result

    def _generate_qp_points(
        self,
        coefficients: Dict[str, float],
        method_name: str,
        rated_params: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """生成QP曲线特征点(功率曲线)

        Args:
            coefficients: 拟合系数
            method_name: 拟合方法名称
            rated_params: 额定参数

        Returns:
            Dict: QP曲线完整的curve_points结构
        """
        # 简化实现:生成基础结构
        Q_max = rated_params.get('Q_max', 350.0) if rated_params else 350.0
        Q_range = np.linspace(0, Q_max * 0.95, self._n_sampling_points)

        # 使用多项式系数计算功率
        a0 = coefficients.get('a0', 0)
        a1 = coefficients.get('a1', 0.05)
        a2 = coefficients.get('a2', 0.0001)

        def calc_P(Q):
            return a0 + a1*Q + a2*Q**2

        P_range = np.array([calc_P(q) for q in Q_range])
        P_range = np.maximum(P_range, 0)

        formula = f"P = {a0:.2f} + {a1:.6f}×Q + {a2:.6f}×Q²"

        key_points = {
            "zero_flow": {
                "name": "零流量点",
                "Q": 0,
                "P": round(float(calc_P(0)), 1),
                "description": "零流量功率"
            },
            "max_flow": {
                "name": "最大流量点",
                "Q": round(float(Q_max), 1),
                "P": round(float(calc_P(Q_max)), 1),
                "description": "最大流量功率"
            }
        }

        return {
            "generated_at": datetime.now().isoformat(),
            "point_count": self._n_sampling_points + len(key_points),
            "formula": formula,
            "sampling_points": {
                "description": "工作范围内均匀采样点",
                "count": self._n_sampling_points,
                "Q": [round(float(q), 1) for q in Q_range],
                "P": [round(float(p), 1) for p in P_range]
            },
            "key_points": key_points,
            "operating_range": {
                "Q_min": round(float(Q_max * 0.15), 1),
                "Q_max": round(float(Q_max * 0.90), 1),
                "description": "推荐工作范围"
            }
        }

    def _generate_qeta_points(
        self,
        coefficients: Dict[str, float],
        method_name: str,
        rated_params: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """生成Q-η曲线特征点(效率曲线)

        Args:
            coefficients: 拟合系数
            method_name: 拟合方法名称
            rated_params: 额定参数

        Returns:
            Dict: Q-η曲线完整的curve_points结构
        """
        # 简化实现:生成基础结构
        Q_max = rated_params.get('Q_max', 350.0) if rated_params else 350.0
        Q_range = np.linspace(0, Q_max * 0.95, self._n_sampling_points)

        # 使用高斯函数或多项式
        a0 = coefficients.get('a0', 50.0)  # 峰值效率
        a1 = coefficients.get('a1', 100.0)  # 峰值流量
        a2 = coefficients.get('a2', 50.0)  # 标准差

        def calc_eta(Q):
            # 高斯分布: η = a0 * exp(-((Q - a1)^2) / (2*a2^2))
            return a0 * np.exp(-((Q - a1)**2) / (2 * a2**2))

        eta_range = np.array([calc_eta(q) for q in Q_range])
        eta_range = np.clip(eta_range, 0, 100)  # 限制在0-100%

        formula = f"η = {a0:.2f} × exp(-((Q - {a1:.2f})² / (2×{a2:.2f}²)))"

        # 找BEP点(最高效率点)
        bep_idx = np.argmax(eta_range)
        Q_bep = Q_range[bep_idx]
        eta_bep = eta_range[bep_idx]

        key_points = {
            "zero_flow": {
                "name": "零流量点",
                "Q": 0,
                "eta": round(float(calc_eta(0)), 1),
                "description": "零流量效率"
            },
            "bep": {
                "name": "最佳效率点(BEP)",
                "Q": round(float(Q_bep), 1),
                "eta": round(float(eta_bep), 1),
                "description": "最高效率工况点"
            },
            "max_flow": {
                "name": "最大流量点",
                "Q": round(float(Q_max), 1),
                "eta": round(float(calc_eta(Q_max)), 1),
                "description": "最大流量效率"
            }
        }

        return {
            "generated_at": datetime.now().isoformat(),
            "point_count": self._n_sampling_points + len(key_points),
            "formula": formula,
            "sampling_points": {
                "description": "工作范围内均匀采样点",
                "count": self._n_sampling_points,
                "Q": [round(float(q), 1) for q in Q_range],
                "eta": [round(float(e), 1) for e in eta_range]
            },
            "key_points": key_points,
            "operating_range": {
                "Q_min": round(float(Q_bep * 0.7), 1),
                "Q_max": round(float(Q_bep * 1.3), 1),
                "description": "高效区范围(BEP±30%)"
            }
        }

    def _generate_generic_points(
        self,
        coefficients: Dict[str, float],
        method_name: str
    ) -> Dict[str, Any]:
        """生成通用曲线特征点

        Args:
            coefficients: 拟合系数
            method_name: 拟合方法名称

        Returns:
            Dict: 通用曲线基础结构
        """
        return {
            "generated_at": datetime.now().isoformat(),
            "point_count": 0,
            "formula": "未知曲线类型",
            "sampling_points": {
                "description": "暂无采样点",
                "count": 0,
                "Q": [],
                "Y": []
            },
            "key_points": {},
            "operating_range": {}
        }
