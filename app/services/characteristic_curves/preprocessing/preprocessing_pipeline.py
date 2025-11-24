"""
预处理管道 (app.services.characteristic_curves.preprocessing.preprocessing_pipeline)

串联预处理步骤的管道。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/03_核心模块/05_预处理层.md
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.services.characteristic_curves.preprocessing.data_cleaner import DataCleaner
from app.services.characteristic_curves.preprocessing.data_validator import DataValidator
from app.services.characteristic_curves.preprocessing.normalizer import Normalizer


@dataclass
class PipelineStep:
    """管道步骤

    Attributes:
        name: 步骤名称
        processor: 处理器实例或函数
        enabled: 是否启用
        params: 额外参数
    """

    name: str
    processor: Any
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """管道执行结果

    Attributes:
        success: 是否成功
        data: 处理后的数据
        steps_executed: 已执行的步骤
        logs: 执行日志
    """

    success: bool
    data: pd.DataFrame
    steps_executed: List[str] = field(default_factory=list)
    logs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "steps_executed": self.steps_executed,
            "logs": self.logs,
        }


class PreprocessingPipeline:
    """预处理管道

    串联多个预处理步骤：验证 → 清洗 → 归一化。

    Attributes:
        steps: 管道步骤列表
    """

    def __init__(self, steps: Optional[List[PipelineStep]] = None) -> None:
        """初始化预处理管道

        Args:
            steps: 管道步骤列表，如果为None则使用默认步骤
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.steps = steps or self._create_default_steps()

    def _create_default_steps(self) -> List[PipelineStep]:
        """创建默认管道步骤"""
        return [
            PipelineStep(name="validate", processor=DataValidator(min_points=10)),
            PipelineStep(name="clean", processor=DataCleaner()),
            PipelineStep(name="normalize", processor=Normalizer(), enabled=False),
        ]

    def add_step(
        self, name: str, processor: Any, position: int = -1, **params: Any
    ) -> None:
        """添加步骤"""
        step = PipelineStep(name=name, processor=processor, params=params)
        if position < 0:
            self.steps.append(step)
        else:
            self.steps.insert(position, step)

    def remove_step(self, name: str) -> bool:
        """移除步骤"""
        original_len = len(self.steps)
        self.steps = [s for s in self.steps if s.name != name]
        return len(self.steps) < original_len

    def enable_step(self, name: str) -> None:
        """启用步骤"""
        for step in self.steps:
            if step.name == name:
                step.enabled = True
                break

    def disable_step(self, name: str) -> None:
        """禁用步骤"""
        for step in self.steps:
            if step.name == name:
                step.enabled = False
                break

    def preprocess(
        self, data: pd.DataFrame, x_col: str = "Q", y_col: str = "H"
    ) -> PipelineResult:
        """执行预处理管道

        Args:
            data: 原始数据
            x_col: X列名
            y_col: Y列名

        Returns:
            PipelineResult: 管道执行结果
        """
        current_data = data.copy()
        steps_executed: List[str] = []
        logs: List[Dict[str, Any]] = []

        for step in self.steps:
            if not step.enabled:
                continue

            try:
                if step.name == "validate":
                    result = step.processor.validate(current_data, x_col, y_col)
                    if not result.is_valid:
                        return PipelineResult(
                            success=False, data=current_data, 
                            steps_executed=steps_executed,
                            logs=[{"step": step.name, "error": "验证失败"}],
                        )
                elif step.name == "clean":
                    result = step.processor.clean(current_data, x_col, y_col)
                    current_data = result.cleaned_data
                    logs.append({"step": step.name, "removed": result.removed_count})
                elif step.name == "normalize":
                    step.processor.fit(current_data[y_col].values)
                    current_data[y_col] = step.processor.transform(current_data[y_col].values)
                    logs.append({"step": step.name, "method": step.processor.method})
                else:
                    # 自定义步骤
                    current_data = step.processor(current_data, **step.params)
                    logs.append({"step": step.name, "custom": True})

                steps_executed.append(step.name)

            except Exception as e:
                self._logger.error(f"步骤 {step.name} 执行失败: {e}")
                return PipelineResult(
                    success=False, data=current_data, steps_executed=steps_executed,
                    logs=[{"step": step.name, "error": str(e)}],
                )

        return PipelineResult(
            success=True, data=current_data, steps_executed=steps_executed, logs=logs
        )

    def get_step_names(self) -> List[str]:
        """获取所有步骤名称"""
        return [s.name for s in self.steps]

    def get_enabled_steps(self) -> List[str]:
        """获取已启用的步骤名称"""
        return [s.name for s in self.steps if s.enabled]

