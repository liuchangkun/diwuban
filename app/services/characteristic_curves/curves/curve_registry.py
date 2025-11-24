"""
曲线注册器 (app.services.characteristic_curves.curves.curve_registry)

曲线类型的注册和获取。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/03_核心模块/03_共用层.md 第8节
"""

import logging
from typing import Dict, List, Optional, Type

from app.services.characteristic_curves.curves.base_curve import BaseCurve, CurveType


class CurveRegistry:
    """曲线注册器（单例模式）

    管理所有曲线类型的注册和获取。

    使用方式:
        registry = get_curve_registry()
        registry.register('qh', QHCurve)
        curve = registry.get_curve('qh')
    """

    _instance: "CurveRegistry" = None

    def __new__(cls) -> "CurveRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._registry: Dict[str, Type[BaseCurve]] = {}
        self._instances: Dict[str, BaseCurve] = {}
        self._initialized = True

    def register(self, curve_type: str, curve_class: Type[BaseCurve]) -> None:
        """注册曲线类型

        Args:
            curve_type: 曲线类型标识 (qh, qp, qeta, etc.)
            curve_class: 曲线类
        """
        curve_type_lower = curve_type.lower()
        self._registry[curve_type_lower] = curve_class
        self._logger.info(f"注册曲线类型: {curve_type_lower} -> {curve_class.__name__}")

    def get_curve(self, curve_type: str) -> Optional[BaseCurve]:
        """获取曲线处理器实例

        Args:
            curve_type: 曲线类型标识

        Returns:
            BaseCurve: 曲线处理器实例，如果未注册返回None
        """
        curve_type_lower = curve_type.lower()

        # 检查缓存
        if curve_type_lower in self._instances:
            return self._instances[curve_type_lower]

        # 创建新实例
        if curve_type_lower in self._registry:
            curve_class = self._registry[curve_type_lower]
            instance = curve_class()
            self._instances[curve_type_lower] = instance
            return instance

        self._logger.warning(f"未找到曲线类型: {curve_type}")
        return None

    def get_curve_class(self, curve_type: str) -> Optional[Type[BaseCurve]]:
        """获取曲线类（不创建实例）"""
        return self._registry.get(curve_type.lower())

    def list_curves(self) -> List[str]:
        """列出所有已注册的曲线类型"""
        return list(self._registry.keys())

    def is_registered(self, curve_type: str) -> bool:
        """检查曲线类型是否已注册"""
        return curve_type.lower() in self._registry

    def unregister(self, curve_type: str) -> bool:
        """注销曲线类型"""
        curve_type_lower = curve_type.lower()
        if curve_type_lower in self._registry:
            del self._registry[curve_type_lower]
            self._instances.pop(curve_type_lower, None)
            return True
        return False

    def get_info(self, curve_type: str) -> Optional[Dict[str, any]]:
        """获取曲线类型信息"""
        curve_type_lower = curve_type.lower()
        if curve_type_lower not in self._registry:
            return None

        curve_class = self._registry[curve_type_lower]
        return {
            "curve_type": curve_type_lower,
            "class_name": curve_class.__name__,
            "monotonicity": getattr(curve_class, "monotonicity", None),
            "recommended_methods": getattr(curve_class, "recommended_methods", []),
        }

    def clear(self) -> None:
        """清除所有注册（主要用于测试）"""
        self._registry.clear()
        self._instances.clear()


# 单例获取函数
_registry_instance: CurveRegistry = None


def get_curve_registry() -> CurveRegistry:
    """获取曲线注册器单例"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = CurveRegistry()
    return _registry_instance

