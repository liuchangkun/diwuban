"""
场景识别器 (app.services.characteristic_curves.preprocessing.scenario_detector)

识别设备运行场景(9种)。

版本: v1.0
参考: 设计文档 3.7.1节
"""

import logging
from typing import Dict, Optional

import pandas as pd

from app.services.characteristic_curves.core.data_structures import (
    ScenarioDetectionResult,
    Scenario,
)


logger = logging.getLogger(__name__)


class ScenarioDetector:
    """场景识别器
    
    识别设备运行场景:
    - P0场景: SOFT_START_SINGLE, VFD_SINGLE, QUASI_FIXED_FREQ_SINGLE
    - P2场景: HOMOGENEOUS_GROUP, HETEROGENEOUS_GROUP等
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化场景识别器
        
        Args:
            config: 配置参数,可选
        """
        self._config = config or {}
        
        logger.info("[场景识别器] 初始化")
    
    def detect(
        self,
        device_id: int,
        device_params: Dict,
        data: pd.DataFrame
    ) -> ScenarioDetectionResult:
        """识别运行场景
        
        Args:
            device_id: 设备ID
            device_params: 设备参数字典
            data: 运行数据
        
        Returns:
            ScenarioDetectionResult: 场景识别结果
        """
        # P0阶段简化实现:只识别单泵场景
        device_type = device_params.get('device_type', 'single_pump')
        pump_type = device_params.get('pump_type', 'fixed_frequency')
        
        # 判断是否为泵组
        is_group = device_type.lower() in ['pump_group', 'group']
        
        if is_group:
            # P2场景:泵组
            scenario = Scenario.HOMOGENEOUS_GROUP
            supported = False  # P0阶段不支持泵组
            need_normalization = False
            confidence = 0.5
        else:
            # P0场景:单泵
            # 分析频率变化
            if 'frequency' in data.columns:
                freq_std = data['frequency'].std()
                freq_mean = data['frequency'].mean()
                
                if freq_std > 2.0:  # 频率波动大,变频泵
                    scenario = Scenario.VFD_SINGLE
                    supported = True
                    need_normalization = True
                    confidence = 0.9
                elif freq_std < 0.5:  # 频率稳定,准恒频
                    scenario = Scenario.QUASI_FIXED_FREQ_SINGLE
                    supported = True
                    need_normalization = False
                    confidence = 0.9
                else:  # 软启动
                    scenario = Scenario.SOFT_START_SINGLE
                    supported = True
                    need_normalization = False
                    confidence = 0.7
            else:
                # 无频率数据,默认准恒频
                scenario = Scenario.QUASI_FIXED_FREQ_SINGLE
                supported = True
                need_normalization = False
                confidence = 0.6
        
        logger.info(
            f"[场景识别] device_id={device_id}, scenario={scenario.value}, "
            f"supported={supported}, confidence={confidence:.2f}"
        )
        
        return ScenarioDetectionResult(
            scenario=scenario,
            supported=supported,
            need_normalization=need_normalization,
            confidence=confidence
        )
