"""
性能监控模块

功能：
1. 记录批次性能指标（耗时、内存、吞吐量）
2. 计算统计信息（平均值、趋势）
3. 持久化到数据库
4. 提供性能分析接口

作者：System
创建时间：2025-10-05
"""

import logging
import time
import psutil
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import deque

from app.adapters.db import get_connection
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    性能监控器
    
    监控计算过程的性能指标，用于自适应优化
    """
    
    def __init__(
        self,
        station_id: int,
        device_id: int,
        run_id: Optional[int] = None,
        history_size: int = 20
    ):
        """
        初始化性能监控器
        
        Args:
            station_id: 泵站ID
            device_id: 设备ID
            run_id: 运行ID（可选）
            history_size: 保留的历史记录数量
        """
        logger.info(
            "[流程-开始] [性能监控器初始化]",
            extra={
                "extra_data": {
                    "station_id": station_id,
                    "device_id": device_id,
                    "run_id": run_id,
                }
            },
        )

        self.station_id = station_id
        self.device_id = device_id
        self.run_id = run_id
        self.history_size = history_size

        # 历史记录（使用deque限制大小）
        self.history: deque = deque(maxlen=history_size)

        # 当前批次信息
        self.current_batch: Optional[Dict] = None
        
        # 进程对象（用于内存监控）
        try:
            self.process = psutil.Process()
        except Exception as e:
            logger.warning(f"无法获取进程对象: {e}")
            self.process = None
        
        logger.info(
            "[核心-初始化] PerformanceMonitor 初始化完成",
            extra={
                "extra_data": {
                    "station_id": station_id,
                    "device_id": device_id,
                    "run_id": run_id
                }
            }
        )
    
    def start_batch(self, batch_number: int, time_window_minutes: int) -> Dict:
        """
        开始批次监控
        
        Args:
            batch_number: 批次编号
            time_window_minutes: 时间窗口大小（分钟）
        
        Returns:
            批次上下文信息
        """
        self.current_batch = {
            'batch_number': batch_number,
            'time_window_minutes': time_window_minutes,
            'start_time': time.time(),
            'start_memory_mb': self.get_memory_usage()
        }
        
        return self.current_batch
    
    def end_batch(
        self,
        batch_size: int,
        data_points: int,
        adjustment_type: Optional[str] = None,
        adjustment_reason: Optional[str] = None,
        old_value: Optional[int] = None,
        new_value: Optional[int] = None
    ) -> Dict:
        """
        结束批次监控，计算性能指标
        
        Args:
            batch_size: 批量大小
            data_points: 数据点数
            adjustment_type: 调整类型（'window'/'batch'/'none'）
            adjustment_reason: 调整原因
            old_value: 调整前的值
            new_value: 调整后的值
        
        Returns:
            性能指标字典
        """
        if self.current_batch is None:
            raise ValueError("未调用start_batch()，无法结束批次")
        
        # 计算耗时
        end_time = time.time()
        duration_s = end_time - self.current_batch['start_time']
        duration_ms = int(duration_s * 1000)
        
        # 计算内存使用
        end_memory_mb = self.get_memory_usage()
        memory_delta = end_memory_mb - self.current_batch['start_memory_mb']
        
        # 计算吞吐量（条/秒）
        throughput = data_points / duration_s if duration_s > 0 else 0
        
        # 构建性能指标
        metrics = {
            'batch_number': self.current_batch['batch_number'],
            'time_window_minutes': self.current_batch['time_window_minutes'],
            'batch_size': batch_size,
            'data_points': data_points,
            'duration_ms': duration_ms,
            'memory_mb': end_memory_mb,
            'memory_delta_mb': memory_delta,
            'throughput': throughput,
            'adjustment_type': adjustment_type or 'none',
            'adjustment_reason': adjustment_reason,
            'old_value': old_value,
            'new_value': new_value,
            'timestamp': datetime.now()
        }
        
        # 添加到历史记录
        self.history.append(metrics)
        
        # 清空当前批次
        self.current_batch = None
        
        logger.debug(
            f"批次 {metrics['batch_number']} 完成: "
            f"{duration_ms}ms, {throughput:.0f}条/秒, {end_memory_mb:.0f}MB",
            extra=metrics
        )
        
        return metrics
    
    def get_memory_usage(self) -> float:
        """
        获取当前内存使用（MB）
        
        Returns:
            内存使用量（MB）
        """
        if self.process is None:
            return 0.0
        
        try:
            # 获取RSS（常驻内存集）
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            return memory_mb
        except Exception as e:
            logger.warning(f"获取内存使用失败: {e}")
            return 0.0
    
    def get_statistics(self, window: int = 10) -> Dict[str, Any]:
        """
        获取最近N个批次的统计信息
        
        Args:
            window: 统计窗口大小（批次数）
        
        Returns:
            统计信息字典
        """
        if len(self.history) == 0:
            return {
                'count': 0,
                'avg_duration_ms': 0,
                'avg_throughput': 0,
                'avg_memory_mb': 0,
                'trend': 'stable'
            }
        
        # 获取最近N个批次
        recent = list(self.history)[-window:]
        
        # 计算平均值
        avg_duration = sum(m['duration_ms'] for m in recent) / len(recent)
        avg_throughput = sum(m['throughput'] for m in recent) / len(recent)
        avg_memory = sum(m['memory_mb'] for m in recent) / len(recent)
        
        # 计算趋势（比较前半部分和后半部分）
        if len(recent) >= 4:
            mid = len(recent) // 2
            first_half_duration = sum(m['duration_ms'] for m in recent[:mid]) / mid
            second_half_duration = sum(m['duration_ms'] for m in recent[mid:]) / (len(recent) - mid)
            
            if second_half_duration > first_half_duration * 1.2:
                trend = 'degrading'
            elif second_half_duration < first_half_duration * 0.8:
                trend = 'improving'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        return {
            'count': len(recent),
            'avg_duration_ms': avg_duration,
            'avg_throughput': avg_throughput,
            'avg_memory_mb': avg_memory,
            'trend': trend
        }
    
    def save_to_db(self, metrics: Dict) -> None:
        """
        保存性能指标到数据库
        
        Args:
            metrics: 性能指标字典
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO calculation_performance_metrics
                        (run_id, station_id, device_id, batch_number,
                         time_window_minutes, batch_size, data_points,
                         duration_ms, memory_mb, throughput,
                         adjustment_type, adjustment_reason, old_value, new_value)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        self.run_id,
                        self.station_id,
                        self.device_id,
                        metrics['batch_number'],
                        metrics['time_window_minutes'],
                        metrics['batch_size'],
                        metrics['data_points'],
                        metrics['duration_ms'],
                        metrics['memory_mb'],
                        metrics['throughput'],
                        metrics['adjustment_type'],
                        metrics['adjustment_reason'],
                        metrics['old_value'],
                        metrics['new_value']
                    ))
                    
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"保存性能指标失败: {e}", exc_info=True)
            # 不抛出异常，避免影响主流程
    
    def get_recent_metrics(self, limit: int = 10) -> List[Dict]:
        """
        获取最近的性能指标
        
        Args:
            limit: 返回数量
        
        Returns:
            性能指标列表
        """
        return list(self.history)[-limit:]
    
    def clear_history(self) -> None:
        """清空历史记录"""
        self.history.clear()

