"""
特性曲线拟合系统 - P2阶段曲线注册表

版本: v2.6
创建日期: 2025-12-09
文件路径: app/services/characteristic_curves/shared/curve_registry.py
来源: 03_共用层.md 第8章

用途:
    - P2阶段泵组合成时获取各单泵的曲线函数
    - 在阶段13（ResultStorage.save）后自动注册
    - 支持正向函数(Q→H)和逆函数(H→Q)
"""

from typing import Callable, Dict, Optional, Tuple, Union, List
from dataclasses import dataclass
import logging
import threading
import numpy as np


@dataclass
class CurveEntry:
    """曲线注册条目

    v2.5更新（P41修复）：
    - coefficients支持两种格式：
      - Dict[str, float]: 如 {"H0": 40.0, "K": -2.5e-6}（推荐，可读性好）
      - List[float]: 如 [40.0, -2.5e-6]（多项式系数，从高次到低次）
    """
    pump_id: int
    curve_type: str
    version: str
    forward_func: Optional[Callable[[float], float]]  # Q → H
    inverse_func: Optional[Callable[[float], float]]  # H → Q（仅qh曲线有）
    Q_range: Tuple[float, float] = (0, 5000)  # 有效流量范围
    H_range: Tuple[float, float] = (0, 100)   # 有效扬程范围
    # v2.3新增：额定参数（用于负荷分配等计算）
    rated_power: Optional[float] = None       # 额定功率 (kW)
    rated_flow: Optional[float] = None        # 额定流量 (m³/h)
    rated_head: Optional[float] = None        # 额定扬程 (m)
    # v2.5修复P41：coefficients支持Dict或List两种格式
    coefficients: Optional[Union[Dict[str, float], List[float]]] = None
    r_squared: Optional[float] = None         # 拟合优度
    method_name: Optional[str] = None         # 拟合方法名
    # v2.4新增：功率和效率曲线函数【P33修复】
    power_func: Optional[Callable[[float], float]] = None      # Q → P (kW)
    efficiency_func: Optional[Callable[[float], float]] = None  # Q → η (%)
    # v2.5新增: FitResult兼容字段
    data_points: int = 0
    fitted_at: Optional[str] = None
    rmse: float = 0.0


