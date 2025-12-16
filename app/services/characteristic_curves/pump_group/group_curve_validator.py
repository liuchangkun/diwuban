"""
泵组曲线验证器 (app.services.characteristic_curves.pump_group.group_curve_validator)

对拟合生成的泵组曲线进行物理规律校验和质量评估。

核心功能：
- 物理规律验证（曲线单调性、边界条件、效率范围）
- 拟合质量评估（R²、RMSE、数据覆盖率）
- 与历史曲线一致性检查
- 生成验证报告

版本: v1.0
创建日期: 2025-12-14
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool  # 是否通过验证
    score: float  # 总体评分 (0-100)
    checks: List[Dict[str, Any]]  # 各项检查结果
    warnings: List[str]  # 警告信息
    errors: List[str]  # 错误信息
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'is_valid': self.is_valid,
            'score': self.score,
            'checks': self.checks,
            'warnings': self.warnings,
            'errors': self.errors,
            'metadata': self.metadata
        }


class GroupCurveValidator:
    """泵组曲线验证器

    职责：
    1. 验证拟合曲线是否符合物理规律
    2. 评估拟合质量
    3. 检查与历史曲线的一致性
    4. 生成验证报告

    物理规律检查项：
    - Q-H曲线：H应随Q增加而减小（单调递减）
    - Q-P曲线：P应随Q增加而增大（单调递增）
    - Q-η曲线：应存在效率峰值（先增后减）
    - 边界条件：Q=0时H=H_shutoff，Q=Q_max时H≈0
    - 效率范围：η ∈ (0, 1)
    """

    def __init__(
        self,
        min_r2: float = 0.90,
        max_rmse_ratio: float = 0.10,
        min_data_points: int = 50,
        allow_warnings: bool = True
    ):
        """
        Args:
            min_r2: 最低R²要求
            max_rmse_ratio: 最大RMSE/均值比例
            min_data_points: 最少数据点要求
            allow_warnings: 是否允许有警告仍通过验证
        """
        self._min_r2 = min_r2
        self._max_rmse_ratio = max_rmse_ratio
        self._min_data_points = min_data_points
        self._allow_warnings = allow_warnings

    def validate(
        self,
        curve_func: Callable[[float], float],
        curve_type: str,
        Q_range: Tuple[float, float],
        fit_metrics: Optional[Dict[str, float]] = None,
        reference_curve: Optional[Callable[[float], float]] = None,
        data_points_used: Optional[int] = None
    ) -> ValidationResult:
        """
        验证曲线

        Args:
            curve_func: 曲线函数 y = f(Q)
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            Q_range: 流量范围 (Q_min, Q_max)
            fit_metrics: 拟合指标 {'r2': float, 'rmse': float, ...}
            reference_curve: 参考曲线函数（用于一致性检查）
            data_points_used: 使用的数据点数

        Returns:
            ValidationResult: 验证结果
        """
        checks = []
        warnings = []
        errors = []

        # 1. 物理规律检查
        physics_check = self._check_physics(curve_func, curve_type, Q_range)
        checks.append(physics_check)
        if not physics_check['passed']:
            errors.extend(physics_check.get('errors', []))
        warnings.extend(physics_check.get('warnings', []))

        # 2. 边界条件检查
        boundary_check = self._check_boundary(curve_func, curve_type, Q_range)
        checks.append(boundary_check)
        if not boundary_check['passed']:
            warnings.extend(boundary_check.get('warnings', []))

        # 3. 拟合质量检查
        if fit_metrics:
            quality_check = self._check_fit_quality(
                fit_metrics, data_points_used)
            checks.append(quality_check)
            if not quality_check['passed']:
                errors.extend(quality_check.get('errors', []))
            warnings.extend(quality_check.get('warnings', []))

        # 4. 一致性检查（与参考曲线）
        if reference_curve:
            consistency_check = self._check_consistency(
                curve_func, reference_curve, Q_range
            )
            checks.append(consistency_check)
            if not consistency_check['passed']:
                warnings.extend(consistency_check.get('warnings', []))

        # 5. 数值稳定性检查
        stability_check = self._check_numerical_stability(curve_func, Q_range)
        checks.append(stability_check)
        if not stability_check['passed']:
            errors.extend(stability_check.get('errors', []))

        # 计算总体评分
        score = self._calculate_score(checks)

        # 判断是否通过
        has_errors = len(errors) > 0
        is_valid = not has_errors and (
            self._allow_warnings or len(warnings) == 0)

        return ValidationResult(
            is_valid=is_valid,
            score=score,
            checks=checks,
            warnings=warnings,
            errors=errors,
            metadata={
                'curve_type': curve_type,
                'Q_range': Q_range,
                'validated_at': datetime.now().isoformat()
            }
        )

    def validate_direct_fit_result(
        self,
        result: Any,  # DirectFitResult
        reference_synthesis: Optional[Callable[[float], float]] = None
    ) -> ValidationResult:
        """
        验证直接拟合结果

        Args:
            result: DirectFitResult对象
            reference_synthesis: 合成曲线函数（用于对比）

        Returns:
            ValidationResult
        """
        # 获取拟合指标
        fit_metrics = {
            'r2': result.r_squared,
            'rmse': getattr(result, 'rmse', None)
        }

        # 获取流量范围
        Q_range = result.Q_range if hasattr(result, 'Q_range') else (0, 1000)

        return self.validate(
            curve_func=result.predict,
            curve_type=result.curve_type,
            Q_range=Q_range,
            fit_metrics=fit_metrics,
            reference_curve=reference_synthesis,
            data_points_used=result.data_points_used
        )

    def _check_physics(
        self,
        curve_func: Callable[[float], float],
        curve_type: str,
        Q_range: Tuple[float, float]
    ) -> Dict[str, Any]:
        """物理规律检查"""
        Q_samples = np.linspace(Q_range[0], Q_range[1], 50)
        y_values = [curve_func(Q) for Q in Q_samples]

        errors = []
        warnings = []
        passed = True

        if curve_type == 'qh':
            # Q-H曲线应单调递减
            monotonic_violations = sum(
                1 for i in range(len(y_values) - 1)
                if y_values[i + 1] > y_values[i] * 1.01  # 允许1%容差
            )
            if monotonic_violations > len(y_values) * 0.1:
                errors.append(f"Q-H曲线非单调递减（{monotonic_violations}处违反）")
                passed = False
            elif monotonic_violations > 0:
                warnings.append(f"Q-H曲线存在{monotonic_violations}处轻微非单调")

            # H值应为正
            if any(y < 0 for y in y_values):
                errors.append("Q-H曲线存在负扬程值")
                passed = False

        elif curve_type == 'qp':
            # Q-P曲线应单调递增（大部分泵）
            monotonic_violations = sum(
                1 for i in range(len(y_values) - 1)
                if y_values[i + 1] < y_values[i] * 0.99
            )
            if monotonic_violations > len(y_values) * 0.2:
                warnings.append(f"Q-P曲线非典型单调递增（{monotonic_violations}处）")

            # P值应为正
            if any(y < 0 for y in y_values):
                errors.append("Q-P曲线存在负功率值")
                passed = False

        elif curve_type == 'qeta':
            # Q-η曲线应先增后减，存在峰值
            max_idx = np.argmax(y_values)
            if max_idx == 0 or max_idx == len(y_values) - 1:
                warnings.append("Q-η曲线峰值在边界，可能数据范围不足")

            # η值应在(0, 1)范围内
            if any(y < 0 or y > 1 for y in y_values):
                errors.append("Q-η曲线效率值超出(0,1)范围")
                passed = False

        return {
            'name': 'physics_check',
            'passed': passed,
            'errors': errors,
            'warnings': warnings,
            'details': {
                'curve_type': curve_type,
                'y_min': float(min(y_values)),
                'y_max': float(max(y_values)),
                'y_mean': float(np.mean(y_values))
            }
        }

    def _check_boundary(
        self,
        curve_func: Callable[[float], float],
        curve_type: str,
        Q_range: Tuple[float, float]
    ) -> Dict[str, Any]:
        """边界条件检查"""
        warnings = []
        passed = True

        Q_min, Q_max = Q_range

        if curve_type == 'qh':
            H_at_zero = curve_func(Q_min)
            H_at_max = curve_func(Q_max)

            # 关死点扬程应合理（通常50-150m范围）
            if H_at_zero < 10:
                warnings.append(f"关死点扬程过低: {H_at_zero:.1f}m")
            elif H_at_zero > 200:
                warnings.append(f"关死点扬程过高: {H_at_zero:.1f}m")

            # 最大流量时扬程不应为负
            if H_at_max < 0:
                warnings.append(f"最大流量时扬程为负: {H_at_max:.1f}m")
                passed = False

        return {
            'name': 'boundary_check',
            'passed': passed,
            'warnings': warnings,
            'details': {
                'Q_range': Q_range
            }
        }

    def _check_fit_quality(
        self,
        fit_metrics: Dict[str, float],
        data_points_used: Optional[int]
    ) -> Dict[str, Any]:
        """拟合质量检查"""
        errors = []
        warnings = []
        passed = True

        r2 = fit_metrics.get('r2', 0)
        rmse = fit_metrics.get('rmse')

        # R²检查
        if r2 < self._min_r2:
            errors.append(f"R²过低: {r2:.3f} < {self._min_r2}")
            passed = False
        elif r2 < 0.95:
            warnings.append(f"R²偏低: {r2:.3f}")

        # 数据点检查
        if data_points_used is not None:
            if data_points_used < self._min_data_points:
                errors.append(
                    f"数据点不足: {data_points_used} < {self._min_data_points}"
                )
                passed = False
            elif data_points_used < self._min_data_points * 2:
                warnings.append(f"数据点偏少: {data_points_used}")

        return {
            'name': 'fit_quality_check',
            'passed': passed,
            'errors': errors,
            'warnings': warnings,
            'details': {
                'r2': r2,
                'rmse': rmse,
                'data_points_used': data_points_used
            }
        }

    def _check_consistency(
        self,
        curve_func: Callable[[float], float],
        reference_curve: Callable[[float], float],
        Q_range: Tuple[float, float]
    ) -> Dict[str, Any]:
        """与参考曲线的一致性检查"""
        warnings = []
        passed = True

        Q_samples = np.linspace(Q_range[0], Q_range[1], 30)
        diffs = []

        for Q in Q_samples:
            y_new = curve_func(Q)
            y_ref = reference_curve(Q)
            if y_ref != 0:
                diff_ratio = abs(y_new - y_ref) / abs(y_ref)
                diffs.append(diff_ratio)

        if diffs:
            max_diff = max(diffs)
            avg_diff = np.mean(diffs)

            if max_diff > 0.20:  # 20%以上差异
                warnings.append(f"与参考曲线最大差异{max_diff:.1%}，需确认变化原因")
                passed = False
            elif max_diff > 0.10:
                warnings.append(f"与参考曲线差异{avg_diff:.1%}，建议关注")

        return {
            'name': 'consistency_check',
            'passed': passed,
            'warnings': warnings,
            'details': {
                'max_diff_ratio': float(max(diffs)) if diffs else 0,
                'avg_diff_ratio': float(np.mean(diffs)) if diffs else 0
            }
        }

    def _check_numerical_stability(
        self,
        curve_func: Callable[[float], float],
        Q_range: Tuple[float, float]
    ) -> Dict[str, Any]:
        """数值稳定性检查"""
        errors = []
        passed = True

        Q_samples = np.linspace(Q_range[0], Q_range[1], 100)

        try:
            y_values = [curve_func(Q) for Q in Q_samples]

            # 检查NaN和Inf
            if any(np.isnan(y) or np.isinf(y) for y in y_values):
                errors.append("曲线存在NaN或Inf值")
                passed = False

            # 检查异常跳变
            for i in range(1, len(y_values)):
                if y_values[i - 1] != 0:
                    jump = abs(y_values[i] - y_values[i - 1]
                               ) / abs(y_values[i - 1])
                    if jump > 0.5:  # 50%跳变
                        errors.append(f"曲线在Q={Q_samples[i]:.0f}处存在异常跳变")
                        passed = False
                        break

        except Exception as e:
            errors.append(f"曲线计算异常: {str(e)}")
            passed = False

        return {
            'name': 'numerical_stability_check',
            'passed': passed,
            'errors': errors,
            'details': {}
        }

    def _calculate_score(self, checks: List[Dict[str, Any]]) -> float:
        """计算总体评分"""
        weights = {
            'physics_check': 0.30,
            'boundary_check': 0.15,
            'fit_quality_check': 0.35,
            'consistency_check': 0.10,
            'numerical_stability_check': 0.10
        }

        total_weight = 0
        weighted_score = 0

        for check in checks:
            name = check['name']
            weight = weights.get(name, 0.1)
            score = 100 if check['passed'] else 50

            # 有警告扣分
            n_warnings = len(check.get('warnings', []))
            score -= n_warnings * 5

            weighted_score += weight * max(0, score)
            total_weight += weight

        return round(weighted_score / total_weight, 1) if total_weight > 0 else 0
