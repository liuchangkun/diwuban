"""
频率归一化器 (app.services.characteristic_curves.preprocessing.frequency_normalizer)

将变频数据归一化到额定频率。

版本: v1.0
参考: 设计文档 3.7.3节
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


class FrequencyNormalizer:
    """频率归一化器
    
    将变频数据归一化到额定频率。
    
    归一化公式(相似定律):
    - Q_normalized = Q_actual × (f_rated / f_actual)
    - H_normalized = H_actual × (f_rated / f_actual)²
    - P_normalized = P_actual × (f_rated / f_actual)³
    """
    
    def __init__(self, config: Optional[dict] = None):
        """初始化频率归一化器
        
        Args:
            config: 配置参数,可选
        """
        self._config = config or {}
        self._default_rated_frequency = self._config.get('rated_frequency', 50.0)
        
        logger.info(
            "[频率归一化器] 初始化",
            extra={"extra_data": {
                "default_rated_frequency": self._default_rated_frequency,
            }}
        )
    
    def normalize(
        self,
        data: pd.DataFrame,
        rated_frequency: Optional[float] = None
    ) -> pd.DataFrame:
        """频率归一化
        
        Args:
            data: 数据DataFrame,必须包含frequency列
            rated_frequency: 额定频率(Hz),可选,默认50Hz
        
        Returns:
            pd.DataFrame: 归一化后的数据
        
        Raises:
            ValueError: 数据缺少必需列时
        """
        if 'frequency' not in data.columns:
            raise ValueError("数据缺少frequency列,无法进行频率归一化")
        
        rated_freq = rated_frequency or self._default_rated_frequency
        
        # 复制数据避免修改原始数据
        normalized_data = data.copy()
        
        # 计算频率比
        freq_ratio = rated_freq / normalized_data['frequency']
        
        # 归一化流量
        if 'flow' in normalized_data.columns:
            normalized_data['flow'] = normalized_data['flow'] * freq_ratio
        
        # 归一化扬程
        if 'head' in normalized_data.columns:
            normalized_data['head'] = normalized_data['head'] * (freq_ratio ** 2)
        
        # 归一化功率
        if 'power' in normalized_data.columns:
            normalized_data['power'] = normalized_data['power'] * (freq_ratio ** 3)
        
        # 效率不变
        # efficiency不需要归一化
        
        # 更新频率为额定频率
        normalized_data['frequency'] = rated_freq
        
        logger.info(
            f"[频率归一化] 完成归一化: rated_freq={rated_freq}Hz, "
            f"数据点数={len(normalized_data)}"
        )
        
        return normalized_data
    
    def should_normalize(
        self,
        data: pd.DataFrame,
        freq_std_threshold: float = 2.0
    ) -> bool:
        """判断是否需要频率归一化
        
        Args:
            data: 数据DataFrame
            freq_std_threshold: 频率标准差阈值,默认2.0Hz
        
        Returns:
            bool: 是否需要归一化
        """
        if 'frequency' not in data.columns:
            return False
        
        freq_std = data['frequency'].std()
        should_norm = freq_std > freq_std_threshold
        
        logger.debug(
            f"[频率归一化判断] freq_std={freq_std:.2f}Hz, "
            f"threshold={freq_std_threshold}Hz, should_normalize={should_norm}"
        )
        
        return should_norm
