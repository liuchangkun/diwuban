"""
循环组求解器：固定点迭代骨架（参数化收敛判据与最大迭代次数）

仅提供接口与流程骨架，不依赖外部库；真实求解策略由 orchestrator 注入依赖（MethodSelector/Calculators/Validator）。

作者：AI
最后修改：2025-10-07
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

_act = logging.getLogger(__name__)


@dataclass
class ConvergenceConfig:
    """
    收敛判据配置

    Attributes:
        max_iterations: 最大迭代次数
        tolerance: 收敛阈值（相邻两次结果差的上限，供策略函数解释）
        strict_mode: 严格模式（True 时可采用更保守策略）
    """

    max_iterations: int = 10
    tolerance: float = 1e-6
    strict_mode: bool = False


class CyclicGroupSolver:
    """
    循环组求解器接口与默认骨架

    调用方向（示意）：
      solver.solve(group_metrics, method_selector, get_calculator, validator, data, ctx)

    约束：
      - 本类不直接修改数据库；只返回更新后的 data 片段与求解状态
      - 具体误差计算/收敛判断由 _has_converged 钩子或回调策略决定
    """

    def __init__(self, config: Optional[ConvergenceConfig] = None) -> None:
        _act.info("[流程-开始] [循环组求解器初始化]")
        self._cfg = config or ConvergenceConfig()

    def solve(
        self,
        group_metrics: List[str],
        select_method: Callable[..., Optional[object]],  # 返回 MethodDescriptor 的函数
        get_calculator: Callable[[str], Callable[..., Tuple[object, dict]]],
        validate: Callable[..., Tuple[object, List[str], List[str]]],
        data: Dict[str, object],
        ctx: object,
    ) -> Tuple[Dict[str, object], Dict[str, object]]:
        """
        求解循环依赖组（固定点迭代骨架）。

        Args:
            group_metrics: 循环组内的 metric_key 列表
            select_method: 方法选择函数（应返回 MethodDescriptor）
            get_calculator: 根据 method_id 返回计算函数
            validate: 结果校验函数
            data: 输入/累积数据字典
            ctx: 统一的 CalculationContext

        Returns:
            (updated_data, meta):
              - updated_data: 组内各 metric_key 的最新 ndarray/序列结果
              - meta: {"iterations": int, "converged": bool}
        """
        _act.info(
            "[流程-开始] [循环组求解]",
            extra={
                "extra_data": {
                    "group_size": len(group_metrics),
                    "max_iterations": self._cfg.max_iterations,
                    "tolerance": self._cfg.tolerance,
                    "metrics": group_metrics,
                }
            },
        )

        iterations = 0
        converged = False
        updated: Dict[str, object] = {}

        while iterations < self._cfg.max_iterations and not converged:
            iterations += 1
            _act.info(
                "[流程-阶段] [迭代求解]",
                extra={
                    "extra_data": {
                        "iteration": iterations,
                        "group_size": len(group_metrics),
                    }
                },
            )

            # 逐个指标进行一次“尝试更新”
            step_updates: Dict[str, object] = {}
            for m in group_metrics:
                method = select_method(m)  # 由上层提供统一签名的适配
                if method is None:
                    continue
                calc_fn = get_calculator(getattr(method, "method_id", None))
                # 计算函数应接受 (ctx, method, data) 新签名；此处只保留骨架调用语义
                values, _meta = calc_fn(ctx, method, data)
                # 校验（mask/错误/警告），此处不展开实现
                _mask, _errs, _warns = validate(m, values, ctx)  # 统一语义
                step_updates[m] = values

            # 合并一次迭代的结果到 updated 与 data 视图
            for k, v in step_updates.items():
                updated[k] = v
                data[k] = v

            # 收敛判断（骨架）：由钩子/策略函数解释 tolerance
            converged = self._has_converged(updated, tolerance=self._cfg.tolerance)

            if converged:
                _act.info(
                    "[流程-阶段] [迭代收敛]",
                    extra={
                        "extra_data": {
                            "iterations": iterations,
                            "converged": True,
                        }
                    },
                )

        if not converged:
            _act.warning(
                "[流程-警告] [未收敛]",
                extra={
                    "extra_data": {
                        "iterations": iterations,
                        "max_iterations": self._cfg.max_iterations,
                        "converged": False,
                    }
                },
            )

        _act.info(
            "[流程-完成] [循环组求解完成]",
            extra={
                "extra_data": {
                    "group_size": len(group_metrics),
                    "iterations": iterations,
                    "converged": converged,
                    "updated_metrics": len(updated),
                }
            },
        )

        meta = {"iterations": iterations, "converged": converged}
        return updated, meta

    # ------------------------- 钩子/策略 -------------------------
    def _has_converged(self, latest: Dict[str, object], *, tolerance: float) -> bool:
        """
        收敛判断钩子：默认返回 False，调用方可在子类中覆盖或注入回调。
        """
        return False


__all__ = ["CyclicGroupSolver", "ConvergenceConfig"]

