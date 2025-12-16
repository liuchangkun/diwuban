"""
稳态识别器 (app.services.characteristic_curves.preprocessing.steady_state_detector)

从数据中提取稳态运行片段。

版本: v1.0
参考: 设计文档 3.7.2节
"""

import logging
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from app.services.characteristic_curves.core.data_structures import SteadyStateResult


logger = logging.getLogger(__name__)


class SteadyStateDetector:
    """稳态识别器
    
    从数据中提取稳态运行片段。
    
    稳态判断标准:
    - 流量波动 < 5%
    - 扬程波动 < 3%
    - 持续时间 ≥ 5分钟
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化稳态识别器
        
        Args:
            config: 配置参数,可选
        """
        self._config = config or {}
        self._flow_threshold = self._config.get('flow_fluctuation_threshold', 0.05)
        self._head_threshold = self._config.get('head_fluctuation_threshold', 0.03)
        self._min_duration_minutes = self._config.get('min_steady_duration_minutes', 5)
        
        logger.info(
            "[稳态识别器] 初始化",
            extra={"extra_data": {
                "flow_threshold": self._flow_threshold,
                "head_threshold": self._head_threshold,
                "min_duration_minutes": self._min_duration_minutes,
            }}
        )
    
    def is_steady(self, data: pd.DataFrame, config: Optional[Dict] = None) -> bool:
        """判断数据是否全部为稳态
        
        Args:
            data: 数据DataFrame
            config: 额外配置(可选)
        
        Returns:
            bool: 是否全部稳态
        """
        if len(data) == 0:
            return False
        
        # 计算波动系数
        flow_cv = data['flow'].std() / data['flow'].mean() if data['flow'].mean() > 0 else 0
        
        # 检查是否有head列(QH曲线)或power列(QP曲线)
        if 'head' in data.columns:
            y_cv = data['head'].std() / data['head'].mean() if data['head'].mean() > 0 else 0
        elif 'power' in data.columns:
            y_cv = data['power'].std() / data['power'].mean() if data['power'].mean() > 0 else 0
        else:
            # 无法判断,默认False
            return False
        
        is_steady = (flow_cv < self._flow_threshold and y_cv < self._head_threshold)
        
        logger.debug(
            f"[稳态判断] flow_cv={flow_cv:.4f}, y_cv={y_cv:.4f}, "
            f"is_steady={is_steady}"
        )
        
        return is_steady
    
    def detect_steady_points(
        self,
        data: pd.DataFrame,
        config: Optional[Dict] = None
    ) -> Tuple[pd.DataFrame, SteadyStateResult]:
        """提取稳态数据点
        
        Args:
            data: 数据DataFrame
            config: 额外配置(可选)
        
        Returns:
            Tuple[pd.DataFrame, SteadyStateResult]:
                - DataFrame: 稳态数据
                - SteadyStateResult: 稳态识别结果
        """
        if len(data) == 0:
            return data, SteadyStateResult(
                steady_segments=[],
                segment_count=0,
                total_steady_points=0,
                steady_ratio=0.0
            )
        
        # P0阶段简化实现:使用滑动窗口检测稳态片段
        window_size = max(10, len(data) // 20)  # 窗口大小:至少10个点
        steady_mask = np.zeros(len(data), dtype=bool)
        
        for i in range(len(data) - window_size + 1):
            window = data.iloc[i:i+window_size]
            
            # 计算窗口内的波动
            flow_cv = window['flow'].std() / window['flow'].mean() if window['flow'].mean() > 0 else 0
            
            # 检查Y值列
            if 'head' in window.columns:
                y_cv = window['head'].std() / window['head'].mean() if window['head'].mean() > 0 else 0
            elif 'power' in window.columns:
                y_cv = window['power'].std() / window['power'].mean() if window['power'].mean() > 0 else 0
            else:
                continue
            
            # 判断是否稳态
            if flow_cv < self._flow_threshold and y_cv < self._head_threshold:
                steady_mask[i:i+window_size] = True
        
        # 提取稳态片段
        steady_segments = []
        in_segment = False
        segment_start = 0
        
        for i, is_steady in enumerate(steady_mask):
            if is_steady and not in_segment:
                segment_start = i
                in_segment = True
            elif not is_steady and in_segment:
                steady_segments.append((segment_start, i))
                in_segment = False
        
        # 处理最后一个片段
        if in_segment:
            steady_segments.append((segment_start, len(data)))
        
        # 过滤太短的片段
        min_points = max(5, len(data) // 100)
        steady_segments = [(start, end) for start, end in steady_segments 
                          if end - start >= min_points]
        
        # 提取稳态数据
        steady_indices = []
        for start, end in steady_segments:
            steady_indices.extend(range(start, end))
        
        steady_data = data.iloc[steady_indices] if steady_indices else data.iloc[:0]
        
        total_steady_points = len(steady_data)
        steady_ratio = total_steady_points / len(data) if len(data) > 0 else 0.0
        
        result = SteadyStateResult(
            steady_segments=steady_segments,
            segment_count=len(steady_segments),
            total_steady_points=total_steady_points,
            steady_ratio=steady_ratio
        )
        
        logger.info(
            f"[稳态识别] 识别到{result.segment_count}个稳态片段, "
            f"总稳态点数={total_steady_points}, 稳态比例={steady_ratio:.2%}"
        )
        
        return steady_data, result
