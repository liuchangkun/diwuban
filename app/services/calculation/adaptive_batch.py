"""
自适应批量大小管理器

功能：
1. 根据性能动态调整批量大小
2. 考虑内存、速度、吞吐量
3. 平滑调整，避免剧烈变化

作者：System
创建时间：2025-10-05
"""

import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class AdaptiveBatchManager:
    """
    自适应批量大小管理器
    
    根据性能指标动态调整批量大小，优化吞吐量和内存使用
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化自适应批量管理器
        
        Args:
            config: 配置字典
                - enabled: 是否启用（默认True）
                - initial_size: 初始批量大小（默认10000）
                - min_size: 最小批量大小（默认1000）
                - max_size: 最大批量大小（默认50000）
                - memory_limit_mb: 内存限制（默认1000MB）
                - target_throughput: 目标吞吐量（默认10000条/秒）
        """
        config = config or {}
        
        self.enabled = config.get('enabled', True)
        self.initial_size = config.get('initial_size', 10000)
        self.min_size = config.get('min_size', 1000)
        self.max_size = config.get('max_size', 50000)
        self.memory_limit = config.get('memory_limit_mb', 1000)
        self.target_throughput = config.get('target_throughput', 10000)
        
        # 验证配置
        if self.min_size >= self.max_size:
            raise ValueError(f"min_size ({self.min_size}) 必须小于 max_size ({self.max_size})")
        
        if self.initial_size < self.min_size or self.initial_size > self.max_size:
            raise ValueError(
                f"initial_size ({self.initial_size}) 必须在 "
                f"[{self.min_size}, {self.max_size}] 范围内"
            )
        
        logger.info(
            "[核心-初始化] AdaptiveBatchManager 初始化完成",
            extra={
                "extra_data": {
                    "enabled": self.enabled,
                    "initial_size": self.initial_size,
                    "range": f"[{self.min_size}, {self.max_size}]",
                    "memory_limit": self.memory_limit,
                    "target_throughput": self.target_throughput
                }
            }
        )
    
    def adjust(
        self,
        current_batch: int,
        performance: Dict
    ) -> Tuple[int, str]:
        """
        调整批量大小
        
        Args:
            current_batch: 当前批量大小
            performance: 性能指标
                - memory_mb: 内存使用（MB）
                - throughput: 吞吐量（条/秒）
                - duration_ms: 耗时（毫秒）
        
        Returns:
            (新批量大小, 调整原因)
        """
        if not self.enabled:
            return current_batch, "自适应批量已禁用"
        
        memory_mb = performance.get('memory_mb', 0)
        throughput = performance.get('throughput', 0)
        duration_ms = performance.get('duration_ms', 0)
        
        # 1. 内存优先（安全第一）
        if self._check_memory_pressure(memory_mb):
            new_batch = int(current_batch * 0.7)
            reason = f"内存压力高({memory_mb:.0f}MB > {self.memory_limit*0.8:.0f}MB)"
            
        # 2. 吞吐量优化
        elif throughput < self.target_throughput * 0.5:
            # 吞吐量太低，减小批量
            new_batch = int(current_batch * 0.5)
            reason = f"吞吐量低({throughput:.0f} < {self.target_throughput*0.5:.0f}条/秒)"
            
        elif throughput > self.target_throughput * 1.5 and memory_mb < self.memory_limit * 0.5:
            # 吞吐量高且内存充足，增大批量
            new_batch = int(current_batch * 2)
            reason = f"吞吐量高({throughput:.0f} > {self.target_throughput*1.5:.0f}条/秒)且内存充足"
            
        else:
            # 性能稳定，保持不变
            new_batch = current_batch
            reason = "性能稳定"
        
        # 3. 限制范围
        new_batch = max(self.min_size, min(self.max_size, new_batch))
        
        # 4. 避免频繁小幅调整（调整幅度<10%则不调整）
        if abs(new_batch - current_batch) < current_batch * 0.1:
            new_batch = current_batch
            reason = "调整幅度过小，保持不变"
        
        # 5. 记录调整
        if new_batch != current_batch:
            logger.info(
                f"调整批量大小: {current_batch} → {new_batch}",
                extra={
                    "old_batch": current_batch,
                    "new_batch": new_batch,
                    "reason": reason,
                    "memory_mb": memory_mb,
                    "throughput": throughput
                }
            )
        
        return new_batch, reason
    
    def _check_memory_pressure(self, memory_mb: float) -> bool:
        """
        检查内存压力
        
        Args:
            memory_mb: 当前内存使用（MB）
        
        Returns:
            是否存在内存压力
        """
        return memory_mb > self.memory_limit * 0.8
    
    def _calculate_optimal_batch(self, performance: Dict) -> int:
        """
        计算最优批量大小（基于历史性能）
        
        Args:
            performance: 性能指标
        
        Returns:
            最优批量大小
        """
        # 简单实现：基于吞吐量线性估算
        throughput = performance.get('throughput', self.target_throughput)
        current_batch = performance.get('batch_size', self.initial_size)
        
        if throughput > 0:
            # 估算达到目标吞吐量需要的批量大小
            optimal = int(current_batch * (self.target_throughput / throughput))
            return max(self.min_size, min(self.max_size, optimal))
        
        return current_batch
    
    def get_initial_size(self) -> int:
        """获取初始批量大小"""
        return self.initial_size
    
    def is_enabled(self) -> bool:
        """是否启用自适应批量"""
        return self.enabled

