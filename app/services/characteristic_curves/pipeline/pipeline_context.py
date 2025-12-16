"""
管道上下文 (app.services.characteristic_curves.pipeline.pipeline_context)

管理管道执行过程中的状态和数据传递。

版本: v1.0
更新日期: 2025-12-09
参考文档: 特性曲线开发/开发文档/02_架构设计/02_数据流定义.md
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import pandas as pd


class PipelineStage(str, Enum):
    """管道阶段枚举（18阶段）"""

    # P0阶段（单泵曲线）
    TIME_WINDOW_SPLIT = "time_window_split"  # 阶段1
    SCENARIO_DETECT = "scenario_detect"  # 阶段2
    DATA_EXTRACT = "data_extract"  # 阶段3
    DATA_CLEAN = "data_clean"  # 阶段4
    STEADY_STATE_DETECT = "steady_state_detect"  # 阶段5
    CONSTRAINT_CALC = "constraint_calc"  # 阶段6
    FREQ_NORMALIZE = "freq_normalize"  # 阶段7
    DATA_NORMALIZE = "data_normalize"  # 阶段8
    METHOD_SELECT = "method_select"  # 阶段9
    CURVE_FIT = "curve_fit"  # 阶段10
    RESULT_VALIDATE = "result_validate"  # 阶段11
    HISTORICAL_EVAL = "historical_eval"  # 阶段12
    RESULT_STORE = "result_store"  # 阶段13
    PLOT_GENERATION = "plot_generation"  # 阶段14（新增）
    REPORT_GENERATION = "report_generation"  # 阶段15（新增）

    # P2阶段（泵组曲线）
    GROUP_TYPE_IDENTIFY = "group_type_identify"  # 阶段16
    PARALLEL_SYNTHESIZE = "parallel_synthesize"  # 阶段17
    CORRECTION_LEARN = "correction_learn"  # 阶段18


@dataclass
class StageResult:
    """阶段执行结果"""

    stage: PipelineStage
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    skipped: bool = False
    skip_reason: Optional[str] = None


@dataclass
class PipelineContext:
    """管道上下文

    管理整个管道执行过程中的状态、数据和日志。

    Attributes:
        device_id: 设备ID
        curve_type: 曲线类型
        start_time: 开始时间
        end_time: 结束时间
        current_stage: 当前阶段
        stage_results: 各阶段执行结果
        data: 阶段间传递的数据
        errors: 错误列表
        warnings: 警告列表
        progress_callback: 进度回调函数
    """

    device_id: int
    curve_type: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    current_stage: Optional[PipelineStage] = None
    stage_results: Dict[PipelineStage, StageResult] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    progress_callback: Optional[Callable[[PipelineStage, float], None]] = None
    _logger: logging.Logger = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """初始化后处理"""
        if self._logger is None:
            self._logger = logging.getLogger(f"{__name__}.PipelineContext")

    def set_stage(self, stage: PipelineStage) -> None:
        """设置当前阶段"""
        self.current_stage = stage
        self._logger.info(f"进入阶段: {stage.value}")

    def add_stage_result(self, result: StageResult) -> None:
        """添加阶段结果"""
        self.stage_results[result.stage] = result
        if not result.success and result.error:
            self.errors.append(f"[{result.stage.value}] {result.error}")

    def get_stage_result(self, stage: PipelineStage) -> Optional[StageResult]:
        """获取指定阶段的结果"""
        return self.stage_results.get(stage)

    def set_data(self, key: str, value: Any) -> None:
        """设置数据"""
        self.data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """获取数据"""
        return self.data.get(key, default)

    def add_warning(self, message: str) -> None:
        """添加警告"""
        self.warnings.append(message)
        self._logger.warning(message)

    def add_error(self, message: str) -> None:
        """添加错误"""
        self.errors.append(message)
        self._logger.error(message)

    def report_progress(self, progress: float) -> None:
        """报告进度"""
        if self.progress_callback and self.current_stage:
            self.progress_callback(self.current_stage, progress)

    def is_success(self) -> bool:
        """检查管道是否成功完成"""
        return len(self.errors) == 0

    def get_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        completed = sum(1 for r in self.stage_results.values() if r.success)
        skipped = sum(1 for r in self.stage_results.values() if r.skipped)
        failed = sum(1 for r in self.stage_results.values() if not r.success and not r.skipped)
        total_duration = sum(r.duration_ms for r in self.stage_results.values())

        return {
            "device_id": self.device_id,
            "curve_type": self.curve_type,
            "success": self.is_success(),
            "stages_completed": completed,
            "stages_skipped": skipped,
            "stages_failed": failed,
            "total_duration_ms": total_duration,
            "errors": self.errors,
            "warnings": self.warnings,
        }

