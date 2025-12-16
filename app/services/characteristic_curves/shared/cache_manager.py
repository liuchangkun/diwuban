"""
缓存管理器 (app.services.characteristic_curves.shared.cache_manager)

本模块提供内存LRU缓存功能：
- 单例模式：全局唯一实例
- 线程安全：使用RLock保护缓存操作
- 自动过期：支持TTL过期机制
- LRU淘汰：超过最大容量时淘汰最久未使用的条目

使用方式：
    from app.services.characteristic_curves.shared import CacheManager
    
    cache = CacheManager(max_size=1000, ttl_seconds=3600)
    cache.set("key", value)
    result = cache.get("key")
"""

import fnmatch
import logging
import threading
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class CacheManager:
    """缓存管理器（单例模式 + LRU缓存）
    
    线程安全说明：
    - 使用 threading.Lock() 保护单例创建过程
    - 使用 threading.RLock() 保护缓存读写操作
    - 所有公共方法都是线程安全的
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, max_size: int = 1000, ttl_seconds: int = 3600):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """初始化缓存管理器
        
        Args:
            max_size: 最大缓存条目数
            ttl_seconds: 缓存过期时间（秒）
        """
        if getattr(self, '_initialized', False):
            return
            
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._stats = {'hits': 0, 'misses': 0, 'evictions': 0}
        self._cache_lock = threading.RLock()
        self._initialized = True
        
        self._logger.info(
            "[缓存] 初始化",
            extra={"extra_data": {
                "组件": "CacheManager",
                "最大缓存条目": max_size,
                "默认过期时间秒": ttl_seconds
            }}
        )

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            Any: 缓存值，不存在或已过期则返回None
        """
        with self._cache_lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            entry = self._cache[key]
            if datetime.now() > entry['expires_at']:
                # 已过期，删除并返回None
                del self._cache[key]
                self._stats['misses'] += 1
                return None
            
            # 命中，移动到末尾（LRU）
            self._cache.move_to_end(key)
            self._stats['hits'] += 1
            return entry['value']

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl_seconds: 过期时间（可选，不指定则使用默认值）
        """
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl_seconds
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        with self._cache_lock:
            # 如果键已存在，先删除
            if key in self._cache:
                del self._cache[key]
            
            # 检查容量，必要时淘汰
            while len(self._cache) >= self._max_size:
                # 淘汰最久未使用的（OrderedDict的第一个）
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats['evictions'] += 1
            
            # 添加新条目
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': datetime.now()
            }

    def delete(self, key: str) -> bool:
        """删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 是否删除成功
        """
        with self._cache_lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self, pattern: Optional[str] = None) -> int:
        """清空缓存

        Args:
            pattern: 键模式（可选，支持通配符*）

        Returns:
            int: 清除的条目数
        """
        with self._cache_lock:
            if pattern is None:
                count = len(self._cache)
                self._cache.clear()
                return count

            # 按模式匹配删除
            keys_to_delete = [
                k for k in self._cache.keys()
                if fnmatch.fnmatch(k, pattern)
            ]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            Dict: 包含命中率、缓存大小等统计信息
        """
        with self._cache_lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (
                self._stats['hits'] / total_requests
                if total_requests > 0 else 0.0
            )

            return {
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'hit_rate': round(hit_rate, 4),
                'size': len(self._cache),
                'max_size': self._max_size,
                'ttl_seconds': self._ttl_seconds
            }

    def build_key(
        self,
        device_id: int,
        curve_type: str,
        method_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """构建缓存键

        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            method_id: 方法ID（可选）
            **kwargs: 其他键值对

        Returns:
            str: 缓存键，格式为 "device_id:curve_type:method_id:key1=value1:..."
        """
        parts = [str(device_id), curve_type]
        if method_id:
            parts.append(method_id)
        for k, v in sorted(kwargs.items()):
            parts.append(f"{k}={v}")
        return ":".join(parts)

    def invalidate_on_save(
        self,
        device_id: int,
        curve_type: str,
        method_id: Optional[str] = None
    ) -> int:
        """保存操作后的缓存失效同步

        在 ResultStorage.save() 成功后调用此方法，确保缓存与数据库一致。

        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            method_id: 方法ID（可选）

        Returns:
            int: 清除的缓存条目数
        """
        if method_id:
            pattern = f"{device_id}:{curve_type}:{method_id}:*"
        else:
            pattern = f"{device_id}:{curve_type}:*"

        count = self.clear(pattern)

        if count > 0:
            self._logger.info(
                "[缓存] 保存后失效同步",
                extra={"extra_data": {
                    "设备ID": device_id,
                    "曲线类型": curve_type,
                    "方法ID": method_id,
                    "清除条目数": count
                }}
            )

        return count

    def reset_stats(self) -> None:
        """重置统计信息"""
        with self._cache_lock:
            self._stats = {'hits': 0, 'misses': 0, 'evictions': 0}