class CurveRegistry:
    """曲线注册表（线程安全单例）

    用于P2阶段泵组合成时获取各单泵的曲线函数。
    在阶段13（ResultStorage.save）后自动注册。
    """

    _instance: Optional['CurveRegistry'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'CurveRegistry':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """初始化注册表"""
        self._entries: Dict[str, CurveEntry] = {}  # key: "{pump_id}_{curve_type}"
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _make_key(self, pump_id: int, curve_type: str) -> str:
        """生成注册表键"""
        return f"{pump_id}_{curve_type}"

    def register(
        self,
        pump_id: int,
        curve_type: str,
        version: str,
        coefficients: Dict[str, float],
        method_name: str,
        Q_range: Tuple[float, float],
        H_range: Tuple[float, float],
        rated_power: Optional[float] = None,
        rated_flow: Optional[float] = None,
        rated_head: Optional[float] = None,
        power_func: Optional[Callable[[float], float]] = None,
        efficiency_func: Optional[Callable[[float], float]] = None,
        r_squared: Optional[float] = None,
        data_points: int = 0,
        fitted_at: Optional[str] = None,
        rmse: float = 0.0
    ) -> None:
        """注册单泵曲线（正向和逆函数同时生成）

        设计说明：
        - 本方法主要用于注册 Q-H 曲线，因为并联合成需要 H → Q 逆函数
        - Q-P 和 Q-η 曲线通过 power_func 和 efficiency_func 参数一并注册

        Args:
            pump_id: 泵ID
            curve_type: 曲线类型（'qh', 'qp', 'qeta'）
            version: 曲线版本
            coefficients: 拟合系数 {"H0": 40.0, "K": -2.5e-6}
            method_name: 拟合方法名
            Q_range: 有效流量范围（必须指定，禁止默认值）
            H_range: 有效扬程范围（必须指定，禁止默认值）
            rated_power: 额定功率 (kW)
            rated_flow: 额定流量 (m³/h)
            rated_head: 额定扬程 (m)
            power_func: Q → P 功率曲线函数
            efficiency_func: Q → η 效率曲线函数
            r_squared: 拟合优度
            data_points: 数据点数
            fitted_at: 拟合时间
            rmse: 均方根误差

        Raises:
            ValueError: curve_type不支持时
        """
        if curve_type not in ('qh', 'qp', 'qeta'):
            raise ValueError(f"不支持的曲线类型: {curve_type}，支持: qh, qp, qeta")

        key = self._make_key(pump_id, curve_type)

        # 根据曲线类型生成不同的函数
        forward_func: Optional[Callable[[float], float]] = None
        inverse_func: Optional[Callable[[float], float]] = None

        if curve_type == 'qh':
            # Q-H 曲线：生成正向函数和逆函数
            H0 = coefficients.get('H0')
            K = coefficients.get('K')

            if H0 is None or K is None:
                raise ValueError(f"qh曲线必须提供H0和K系数，当前: {coefficients}")

            # 捕获变量用于闭包
            _H0, _K = H0, K

            # 生成正向函数: Q → H = H0 + K*Q²
            def forward_func(Q: float, H0: float = _H0, K: float = _K) -> float:
                return H0 + K * Q ** 2

            # 生成逆函数: H → Q = sqrt((H - H0) / K)
            def inverse_func(H: float, H0: float = _H0, K: float = _K) -> float:
                if K >= 0:
                    raise ValueError(f"K必须为负数，当前K={K}")

                # 边界检查：H不能超过关死点H0
                if H > H0:
                    if H - H0 < 0.01:  # 容差0.01m
                        return 0.0  # 接近关死点，流量为0
                    else:
                        self._logger.warning(
                            f"[CurveRegistry] 扬程 H={H:.2f}m 超出关死点 H0={H0:.2f}m，返回Q=0"
                        )
                        return 0.0

                discriminant = (H - H0) / K
                if discriminant < 0:
                    return 0.0

                return float(np.sqrt(max(discriminant, 0.0)))

        elif curve_type == 'qp':
            # Q-P 曲线：使用 power_func 作为正向函数，无逆函数
            if power_func is not None:
                forward_func = power_func
            else:
                self._logger.warning(f"[曲线注册] qp曲线未提供power_func，pump_id={pump_id}")

        elif curve_type == 'qeta':
            # Q-η 曲线：使用 efficiency_func 作为正向函数，无逆函数
            if efficiency_func is not None:
                forward_func = efficiency_func
            else:
                self._logger.warning(f"[曲线注册] qeta曲线未提供efficiency_func，pump_id={pump_id}")

        # 创建CurveEntry
        entry = CurveEntry(
            pump_id=pump_id,
            curve_type=curve_type,
            version=version,
            forward_func=forward_func,
            inverse_func=inverse_func,
            Q_range=Q_range,
            H_range=H_range,
            rated_power=rated_power,
            rated_flow=rated_flow,
            rated_head=rated_head,
            coefficients=coefficients,
            r_squared=r_squared,
            method_name=method_name,
            power_func=power_func,
            efficiency_func=efficiency_func,
            data_points=data_points,
            fitted_at=fitted_at,
            rmse=rmse
        )

        with self._lock:
            old_entry = self._entries.get(key)
            self._entries[key] = entry
            if old_entry:
                self._logger.info(
                    f"[曲线注册] 更新 pump={pump_id}, type={curve_type}, "
                    f"version: {old_entry.version} → {version}"
                )
            else:
                self._logger.info(
                    f"[曲线注册] 新增 pump={pump_id}, type={curve_type}, version={version}"
                )

    def get_forward(self, pump_id: int, curve_type: str) -> Callable[[float], float]:
        """获取正向函数 Q → H"""
        key = self._make_key(pump_id, curve_type)
        entry = self._entries.get(key)
        if not entry:
            raise KeyError(f"未注册曲线: pump_id={pump_id}, curve_type={curve_type}")
        if entry.forward_func is None:
            raise ValueError(f"曲线无正向函数: pump_id={pump_id}, curve_type={curve_type}")
        return entry.forward_func

    def get_inverse(self, pump_id: int, curve_type: str) -> Callable[[float], float]:
        """获取逆函数 H → Q"""
        key = self._make_key(pump_id, curve_type)
        entry = self._entries.get(key)
        if not entry:
            raise KeyError(f"未注册曲线: pump_id={pump_id}, curve_type={curve_type}")
        if entry.inverse_func is None:
            raise ValueError(f"曲线无逆函数: pump_id={pump_id}, curve_type={curve_type}")
        return entry.inverse_func

    def has_curve(self, pump_id: int, curve_type: str) -> bool:
        """检查曲线是否已注册"""
        key = self._make_key(pump_id, curve_type)
        return key in self._entries

    def get_version(self, pump_id: int, curve_type: str) -> Optional[str]:
        """获取曲线版本"""
        key = self._make_key(pump_id, curve_type)
        entry = self._entries.get(key)
        return entry.version if entry else None

    def unregister(self, pump_id: int, curve_type: str) -> bool:
        """注销曲线"""
        key = self._make_key(pump_id, curve_type)
        with self._lock:
            if key in self._entries:
                del self._entries[key]
                self._logger.info(f"[曲线注册] 注销 pump={pump_id}, type={curve_type}")
                return True
            return False

    def list_registered(self, curve_type: str) -> Dict[int, str]:
        """列出所有已注册的泵及其版本"""
        result: Dict[int, str] = {}
        for key, entry in self._entries.items():
            if entry.curve_type == curve_type:
                result[entry.pump_id] = entry.version
        return result

    def get_entry(self, pump_id: int, curve_type: str) -> Optional[CurveEntry]:
        """获取完整的曲线注册条目

        Args:
            pump_id: 泵ID
            curve_type: 曲线类型

        Returns:
            CurveEntry: 曲线条目（包含rated_power等属性），未注册时返回None
        """
        key = self._make_key(pump_id, curve_type)
        return self._entries.get(key)

    def clear(self) -> None:
        """清除所有注册（主要用于测试）"""
        with self._lock:
            self._entries.clear()
            self._logger.info("[曲线注册] 已清除所有注册")

