"""
依赖注入容器 (app.services.characteristic_curves.pipeline.dependency_container)

管理服务的依赖注入和生命周期。

版本: v1.0
更新日期: 2025-12-09
"""

import logging
from typing import Any, Callable, Dict, Optional, Type, TypeVar

T = TypeVar("T")

# 全局单例实例
_container_instance: Optional["DependencyContainer"] = None


class DependencyContainer:
    """依赖注入容器

    提供服务注册、解析和生命周期管理。

    使用方式:
        container = get_container()
        container.register(ServiceClass, instance)
        service = container.resolve(ServiceClass)
    """

    def __init__(self) -> None:
        """初始化容器"""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[[], Any]] = {}
        self._transients: Dict[Type, Type] = {}

    def register_singleton(self, service_type: Type[T], instance: T) -> None:
        """注册单例服务"""
        self._singletons[service_type] = instance
        self._logger.debug(f"注册单例: {service_type.__name__}")

    def register_factory(
        self, service_type: Type[T], factory: Callable[[], T]
    ) -> None:
        """注册工厂方法"""
        self._factories[service_type] = factory
        self._logger.debug(f"注册工厂: {service_type.__name__}")

    def register_transient(
        self, service_type: Type[T], implementation: Type[T]
    ) -> None:
        """注册瞬态服务（每次解析创建新实例）"""
        self._transients[service_type] = implementation
        self._logger.debug(f"注册瞬态: {service_type.__name__}")

    def resolve(self, service_type: Type[T]) -> Optional[T]:
        """解析服务

        优先级: 单例 > 工厂 > 瞬态
        """
        # 检查单例
        if service_type in self._singletons:
            return self._singletons[service_type]

        # 检查工厂
        if service_type in self._factories:
            instance = self._factories[service_type]()
            return instance

        # 检查瞬态
        if service_type in self._transients:
            impl = self._transients[service_type]
            return impl()

        self._logger.warning(f"未找到服务: {service_type.__name__}")
        return None

    def is_registered(self, service_type: Type) -> bool:
        """检查服务是否已注册"""
        return (
            service_type in self._singletons
            or service_type in self._factories
            or service_type in self._transients
        )

    def unregister(self, service_type: Type) -> bool:
        """注销服务"""
        removed = False
        if service_type in self._singletons:
            del self._singletons[service_type]
            removed = True
        if service_type in self._factories:
            del self._factories[service_type]
            removed = True
        if service_type in self._transients:
            del self._transients[service_type]
            removed = True
        return removed

    def clear(self) -> None:
        """清空所有注册"""
        self._singletons.clear()
        self._factories.clear()
        self._transients.clear()
        self._logger.info("容器已清空")

    def create_scope(self) -> "ScopedContainer":
        """创建作用域容器"""
        return ScopedContainer(self)


class ScopedContainer:
    """作用域容器

    继承父容器的注册，但有自己的单例作用域。
    """

    def __init__(self, parent: DependencyContainer) -> None:
        self._parent = parent
        self._scoped_singletons: Dict[Type, Any] = {}

    def resolve(self, service_type: Type[T]) -> Optional[T]:
        """解析服务（优先查找作用域单例）"""
        if service_type in self._scoped_singletons:
            return self._scoped_singletons[service_type]
        return self._parent.resolve(service_type)

    def register_scoped(self, service_type: Type[T], instance: T) -> None:
        """注册作用域单例"""
        self._scoped_singletons[service_type] = instance

    def dispose(self) -> None:
        """释放作用域资源"""
        self._scoped_singletons.clear()


def get_container() -> DependencyContainer:
    """获取全局容器实例（单例）"""
    global _container_instance
    if _container_instance is None:
        _container_instance = DependencyContainer()
    return _container_instance


def reset_container() -> None:
    """重置全局容器"""
    global _container_instance
    if _container_instance:
        _container_instance.clear()
    _container_instance = None

