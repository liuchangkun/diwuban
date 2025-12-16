"""
派生曲线生成器 (app.services.characteristic_curves.pump_group.derived_curve_generator)

从基础曲线（qh, qp, qeta）派生其他曲线类型（heta, peta等）。

核心功能：
- H-η曲线派生（从qh+qeta）
- P-η曲线派生（从qp+qeta）
- 反函数计算（Q=f(H), Q=f(P)）
- 曲面拟合支持（η=f(Q,H)二元函数）

物理原理：
- heta(H) = qeta(qh_inverse(H))  // 通过qh反函数将H映射到Q
- peta(P) = qeta(qp_inverse(P))  // 通过qp反函数将P映射到Q

版本: v1.0
创建日期: 2025-12-14
参考文档: 08_泵组直接拟合.md 第14.3节
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DerivedCurveResult:
    """派生曲线结果"""
    curve_type: str  # heta, peta, pq等
    source_curves: List[str]  # 源曲线类型

    # 曲线数据点
    x_values: List[float] = field(default_factory=list)
    y_values: List[float] = field(default_factory=list)

    # 拟合系数（如果进行了拟合）
    coefficients: List[float] = field(default_factory=list)

    # 评估指标
    r_squared: float = 0.0
    rmse: float = 0.0

    # 有效范围
    valid_x_range: Tuple[float, float] = (0.0, 100.0)

    # 预测函数
    _predict_func: Optional[Callable[[float], float]] = None

    # 元数据
    generated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def predict(self, x: float) -> float:
        """预测Y值"""
        if self._predict_func is not None:
            return self._predict_func(x)
        if self.coefficients:
            return sum(c * (x ** i) for i, c in enumerate(self.coefficients))
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "curve_type": self.curve_type,
            "source_curves": self.source_curves,
            "x_values": self.x_values,
            "y_values": self.y_values,
            "coefficients": self.coefficients,
            "r_squared": self.r_squared,
            "rmse": self.rmse,
            "valid_x_range": self.valid_x_range,
            "generated_at": self.generated_at.isoformat(),
            "metadata": self.metadata,
        }


class DerivedCurveGenerator:
    """派生曲线生成器

    职责：
    1. 从qh+qeta派生heta曲线（H-η关系）
    2. 从qp+qeta派生peta曲线（P-η关系）
    3. 计算曲线反函数
    4. 支持二元曲面拟合

    物理背景：
    - H-η曲线：在固定系统中，扬程与效率的关系
    - P-η曲线：功率与效率的关系，用于能效评估
    """

    def __init__(self, polynomial_degree: int = 3):
        """初始化

        Args:
            polynomial_degree: 派生曲线拟合阶数
        """
        self._poly_degree = polynomial_degree
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

    def derive_heta_curve(
        self,
        qh_curve: Callable[[float], float],
        qeta_curve: Callable[[float], float],
        H_range: Tuple[float, float] = (20, 60),
        n_points: int = 50
    ) -> DerivedCurveResult:
        """从Q-H和Q-η曲线派生H-η曲线

        物理原理：
        1. 给定H，通过qh的反函数求 Q = qh_inverse(H)
        2. 将Q代入qeta求 η = qeta(Q)
        3. 得到 H-η 关系

        Args:
            qh_curve: Q-H曲线函数 H = f(Q)
            qeta_curve: Q-η曲线函数 η = f(Q)
            H_range: 扬程范围 (m)
            n_points: 采样点数

        Returns:
            DerivedCurveResult: H-η派生曲线
        """
        result = DerivedCurveResult(
            curve_type="heta",
            source_curves=["qh", "qeta"],
            valid_x_range=H_range,
        )

        # 首先构建qh的反函数
        qh_inverse = self._build_inverse_function(
            qh_curve, x_range=(0, 2000), n_samples=100)

        if qh_inverse is None:
            self._logger.error("[派生曲线] 无法构建qh反函数")
            return result

        # 在H范围内采样
        H_values = np.linspace(H_range[0], H_range[1], n_points)

        for H in H_values:
            try:
                Q = qh_inverse(H)
                if Q is not None and Q > 0:
                    eta = qeta_curve(Q)
                    if eta is not None and 0 <= eta <= 1:
                        result.x_values.append(float(H))
                        result.y_values.append(float(eta))
            except Exception as e:
                self._logger.warning(f"[派生曲线] H={H}计算失败: {e}")
                continue

        # 拟合多项式
        if len(result.x_values) >= 3:
            self._fit_polynomial(result)

        self._logger.info(
            f"[H-η派生] 生成{len(result.x_values)}个点, R²={result.r_squared:.4f}"
        )

        return result

    def derive_peta_curve(
        self,
        qp_curve: Callable[[float], float],
        qeta_curve: Callable[[float], float],
        P_range: Tuple[float, float] = (10, 200),
        n_points: int = 50
    ) -> DerivedCurveResult:
        """从Q-P和Q-η曲线派生P-η曲线

        物理原理：
        1. 给定P，通过qp的反函数求 Q = qp_inverse(P)
        2. 将Q代入qeta求 η = qeta(Q)
        3. 得到 P-η 关系

        Args:
            qp_curve: Q-P曲线函数 P = f(Q)
            qeta_curve: Q-η曲线函数 η = f(Q)
            P_range: 功率范围 (kW)
            n_points: 采样点数

        Returns:
            DerivedCurveResult: P-η派生曲线
        """
        result = DerivedCurveResult(
            curve_type="peta",
            source_curves=["qp", "qeta"],
            valid_x_range=P_range,
        )

        # 构建qp的反函数
        qp_inverse = self._build_inverse_function(
            qp_curve, x_range=(0, 2000), n_samples=100)

        if qp_inverse is None:
            self._logger.error("[派生曲线] 无法构建qp反函数")
            return result

        # 在P范围内采样
        P_values = np.linspace(P_range[0], P_range[1], n_points)

        for P in P_values:
            try:
                Q = qp_inverse(P)
                if Q is not None and Q > 0:
                    eta = qeta_curve(Q)
                    if eta is not None and 0 <= eta <= 1:
                        result.x_values.append(float(P))
                        result.y_values.append(float(eta))
            except Exception as e:
                self._logger.warning(f"[派生曲线] P={P}计算失败: {e}")
                continue

        # 拟合多项式
        if len(result.x_values) >= 3:
            self._fit_polynomial(result)

        self._logger.info(
            f"[P-η派生] 生成{len(result.x_values)}个点, R²={result.r_squared:.4f}"
        )

        return result

    def derive_pq_curve(
        self,
        qp_curve: Callable[[float], float],
        Q_range: Tuple[float, float] = (0, 2000),
        n_points: int = 50
    ) -> DerivedCurveResult:
        """派生P-Q曲线（功率反推流量）

        本质上是Q-P曲线的反函数。

        Args:
            qp_curve: Q-P曲线函数
            Q_range: 流量范围
            n_points: 采样点数

        Returns:
            DerivedCurveResult: P-Q派生曲线
        """
        result = DerivedCurveResult(
            curve_type="pq",
            source_curves=["qp"],
        )

        # 采样Q-P关系
        Q_values = np.linspace(Q_range[0], Q_range[1], n_points)
        P_values = []
        valid_Q = []

        for Q in Q_values:
            try:
                P = qp_curve(Q)
                if P is not None and P > 0:
                    P_values.append(float(P))
                    valid_Q.append(float(Q))
            except Exception:
                continue

        # 交换X/Y得到P-Q关系
        result.x_values = P_values
        result.y_values = valid_Q

        if P_values:
            result.valid_x_range = (min(P_values), max(P_values))

        # 拟合
        if len(result.x_values) >= 3:
            self._fit_polynomial(result)

        return result

    def fit_eta_surface(
        self,
        Q_data: np.ndarray,
        H_data: np.ndarray,
        eta_data: np.ndarray,
        degree: int = 2
    ) -> Dict[str, Any]:
        """拟合效率曲面 η = f(Q, H)

        解决Q-η直接拟合忽略H影响的问题。

        Args:
            Q_data: 流量数据数组
            H_data: 扬程数据数组
            eta_data: 效率数据数组
            degree: 多项式阶数

        Returns:
            Dict: 包含模型、系数、评估指标
        """
        try:
            from sklearn.preprocessing import PolynomialFeatures
            from sklearn.linear_model import Ridge
            from sklearn.metrics import r2_score, mean_squared_error
        except ImportError:
            self._logger.error("[曲面拟合] 需要sklearn库")
            return {"success": False, "error": "sklearn not available"}

        # 构建特征矩阵
        X = np.column_stack([Q_data, H_data])

        # 多项式特征
        poly = PolynomialFeatures(degree=degree)
        X_poly = poly.fit_transform(X)

        # 岭回归拟合
        model = Ridge(alpha=0.1)
        model.fit(X_poly, eta_data)

        # 预测和评估
        eta_pred = model.predict(X_poly)
        r2 = r2_score(eta_data, eta_pred)
        rmse = np.sqrt(mean_squared_error(eta_data, eta_pred))

        # 构建预测函数
        def predict_eta(Q: float, H: float) -> float:
            X_new = poly.transform([[Q, H]])
            return float(model.predict(X_new)[0])

        result = {
            "success": True,
            "model_type": "polynomial_surface",
            "degree": degree,
            "r_squared": r2,
            "rmse": rmse,
            "coefficients": model.coef_.tolist(),
            "intercept": float(model.intercept_),
            "feature_names": poly.get_feature_names_out().tolist(),
            "predict_func": predict_eta,
            "generated_at": datetime.now().isoformat(),
        }

        self._logger.info(f"[曲面拟合] η=f(Q,H) R²={r2:.4f}, RMSE={rmse:.4f}")

        return result

    def _build_inverse_function(
        self,
        func: Callable[[float], float],
        x_range: Tuple[float, float],
        n_samples: int = 100
    ) -> Optional[Callable[[float], Optional[float]]]:
        """构建函数的反函数（数值方法）

        通过采样和插值构建反函数。
        """
        try:
            from scipy.interpolate import interp1d
        except ImportError:
            # 回退到简单的线性插值
            return self._simple_inverse(func, x_range, n_samples)

        # 采样原函数
        x_values = np.linspace(x_range[0], x_range[1], n_samples)
        y_values = []
        valid_x = []

        for x in x_values:
            try:
                y = func(x)
                if y is not None and np.isfinite(y):
                    y_values.append(y)
                    valid_x.append(x)
            except Exception:
                continue

        if len(valid_x) < 3:
            return None

        # 构建反函数（交换x/y）
        try:
            inverse = interp1d(
                y_values, valid_x,
                kind='linear',
                bounds_error=False,
                fill_value='extrapolate'
            )
            return lambda y: float(inverse(y))
        except Exception:
            return None

    def _simple_inverse(
        self,
        func: Callable[[float], float],
        x_range: Tuple[float, float],
        n_samples: int
    ) -> Optional[Callable[[float], Optional[float]]]:
        """简单的反函数实现（线性插值）"""
        x_values = np.linspace(x_range[0], x_range[1], n_samples)
        pairs = []

        for x in x_values:
            try:
                y = func(x)
                if y is not None and np.isfinite(y):
                    pairs.append((y, x))
            except Exception:
                continue

        if not pairs:
            return None

        pairs.sort(key=lambda p: p[0])

        def inverse(y_target: float) -> Optional[float]:
            for i in range(len(pairs) - 1):
                y1, x1 = pairs[i]
                y2, x2 = pairs[i + 1]
                if y1 <= y_target <= y2 or y2 <= y_target <= y1:
                    if abs(y2 - y1) < 1e-10:
                        return x1
                    t = (y_target - y1) / (y2 - y1)
                    return x1 + t * (x2 - x1)
            return None

        return inverse

    def _fit_polynomial(self, result: DerivedCurveResult) -> None:
        """拟合多项式"""
        if len(result.x_values) < 3:
            return

        x = np.array(result.x_values)
        y = np.array(result.y_values)

        try:
            coeffs = np.polyfit(x, y, min(self._poly_degree, len(x) - 1))
            result.coefficients = coeffs[::-1].tolist()  # 从低次到高次

            # 计算R²
            y_pred = np.polyval(coeffs, x)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            result.r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

            # 计算RMSE
            result.rmse = np.sqrt(np.mean((y - y_pred) ** 2))

            # 创建预测函数
            result._predict_func = lambda x_val: float(
                np.polyval(coeffs, x_val))

        except Exception as e:
            self._logger.warning(f"[多项式拟合] 失败: {e}")
