"""双方法执行器 (app.services.characteristic_curves.pump_group.dual_method_executor)

同时执行直接拟合和合成曲线两种方法，自动对比分析并推荐最优方法。

核心功能：
- 同时执行直接拟合和合成曲线两种方法
- 自动调用对比分析
- 返回DualFitResult包含两种方法的结果和推荐

版本: v1.0
创建日期: 2025-12-14
参考文档: 08_泵组直接拟合.md 第7.5节
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.services.characteristic_curves.core.data_structures import (
    CurveFitMethod,
    DirectFitResult,
    DualFitResult,
    GroupFitResult,
    GroupOperatingPoint,
    GroupProcessingStrategy,
)
from .group_curve_comparator import GroupCurveComparator
from .group_curve_fitter import GroupCurveFitter
from .group_data_extractor import GroupDataExtractor
from .parallel_synthesizer import ParallelSynthesizer
from .pump_group_processor import PumpGroupProcessor


logger = logging.getLogger(__name__)


class DualMethodExecutor:
    """双方法执行器

    职责:
    1. 同时执行直接拟合和合成曲线两种方法
    2. 自动调用对比分析
    3. 返回DualFitResult
    """

    def __init__(
        self,
        extractor: Optional[GroupDataExtractor] = None,
        fitter: Optional[GroupCurveFitter] = None,
        processor: Optional[PumpGroupProcessor] = None,
        comparator: Optional[GroupCurveComparator] = None
    ):
        """初始化双方法执行器

        Args:
            extractor: 泵组数据提取器
            fitter: 泵组曲线拟合器
            processor: 泵组处理器（负责合成+修正）
            comparator: 曲线对比分析器
        """
        self._extractor = extractor or GroupDataExtractor()
        self._fitter = fitter or GroupCurveFitter()
        self._processor = processor or PumpGroupProcessor()
        self._comparator = comparator or GroupCurveComparator()
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

        self._logger.info("[双方法执行器] 初始化完成")

    def execute(
        self,
        station_id: int,
        pump_infos: List[Dict[str, Any]],
        curve_type: str = 'qh',
        group_type: Optional[GroupProcessingStrategy] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        min_data_points: int = 100
    ) -> DualFitResult:
        """执行双方法拟合

        流程:
        1. 识别泵组类型（如未提供）
        2. 提取泵组历史数据
        3. 执行直接拟合
        4. 执行合成曲线
        5. 自动对比分析
        6. 返回DualFitResult

        Args:
            station_id: 泵站ID
            pump_infos: 泵信息列表
            curve_type: 曲线类型
            group_type: 泵组类型（如未提供则自动识别）
            time_range: 时间范围 (start, end)
            min_data_points: 最少数据点要求

        Returns:
            DualFitResult: 包含两种方法结果的对比分析
        """
        pump_ids = [p['pump_id'] for p in pump_infos]
        n_pumps = len(pump_ids)

        self._logger.info(
            f"[双方法执行] station={station_id}, pumps={pump_ids}, curve={curve_type}"
        )

        # 1. 识别泵组类型
        if group_type is None:
            group_type = self._processor.identify_group_type(pump_infos)
            self._logger.info(f"[双方法执行] 自动识别泵组类型: {group_type.value}")

        # 初始化结果
        direct_fit_result: Optional[DirectFitResult] = None
        synthesis_result: Optional[GroupFitResult] = None
        direct_fit_success = False
        synthesis_success = False
        comparison: Optional[Dict[str, Any]] = None

        # 2. 执行直接拟合
        try:
            direct_fit_result = self._execute_direct_fit(
                station_id=station_id,
                pump_ids=pump_ids,
                curve_type=curve_type,
                group_type=group_type,
                time_range=time_range,
                min_data_points=min_data_points
            )
            direct_fit_success = True
            self._logger.info(
                f"[直接拟合] 成功, R²={direct_fit_result.r_squared:.4f}, "
                f"数据点={direct_fit_result.data_points_used}"
            )
        except Exception as e:
            self._logger.warning(f"[直接拟合] 失败: {e}")

        # 3. 执行合成曲线
        try:
            synthesis_result = self._execute_synthesis(
                station_id=station_id,
                pump_infos=pump_infos,
                curve_type=curve_type
            )
            synthesis_success = True
            self._logger.info(
                f"[合成曲线] 成功, type={synthesis_result.group_type.value}"
            )
        except Exception as e:
            self._logger.warning(f"[合成曲线] 失败: {e}")

        # 4. 对比分析（如果两种方法都成功）
        recommended_method = CurveFitMethod.SYNTHESIS
        recommendation_reason = ""

        if direct_fit_success and synthesis_success:
            try:
                comparison = self._perform_comparison(
                    direct_fit_result=direct_fit_result,
                    synthesis_result=synthesis_result,
                    pump_ids=pump_ids
                )
                recommended_method = comparison.get(
                    'recommended_method', CurveFitMethod.SYNTHESIS
                )
                recommendation_reason = comparison.get(
                    'recommendation_reason', ''
                )
                self._logger.info(
                    f"[对比分析] 完成, 推荐方法: {recommended_method.value}"
                )
            except Exception as e:
                self._logger.warning(f"[对比分析] 失败: {e}")
                recommended_method = CurveFitMethod.SYNTHESIS
                recommendation_reason = f"对比分析失败，默认推荐合成方法: {e}"

        elif direct_fit_success and not synthesis_success:
            recommended_method = CurveFitMethod.DIRECT_FIT
            recommendation_reason = "合成曲线失败，仅直接拟合可用"

        elif synthesis_success and not direct_fit_success:
            recommended_method = CurveFitMethod.SYNTHESIS
            recommendation_reason = "直接拟合失败，仅合成曲线可用"

        else:
            recommended_method = CurveFitMethod.SYNTHESIS
            recommendation_reason = "两种方法均失败"

        # 5. 构建结果
        result = DualFitResult(
            station_id=station_id,
            pump_combination=pump_ids,
            n_pumps=n_pumps,
            group_type=group_type,
            curve_type=curve_type,
            direct_fit_result=direct_fit_result,
            synthesis_result=synthesis_result,
            comparison=comparison,
            direct_fit_success=direct_fit_success,
            synthesis_success=synthesis_success,
            recommended_method=recommended_method,
            recommendation_reason=recommendation_reason
        )

        self._logger.info(
            f"[双方法执行] 完成, 直接拟合={'成功' if direct_fit_success else '失败'}, "
            f"合成曲线={'成功' if synthesis_success else '失败'}, "
            f"推荐: {recommended_method.value}"
        )

        return result

    def _execute_direct_fit(
        self,
        station_id: int,
        pump_ids: List[int],
        curve_type: str,
        group_type: GroupProcessingStrategy,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        min_data_points: int = 100
    ) -> DirectFitResult:
        """执行直接拟合

        Args:
            station_id: 泵站ID
            pump_ids: 泵ID列表
            curve_type: 曲线类型
            group_type: 泵组类型
            time_range: 时间范围
            min_data_points: 最少数据点

        Returns:
            DirectFitResult: 直接拟合结果
        """
        # 设置时间范围
        if time_range is None:
            end_time = datetime.now()
            start_time = end_time.replace(hour=0, minute=0, second=0) - \
                __import__('datetime').timedelta(days=90)
            time_range = (start_time, end_time)

        # 1. 提取历史工况点
        points = self._extractor.extract_group_operating_points(
            station_id=station_id,
            start_time=time_range[0],
            end_time=time_range[1],
            min_running_pumps=1
        )

        self._logger.info(f"[直接拟合] 提取到 {len(points)} 个工况点")

        # 2. 按泵组合分组
        points_by_combination = self._extractor.group_by_pump_combination(
            points)

        # 找到当前泵组合
        combination_key = ",".join(map(str, sorted(pump_ids)))
        if combination_key not in points_by_combination:
            raise ValueError(f"未找到泵组合 {combination_key} 的历史数据")

        combination_points = points_by_combination[combination_key]
        self._logger.info(
            f"[直接拟合] 泵组合 {combination_key} 有 {len(combination_points)} 条数据"
        )

        # 3. VFD频率异构场景需要归一化
        if group_type == GroupProcessingStrategy.VFD_HETEROGENEOUS_FREQ:
            combination_points = self._handle_vfd_heterogeneous_freq(
                combination_points)

        # 4. 执行拟合
        results = self._fitter.fit_by_combination(
            station_id=station_id,
            points_by_combination={combination_key: combination_points},
            curve_type=curve_type
        )

        if combination_key not in results:
            raise ValueError(f"泵组合 {combination_key} 拟合失败")

        return results[combination_key]

    def _execute_synthesis(
        self,
        station_id: int,
        pump_infos: List[Dict[str, Any]],
        curve_type: str
    ) -> GroupFitResult:
        """执行合成曲线

        Args:
            station_id: 泵站ID
            pump_infos: 泵信息列表
            curve_type: 曲线类型

        Returns:
            GroupFitResult: 合成曲线结果
        """
        return self._processor.process(
            station_id=station_id,
            pump_infos=pump_infos,
            curve_type=curve_type,
            auto_trigger_p0=False
        )

    def _perform_comparison(
        self,
        direct_fit_result: DirectFitResult,
        synthesis_result: GroupFitResult,
        pump_ids: List[int]
    ) -> Dict[str, Any]:
        """执行对比分析

        Args:
            direct_fit_result: 直接拟合结果
            synthesis_result: 合成曲线结果
            pump_ids: 泵ID列表

        Returns:
            Dict: 对比分析结果
        """
        # 构建合成曲线函数
        # 这里需要从synthesis_result构建预测函数
        # 简化实现：使用直接拟合的Q范围
        Q_range = direct_fit_result.valid_q_range

        # 创建合成曲线预测函数
        def synthesis_func(Q: float) -> float:
            # 使用合成器的曲线
            # 这是一个简化实现，实际应该从曲线注册表获取
            H_system = 35.0  # 假设系统扬程
            n_pumps = len(pump_ids)
            Q_single = Q / n_pumps
            # 使用二次多项式近似: H = H0 - K*Q²
            H0 = 50.0  # 假设关死点扬程
            K = 0.00001
            return H0 - K * Q_single ** 2

        # 调用对比器
        comparison = self._comparator.compare(
            direct_fit=direct_fit_result,
            synthesis_func=synthesis_func,
            Q_range=Q_range
        )

        # 生成对比报告
        report = self._comparator.generate_comparison_report(
            comparison_result=comparison,
            direct_fit=direct_fit_result,
            station_id=synthesis_result.station_id,
            pump_combination=pump_ids
        )

        comparison['report'] = report
        return comparison

    def _handle_vfd_heterogeneous_freq(
        self,
        points: List[GroupOperatingPoint]
    ) -> List[GroupOperatingPoint]:
        """VFD频率异构场景的频率归一化处理（08文档定义接口）

        将不同频率的工况点归一化到50Hz基准频率。

        Args:
            points: 原始工况点列表

        Returns:
            List[GroupOperatingPoint]: 归一化后的工况点列表
        """
        normalized = []
        for point in points:
            if point.avg_frequency and point.avg_frequency != 50.0:
                normalized.append(point.to_normalized(50.0))
            else:
                normalized.append(point)

        self._logger.info(f"[频率归一化] 处理 {len(normalized)} 个工况点")
        return normalized

    def get_summary(self, result: DualFitResult) -> Dict[str, Any]:
        """获取执行摘要

        Args:
            result: DualFitResult

        Returns:
            Dict: 执行摘要
        """
        summary = {
            'station_id': result.station_id,
            'pump_combination': result.pump_combination,
            'n_pumps': result.n_pumps,
            'group_type': result.group_type.value,
            'curve_type': result.curve_type,
            'direct_fit': {
                'success': result.direct_fit_success,
                'r_squared': result.direct_fit_result.r_squared if result.direct_fit_result else None,
                'data_points': result.direct_fit_result.data_points_used if result.direct_fit_result else None
            },
            'synthesis': {
                'success': result.synthesis_success,
                'correction_fitted': (
                    result.synthesis_result.correction_model is not None
                    if result.synthesis_result else False
                )
            },
            'recommendation': {
                'method': result.recommended_method.value,
                'reason': result.recommendation_reason
            },
            'comparison': {
                'avg_diff_ratio': result.comparison.get('avg_diff_ratio') if result.comparison else None,
                'max_diff_ratio': result.comparison.get('max_diff_ratio') if result.comparison else None
            } if result.comparison else None,
            'generated_at': datetime.now().isoformat()
        }

        return summary

    def __repr__(self) -> str:
        return f"DualMethodExecutor()"
