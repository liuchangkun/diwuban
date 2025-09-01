"""
优化结果数据模型（app.models.optimization）

本模块定义了泵组优化相关的数据模型，包括：

核心模型：
- Optimization：优化结果完整模型
- OptimizationCreate：创建优化记录数据模型
- OptimizationRequest：优化请求模型
- OptimizationResponse：API 响应模型

优化类型：
- 能耗优化：最小化电力消耗
- 效率优化：最大化系统效率
- 成本优化：最小化运行成本
- 多目标优化：综合考虑多个目标

数据字段：
- 基础信息：优化ID、泵站ID、执行时间
- 优化目标：目标类型、约束条件
- 结果数据：推荐配置、预期收益、状态
- 执行信息：执行者、算法版本、耗时

使用方式：
    from app.models.optimization import OptimizationRequest, OptimizationTarget
    
    # 优化请求
    request = OptimizationRequest(
        station_id="PUMP001",
        target=OptimizationTarget.MIN_ENERGY,
        constraints={"min_flow": 100, "max_pressure": 0.8}
    )

注意事项：
- 推荐配置以 JSON 格式存储设备参数
- 预期收益以百分比形式表示
- 支持多种优化算法和目标函数
- 结果包含详细的分析和建议
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator, model_validator

from app.models.base import BaseModel, DeviceId, OptimizationStatus, StationId, TimestampMixin, ValidationMixin


class OptimizationTarget:
    """优化目标常量"""
    MIN_ENERGY = "min_energy"  # 最小化能耗
    MAX_EFFICIENCY = "max_efficiency"  # 最大化效率
    MIN_COST = "min_cost"  # 最小化成本
    MAX_FLOW = "max_flow"  # 最大化流量
    MIN_CARBON = "min_carbon"  # 最小化碳排放
    MULTI_OBJECTIVE = "multi_objective"  # 多目标优化
    
    @classmethod
    def all(cls) -> list[str]:
        """获取所有优化目标"""
        return [cls.MIN_ENERGY, cls.MAX_EFFICIENCY, cls.MIN_COST, 
                cls.MAX_FLOW, cls.MIN_CARBON, cls.MULTI_OBJECTIVE]


class OptimizationAlgorithm:
    """优化算法常量"""
    GENETIC_ALGORITHM = "genetic_algorithm"  # 遗传算法
    PARTICLE_SWARM = "particle_swarm"  # 粒子群算法
    DIFFERENTIAL_EVOLUTION = "differential_evolution"  # 差分进化
    SIMULATED_ANNEALING = "simulated_annealing"  # 模拟退火
    LINEAR_PROGRAMMING = "linear_programming"  # 线性规划
    NONLINEAR_PROGRAMMING = "nonlinear_programming"  # 非线性规划
    HEURISTIC = "heuristic"  # 启发式算法
    
    @classmethod
    def all(cls) -> list[str]:
        """获取所有优化算法"""
        return [cls.GENETIC_ALGORITHM, cls.PARTICLE_SWARM, cls.DIFFERENTIAL_EVOLUTION,
                cls.SIMULATED_ANNEALING, cls.LINEAR_PROGRAMMING, cls.NONLINEAR_PROGRAMMING,
                cls.HEURISTIC]


class Optimization(BaseModel, TimestampMixin, ValidationMixin):
    """
    优化结果完整数据模型
    
    包含泵组优化计算的所有结果信息和执行详情。
    对应数据库中的 optimization 表。
    """
    
    opt_id: Optional[int] = Field(
        description="优化ID（自增主键）",
        default=None
    )
    
    station_id: StationId = Field(
        description="泵站ID",
        max_length=50
    )
    
    run_timestamp: datetime = Field(
        description="优化计算执行时间"
    )
    
    target: str = Field(
        description="优化目标"
    )
    
    recommended_config: Dict[str, Any] = Field(
        description="推荐的设备运行配置（JSON格式）"
    )
    
    expected_savings: Optional[Decimal] = Field(
        description="预期节能率（%）",
        default=None,
        ge=0,
        le=100,
        decimal_places=2
    )
    
    status: str = Field(
        description="优化状态",
        default=OptimizationStatus.PENDING
    )
    
    executed_by: Optional[str] = Field(
        description="执行者",
        default=None,
        max_length=50
    )
    
    executed_at: Optional[datetime] = Field(
        description="执行时间",
        default=None
    )
    
    # 扩展字段
    algorithm: Optional[str] = Field(
        description="使用的优化算法",
        default=None
    )
    
    algorithm_version: Optional[str] = Field(
        description="算法版本",
        default=None,
        max_length=20
    )
    
    constraints: Optional[Dict[str, Any]] = Field(
        description="约束条件（JSON格式）",
        default=None
    )
    
    objective_values: Optional[Dict[str, Decimal]] = Field(
        description="目标函数值",
        default=None
    )
    
    computation_time_ms: Optional[float] = Field(
        description="计算耗时（毫秒）",
        default=None,
        ge=0
    )
    
    confidence_score: Optional[Decimal] = Field(
        description="置信度评分（0-100）",
        default=None,
        ge=0,
        le=100
    )
    
    baseline_config: Optional[Dict[str, Any]] = Field(
        description="基准配置（用于对比）",
        default=None
    )
    
    @field_validator('target')
    @classmethod
    def validate_target(cls, v: str) -> str:
        """验证优化目标"""
        if v not in OptimizationTarget.all():
            raise ValueError(f"无效的优化目标: {v}")
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """验证优化状态"""
        if v not in OptimizationStatus.all():
            raise ValueError(f"无效的优化状态: {v}")
        return v
    
    @field_validator('algorithm')
    @classmethod
    def validate_algorithm(cls, v: Optional[str]) -> Optional[str]:
        """验证优化算法"""
        if v is not None and v not in OptimizationAlgorithm.all():
            raise ValueError(f"无效的优化算法: {v}")
        return v


class OptimizationCreate(BaseModel, ValidationMixin):
    """
    创建优化记录时的数据模型
    
    包含创建优化记录所需的必要字段。
    """
    
    station_id: StationId = Field(
        description="泵站ID",
        max_length=50
    )
    
    target: str = Field(description="优化目标")
    
    recommended_config: Dict[str, Any] = Field(
        description="推荐配置"
    )
    
    expected_savings: Optional[Decimal] = Field(
        description="预期节能率",
        default=None,
        ge=0,
        le=100,
        decimal_places=2
    )
    
    executed_by: Optional[str] = Field(
        description="执行者",
        default=None,
        max_length=50
    )
    
    algorithm: Optional[str] = Field(
        description="优化算法",
        default=None
    )
    
    constraints: Optional[Dict[str, Any]] = Field(
        description="约束条件",
        default=None
    )
    
    objective_values: Optional[Dict[str, Decimal]] = Field(
        description="目标函数值",
        default=None
    )
    
    computation_time_ms: Optional[float] = Field(
        description="计算耗时",
        default=None,
        ge=0
    )


class OptimizationRequest(BaseModel, ValidationMixin):
    """
    优化请求模型
    
    用于定义优化任务的参数和选项。
    """
    
    station_id: StationId = Field(description="泵站ID")
    
    target: str = Field(description="优化目标")
    
    # 时间范围
    start_time: Optional[datetime] = Field(
        description="历史数据开始时间",
        default=None
    )
    
    end_time: Optional[datetime] = Field(
        description="历史数据结束时间",
        default=None
    )
    
    # 约束条件
    constraints: Dict[str, Any] = Field(
        description="约束条件",
        default_factory=dict
    )
    
    # 算法选项
    algorithm: str = Field(
        description="优化算法",
        default=OptimizationAlgorithm.GENETIC_ALGORITHM
    )
    
    max_iterations: Optional[int] = Field(
        description="最大迭代次数",
        default=1000,
        gt=0,
        le=10000
    )
    
    convergence_tolerance: Optional[Decimal] = Field(
        description="收敛容差",
        default=Decimal("0.001"),
        gt=0,
        le=1
    )
    
    # 目标权重（多目标优化时使用）
    objective_weights: Optional[Dict[str, Decimal]] = Field(
        description="目标权重",
        default=None
    )
    
    # 设备选择
    device_ids: Optional[List[DeviceId]] = Field(
        description="参与优化的设备ID列表",
        default=None
    )
    
    include_pump_curves: bool = Field(
        description="是否使用泵特性曲线",
        default=True
    )
    
    # 场景设置
    scenario_name: Optional[str] = Field(
        description="优化场景名称",
        default=None,
        max_length=100
    )
    
    base_load_profile: Optional[Dict[str, Any]] = Field(
        description="基础负荷曲线",
        default=None
    )
    
    @field_validator('target')
    @classmethod
    def validate_target(cls, v: str) -> str:
        """验证优化目标"""
        if v not in OptimizationTarget.all():
            raise ValueError(f"无效的优化目标: {v}")
        return v
    
    @field_validator('algorithm')
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """验证优化算法"""
        if v not in OptimizationAlgorithm.all():
            raise ValueError(f"无效的优化算法: {v}")
        return v
    
    @model_validator(mode='after')
    def validate_time_range(self) -> 'OptimizationRequest':
        """验证时间范围"""
        if self.start_time is not None and self.end_time is not None:
            if self.end_time <= self.start_time:
                raise ValueError("结束时间必须大于开始时间")
        return self


class OptimizationResult(BaseModel):
    """
    优化计算结果模型
    
    包含优化过程的详细结果和分析。
    """
    
    success: bool = Field(description="优化是否成功")
    
    optimization: Optional[Optimization] = Field(
        description="优化结果记录",
        default=None
    )
    
    # 性能指标
    improvement_percentage: Optional[Decimal] = Field(
        description="改进百分比",
        default=None
    )
    
    annual_savings_estimate: Optional[Decimal] = Field(
        description="年度节约估算（元）",
        default=None
    )
    
    payback_period_months: Optional[int] = Field(
        description="投资回收期（月）",
        default=None
    )
    
    # 详细分析
    current_performance: Optional[Dict[str, Any]] = Field(
        description="当前性能指标",
        default=None
    )
    
    optimized_performance: Optional[Dict[str, Any]] = Field(
        description="优化后性能指标",
        default=None
    )
    
    sensitivity_analysis: Optional[Dict[str, Any]] = Field(
        description="敏感性分析结果",
        default=None
    )
    
    # 实施建议
    implementation_steps: List[str] = Field(
        description="实施步骤",
        default_factory=list
    )
    
    risks: List[str] = Field(
        description="风险提示",
        default_factory=list
    )
    
    monitoring_suggestions: List[str] = Field(
        description="监控建议",
        default_factory=list
    )
    
    # 错误信息
    error_message: Optional[str] = Field(
        description="错误信息（失败时）",
        default=None
    )
    
    warnings: List[str] = Field(
        description="警告信息",
        default_factory=list
    )


class OptimizationResponse(Optimization):
    """
    API 响应中的优化模型
    
    继承自完整的 Optimization 模型，可以添加额外的响应字段。
    """
    
    # 关联信息
    station_name: Optional[str] = Field(
        description="泵站名称",
        default=None
    )
    
    # 实施状态
    implementation_status: Optional[str] = Field(
        description="实施状态",
        default=None
    )
    
    actual_savings: Optional[Decimal] = Field(
        description="实际节约效果",
        default=None
    )
    
    feedback_score: Optional[int] = Field(
        description="用户反馈评分（1-5）",
        default=None,
        ge=1,
        le=5
    )


class OptimizationComparison(BaseModel):
    """
    优化方案比较模型
    
    用于比较多个优化方案的效果。
    """
    
    baseline: Dict[str, Any] = Field(description="基准方案")
    
    options: List[Dict[str, Any]] = Field(description="优化方案列表")
    
    comparison_metrics: List[str] = Field(
        description="比较指标",
        default=["energy_consumption", "cost", "efficiency", "carbon_emission"]
    )
    
    recommendation: Optional[str] = Field(
        description="推荐方案",
        default=None
    )
    
    recommendation_reason: Optional[str] = Field(
        description="推荐理由",
        default=None
    )


class OptimizationSchedule(BaseModel, ValidationMixin):
    """
    优化调度模型
    
    用于定期优化任务的调度配置。
    """
    
    schedule_id: Optional[int] = Field(
        description="调度ID",
        default=None
    )
    
    station_id: StationId = Field(description="泵站ID")
    
    target: str = Field(description="优化目标")
    
    schedule_type: str = Field(
        description="调度类型",
        default="periodic"  # periodic, on_demand, event_triggered
    )
    
    frequency: Optional[str] = Field(
        description="执行频率（如 'daily', 'weekly', 'monthly'）",
        default=None
    )
    
    next_run: Optional[datetime] = Field(
        description="下次执行时间",
        default=None
    )
    
    is_active: bool = Field(
        description="是否激活",
        default=True
    )
    
    auto_apply: bool = Field(
        description="是否自动应用结果",
        default=False
    )
    
    notification_emails: List[str] = Field(
        description="通知邮箱列表",
        default_factory=list
    )