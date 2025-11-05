"""
参数优化器 - 使用递归最小二乘法(RLS)优化计算参数

功能：
1. 实现RLS算法进行在线参数估计
2. 支持参数约束（上下界）
3. 计算参数置信度
4. 保存优化历史记录
5. 评估优化效果

作者：System
创建时间：2025-10-05
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import numpy as np
from scipy import stats

from app.adapters.db import get_connection
from app.core.exceptions import DatabaseError, DataValidationError

logger = logging.getLogger(__name__)


class ParameterOptimizer:
    """
    参数优化器类
    
    使用递归最小二乘法(RLS)进行参数优化
    """
    
    def __init__(self, forgetting_factor: float = 0.98):
        """
        初始化参数优化器

        Args:
            forgetting_factor: 遗忘因子λ (0 < λ ≤ 1)
                - λ = 1: 标准RLS，所有数据权重相同
                - λ < 1: 指数遗忘RLS，旧数据权重衰减
                - 推荐值：0.95-0.99
        """
        logger.info("[流程-开始] [参数优化器初始化]")

        if not 0 < forgetting_factor <= 1:
            raise ValueError(f"遗忘因子必须在(0, 1]范围内，当前值：{forgetting_factor}")

        self.forgetting_factor = forgetting_factor

        logger.info(
            "[核心-初始化] ParameterOptimizer 初始化完成",
            extra={"extra_data": {"forgetting_factor": forgetting_factor}}
        )
    
    def optimize_parameters(
        self,
        method_id: str,
        measured_data: Dict[str, np.ndarray],
        calculated_data: Dict[str, np.ndarray],
        current_params: Dict[str, float],
        param_bounds: Optional[Dict[str, Tuple[float, float]]] = None,
        rated_params: Optional[Dict[str, float]] = None,
        device_id: Optional[int] = None,
        station_id: Optional[int] = None
    ) -> Tuple[Dict[str, float], Dict[str, Any]]:
        """
        优化参数

        Args:
            method_id: 计算方法ID
            measured_data: 实测数据字典 {变量名: 数组}
            calculated_data: 计算数据字典 {变量名: 数组}
            current_params: 当前参数字典 {参数名: 值}
            param_bounds: 参数约束字典 {参数名: (最小值, 最大值)}
            rated_params: 设备额定参数字典 {参数名: 值}（可选，用于约束优化）
            device_id: 设备ID（可选）
            station_id: 站点ID（可选）

        Returns:
            (优化后的参数字典, 优化指标字典)
        """
        logger.info(
            "[流程-开始] [参数优化]",
            extra={
                "extra_data": {
                    "method_id": method_id,
                    "device_id": device_id,
                    "station_id": station_id,
                    "param_count": len(current_params),
                    "current_params": current_params,
                }
            }
        )

        # 验证输入数据
        self._validate_input_data(measured_data, calculated_data)

        logger.info(
            "[流程-阶段] [数据验证完成]",
            extra={
                "extra_data": {
                    "measured_vars": len(measured_data),
                    "calculated_vars": len(calculated_data),
                }
            }
        )

        # 构建观测矩阵和输出向量
        X, y = self._build_observation_matrix(measured_data, calculated_data, method_id)

        if X is None or y is None:
            logger.error(
                "[流程-错误] [无法构建观测矩阵]",
                extra={"extra_data": {"method_id": method_id}}
            )
            raise DataValidationError("无法构建观测矩阵")

        logger.info(
            "[流程-阶段] [观测矩阵构建完成]",
            extra={
                "extra_data": {
                    "matrix_shape": X.shape if hasattr(X, 'shape') else None,
                    "observation_count": len(y) if y is not None else 0,
                }
            }
        )

        # 将参数转换为向量
        param_names = sorted(current_params.keys())
        theta = np.array([current_params[name] for name in param_names])

        # 加载上次优化的协方差矩阵P（如果存在）
        P_previous, rls_iterations_previous = self._load_covariance_matrix(
            method_id=method_id,
            device_id=device_id,
            station_id=station_id,
            param_names=param_names
        )

        # 初始化协方差矩阵
        n_params = len(current_params)
        if P_previous is not None:
            # 使用上次优化的P矩阵（增量优化）
            P = P_previous
            logger.info(
                "[流程-阶段] [加载历史P矩阵]",
                extra={
                    "extra_data": {
                        "method_id": method_id,
                        "device_id": device_id,
                        "P_trace": float(np.trace(P)),
                        "P_condition": float(np.linalg.cond(P)),
                        "previous_iterations": rls_iterations_previous,
                        "optimization_mode": "incremental"
                    }
                }
            )
        else:
            # 首次优化，初始化P矩阵
            P = np.eye(n_params) * 1000
            rls_iterations_previous = 0
            logger.info(
                "[流程-阶段] [初始化P矩阵]",
                extra={
                    "extra_data": {
                        "method_id": method_id,
                        "device_id": device_id,
                        "P_trace": float(np.trace(P)),
                        "optimization_mode": "first_time"
                    }
                }
            )

        # 应用RLS算法
        logger.info(
            "[流程-阶段] [开始RLS优化]",
            extra={
                "extra_data": {
                    "n_samples": X.shape[0],
                    "n_params": n_params,
                    "initial_params": theta.tolist(),
                    "forgetting_factor": self.forgetting_factor,
                    "data_stats": {
                        "X_mean": float(np.mean(X)),
                        "X_std": float(np.std(X)),
                        "y_mean": float(np.mean(y)),
                        "y_std": float(np.std(y))
                    }
                }
            }
        )
        theta_new, P_new, residuals = self.apply_rls(X, y, theta, P)

        # 计算累计迭代次数
        rls_iterations_new = rls_iterations_previous + X.shape[0]

        logger.info(
            "[流程-阶段] [RLS优化完成]",
            extra={
                "extra_data": {
                    "optimized_params": theta_new.tolist(),
                    "param_changes": {
                        param_names[i]: {
                            "old": float(theta[i]),
                            "new": float(theta_new[i]),
                            "change": float(theta_new[i] - theta[i]),
                            "change_pct": float((theta_new[i] - theta[i]) / theta[i] * 100) if theta[i] != 0 else None
                        }
                        for i in range(len(param_names))
                    },
                    "residual_stats": {
                        "mean": float(np.mean(residuals)) if residuals is not None else None,
                        "std": float(np.std(residuals)) if residuals is not None else None,
                        "max": float(np.max(np.abs(residuals))) if residuals is not None else None,
                        "median": float(np.median(np.abs(residuals))) if residuals is not None else None
                    },
                    "covariance_stats": {
                        "trace": float(np.trace(P_new)),
                        "condition_number": float(np.linalg.cond(P_new)),
                        "trace_reduction": float(np.trace(P) - np.trace(P_new)) if P_previous is not None else None,
                        "total_iterations": rls_iterations_new
                    }
                }
            }
        )

        # 应用参数约束
        if param_bounds:
            theta_new = self._apply_constraints(theta_new, param_names, param_bounds)
            logger.info("[流程-阶段] [参数约束应用完成]")

        # 应用额定参数约束（软约束）
        if rated_params:
            theta_new = self._apply_rated_constraints(
                theta_new, param_names, rated_params, current_params
            )
            logger.info(
                "[流程-阶段] [额定参数约束应用完成]",
                extra={
                    "extra_data": {
                        "rated_params_used": list(rated_params.keys()),
                        "constraint_type": "soft"
                    }
                }
            )

        # 验证参数合理性
        if not self._validate_parameters(theta_new, param_names, param_bounds):
            logger.warning(
                "[流程-跳过] [参数验证失败]",
                extra={
                    "extra_data": {
                        "method_id": method_id,
                        "reason": "优化后的参数不合理",
                    }
                }
            )
            return current_params, {"success": False, "reason": "参数验证失败"}
        
        # 构建新参数字典
        new_params = {name: float(theta_new[i]) for i, name in enumerate(param_names)}
        
        # 计算优化效果指标
        metrics = self._calculate_metrics(y, X @ theta_new, residuals, P_new)
        
        # 计算置信度
        confidence = self._calculate_confidence(residuals, P_new)
        metrics['confidence'] = confidence
        
        # 保存优化结果（包含P矩阵）
        self._save_optimization_result(
            method_id=method_id,
            old_params=current_params,
            new_params=new_params,
            metrics=metrics,
            device_id=device_id,
            station_id=station_id,
            P_matrix=P_new,  # 新增参数
            rls_iterations=rls_iterations_new  # 新增参数
        )

        logger.info(
            "[流程-完成] [参数优化完成]",
            extra={
                "extra_data": {
                    "method_id": method_id,
                    "device_id": device_id,
                    "station_id": station_id,
                    "rmse": metrics.get('rmse'),
                    "r2": metrics.get('r2'),
                    "confidence": confidence,
                    "param_changes": {
                        name: {"old": current_params.get(name), "new": new_params.get(name)}
                        for name in new_params.keys()
                    },
                }
            }
        )

        return new_params, metrics
    
    def apply_rls(
        self,
        X: np.ndarray,
        y: np.ndarray,
        theta: np.ndarray,
        P: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        应用递归最小二乘法(RLS)算法
        
        RLS更新公式：
        1. 增益矩阵：K(k) = P(k-1)φ(k) / [λ + φ(k)ᵀP(k-1)φ(k)]
        2. 参数更新：θ(k) = θ(k-1) + K(k)[y(k) - φ(k)ᵀθ(k-1)]
        3. 协方差更新：P(k) = [P(k-1) - K(k)φ(k)ᵀP(k-1)] / λ
        
        Args:
            X: 观测矩阵 (n_samples, n_params)
            y: 输出向量 (n_samples,)
            theta: 当前参数向量 (n_params,)
            P: 当前协方差矩阵 (n_params, n_params)
        
        Returns:
            (更新后的参数向量, 更新后的协方差矩阵, 残差向量)
        """
        n_samples = X.shape[0]
        residuals = np.zeros(n_samples)
        
        # 逐样本更新
        for k in range(n_samples):
            phi = X[k, :]  # 当前观测向量
            y_k = y[k]     # 当前输出
            
            # 预测误差
            e_k = y_k - phi @ theta
            residuals[k] = e_k
            
            # 计算增益矩阵
            P_phi = P @ phi
            denominator = self.forgetting_factor + phi @ P_phi

            # 数值稳定性保护：检查分母是否过小
            if abs(denominator) < 1e-10:
                logger.warning(
                    f"分母过小: {denominator:.2e}，跳过本次更新",
                    extra={"iteration": k, "denominator": float(denominator)}
                )
                continue

            K = P_phi / denominator

            # 数值稳定性保护：检查增益矩阵是否包含异常值
            if np.any(np.isnan(K)) or np.any(np.isinf(K)):
                logger.warning(
                    f"增益矩阵包含NaN或Inf，跳过本次更新",
                    extra={"iteration": k}
                )
                continue
            elif np.max(np.abs(K)) > 1e6:
                logger.warning(
                    f"增益矩阵元素过大: max={np.max(np.abs(K)):.2e}，限制范围",
                    extra={"iteration": k, "max_value": float(np.max(np.abs(K)))}
                )
                K = np.clip(K, -1e6, 1e6)

            # 更新参数
            theta_old = theta.copy()
            theta = theta + K * e_k

            # 数值稳定性保护：检查参数是否包含异常值
            if np.any(np.isnan(theta)) or np.any(np.isinf(theta)):
                logger.warning(
                    f"参数包含NaN或Inf，恢复到上一次值",
                    extra={"iteration": k, "theta_old": theta_old.tolist()}
                )
                theta = theta_old
                continue

            # 更新协方差矩阵
            P = (P - np.outer(K, P_phi)) / self.forgetting_factor

            # 数值稳定性保护：检查P矩阵是否包含异常值
            if np.any(np.isnan(P)) or np.any(np.isinf(P)):
                logger.warning(
                    f"P矩阵包含NaN或Inf，重新初始化",
                    extra={"iteration": k}
                )
                P = np.eye(len(theta)) * 1000
            elif np.max(np.abs(P)) > 1e8:
                # 只在P矩阵元素过大时才限制范围
                logger.warning(
                    f"P矩阵元素过大: max={np.max(np.abs(P)):.2e}，限制范围",
                    extra={"iteration": k, "max_value": float(np.max(np.abs(P)))}
                )
                P = np.clip(P, -1e8, 1e8)

            # 每100次迭代检查一次条件数并记录进度
            if k > 0 and k % 100 == 0:
                try:
                    cond = np.linalg.cond(P)
                    # 记录RLS优化进度
                    logger.debug(
                        f"RLS优化进度: {k}/{n_samples} ({k/n_samples*100:.1f}%)",
                        extra={
                            "iteration": k,
                            "total_samples": n_samples,
                            "current_params": theta.tolist(),
                            "condition_number": float(cond),
                            "avg_residual": float(np.mean(np.abs(residuals[:k])))
                        }
                    )
                    if cond > 1e12:
                        logger.warning(
                            f"P矩阵条件数过大: {cond:.2e}，重新初始化",
                            extra={"iteration": k, "condition_number": float(cond)}
                        )
                        # 重新初始化P矩阵
                        P = np.eye(len(theta)) * 1000
                except np.linalg.LinAlgError:
                    logger.warning(f"P矩阵条件数计算失败，重新初始化", extra={"iteration": k})
                    P = np.eye(len(theta)) * 1000

        return theta, P, residuals
    
    def _validate_input_data(
        self,
        measured_data: Dict[str, np.ndarray],
        calculated_data: Dict[str, np.ndarray]
    ) -> None:
        """验证输入数据"""
        if not measured_data or not calculated_data:
            raise DataValidationError("实测数据和计算数据不能为空")

        # 检查数据长度一致性
        lengths = set()
        for data in list(measured_data.values()) + list(calculated_data.values()):
            if isinstance(data, np.ndarray):
                lengths.add(len(data))

        if len(lengths) > 1:
            raise DataValidationError(f"数据长度不一致: {lengths}")

        if len(lengths) == 0 or list(lengths)[0] == 0:
            raise DataValidationError("数据为空")
    
    def _build_observation_matrix(
        self,
        measured_data: Dict[str, np.ndarray],
        calculated_data: Dict[str, np.ndarray],
        method_id: str
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        构建观测矩阵和输出向量

        根据不同的计算方法构建相应的观测矩阵：
        - pump_flow_rate_method_a: 对数线性化幂律模型
        - 其他方法: 通用线性模型（带警告）

        Args:
            measured_data: 实测数据字典
            calculated_data: 计算数据字典
            method_id: 计算方法ID

        Returns:
            (观测矩阵X, 输出向量y) 或 (None, None)
        """
        try:
            if method_id == 'pump_flow_rate_method_a':
                # 公式: Q_i = Q_total * (P_i^alpha * f_i^beta) / Σ(P_j^alpha * f_j^beta)
                # 对数线性化: log(Q_i/Q_total) = alpha*log(P_i) + beta*log(f_i) + log(1/Σ(...))
                # 简化为: log(Q_i/Q_total) ≈ alpha*log(P_i) + beta*log(f_i)

                # 提取数据
                P = measured_data.get('pump_active_power')
                f = measured_data.get('pump_frequency')
                Q_i = calculated_data.get('pump_flow_rate')
                Q_total = measured_data.get('main_pipeline_flow_rate')

                if P is None or f is None or Q_i is None or Q_total is None:
                    logger.error(
                        "pump_flow_rate_method_a缺少必要数据",
                        extra={
                            "has_power": P is not None,
                            "has_frequency": f is not None,
                            "has_flow": Q_i is not None,
                            "has_total_flow": Q_total is not None
                        }
                    )
                    return None, None

                # 过滤有效数据（必须为正值，避免log(0)或log(负数)）
                valid = (P > 0) & (f > 0) & (Q_i > 0) & (Q_total > 0)
                valid &= ~(np.isnan(P) | np.isnan(f) | np.isnan(Q_i) | np.isnan(Q_total))

                n_valid = np.sum(valid)
                if n_valid < 10:
                    logger.warning(
                        f"pump_flow_rate_method_a有效数据点不足: {n_valid}/10",
                        extra={"valid_samples": int(n_valid), "total_samples": len(P)}
                    )
                    return None, None

                # 对数变换
                log_P = np.log(P[valid])
                log_f = np.log(f[valid])
                log_Q_ratio = np.log(Q_i[valid] / Q_total[valid])

                # 构建观测矩阵 [log(P), log(f)]
                X = np.column_stack([log_P, log_f])
                y = log_Q_ratio

                logger.info(
                    "pump_flow_rate_method_a观测矩阵构建完成",
                    extra={
                        "method_id": method_id,
                        "valid_samples": int(n_valid),
                        "X_shape": X.shape,
                        "y_range": [float(np.min(y)), float(np.max(y))],
                        "y_mean": float(np.mean(y)),
                        "y_std": float(np.std(y))
                    }
                )

                return X, y

            else:
                # 通用线性模型（简化版本）
                logger.warning(
                    f"使用通用线性模型构建观测矩阵，可能不适用于非线性计算方法",
                    extra={"method_id": method_id}
                )

                # 获取输出变量（假设是第一个calculated_data的键）
                if not calculated_data:
                    return None, None

                output_key = list(calculated_data.keys())[0]
                y = calculated_data[output_key]

                # 构建观测矩阵（使用measured_data的所有变量）
                X_list = []
                for key in sorted(measured_data.keys()):
                    X_list.append(measured_data[key])

                if not X_list:
                    return None, None

                X = np.column_stack(X_list)

                # 添加常数项（截距）
                X = np.column_stack([np.ones(len(y)), X])

                # 过滤NaN
                valid = ~(np.isnan(y) | np.any(np.isnan(X), axis=1))
                X = X[valid]
                y = y[valid]

                if len(y) < 10:
                    logger.warning(
                        f"通用线性模型有效数据点不足: {len(y)}/10",
                        extra={"valid_samples": len(y)}
                    )
                    return None, None

                logger.info(
                    "通用线性模型观测矩阵构建完成",
                    extra={
                        "method_id": method_id,
                        "valid_samples": len(y),
                        "X_shape": X.shape
                    }
                )

                return X, y

        except Exception as e:
            logger.error(f"构建观测矩阵失败: {e}", exc_info=True)
            return None, None

    def _apply_constraints(
        self,
        theta: np.ndarray,
        param_names: List[str],
        param_bounds: Dict[str, Tuple[float, float]]
    ) -> np.ndarray:
        """应用参数约束"""
        theta_constrained = theta.copy()

        for i, name in enumerate(param_names):
            if name in param_bounds:
                min_val, max_val = param_bounds[name]

                # 先检查是否为NaN或Inf
                if np.isnan(theta[i]) or np.isinf(theta[i]):
                    logger.warning(
                        f"参数 {name} 包含NaN或Inf，使用中间值: {(min_val + max_val) / 2:.4f}",
                        extra={"param": name, "original": theta[i], "default": (min_val + max_val) / 2}
                    )
                    theta_constrained[i] = (min_val + max_val) / 2
                else:
                    theta_constrained[i] = np.clip(theta[i], min_val, max_val)

                    if theta_constrained[i] != theta[i]:
                        logger.warning(
                            f"参数 {name} 超出约束范围，已裁剪: {theta[i]:.4f} -> {theta_constrained[i]:.4f}",
                            extra={"param": name, "original": theta[i], "clipped": theta_constrained[i]}
                        )

        return theta_constrained

    def _apply_rated_constraints(
        self,
        theta: np.ndarray,
        param_names: List[str],
        rated_params: Dict[str, float],
        current_params: Dict[str, float]
    ) -> np.ndarray:
        """
        应用额定参数约束（软约束）

        策略：如果优化后的参数与额定参数偏差过大，则进行调整

        Args:
            theta: 优化后的参数向量
            param_names: 参数名列表
            rated_params: 设备额定参数字典
            current_params: 当前参数字典

        Returns:
            调整后的参数向量
        """
        theta_adjusted = theta.copy()

        # 定义额定参数的允许偏差范围（相对偏差）
        # 例如：rated_flow允许±20%偏差
        rated_param_tolerance = {
            'rated_flow': 0.20,      # ±20%
            'rated_head': 0.20,      # ±20%
            'rated_efficiency': 0.15, # ±15%
            'rated_frequency': 0.05,  # ±5%
            'rated_power': 0.20,      # ±20%
            'eta_motor': 0.10,        # ±10%
            'eta_vfd': 0.10,          # ±10%
        }

        for i, name in enumerate(param_names):
            # 检查是否是额定参数
            if name in rated_params and name in rated_param_tolerance:
                rated_value = rated_params[name]
                optimized_value = theta[i]
                tolerance = rated_param_tolerance[name]

                # 计算相对偏差
                if rated_value != 0:
                    relative_deviation = abs(optimized_value - rated_value) / rated_value

                    # 如果偏差超过允许范围，进行调整
                    if relative_deviation > tolerance:
                        # 使用加权平均：70%额定值 + 30%优化值
                        adjusted_value = 0.7 * rated_value + 0.3 * optimized_value
                        theta_adjusted[i] = adjusted_value

                        logger.warning(
                            f"参数 {name} 优化值偏离额定值过大，已调整",
                            extra={
                                "extra_data": {
                                    "param": name,
                                    "rated_value": float(rated_value),
                                    "optimized_value": float(optimized_value),
                                    "relative_deviation": float(relative_deviation),
                                    "tolerance": tolerance,
                                    "adjusted_value": float(adjusted_value),
                                    "adjustment_strategy": "weighted_average_70_30"
                                }
                            }
                        )
                    else:
                        logger.info(
                            f"参数 {name} 优化值在额定值允许范围内",
                            extra={
                                "extra_data": {
                                    "param": name,
                                    "rated_value": float(rated_value),
                                    "optimized_value": float(optimized_value),
                                    "relative_deviation": float(relative_deviation),
                                    "tolerance": tolerance
                                }
                            }
                        )

        return theta_adjusted

    def _validate_parameters(
        self,
        theta: np.ndarray,
        param_names: List[str],
        param_bounds: Optional[Dict[str, Tuple[float, float]]]
    ) -> bool:
        """验证参数合理性"""
        # 检查NaN和Inf
        if np.any(np.isnan(theta)) or np.any(np.isinf(theta)):
            logger.error("参数包含NaN或Inf")
            return False

        # 检查约束
        if param_bounds:
            for i, name in enumerate(param_names):
                if name in param_bounds:
                    min_val, max_val = param_bounds[name]
                    if not min_val <= theta[i] <= max_val:
                        logger.error(
                            f"参数 {name} 超出约束范围: {theta[i]} not in [{min_val}, {max_val}]"
                        )
                        return False

        return True

    def _calculate_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        residuals: np.ndarray,
        P: np.ndarray
    ) -> Dict[str, float]:
        """计算优化效果指标"""
        # RMSE (Root Mean Square Error)
        rmse = np.sqrt(np.mean(residuals ** 2))

        # MAE (Mean Absolute Error)
        mae = np.mean(np.abs(residuals))

        # R² (Coefficient of Determination)
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # MAPE (Mean Absolute Percentage Error)
        # 避免除零
        mask = np.abs(y_true) > 1e-6
        if np.any(mask):
            mape = np.mean(np.abs(residuals[mask] / y_true[mask])) * 100
        else:
            mape = 0

        # 参数不确定性（协方差矩阵对角线元素的平方根）
        param_std = np.sqrt(np.diag(P))

        return {
            'rmse': float(rmse),
            'mae': float(mae),
            'r2': float(r2),
            'mape': float(mape),
            'param_std_mean': float(np.mean(param_std)),
            'param_std_max': float(np.max(param_std)),
            'n_samples': len(y_true),
            'success': True
        }

    def _calculate_confidence(
        self,
        residuals: np.ndarray,
        P: np.ndarray
    ) -> float:
        """
        计算参数置信度

        基于以下因素：
        1. 残差大小（越小越好）
        2. 参数不确定性（协方差矩阵对角线元素，越小越好）
        3. 样本数量（越多越好）

        Returns:
            置信度分数 (0-1)，越高表示参数越可靠
        """
        # 残差标准差（归一化）
        residual_std = np.std(residuals)
        residual_score = 1 / (1 + residual_std)  # 越小越好

        # 参数不确定性（归一化）
        param_uncertainty = np.mean(np.sqrt(np.diag(P)))
        uncertainty_score = 1 / (1 + param_uncertainty)  # 越小越好

        # 样本数量（归一化）
        n_samples = len(residuals)
        sample_score = min(n_samples / 100, 1.0)  # 100个样本为满分

        # 综合置信度（加权平均）
        confidence = (
            0.4 * residual_score +
            0.4 * uncertainty_score +
            0.2 * sample_score
        )

        return float(np.clip(confidence, 0, 1))

    def _load_covariance_matrix(
        self,
        method_id: str,
        device_id: Optional[int],
        station_id: Optional[int],
        param_names: List[str]
    ) -> Tuple[Optional[np.ndarray], int]:
        """
        加载上次优化的协方差矩阵P

        Args:
            method_id: 计算方法ID
            device_id: 设备ID（可选）
            station_id: 站点ID（可选）
            param_names: 参数名称列表（已排序）

        Returns:
            (P矩阵, RLS迭代次数)，如果没有历史记录则返回 (None, 0)
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 查询最新的优化记录
                    query = """
                        SELECT
                            covariance_matrix,
                            rls_state
                        FROM optimization_history
                        WHERE method_id = %s
                          AND (device_id IS NOT DISTINCT FROM %s)
                          AND (station_id IS NOT DISTINCT FROM %s)
                        ORDER BY created_at DESC
                        LIMIT 1
                    """
                    cur.execute(query, (method_id, device_id, station_id))
                    row = cur.fetchone()

                    if row and row[0] is not None:
                        # 解析P矩阵（从JSONB转换为numpy数组）
                        P_list = row[0]  # JSONB自动解析为Python list
                        P = np.array(P_list, dtype=float)

                        # 验证P矩阵的维度
                        n_params = len(param_names)
                        if P.shape != (n_params, n_params):
                            logger.warning(
                                f"P矩阵维度不匹配: 期望 ({n_params}, {n_params}), 实际 {P.shape}",
                                extra={
                                    "method_id": method_id,
                                    "device_id": device_id,
                                    "expected_shape": (n_params, n_params),
                                    "actual_shape": P.shape
                                }
                            )
                            return None, 0

                        # 解析RLS状态
                        rls_iterations = 0
                        if row[1] is not None:
                            rls_state = row[1]
                            rls_iterations = rls_state.get('iterations', 0)

                        logger.info(
                            f"成功加载历史P矩阵",
                            extra={
                                "method_id": method_id,
                                "device_id": device_id,
                                "P_trace": float(np.trace(P)),
                                "P_condition": float(np.linalg.cond(P)),
                                "rls_iterations": rls_iterations
                            }
                        )

                        return P, rls_iterations
                    else:
                        logger.info(
                            f"未找到历史P矩阵，将使用初始值",
                            extra={"method_id": method_id, "device_id": device_id}
                        )
                        return None, 0

        except Exception as e:
            logger.error(f"加载P矩阵失败: {e}", exc_info=True)
            return None, 0

    def _save_optimization_result(
        self,
        method_id: str,
        old_params: Dict[str, float],
        new_params: Dict[str, float],
        metrics: Dict[str, Any],
        device_id: Optional[int] = None,
        station_id: Optional[int] = None,
        P_matrix: Optional[np.ndarray] = None,  # 新增参数
        rls_iterations: int = 0  # 新增参数
    ) -> None:
        """保存优化结果到数据库"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    import json
                    from datetime import timedelta

                    # 保存到 optimization_history 表
                    if P_matrix is not None:
                        # 将P矩阵转换为JSONB格式（二维数组）
                        P_list = P_matrix.tolist()

                        # 构建RLS状态
                        rls_state = {
                            'iterations': rls_iterations,
                            'forgetting_factor': self.forgetting_factor,
                            'timestamp': datetime.now().isoformat()
                        }

                        # 从 method_id 推断 metric_key
                        metric_key = self._infer_metric_key_from_method_id(method_id)

                        # 插入 optimization_history 表
                        insert_query = """
                            INSERT INTO optimization_history (
                                station_id,
                                device_id,
                                metric_key,
                                method_id,
                                optimization_type,
                                params_before,
                                params_after,
                                improvement_score,
                                data_window_start,
                                data_window_end,
                                data_points_count,
                                covariance_matrix,
                                rls_state,
                                created_at,
                                created_by
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), 'optimizer'
                            )
                        """

                        cur.execute(
                            insert_query,
                            (
                                station_id,
                                device_id,
                                metric_key,
                                method_id,
                                'RLS',  # optimization_type
                                json.dumps(old_params),  # params_before
                                json.dumps(new_params),  # params_after
                                metrics.get('r2'),  # improvement_score（使用R²作为改进分数）
                                datetime.now() - timedelta(hours=1),  # data_window_start（示例）
                                datetime.now(),  # data_window_end
                                metrics.get('n_samples', 0),  # data_points_count
                                json.dumps(P_list),  # covariance_matrix
                                json.dumps(rls_state)  # rls_state
                            )
                        )

                        logger.info(
                            f"已保存优化历史到 optimization_history 表",
                            extra={
                                "method_id": method_id,
                                "device_id": device_id,
                                "metric_key": metric_key,
                                "P_trace": float(np.trace(P_matrix))
                            }
                        )

                    # 构建优化历史记录（用于JSONB字段）
                    history_entry = {
                        'timestamp': datetime.now().isoformat(),
                        'old_params': old_params,
                        'new_params': new_params,
                        'metrics': metrics
                    }

                    # 更新每个参数（使用原子操作避免并发竞态条件）
                    for param_name, new_value in new_params.items():
                        # 构建单个参数的历史记录
                        param_history_entry = {
                            'timestamp': datetime.now().isoformat(),
                            'old_value': old_params.get(param_name),
                            'new_value': new_value,
                            'metrics': metrics
                        }

                        history_json = json.dumps(param_history_entry)

                        # 准备P矩阵的JSONB（所有参数共享同一个P矩阵）
                        P_json = json.dumps(P_matrix.tolist()) if P_matrix is not None else None
                        P_trace = float(np.trace(P_matrix)) if P_matrix is not None else None

                        # 使用原子操作更新（避免SELECT-UPDATE竞态）
                        # JSONB数组追加操作是原子的，无需先SELECT
                        update_query = """
                            UPDATE calculation_parameters
                            SET
                                param_value = %s,
                                confidence_score = %s,
                                last_optimized_at = NOW(),
                                optimization_count = COALESCE(optimization_count, 0) + 1,
                                optimization_history = (
                                    -- 保留最近9次记录，追加新记录（总共10次）
                                    CASE
                                        WHEN jsonb_array_length(COALESCE(optimization_history, '[]'::jsonb)) >= 10
                                        THEN (
                                            -- 截取最后9个元素
                                            (SELECT jsonb_agg(elem)
                                             FROM (
                                                 SELECT elem
                                                 FROM jsonb_array_elements(COALESCE(optimization_history, '[]'::jsonb)) elem
                                                 OFFSET 1
                                             ) sub)
                                            || %s::jsonb
                                        )
                                        ELSE COALESCE(optimization_history, '[]'::jsonb) || %s::jsonb
                                    END
                                ),
                                covariance_matrix = %s,
                                rls_iterations = %s,
                                last_p_trace = %s,
                                updated_at = NOW(),
                                updated_by = 'optimizer'
                            WHERE method_id = %s
                              AND param_name = %s
                              AND (device_id IS NOT DISTINCT FROM %s)
                              AND (station_id IS NOT DISTINCT FROM %s)
                        """

                        cur.execute(
                            update_query,
                            (
                                new_value,
                                metrics.get('confidence', 0.5),
                                history_json,
                                history_json,
                                P_json,  # 新增
                                rls_iterations,  # 新增
                                P_trace,  # 新增
                                method_id,
                                param_name,
                                device_id,
                                station_id
                            )
                        )

                        if cur.rowcount > 0:
                            logger.info(
                                f"参数已更新: {param_name} = {new_value}",
                                extra={
                                    "method_id": method_id,
                                    "param_name": param_name,
                                    "old_value": old_params.get(param_name),
                                    "new_value": new_value,
                                    "confidence": metrics.get('confidence', 0.5),
                                    "P_trace": P_trace
                                }
                            )
                        else:
                            logger.warning(
                                f"参数更新失败，记录不存在: {param_name}",
                                extra={
                                    "method_id": method_id,
                                    "param_name": param_name,
                                    "device_id": device_id,
                                    "station_id": station_id
                                }
                            )

                    conn.commit()

        except Exception as e:
            logger.error(f"保存优化结果失败: {e}", exc_info=True)
            raise DatabaseError(f"保存优化结果失败: {e}") from e

    def _infer_metric_key_from_method_id(self, method_id: str) -> str:
        """从 method_id 推断 metric_key"""
        # 简单的映射规则（可以从数据库查询）
        method_to_metric = {
            'FLOW_COEF_V1': 'pump_flow_rate',
            'FLOW_SIMPLE_V1': 'pump_flow_rate',
            'HEAD_COEF_V1': 'pump_head',
            'HEAD_SIMPLE_V1': 'pump_head',
            'EFF_SIMPLE_V1': 'pump_efficiency',
            'PIN_COEF_V1': 'pump_input_power',
            'TORQUE_SIMPLE_V1': 'pump_torque',
            'SPEED_SIMPLE_V1': 'pump_speed',
            'POUT_SIMPLE_V1': 'pump_output_power',
            'MAIN_FLOW_SIMPLE_V1': 'main_pipeline_flow_rate',
            'MAIN_HEAD_SIMPLE_V1': 'main_pipeline_head',
            'MAIN_PIN_SIMPLE_V1': 'main_pipeline_inlet_pressure',
            'MAIN_POUT_SIMPLE_V1': 'main_pipeline_outlet_pressure',
        }
        return method_to_metric.get(method_id, 'unknown')

