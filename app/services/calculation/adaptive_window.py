"""
自适应时间窗口管理器

功能：
1. 根据性能动态调整时间窗口
2. 考虑数据密度和处理速度
3. 使用EMA平滑调整

作者：System
创建时间：2025-10-05
"""

import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class AdaptiveWindowManager:
    """
    自适应时间窗口管理器
    
    根据性能指标和数据密度动态调整时间窗口大小
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化自适应窗口管理器

        Args:
            config: 配置字典
                - enabled: 是否启用（默认True）
                - initial_minutes: 初始窗口大小（默认60分钟）
                - min_minutes: 最小窗口大小（默认15分钟）
                - max_minutes: 最大窗口大小（默认240分钟）
                - target_duration_ms: 目标处理时间（默认5000毫秒）
                - adjustment_factor: 调整因子（默认0.2）
                - smoothing_alpha: EMA平滑系数（默认0.3）
        """
        logger.info("[流程-开始] [自适应窗口管理器初始化]")

        config = config or {}

        self.enabled = config.get('enabled', True)
        self.initial_minutes = config.get('initial_minutes', 60)
        self.min_minutes = config.get('min_minutes', 15)
        self.max_minutes = config.get('max_minutes', 240)
        self.target_duration = config.get('target_duration_ms', 5000)
        self.adjustment_factor = config.get('adjustment_factor', 0.2)
        self.smoothing_alpha = config.get('smoothing_alpha', 0.3)
        
        # 验证配置
        if self.min_minutes >= self.max_minutes:
            raise ValueError(
                f"min_minutes ({self.min_minutes}) 必须小于 max_minutes ({self.max_minutes})"
            )
        
        if self.initial_minutes < self.min_minutes or self.initial_minutes > self.max_minutes:
            raise ValueError(
                f"initial_minutes ({self.initial_minutes}) 必须在 "
                f"[{self.min_minutes}, {self.max_minutes}] 范围内"
            )
        
        if not 0 < self.smoothing_alpha < 1:
            raise ValueError(f"smoothing_alpha ({self.smoothing_alpha}) 必须在 (0, 1) 范围内")
        
        logger.info(
            "[核心-初始化] AdaptiveWindowManager 初始化完成",
            extra={
                "extra_data": {
                    "enabled": self.enabled,
                    "initial_minutes": self.initial_minutes,
                    "range": f"[{self.min_minutes}, {self.max_minutes}]",
                    "target_duration": self.target_duration,
                    "adjustment_factor": self.adjustment_factor,
                    "smoothing_alpha": self.smoothing_alpha
                }
            }
        )
    
    def adjust(
        self,
        current_window: int,
        performance: Dict
    ) -> Tuple[int, str]:
        """
        调整时间窗口
        
        Args:
            current_window: 当前窗口大小（分钟）
            performance: 性能指标
                - duration_ms: 处理耗时（毫秒）
                - data_points: 数据点数
        
        Returns:
            (新窗口大小, 调整原因)
        """
        if not self.enabled:
            return current_window, "自适应窗口已禁用"
        
        duration_ms = performance.get('duration_ms', 0)
        data_points = performance.get('data_points', 0)
        
        # 1. 计算数据密度（点/分钟）
        density = data_points / current_window if current_window > 0 else 0
        
        # 2. 性能驱动调整
        adjustment = 1.0
        reasons = []
        
        if duration_ms > self.target_duration * 1.5:
            # 处理太慢，缩小窗口
            adjustment *= (1 - self.adjustment_factor)
            reasons.append(
                f"处理慢({duration_ms}ms > {self.target_duration*1.5:.0f}ms)"
            )
            
        elif duration_ms < self.target_duration * 0.5:
            # 处理太快，扩大窗口
            adjustment *= (1 + self.adjustment_factor)
            reasons.append(
                f"处理快({duration_ms}ms < {self.target_duration*0.5:.0f}ms)"
            )
        
        # 3. 数据密度调整
        if density > 100:  # 数据密集（>100点/分钟）
            adjustment *= 0.9
            reasons.append(f"数据密集({density:.0f}点/分钟)")
        elif density < 10:  # 数据稀疏（<10点/分钟）
            adjustment *= 1.1
            reasons.append(f"数据稀疏({density:.0f}点/分钟)")
        
        # 4. 计算新窗口
        new_window_raw = current_window * adjustment
        
        # 5. EMA平滑（避免剧烈变化）
        new_window_smoothed = self._smooth_adjustment(current_window, new_window_raw)
        
        # 6. 限制范围
        new_window = max(self.min_minutes, min(self.max_minutes, int(new_window_smoothed)))
        
        # 7. 避免频繁小幅调整（调整幅度<5分钟则不调整）
        if abs(new_window - current_window) < 5:
            new_window = current_window
            reason = "调整幅度过小，保持不变"
        else:
            reason = ", ".join(reasons) if reasons else "性能稳定"
        
        # 8. 记录调整
        if new_window != current_window:
            logger.info(
                f"调整时间窗口: {current_window}分钟 → {new_window}分钟",
                extra={
                    "old_window": current_window,
                    "new_window": new_window,
                    "reason": reason,
                    "duration_ms": duration_ms,
                    "density": density
                }
            )
        
        return new_window, reason
    
    def _calculate_data_density(self, data_points: int, window_minutes: int) -> float:
        """
        计算数据密度（点/分钟）
        
        Args:
            data_points: 数据点数
            window_minutes: 窗口大小（分钟）
        
        Returns:
            数据密度
        """
        if window_minutes <= 0:
            return 0.0
        return data_points / window_minutes
    
    def _smooth_adjustment(self, old_value: float, new_value: float) -> float:
        """
        EMA平滑调整
        
        使用指数移动平均（Exponential Moving Average）平滑调整，
        避免剧烈变化
        
        Args:
            old_value: 旧值
            new_value: 新值
        
        Returns:
            平滑后的值
        """
        # EMA公式：smoothed = alpha * new + (1 - alpha) * old
        smoothed = self.smoothing_alpha * new_value + (1 - self.smoothing_alpha) * old_value
        return smoothed
    
    def get_initial_minutes(self) -> int:
        """获取初始窗口大小"""
        return self.initial_minutes
    
    def is_enabled(self) -> bool:
        """是否启用自适应窗口"""
        return self.enabled

