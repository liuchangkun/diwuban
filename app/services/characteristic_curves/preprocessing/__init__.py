"""
预处理层模块 (app.services.characteristic_curves.preprocessing)

本模块提供数据预处理功能：
- DataCleaner: 数据清洗器
- Normalizer: 归一化器
- FeatureEngineer: 特征工程器

版本: v2.0
更新日期: 2025-12-11
清理说明: 删除了DataValidator和PreprocessingPipeline(不符合文档架构)
"""""

from app.services.characteristic_curves.preprocessing.data_cleaner import DataCleaner
from app.services.characteristic_curves.preprocessing.feature_engineer import FeatureEngineer
from app.services.characteristic_curves.preprocessing.normalizer import Normalizer
# P0新增模块
from app.services.characteristic_curves.preprocessing.scenario_detector import ScenarioDetector
from app.services.characteristic_curves.preprocessing.device_type_detector import DeviceTypeDetector
from app.services.characteristic_curves.preprocessing.steady_state_detector import SteadyStateDetector
from app.services.characteristic_curves.preprocessing.frequency_normalizer import FrequencyNormalizer
from app.services.characteristic_curves.preprocessing.data_normalizer import DataNormalizer, NormalizationParams

__all__ = [
    "DataCleaner",
    "Normalizer",
    "FeatureEngineer",
    # P0新增
    "ScenarioDetector",
    "DeviceTypeDetector",
    "SteadyStateDetector",
    "FrequencyNormalizer",
    "DataNormalizer",
    "NormalizationParams",
]
