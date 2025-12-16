"""
自适应时间分片管理器 (AdaptiveChunkManager)

职责：
- 根据数据量、设备数量、内存使用情况动态调整时间分片大小
- 优化计算性能，避免单个任务过大或过小
- 类似于 AdaptiveBatchManager，但用于时间分片而非批量大小

设计思路：
1. 初始分片大小：根据历史数据估算合理的初始值
2. 动态调整：根据任务执行性能实时调整
3. 约束条件：
   - 最小分片：避免任务过多导致调度开销
   - 最大分片：避免单个任务内存溢出
   - 数据量估算：根据设备数量和采样率估算数据量
"""

from __future__ import annotations

import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class AdaptiveChunkManager:
    """
    自适应时间分片管理器
    
    根据数据量、设备数量、任务执行性能动态调整时间分片大小
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化自适应时间分片管理器
        
        Args:
            config: 配置字典
                - enabled: 是否启用（默认True）
                - initial_hours: 初始分片大小（小时，默认24）
                - min_hours: 最小分片大小（小时，默认1）
                - max_hours: 最大分片大小（小时，默认168=7天）
                - target_rows_per_task: 目标每任务数据行数（默认100000）
                - target_duration_seconds: 目标任务执行时间（秒，默认60）
                - estimated_rows_per_hour: 估算每小时数据行数（默认3600，即1秒1条）
        """
        config = config or {}
        
        self.enabled = config.get('enabled', True)
        self.initial_hours = config.get('initial_hours', 24)
        self.min_hours = config.get('min_hours', 1)
        self.max_hours = config.get('max_hours', 168)  # 7天
        self.target_rows_per_task = config.get('target_rows_per_task', 100000)
        self.target_duration_seconds = config.get('target_duration_seconds', 60)
        self.estimated_rows_per_hour = config.get('estimated_rows_per_hour', 3600)
        
        # 验证配置
        if self.min_hours >= self.max_hours:
            raise ValueError(f"min_hours ({self.min_hours}) 必须小于 max_hours ({self.max_hours})")
        
        if self.initial_hours < self.min_hours or self.initial_hours > self.max_hours:
            raise ValueError(
                f"initial_hours ({self.initial_hours}) 必须在 "
                f"[{self.min_hours}, {self.max_hours}] 范围内"
            )
        
        # 性能历史（用于自适应调整）
        self.performance_history = []
        self.max_history_size = 10
        
        logger.info(
            "[自适应分片] AdaptiveChunkManager 初始化完成",
            extra={
                "extra_data": {
                    "已启用": self.enabled,
                    "初始小时数": self.initial_hours,
                    "范围": f"[{self.min_hours}, {self.max_hours}]小时",
                    "目标行数每任务": self.target_rows_per_task,
                    "目标执行时长秒": self.target_duration_seconds,
                }
            }
        )
    
    def calculate_optimal_chunk_hours(
        self,
        device_count: int,
        total_hours: float,
        metric_key: str = None
    ) -> int:
        """
        计算最优时间分片大小
        
        Args:
            device_count: 设备数量
            total_hours: 总时间跨度（小时）
            metric_key: 指标键（可选，用于特定指标的优化）
        
        Returns:
            最优分片大小（小时）
        """
        if not self.enabled:
            return self.initial_hours
        
        # 1. 估算每个时间分片的数据量
        estimated_rows_per_chunk = self.estimated_rows_per_hour * self.initial_hours * device_count
        
        # 2. 根据目标数据量调整分片大小
        if estimated_rows_per_chunk > self.target_rows_per_task * 1.5:
            # 数据量过大，减小分片
            optimal_hours = int(self.initial_hours * (self.target_rows_per_task / estimated_rows_per_chunk))
        elif estimated_rows_per_chunk < self.target_rows_per_task * 0.5:
            # 数据量过小，增大分片
            optimal_hours = int(self.initial_hours * (self.target_rows_per_task / estimated_rows_per_chunk))
        else:
            # 数据量合适，使用初始值
            optimal_hours = self.initial_hours
        
        # 3. 限制范围
        optimal_hours = max(self.min_hours, min(self.max_hours, optimal_hours))
        
        # 4. 确保分片大小不超过总时间跨度
        optimal_hours = min(optimal_hours, int(total_hours))
        
        # 5. 避免过小的分片（至少1小时）
        optimal_hours = max(1, optimal_hours)
        
        logger.info(
            f"[自适应分片] 计算最优分片大小: {optimal_hours}小时",
            extra={
                "extra_data": {
                    "指标键": metric_key,
                    "设备数量": device_count,
                    "总小时数": total_hours,
                    "预估每分片行数": estimated_rows_per_chunk,
                    "目标行数每任务": self.target_rows_per_task,
                    "最优小时数": optimal_hours,
                }
            }
        )
        
        return optimal_hours

    def adjust_based_on_performance(
        self,
        current_chunk_hours: int,
        performance: Dict
    ) -> Tuple[int, str]:
        """
        根据任务执行性能调整分片大小

        Args:
            current_chunk_hours: 当前分片大小（小时）
            performance: 性能指标
                - duration_seconds: 任务执行时间（秒）
                - data_rows: 处理的数据行数
                - memory_mb: 内存使用（MB）
                - success: 是否成功

        Returns:
            (新分片大小, 调整原因)
        """
        if not self.enabled:
            return current_chunk_hours, "自适应分片已禁用"

        duration = performance.get('duration_seconds', 0)
        data_rows = performance.get('data_rows', 0)
        memory_mb = performance.get('memory_mb', 0)
        success = performance.get('success', True)

        # 记录性能历史
        self.performance_history.append(performance)
        if len(self.performance_history) > self.max_history_size:
            self.performance_history.pop(0)

        # 1. 失败任务：减小分片
        if not success:
            new_hours = int(current_chunk_hours * 0.5)
            reason = "任务失败，减小分片"

        # 2. 执行时间过长：减小分片
        elif duration > self.target_duration_seconds * 2:
            new_hours = int(current_chunk_hours * 0.7)
            reason = f"执行时间过长({duration:.0f}s > {self.target_duration_seconds*2:.0f}s)"

        # 3. 执行时间过短且数据量小：增大分片
        elif duration < self.target_duration_seconds * 0.3 and data_rows < self.target_rows_per_task * 0.5:
            new_hours = int(current_chunk_hours * 1.5)
            reason = f"执行时间短({duration:.0f}s)且数据量小({data_rows}行)"

        # 4. 数据量过大：减小分片
        elif data_rows > self.target_rows_per_task * 2:
            new_hours = int(current_chunk_hours * 0.8)
            reason = f"数据量过大({data_rows} > {self.target_rows_per_task*2}行)"

        # 5. 性能稳定：保持不变
        else:
            new_hours = current_chunk_hours
            reason = "性能稳定"

        # 6. 限制范围
        new_hours = max(self.min_hours, min(self.max_hours, new_hours))

        # 7. 避免频繁小幅调整（调整幅度<20%则不调整）
        if abs(new_hours - current_chunk_hours) < current_chunk_hours * 0.2:
            new_hours = current_chunk_hours
            reason = "调整幅度过小，保持不变"

        # 8. 记录调整
        if new_hours != current_chunk_hours:
            logger.info(
                f"[自适应分片] 调整分片大小: {current_chunk_hours}小时 → {new_hours}小时",
                extra={
                    "extra_data": {
                        "旧小时数": current_chunk_hours,
                        "新小时数": new_hours,
                        "原因": reason,
                        "执行时长秒": duration,
                        "数据行数": data_rows,
                        "内存MB": memory_mb,
                    }
                }
            )

        return new_hours, reason

    def get_initial_hours(self) -> int:
        """获取初始分片大小"""
        return self.initial_hours

    def is_enabled(self) -> bool:
        """是否启用自适应分片"""
        return self.enabled

    def get_average_performance(self) -> Dict:
        """获取平均性能指标"""
        if not self.performance_history:
            return {}

        avg_duration = sum(p.get('duration_seconds', 0) for p in self.performance_history) / len(self.performance_history)
        avg_rows = sum(p.get('data_rows', 0) for p in self.performance_history) / len(self.performance_history)
        success_rate = sum(1 for p in self.performance_history if p.get('success', True)) / len(self.performance_history)

        return {
            'avg_duration_seconds': avg_duration,
            'avg_data_rows': avg_rows,
            'success_rate': success_rate,
            'history_size': len(self.performance_history),
        }

