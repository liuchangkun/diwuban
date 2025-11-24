"""
批处理器 (app.services.characteristic_curves.shared.batch_processor)

本模块提供大数据量的分批处理功能：
- 顺序执行：禁止线程并发，避免GIL限制和调试复杂性
- 内存友好：使用迭代器模式，避免内存溢出
- 批大小可配置：根据数据量动态调整

设计决策（2025-12）：
- 统一采用顺序执行模式，禁止使用线程并发
- 原因：拟合计算是CPU密集型，GIL限制下多线程无法提升性能

使用方式：
    from app.services.characteristic_curves.shared import BatchProcessor
    
    processor = BatchProcessor(batch_size=5000)
    results = processor.process_batches(data, process_func)
"""

import logging
import time
from typing import Any, Callable, Dict, Iterator, List, Optional

import pandas as pd


class BatchProcessor:
    """批处理器（顺序执行）
    
    提供大数据量的分批处理功能，采用迭代器模式避免内存溢出。
    所有处理均为顺序执行，禁止线程并发。
    """

    def __init__(self, batch_size: int = 5000):
        """初始化批处理器
        
        Args:
            batch_size: 每批数据量，默认5000
        """
        self._batch_size = batch_size
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        self._logger.info(
            "[批处理] 初始化",
            extra={"extra_data": {
                "组件": "BatchProcessor",
                "批大小": batch_size,
                "执行模式": "顺序执行"
            }}
        )

    def process_batches(
        self,
        data: pd.DataFrame,
        process_func: Callable[[pd.DataFrame], Any],
        batch_size: Optional[int] = None
    ) -> List[Any]:
        """分批处理数据（顺序执行）
        
        Args:
            data: 输入数据
            process_func: 处理函数，接收DataFrame返回处理结果
            batch_size: 批大小（可选，不指定则使用默认值）
            
        Returns:
            List[Any]: 各批次处理结果列表
        """
        start_time = time.time()
        batch_size = batch_size or self._batch_size
        total_rows = len(data)
        
        if total_rows == 0:
            self._logger.warning("[批处理] 输入数据为空")
            return []
        
        results = []
        batch_count = 0
        
        for batch in self.iterate_batches(data, batch_size):
            batch_count += 1
            batch_start = time.time()
            
            try:
                result = process_func(batch)
                results.append(result)
                
                batch_duration = (time.time() - batch_start) * 1000
                self._logger.debug(
                    f"[批处理] 批次{batch_count}完成",
                    extra={"extra_data": {
                        "批次": batch_count,
                        "批大小": len(batch),
                        "耗时ms": round(batch_duration, 2)
                    }}
                )
            except Exception as e:
                self._logger.error(
                    f"[批处理] 批次{batch_count}失败",
                    extra={"extra_data": {
                        "批次": batch_count,
                        "错误类型": type(e).__name__,
                        "错误信息": str(e)
                    }},
                    exc_info=True
                )
                raise
        
        total_duration = (time.time() - start_time) * 1000
        self._logger.info(
            "[批处理] 分批处理完成",
            extra={"extra_data": {
                "总行数": total_rows,
                "批次数": batch_count,
                "批大小": batch_size,
                "总耗时ms": round(total_duration, 2)
            }}
        )
        
        return results

    def process_sequential(
        self,
        tasks: List[Dict[str, Any]],
        process_func: Callable[[Dict[str, Any]], Any]
    ) -> List[Any]:
        """顺序处理多个任务
        
        替代原 process_parallel，采用顺序执行模式。
        
        Args:
            tasks: 任务列表，每个任务是一个字典
            process_func: 处理函数，接收任务字典返回处理结果
            
        Returns:
            List[Any]: 各任务处理结果列表
        """
        start_time = time.time()
        total_tasks = len(tasks)
        
        if total_tasks == 0:
            self._logger.warning("[批处理] 任务列表为空")
            return []
        
        results = []
        
        for i, task in enumerate(tasks, 1):
            task_start = time.time()
            
            try:
                result = process_func(task)
                results.append(result)
                
                task_duration = (time.time() - task_start) * 1000
                self._logger.debug(
                    f"[批处理] 任务{i}/{total_tasks}完成",
                    extra={"extra_data": {
                        "任务序号": i,
                        "任务内容": task,
                        "耗时ms": round(task_duration, 2)
                    }}
                )
            except Exception as e:
                self._logger.error(
                    f"[批处理] 任务{i}失败",
                    extra={"extra_data": {
                        "任务序号": i,
                        "任务内容": task,
                        "错误类型": type(e).__name__,
                        "错误信息": str(e)
                    }},
                    exc_info=True
                )
                raise
        
        total_duration = (time.time() - start_time) * 1000
        self._logger.info(
            "[批处理] 顺序处理完成",
            extra={"extra_data": {
                "任务数": total_tasks,
                "成功数": len(results),
                "总耗时ms": round(total_duration, 2)
            }}
        )
        
        return results

    def iterate_batches(
        self,
        data: pd.DataFrame,
        batch_size: Optional[int] = None
    ) -> Iterator[pd.DataFrame]:
        """迭代数据批次（内存友好）
        
        使用生成器模式，每次只返回一个批次的数据，避免内存溢出。
        
        Args:
            data: 输入数据
            batch_size: 批大小（可选）
            
        Yields:
            pd.DataFrame: 数据批次
        """
        batch_size = batch_size or self._batch_size
        total_rows = len(data)
        
        for start_idx in range(0, total_rows, batch_size):
            end_idx = min(start_idx + batch_size, total_rows)
            yield data.iloc[start_idx:end_idx]

    @property
    def batch_size(self) -> int:
        """获取当前批大小"""
        return self._batch_size

    @batch_size.setter
    def batch_size(self, value: int) -> None:
        """设置批大小"""
        if value <= 0:
            raise ValueError("批大小必须大于0")
        self._batch_size = value

