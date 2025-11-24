"""
双方法执行器

本模块负责执行双方法流程：
1. 执行直接拟合
2. 对比两种方法
3. 推荐最佳方法

版本: v1.0
创建日期: 2025-12-09
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.services.characteristic_curves.models import GroupProcessingStrategy
from app.services.characteristic_curves.pump_group.group_curve_comparator import (
    GroupCurveComparator,
)
from app.services.characteristic_curves.pump_group.group_curve_fitter import (
    GroupCurveFitter,
)
from app.services.characteristic_curves.pump_group.group_data_extractor import (
    GroupDataExtractor,
)
from app.services.characteristic_curves.pump_group.models import (
    ComparisonResult,
    CurveFitMethod,
    DirectFitResult,
)


class DualMethodExecutor:
    """双方法执行器（简化版）"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化执行器

        Args:
            config: 配置字典（可选）
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._config = config or self._load_default_config()

        # 初始化组件
        self._extractor = GroupDataExtractor(config=self._config.get("extractor"))
        self._fitter = GroupCurveFitter(config=self._config.get("fitter"))
        self._comparator = GroupCurveComparator(config=self._config.get("comparator"))

    def execute_direct_fit(
        self,
        station_id: int,
        pump_ids: List[int],
        group_type: GroupProcessingStrategy,
        synthesis_result: Dict[str, Any],
        start_time: datetime,
        end_time: datetime,
        curve_type: str = "qh",
    ) -> Tuple[DirectFitResult, ComparisonResult, CurveFitMethod]:
        """
        执行直接拟合和对比分析

        Args:
            station_id: 站点ID
            pump_ids: 泵ID列表
            group_type: 泵组类型
            synthesis_result: 合成曲线结果（用于对比）
            start_time: 开始时间
            end_time: 结束时间
            curve_type: 曲线类型

        Returns:
            Tuple[DirectFitResult, ComparisonResult, CurveFitMethod]:
                (直接拟合结果, 对比结果, 推荐方法)

        Raises:
            InsufficientDataError: 数据不足
            CurveFittingError: 拟合质量不达标
        """
        self._logger.info(
            f"[双方法执行] 开始执行直接拟合: station_id={station_id}, "
            f"pumps={pump_ids}, group_type={group_type.value}"
        )

        # 步骤1: 提取数据
        points = self._extractor.extract_group_operating_points(
            station_id=station_id,
            pump_ids=pump_ids,
            start_time=start_time,
            end_time=end_time,
        )

        # 步骤2: 频率归一化（如果需要）
        points = self._extractor.normalize_by_frequency(
            points=points, scenario_type=group_type
        )

        # 步骤3: 按泵组合分组
        groups = self._extractor.group_by_pump_combination(points)

        # 步骤4: 选择最大组合进行拟合
        largest_combo = max(groups.keys(), key=lambda c: len(groups[c]))
        largest_points = groups[largest_combo]

        self._logger.info(
            f"[双方法执行] 选择最大泵组合: {largest_combo}, 数据点数: {len(largest_points)}"
        )

        # 步骤5: 执行拟合
        direct_fit_result = self._fitter.fit_polynomial(
            station_id=station_id,
            pump_combination=list(largest_combo),
            points=largest_points,
            curve_type=curve_type,
            degree=None,  # 自动选择阶数
            group_type=group_type.value,
        )

        # 步骤6: 对比分析
        comparison_result = self._comparator.compare(
            direct_fit=direct_fit_result, synthesis=synthesis_result
        )

        # 步骤7: 推荐方法
        recommended_method = comparison_result.recommended_method

        self._logger.info(
            f"[双方法执行] 完成: 推荐方法={recommended_method.value}, "
            f"理由={comparison_result.recommendation_reason}"
        )

        return direct_fit_result, comparison_result, recommended_method

    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "extractor": {
                "min_data_points": 100,
                "time_bucket_interval": "5 minutes",
            },
            "fitter": {
                "min_data_points": 100,
                "min_r_squared": 0.85,
                "regularization_alpha": 1.0,
                "cv_folds": 5,
            },
            "comparator": {
                "recommendation_threshold_pct": 2.0,
            },
        }

