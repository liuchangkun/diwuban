"""曲线对比分析器 (app.services.characteristic_curves.pump_group.group_curve_comparator)

对比直接拟合与合成曲线的差异，根据决策规则推荐最优方法。

核心功能：
- 量化直接拟合与合成曲线的差异
- 分区域分析差异分布
- 根据决策规则推荐最优方法
- 生成对比报告用于诊断

版本: v1.0
创建日期: 2025-12-14
参考文档: 08_泵组直接拟合.md 第8节
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from app.services.characteristic_curves.core.data_structures import (
    CurveFitMethod,
    DirectFitResult,
)


logger = logging.getLogger(__name__)


@dataclass
class ComparisonConfig:
    """对比配置"""
    max_acceptable_diff: float = 0.05  # 最大可接受差异5%
    min_r2_for_direct_fit: float = 0.90  # 直接拟合最低R²要求
    min_data_points: int = 100  # 最少数据点
    n_sample_points: int = 100  # 采样点数


class GroupCurveComparator:
    """泵组曲线对比分析器

    职责：
    1. 量化直接拟合与合成曲线的差异
    2. 根据决策规则推荐最优方法
    3. 生成对比报告用于诊断
    """

    def __init__(self, config: Optional[ComparisonConfig] = None):
        """初始化对比分析器

        Args:
            config: 对比配置
        """
        self._config = config or ComparisonConfig()
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

    def compare(
        self,
        direct_fit: DirectFitResult,
        synthesis_func: Callable[[float], float],
        Q_range: Tuple[float, float],
        n_sample_points: Optional[int] = None
    ) -> Dict[str, Any]:
        """对比两种方法的曲线

        Args:
            direct_fit: 直接拟合结果
            synthesis_func: 合成曲线函数 H = f(Q)
            Q_range: 比较的流量范围
            n_sample_points: 采样点数（默认使用配置值）

        Returns:
            Dict: {
                'max_diff_h': 最大扬程差 (m),
                'avg_diff_h': 平均扬程差 (m),
                'max_diff_ratio': 最大相对差异,
                'avg_diff_ratio': 平均相对差异,
                'diff_by_region': 分区域差异分析,
                'sample_diffs': 详细采样数据,
                'recommended_method': 推荐方法,
                'recommendation_reason': 推荐理由,
                'confidence': 置信度,
                'generated_at': 生成时间
            }
        """
        n_points = n_sample_points or self._config.n_sample_points

        # 1. 在流量范围内采样
        Q_samples = np.linspace(Q_range[0], Q_range[1], n_points)

        diffs = []
        for Q in Q_samples:
            try:
                H_direct = direct_fit.predict(Q)
                H_synthesis = synthesis_func(Q)

                if H_synthesis > 0:
                    diff_ratio = abs(H_direct - H_synthesis) / H_synthesis
                    diffs.append({
                        'Q': float(Q),
                        'H_direct': float(H_direct),
                        'H_synthesis': float(H_synthesis),
                        'diff_h': float(H_direct - H_synthesis),
                        'diff_ratio': float(diff_ratio)
                    })
            except Exception as e:
                self._logger.debug(f"[对比] Q={Q:.1f}计算失败: {e}")
                continue

        if not diffs:
            self._logger.warning("[对比] 无有效采样点")
            return self._empty_result(direct_fit)

        # 2. 计算统计指标
        diff_ratios = [d['diff_ratio'] for d in diffs]
        diff_hs = [abs(d['diff_h']) for d in diffs]

        max_diff_ratio = max(diff_ratios)
        avg_diff_ratio = float(np.mean(diff_ratios))
        max_diff_h = max(diff_hs)
        avg_diff_h = float(np.mean(diff_hs))

        # 3. 分区域分析（低流量、中流量、高流量）
        n_third = len(diffs) // 3
        if n_third > 0:
            region_diffs = {
                'low_Q': float(np.mean([d['diff_ratio'] for d in diffs[:n_third]])),
                'mid_Q': float(np.mean([d['diff_ratio'] for d in diffs[n_third:2*n_third]])),
                'high_Q': float(np.mean([d['diff_ratio'] for d in diffs[2*n_third:]]))
            }
        else:
            region_diffs = {'low_Q': 0.0, 'mid_Q': 0.0, 'high_Q': 0.0}

        # 4. 决策推荐
        recommended, reason, confidence = self._determine_recommendation(
            direct_fit, max_diff_ratio, avg_diff_ratio, region_diffs
        )

        result = {
            'max_diff_h': float(max_diff_h),
            'avg_diff_h': float(avg_diff_h),
            'max_diff_ratio': float(max_diff_ratio),
            'avg_diff_ratio': float(avg_diff_ratio),
            'diff_by_region': region_diffs,
            'sample_diffs': diffs,
            'recommended_method': recommended,
            'recommendation_reason': reason,
            'confidence': float(confidence),
            'Q_range': list(Q_range),
            'n_samples': len(diffs),
            'generated_at': datetime.now().isoformat()
        }

        self._logger.info(
            f"[对比完成] avg_diff={avg_diff_ratio:.1%}, "
            f"max_diff={max_diff_ratio:.1%}, "
            f"推荐: {recommended.value}"
        )

        return result

    def _determine_recommendation(
        self,
        direct_fit: DirectFitResult,
        max_diff_ratio: float,
        avg_diff_ratio: float,
        region_diffs: Dict[str, float]
    ) -> Tuple[CurveFitMethod, str, float]:
        """确定推荐方法

        决策规则（优先级从高到低）：

        1. 直接拟合数据不足 → 推荐合成
           条件：data_points_used < min_data_points

        2. 直接拟合质量差 → 推荐合成
           条件：R² < 0.90

        3. 差异很小 → 推荐合成（更灵活）
           条件：avg_diff_ratio < 2%

        4. 直接拟合质量优秀且差异显著 → 推荐直接拟合
           条件：R² > 0.95 且 data_points > 200 且 avg_diff_ratio > 3%

        5. 区域差异不均匀 → 推荐直接拟合
           条件：max(region_diffs) - min(region_diffs) > 5%

        6. 其他情况 → 推荐合成（保守选择）
        """
        # 规则1：数据量不足
        if direct_fit.data_points_used < self._config.min_data_points:
            return (
                CurveFitMethod.SYNTHESIS,
                f"直接拟合数据点不足（{direct_fit.data_points_used} < {self._config.min_data_points}）",
                0.9
            )

        # 规则2：拟合质量差
        if direct_fit.r_squared < self._config.min_r2_for_direct_fit:
            return (
                CurveFitMethod.SYNTHESIS,
                f"直接拟合R²过低（{direct_fit.r_squared:.3f} < {self._config.min_r2_for_direct_fit}）",
                0.85
            )

        # 规则3：差异很小
        if avg_diff_ratio < 0.02:
            return (
                CurveFitMethod.SYNTHESIS,
                f"两种方法差异很小（{avg_diff_ratio:.1%}），合成方法更灵活",
                0.95
            )

        # 规则4：直接拟合优秀且差异显著
        if (direct_fit.r_squared > 0.95 and
            direct_fit.data_points_used > 200 and
                avg_diff_ratio > 0.03):
            return (
                CurveFitMethod.DIRECT_FIT,
                f"直接拟合质量优秀（R²={direct_fit.r_squared:.3f}，"
                f"数据点={direct_fit.data_points_used}），差异{avg_diff_ratio:.1%}显著",
                0.90
            )

        # 规则5：区域差异不均匀
        if region_diffs:
            region_range = max(region_diffs.values()) - \
                min(region_diffs.values())
            if region_range > 0.05:
                worst_region = max(region_diffs, key=region_diffs.get)
                return (
                    CurveFitMethod.DIRECT_FIT,
                    f"合成方法在{worst_region}区域偏差较大（区域差异范围{region_range:.1%}）",
                    0.75
                )

        # 规则6：默认推荐合成
        return (
            CurveFitMethod.SYNTHESIS,
            "差异在可接受范围内，推荐使用更灵活的合成方法",
            0.7
        )

    def _empty_result(self, direct_fit: DirectFitResult) -> Dict[str, Any]:
        """生成空结果"""
        return {
            'max_diff_h': 0.0,
            'avg_diff_h': 0.0,
            'max_diff_ratio': 0.0,
            'avg_diff_ratio': 0.0,
            'diff_by_region': {},
            'sample_diffs': [],
            'recommended_method': CurveFitMethod.SYNTHESIS,
            'recommendation_reason': '无法进行对比，默认推荐合成方法',
            'confidence': 0.5,
            'Q_range': [0, 0],
            'n_samples': 0,
            'generated_at': datetime.now().isoformat()
        }

    def generate_comparison_report(
        self,
        comparison_result: Dict[str, Any],
        direct_fit: DirectFitResult,
        station_id: int,
        pump_combination: List[int]
    ) -> Dict[str, Any]:
        """生成对比报告

        Args:
            comparison_result: compare()方法的返回值
            direct_fit: 直接拟合结果
            station_id: 泵站ID
            pump_combination: 泵组合

        Returns:
            Dict: 结构化的对比报告
        """
        # 差异程度分类
        avg_diff = comparison_result.get('avg_diff_ratio', 0)
        if avg_diff < 0.02:
            diff_level = '极小'
            diff_description = '系统损失小，单泵曲线准确'
            suggested_action = '继续使用合成方法'
        elif avg_diff < 0.05:
            diff_level = '正常'
            diff_description = '存在并联损失，属正常范围'
            suggested_action = '两种方法均可'
        elif avg_diff < 0.10:
            diff_level = '偏大'
            diff_description = '管网复杂或单泵曲线偏差'
            suggested_action = '优先使用直接拟合'
        else:
            diff_level = '过大'
            diff_description = '单泵曲线或合成逻辑有问题'
            suggested_action = '需排查诊断'

        report = {
            'summary': {
                'station_id': station_id,
                'pump_combination': pump_combination,
                'pump_count': len(pump_combination),
                'diff_level': diff_level,
                'diff_description': diff_description,
                'suggested_action': suggested_action
            },
            'direct_fit_info': {
                'r_squared': direct_fit.r_squared,
                'rmse': direct_fit.rmse,
                'data_points': direct_fit.data_points_used,
                'polynomial_degree': direct_fit.polynomial_degree,
                'frequency_normalized': direct_fit.frequency_normalized
            },
            'comparison_metrics': {
                'avg_diff_h': comparison_result.get('avg_diff_h'),
                'max_diff_h': comparison_result.get('max_diff_h'),
                'avg_diff_ratio': comparison_result.get('avg_diff_ratio'),
                'max_diff_ratio': comparison_result.get('max_diff_ratio')
            },
            'region_analysis': comparison_result.get('diff_by_region', {}),
            'recommendation': {
                'method': comparison_result.get('recommended_method', CurveFitMethod.SYNTHESIS).value,
                'reason': comparison_result.get('recommendation_reason', ''),
                'confidence': comparison_result.get('confidence', 0)
            },
            'generated_at': datetime.now().isoformat()
        }

        self._logger.info(
            f"[对比报告] station={station_id}, pumps={pump_combination}, "
            f"差异程度={diff_level}, 推荐={report['recommendation']['method']}"
        )

        return report

    def __repr__(self) -> str:
        return (
            f"GroupCurveComparator("
            f"max_diff={self._config.max_acceptable_diff:.0%}, "
            f"min_r2={self._config.min_r2_for_direct_fit})"
        )
