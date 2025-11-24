"""
方法注册表 (app.services.characteristic_curves.methods.method_registry)

本模块提供拟合方法的注册、查找和管理功能。

设计模式：单例模式 + 注册表模式（线程安全）
线程安全：使用双重检查锁定（Double-Checked Locking）

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/03_核心模块/02_方法层.md
"""

import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

import pandas as pd

from .base_method import BaseMethod


@dataclass
class MethodBenchmark:
    """方法性能基准数据

    Attributes:
        avg_fit_time_ms: 平均拟合耗时（毫秒）
        avg_memory_mb: 平均内存占用（MB）
        typical_r_squared: 典型R²值
        recommended_data_points: 推荐数据点数量
        max_data_points: 最大支持数据点数量
    """

    avg_fit_time_ms: float
    avg_memory_mb: float
    typical_r_squared: float
    recommended_data_points: int
    max_data_points: int


# 预定义的方法性能基准（基于实际测试数据）
# 包含全部 14 种 P0 优先级方法
DEFAULT_METHOD_BENCHMARKS: Dict[str, MethodBenchmark] = {
    # 数学方法 - 多项式
    "math_poly_2": MethodBenchmark(50, 10, 0.95, 1000, 100000),
    "math_poly_3": MethodBenchmark(80, 15, 0.97, 1000, 100000),
    # 数学方法 - 样条
    "math_spline_cubic": MethodBenchmark(120, 25, 0.98, 500, 50000),
    "math_spline_bspline": MethodBenchmark(150, 30, 0.98, 500, 50000),
    # 数学方法 - 核方法
    "math_kernel_rbf": MethodBenchmark(200, 50, 0.96, 1000, 80000),
    # 数学方法 - 有理函数
    "math_rational_pade": MethodBenchmark(180, 35, 0.97, 800, 60000),
    # 数学方法 - 统计
    "math_stat_gaussian": MethodBenchmark(100, 20, 0.94, 1000, 100000),
    # 数学方法 - 局部
    "math_local_lowess": MethodBenchmark(300, 40, 0.96, 500, 30000),
    # 物理模型
    "physics_pump_char": MethodBenchmark(100, 20, 0.96, 500, 50000),
    "physics_power_eq": MethodBenchmark(80, 15, 0.95, 500, 50000),
    # 机器学习方法
    "ml_gradient_boost": MethodBenchmark(2000, 200, 0.98, 2000, 200000),
    "ml_random_forest": MethodBenchmark(1500, 150, 0.97, 2000, 200000),
    "ml_gaussian_process": MethodBenchmark(3000, 300, 0.98, 1000, 50000),
    # 混合方法
    "hybrid_physics_poly": MethodBenchmark(250, 45, 0.97, 800, 80000),
}


