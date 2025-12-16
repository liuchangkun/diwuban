"""
参数管理器（ParameterManager）

职责：
- 从数据库加载参数配置
- 参数缓存和更新
- 三级参数合并（全局 → 泵站 → 设备）
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.logging.setup import log_activity


class ParameterManager:
    """
    参数管理器（单例）

    职责：
    - 从数据库加载参数配置
    - 参数缓存和更新
    - 三级参数合并（全局 → 泵站 → 设备）
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化参数管理器"""
        if hasattr(self, '_initialized'):
            return

        self.cache: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
        self._initialized = True

        # 默认参数配置
        self.default_params = {
            'pump_flow_rate': {
                'method_a': {'alpha': 1.0, 'beta': 1.0},
                'method_b': {'smooth_window': 5},
                'method_c': {},
                'method_d': {'alpha': 1.0},
                'method_e': {'beta': 1.0},
                'method_f': {'model_type': 'linear', 'min_samples': 100},
                'global': {
                    'max_flow': 500.0,
                    'max_power': 200.0,
                    'max_freq': 50.0
                }
            }
        }

    def get_parameters(
        self,
        metric_key: str,
        method_id: Optional[str] = None,  # 保留参数以兼容旧代码，但不再使用
        station_id: Optional[int] = None,
        device_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取参数配置（三级合并：全局 → 泵站 → 设备）

        Args:
            metric_key: 指标键
            method_id: 已废弃，保留以兼容旧代码
            station_id: 泵站ID（可选）
            device_id: 设备ID（可选）

        Returns:
            参数字典
        """
        # 构造缓存键（不再包含method_id）
        cache_key = f"{metric_key}:{station_id}:{device_id}"

        # 检查缓存
        if cache_key in self.cache:
            # 增强日志：缓存命中
            cache_hit_rate = len(self.cache) / (len(self.cache) + 1) * 100  # 简化的命中率计算
            self.logger.debug(
                f"[参数管理] 参数缓存命中",
                extra={'extra_data': {
                    '指标键': metric_key,
                    '泵站ID': station_id,
                    '设备ID': device_id,
                    '来自缓存': True,
                    '缓存大小': len(self.cache),
                    '缓存命中率': f"{cache_hit_rate:.1f}%"
                }}
            )
            return self.cache[cache_key].copy()

        # 从数据库加载参数（带详细日志）
        params, param_sources = self._load_params_from_db_with_sources(metric_key, station_id, device_id)

        # 如果数据库没有参数，记录错误并抛出异常（禁止使用默认值）
        if not params:
            # 尝试使用默认值（仅用于错误日志）
            default_params = self._get_default_params(metric_key)

            # 记录错误日志
            self.logger.error(
                f"[参数管理] 数据库中无参数配置，禁止使用默认值",
                extra={'extra_data': {
                    '指标键': metric_key,
                    '泵站ID': station_id,
                    '设备ID': device_id,
                    '缺失参数': list(default_params.keys()) if default_params else '未知',
                    '错误': '必须在calculation_parameters表中配置参数'
                }}
            )

            # 抛出异常，终止执行
            raise ValueError(
                f"参数加载失败: metric_key={metric_key}, "
                f"station_id={station_id}, device_id={device_id}. "
                f"数据库中无参数配置，必须在calculation_parameters表中添加参数。"
            )

        # 缓存
        self.cache[cache_key] = params.copy()

        # 增强日志：包含参数来源层级
        self.logger.info(
            f"[参数管理] 加载参数",
            extra={'extra_data': {
                '指标键': metric_key,
                '泵站ID': station_id,
                '设备ID': device_id,
                '最终参数': params,
                '参数来源': param_sources,
                '来自缓存': False,
                '缓存大小': len(self.cache)
            }}
        )

        return params

    def _load_params_from_db_with_sources(
        self,
        metric_key: str,
        station_id: Optional[int],
        device_id: Optional[int]
    ) -> tuple[Dict[str, Any], Dict[str, str]]:
        """
        从数据库加载参数（三级优先级：设备 > 泵站 > 全局），并返回参数来源

        Args:
            metric_key: 指标键
            station_id: 泵站ID
            device_id: 设备ID

        Returns:
            (参数字典, 参数来源字典)
        """
        from app.adapters.db.pool import get_connection

        # SQL 查询（不再使用method_id）
        sql = """
            WITH param_hierarchy AS (
                SELECT
                    param_name,
                    param_value,
                    CASE
                        WHEN device_id IS NOT NULL THEN 1  -- 设备级
                        WHEN station_id IS NOT NULL THEN 2  -- 泵站级
                        ELSE 3  -- 全局级
                    END AS priority,
                    CASE
                        WHEN device_id IS NOT NULL THEN 'device'
                        WHEN station_id IS NOT NULL THEN 'station'
                        ELSE 'global'
                    END AS source_level
                FROM calculation_parameters
                WHERE metric_key = %s
                  AND (
                      (station_id = %s AND device_id = %s) OR  -- 设备级
                      (station_id = %s AND device_id IS NULL) OR  -- 泵站级
                      (station_id IS NULL AND device_id IS NULL)  -- 全局级
                  )
            )
            SELECT DISTINCT ON (param_name) param_name, param_value, source_level
            FROM param_hierarchy
            ORDER BY param_name, priority
        """
        query_params = [metric_key, station_id, device_id, station_id]

        try:
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, query_params)
                    rows = cursor.fetchall()

            # 转换为字典（修复：使用 is not None 而不是 if row[1]，避免0.0被转换为None）
            params = {row[0]: float(row[1]) if row[1] is not None else None for row in rows}
            param_sources = {row[0]: row[2] for row in rows}

            # 按来源层级分组参数
            global_params = {k: v for k, v in params.items() if param_sources.get(k) == 'global'}
            station_params = {k: v for k, v in params.items() if param_sources.get(k) == 'station'}
            device_params = {k: v for k, v in params.items() if param_sources.get(k) == 'device'}

            # 增强日志：输出参数合并过程
            self.logger.info(
                f"[参数管理] 参数合并过程",
                extra={'extra_data': {
                    '指标键': metric_key,
                    '泵站ID': station_id,
                    '设备ID': device_id,
                    '全局参数': global_params,
                    '泵站参数覆盖': station_params,
                    '设备参数覆盖': device_params,
                    '最终参数': params,
                    '参数总数': len(params)
                }}
            )

            return params, param_sources

        except Exception as e:
            self.logger.error(
                f"[参数管理] 从数据库加载参数失败: {str(e)}",
                extra={'extra_data': {
                    '指标键': metric_key,
                    '错误信息': str(e)
                }}
            )
            return {}, {}

    def _get_default_params(self, metric_key: str) -> Dict[str, Any]:
        """
        获取默认参数

        Args:
            metric_key: 指标键

        Returns:
            默认参数字典
        """
        if metric_key not in self.default_params:
            return {}

        return self.default_params[metric_key].get('global', {}).copy()

    def update_params(
        self,
        metric_key: str,
        method_id: str,
        params: Dict[str, Any],
        station_id: Optional[int] = None,
        device_id: Optional[int] = None
    ):
        """
        更新参数（写入数据库并清除缓存）

        Args:
            metric_key: 指标键
            method_id: 方法ID
            params: 参数字典
            station_id: 泵站ID
            device_id: 设备ID
        """
        from app.adapters.db.pool import get_connection

        try:
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    for param_name, param_value in params.items():
                        sql = """
                            INSERT INTO calculation_parameters (
                                metric_key, method_id, parameter_name, parameter_value,
                                station_id, device_id
                            )
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (metric_key, method_id, parameter_name, station_id, device_id)
                            DO UPDATE SET
                                parameter_value = EXCLUDED.parameter_value,
                                updated_at = NOW()
                        """

                        cursor.execute(sql, [
                            metric_key, method_id, param_name, param_value,
                            station_id, device_id
                        ])

                    conn.commit()

            # 清除缓存
            self.clear_cache()

            self.logger(
                f"[参数管理] 更新参数",
                extra={'extra_data': {
                    '指标键': metric_key,
                    '方法ID': method_id,
                    '最终参数': params,
                    '泵站ID': station_id,
                    '设备ID': device_id
                }}
            )

        except Exception as e:
            self.logger(
                f"[参数管理] 更新参数失败: {str(e)}",
                extra={'extra_data': {
                    '指标键': metric_key,
                    '方法ID': method_id,
                    '错误信息': str(e)
                }}
            )
            raise

    def clear_cache(self):
        """清除参数缓存"""
        self.cache.clear()
        self.logger("[参数管理] 缓存已清除")

    def reload_cache(self):
        """重新加载参数缓存"""
        self.clear_cache()
        self.logger("[参数管理] 缓存已重载")

