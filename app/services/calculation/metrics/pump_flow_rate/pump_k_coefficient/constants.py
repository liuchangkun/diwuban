"""
泵 k 系数常量定义（app.services.calculation.metrics.pump_flow_rate.pump_k_coefficient.constants）

本模块仅定义：
1. 物理常数（不可变）
2. 参数名称常量（用于数据库查询）
3. 置信度等级标识

所有可调参数从 calculation_parameters 表读取，禁止硬编码。
"""

from __future__ import annotations

# ==============================================================================
# 物理常数（不可变）
# ==============================================================================

# 压力转扬程系数：1 MPa ≈ 102 米水柱
# 物理推导：H = P / (ρg) = 1,000,000 / (1000 × 9.81) ≈ 102 米
PRESSURE_TO_HEAD: float = 102.0

# ==============================================================================
# 置信度等级标识
# ==============================================================================

CONFIDENCE_HIGH: str = "high"      # 样本数 >= 1000
CONFIDENCE_MEDIUM: str = "medium"  # 样本数 >= 100
CONFIDENCE_LOW: str = "low"        # 样本数 < 100（使用回退值）

# ==============================================================================
# 数据库参数名称常量
# ==============================================================================

# metric_key 和 method_id
METRIC_KEY: str = "pump_flow_rate"
METHOD_ID: str = "pump_flow_rate_method_a"

# 设备级参数（每台泵独立）
PARAM_NAME_K_COEFFICIENT: str = "pump_k_coefficient"

# 全局级参数
PARAM_NAME_H_RATED_DEFAULT: str = "pump_k_h_rated_default"
PARAM_NAME_F_RATED: str = "pump_k_f_rated"
PARAM_NAME_K_DEFAULT: str = "pump_k_default"
PARAM_NAME_K_MIN: str = "pump_k_min"
PARAM_NAME_K_MAX: str = "pump_k_max"
PARAM_NAME_HIGH_FREQ_THRESHOLD: str = "pump_k_high_freq_threshold"
PARAM_NAME_F_MIN_FALLBACK: str = "pump_k_f_min_fallback"
PARAM_NAME_F_MIN_LOWER_BOUND: str = "pump_k_f_min_lower_bound"
PARAM_NAME_F_MIN_UPPER_BOUND: str = "pump_k_f_min_upper_bound"
PARAM_NAME_MIN_SAMPLES: str = "pump_k_min_samples"

# 元数据参数名（存储学习结果的额外信息）
PARAM_NAME_K_SAMPLE_COUNT: str = "pump_k_sample_count"
PARAM_NAME_K_CONFIDENCE: str = "pump_k_confidence"
PARAM_NAME_K_SOURCE: str = "pump_k_source"

