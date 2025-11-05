"""
特性曲线优化器 - 根据实测数据优化和校准水泵特性曲线

功能：
1. 曲线拟合（多项式、样条插值）
2. 异常点检测和处理
3. 曲线单调性验证
4. 曲线质量评估
5. 曲线点更新

作者：System
创建时间：2025-10-05
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import numpy as np
from scipy import interpolate, stats
from scipy.optimize import curve_fit

from app.adapters.db import get_connection
from app.core.exceptions import DatabaseError, DataValidationError

logger = logging.getLogger(__name__)


class CurveOptimizer:
    """
    特性曲线优化器类
    
    使用多项式拟合和样条插值优化水泵特性曲线
    """
    
    def __init__(self, min_samples: int = 20):
        """
        初始化曲线优化器

        Args:
            min_samples: 最小样本数，少于此数量不进行优化
        """
        logger.info("[流程-开始] [曲线优化器初始化]")

        if min_samples < 10:
            raise ValueError(f"最小样本数必须≥10，当前值：{min_samples}")

        self.min_samples = min_samples

        logger.info(
            "[核心-初始化] CurveOptimizer 初始化完成",
            extra={"extra_data": {"min_samples": min_samples}}
        )
    
    def optimize_curve(
        self,
        device_id: int,
        curve_type: str,
        measured_data: Dict[str, np.ndarray],
        current_curve: Optional[List[Tuple[float, float]]] = None,
        method: str = 'polynomial',
        polynomial_degree: int = 3
    ) -> Tuple[List[Tuple[float, float]], Dict[str, Any]]:
        """
        优化特性曲线
        
        Args:
            device_id: 设备ID
            curve_type: 曲线类型（Q-H, Q-P, Q-eta）
            measured_data: 实测数据 {'flow_rate': array, 'value': array}
            current_curve: 当前曲线点列表 [(flow, value), ...]
            method: 优化方法（polynomial, spline）
            polynomial_degree: 多项式阶数（2-4）
        
        Returns:
            (优化后的曲线点列表, 优化指标字典)
        """
        logger.info(
            "[流程-开始] [曲线优化]",
            extra={
                "extra_data": {
                    "device_id": device_id,
                    "curve_type": curve_type,
                    "method": method,
                    "polynomial_degree": polynomial_degree,
                    "sample_count": len(measured_data.get('flow_rate', [])),
                }
            }
        )

        # 验证输入数据
        self._validate_input_data(measured_data)

        flow_rates = measured_data['flow_rate']
        values = measured_data['value']

        logger.info(
            "[流程-阶段] [数据验证完成]",
            extra={
                "extra_data": {
                    "total_samples": len(flow_rates),
                    "min_required": self.min_samples,
                }
            }
        )

        # 检查样本数量
        if len(flow_rates) < self.min_samples:
            logger.error(
                "[流程-错误] [样本数量不足]",
                extra={
                    "extra_data": {
                        "device_id": device_id,
                        "curve_type": curve_type,
                        "actual_samples": len(flow_rates),
                        "min_required": self.min_samples,
                    }
                }
            )
            raise DataValidationError(
                f"样本数量不足：{len(flow_rates)} < {self.min_samples}"
            )

        # 异常点检测和处理
        flow_rates_clean, values_clean, outlier_mask = self._detect_outliers(
            flow_rates, values
        )

        logger.info(
            "[流程-阶段] [异常点检测完成]",
            extra={
                "extra_data": {
                    "outliers_removed": int(np.sum(outlier_mask)),
                    "clean_samples": len(flow_rates_clean),
                    "outlier_rate": float(np.sum(outlier_mask) / len(flow_rates)),
                }
            }
        )
        
        # 曲线拟合
        logger.info(
            "[流程-阶段] [开始曲线拟合]",
            extra={
                "extra_data": {
                    "method": method,
                    "polynomial_degree": polynomial_degree if method == 'polynomial' else None,
                }
            }
        )

        if method == 'polynomial':
            fitted_curve = self._fit_polynomial(
                flow_rates_clean, values_clean, polynomial_degree
            )
        elif method == 'spline':
            fitted_curve = self._fit_spline(flow_rates_clean, values_clean)
        else:
            logger.error(
                "[流程-错误] [不支持的优化方法]",
                extra={"extra_data": {"method": method}}
            )
            raise ValueError(f"不支持的优化方法: {method}")

        logger.info(
            "[流程-阶段] [曲线拟合完成]",
            extra={"extra_data": {"curve_points": len(fitted_curve)}}
        )

        # 验证曲线单调性
        if not self._validate_monotonicity(fitted_curve, curve_type):
            logger.warning(
                "[流程-跳过] [曲线单调性验证失败]",
                extra={
                    "extra_data": {
                        "device_id": device_id,
                        "curve_type": curve_type,
                        "reason": "单调性验证失败",
                    }
                }
            )
            if current_curve:
                return current_curve, {"success": False, "reason": "单调性验证失败"}
            else:
                raise DataValidationError("曲线单调性验证失败且无原始曲线")
        
        # 计算曲线质量指标
        quality_metrics = self._calculate_curve_quality(
            measured_data, fitted_curve
        )

        logger.info(
            "[流程-阶段] [质量评估完成]",
            extra={
                "extra_data": {
                    "rmse": quality_metrics.get('rmse'),
                    "r2": quality_metrics.get('r2'),
                    "quality_score": quality_metrics.get('quality_score'),
                }
            }
        )

        # 更新数据库
        self._update_curve_points(
            device_id=device_id,
            curve_type=curve_type,
            new_points=fitted_curve,
            quality_score=quality_metrics['quality_score'],
            sample_count=len(flow_rates_clean),
            method=method
        )

        logger.info(
            "[流程-完成] [曲线优化完成]",
            extra={
                "extra_data": {
                    "device_id": device_id,
                    "curve_type": curve_type,
                    "curve_points": len(fitted_curve),
                    "rmse": quality_metrics['rmse'],
                    "quality_score": quality_metrics['quality_score'],
                    "sample_count": len(flow_rates_clean),
                }
            }
        )

        return fitted_curve, quality_metrics
    
    def _validate_input_data(self, measured_data: Dict[str, np.ndarray]) -> None:
        """验证输入数据"""
        if 'flow_rate' not in measured_data or 'value' not in measured_data:
            raise DataValidationError("实测数据必须包含flow_rate和value字段")
        
        flow_rates = measured_data['flow_rate']
        values = measured_data['value']
        
        if len(flow_rates) != len(values):
            raise DataValidationError(
                f"flow_rate和value长度不一致: {len(flow_rates)} != {len(values)}"
            )
        
        if len(flow_rates) == 0:
            raise DataValidationError("数据为空")
        
        # 检查NaN和Inf
        if np.any(np.isnan(flow_rates)) or np.any(np.isnan(values)):
            raise DataValidationError("数据包含NaN")
        
        if np.any(np.isinf(flow_rates)) or np.any(np.isinf(values)):
            raise DataValidationError("数据包含Inf")
    
    def _detect_outliers(
        self,
        flow_rates: np.ndarray,
        values: np.ndarray,
        z_threshold: float = 2.5
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        检测异常点（使用Z-score方法）

        Returns:
            (清洗后的flow_rates, 清洗后的values, 异常点掩码)
        """
        # 计算Z-score
        z_scores = np.abs(stats.zscore(values))

        # 标记异常点
        outlier_mask = z_scores > z_threshold

        # 移除异常点
        flow_rates_clean = flow_rates[~outlier_mask]
        values_clean = values[~outlier_mask]

        return flow_rates_clean, values_clean, outlier_mask
    
    def _fit_polynomial(
        self,
        flow_rates: np.ndarray,
        values: np.ndarray,
        degree: int = 3
    ) -> List[Tuple[float, float]]:
        """
        多项式拟合
        
        Args:
            flow_rates: 流量数组
            values: 值数组
            degree: 多项式阶数（2-4）
        
        Returns:
            拟合后的曲线点列表
        """
        # 拟合多项式
        coeffs = np.polyfit(flow_rates, values, degree)
        poly_func = np.poly1d(coeffs)
        
        # 生成拟合点（在数据范围内均匀分布）
        flow_min = np.min(flow_rates)
        flow_max = np.max(flow_rates)
        
        # 生成10-20个点
        n_points = min(20, max(10, len(flow_rates) // 5))
        fitted_flow = np.linspace(flow_min, flow_max, n_points)
        fitted_values = poly_func(fitted_flow)
        
        # 转换为列表
        fitted_curve = [(float(f), float(v)) for f, v in zip(fitted_flow, fitted_values)]
        
        return fitted_curve
    
    def _fit_spline(
        self,
        flow_rates: np.ndarray,
        values: np.ndarray,
        smoothing: float = 0.1
    ) -> List[Tuple[float, float]]:
        """
        样条插值拟合
        
        Args:
            flow_rates: 流量数组
            values: 值数组
            smoothing: 平滑参数（0=插值，>0=平滑）
        
        Returns:
            拟合后的曲线点列表
        """
        # 排序（样条插值要求x单调）
        sorted_indices = np.argsort(flow_rates)
        flow_sorted = flow_rates[sorted_indices]
        values_sorted = values[sorted_indices]
        
        # 创建样条插值
        spline = interpolate.UnivariateSpline(
            flow_sorted, values_sorted, s=smoothing
        )
        
        # 生成拟合点
        flow_min = np.min(flow_rates)
        flow_max = np.max(flow_rates)
        
        n_points = min(20, max(10, len(flow_rates) // 5))
        fitted_flow = np.linspace(flow_min, flow_max, n_points)
        fitted_values = spline(fitted_flow)
        
        # 转换为列表
        fitted_curve = [(float(f), float(v)) for f, v in zip(fitted_flow, fitted_values)]

        return fitted_curve

    def _validate_monotonicity(
        self,
        curve_points: List[Tuple[float, float]],
        curve_type: str
    ) -> bool:
        """
        验证曲线单调性

        Args:
            curve_points: 曲线点列表
            curve_type: 曲线类型（Q-H, Q-P, Q-eta）

        Returns:
            是否满足单调性要求
        """
        if len(curve_points) < 2:
            return False

        # 提取流量和值
        flows = np.array([p[0] for p in curve_points])
        values = np.array([p[1] for p in curve_points])

        # 计算差分
        flow_diff = np.diff(flows)
        value_diff = np.diff(values)

        # 流量必须单调递增
        if not np.all(flow_diff > 0):
            logger.warning("流量不是单调递增")
            return False

        # Q-H曲线：扬程应该单调递减（或基本递减）
        if curve_type == 'Q-H':
            # 允许少量上升点（<5%），提高单调性要求
            increasing_points = np.sum(value_diff > 0)
            if increasing_points > len(value_diff) * 0.05:
                logger.warning(
                    f"Q-H曲线单调性不足: {increasing_points}/{len(value_diff)} 个上升点"
                )
                return False

        # Q-eta曲线：效率应该先增后减（允许更灵活）
        elif curve_type == 'Q-eta':
            # 效率曲线比较复杂，只检查是否有合理的峰值
            max_idx = np.argmax(values)
            if max_idx == 0 or max_idx == len(values) - 1:
                logger.warning("Q-eta曲线峰值在边界")
                return False

        # Q-P曲线：功率应该先增后减或单调递增
        elif curve_type == 'Q-P':
            # 功率曲线比较灵活，只检查是否有异常波动
            # 计算相对变化（避免除以0）
            mask = values[:-1] > 1e-6
            if np.any(mask):
                rel_changes = np.abs(value_diff[mask] / values[:-1][mask])
                if np.any(rel_changes > 0.5):  # 单步变化>50%认为异常（从100%降低到50%）
                    logger.warning("Q-P曲线有异常波动")
                    return False

        return True

    def _calculate_curve_quality(
        self,
        measured_data: Dict[str, np.ndarray],
        fitted_curve: List[Tuple[float, float]]
    ) -> Dict[str, float]:
        """
        计算曲线质量指标

        Args:
            measured_data: 实测数据
            fitted_curve: 拟合曲线

        Returns:
            质量指标字典
        """
        flow_rates = measured_data['flow_rate']
        values = measured_data['value']

        # 创建插值函数
        curve_flows = np.array([p[0] for p in fitted_curve])
        curve_values = np.array([p[1] for p in fitted_curve])

        interp_func = interpolate.interp1d(
            curve_flows, curve_values,
            kind='linear',
            fill_value='extrapolate'
        )

        # 计算拟合值
        fitted_values = interp_func(flow_rates)

        # 计算残差
        residuals = values - fitted_values

        # RMSE
        rmse = np.sqrt(np.mean(residuals ** 2))

        # MAE
        mae = np.mean(np.abs(residuals))

        # R²
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((values - np.mean(values)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # MAPE
        mask = np.abs(values) > 1e-6
        if np.any(mask):
            mape = np.mean(np.abs(residuals[mask] / values[mask])) * 100
        else:
            mape = 0

        # 质量分数（综合评分0-1）
        # 基于R²（60%）和样本数（40%）
        r2_score = max(0, min(1, r2))
        sample_score = min(len(flow_rates) / 100, 1.0)  # 100个样本为满分
        quality_score = 0.6 * r2_score + 0.4 * sample_score

        return {
            'rmse': float(rmse),
            'mae': float(mae),
            'r2': float(r2),
            'mape': float(mape),
            'quality_score': float(quality_score),
            'sample_count': len(flow_rates)
        }

    def _update_curve_points(
        self,
        device_id: int,
        curve_type: str,
        new_points: List[Tuple[float, float]],
        quality_score: float,
        sample_count: int,
        method: str
    ) -> None:
        """更新数据库中的曲线点

        使用UPSERT策略（ON CONFLICT ... DO UPDATE），确保事务安全：
        1. 获取当前最大版本号
        2. 使用新版本号进行UPSERT操作
        3. 如果flow_rate已存在，更新为新值和新版本号
        4. 如果flow_rate不存在，插入新记录
        5. 整个操作在事务中执行，失败时自动回滚
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 获取当前最大版本号
                    cur.execute("""
                        SELECT COALESCE(MAX(curve_version), 0)
                        FROM pump_characteristic_curves
                        WHERE device_id = %s AND curve_type = %s
                    """, (device_id, curve_type))

                    current_version = cur.fetchone()[0]
                    new_version = current_version + 1

                    # 去重：如果有重复的flow_rate，保留最后一个
                    unique_points = {}
                    for flow_rate, value in new_points:
                        unique_points[flow_rate] = value

                    if len(unique_points) < len(new_points):
                        logger.warning(
                            f"曲线点包含重复的flow_rate，已去重: {len(new_points)} -> {len(unique_points)}",
                            extra={
                                "device_id": device_id,
                                "curve_type": curve_type,
                                "original_count": len(new_points),
                                "unique_count": len(unique_points)
                            }
                        )

                    # 使用UPSERT策略更新曲线点
                    upserted_count = 0
                    for flow_rate, value in unique_points.items():
                        cur.execute("""
                            INSERT INTO pump_characteristic_curves
                            (device_id, curve_type, speed, frequency, flow_rate, value,
                             source, curve_version, quality_score, sample_count,
                             last_optimized_at, optimization_method)
                            VALUES (%s, %s, NULL, NULL, %s, %s, %s, %s, %s, %s, NOW(), %s)
                            ON CONFLICT (device_id, curve_type,
                                         COALESCE(speed, -1),
                                         COALESCE(frequency, -1),
                                         flow_rate)
                            DO UPDATE SET
                                value = EXCLUDED.value,
                                source = EXCLUDED.source,
                                curve_version = EXCLUDED.curve_version,
                                quality_score = EXCLUDED.quality_score,
                                sample_count = EXCLUDED.sample_count,
                                last_optimized_at = EXCLUDED.last_optimized_at,
                                optimization_method = EXCLUDED.optimization_method,
                                updated_at = NOW()
                        """, (
                            device_id, curve_type, flow_rate, value,
                            'optimized', new_version, quality_score, sample_count, method
                        ))
                        upserted_count += 1

                    # 验证UPSERT成功
                    if upserted_count != len(unique_points):
                        raise DatabaseError(
                            f"曲线点UPSERT不完整: 预期{len(unique_points)}个，实际处理{upserted_count}个"
                        )

                    # 提交事务
                    conn.commit()

                    logger.debug(
                        f"曲线更新事务完成: UPSERT {upserted_count}个点",
                        extra={
                            "device_id": device_id,
                            "curve_type": curve_type,
                            "new_version": new_version,
                            "upserted": upserted_count
                        }
                    )

                    logger.info(
                        f"曲线点已更新: {len(unique_points)} 个点，版本 {new_version}",
                        extra={
                            "device_id": device_id,
                            "curve_type": curve_type,
                            "version": new_version,
                            "points": len(unique_points)
                        }
                    )

        except Exception as e:
            logger.error(f"更新曲线点失败: {e}", exc_info=True)
            raise DatabaseError(f"更新曲线点失败: {e}") from e

