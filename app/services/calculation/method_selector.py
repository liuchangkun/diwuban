"""
MethodSelector - 计算方法选择器

根据可用数据和条件选择最合适的计算方法。

核心功能:
1. 检查方法的依赖是否满足
2. 检查方法的条件是否满足
3. 按优先级选择最佳方法

使用示例:
    from app.services.calculation.method_selector import MethodSelector

    selector = MethodSelector()
    method = selector.select_method(
        metric_key='pump_flow_rate',
        available_metrics=['main_pipeline_flow_rate', 'pump_active_power', 'pump_frequency'],
        context={'running_count': 2}
    )
    # 返回: {'method_id': 'pump_flow_rate_method_a', 'method_code': 'A', ...}
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from app.adapters.db import get_connection

from app.services.calculation.domain import CalculationContext, MethodDescriptor

logger = logging.getLogger(__name__)


class MethodSelector:
    """
    计算方法选择器

    根据可用数据和条件选择最合适的计算方法。

    Attributes:
        _method_registry: 计算方法注册表（从数据库加载）
    """

    def __init__(self):
        """初始化方法选择器"""
        logger.info("[流程-开始] [方法选择器初始化]")

        self._method_registry: Dict[str, List[Dict]] = {}
        self._load_methods_from_db()
        logger.info("[核心-初始化] MethodSelector 初始化完成")

    def _load_methods_from_db(self) -> None:
        """从数据库加载计算方法注册表"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT
                            method_id, metric_key, method_name, method_code,
                            priority, dependencies, conditions, accuracy_level, is_enabled,
                            COALESCE(allowed_device_types, '{}'::text[]) AS allowed_device_types
                        FROM calculation_method_registry
                        WHERE is_enabled = TRUE
                        ORDER BY metric_key, priority DESC
                    """
                    cur.execute(query)
                    rows = cur.fetchall()

                    # 按metric_key分组
                    for row in rows:
                        (method_id, metric_key, method_name, method_code,
                         priority, dependencies, conditions, accuracy_level, is_enabled, allowed_device_types) = row

                        if metric_key not in self._method_registry:
                            self._method_registry[metric_key] = []

                        self._method_registry[metric_key].append({
                            'method_id': method_id,
                            'metric_key': metric_key,
                            'method_name': method_name,
                            'method_code': method_code,
                            'priority': priority,
                            'dependencies': dependencies or [],
                            'conditions': conditions or {},
                            'accuracy_level': accuracy_level,
                            'allowed_device_types': list(allowed_device_types or [])
                        })

                    logger.info(
                        f"MethodSelector 加载完成：{len(self._method_registry)} 个指标的方法",
                        extra={"extra_data": {"metric_count": len(self._method_registry)}}
                    )
        except Exception as e:
            logger.error(f"MethodSelector 加载失败: {e}", exc_info=True)
            raise

    def get_union_dependencies(self, metric_key: str) -> List[str]:
        """返回该指标所有启用方法的依赖项并集（去重后按字母排序）。"""
        methods = self._method_registry.get(metric_key, [])
        deps: set[str] = set()
        for m in methods:
            for d in m.get('dependencies', []) or []:
                deps.add(d)
        return sorted(deps)

    def check_dependencies(
        self,
        dependencies: List[str],
        available_metrics: List[str],
        data: Optional[Dict[str, np.ndarray]] = None
    ) -> bool:
        """
        检查依赖是否满足

        Args:
            dependencies: 方法所需的依赖指标列表
            available_metrics: 可用的指标列表
            data: 可选的数据字典，用于检查数据有效性

        Returns:
            True 如果所有依赖都满足，否则 False

        Example:
            >>> selector.check_dependencies(
            ...     ['pump_active_power', 'pump_frequency'],
            ...     ['pump_active_power', 'pump_frequency', 'pump_inlet_pressure']
            ... )
            True
        """
        # 步骤1：检查依赖指标是否在可用列表中
        available_set = set(available_metrics)
        if not all(dep in available_set for dep in dependencies):
            return False

        # 步骤2：如果提供了data，检查数据有效性
        if data is not None:
            for dep in dependencies:
                if dep not in data:
                    logger.debug(f"依赖指标 {dep} 不在数据字典中")
                    return False

                dep_data = data[dep]

                # 检查数据长度
                if len(dep_data) == 0:
                    logger.debug(f"依赖指标 {dep} 的数据为空")
                    return False

                # 检查是否至少有一个非NaN值
                valid_mask = ~np.isnan(dep_data)
                valid_count = np.sum(valid_mask)
                if valid_count == 0:
                    logger.debug(f"依赖指标 {dep} 的所有数据都是NaN")
                    return False

                # 对于特定指标，检查是否有非零值（频率、功率等）
                # 如果指标名称包含frequency、power、flow等关键词，检查是否有非零值
                if any(keyword in dep.lower() for keyword in ['frequency', 'power', 'flow']):
                    valid_data = dep_data[valid_mask]
                    non_zero_count = np.sum(valid_data > 0)
                    if non_zero_count == 0:
                        logger.debug(f"依赖指标 {dep} 的所有有效数据都是0或负数")
                        return False

        return True

    def check_conditions(
        self,
        conditions: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """
        检查条件是否满足

        Args:
            conditions: 方法所需的条件字典
            context: 当前上下文字典

        Returns:
            True 如果所有条件都满足，否则 False

        Example:
            >>> selector.check_conditions(
            ...     {'running_count': {'exact': 1}},
            ...     {'running_count': 1}
            ... )
            True
        """
        if not conditions:
            return True

        for key, value in conditions.items():
            # 跳过描述性字段
            if key in ['description', 'note', 'comment']:
                continue

            # 跳过数值型计算参数（这些参数应该从 calculation_parameters 表读取，不是条件）
            # 注意：bool 是 int 的子类，所以需要排除 bool
            # 保留 min_running_pumps 和 max_running_pumps 的检查
            if isinstance(value, (int, float)) and not isinstance(value, bool) and key not in ['min_running_pumps', 'max_running_pumps']:
                continue

            # 处理特殊的布尔条件（如 requires_cumulative_flow, requires_training）
            if key.startswith('requires_') or key.startswith('has_'):
                # 这些条件需要在context中明确设置为True
                if not context.get(key, False):
                    return False
                continue

            # 处理 min_running_pumps 条件
            if key == 'min_running_pumps':
                running_count = context.get('running_count', 0)
                if running_count < value:
                    return False
                continue

            # 处理 max_running_pumps 条件
            if key == 'max_running_pumps':
                running_count = context.get('running_count', 0)
                if running_count > value:
                    return False
                continue

            # 处理其他条件
            if key not in context:
                return False

            context_value = context[key]

            # 处理不同类型的条件
            if isinstance(value, dict):
                # 复杂条件（如 {'exact': 1}, {'min': 2}, {'max': 10}）
                if 'exact' in value:
                    if context_value != value['exact']:
                        return False
                if 'min' in value:
                    if context_value < value['min']:
                        return False
                if 'max' in value:
                    if context_value > value['max']:
                        return False
            else:
                # 简单条件（直接比较）
                if context_value != value:
                    return False

        return True

    def select_method(
        self,
        metric_key: str,
        available_metrics: List[str],
        context: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, np.ndarray]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        选择最合适的计算方法

        按优先级从高到低遍历所有方法，选择第一个满足依赖和条件的方法。

        Args:
            metric_key: 需要计算的指标键
            available_metrics: 可用的指标列表
            context: 上下文字典（用于条件检查）
            data: 可选的数据字典，用于检查依赖数据的有效性

        Returns:
            选中的方法字典，如果没有合适的方法则返回 None

        Example:
            >>> method = selector.select_method(
            ...     'pump_flow_rate',
            ...     ['main_pipeline_flow_rate', 'pump_active_power', 'pump_frequency'],
            ...     {'running_count': 2}
            ... )
            >>> print(method['method_code'])
            'A'
        """
        logger.info(
            "[流程-开始] [方法选择]",
            extra={
                "extra_data": {
                    "metric_key": metric_key,
                    "available_metrics_count": len(available_metrics) if available_metrics else 0,
                }
            },
        )

        if context is None:
            context = {}

        if metric_key not in self._method_registry:
            logger.warning(
                f"指标 {metric_key} 没有注册的计算方法",
                extra={
                    "extra_data": {
                        "指标键": metric_key,
                        "泵站ID": context.get("station_id"),
                        "设备ID": context.get("device_id"),
                        "开始时间": context.get("start_ts"),
                        "结束时间": context.get("end_ts"),
                    }
                },
            )
            return None

        methods = self._method_registry[metric_key]

        for method in methods:
            # 设备类型适配性预检（若提供 device_type，则需命中 allowed_device_types）
            device_type = (context or {}).get('device_type') if context is not None else None
            allowed_types = method.get('allowed_device_types') or []
            if device_type and allowed_types and device_type not in allowed_types:
                logger.debug(
                    f"方法 {method['method_code']} 不适用于设备类型 {device_type}，允许: {allowed_types}"
                )
                continue

            # 检查依赖（包括数据有效性检查）
            if not self.check_dependencies(method['dependencies'], available_metrics, data):
                # 根据是否提供data，输出不同的日志信息
                if data is not None:
                    missing = [d for d in (method.get('dependencies') or []) if d not in (available_metrics or [])]
                    logger.info(
                        f"方法 {method['method_code']} 因依赖数据无效被跳过: 需要 {method['dependencies']}",
                        extra={
                            "extra_data": {
                                "泵站ID": context.get("station_id"),
                                "设备ID": context.get("device_id"),
                                "指标键": metric_key,
                                "方法名称": method.get("method_name") or method.get("method_id") or method.get("method_code"),
                                "开始时间": context.get("start_ts") or context.get("start_time"),
                                "结束时间": context.get("end_ts") or context.get("end_time"),
                                "可用指标": list(available_metrics or []),
                                "缺失依赖": missing,
                            }
                        }
                    )
                else:
                    logger.debug(
                        f"方法 {method['method_code']} 依赖不满足: "
                        f"需要 {method['dependencies']}, 可用 {available_metrics}"
                    )
                continue

            # 检查条件
            if not self.check_conditions(method['conditions'], context):
                logger.debug(
                    f"方法 {method['method_code']} 条件不满足: "
                    f"需要 {method['conditions']}, 上下文 {context}"
                )
                continue

            # 找到合适的方法
            logger.info(
                f"为指标 {metric_key} 选择方法 {method['method_code']} (优先级: {method['priority']}, 精度: {method['accuracy_level']})",
                extra={
                    "extra_data": {
                        "泵站ID": context.get("station_id"),
                        "设备ID": context.get("device_id"),
                        "指标键": metric_key,
                        "方法名称": method.get("method_name") or method.get("method_id") or method.get("method_code"),
                        "priority": method.get("priority"),
                        "accuracy_level": method.get("accuracy_level"),
                        "开始时间": context.get("start_ts") or context.get("start_time"),
                        "结束时间": context.get("end_ts") or context.get("end_time"),
                        "可用指标": list(available_metrics or []),
                    }
                }
            )
            return method

        # 没有找到合适的方法
        logger.warning(
            f"为指标 {metric_key} 未找到合适的方法 (可用指标: {available_metrics})",
            extra={
                "extra_data": {
                    "\u6cf5\u7ad9ID": context.get("station_id"),
                    "\u8bbe\u5907ID": context.get("device_id"),
                    "\u6307\u6807\u952e": metric_key,
                    "\u5f00\u59cb\u65f6\u95f4": context.get("start_ts") or context.get("start_time"),
                    "\u7ed3\u675f\u65f6\u95f4": context.get("end_ts") or context.get("end_time"),
                    "\u53ef\u7528\u6307\u6807": list(available_metrics or []),
                }
            }
        )
        return None

    def select_methods_batch(
        self,
        metric_keys: List[str],
        available_metrics: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        批量选择计算方法

        Args:
            metric_keys: 需要计算的指标键列表
            available_metrics: 可用的指标列表
            context: 上下文字典（用于条件检查）

        Returns:
            指标键到方法字典的映射

        Example:
            >>> methods = selector.select_methods_batch(
            ...     ['pump_flow_rate', 'pump_head'],
            ...     ['main_pipeline_flow_rate', 'pump_active_power', 'pump_frequency', 'pump_outlet_pressure'],
            ...     {'running_count': 2}
            ... )
            >>> print(methods['pump_flow_rate']['method_code'])
            'A'
        """
        result = {}
        for metric_key in metric_keys:
            result[metric_key] = self.select_method(metric_key, available_metrics, context)
        return result

    # ------------------------- 统一签名适配层（保持向后兼容） -------------------------
    def select_method_ctx(
        self,
        ctx: CalculationContext,
        metric_key: str,
        available_metrics: List[str],
        data: Optional[Dict[str, np.ndarray]] = None,
    ) -> Optional[MethodDescriptor]:
        """
        基于统一领域上下文的选择方法（不移除旧路径，内部适配为原有字典风格）。

        Args:
            ctx: 统一的 CalculationContext
            metric_key: 指标键
            available_metrics: 可用指标列表
            data: 可选的数据字典

        Returns:
            MethodDescriptor 或 None
        """
        # 将上下文适配为旧版字典语义（保留最常用键，附带 quality_filters/extra）
        legacy_context: Dict[str, Any] = {
            "station_id": ctx.station_id,
            "device_id": ctx.device_id,
            "strict_mode": ctx.strict_mode,
        }
        # 合并质量过滤与其他上下文扩展（避免覆盖核心键）
        for src in (ctx.quality_filters or {}, ctx.extra or {}):
            for k, v in src.items():
                if k not in legacy_context:
                    legacy_context[k] = v

        # 透传时间窗口到日志上下文（用于方法未注册/未选中时补充定位信息）
        if getattr(ctx, "start_ts", None) is not None:
            legacy_context["start_ts"] = ctx.start_ts
        if getattr(ctx, "end_ts", None) is not None:
            legacy_context["end_ts"] = ctx.end_ts

        method_dict = self.select_method(metric_key, available_metrics, legacy_context, data)
        if method_dict is None:
            return None

        # 映射为统一的 MethodDescriptor（仅字段对齐，无语义变更）
        return MethodDescriptor(
            method_id=method_dict.get("method_id"),
            method_code=method_dict.get("method_code"),
            metric_key=method_dict.get("metric_key", metric_key),
            priority=int(method_dict.get("priority", 0)),
            dependencies=list(method_dict.get("dependencies", [])),
            conditions=dict(method_dict.get("conditions", {})),
            params={},  # 具体参数在执行阶段由参数管理装配
            validator_hint=None,
        )

    def get_all_methods(self, metric_key: str) -> List[Dict[str, Any]]:
        """
        获取指定指标的所有方法

        Args:
            metric_key: 指标键

        Returns:
            方法列表（按优先级降序）
        """
        return self._method_registry.get(metric_key, [])

    def refresh(self) -> None:
        """刷新方法注册表"""
        logger.info("MethodSelector 刷新")
        self._method_registry.clear()
        self._load_methods_from_db()

