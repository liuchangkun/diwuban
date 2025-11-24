"""
参数管理器 (app.services.characteristic_curves.shared.parameter_manager)

统一管理曲线拟合和约束的参数配置。

版本: v1.0
更新日期: 2025-12-08
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ParameterConfig:
    """参数配置

    Attributes:
        name: 参数名称
        value: 参数值
        default: 默认值
        min_value: 最小值
        max_value: 最大值
        description: 参数描述
    """

    name: str
    value: Any
    default: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: str = ""

    def validate(self) -> bool:
        """验证参数值是否在范围内"""
        if self.min_value is not None and self.value < self.min_value:
            return False
        if self.max_value is not None and self.value > self.max_value:
            return False
        return True


class ParameterManager:
    """参数管理器

    统一管理各模块的参数配置，支持参数验证和默认值设置。

    使用方式:
        manager = ParameterManager()
        manager.set('qh.polynomial.degree', 3)
        degree = manager.get('qh.polynomial.degree')
    """

    def __init__(self) -> None:
        """初始化参数管理器"""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._parameters: Dict[str, ParameterConfig] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """加载默认参数配置"""
        defaults = {
            # 多项式拟合参数
            "polynomial.degree": (3, 1, 10, "多项式阶数"),
            "polynomial.regularization": (0.01, 0.0, 1.0, "正则化系数"),
            # 样条拟合参数
            "spline.smoothing": (0.1, 0.0, 1.0, "平滑因子"),
            "spline.degree": (3, 1, 5, "样条阶数"),
            # 约束参数
            "constraint.tolerance": (0.01, 0.0, 0.1, "约束容差"),
            "constraint.max_iterations": (100, 10, 1000, "最大迭代次数"),
            # 预处理参数
            "preprocessing.outlier_threshold": (1.5, 1.0, 3.0, "异常值阈值(IQR倍数)"),
            "preprocessing.min_points": (10, 5, 100, "最小数据点数"),
        }

        for name, (default, min_val, max_val, desc) in defaults.items():
            self._parameters[name] = ParameterConfig(
                name=name,
                value=default,
                default=default,
                min_value=min_val,
                max_value=max_val,
                description=desc,
            )

    def set(self, name: str, value: Any) -> bool:
        """设置参数值

        Args:
            name: 参数名称
            value: 参数值

        Returns:
            bool: 是否设置成功
        """
        if name in self._parameters:
            config = self._parameters[name]
            old_value = config.value
            config.value = value
            if not config.validate():
                config.value = old_value
                self._logger.warning(f"参数 {name}={value} 超出范围")
                return False
            self._logger.debug(f"设置参数 {name}={value}")
            return True
        else:
            # 创建新参数
            self._parameters[name] = ParameterConfig(name=name, value=value, default=value)
            return True

    def get(self, name: str, default: Any = None) -> Any:
        """获取参数值"""
        if name in self._parameters:
            return self._parameters[name].value
        return default

    def reset(self, name: str) -> bool:
        """重置参数为默认值"""
        if name in self._parameters:
            config = self._parameters[name]
            config.value = config.default
            return True
        return False

    def reset_all(self) -> None:
        """重置所有参数为默认值"""
        for config in self._parameters.values():
            config.value = config.default

    def get_all(self) -> Dict[str, Any]:
        """获取所有参数"""
        return {name: config.value for name, config in self._parameters.items()}

    def get_config(self, name: str) -> Optional[ParameterConfig]:
        """获取参数配置"""
        return self._parameters.get(name)

    def list_parameters(self) -> List[str]:
        """列出所有参数名称"""
        return list(self._parameters.keys())


# 单例实例
_manager_instance: ParameterManager = None


def get_parameter_manager() -> ParameterManager:
    """获取参数管理器单例"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ParameterManager()
    return _manager_instance

