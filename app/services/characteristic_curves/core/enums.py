"""
特性曲线核心枚举定义 (app.services.characteristic_curves.core.enums)

本模块定义特性曲线拟合系统的所有枚举类型。

核心枚举:
- Scenario: 场景枚举(9种场景,包括P0单泵和P2泵组)
- CurveType: 曲线类型枚举
- PipelineStage: 管道阶段枚举(16个阶段)
- GroupProcessingStrategy: 泵组处理策略枚举(P2阶段)
- FitStatus: 拟合状态枚举
- ValidationStatus: 验证状态枚举
- PumpType: 泵类型枚举
- MonotonicityType: 单调性类型枚举

版本: v1.0
创建日期: 2025-12-11
参考文档: 特性曲线开发/开发文档/02_架构设计/02_数据流定义.md
"""

from enum import Enum


class Scenario(str, Enum):
    """场景枚举(9种场景)
    
    根据02_数据流定义.md第2节场景识别定义。
    
    P0阶段(单泵场景,3种):
    - SOFT_START_SINGLE: 软启动单泵(固定频率)
    - VFD_SINGLE: 变频单泵(频率波动 > 2Hz)
    - QUASI_FIXED_FREQ_SINGLE: 准固定频率单泵(频率波动 ≤ 2Hz)
    
    P2阶段(泵组场景,6种):
    - HOMOGENEOUS_GROUP: 同型号并联泵组
    - HETEROGENEOUS_GROUP: 异型号并联泵组(固定频率)
    - VFD_HETEROGENEOUS_FREQ: 异型号变频泵组
    - MIXED_GROUP: 混合运行模式泵组
    - MIXED_HETEROGENEOUS: 混合异型号泵组
    - GROUP_COMPOSITE: 复杂组合泵组
    """
    
    # P0单泵场景
    SOFT_START_SINGLE = "soft_start_single"  # 软启动单泵
    VFD_SINGLE = "vfd_single"  # 变频单泵
    QUASI_FIXED_FREQ_SINGLE = "quasi_fixed_freq_single"  # 准固定频率单泵
    
    # P2泵组场景
    HOMOGENEOUS_GROUP = "homogeneous_group"  # 同型号并联
    HETEROGENEOUS_GROUP = "heterogeneous_group"  # 异型号并联(固定频率)
    VFD_HETEROGENEOUS_FREQ = "vfd_heterogeneous_freq"  # 异型号变频
    MIXED_GROUP = "mixed_group"  # 混合运行模式
    MIXED_HETEROGENEOUS = "mixed_heterogeneous"  # 混合异型号
    GROUP_COMPOSITE = "group_composite"  # 复杂组合


class CurveType(str, Enum):
    """曲线类型枚举
    
    支持的曲线类型包括单泵曲线和泵组曲线。
    
    单泵曲线(6种):
    - QH: 流量-扬程曲线
    - QP: 流量-功率曲线
    - QETA: 流量-效率曲线
    - HETA: 扬程-效率曲线
    - PETA: 功率-效率曲线
    - QNPSH: 流量-汽蚀余量曲线
    
    泵组曲线(15种,P2阶段):
    - PARALLEL_QH/QP/QETA: 并联泵组曲线
    - N_Q/P/ETA: 台数优化曲线
    - 分配曲线、控制策略曲线等
    """
    
    # 单泵曲线
    QH = "qh"  # 流量-扬程
    QP = "qp"  # 流量-功率
    QETA = "qeta"  # 流量-效率
    HETA = "heta"  # 扬程-效率
    PETA = "peta"  # 功率-效率
    QNPSH = "qnpsh"  # 流量-汽蚀余量
    
    # 泵组曲线(P2阶段)
    PARALLEL_QH = "parallel_qh"  # 并联Q-H
    PARALLEL_QP = "parallel_qp"  # 并联Q-P
    PARALLEL_QETA = "parallel_qeta"  # 并联Q-η
    N_Q = "n_q"  # 台数-流量
    N_P = "n_p"  # 台数-功率
    N_ETA = "n_eta"  # 台数-效率
    LOAD_DISTRIBUTION = "load_distribution"  # 负载分配
    FLOW_DISTRIBUTION = "flow_distribution"  # 流量分配
    POWER_DISTRIBUTION = "power_distribution"  # 功率分配
    START_STOP_STRATEGY = "start_stop_strategy"  # 启停策略
    SWITCHING_TIMING = "switching_timing"  # 切换时机
    SWITCHING_PROCESS = "switching_process"  # 切换过程
    OPTIMAL_REGION = "optimal_region"  # 最优运行区域
    SPECIFIC_ENERGY = "specific_energy"  # 单位能耗
    COORDINATION_CONTROL = "coordination_control"  # 协调控制


