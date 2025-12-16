"""
历史数据评估器 (app.services.characteristic_curves.shared.historical_data_evaluator)

本模块提供曲线预测能力的评估功能：
- 核心功能：用独立测试数据验证曲线预测能力
- 数据质量评估：完整性、一致性、异常值
- 稳定性分析：拟合结果的历史稳定性
- 版本对比：对比不同版本的拟合结果

设计决策（2025-12-08）：
- 直接读取 `fact_measurements` 表中已由缺失指标计算系统计算的指标
- 指标列：`pump_flow_rate`、`pump_head`、`pump_efficiency`

使用方式：
    from app.services.characteristic_curves.shared import HistoricalDataEvaluator
    
    evaluator = HistoricalDataEvaluator(data_extractor)
    result = evaluator.evaluate_prediction_accuracy(device_id, curve_type, predict_func, test_window)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

# 曲线类型与指标列的映射（直接从fact_measurements读取）
CURVE_METRICS = {
    'qh': {'x': 'pump_flow_rate', 'y': 'pump_head'},
    'qp': {'x': 'pump_flow_rate', 'y': 'pump_active_power'},
    'qeta': {'x': 'pump_flow_rate', 'y': 'pump_efficiency'}
}


@dataclass
class TimeWindow:
    """时间窗口"""
    start: datetime
    end: datetime
    point_count: int = 0


@dataclass
class TimeWindowSplitResult:
    """时间窗口划分结果"""
    fit_window: TimeWindow
    test_window: TimeWindow
    total_days: int = 0
    fit_days: int = 0
    test_days: int = 0
    can_evaluate: bool = True
    warnings: List[str] = field(default_factory=list)


class HistoricalDataEvaluator:
    """历史数据评估器

    评估曲线对独立测试数据的预测能力。
    合格标准：within_5_percent ≥ 90%（90%的测试点偏差小于5%）
    """

    def __init__(self, data_extractor: Optional[Any] = None):
        """初始化历史数据评估器

        Args:
            data_extractor: 数据提取器（可选，用于从数据库提取数据）
        """
        self._extractor = data_extractor
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

        self._logger.info(
            "[历史评估] 初始化",
            extra={"extra_data": {"组件": "HistoricalDataEvaluator"}}
        )

    def evaluate_prediction_accuracy(
        self,
        device_id: int,
        curve_type: str,
        predict_func: Callable[[float], float],
        test_window: TimeWindow,
        test_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """评估曲线对独立测试数据的预测能力（核心方法）

        Args:
            device_id: 设备ID
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            predict_func: 预测函数，输入X返回预测Y
            test_window: 测试窗口
            test_data: 测试数据（可选，如不提供则从数据库读取）

        Returns:
            Dict: {
                'test_period': {'start': datetime, 'end': datetime},
                'test_point_count': int,
                'deviation_stats': {...},
                'pass_rate': {'within_5_percent': float, 'within_10_percent': float},
                'segment_evaluation': {...},
                'overall_passed': bool
            }
        """
        if curve_type not in CURVE_METRICS:
            self._logger.error(f"[历史评估] 不支持的曲线类型: {curve_type}")
            return {'error': f'不支持的曲线类型: {curve_type}', 'overall_passed': False}

        x_col = CURVE_METRICS[curve_type]['x']
        y_col = CURVE_METRICS[curve_type]['y']

        # 获取测试数据
        if test_data is None:
            if self._extractor is None:
                self._logger.error("[历史评估] 未提供测试数据且无数据提取器")
                return {'error': '未提供测试数据', 'overall_passed': False}
            test_data = self._extract_test_data(
                device_id, curve_type, test_window)

        if test_data is None or len(test_data) == 0:
            self._logger.warning("[历史评估] 测试数据为空")
            return {
                'test_period': {'start': test_window.start, 'end': test_window.end},
                'test_point_count': 0,
                'deviation_stats': {},
                'pass_rate': {'within_5_percent': 0.0, 'within_10_percent': 0.0},
                'overall_passed': False,
                'error': '测试数据为空'
            }

        # 过滤有效数据
        valid_data = test_data[[x_col, y_col]].dropna()
        valid_data = valid_data[(valid_data[x_col] > 0)
                                & (valid_data[y_col] > 0)]

        if len(valid_data) == 0:
            return {
                'test_period': {'start': test_window.start, 'end': test_window.end},
                'test_point_count': 0,
                'overall_passed': False,
                'error': '无有效测试数据点'
            }

        X = valid_data[x_col].values
        Y_actual = valid_data[y_col].values

        # 计算预测值和偏差
        Y_pred = np.array([predict_func(x) for x in X])
        relative_deviations = np.abs(
            (Y_pred - Y_actual) / Y_actual) * 100  # 百分比

        return self._build_evaluation_result(
            test_window, X, Y_actual, Y_pred, relative_deviations
        )

    def _build_evaluation_result(
        self,
        test_window: TimeWindow,
        X: np.ndarray,
        Y_actual: np.ndarray,
        Y_pred: np.ndarray,
        relative_deviations: np.ndarray
    ) -> Dict[str, Any]:
        """构建评估结果"""
        test_point_count = len(X)

        # 计算偏差统计
        deviation_stats = {
            'mean_relative_deviation': float(np.mean(relative_deviations)),
            'max_relative_deviation': float(np.max(relative_deviations)),
            'min_relative_deviation': float(np.min(relative_deviations)),
            'std_relative_deviation': float(np.std(relative_deviations)),
            'p50_deviation': float(np.percentile(relative_deviations, 50)),
            'p90_deviation': float(np.percentile(relative_deviations, 90)),
            'p95_deviation': float(np.percentile(relative_deviations, 95))
        }

        # 计算通过率
        within_5_percent = float(np.mean(relative_deviations <= 5.0))
        within_10_percent = float(np.mean(relative_deviations <= 10.0))

        pass_rate = {
            'within_5_percent': within_5_percent,
            'within_10_percent': within_10_percent
        }

        # 分段评估
        segment_evaluation = self._evaluate_segments(X, relative_deviations)

        # 判断是否通过（90%的点偏差小于5%）
        overall_passed = within_5_percent >= 0.90

        result = {
            'test_period': {
                'start': test_window.start.isoformat() if isinstance(test_window.start, datetime) else str(test_window.start),
                'end': test_window.end.isoformat() if isinstance(test_window.end, datetime) else str(test_window.end)
            },
            'test_point_count': test_point_count,
            'deviation_stats': deviation_stats,
            'pass_rate': pass_rate,
            'segment_evaluation': segment_evaluation,
            'overall_passed': overall_passed
        }

        self._logger.info(
            "[历史评估] 预测准确性评估完成",
            extra={"extra_data": {
                "测试点数": test_point_count,
                "5%内通过率": f"{within_5_percent:.2%}",
                "总体通过": overall_passed
            }}
        )

        return result

    def _evaluate_segments(
        self,
        X: np.ndarray,
        deviations: np.ndarray
    ) -> Dict[str, Dict[str, Any]]:
        """分段评估"""
        x_min, x_max = np.min(X), np.max(X)
        x_range = x_max - x_min

        if x_range <= 0:
            return {}

        # 按流量分为低/中/高三段
        segments = {
            'low_flow': {'range': [0, 0.4]},
            'medium_flow': {'range': [0.4, 0.8]},
            'high_flow': {'range': [0.8, 1.2]}
        }

        result = {}
        for seg_name, seg_config in segments.items():
            low_ratio, high_ratio = seg_config['range']
            low_bound = x_min + low_ratio * x_range
            high_bound = x_min + high_ratio * x_range

            mask = (X >= low_bound) & (X < high_bound)
            seg_deviations = deviations[mask]

            if len(seg_deviations) > 0:
                result[seg_name] = {
                    'range': [float(low_bound), float(high_bound)],
                    'point_count': int(np.sum(mask)),
                    'mean_deviation': float(np.mean(seg_deviations)),
                    'max_deviation': float(np.max(seg_deviations))
                }

        return result

    def _extract_test_data(
        self,
        device_id: int,
        curve_type: str,
        test_window: TimeWindow
    ) -> pd.DataFrame:
        """从数据库提取测试数据

        Raises:
            ValueError: 数据提取器未初始化
            Exception: 数据提取失败
        """
        if self._extractor is None:
            raise ValueError("数据提取器未初始化，请在构造函数中提供extractor参数")

        try:
            return self._extractor.extract(
                device_id=device_id,
                curve_type=curve_type,
                start_time=test_window.start,
                end_time=test_window.end
            )
        except Exception as e:
            self._logger.error(
                f"[历史评估] 提取测试数据失败: {e}",
                exc_info=True
            )
            raise

    def evaluate_data_quality(
        self,
        data: pd.DataFrame,
        required_columns: List[str]
    ) -> Dict[str, Any]:
        """评估数据质量

        Args:
            data: 待评估的数据
            required_columns: 必需的列名列表

        Returns:
            Dict: {
                'row_count': int,
                'completeness': {'column': coverage_ratio},
                'missing_columns': [...],
                'overall_quality_score': float
            }
        """
        result = {
            'row_count': len(data),
            'completeness': {},
            'missing_columns': [],
            'overall_quality_score': 0.0
        }

        if len(data) == 0:
            return result

        # 检查缺失列
        for col in required_columns:
            if col not in data.columns:
                result['missing_columns'].append(col)
            else:
                # 计算非空比例
                coverage = data[col].notna().mean()
                result['completeness'][col] = float(coverage)

        # 计算总体质量分数
        if result['completeness']:
            result['overall_quality_score'] = float(
                np.mean(list(result['completeness'].values()))
            )

        return result

    def evaluate_stability(
        self,
        device_id: int,
        curve_type: str,
        versions: List[str]
    ) -> Dict[str, Any]:
        """评估拟合结果稳定性

        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            versions: 版本列表

        Returns:
            Dict: {
                'r2_variance': float,
                'stability_score': float,
                'evaluated_versions': int
            }
        """
        # 从数据库读取历史版本的R²和RMSE数据
        try:
            from app.services.characteristic_curves.shared import ResultStorage
            storage = ResultStorage()

            r2_values = []
            rmse_values = []

            for version in versions:
                try:
                    fit_result = storage.load(
                        device_id=device_id,
                        curve_type=curve_type,
                        version=version
                    )
                    if fit_result and fit_result.r_squared is not None:
                        r2_values.append(fit_result.r_squared)
                        if fit_result.rmse is not None:
                            rmse_values.append(fit_result.rmse)
                except Exception as e:
                    self._logger.warning(
                        f"[历史评估] 加载版本{version}失败: {e}"
                    )
                    continue

            if len(r2_values) < 2:
                self._logger.warning(
                    f"[历史评估] 可用版本不足({len(r2_values)}<2)，稳定性评估无效"
                )
                return {
                    'r2_variance': 0.0,
                    'stability_score': 0.0,
                    'evaluated_versions': len(r2_values),
                    'warning': 'insufficient_versions'
                }

            # 计算R²方差和稳定性得分
            r2_variance = float(np.var(r2_values))
            r2_std = float(np.std(r2_values))
            r2_mean = float(np.mean(r2_values))

            # 稳定性得分: 方差越小得分越高 (0-1)
            # 使用公式: score = exp(-10 * variance)
            stability_score = float(np.exp(-10 * r2_variance))

            self._logger.info(
                "[历史评估] 稳定性评估完成",
                extra={"extra_data": {
                    "设备ID": device_id,
                    "曲线类型": curve_type,
                    "版本数": len(r2_values),
                    "R²均值": r2_mean,
                    "R²方差": r2_variance,
                    "稳定性得分": stability_score
                }}
            )

            result = {
                'r2_variance': r2_variance,
                'r2_std': r2_std,
                'r2_mean': r2_mean,
                'stability_score': stability_score,
                'evaluated_versions': len(r2_values)
            }

            if rmse_values:
                result['rmse_variance'] = float(np.var(rmse_values))
                result['rmse_mean'] = float(np.mean(rmse_values))

            return result

        except Exception as e:
            self._logger.error(
                f"[历史评估] 稳定性评估失败: {e}",
                extra={"extra_data": {"错误": str(e)}}
            )
            return {
                'r2_variance': 0.0,
                'stability_score': 0.0,
                'evaluated_versions': 0,
                'error': str(e)
            }

    def compare_versions(
        self,
        device_id: int,
        curve_type: str,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """对比两个版本的拟合结果

        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            version1: 版本1
            version2: 版本2

        Returns:
            Dict: 包含两个版本的对比信息
        """
        # 从数据库读取两个版本的拟合结果
        try:
            from app.services.characteristic_curves.shared import ResultStorage
            storage = ResultStorage()

            result1 = storage.load(
                device_id=device_id,
                curve_type=curve_type,
                version=version1
            )
            result2 = storage.load(
                device_id=device_id,
                curve_type=curve_type,
                version=version2
            )

            if not result1 or not result2:
                missing = []
                if not result1:
                    missing.append(version1)
                if not result2:
                    missing.append(version2)
                return {
                    'device_id': device_id,
                    'curve_type': curve_type,
                    'version1': version1,
                    'version2': version2,
                    'error': f'版本不存在: {missing}'
                }

            # 计算指标差异
            r2_diff = abs(result1.r_squared - result2.r_squared)
            rmse_diff = abs(
                result1.rmse - result2.rmse) if result1.rmse and result2.rmse else None

            # 参数变化
            param_changes = {}
            if result1.coefficients and result2.coefficients:
                all_keys = set(result1.coefficients.keys()) | set(
                    result2.coefficients.keys())
                for key in all_keys:
                    val1 = result1.coefficients.get(key, 0)
                    val2 = result2.coefficients.get(key, 0)
                    param_changes[key] = {
                        'v1': float(val1),
                        'v2': float(val2),
                        'change': float(val2 - val1),
                        'change_pct': float((val2 - val1) / val1 * 100) if val1 != 0 else None
                    }

            self._logger.info(
                "[历史评估] 版本对比完成",
                extra={"extra_data": {
                    "设备ID": device_id,
                    "曲线类型": curve_type,
                    "版本1": version1,
                    "版本2": version2,
                    "R²差异": r2_diff
                }}
            )

            comparison = {
                'r2_diff': float(r2_diff),
                'r2_v1': float(result1.r_squared),
                'r2_v2': float(result2.r_squared),
                'param_changes': param_changes
            }

            if rmse_diff is not None:
                comparison['rmse_diff'] = float(rmse_diff)
                comparison['rmse_v1'] = float(result1.rmse)
                comparison['rmse_v2'] = float(result2.rmse)

            return {
                'device_id': device_id,
                'curve_type': curve_type,
                'version1': version1,
                'version2': version2,
                'comparison': comparison
            }

        except Exception as e:
            self._logger.error(
                f"[历史评估] 版本对比失败: {e}",
                extra={"extra_data": {"错误": str(e)}}
            )
            return {
                'device_id': device_id,
                'curve_type': curve_type,
                'version1': version1,
                'version2': version2,
                'error': str(e)
            }
