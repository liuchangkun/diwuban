"""
设备类型识别器 (app.services.characteristic_curves.preprocessing.device_type_detector)

识别设备类型(离心泵、混流泵、轴流泵等)。

版本: v1.0
参考: 设计文档 3.7.4节
"""

import logging
from typing import Any, Dict, Optional

import pandas as pd


logger = logging.getLogger(__name__)


class DeviceTypeDetector:
    """设备类型识别器
    
    识别设备类型:
    - 离心泵: specific_speed < 80
    - 混流泵: 80 ≤ specific_speed < 150
    - 轴流泵: specific_speed ≥ 150
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化设备类型识别器
        
        Args:
            config: 配置参数,可选
        """
        self._config = config or {}
        
        logger.info("[设备类型识别器] 初始化")
    
    def detect(
        self,
        device_params: Dict,
        data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """识别设备类型
        
        Args:
            device_params: 设备参数字典
            data: 运行数据(可选)
        
        Returns:
            Dict: 识别结果
                {
                    "device_type": str,  # 'centrifugal', 'mixed_flow', 'axial_flow'
                    "confidence": float,  # 0-1
                    "method": str,  # 'param_based', 'specific_speed', 'data_analysis'
                    "details": Dict  # 额外信息
                }
        """
        # 方法1: 优先检查device_params中的pump_type字段
        if 'pump_type' in device_params:
            pump_type = device_params['pump_type']
            return {
                "device_type": pump_type,
                "confidence": 0.95,
                "method": "param_based",
                "details": {"source": "device_params.pump_type"}
            }
        
        # 方法2: 基于specific_speed计算
        if 'specific_speed' in device_params:
            ns = device_params['specific_speed']
            
            if ns < 80:
                device_type = 'centrifugal'
            elif ns < 150:
                device_type = 'mixed_flow'
            else:
                device_type = 'axial_flow'
            
            logger.info(
                f"[设备类型识别] 基于比转速: ns={ns}, type={device_type}"
            )
            
            return {
                "device_type": device_type,
                "confidence": 0.90,
                "method": "specific_speed",
                "details": {"specific_speed": ns}
            }
        
        # 方法3: 基于数据特征推断(简化实现)
        if data is not None and 'flow' in data.columns and 'head' in data.columns:
            # 简化的特征分析
            flow_mean = data['flow'].mean()
            head_mean = data['head'].mean()
            
            # 粗略估计(需要更复杂的算法)
            if head_mean > 50:
                device_type = 'centrifugal'
            elif head_mean > 20:
                device_type = 'mixed_flow'
            else:
                device_type = 'axial_flow'
            
            logger.info(
                f"[设备类型识别] 基于数据特征: head_mean={head_mean:.1f}, "
                f"type={device_type}"
            )
            
            return {
                "device_type": device_type,
                "confidence": 0.60,
                "method": "data_analysis",
                "details": {
                    "flow_mean": flow_mean,
                    "head_mean": head_mean
                }
            }
        
        # 默认:无法识别,返回离心泵
        logger.warning("[设备类型识别] 无足够信息,默认为离心泵")
        
        return {
            "device_type": "centrifugal",
            "confidence": 0.30,
            "method": "default",
            "details": {"reason": "insufficient_information"}
        }
