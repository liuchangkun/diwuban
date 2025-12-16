"""
约束缓存 (app.services.characteristic_curves.constraints.constraint_cache)

缓存约束参数以提高性能。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/03_核心模块/04_约束层.md
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.services.characteristic_curves.shared.cache_manager import CacheManager


@dataclass
class CachedConstraint:
    """缓存的约束参数

    Attributes:
        constraint_type: 约束类型
        parameters: 约束参数
        curve_type: 曲线类型
        device_id: 设备ID
        created_at: 创建时间
        expires_at: 过期时间
        hit_count: 命中次数
    """

    constraint_type: str
    parameters: Dict[str, Any]
    curve_type: str
    device_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    hit_count: int = 0

    def is_expired(self) -> bool:
        """检查是否已过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "constraint_type": self.constraint_type,
            "parameters": self.parameters,
            "curve_type": self.curve_type,
            "device_id": self.device_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "hit_count": self.hit_count,
        }


class ConstraintCache:
    """约束缓存管理器

    与CacheManager集成，提供约束参数的缓存功能。

    Attributes:
        _cache_manager: 缓存管理器实例
        _local_cache: 本地内存缓存
        _default_ttl: 默认过期时间（秒）
    """

    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        default_ttl_seconds: int = 3600,
    ) -> None:
        """初始化约束缓存

        Args:
            cache_manager: 缓存管理器实例
            default_ttl_seconds: 默认过期时间（秒）
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._cache_manager = cache_manager
        self._local_cache: Dict[str, CachedConstraint] = {}
        self._default_ttl = default_ttl_seconds

    def _generate_cache_key(
        self, constraint_type: str, curve_type: str, device_id: Optional[str] = None
    ) -> str:
        """生成缓存键"""
        key_parts = [constraint_type, curve_type]
        if device_id:
            key_parts.append(device_id)
        key_str = ":".join(key_parts)
        return f"constraint:{hashlib.md5(key_str.encode()).hexdigest()[:16]}"

    def get_cached_constraints(
        self, constraint_type: str, curve_type: str, device_id: Optional[str] = None
    ) -> Optional[CachedConstraint]:
        """获取缓存的约束参数

        Args:
            constraint_type: 约束类型
            curve_type: 曲线类型
            device_id: 设备ID

        Returns:
            CachedConstraint: 缓存的约束，如果不存在或已过期则返回None
        """
        cache_key = self._generate_cache_key(constraint_type, curve_type, device_id)

        # 先查本地缓存
        if cache_key in self._local_cache:
            cached = self._local_cache[cache_key]
            if not cached.is_expired():
                cached.hit_count += 1
                return cached
            else:
                del self._local_cache[cache_key]

        return None

    def cache_constraints(
        self,
        constraint_type: str,
        curve_type: str,
        parameters: Dict[str, Any],
        device_id: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> str:
        """缓存约束参数

        Args:
            constraint_type: 约束类型
            curve_type: 曲线类型
            parameters: 约束参数
            device_id: 设备ID
            ttl_seconds: 过期时间（秒）

        Returns:
            str: 缓存键
        """
        cache_key = self._generate_cache_key(constraint_type, curve_type, device_id)
        ttl = ttl_seconds or self._default_ttl

        cached = CachedConstraint(
            constraint_type=constraint_type,
            parameters=parameters,
            curve_type=curve_type,
            device_id=device_id,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=ttl),
        )

        self._local_cache[cache_key] = cached
        self._logger.debug(f"缓存约束: {cache_key}, TTL={ttl}s")

        return cache_key

    def invalidate(
        self, constraint_type: str, curve_type: str, device_id: Optional[str] = None
    ) -> bool:
        """使缓存失效"""
        cache_key = self._generate_cache_key(constraint_type, curve_type, device_id)
        if cache_key in self._local_cache:
            del self._local_cache[cache_key]
            return True
        return False

    def clear_all(self) -> int:
        """清除所有缓存"""
        count = len(self._local_cache)
        self._local_cache.clear()
        return count

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_hits = sum(c.hit_count for c in self._local_cache.values())
        return {
            "total_entries": len(self._local_cache),
            "total_hits": total_hits,
            "expired_count": sum(1 for c in self._local_cache.values() if c.is_expired()),
        }

