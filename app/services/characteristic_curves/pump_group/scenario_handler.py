"""
场景处理器 (app.services.characteristic_curves.pump_group.scenario_handler)

本模块提供泵组场景识别和处理功能：
- P0单泵场景识别
- P2泵组场景识别
- 场景特定处理逻辑路由

版本: v1.0
更新日期: 2025-12-09
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

from app.services.characteristic_curves.models import GroupProcessingStrategy


class Scenario(str, Enum):
    """泵运行场景枚举"""

    # P0 单泵场景
    SOFT_START_SINGLE = "soft_start_single"  # 软启泵单泵
    VFD_SINGLE = "vfd_single"  # 变频泵单泵（频率变化大）
    QUASI_FIXED_FREQ_SINGLE = "quasi_fixed_freq_single"  # 类工频变频泵单泵

    # P2 泵组场景
    HOMOGENEOUS_GROUP = "homogeneous"  # 同构泵组
    HETEROGENEOUS_GROUP = "heterogeneous"  # 异构泵组
    VFD_HETEROGENEOUS_FREQ = "vfd_hetero_freq"  # VFD频率异构
    MIXED_GROUP = "mixed"  # 混合泵组
    MIXED_HETEROGENEOUS = "mixed_heterogeneous"  # 混合异构泵组
    GROUP_COMPOSITE = "group_composite"  # 泵组综合曲线


@dataclass
class ScenarioContext:
    """场景上下文"""

    scenario: Scenario
    is_single_pump: bool
    is_vfd: bool
    needs_frequency_normalization: bool
    pump_count: int
    pump_ids: List[int] = field(default_factory=list)
    group_type: Optional[GroupProcessingStrategy] = None
    extra: Dict[str, Any] = field(default_factory=dict)


class ScenarioHandler:
    """
    场景处理器

    职责：
    1. P0单泵场景识别
    2. P2泵组场景识别
    3. 场景特定处理逻辑路由
    """

    # 频率标准差阈值（Hz）
    FREQ_STD_THRESHOLD = 2.0

    def __init__(self):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def identify_single_pump_scenario(
        self, control_type: str, freq_std: float
    ) -> Scenario:
        """
        识别单泵场景

        Args:
            control_type: 控制类型 ('VFD' 或 'SS')
            freq_std: 频率标准差

        Returns:
            Scenario: 单泵场景
        """
        if control_type == "SS":
            return Scenario.SOFT_START_SINGLE

        # VFD泵
        if freq_std > self.FREQ_STD_THRESHOLD:
            return Scenario.VFD_SINGLE
        else:
            return Scenario.QUASI_FIXED_FREQ_SINGLE

    def identify_group_scenario(
        self, group_type: GroupProcessingStrategy
    ) -> Scenario:
        """
        将泵组类型转换为场景

        Args:
            group_type: 泵组处理策略

        Returns:
            Scenario: 泵组场景
        """
        mapping = {
            GroupProcessingStrategy.HOMOGENEOUS_GROUP: Scenario.HOMOGENEOUS_GROUP,
            GroupProcessingStrategy.HETEROGENEOUS_GROUP: Scenario.HETEROGENEOUS_GROUP,
            GroupProcessingStrategy.VFD_HETEROGENEOUS_FREQ: Scenario.VFD_HETEROGENEOUS_FREQ,
            GroupProcessingStrategy.MIXED_GROUP: Scenario.MIXED_GROUP,
            GroupProcessingStrategy.MIXED_HETEROGENEOUS: Scenario.MIXED_HETEROGENEOUS,
        }
        return mapping.get(group_type, Scenario.GROUP_COMPOSITE)

    def build_context(
        self,
        pump_infos: List[Dict[str, Any]],
        freq_std: Optional[float] = None,
        group_type: Optional[GroupProcessingStrategy] = None,
    ) -> ScenarioContext:
        """
        构建场景上下文

        Args:
            pump_infos: 泵信息列表
            freq_std: 频率标准差
            group_type: 泵组类型

        Returns:
            ScenarioContext: 场景上下文
        """
        pump_ids = [p.get("pump_id") for p in pump_infos]
        pump_count = len(pump_ids)

        # 检查是否全VFD
        control_types = set(p.get("control_type") for p in pump_infos)
        is_vfd = control_types == {"VFD"}

        # 单泵场景
        if pump_count == 1:
            control_type = pump_infos[0].get("control_type", "SS")
            scenario = self.identify_single_pump_scenario(
                control_type, freq_std or 0.0
            )
            return ScenarioContext(
                scenario=scenario,
                is_single_pump=True,
                is_vfd=(control_type == "VFD"),
                needs_frequency_normalization=(
                    control_type == "VFD"
                    and (freq_std or 0) > self.FREQ_STD_THRESHOLD
                ),
                pump_count=1,
                pump_ids=pump_ids,
                group_type=None,
            )

        # 泵组场景
        scenario = self.identify_group_scenario(
            group_type or GroupProcessingStrategy.HOMOGENEOUS_GROUP
        )

        needs_freq_norm = is_vfd and (freq_std or 0) > self.FREQ_STD_THRESHOLD

        return ScenarioContext(
            scenario=scenario,
            is_single_pump=False,
            is_vfd=is_vfd,
            needs_frequency_normalization=needs_freq_norm,
            pump_count=pump_count,
            pump_ids=pump_ids,
            group_type=group_type,
        )

    def get_processing_requirements(
        self, context: ScenarioContext
    ) -> Dict[str, Any]:
        """
        获取场景处理要求

        Args:
            context: 场景上下文

        Returns:
            Dict: 处理要求配置
        """
        requirements = {
            "needs_p0_fit": True,  # 是否需要P0拟合
            "needs_p2_synthesis": not context.is_single_pump,  # 是否需要P2合成
            "needs_frequency_normalization": context.needs_frequency_normalization,
            "needs_correction_model": False,
            "needs_weighted_synthesis": False,
            "synthesis_method": "direct",
        }

        # 根据场景设置特定要求
        if context.scenario == Scenario.VFD_HETEROGENEOUS_FREQ:
            requirements["needs_frequency_normalization"] = True
            requirements["synthesis_method"] = "frequency_normalized"

        elif context.scenario == Scenario.HETEROGENEOUS_GROUP:
            requirements["needs_correction_model"] = True
            requirements["synthesis_method"] = "heterogeneous"

        elif context.scenario == Scenario.MIXED_GROUP:
            requirements["needs_weighted_synthesis"] = True
            requirements["synthesis_method"] = "mixed_weighted"

        elif context.scenario == Scenario.MIXED_HETEROGENEOUS:
            requirements["needs_correction_model"] = True
            requirements["needs_weighted_synthesis"] = True
            requirements["synthesis_method"] = "mixed_heterogeneous"

        self._logger.debug(
            f"[处理要求] scenario={context.scenario.value}, "
            f"requirements={requirements}"
        )
        return requirements

    def get_stage_sequence(
        self, context: ScenarioContext
    ) -> List[str]:
        """
        获取场景对应的阶段序列

        Args:
            context: 场景上下文

        Returns:
            List[str]: 阶段名称列表
        """
        # P0阶段（单泵拟合）
        p0_stages = [
            "time_window_split",  # 阶段1
            "scenario_detect",  # 阶段2
            "data_extract",  # 阶段3
            "data_clean",  # 阶段4
            "steady_state_detect",  # 阶段5
            "constraint_compute",  # 阶段6
        ]

        # 条件阶段
        if context.needs_frequency_normalization:
            p0_stages.append("frequency_normalize")  # 阶段7

        p0_stages.extend(
            [
                "data_normalize",  # 阶段8
                "method_select",  # 阶段9
                "fit_execute",  # 阶段10
                "result_validate",  # 阶段11
                "historical_evaluate",  # 阶段12
                "result_store",  # 阶段13
            ]
        )

        # P2阶段（泵组合成）
        if not context.is_single_pump:
            p2_stages = [
                "group_identify",  # 阶段14
                "parallel_synthesize",  # 阶段15
                "group_store",  # 阶段16
            ]
            return p0_stages + p2_stages

        return p0_stages

    def should_skip_stage(
        self, context: ScenarioContext, stage_name: str
    ) -> bool:
        """
        判断是否跳过某阶段

        Args:
            context: 场景上下文
            stage_name: 阶段名称

        Returns:
            bool: 是否跳过
        """
        # 软启泵跳过频率归一化
        if stage_name == "frequency_normalize" and not context.is_vfd:
            return True

        # 单泵跳过P2阶段
        if context.is_single_pump and stage_name in (
            "group_identify",
            "parallel_synthesize",
            "group_store",
        ):
            return True

        # 类工频变频泵跳过频率归一化（频率变化小）
        if (
            stage_name == "frequency_normalize"
            and context.scenario == Scenario.QUASI_FIXED_FREQ_SINGLE
        ):
            return True

        return False

    def log_scenario_info(self, context: ScenarioContext) -> None:
        """记录场景信息到日志"""
        self._logger.info(
            f"[场景识别] scenario={context.scenario.value}, "
            f"is_single={context.is_single_pump}, is_vfd={context.is_vfd}, "
            f"pump_count={context.pump_count}, pump_ids={context.pump_ids}, "
            f"needs_freq_norm={context.needs_frequency_normalization}"
        )