class PipelineStage(str, Enum):
    """管道阶段枚举(16个阶段)
    
    根据02_数据流定义.md定义的完整16阶段数据流。
    
    P0阶段(13个阶段):
    1-13: 从时间窗口划分到结果存储
    
    P2阶段(3个阶段):
    14-16: 泵组处理相关阶段
    """
    
    # P0阶段(单泵曲线,13阶段)
    TIME_WINDOW_SPLIT = "time_window_split"  # 阶段1: 时间窗口划分
    SCENARIO_DETECT = "scenario_detect"  # 阶段2: 场景识别
    DATA_EXTRACT = "data_extract"  # 阶段3: 数据提取
    DATA_CLEAN = "data_clean"  # 阶段4: 数据预处理
    STEADY_STATE_DETECT = "steady_state_detect"  # 阶段5: 稳态识别
    CONSTRAINT_CALC = "constraint_calc"  # 阶段6: 约束计算
    FREQ_NORMALIZE = "freq_normalize"  # 阶段7: 频率归一化
    DATA_NORMALIZE = "data_normalize"  # 阶段8: 数据归一化
    METHOD_SELECT = "method_select"  # 阶段9: 方法选择
    CURVE_FIT = "curve_fit"  # 阶段10: 曲线拟合
    RESULT_VALIDATE = "result_validate"  # 阶段11: 结果验证
    HISTORICAL_EVAL = "historical_eval"  # 阶段12: 历史评估
    RESULT_STORE = "result_store"  # 阶段13: 存储结果
    
    # P2阶段(泵组曲线,3阶段)
    PUMP_GROUP_TYPE_DETECT = "pump_group_type_detect"  # 阶段14: 泵组类型识别
    PARALLEL_SYNTHESIS = "parallel_synthesis"  # 阶段15: 并联合成
    CORRECTION_MODEL_LEARN = "correction_model_learn"  # 阶段16: 修正系数学习
    
    # 额外阶段(非标准流程)
    PLOT_GENERATION = "plot_generation"  # 图表生成
    REPORT_GENERATION = "report_generation"  # 报告生成


class GroupProcessingStrategy(str, Enum):
    """泵组处理策略枚举(P2阶段)
    
    根据泵组类型选择不同的处理策略。
    """
    
    HOMOGENEOUS_PARALLEL = "homogeneous_parallel"  # 同型号并联
    HETEROGENEOUS_PARALLEL = "heterogeneous_parallel"  # 异型号并联
    VFD_GROUP = "vfd_group"  # 变频泵组
    MIXED_MODE = "mixed_mode"  # 混合模式
    SERIES_CONNECTION = "series_connection"  # 串联连接
    COMPLEX_COMBINATION = "complex_combination"  # 复杂组合


class FitStatus(str, Enum):
    """拟合状态枚举
    
    用于标识拟合结果的生命周期状态。
    """
    
    ACTIVE = "active"  # 活跃(最新版本)
    ARCHIVED = "archived"  # 已归档(历史版本)
    DEPRECATED = "deprecated"  # 已废弃(不再使用)


class ValidationStatus(str, Enum):
    """验证状态枚举
    
    用于标识验证结果的状态。
    """
    
    PASSED = "passed"  # 通过
    FAILED = "failed"  # 失败
    WARNING = "warning"  # 警告(部分通过)


class PumpType(str, Enum):
    """泵类型枚举
    
    根据控制方式区分泵的类型。
    """
    
    VARIABLE_FREQUENCY = "variable_frequency"  # 变频泵
    SOFT_START = "soft_start"  # 软启动泵
    UNKNOWN = "unknown"  # 未知类型


class MonotonicityType(str, Enum):
    """单调性类型枚举
    
    用于描述曲线的单调性特征。
    """
    
    INCREASING = "increasing"  # 单调递增
    DECREASING = "decreasing"  # 单调递减
    UNIMODAL = "unimodal"  # 单峰(先增后减)
    NON_MONOTONIC = "non_monotonic"  # 非单调


class QualityGrade(str, Enum):
    """质量等级枚举
    
    根据R²值划分拟合质量等级。
    
    等级标准:
    - EXCELLENT: R² ≥ 0.98
    - GOOD: 0.95 ≤ R² < 0.98
    - ACCEPTABLE: 0.90 ≤ R² < 0.95
    - POOR: R² < 0.90
    """
    
    EXCELLENT = "excellent"  # 优秀
    GOOD = "good"  # 良好
    ACCEPTABLE = "acceptable"  # 可接受
    POOR = "poor"  # 差


__all__ = [
    # 场景和类型
    "Scenario",
    "CurveType",
    "PumpType",
    
    # 管道和策略
    "PipelineStage",
    "GroupProcessingStrategy",
    
    # 状态和质量
    "FitStatus",
    "ValidationStatus",
    "QualityGrade",
    
    # 特征
    "MonotonicityType",
]
