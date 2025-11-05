"""
领域模型定义：缺失指标计算的统一上下文与方法描述

本模块仅定义轻量级的领域数据结构，供 orchestrator、method_selector、calculators、validator
等组件在统一签名下协同工作。严格遵循项目规则：
- 中文注释与中文日志信息规范
- Google 风格 docstring
- 单文件行数、函数长度与复杂度控制（本文件仅数据类定义）

作者：AI
最后修改：2025-10-07
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class CalculationContext:
    """计算上下文（统一在各组件之间传递）

    定义一次缺失指标计算在设备/时间窗口/运行态下的公共信息。所有计算、校验、选择
    都应依赖该上下文，避免散落的参数与隐式全局状态。

    Args:
        station_id: 泵站ID。
        device_id: 设备ID。
        start_ts: 计算窗口起始时间（UTC）。
        end_ts: 计算窗口结束时间（UTC）。
        bucket_size_sec: 时间对齐粒度（秒），例如 1 表示秒级对齐。
        run_id: 本次运行/批次的全局唯一标识（用于统计与幂等）。
        batch_no: 当前批次编号（可选，用于性能/监控分段）。
        strict_mode: 严格模式（True 时更严格的校验/过滤策略）。
        quality_filters: 数据质量过滤配置（如 quality_status 白名单等）。
        extra: 其他上下文扩展字段（仅用于非关键控制信息）。
    """

    station_id: int
    device_id: int
    start_ts: datetime
    end_ts: datetime
    bucket_size_sec: int = 1
    run_id: str = ""
    batch_no: Optional[int] = None
    strict_mode: bool = False
    quality_filters: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MethodDescriptor:
    """方法描述（统一方法元数据）

    用于表达“某个 metric 的具体计算方法”与其依赖/条件/参数。MethodSelector 应返回该对象；
    Calculators 接收该对象并据此调用相应计算函数；Validator 可根据 validator_hint 选择校验策略。

    Args:
        method_id: 方法ID（注册表主键，唯一且稳定）。
        method_code: 方法可读别名/短码（便于日志与审计）。
        metric_key: 指标键（如 "pump_flow_rate"）。
        priority: 该方法的优先级（数值越小越优先或依据项目约定）。
        dependencies: 该方法所需的依赖指标键列表（用于可用性与拓扑判定）。
        conditions: 方法适用条件（JSON语义，选择器负责解析判断）。
        params: 计算所需参数（来自 calculation_parameters 或上下文汇总）。
        validator_hint: 校验器提示（可选，如物理边界/特性曲线策略）。
    """

    method_id: str
    method_code: str
    metric_key: str
    priority: int
    dependencies: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    validator_hint: Optional[str] = None


__all__ = [
    "CalculationContext",
    "MethodDescriptor",
]