class MethodRegistry:
    """方法注册表（线程安全的单例模式）

    使用双重检查锁定模式（Double-Checked Locking）确保线程安全。

    核心功能：
    - 方法注册和管理
    - 方法查找和实例化
    - 自动选择最佳方法
    - 方法元数据管理
    """

    _instance: Optional["MethodRegistry"] = None
    _lock = threading.Lock()  # 类级别锁，保护实例创建

    def __new__(cls) -> "MethodRegistry":
        # 双重检查锁定模式
        if cls._instance is None:
            with cls._lock:
                # 再次检查，防止多线程竞争
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                    cls._instance._instance_lock = threading.RLock()  # 实例级别锁
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
            self._methods: Dict[str, Dict[str, Type[BaseMethod]]] = {}
            self._method_metadata: Dict[str, Dict[str, Dict[str, Any]]] = {}
            self._method_benchmarks: Dict[str, MethodBenchmark] = (
                DEFAULT_METHOD_BENCHMARKS.copy()
            )
            self._initialized = True
            self._logger.info(
                "[方法注册表] 单例初始化完成",
                extra={"extra_data": {"线程ID": threading.current_thread().name}},
            )

    def register(
        self,
        curve_type: str,
        method_id: str,
        method_name: str,
        method_class: Type[BaseMethod],
        priority: int,
        description: str,
        dependencies: Optional[List[str]] = None,
        applicable_conditions: Optional[Dict[str, Any]] = None,
    ) -> None:
        """注册拟合方法（线程安全）

        Args:
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            method_id: 方法唯一标识
            method_name: 方法显示名称（中文）
            method_class: 方法类（BaseMethod的子类）
            priority: 优先级（越高越优先）
            description: 方法描述
            dependencies: 依赖的数据列列表
            applicable_conditions: 适用条件字典
        """
        with self._instance_lock:
            if curve_type not in self._methods:
                self._methods[curve_type] = {}
                self._method_metadata[curve_type] = {}

            self._methods[curve_type][method_id] = method_class
            self._method_metadata[curve_type][method_id] = {
                "method_name": method_name,
                "priority": priority,
                "description": description,
                "dependencies": dependencies if dependencies is not None else [],
                "applicable_conditions": (
                    applicable_conditions if applicable_conditions is not None else {}
                ),
            }

            self._logger.info(
                "[注册器] 方法注册成功",
                extra={
                    "extra_data": {
                        "曲线类型": curve_type,
                        "方法ID": method_id,
                        "方法名称": method_name,
                        "优先级": priority,
                    }
                },
            )

    def get_method(self, curve_type: str, method_id: str) -> BaseMethod:
        """获取拟合方法实例

        Args:
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            method_id: 方法唯一标识

        Returns:
            BaseMethod: 方法实例

        Raises:
            ValueError: 方法不存在
            RuntimeError: 方法实例化失败
        """
        if curve_type not in self._methods:
            raise ValueError(f"曲线类型不存在: {curve_type}")
        if method_id not in self._methods[curve_type]:
            raise ValueError(f"方法不存在: {curve_type}/{method_id}")

        try:
            method_class = self._methods[curve_type][method_id]
            method_name = self._method_metadata[curve_type][method_id]["method_name"]
            return method_class(method_name=method_name, method_id=method_id)
        except Exception as e:
            raise RuntimeError(
                f"方法实例化失败: {curve_type}/{method_id}, 原因: {str(e)}"
            ) from e

    def select_best_method(
        self,
        device_id: int,
        curve_type: str,
        data: pd.DataFrame,
        available_columns: List[str],
    ) -> str:
        """自动选择最佳拟合方法

        选择逻辑：
        1. 过滤满足依赖条件的方法
        2. 过滤满足数据量要求的方法
        3. 按优先级排序
        4. 返回最高优先级方法

        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            data: 输入数据
            available_columns: 可用数据列

        Returns:
            str: 选中的方法ID

        Raises:
            ValueError: 无适用方法
        """
        if curve_type not in self._methods:
            raise ValueError(f"曲线类型不存在: {curve_type}")

        data_points = len(data)
        candidates: List[tuple[int, str]] = []  # (priority, method_id)

        for method_id, metadata in self._method_metadata[curve_type].items():
            # 检查依赖条件
            dependencies = metadata.get("dependencies", [])
            if dependencies and not all(dep in available_columns for dep in dependencies):
                continue

            # 检查数据量要求
            conditions = metadata.get("applicable_conditions", {})
            min_points = conditions.get("min_data_points", 50)
            if data_points < min_points:
                continue

            # 添加到候选列表
            candidates.append((metadata["priority"], method_id))

        if not candidates:
            raise ValueError(
                f"无适用方法: 曲线类型={curve_type}, 数据点数={data_points}"
            )

        # 按优先级降序排序，返回最高优先级方法
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def list_methods(self, curve_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有已注册方法

        Args:
            curve_type: 曲线类型（可选，为None时返回所有类型）

        Returns:
            List[Dict]: 方法信息列表
        """
        result: List[Dict[str, Any]] = []

        if curve_type is not None:
            if curve_type not in self._method_metadata:
                return result
            for method_id, metadata in self._method_metadata[curve_type].items():
                result.append(
                    {
                        "curve_type": curve_type,
                        "method_id": method_id,
                        **metadata,
                    }
                )
        else:
            for ct, methods in self._method_metadata.items():
                for method_id, metadata in methods.items():
                    result.append(
                        {
                            "curve_type": ct,
                            "method_id": method_id,
                            **metadata,
                        }
                    )

        return result

    def get_recommended_method(
        self, curve_type: str, method_recommendations: Dict[str, str]
    ) -> str:
        """获取曲线类型的推荐方法

        ⚠️ 注意：推荐方法必须从数据库读取，禁止硬编码默认值

        Args:
            curve_type: 曲线类型
            method_recommendations: 方法推荐配置（从数据库读取）
                格式: {'qh': 'method_id', 'qp': 'method_id', 'qeta': 'method_id'}

        Returns:
            str: 推荐方法ID

        Raises:
            ValueError: 如果数据库中未配置该曲线类型的推荐方法
        """
        if curve_type not in method_recommendations:
            raise ValueError(f"数据库中未配置曲线类型 {curve_type} 的推荐方法")
        return method_recommendations[curve_type]

    def get_benchmark(self, method_id: str) -> Optional[MethodBenchmark]:
        """获取方法性能基准数据

        Args:
            method_id: 方法ID

        Returns:
            MethodBenchmark: 性能基准数据，不存在时返回None
        """
        return self._method_benchmarks.get(method_id)

