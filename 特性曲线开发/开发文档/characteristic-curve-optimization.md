# 特性曲线拟合系统优化与完善 - 设计文档

**版本**: v1.0  
**创建日期**: 2025-12-11  
**状态**: 研究分析完成  

---

## 1. 问题概述

### 1.1 用户反馈的核心问题

根据用户描述,当前特性曲线拟合系统存在以下严重问题:

1. **代码实现严重偏离文档规范**:已完成的代码与开发文档中定义的架构、数据流、接口设计存在显著差异
2. **功能与流程缺失**:16阶段数据流中多个关键阶段未实现或仅为占位符
3. **占位函数泛滥**:大量函数仅有空实现或返回默认值,无实际业务逻辑
4. **执行结果不正确**:即使代码运行不报错,拟合结果也不符合物理规律或精度要求

### 1.2 参考文档体系

本优化设计基于以下权威文档:

**主要参考**:
- `特性曲线开发\开发文档` - 完整的37份设计文档(P0+P2阶段)
- `02_架构设计\02_数据流定义.md` - **权威**16阶段数据流定义
- `03_核心模块\01-08` - 8份核心模块详细设计
- `04_曲线模块\00-04` - 曲线基类与具体曲线实现
- `05_拟合方法\01-04` - 188种拟合方法分类定义

**补充参考**:
- `第一次开发` 目录下的文档 - 可作为参考但需综合研判

---

## 2. 研究分析

### 2.1 架构设计对比分析

#### 2.1.1 文档定义的标准架构

根据`02_架构设计\01_系统架构总览.md`,系统采用**分层模块化架构**:

**层次划分**:

| 层次 | 模块数 | 职责 | 优先级 |
|-----|-------|-----|-------|
| **核心数据结构** | 4 | FitResult, ValidationResult, MethodResult, EvaluationReport | P0 |
| **主管道层** | 1 | CurveFittingPipeline - 总入口协调者 | P0 |
| **方法层基础** | 2 | BaseMethod, MethodRegistry | P0 |
| **共用层核心** | 2 | ResultStorage, CacheManager | P0 |
| **共用层扩展** | 5 | BatchProcessor, ParameterOptimizer, HistoricalDataEvaluator, TimeWindowValidator, ResultOutput | P1 |
| **约束层** | 3 | MonotonicityConstraint, BoundaryConstraint, PhysicsValidator | P0 |
| **预处理层** | 3 | DataCleaner, Normalizer, FeatureEngineer | P1 |
| **曲线层** | 3+ | QHCurve, QPCurve, QEtaCurve + 泵组曲线 | P0/P2 |
| **拟合方法实现** | 188 | 数学方法75种, 物理模型39种, ML方法20种, 混合方法6种 | P0-P3 |

**关键设计原则**:

| 原则 | 说明 |
|-----|------|
| **依赖注入** | 共用层组件通过构造函数注入,不在内部创建 |
| **数据库访问** | 必须使用项目现有连接池`app/adapters/db/pool.py`,禁止重复造轮子 |
| **类型安全** | 使用Literal和TypedDict确保类型安全 |
| **顺序执行** | 禁止并发拟合多个设备 |

#### 2.1.2 当前代码实现的架构

通过代码分析发现的实际目录结构:

```
app/services/characteristic_curves/
├── __init__.py
├── models.py (DEPRECATED - 已废弃但仍被引用)
├── core/ (3 files)
├── shared/ (20 files - 共用层)
├── methods/ (4 dirs + 3 files - 方法层)
├── curves/ (11 files - 曲线层)
├── constraints/ (13 files - 约束层)
├── preprocessing/ (7 files - 预处理层)
├── output/ (3 files - 输出层)
├── pipeline/ (5 files - 管道层)
└── pump_group/ (16 files - 泵组处理层)
```

**问题识别**:

1. **models.py已废弃但仍被大量引用**:文件标记为DEPRECATED,建议使用`core.data_structures`,但`__init__.py`、`pipeline`等仍在导入
2. **core/目录缺失关键模块**:只有3个文件,缺少文档中定义的多个核心数据结构
3. **shared/目录文件过多**:20个文件混杂,缺乏清晰的子模块划分
4. **pump_group/目录提前实现**:P2阶段功能(泵组处理)优先级低于P0,不应在P0未完善时开发

### 2.2 数据流完整性分析

#### 2.2.1 权威数据流定义(16阶段)

根据`02_数据流定义.md`的**权威定义**:

**P0阶段(单泵曲线,13阶段)**:

| 阶段 | 名称 | 模块 | 输入 | 输出 | 执行类型 |
|:----:|------|------|------|------|:--------:|
| **1** | 时间窗口划分 | TimeWindowSplitter | device_id, curve_type | TimeWindowSplitResult | 必须 |
| **2** | 场景识别 | ScenarioDetector | device_id, 设备参数 | Scenario枚举 | **条件** |
| **3** | 数据提取 | DataExtractor | device_id, 时间窗口 | raw_data (DataFrame) | 必须 |
| **4** | 数据预处理 | DataCleaner | raw_data | cleaned_data | 必须 |
| **5** | 稳态识别 | SteadyStateDetector | cleaned_data | steady_state_data | **条件** |
| **6** | 约束计算 | Constraints | data, device_params | constraints_dict | 必须 |
| **7** | 频率归一化 | FrequencyNormalizer | data, frequency | normalized_data | **条件** |
| **8** | 数据归一化 | Normalizer | data, constraints | normalized_data, norm_params | 必须 |
| **9** | 方法选择 | MethodRegistry | curve_type, data | method_id | 必须 |
| **10** | 曲线拟合 | BaseMethod.fit() | X, y, constraints | MethodResult | 必须 |
| **11** | 结果验证 | Validator | method_result | ValidationResult | 必须 |
| **12** | 历史评估 | HistoricalDataEvaluator | predict_func, test_window | EvaluationReport | **条件** |
| **13** | 存储结果 | ResultStorage | FitResult | version | 必须 |

**P2阶段(泵组曲线,3阶段)**:

| 阶段 | 名称 | 模块 | 输入 | 输出 | 执行类型 |
|:----:|------|------|------|------|:--------:|
| **14** | 泵组类型识别 | PumpGroupProcessor | pump_infos | GroupProcessingStrategy | **条件** |
| **15** | 并联合成 | ParallelSynthesizer | 单泵曲线, N, H_system | SynthesisResult | 必须 |
| **16** | 修正系数学习 | SystemCorrectionModel | 运行数据 | correction_model | 必须 |

**关键执行条件**:

- 阶段2:根据配置决定是否执行场景识别
- 阶段5:当数据包含非稳态运行数据时执行
- 阶段7:仅当`pump_type='variable_frequency'`且`freq_std > 2.0`时执行
- 阶段12:仅当`time_split.can_evaluate=True`时执行
- 阶段14-16:P2阶段,仅当输入为`station_id + pump_combination`时执行

#### 2.2.2 当前代码实现的数据流

通过`pipeline/curve_fitting_pipeline.py`分析:

**已注册的阶段处理器**:

```python
_stage_handlers = {
    PipelineStage.TIME_WINDOW_SPLIT: self._stage_time_window_split,
    PipelineStage.SCENARIO_DETECT: self._stage_scenario_detect,
    PipelineStage.DATA_EXTRACT: self._stage_data_extract,
    PipelineStage.DATA_CLEAN: self._stage_data_clean,
    PipelineStage.STEADY_STATE_DETECT: self._stage_steady_state_detect,
    PipelineStage.CONSTRAINT_CALC: self._stage_constraint_calc,
    PipelineStage.FREQ_NORMALIZE: self._stage_freq_normalize,
    PipelineStage.DATA_NORMALIZE: self._stage_data_normalize,
    PipelineStage.METHOD_SELECT: self._stage_method_select,
    PipelineStage.CURVE_FIT: self._stage_curve_fit,
    PipelineStage.RESULT_VALIDATE: self._stage_result_validate,
    PipelineStage.HISTORICAL_EVAL: self._stage_historical_eval,
    PipelineStage.RESULT_STORE: self._stage_result_store,
    PipelineStage.PLOT_GENERATION: self._stage_plot_generation,
    PipelineStage.REPORT_GENERATION: self._stage_report_generation,
}
```

**缺失阶段对比**:

| 文档定义阶段 | 代码实现状态 | 问题描述 |
|------------|------------|---------|
| 阶段1-13 | 部分实现 | 处理器已注册,但多数仅为占位 |
| 阶段14-16 | **缺失** | P2泵组阶段完全未集成到管道 |
| 阶段17-18 | **额外** | 文档未定义的PLOT_GENERATION和REPORT_GENERATION |

### 2.3 关键模块缺失与占位分析

通过grep搜索和代码检查,识别以下缺失模块:

#### 2.3.1 共用层缺失模块(独立模块)

| 模块名 | 文件路径 | 状态 |
|-------|---------|------|
| DataExtractor | `shared/data_extractor.py` | **缺失** |
| ResultStorage | `shared/result_storage.py` | ✓ 存在 |
| CacheManager | `shared/cache_manager.py` | ✓ 存在 |
| TimeWindowSplitter | `shared/time_window_splitter.py` | ✓ 存在 |
| BatchProcessor | `shared/batch_processor.py` | **缺失** |
| ParameterOptimizer | `shared/parameter_optimizer.py` | **缺失** |
| HistoricalDataEvaluator | `shared/historical_data_evaluator.py` | **缺失** |
| TimeWindowValidator | `shared/time_window_validator.py` | **缺失** |
| CurvePointGenerator | `shared/curve_point_generator.py` | **缺失** |
| ResultOutput | `output/result_output.py` | 部分存在,需对照文档 |

#### 2.3.2 预处理层缺失模块(独立模块)

| 模块名 | 文件路径 | 状态 |
|-------|---------|------|
| ScenarioDetector | `preprocessing/scenario_detector.py` | **缺失** |
| DeviceTypeDetector | `preprocessing/device_type_detector.py` | **缺失** |
| SteadyStateDetector | `preprocessing/steady_state_detector.py` | **缺失** |
| FrequencyNormalizer | `preprocessing/frequency_normalizer.py` | **缺失** |

**重要说明**: DataCleaner、Normalizer、FeatureEngineer等不是独立模块,而是各个曲线内部的子模块(如QHPreprocessor)

**场景枚举定义缺失**:

文档要求的`Scenario`枚举应包含9种场景:

- P0单泵: SOFT_START_SINGLE, VFD_SINGLE, QUASI_FIXED_FREQ_SINGLE
- P2泵组: HOMOGENEOUS_GROUP, HETEROGENEOUS_GROUP, VFD_HETEROGENEOUS_FREQ, MIXED_GROUP, MIXED_HETEROGENEOUS, GROUP_COMPOSITE

当前`models.py`中的`FittingScenario`枚举定义不完整且已废弃。

#### 2.3.3 曲线层模块完整性

| 曲线类 | 文件路径 | 状态 | 必需的子模块(7个) |
|-------|---------|------|------------------|
| QHCurve | `curves/qh_curve.py` | ✓ 存在 | QHDataExtractor, QHPreprocessor, QHConstraints, QHNormalizer, QHMethodSelector, QHCurveFitter, QHValidator |
| QPCurve | `curves/qp_curve.py` | ✓ 存在 | QPDataExtractor, QPPreprocessor, QPConstraints, QPNormalizer, QPMethodSelector, QPCurveFitter, QPValidator |
| QEtaCurve | `curves/qeta_curve.py` | ✓ 存在 | QEtaDataExtractor, QEtaPreprocessor, QEtaConstraints, QEtaNormalizer, QEtaMethodSelector, QEtaCurveFitter, QEtaValidator |

**重要**: 需要验证每个曲线类是否包含完整的7个子模块。曲线子模块不是独立文件,而是在曲线类内部实现。

### 2.4 拟合方法完整性分析

#### 2.4.1 文档定义的方法分类

根据`05_拟合方法\98_188种方法目录.md`:

| 方法类别 | 方法数量 | 优先级 | 关键方法示例 |
|---------|:-------:|:------:|------------|
| **数学方法** | 75 | P0-P2 | 多项式(2-10阶), 样条插值, B样条, 傅里叶级数 |
| **物理模型** | 39 | P0 | 泵特性方程, 流体力学模型 |
| **机器学习** | 20 | P1 | SVR, RandomForest, GradientBoost, MLP |
| **混合方法** | 6 | P2 | 物理+ML, 多尺度混合 |

#### 2.4.2 当前代码实现的方法

通过目录结构分析:

```
methods/
├── mathematical/ (8 files)
│   ├── polynomial.py
│   ├── spline.py
│   ├── ...
├── physical/ (4 files)
│   ├── pump_characteristic.py
│   ├── ...
├── machine_learning/ (5 files)
│   ├── gradient_boost.py
│   ├── ...
└── hybrid/ (3 files)
```

**问题识别**:

1. **方法数量严重不足**:
   - 数学方法:8个文件 vs 文档要求75种
   - 物理模型:4个文件 vs 文档要求39种
   - 机器学习:5个文件 vs 文档要求20种
   - 混合方法:3个文件 vs 文档要求6种

2. **方法注册不完整**:需验证`MethodRegistry`是否正确注册所有已实现方法

3. **方法优先级混乱**:P0核心方法与P1扩展方法未区分

### 2.5 核心数据结构一致性分析

#### 2.5.1 文档定义的核心数据结构

根据`03_核心模块\06_数据结构.md`:

| 数据结构 | 用途 | 关键字段 |
|---------|-----|---------|
| **FitResult** | 完整拟合流程的最终输出 | device_id, curve_type, method_id, coefficients, r_squared, rmse, validation_result, version |
| **ValidationResult** | 验证结果 | is_valid, monotonicity_passed, boundary_passed, physics_passed, physics_score |
| **MethodResult** | 单个拟合方法的直接输出 | method_id, coefficients, r_squared, predict_func, formula |
| **EvaluationReport** | 历史评估报告 | deviation_stats, pass_rate, segment_evaluation |
| **TimeWindowSplitResult** | 时间窗口划分结果 | fit_window, test_window, can_evaluate |
| **ScenarioDetectionResult** | 场景识别结果 | scenario, supported, need_normalization |
| **GroupFitResult** | 泵组拟合结果(P2) | station_id, pump_combination, group_type |
| **SynthesisResult** | 并联合成结果(P2) | Q_total, H_system, pump_flows |

#### 2.5.2 当前代码实现的数据结构

当前`models.py`标记为DEPRECATED,但仍包含部分数据结构定义。

**问题识别**:

1. **TimeWindowSplitResult缺失**:文档明确定义该结构,但代码中未找到
2. **ScenarioDetectionResult缺失**:场景识别结果的标准结构未定义
3. **EvaluationReport不完整**:缺少分段评估等关键字段

### 2.6 数据库表结构分析

#### 2.6.1 文档定义的表结构

根据`06_数据库\01_表结构设计.md`,采用**三表分离设计**:

**核心表**:

| 表名 | 用途 | 关键字段 |
|-----|-----|---------|
| `curve_fit_results` | 主表 | id, device_id, curve_type, version, method_name, status |
| `curve_fit_params` | 参数表 | result_id, param_category, param_key, param_value |
| `curve_fit_metrics` | 指标表 | result_id, metric_name, metric_value |

**P2扩展字段**:

- `curve_fit_results`新增: station_id, pump_combination, group_type, correction_model

**约束条件**:

1. 单泵/泵组互斥: device_id和pump_combination不能同时为空或同时有值
2. 泵组版本唯一性: (station_id, pump_combination, curve_type, version) UNIQUE
3. 泵组类型枚举: group_type CHECK约束与GroupProcessingStrategy枚举对齐

#### 2.6.2 当前数据库实现

由于数据库连接问题暂未验证,但从文档和代码推断:

**待验证项**:

1. 三表是否已创建
2. P2扩展字段是否已添加
3. 约束条件是否已实施
4. 索引是否已创建(JSONB字段的GIN索引,复合索引等)

### 2.7 主管道实现问题分析

#### 2.7.1 依赖注入问题

**文档要求**:

```python
class CurveFittingPipeline:
    def __init__(
        self,
        method_registry: 'MethodRegistry',           # 必需
        result_storage: 'ResultStorage',             # 必需
        cache_manager: Optional['CacheManager'] = None,
        ...
    ):
```

**当前实现**:

```python
def __init__(
    self,
    method_registry: Optional[Any] = None,  # 暂时可选以保持向后兼容
    result_storage: Optional[Any] = None,   # 暂时可选以保持向后兼容
    ...
):
    if method_registry is None:
        self._method_registry = MethodRegistry()  # 自动创建
```

**问题**:

1. 必需参数改为可选,违反依赖注入原则
2. 在构造函数内部创建依赖,增加耦合
3. "向后兼容"理由不成立,应直接按文档重构

#### 2.7.2 阶段处理器占位问题

通过代码检查,多数`_stage_*`方法仅为占位:

```python
def _stage_scenario_detect(self, ctx: PipelineContext) -> StageResult:
    """场景识别 - 占位实现"""
    # TODO: 实现场景识别逻辑
    return StageResult(success=True, data={'scenario': 'unknown'})
```

**占位阶段列表**(需逐一验证):

- _stage_scenario_detect
- _stage_data_extract
- _stage_steady_state_detect
- _stage_freq_normalize
- _stage_constraint_calc
- _stage_historical_eval

#### 2.7.3 错误处理缺失

文档要求的异常类型:

| 异常类型 | 错误码 | 触发条件 |
|---------|-------|---------|
| DataExtractionError | CF009 | 数据提取失败 |
| FittingError | CF010 | 拟合失败 |
| ValidationError | CF011 | 验证失败 |
| DatabaseConnectionError | CF012 | 数据库连接失败 |
| PumpGroupProcessingError | CF015 | 泵组处理失败 |

当前代码缺少系统化的异常定义和处理机制。

### 2.8 测试覆盖缺失分析

根据`09_测试规范`,系统应包含:

| 测试类型 | 覆盖率目标 | 说明 |
|---------|:--------:|------|
| **单元测试** | 90% | 每个模块独立测试 |
| **集成测试** | 80% | 模块间协作测试 |
| **端到端测试** | 关键路径100% | 完整拟合流程测试 |

当前`tests/`目录下虽有测试文件,但:

1. 测试覆盖率未知
2. 缺少完整的端到端测试
3. 占位函数无对应测试

---

## 3. 关键发现总结

### 3.1 严重程度分级

| 等级 | 问题 | 影响 |
|:---:|------|------|
| **P0-Critical** | 16阶段数据流未完整实现 | 系统核心功能不可用 |
| **P0-Critical** | DataExtractor等关键模块缺失 | 无法从数据库提取数据 |
| **P0-Critical** | 188种拟合方法严重不足 | 拟合精度和适用性差 |
| **P0-Critical** | 数据库表结构未验证 | 无法正确存储结果 |
| **P1-High** | ScenarioDetector等条件执行模块缺失 | 部分场景无法正确处理 |
| **P1-High** | HistoricalDataEvaluator缺失 | 无法评估拟合精度 |
| **P1-High** | 依赖注入不符合规范 | 代码耦合度高,难以测试 |
| **P2-Medium** | P2泵组阶段未集成 | 泵组曲线功能不可用 |
| **P2-Medium** | 测试覆盖不足 | 代码质量无保障 |

### 3.2 偏离文档的根本原因

通过分析,识别出以下根本原因:

1. **渐进式开发失序**:
   - P0阶段未完成就开始P2阶段(pump_group目录)
   - 核心功能未稳定就添加扩展功能(PLOT_GENERATION等)

2. **文档理解偏差**:
   - 未严格按照`02_数据流定义.md`的权威流程实现
   - 混淆了P0、P1、P2的优先级

3. **向后兼容误区**:
   - 过度追求"向后兼容",导致应该废弃的代码(models.py)仍被引用
   - 应该强制的依赖注入被改为可选

4. **模块拆分过细**:
   - shared/目录20个文件,缺乏清晰的子目录结构
   - 导致难以理解模块边界

### 3.3 数据验证需求

为确保准确性,需验证:

1. **数据库表结构**:
   - 三表是否已创建并符合文档定义
   - P2扩展字段是否已添加
   - 约束和索引是否完整

2. **现有方法可用性**:
   - 已实现的拟合方法能否正常运行
   - MethodRegistry是否正确注册

3. **测试数据可用性**:
   - fact_measurements表是否有测试数据
   - device_rated_params表是否有设备参数

---

## 4. 澄清问题

### 4.1 优先级确认

由于问题范围广泛,需要用户明确优先级:

1. **P0阶段完善优先还是P2阶段实现优先?**
   - 建议:先完善P0单泵拟合,再实现P2泵组拟合

2. **188种方法全部实现还是核心方法优先?**
   - 建议:
     - P0阶段:数学方法(多项式2-5阶)、物理模型(泵特性方程)
     - P1阶段:补充数学方法(样条)、机器学习方法(SVR)
     - P2-P3阶段:补充剩余方法

3. **测试覆盖率要求?**
   - 建议:P0核心功能单元测试90%,端到端测试覆盖主流程

### 4.2 技术选型确认

1. **是否保留现有占位代码?**
   - 建议:删除占位代码,按文档从零实现

2. **models.py废弃后的迁移策略?**
   - 建议:
     - 立即停止引用models.py
     - 所有引用迁移到core.data_structures
     - 删除models.py

3. **依赖注入强制执行?**
   - 建议:严格按文档要求,method_registry和result_storage为必需参数

### 4.3 数据验证需求

需要用户协助验证:

1. 数据库中curve_fit_*三表是否存在?
2. fact_measurements表是否有可用的测试数据?
3. 是否需要保留现有的拟合结果数据?

---

## 5. 优化方案设计

### 5.1 方案选择

**用户确认**: 采用方案2 - 全面重构

**核心理念**: 由于已有落地代码,需要及时删除无用、废弃、冗余的垃圾代码,确保代码库的清洁性和可维护性。

### 5.2 代码清理策略

#### 5.2.1 废弃代码识别与删除

**目标**: 删除已标记为废弃但仍被引用的代码,阻止技术债务积累

**待删除的废弃代码**:

| 文件/模块 | 路径 | 废弃原因 | 删除策略 |
|---------|------|---------|----------|
| **models.py** | `app/services/characteristic_curves/models.py` | 已标记DEPRECATED,应使用core.data_structures | 1. 迁移所有引用到core.data_structures<br>2. 删除文件 |
| **旧版数据结构** | models.py中的FittingScenario等 | 定义不完整且不符合文档规范 | 在core.data_structures中重新定义标准结构 |

**引用清理范围**:

需要清理models.py引用的文件包括:
- `__init__.py`
- `pipeline/curve_fitting_pipeline.py`
- 其他导入models.py的模块

#### 5.2.2 占位代码识别与删除

**目标**: 删除无实际业务逻辑的占位函数,避免误导和维护成本

**占位代码识别标准**:

1. 函数体仅包含`pass`语句
2. 函数体仅包含`# TODO`注释
3. 函数返回硬编码的默认值而无实际逻辑
4. 函数标注"占位实现"但无后续补充

**已识别的占位处理器**(pipeline层):

| 处理器方法 | 当前状态 | 清理策略 |
|----------|---------|----------|
| _stage_scenario_detect | 返回硬编码'unknown' | 删除,待实现ScenarioDetector后重新集成 |
| _stage_data_extract | 需验证 | 如为占位则删除 |
| _stage_steady_state_detect | 需验证 | 如为占位则删除 |
| _stage_freq_normalize | 需验证 | 如为占位则删除 |
| _stage_constraint_calc | 需验证 | 如为占位则删除 |
| _stage_historical_eval | 需验证 | 如为占位则删除 |

**清理原则**:

- 占位代码不保留:删除而非注释
- 管道阶段注册同步删除:从`_stage_handlers`字典中移除对应条目
- 相关测试同步删除:删除针对占位函数的无意义测试

#### 5.2.3 冗余代码识别与删除

**目标**: 删除重复实现、未使用的工具函数、过时的辅助类

**冗余代码识别维度**:

| 维度 | 识别方法 | 处理策略 |
|-----|---------|----------|
| **重复实现** | 多个模块实现相同功能 | 保留符合文档的版本,删除其他版本 |
| **未使用代码** | 无任何地方调用的函数/类 | 直接删除 |
| **过度抽象** | 仅被一处调用的抽象基类 | 合并到调用方,删除抽象层 |
| **冗余参数** | 函数中未使用的参数 | 删除参数并更新调用方 |

**shared/目录重点检查**:

shared/目录包含20个文件,需逐一检查:

1. **功能重复检查**: 是否有多个文件实现类似功能
2. **调用分析**: 识别未被任何地方调用的模块
3. **文档对照**: 不在文档定义范围内的自创模块应删除

#### 5.2.4 P2阶段代码处理

**目标**: 暂时隔离或删除P2泵组代码,聚焦P0阶段完善

**pump_group/目录处理策略**:

| 策略 | 描述 | 优缺点 |
|-----|------|--------|
| **策略A: 暂时隔离** | 将pump_group目录移至项目外部备份 | 优点:可复用<br>缺点:仍占用心智负担 |
| **策略B: 完全删除** | 删除整个pump_group目录及相关代码 | 优点:彻底清理<br>缺点:P2阶段需重新实现 |
| **策略C: 最小保留** | 仅保留PumpGroupProcessor框架,删除未完成的实现 | 优点:保留架构<br>缺点:仍需维护框架 |

**推荐策略**: 策略B - 完全删除

**理由**:

1. P0阶段尚未稳定,P2代码价值有限
2. 文档已充分定义P2需求,重新实现成本可控
3. 避免半成品代码干扰P0开发

**删除范围**:

- `pump_group/`目录全部内容
- pipeline中的P2阶段处理器(PUMP_GROUP_PROCESS等)
- 数据结构中的GroupFitResult、SynthesisResult(如已实现)

### 5.3 代码重组策略

#### 5.3.1 目录结构优化

**目标**: 建立清晰的模块边界,符合文档架构定义

**优化后的目录结构**:

```
app/services/characteristic_curves/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── data_structures.py        # 所有核心数据结构集中定义
│   ├── exceptions.py             # 系统异常类型定义
│   └── enums.py                  # 枚举类型(Scenario等)
│
├── pipeline/
│   ├── __init__.py
│   ├── curve_fitting_pipeline.py # 主管道
│   └── context.py                # 管道上下文
│
├── shared/
│   ├── __init__.py
│   ├── result_storage.py         # P0必需
│   ├── cache_manager.py          # P0必需
│   └── time_window_splitter.py   # P0必需
│   # 删除其他17个未在文档中明确定义的文件
│
├── preprocessing/
│   ├── __init__.py
│   ├── data_cleaner.py           # P0必需
│   └── normalizer.py             # P0必需
│   # 其他模块待P0核心稳定后补充
│
├── constraints/
│   ├── __init__.py
│   ├── monotonicity.py           # P0必需
│   ├── boundary.py               # P0必需
│   └── physics_validator.py      # P0必需
│
├── curves/
│   ├── __init__.py
│   ├── base_curve.py
│   ├── qh_curve.py               # P0必需
│   ├── qp_curve.py               # P0必需
│   └── qeta_curve.py             # P0必需
│
├── methods/
│   ├── __init__.py
│   ├── base_method.py
│   ├── method_registry.py
│   ├── mathematical/
│   │   ├── __init__.py
│   │   └── polynomial.py         # P0核心方法
│   └── physical/
│       ├── __init__.py
│       └── pump_characteristic.py # P0核心方法
│   # P1阶段再补充machine_learning/和hybrid/
│
└── output/
    ├── __init__.py
    └── plotter.py                # 图表生成
```

**关键变化**:

1. **删除models.py**: 所有定义迁移到core/
2. **精简shared/**: 从20个文件减少到3个P0必需文件
3. **删除pump_group/**: 整个目录移除
4. **methods/分阶段**: P0仅保留数学和物理方法,ML和混合方法待后续补充

#### 5.3.2 依赖关系梳理

**目标**: 建立清晰的依赖层次,避免循环依赖

**依赖层次定义**:

```
core/ (最底层,无依赖)
  ↓
curves/, constraints/, preprocessing/ (依赖core)
  ↓
methods/ (依赖core + curves + constraints)
  ↓
shared/ (依赖core + methods)
  ↓
pipeline/ (依赖所有层)
  ↓
output/ (依赖pipeline + core)
```

**禁止的依赖模式**:

- core/不得依赖任何内部模块
- methods/不得依赖shared/或pipeline/
- 任何模块不得依赖output/

#### 5.3.3 数据库访问统一化

**目标**: 复用项目现有数据库连接池,删除重复造轮子的代码

**用户要求**: 不要重复造轮子

**统一访问模式**:

| 组件 | 数据库需求 | 实现方式 |
|-----|----------|----------|
| DataExtractor | 读取fact_measurements | 通过连接池获取session |
| ResultStorage | 写入curve_fit_* | 通过连接池获取session |
| HistoricalDataEvaluator | 读取历史数据 | 复用DataExtractor |

**强制规范**:

```python
# ✓ 正确:复用现有连接池
from app.adapters.db.pool import get_db_session

class DataExtractor:
    def __init__(self):
        # 不持有连接,使用时获取
        pass
    
    def extract(self, ...):
        with get_db_session() as session:
            # 使用session查询
            pass

# ❌ 禁止:重复造轮子
from sqlalchemy import create_engine
engine = create_engine("postgresql://...")  # 禁止

# ❌ 禁止:自建连接池
from sqlalchemy.pool import QueuePool
pool = QueuePool(...)  # 禁止
```

**清理范围**:

- 删除所有`create_engine`调用
- 删除所有自建连接池代码
- 删除数据库URL硬编码
- 统一使用`app.adapters.db.pool`

### 5.4 核心模块补全策略

**用户明确要求**: 除了拟合方法外,所有模块必须完整实现

#### 5.4.1 core/模块补全 (必须实现)

**目标**: 建立完整的核心数据结构和异常体系

**core/data_structures.py** - 必须实现所有数据结构:

| 数据结构 | 实现要求 | 关键字段定义 |
|---------|:-------:|------------|
| FitResult | **必须** | device_id, curve_type, method_id, coefficients, r_squared, rmse, validation_result, version, created_at |
| ValidationResult | **必须** | is_valid, monotonicity_passed, boundary_passed, physics_passed, physics_score, error_details |
| MethodResult | **必须** | method_id, coefficients, r_squared, predict_func, formula, convergence_info |
| TimeWindowSplitResult | **必须** | fit_window: tuple[datetime, datetime], test_window: Optional[tuple], can_evaluate: bool |
| ScenarioDetectionResult | **必须** | scenario: Scenario, supported: bool, need_normalization: bool, confidence: float |
| EvaluationReport | **必须** | deviation_stats: dict, pass_rate: float, segment_evaluation: list, test_window: tuple |
| GroupFitResult | **必须** | station_id, pump_combination, group_type (P2阶段使用) |
| SynthesisResult | **必须** | Q_total, H_system, pump_flows (P2阶段使用) |

**core/exceptions.py** - 必须实现所有异常:

| 异常类 | 错误码 | 继承关系 | 实现要求 |
|-------|-------|----------|:-------:|
| CurveFittingError | CF000 | Exception (基类) | **必须** |
| DataExtractionError | CF009 | CurveFittingError | **必须** |
| FittingError | CF010 | CurveFittingError | **必须** |
| ValidationError | CF011 | CurveFittingError | **必须** |
| DatabaseConnectionError | CF012 | CurveFittingError | **必须** |
| PumpGroupProcessingError | CF015 | CurveFittingError | **必须** |

**core/enums.py** - 必须实现所有枚举:

| 枚举 | 值定义 | 用途 | 实现要求 |
|-----|-------|------|:-------:|
| Scenario | 9种场景(包括P0和P2) | 场景识别 | **必须** |
| CurveType | QH, QP, QETA | 曲线类型 | **必须** |
| PipelineStage | 16个阶段枚举 | 管道阶段标识 | **必须** |
| GroupProcessingStrategy | 泵组类型枚举 | P2泵组处理 | **必须** |

#### 5.4.2 共用层模块补全 (必须全部实现)

**用户提醒**: 不要把公用模块和独立模块搞混

**说明**: shared/目录下是所有曲线共用的独立模块,必须全部完整实现

| 模块 | 文件路径 | 实现要求 | 职责 |
|-----|---------|:-------:|------|
| DataExtractor | shared/data_extractor.py | **必须实现** | 从fact_measurements提取数据 |
| ResultStorage | shared/result_storage.py | **必须实现** | 拟合结果存储和加载 |
| CacheManager | shared/cache_manager.py | **必须实现** | 缓存管理 |
| TimeWindowSplitter | shared/time_window_splitter.py | **必须实现** | 时间窗口划分 |
| BatchProcessor | shared/batch_processor.py | **必须实现** | 批处理 |
| ParameterOptimizer | shared/parameter_optimizer.py | **必须实现** | 参数优化 |
| HistoricalDataEvaluator | shared/historical_data_evaluator.py | **必须实现** | 历史评估 |
| TimeWindowValidator | shared/time_window_validator.py | **必须实现** | 时间窗口验证 |
| CurvePointGenerator | shared/curve_point_generator.py | **必须实现** | 曲线特征点生成 |
| MethodSelector | shared/method_selector.py | **必须实现** | 拟合方法选择 |
| ConstraintOptimizer | constraints/constraint_optimizer.py | **必须实现** | 约束优化 |

##### 5.4.2.1 DataExtractor数据获取规范

**用户要求**: 特性曲线对数据量、时间跨度、覆盖范围、质量都有明确要求

(…SQL查询模板略…)

##### 5.4.2.2 HistoricalDataEvaluator历史评估器规范

**职责**: 评估曲线对独立测试数据的预测能力

**评估原理**:

- 曲线拟合使用**fit_window(拟合窗口)**内的数据进行训练
- 预测评估使用**test_window(测试窗口)**内的独立数据进行验证
- 两个窗口**不重叠**,测试窗口在拟合窗口之后
- 合格标准: `within_5_percent ≥ 90%`(90%的测试点偏差小于5%)

**核心功能**:

1. **曲线预测评估**(核心): 用独立测试数据验证曲线预测能力
2. 数据质量评估(完整性、一致性、异常值)
3. 拟合结果稳定性分析
4. 历史版本对比

**核心接口**:

```python
class HistoricalDataEvaluator:
    """历史数据评估器"""
    
    def __init__(self, data_extractor: Optional['DataExtractor'] = None):
        """初始化
        
        Args:
            data_extractor: 数据提取器(可选,用于从数据库提取数据)
        """
    
    def evaluate_prediction_accuracy(
        self,
        device_id: int,
        curve_type: str,
        predict_func: Callable[[float], float],
        test_window: TimeWindow,
        test_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """评估曲线对独立测试数据的预测能力(核心方法)
        
        Args:
            device_id: 设备ID
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            predict_func: 预测函数,输入X返回预测Y
            test_window: 测试窗口
            test_data: 测试数据(可选,如不提供则从fact_measurements读取)
            
        Returns:
            Dict: {
                'test_period': {'start': datetime, 'end': datetime},
                'test_point_count': int,
                'deviation_stats': {
                    'mean_relative_deviation': float,  # 平均相对偏差(%)
                    'max_relative_deviation': float,   # 最大相对偏差(%)
                    'p50_deviation': float,            # 中位数偏差(%)
                    'p90_deviation': float,            # 90%分位数偏差(%)
                    'p95_deviation': float             # 95%分位数偏差(%)
                },
                'pass_rate': {
                    'within_5_percent': float,  # 5%内通过率
                    'within_10_percent': float  # 10%内通过率
                },
                'segment_evaluation': {  # 分段评估(低/中/高流量)
                    'low_flow': {...},
                    'medium_flow': {...},
                    'high_flow': {...}
                },
                'overall_passed': bool  # 总体是否通过(within_5_percent >= 0.90)
            }
        """
    
    def evaluate_data_quality(
        self,
        data: pd.DataFrame,
        required_columns: List[str]
    ) -> Dict[str, Any]:
        """评估数据质量
        
        Returns:
            Dict: 包含completeness, outlier_ratio, quality_score等
        """
    
    def evaluate_stability(
        self,
        device_id: int,
        curve_type: str,
        versions: List[str]
    ) -> Dict[str, Any]:
        """评估拟合结果稳定性
        
        Returns:
            Dict: 包含stability_score, evaluated_versions等
        """
    
    def compare_versions(
        self,
        device_id: int,
        curve_type: str,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """对比两个版本的拟合结果
        
        Returns:
            Dict: 包含r2_diff, rmse_diff, param_changes等
        """
```

**关键实现要求**:

1. **数据来源**: 必须从TimeWindow指定的时间范围内的fact_measurements表读取
2. **相对偏差计算**: `relative_deviation = |Y_pred - Y_actual| / Y_actual * 100%`
3. **通过率计算**: `within_5_percent = (偏差≤5%的点数) / (总测试点数)`
4. **分段评估**: 按流量分为低/中/高三段,分别统计偏差
5. **合格标准**: within_5_percent >= 0.90 且 within_10_percent >= 0.98
6. **禁止硬编码**: 通过率阈值必须从数据库method_params JSONB读取

##### 5.4.2.3 CacheManager缓存管理器规范

**职责**: 管理系统级别的缓存,提高性能

**缓存策略**:

- **缓存键**: 基于设备ID、曲线类型等生成
- **失效条件**: 设备参数更新、版本更新时失效
- **存储方式**: 进程级内存缓存(Dict)
- **缓存范围**: 约束参数、拟合结果、设备参数等

**核心接口**:

```python
class CacheManager:
    """缓存管理器(单例模式)"""
    
    _instance: Optional['CacheManager'] = None
    _cache: Dict[str, Any] = {}
    _stats: Dict[str, int] = {'hits': 0, 'misses': 0}
    
    def __new__(cls) -> 'CacheManager':
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        """获取缓存
        
        Args:
            key: 缓存键
            default: 默认值(缓存不存在时返回)
            
        Returns:
            缓存值或默认值
        """
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间(秒,可选)
        """
    
    def invalidate(
        self,
        pattern: Optional[str] = None
    ) -> int:
        """使缓存失效
        
        Args:
            pattern: 缓存键模式(可选,不指定则清除所有缓存)
            
        Returns:
            int: 清除的缓存数量
        """
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计
        
        Returns:
            Dict: {
                'hits': int,
                'misses': int,
                'hit_rate': float,
                'cache_size': int
            }
        """
```

**关键实现要求**:

1. **必须使用单例模式**: 确保全局唯一实例
2. **线程安全**: 如果需要支持多线程,必须使用threading.Lock
3. **缓存键生成**: 必须使用一致的缓存键格式,建议: `f"{module}:{entity_id}:{attribute}"`
4. **缓存统计**: 必须记录hits/misses,用于性能分析
5. **内存控制**: 防止缓存无限增长,建议设置最大缓存数量限制

##### 5.4.2.4 DataExtractor数据获取规范(继续)

**数据量要求**:

| 级别 | 数据点数 | 拟合质量 | SQL WHERE条件建议 |
|-----|---------|---------|-------------------|
| 最小 | ≥100个 | 可拟合基本曲线 | 时间跨度≥1天 |
| 推荐 | 500-1000个 | 较好精度 | 时间跨度≥1周 |
| 理想 | >5000个 | 高精度,覆盖各种工况 | 时间跨度≥1个月 |

**数据时间跨度要求**:

| 级别 | 时间跨度 | 覆盖工况 | 适用场景 |
|-----|---------|---------|----------|
| 最小 | 1天 | 日常运行工况 | 紧急拟合、快速验证 |
| 推荐 | 1周 | 不同负荷模式 | 常规拟合任务 |
| 理想 | 1个月 | 季节性变化、各种运行模式 | 高精度拟合、模型训练 |

**数据覆盖范围要求**:

| 优先级 | 流量范围 | 覆盖工况 | WHERE条件示例 |
|-------|---------|---------|---------------|
| 必须覆盖 | 20%-100% Q_rated | 正常运行工况 | `Q BETWEEN 0.2*Q_rated AND Q_rated` |
| 推荐覆盖 | 10%-120% Q_rated | 低负荷+高负荷 | `Q BETWEEN 0.1*Q_rated AND 1.2*Q_rated` |
| 理想覆盖 | 0%-120% Q_rated | 全范围工况(含启停、变频) | `Q >= 0 AND Q <= 1.2*Q_rated` |

**数据质量要求**:

| 质量指标 | 推荐值 | 验证方式 | SQL过滤条件 |
|---------|-------|---------|-------------|
| 数据完整性 | 缺失率<5% (推荐<2%) | `COUNT(Q IS NULL)/COUNT(*) < 0.05` | `Q IS NOT NULL AND H IS NOT NULL` |
| 数据准确性 | 异常值率<3% (推荐<1%) | 基于3σ或IQR识别异常值 | `Q > 0 AND H > 0` |
| 采样频率 | 每分钟1次 (推荐30秒) | 检查ts_bucket间隔 | `ts_bucket间隔≤1分钟` |

**标准SQL查询模板**(结合所有要求):

```sql
-- 通用数据提取查询(适用于QH/QP/QEta)
WITH raw_data AS (
    SELECT 
        ts_bucket,
        device_id,
        MAX(CASE WHEN metric_key = 'pump_flow_rate' THEN value END) AS Q,
        MAX(CASE WHEN metric_key = :target_metric THEN value END) AS Y,
        MAX(CASE WHEN metric_key = 'pump_status' THEN value END) AS status
    FROM fact_measurements
    WHERE 
        device_id = :device_id
        AND ts_bucket BETWEEN :start_time AND :end_time
        AND metric_key IN ('pump_flow_rate', :target_metric, 'pump_status')
    GROUP BY ts_bucket, device_id
),
valid_data AS (
    SELECT 
        ts_bucket,
        Q,
        Y
    FROM raw_data
    WHERE 
        -- 数据完整性: 必须同时存在Q和Y
        Q IS NOT NULL 
        AND Y IS NOT NULL
        -- 数据准确性: 删除明显无效值
        AND Q >= 0 
        AND Y >= 0
        -- 运行状态: 仅保留泵运行状态数据(status=1)
        AND (status IS NULL OR status = 1)
),
data_quality_check AS (
    SELECT 
        COUNT(*) AS total_points,
        COUNT(DISTINCT ts_bucket) AS unique_timestamps,
        MIN(ts_bucket) AS data_start,
        MAX(ts_bucket) AS data_end,
        EXTRACT(EPOCH FROM (MAX(ts_bucket) - MIN(ts_bucket))) / 86400 AS time_span_days,
        MIN(Q) AS Q_min,
        MAX(Q) AS Q_max,
        AVG(Q) AS Q_avg,
        STDDEV(Q) AS Q_std
    FROM valid_data
)
SELECT 
    vd.ts_bucket,
    vd.Q,
    vd.Y
FROM valid_data vd
CROSS JOIN data_quality_check dqc
WHERE 
    -- 最小数据量检查: 至少100个有效数据点
    dqc.total_points >= 100
    -- 时间跨度检查: 至少1天
    AND dqc.time_span_days >= 1.0
    -- 流量覆盖范围检查: 必须覆盖正常运行工况(20%-100% Q_rated)
    AND dqc.Q_max >= 0.2 * :q_rated
ORDER BY vd.ts_bucket;
```

**参数说明**:

| 参数 | 类型 | 说明 | QH示例 | QP示例 | QEta示例 |
|-----|------|------|--------|--------|----------|
| :device_id | VARCHAR | 设备ID | 'PUMP_001' | 'PUMP_001' | 'PUMP_001' |
| :start_time | TIMESTAMP | 查询开始时间 | NOW() - INTERVAL '7 days' | NOW() - INTERVAL '7 days' | NOW() - INTERVAL '7 days' |
| :end_time | TIMESTAMP | 查询结束时间 | NOW() | NOW() | NOW() |
| :target_metric | VARCHAR | 目标指标 | 'pump_head' | 'pump_active_power' | 'pump_efficiency' |
| :q_rated | FLOAT | 额定流量 | 100.0 | 100.0 | 100.0 |

**数据质量验证逻辑**(Python实现):

提取数据后,DataExtractor必须验证:

1. **数据点数验证**:
   - 最小要求: ≥100个
   - 推荐: ≥500个
   - 理想: ≥5000个
   - 不满足最小要求时抛出DataExtractionError

2. **时间跨度验证**:
   - 计算: (max(ts_bucket) - min(ts_bucket)).days
   - 最小要求: ≥1天
   - 推荐: ≥7天
   - 不满足最小要求时发出警告

3. **流量覆盖范围验证**:
   - 计算: Q_min, Q_max
   - 必须覆盖: Q_max ≥ 0.2 × Q_rated
   - 推荐覆盖: Q_min ≤ 0.1 × Q_rated AND Q_max ≥ Q_rated
   - 未覆盖正常工况时抛出异常

4. **数据完整性验证**:
   - 缺失率 = (NULL值数量) / (总查询时间戳数)
   - 要求: 缺失率 < 5%
   - 推荐: 缺失率 < 2%
   - 超过阈值时发出警告

5. **数据准确性验证**:
   - 使用3σ规则识别异常值: |X - μ| > 3σ
   - 异常值率 = (异常值数量) / (总数据点数)
   - 要求: 异常值率 < 3%
   - 推荐: 异常值率 < 1%
   - 超过阈值时发出警告

**关键实现要求**:

1. **必须使用连接池**: 通过`app.adapters.db.pool.get_db_session()`获取session
2. **禁止硬编码**: 所有阈值(100点、1天等)必须从配置文件读取
3. **异常处理**: 数据不满足最小要求时抛出DataExtractionError,附带详细错误信息
4. **日志记录**: 记录数据质量指标(点数、时间跨度、覆盖范围等)到日志
5. **返回元数据**: 除返回DataFrame外,还需返回数据质量报告(total_points, time_span_days, Q_range等)

#### 5.4.3 预处理层独立模块补全 (必须实现)

**说明**: 以下是预处理层的独立模块,不是曲线内部的子模块

| 模块 | 文件路径 | 实现要求 | 职责 |
|-----|---------|:-------:|------|
| ScenarioDetector | preprocessing/scenario_detector.py | **必须实现** | 场景识别(9种场景) |
| DeviceTypeDetector | preprocessing/device_type_detector.py | **必须实现** | 设备类型检测 |
| SteadyStateDetector | preprocessing/steady_state_detector.py | **必须实现** | 稳态识别 |
| FrequencyNormalizer | preprocessing/frequency_normalizer.py | **必须实现** | 频率归一化(变频泵) |

#### 5.4.4 约束层模块补全 (必须实现)

**所有约束层模块必须完整实现**:

| 模块 | 文件路径 | 实现要求 | 依赖模块 |
|-----|---------|:-------:|----------|
| MonotonicityConstraint | constraints/monotonicity.py | **必须实现** | core, numpy |
| BoundaryConstraint | constraints/boundary.py | **必须实现** | core, numpy |
| PhysicsValidator | constraints/physics_validator.py | **必须实现** | core, MonotonicityConstraint, BoundaryConstraint |
| ConstraintCalculator | constraints/constraint_calculator.py | **必须实现** | core, curves |
| ConstraintLearner | constraints/constraint_learner.py | **必须实现** | core |
| ConstraintParameterManager | constraints/constraint_parameter_manager.py | **必须实现** | core |
| ConstraintOptimizer | constraints/constraint_optimizer.py | **必须实现** | scipy.optimize |
| ParameterLearner | params/parameter_learner.py | **必须实现** | core, pandas, numpy |

##### 5.4.4.1 ConstraintOptimizer约束优化器规范

**职责**: 在满足物理约束的前提下优化拟合结果

**核心功能**:

1. 约束优化(scipy.optimize)
2. 强制单调性
3. 强制边界条件
4. 多目标优化

**核心接口**:

```python
class ConstraintOptimizer:
    """约束优化器"""
    
    def optimize(
        self,
        initial_params: Dict[str, float],
        objective_func: Callable,
        constraints: List[Dict[str, Any]],
        bounds: Optional[Dict[str, Tuple[float, float]]] = None,
        method: str = 'SLSQP'
    ) -> Dict[str, Any]:
        """执行约束优化
        
        Args:
            initial_params: 初始参数
            objective_func: 目标函数(最小化)
            constraints: 约束条件列表
            bounds: 参数边界
            method: 优化方法 ('SLSQP', 'trust-constr', 'COBYLA')
            
        Returns:
            Dict: 包含optimized_params, success, iterations, final_cost
        """
    
    def enforce_monotonicity(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
        direction: str = 'decreasing'
    ) -> np.ndarray:
        """强制单调性
        
        Args:
            x_values: X轴值
            y_values: Y轴值
            direction: 单调方向 ('increasing', 'decreasing')
            
        Returns:
            np.ndarray: 调整后的Y值
        """
    
    def multi_objective_optimize(
        self,
        initial_params: Dict[str, float],
        objectives: List[Callable],
        weights: List[float],
        constraints: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """多目标优化
        
        Args:
            initial_params: 初始参数
            objectives: 目标函数列表
            weights: 权重列表
            constraints: 约束条件
            
        Returns:
            Dict: 优化结果
        """
```

**使用场景**:

在拟合结果违反物理约束时,使用约束优化器调整参数:

1. 单调性违反 → enforce_monotonicity()
2. 边界条件违反 → optimize()带边界约束
3. 需要平衡多个目标 → multi_objective_optimize()

**关键实现要求**:

1. 必须使用scipy.optimize,不重复造轮子
2. 优化方法必须支持SLSQP、trust-constr、COBYLA
3. 约束条件格式必须符合scipy.optimize规范
4. 优化失败时必须抛出ConstraintOptimizationError

##### 5.4.4.2 MonotonicityConstraint单调性约束规范

**职责**: 验证曲线的单调性约束,确保拟合结果符合流体力学基本规律

**核心功能**:

1. 验证Q-H曲线单调递减
2. 验证Q-P曲线单调递增
3. 验证Q-η曲线先增后减(单峰)
4. 计算单调性违反程度

**曲线单调性规则**:

| 曲线类型 | 单调性要求 | 物理含义 | 验证方法 |
|---------|-----------|---------|---------|
| **Q-H** | 单调递减 | 流量增加,扬程下降 | `_validate_decreasing()` |
| **Q-P** | 单调递增 | 流量增加,功率增加 | `_validate_increasing()` |
| **Q-η** | 单峰(先增后减) | 存在最高效率点 | `_validate_unimodal()` |

**核心接口**:

```python
class MonotonicityConstraint:
    """单调性约束验证器"""
    
    def __init__(self):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def validate(
        self,
        curve_type: str,
        x_values: np.ndarray,
        y_values: np.ndarray,
        tolerance: float = 0.01
    ) -> Dict[str, Any]:
        """验证单调性约束
        
        Args:
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            x_values: X轴值(流量)
            y_values: Y轴值(扬程/功率/效率)
            tolerance: 容差(允许的微小违反,相对于y值范围的比例)
            
        Returns:
            Dict: {
                'is_valid': bool,              # 是否通过验证
                'violation_ratio': float,      # 违反比例 (0-1)
                'violation_points': List[int], # 违反点的索引
                'peak_x': float,               # 峰值X坐标(仅qeta)
                'peak_y': float                # 峰值Y坐标(仅qeta)
            }
        """
    
    def _validate_decreasing(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
        tolerance: float
    ) -> Dict[str, Any]:
        """验证单调递减(Q-H曲线)
        
        算法:
        1. 计算相邻点差值: diff = np.diff(y_values)
        2. 计算容差阈值: threshold = tolerance × (y_max - y_min)
        3. 找出违反点: diff > threshold
        4. 计算违反比例: len(violation_points) / len(diff)
        """
    
    def _validate_increasing(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
        tolerance: float
    ) -> Dict[str, Any]:
        """验证单调递增(Q-P曲线)"""
    
    def _validate_unimodal(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
        tolerance: float
    ) -> Dict[str, Any]:
        """验证单峰(Q-η曲线)
        
        算法:
        1. 找到峰值位置: peak_idx = np.argmax(y_values)
        2. 峰值前应单调递增: _validate_increasing(y[:peak_idx])
        3. 峰值后应单调递减: _validate_decreasing(y[peak_idx:])
        4. 合并违反点并计算综合违反比例
        """
```

**使用场景**:

在拟合结果验证阶段,通过MonotonicityConstraint检查曲线是否符合物理规律:

```
验证流程:
1. 拟合完成后,获取拟合曲线的采样点(x_values, y_fitted)
2. 调用validate(curve_type, x_values, y_fitted)
3. 检查is_valid字段,如果为False:
   - 查看violation_ratio了解违反程度
   - 查看violation_points定位违反位置
   - 考虑使用ConstraintOptimizer强制修正
```

**关键实现要求**:

1. **必须使用numpy**: diff、argmax等操作必须使用numpy,不重复造轮子
2. **容差机制**: tolerance参数相对于y值范围,避免微小波动误判
3. **禁止硬编码**: tolerance默认值0.01应从配置文件读取
4. **详细日志**: 记录违反点位置、违反程度到日志
5. **返回完整结果**: 不仅返回布尔值,还要返回违反详情供后续分析

##### 5.4.4.3 BoundaryConstraint边界条件约束规范

**职责**: 验证曲线的边界条件约束,防止拟合结果超出设备设计范围

**核心功能**:

1. 验证零流量点(Q=0时的H₀、P₀、η₀)
2. 验证最大流量点
3. 验证值域范围
4. 验证物理边界

**边界条件定义**:

| 曲线类型 | 零流量点 | 最大流量点 | 值域范围 |
|---------|---------|-----------|---------|
| **Q-H** | H₀ ≈ 1.1~1.3 × H_rated | H → 0 | H ≥ 0 |
| **Q-P** | P₀ ≈ 0.3~0.5 × P_rated | P_max ≤ 1.2 × P_rated | P > 0 |
| **Q-η** | η₀ = 0 | η → 0 | 0 ≤ η ≤ 1 |

**核心接口**:

```python
class BoundaryConstraint:
    """边界约束验证器"""
    
    def __init__(self):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def validate(
        self,
        curve_type: str,
        fit_params: Dict[str, Any],
        device_params: Dict[str, float],
        tolerance: float = 0.05
    ) -> Dict[str, Any]:
        """验证边界约束
        
        Args:
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            fit_params: 拟合参数(包含coefficients)
            device_params: 设备参数(从device_rated_params表读取)
            tolerance: 容差(相对偏差)
            
        Returns:
            Dict: {
                'is_valid': bool,                   # 总体是否通过
                'boundary_checks': List[Dict],      # 每项检查的详情
                'violations': List[str]             # 违反项描述
            }
            
            其中boundary_checks每项包含:
            {
                'name': str,        # 检查项名称
                'passed': bool,     # 是否通过
                'actual': float,    # 实际值
                'expected': float,  # 期望值
                'min': float,       # 最小边界(可选)
                'max': float        # 最大边界(可选)
            }
        """
    
    def get_boundary_conditions(
        self,
        curve_type: str,
        device_params: Dict[str, float]
    ) -> Dict[str, Dict[str, float]]:
        """获取边界条件
        
        Args:
            curve_type: 曲线类型
            device_params: 设备参数
            
        Returns:
            Dict: 边界条件字典
            
        示例(QH曲线):
        {
            'zero_flow': {
                'name': '零流量扬程',
                'min': 1.1 * rated_head,
                'max': 1.3 * rated_head
            },
            'rated_point': {
                'name': '额定工况点',
                'Q': rated_flow,
                'H_min': 0.95 * rated_head,
                'H_max': 1.05 * rated_head
            },
            'value_range': {
                'name': '值域范围',
                'H_min': 0,
                'H_max': 1.5 * rated_head
            }
        }
        
        Raises:
            ValueError: device_params缺少必需的额定参数时抛出
        """
    
    def _validate_qh_boundary(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
        device_params: Dict[str, float],
        tolerance: float
    ) -> Tuple[bool, List[Dict]]:
        """验证Q-H曲线边界"""
    
    def _validate_qp_boundary(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
        device_params: Dict[str, float],
        tolerance: float
    ) -> Tuple[bool, List[Dict]]:
        """验证Q-P曲线边界"""
    
    def _validate_qeta_boundary(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
        tolerance: float
    ) -> Tuple[bool, List[Dict]]:
        """验证Q-η曲线边界"""
```

**边界验证流程**:

```
验证步骤:
1. 从device_rated_params表读取额定参数(rated_flow, rated_head等)
   → 缺失时抛出ValueError,禁止使用默认值
2. 根据curve_type调用get_boundary_conditions()获取边界条件
3. 使用拟合函数计算关键点(Q=0, Q=Q_rated等)
4. 逐项检查是否在边界范围内
5. 返回详细的验证结果(包含每项检查的实际值、期望值)
```

**关键实现要求**:

1. **必须读取额定参数**: device_params必须从device_rated_params表读取,不允许硬编码
2. **参数缺失检查**: 检查required_params,缺失时抛出ValueError并明确指出缺失项
3. **边界范围计算**: 边界范围必须基于额定参数动态计算,禁止硬编码边界值
4. **详细检查结果**: boundary_checks必须包含每项的actual、expected、min、max
5. **容差机制**: tolerance应用于所有边界检查,默认5%
6. **禁止降级**: 额定参数缺失时直接抛出异常,不使用默认值或降级策略

##### 5.4.4.4 PhysicsValidator物理一致性验证规范

**职责**: 综合验证拟合结果的物理合理性,组合多种约束检查

**核心功能**:

1. 组合多种约束验证(单调性+边界)
2. 计算综合物理得分(0-100分)
3. 生成验证报告
4. 提供修复建议
5. 能量守恒验证(可选)
6. 效率范围验证

**评分规则**:

- 单调性权重: 40%
- 边界条件权重: 60%
- 物理得分 = 0.4 × 单调性得分 + 0.6 × 边界得分

**核心接口**:

```python
class PhysicsValidator:
    """物理验证器(组合多种约束)"""
    
    def __init__(self):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._monotonicity = MonotonicityConstraint()
        self._boundary = BoundaryConstraint()
    
    def validate(
        self,
        device_id: int,
        curve_type: str,
        fit_result: 'FitResult',
        device_params: Dict[str, float]
    ) -> 'ValidationResult':
        """执行完整物理验证
        
        Args:
            device_id: 设备ID
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            fit_result: 拟合结果(包含x_values, y_fitted, coefficients)
            device_params: 设备参数(从device_rated_params表读取)
            
        Returns:
            ValidationResult: 验证结果,包含:
                - overall_passed: 总体是否通过
                - monotonicity_passed: 单调性是否通过
                - boundary_passed: 边界是否通过
                - physics_score: 物理得分(0-100)
                - monotonicity_details: 单调性验证详情
                - boundary_details: 边界验证详情
                - suggestions: 修复建议列表
        """
    
    def calculate_physics_score(
        self,
        mono_result: Dict[str, Any],
        bound_result: Dict[str, Any]
    ) -> float:
        """计算物理得分(0-100)
        
        Args:
            mono_result: 单调性验证结果
            bound_result: 边界验证结果
            
        Returns:
            float: 物理得分 = 0.4 × 单调性得分 + 0.6 × 边界得分
            
        计算规则:
        - 单调性得分 = 100 × (1 - violation_ratio)
        - 边界得分 = 100 × (通过检查项数 / 总检查项数)
        """
    
    def suggest_fixes(
        self,
        validation_result: 'ValidationResult'
    ) -> List[str]:
        """提供修复建议
        
        Args:
            validation_result: 验证结果
            
        Returns:
            List[str]: 修复建议列表,例如:
                - "单调性违反: 考虑使用带单调性约束的拟合方法"
                - "边界条件违反: 检查设备额定参数是否正确"
                - "检查数据是否存在异常点或噪声"
                - "考虑调整拟合参数或使用物理约束拟合"
        """
    
    def check_efficiency_range(
        self,
        eta_values: np.ndarray
    ) -> Dict[str, Any]:
        """检查效率范围(0-100%)
        
        Returns:
            Dict: {
                'is_valid': bool,
                'min_eta': float,
                'max_eta': float,
                'out_of_range_count': int
            }
        """
    
    def check_energy_conservation(
        self,
        Q: np.ndarray,
        H: np.ndarray,
        P: np.ndarray,
        eta: np.ndarray
    ) -> Dict[str, Any]:
        """检查能量守恒 P = ρ × g × Q × H / η
        
        Returns:
            Dict: {
                'is_valid': bool,
                'mean_deviation': float,  # 平均偏差(%)
                'max_deviation': float    # 最大偏差(%)
            }
        """
```

**验证流程**:

```
物理验证执行顺序:
1. 单调性验证
   → _monotonicity.validate(curve_type, x_values, y_fitted)
   → 记录违反点和违反比例

2. 边界条件验证
   → _boundary.validate(curve_type, fit_params, device_params)
   → 检查零流量点、额定点、值域范围

3. 计算综合得分
   → calculate_physics_score(mono_result, bound_result)
   → 应用40%/60%权重计算

4. 生成修复建议(如验证失败)
   → suggest_fixes(validation_result)
   → 根据具体违反类型提供针对性建议

5. 返回ValidationResult
   → 包含所有验证详情和建议
```

**关键实现要求**:

1. **组合模式**: 必须组合使用MonotonicityConstraint和BoundaryConstraint,不重复实现验证逻辑
2. **权重固定**: 物理得分计算必须使用40%/60%权重,不允许调整
3. **详细日志**: 记录每项验证的耗时、结果到日志
4. **不抛异常**: 验证失败时不抛出异常,返回ValidationResult.overall_passed=False
5. **完整建议**: suggest_fixes()必须根据具体违反类型提供可操作的修复建议
6. **依赖注入**: MonotonicityConstraint和BoundaryConstraint通过__init__初始化,支持测试时mock



##### 5.4.4.5 ConstraintCalculator约束计算器规范

**职责**: 计算每条曲线的物理约束参数

**核心功能**:

1. 根据数据和设备参数计算约束参数
2. 支持QH/QP/QEta三种曲线类型
3. 自动识别约束范围
4. 提供约束参数验证

**约束参数定义**:

| 曲线类型 | 约束参数 | 说明 |
|---------|---------|------|
| **QH** | H0, Q_max, K, H_rated, Q_rated, monotonicity, convexity | 零流量扬程、最大流量、曲线系数、额定工况、单调性、凸性 |
| **QP** | P0, P_max, P_rated, Q_rated, monotonicity, energy_balance | 零流量功率、最大功率、额定功率、额定流量、单调性、能量守恒 |
| **QEta** | Q_BEP, eta_max, Q_rated, eta_rated, unimodal, efficiency_range | 最佳效率点流量、最大效率、额定流量、额定效率、单峰性、效率范围 |

**核心接口**:

```python
class ConstraintCalculator:
    """约束计算器 - 计算每条曲线的物理约束参数"""
    
    def __init__(self):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def calculate(
        self,
        curve_type: str,
        data: pd.DataFrame,
        device_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算约束参数
        
        Args:
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            data: 原始数据,包含流量Q和对应的Y值(H/P/η)
            device_params: 设备参数(从device_rated_params表读取)
            
        Returns:
            Dict: 约束参数字典,根据曲线类型返回不同的参数
            
        计算逻辑:
        - QH曲线: 计算H0(零流量扬程)、Q_max(最大流量)、曲线系数K等
        - QP曲线: 计算P0(零流量功率)、P_max(最大功率)、能量守恒参数等
        - QEta曲线: 计算Q_BEP(最佳效率点流量)、eta_max(最大效率)等
        
        Raises:
            ValueError: curve_type不支持或device_params缺少必需参数时抛出
        """
    
    def calculate_qh_constraints(
        self,
        data: pd.DataFrame,
        device_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算Q-H曲线约束参数
        
        Returns:
            Dict: {
                'H0': float,              # 零流量扬程估计值
                'H0_min': float,          # 零流量扬程下限 (1.1 × rated_head)
                'H0_max': float,          # 零流量扬程上限 (1.3 × rated_head)
                'Q_max': float,           # 最大流量 (1.2 × rated_flow)
                'K': float,               # 曲线系数估计值
                'H_rated': float,         # 额定扬程
                'Q_rated': float,         # 额定流量
                'monotonicity': str,      # 'decreasing'
                'convexity': str          # 'concave_down'
            }
        """
    
    def calculate_qp_constraints(
        self,
        data: pd.DataFrame,
        device_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算Q-P曲线约束参数
        
        Returns:
            Dict: {
                'P0': float,              # 零流量功率估计值
                'P0_min': float,          # 零流量功率下限 (0.3 × rated_power)
                'P0_max': float,          # 零流量功率上限 (0.5 × rated_power)
                'P_max': float,           # 最大功率 (1.2 × rated_power)
                'P_rated': float,         # 额定功率
                'Q_rated': float,         # 额定流量
                'monotonicity': str,      # 'increasing'
                'energy_balance': bool    # 能量守恒检查开关
            }
        """
    
    def calculate_qeta_constraints(
        self,
        data: pd.DataFrame,
        device_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算Q-η曲线约束参数
        
        Returns:
            Dict: {
                'Q_BEP': float,           # 最佳效率点流量
                'eta_max': float,         # 最大效率
                'Q_rated': float,         # 额定流量
                'eta_rated': float,       # 额定效率
                'Q_BEP_min': float,       # BEP流量下限 (0.6 × rated_flow)
                'Q_BEP_max': float,       # BEP流量上限 (1.2 × rated_flow)
                'unimodal': bool,         # 单峰性检查开关
                'efficiency_range': Tuple[float, float]  # 效率范围 (0, 1.0)
            }
        """
    
    def validate_constraints(
        self,
        constraints: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """验证约束参数的合理性
        
        Args:
            constraints: 计算出的约束参数
            
        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
```

**约束计算原理**:

```
QH曲线约束计算:
1. H0估计: 从低流量区域(Q < 0.2×Q_rated)的数据点估计零流量扬程
2. Q_max确定: 基于额定流量的1.2倍,确保覆盖运行范围
3. K系数估计: 通过二次拟合初步估计曲线系数 K ≈ -H0/(Q_rated^2)
4. 单调性: 强制要求Q-H曲线单调递减
5. 凸性: 要求曲线下凸(d²H/dQ² > 0)

QP曲线约束计算:
1. P0估计: 从低流量区域估计零流量功率,应在0.3~0.5×P_rated范围
2. P_max确定: 基于额定功率的1.2倍
3. 能量守恒: P ≈ ρgQH/η (可选验证)
4. 单调性: 强制要求Q-P曲线单调递增

QEta曲线约束计算:
1. Q_BEP识别: 从数据中找到效率最大值对应的流量
2. eta_max提取: 数据中的最大效率值
3. BEP范围验证: 检查Q_BEP是否在0.6~1.2×Q_rated范围内
4. 单峰性: 强制要求效率曲线单峰(先增后减)
5. 效率范围: 强制要求0 ≤ η ≤ 1.0
```

**关键实现要求**:

1. **数据来源**: data必须是经过预处理的clean_data,包含有效的Q和Y列
2. **参数来源**: device_params必须从device_rated_params表读取,禁止硬编码
3. **参数缺失处理**: 必需的device_params缺失时抛出ValueError,不使用默认值
4. **估计算法**: H0/P0/Q_BEP等估计值应基于数据统计,不能随意假设
5. **约束范围计算**: 所有min/max范围必须基于额定参数动态计算,不能硬编码系数
6. **验证逻辑**: validate_constraints()必须检查约束参数的物理合理性

##### 5.4.4.6 ConstraintLearner约束学习器规范

**职责**: 从历史成功拟合中学习约束参数,实现约束的自适应优化

**核心功能**:

1. 从历史拟合结果中学习约束参数范围
2. 分析约束违反趋势
3. 提供约束参数优化建议
4. 计算约束参数的置信度

**核心接口**:

```python
class ConstraintLearner:
    """约束学习器 - 从历史数据学习约束参数"""
    
    def __init__(self, result_storage: 'ResultStorage'):
        """初始化
        
        Args:
            result_storage: 结果存储器,用于读取历史拟合结果
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._result_storage = result_storage
    
    def learn_from_history(
        self,
        device_id: int,
        curve_type: str,
        min_samples: int = 20
    ) -> Dict[str, Any]:
        """从历史成功拟合中学习约束参数
        
        Args:
            device_id: 设备ID
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            min_samples: 最小样本数(默认20次成功拟合)
            
        Returns:
            Dict: 学习到的约束参数,包含:
            {
                'H0_range': {'min': float, 'max': float},  # 零流量扬程范围(QH)
                'K_range': {'min': float, 'max': float},   # 曲线系数范围(QH)
                'P0_range': {'min': float, 'max': float},  # 零流量功率范围(QP)
                'Q_BEP_range': {'min': float, 'max': float},  # BEP流量范围(QEta)
                'tolerance': float,                        # 推荐容差
                'sample_count': int,                       # 样本数量
                'confidence': float                        # 置信度(0-1)
            }
            
        学习逻辑:
        1. 从curve_fit_params表读取历史成功拟合的参数
        2. 筛选条件: status='success' AND physics_score >= 80
        3. 统计参数分布:收集H0、K、P0、Q_BEP等关键参数的分布特征
        4. 计算推荐范围: min = P10(第10百分位数), max = P90(第90百分位数)
        5. 样本数 < min_samples时使用默认约束参数(从配置读取)
        
        Raises:
            ValueError: curve_type不支持时抛出
        """
    
    def analyze_violations(
        self,
        device_id: int,
        curve_type: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """分析约束违反情况
        
        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            start_time: 开始时间(可选)
            end_time: 结束时间(可选)
            
        Returns:
            Dict: {
                'total_validations': int,      # 总验证次数
                'violation_count': int,        # 违反次数
                'violation_rate': float,       # 违反率
                'common_violations': List[str], # 常见违反类型
                'trend': str                   # 趋势 ('improving', 'worsening', 'stable')
            }
        """
    
    def suggest_improvements(
        self,
        device_id: int,
        curve_type: str
    ) -> List[str]:
        """提供约束参数改进建议
        
        Returns:
            List[str]: 建议列表,例如:
                - "H0范围过窄,建议扩大至[52.0, 58.0]"
                - "单调性容差过严,建议从0.01放宽至0.02"
                - "边界条件检查过于宽松,建议收紧P_max上限"
        """
    
    def calculate_confidence(
        self,
        sample_count: int,
        time_span_days: float,
        violation_rate: float
    ) -> float:
        """计算学习结果的置信度
        
        Args:
            sample_count: 样本数量
            time_span_days: 时间跨度(天)
            violation_rate: 约束违反率
            
        Returns:
            float: 置信度(0-1)
            
        计算公式:
        confidence = w1 × sample_score + w2 × time_score + w3 × quality_score
        
        其中:
        - sample_score = min(sample_count / 50, 1.0)  # 50次样本为满分
        - time_score = min(time_span_days / 90, 1.0)  # 90天为满分
        - quality_score = 1.0 - violation_rate         # 违反率越低质量越高
        - w1=0.4, w2=0.3, w3=0.3
        """
```

**学习方法**:

| 方法 | 适用场景 | 算法描述 | 优缺点 |
|------|---------|---------|-------|
| **percentile** | 样本数≥20 | 使用P10-P90分位数确定约束范围 | 鲁棒性好,适合大样本 |
| **3sigma** | 样本数≥50且正态分布 | μ±3σ确定约束范围 | 适合正态分布,对异常值敏感 |
| **config_based** | 样本数<20 | 使用配置文件中的默认约束 | 保守但可靠,适合新设备 |

**使用场景**:

```
约束学习触发时机:
1. 新设备初次拟合后(积累10次以上成功拟合后)
   → 学习初始约束参数范围
   
2. 定期约束校准(每月一次)
   → 根据最新数据更新约束参数,适应设备老化
   
3. 约束频繁违反时(违反率>30%)
   → 分析违反原因,调整约束参数
   
4. 拟合质量下降时(physics_score < 70)
   → 检查约束参数是否需要优化
```

**关键实现要求**:

1. **数据来源**: 必须从curve_fit_params表读取历史参数,结合curve_fit_results表的验证结果
2. **筛选条件**: 只学习成功拟合(status='success')且物理得分高(physics_score≥80)的样本
3. **最小样本数**: min_samples默认20,必须从配置读取,样本不足时使用默认约束
4. **分位数计算**: 使用numpy.percentile计算P10/P90,不能手工计算
5. **置信度评估**: 必须综合考虑样本数、时间跨度、违反率三个维度
6. **禁止默认值**: 无历史数据时使用配置中的约束参数,不硬编码默认值
7. **趋势分析**: analyze_violations()必须比较不同时间段的违反率判断趋势

##### 5.4.4.7 ConstraintParameterManager约束参数管理器规范

**职责**: 统一管理约束参数的加载、缓存、更新和学习

**核心功能**:

1. 加载约束参数(优先级: 学习值 > 配置值 > 计算值)
2. 约束参数缓存管理
3. 触发约束学习和更新
4. 提供约束参数查询接口

**参数优先级策略**:

```
约束参数获取优先级(从高到低):
1. 学习值(Learned): 从历史拟合中学习的约束参数(置信度≥0.7)
2. 配置值(Configured): 从配置文件/数据库读取的约束参数
3. 计算值(Calculated): 基于当前数据和设备参数实时计算的约束

选择逻辑:
if has_learned_constraints AND confidence >= 0.7:
    use learned_constraints
elif has_configured_constraints:
    use configured_constraints
else:
    use calculated_constraints
```

**核心接口**:

```python
class ConstraintParameterManager:
    """约束参数管理器 - 统一管理约束参数"""
    
    def __init__(
        self,
        constraint_calculator: 'ConstraintCalculator',
        constraint_learner: 'ConstraintLearner',
        constraint_cache: 'ConstraintCache'
    ):
        """初始化
        
        Args:
            constraint_calculator: 约束计算器
            constraint_learner: 约束学习器
            constraint_cache: 约束缓存
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._calculator = constraint_calculator
        self._learner = constraint_learner
        self._cache = constraint_cache
    
    def get_constraints(
        self,
        device_id: int,
        curve_type: str,
        data: pd.DataFrame,
        device_params: Dict[str, Any],
        use_cache: bool = True,
        force_learn: bool = False
    ) -> Dict[str, Any]:
        """获取约束参数(应用优先级策略)
        
        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            data: 原始数据
            device_params: 设备参数
            use_cache: 是否使用缓存
            force_learn: 是否强制触发学习
            
        Returns:
            Dict: 约束参数字典,包含source字段标识参数来源
            {
                'source': str,  # 'learned' | 'configured' | 'calculated'
                'confidence': float,  # 仅learned来源有此字段
                ...其他约束参数
            }
            
        执行逻辑:
        1. 检查缓存: 如果use_cache=True,先从缓存获取
        2. 尝试学习值: 调用learner.learn_from_history(),检查置信度
        3. 回退配置值: 如果学习失败或置信度低,从配置读取
        4. 最后计算值: 如果配置也没有,使用calculator实时计算
        5. 更新缓存: 将获取的约束参数存入缓存
        """
    
    def update_constraints(
        self,
        device_id: int,
        curve_type: str,
        constraints: Dict[str, Any],
        source: str = 'manual'
    ) -> bool:
        """更新约束参数
        
        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            constraints: 新的约束参数
            source: 来源 ('manual', 'learned', 'optimized')
            
        Returns:
            bool: 是否成功
        """
    
    def trigger_learning(
        self,
        device_id: int,
        curve_type: str
    ) -> Dict[str, Any]:
        """触发约束学习
        
        Returns:
            Dict: 学习结果,包含learned_constraints和confidence
        """
    
    def invalidate_cache(
        self,
        device_id: Optional[int] = None
    ) -> int:
        """使缓存失效
        
        Args:
            device_id: 设备ID(可选,不指定则清除所有缓存)
            
        Returns:
            int: 清除的缓存数量
        """
    
    def get_constraint_source(
        self,
        device_id: int,
        curve_type: str
    ) -> str:
        """查询约束参数来源
        
        Returns:
            str: 'learned' | 'configured' | 'calculated' | 'unknown'
        """
    
    def analyze_constraint_quality(
        self,
        device_id: int,
        curve_type: str
    ) -> Dict[str, Any]:
        """分析约束参数质量
        
        Returns:
            Dict: {
                'source': str,
                'confidence': float,
                'violation_rate': float,
                'last_updated': datetime,
                'recommendations': List[str]
            }
        """
```

**缓存失效策略**:

| 触发条件 | 失效范围 | 说明 |
|---------|---------|------|
| 设备额定参数更新 | 该设备所有曲线 | device_params变更时清除缓存 |
| 约束学习完成 | 该设备该曲线 | 学习到新约束时更新缓存 |
| 手动更新约束 | 该设备该曲线 | 管理员手动修改约束时清除 |
| 定期清理 | 所有设备 | 每天凌晨清理所有缓存(可选) |

**关键实现要求**:

1. **依赖注入**: ConstraintCalculator、ConstraintLearner、ConstraintCache必须通过构造函数注入
2. **优先级策略**: 严格按照"学习值 > 配置值 > 计算值"优先级获取约束
3. **置信度阈值**: 学习值的置信度阈值0.7必须从配置读取,不硬编码
4. **缓存管理**: 必须使用ConstraintCache进行缓存,不自行实现缓存逻辑
5. **来源追踪**: 返回的约束参数必须包含source字段,标识参数来源
6. **质量分析**: analyze_constraint_quality()必须结合learner的分析结果
7. **日志记录**: 每次获取约束参数都要记录来源、置信度到日志
8. **禁止硬编码**: 所有默认值、阈值都必须从配置文件或数据库读取

##### 5.4.4.8 ParameterLearner参数学习器规范

**职责**: 从历史成功拟合中学习最优参数,实现参数自适应优化

**核心功能**:

1. 从历史数据学习设备参数
2. 从历史拟合中学习约束参数
3. 计算参数置信度
4. 参数范围推荐

**核心接口**:

```python
class ParameterLearner:
    """参数学习器 - 从历史数据自动学习设备参数"""
    
    def __init__(self, parameter_manager: 'ParameterManager'):
        """初始化
        
        Args:
            parameter_manager: 参数管理器,用于读取和更新参数
        """
        self._param_manager = parameter_manager
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def learn_from_history(
        self,
        device_id: int,
        start_time: datetime,
        end_time: datetime,
        min_data_points: int = 1000
    ) -> Dict[str, Any]:
        """从历史数据学习设备参数
        
        Args:
            device_id: 设备ID
            start_time: 开始时间
            end_time: 结束时间
            min_data_points: 最小数据点数(默认1000)
            
        Returns:
            Dict: {
                'learned_params': {
                    'rated_flow': float,
                    'rated_head': float,
                    'rated_power': float,
                    'rated_efficiency': float
                },
                'confidence': {
                    'rated_flow': float,      # 0-1,置信度
                    'rated_head': float,
                    'rated_power': float,
                    'rated_efficiency': float
                },
                'sample_count': int,           # 样本数量
                'time_span_days': float,       # 时间跨度(天)
                'learning_method': str         # 学习方法(3sigma/quantile/rated_based)
            }
            
        学习逻辑:
        1. 从fact_measurements表提取[start_time, end_time]内的历史数据
        2. 过滤异常值(3σ原则或IQR)
        3. 根据数据分布选择学习方法:
           - rated_based: 已有额定参数时,基于额定值验证和微调
           - 3sigma: 数据呈正态分布时,使用均值±3σ
           - quantile: 数据非正态分布时,使用分位数方法
        4. 计算置信度: 基于样本数量、时间跨度、数据质量
        5. 数据点数 < min_data_points 时抛出InsufficientDataError
        
        Raises:
            InsufficientDataError: 数据点数不足时抛出
            DataExtractionError: 数据提取失败时抛出
        """
    
    def learn_constraints(
        self,
        device_id: int,
        curve_type: str,
        min_samples: int = 20
    ) -> Dict[str, Any]:
        """从历史成功拟合中学习约束参数
        
        Args:
            device_id: 设备ID
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            min_samples: 最小样本数(默认20次成功拟合)
            
        Returns:
            Dict: 约束参数,例如:
            {
                'H0_range': {'min': float, 'max': float},  # 零流量扬程范围
                'K_range': {'min': float, 'max': float},   # 二次项系数范围
                'tolerance': float,                        # 推荐容差
                'boundary_margins': {                      # 边界裕量
                    'H0_margin': float,
                    'rated_margin': float
                },
                'sample_count': int,                       # 样本数量
                'confidence': float                        # 置信度(0-1)
            }
            
        学习逻辑:
        1. 从curve_fit_params表读取历史成功拟合的参数
        2. 筛选条件: status='success' AND physics_score >= 80
        3. 统计参数分布:
           - H0: 零流量扬程的分布范围
           - K: 二次项系数的分布范围
           - 其他关键参数的统计特性
        4. 计算推荐范围:
           - min = P10(第10百分位数)
           - max = P90(第90百分位数)
        5. 样本数 < min_samples 时使用默认约束参数(从配置读取)
        
        Raises:
            ValueError: curve_type不支持时抛出
        """
    
    def calculate_confidence(
        self,
        sample_count: int,
        time_span_days: float,
        data_quality: Dict[str, float]
    ) -> float:
        """计算参数学习的置信度
        
        Args:
            sample_count: 样本数量
            time_span_days: 时间跨度(天)
            data_quality: 数据质量指标
            
        Returns:
            float: 置信度(0-1)
            
        计算公式:
        confidence = w1 × sample_score + w2 × time_score + w3 × quality_score
        
        其中:
        - sample_score = min(sample_count / 5000, 1.0)
        - time_score = min(time_span_days / 30, 1.0)
        - quality_score = data_quality['completeness'] × data_quality['accuracy']
        - w1=0.4, w2=0.3, w3=0.3
        """
    
    def recommend_parameter_ranges(
        self,
        device_id: int,
        curve_type: str,
        learned_params: Dict[str, float]
    ) -> Dict[str, Tuple[float, float]]:
        """推荐参数范围(用于参数优化)
        
        Returns:
            Dict: {
                'a0': (min, max),  # 常数项范围
                'a1': (min, max),  # 一次项范围
                'a2': (min, max)   # 二次项范围
            }
        """
```

**学习方法说明**:

| 方法 | 适用场景 | 算法描述 | 优缺点 |
|------|---------|---------|-------|
| **rated_based** | 已有额定参数 | 基于额定值±10%范围验证和微调 | 准确度高,依赖额定参数准确性 |
| **3sigma** | 正态分布数据 | μ±3σ确定范围,μ为参数估计值 | 适合大样本,对异常值敏感 |
| **quantile** | 非正态分布 | P10-P90分位数确定范围 | 鲁棒性好,适合小样本 |

**使用场景**:

```
参数学习触发时机:
1. 新设备初次拟合
   → 无额定参数时,从历史数据学习
   
2. 拟合失败后的参数优化
   → 学习成功拟合的参数范围,缩小搜索空间
   
3. 定期参数校准(每月一次)
   → 根据最新数据更新参数,适应设备老化
   
4. 约束参数自适应
   → 从历史拟合中学习合理的约束范围
```

**关键实现要求**:

1. **数据来源**: 历史数据必须从fact_measurements表读取,约束参数从curve_fit_params表读取
2. **最小样本数**: min_data_points默认1000,min_samples默认20,必须从配置文件读取
3. **异常值过滤**: 必须使用3σ或IQR方法过滤异常值,防止学习结果偏差
4. **置信度计算**: 必须考虑样本数、时间跨度、数据质量三个维度
5. **禁止默认值**: 数据不足时抛出异常,不使用硬编码的默认参数
6. **学习结果验证**: 学习到的参数必须与物理常识一致,异常时记录警告
7. **缓存学习结果**: 学习结果应缓存,避免重复计算

#### 5.4.5 曲线层模块补全 (必须实现)

**用户提醒**: 每个曲线需要提取的数据不一样,数据特性、数据特征都要符合要求,曲线需要实现的功能不要遗漏

**所有曲线类必须完整实现**:

| 曲线类 | 文件路径 | 实现要求 | 必需指标 | 物理特性 |
|-------|---------|:-------:|---------|----------|
| BaseCurve | curves/base_curve.py | **必须实现** | - | 曲线基类,定义模板方法 |
| QHCurve | curves/qh_curve.py | **必须实现** | pump_flow_rate, pump_head | 单调递减、下凸 |
| QPCurve | curves/qp_curve.py | **必须实现** | pump_flow_rate, pump_active_power | 单调递增、上凸 |
| QEtaCurve | curves/qeta_curve.py | **必须实现** | pump_flow_rate, pump_efficiency | 单峰、0≤η≤1 |

#### 5.4.6 输出层模块补全 (必须实现)

**用户要求**: 特性曲线拟合结果必须按照要求进行保存、输出、生成图片、导出曲线,是拟合系统的重要功能

##### 5.4.6.1 ResultStorage结果存储规范

**职责**: 负责拟合结果的三表分离存储、版本管理、曲线特征点生成

**三表分离存储逻辑**:

| 表名 | 用途 | 关键字段 | 存储内容 |
|-----|------|---------|----------|
| curve_fit_results | 主表 | id, device_id, curve_type, version, method_name, status, curve_points | 拟合元数据、曲线特征点(JSONB) |
| curve_fit_params | 参数表 | result_id, param_category, param_key, param_value | 拟合系数、归一化参数 |
| curve_fit_metrics | 指标表 | result_id, metric_name, metric_value | R²、RMSE、MAE、MAPE等 |

**curve_points曲线特征点生成规范**:

必须在ResultStorage.save()方法中调用CurvePointGenerator生成曲线特征点,存入curve_fit_results.curve_points字段

数据结构(JSONB格式):

```json
{
  "sample_count": 20,
  "q_values": [0.0, 26.25, 52.5, ..., 525.0],
  "y_values": [55.2, 54.1, 51.8, ..., 22.3],
  "sampling_method": "uniform",
  "q_range": {"min": 0.0, "max": 525.0}
}
```

采样点数规范:

| 级别 | 采样点数 | 适用场景 | 存储大小估算 |
|-----|---------|---------|-------------|
| 默认 | 20个 | 常规曲线展示 | ~500字节 |
| 高精度 | 50个 | 详细分析 | ~1.2KB |
| 超高精度 | 100个 | 科研级精度 | ~2.5KB |

**版本管理规范**:

版本号格式: `YYYYMMDD_HHMMSS`

示例: `20250128_143052`

版本状态枚举:

| 状态 | 说明 | 操作 |
|-----|------|------|
| active | 当前活跃版本 | 默认查询、预测使用 |
| archived | 已归档版本 | 仅供历史对比 |
| deprecated | 已废弃版本 | 软删除,不展示 |

版本更新规则:

1. 新版本保存时,自动将device_id + curve_type的前一个active版本修改为archived
2. 支持版本回滚:将指定archived版本修改为active,当前active修改为archived
3. 版本删除:仅修改status为deprecated,不物理删除

**事务保护**:

三表写入必须在同一事务中完成,确保原子性:

```python
# 事务写入伪代码
with db_session.begin():
    # 1. 插入curve_fit_results主记录
    result_id = insert_fit_result(...)
    
    # 2. 批量插入curve_fit_params
    insert_params(result_id, params_dict)
    
    # 3. 批量插入curve_fit_metrics
    insert_metrics(result_id, metrics_dict)
    
    # 任一步骤失败,自动回滚全部
```

**关键实现要求**:

1. 必须使用项目连接池: `app.adapters.db.pool.get_db_session()`
2. 必须调用CurvePointGenerator生成曲线特征点
3. 版本号生成: `datetime.now().strftime('%Y%m%d_%H%M%S')`
4. 禁止硬编码采样点数,必须从配置读取
5. 写入失败时抛出ResultStorageError(异常码CF011)

##### 5.4.6.2 MethodSelector拟合方法选择规范

**职责**: 智能选择最适合的拟合方法

**核心功能**:

1. 根据数据特征推荐方法
2. 根据历史表现排序方法
3. 方法过滤和排序
4. 数据质量分析

**推荐规则来源**(禁止硬编码):

从数据库method_params JSONB字段读取,必须包含:

```json
{
  "qh": {
    "default": ["polynomial_3", "pump_characteristic"],
    "high_quality": ["polynomial_4", "gaussian"],
    "sparse_data": ["polynomial_2", "linear"],
    "noisy_data": ["savitzky_golay", "polynomial_3"]
  },
  "qp": {...},
  "qeta": {...}
}
```

**核心接口**:

```python
class MethodSelector:
    """方法选择器"""
    
    def __init__(
        self,
        method_registry: 'MethodRegistry',
        recommendations: Dict[str, Dict[str, List[str]]]
    ):
        """初始化
        
        Args:
            method_registry: 方法注册表
            recommendations: 从数据库读取的推荐规则
            
        Raises:
            ValueError: 推荐规则缺失必需的曲线类型或数据质量类型
        """
    
    def select(
        self,
        curve_type: str,
        data: pd.DataFrame,
        device_params: Optional[Dict[str, float]] = None,
        preferred_methods: Optional[List[str]] = None
    ) -> List[str]:
        """选择推荐的拟合方法
        
        Returns:
            List[str]: 推荐的方法列表(按优先级排序)
        """
    
    def analyze_data_quality(
        self,
        data: pd.DataFrame
    ) -> str:
        """分析数据质量
        
        Returns:
            str: 'high_quality' | 'sparse_data' | 'noisy_data' | 'default'
        """
    
    def rank_methods_by_history(
        self,
        device_id: int,
        curve_type: str,
        candidate_methods: List[str]
    ) -> List[str]:
        """根据历史表现排序方法
        
        Returns:
            List[str]: 排序后的方法列表
        """
```

**关键实现要求**:

1. 推荐规则必须从数据库读取,缺失时抛出ValueError
2. 必须验证recommendations包含所有必需的曲线类型(qh/qp/qeta)
3. 必须验证每个曲线类型包含所有数据质量类型(default/high_quality/sparse_data/noisy_data)
4. 历史表现排序需查询curve_fit_results表的R²和RMSE指标
5. 禁止使用任何硬编码的默认推荐方法

##### 5.4.6.3 CurvePointGenerator曲线特征点生成规范

**职责**: 在拟合曲线的流量范围内均匀采样,生成用于存储和可视化的特征点

**采样点数规范**:

从配置文件读取: `curve_point_count`

默认值: 20个

**采样算法**:

均匀采样 (Uniform Sampling):

```python
# 伪代码
q_min, q_max = data['Q'].min(), data['Q'].max()
q_samples = np.linspace(q_min, q_max, num=curve_point_count)
y_samples = predict_func(q_samples)
```

**输出数据结构**:

返回字典,用于存入curve_fit_results.curve_points字段(JSONB):

```python
{
    "sample_count": 20,
    "q_values": [float],  # 采样流量点列表
    "y_values": [float],  # 对应的预测值列表
    "sampling_method": "uniform",
    "q_range": {"min": float, "max": float}
}
```

**关键实现要求**:

1. 采样点数必须从配置读取,禁止硬编码
2. 必须覆盖数据的完整流量范围 [Q_min, Q_max]
3. 使用numpy.linspace()确保均匀分布
4. 返回的q_values和y_values必须是Python原生list,不能是numpy数组(JSON序列化兼容)

##### 5.4.6.3 HighResPlotter高分辨率可视化规范

**用户要求**: 生成8K高清拟合曲线图,全中文标签,5种图片类型

**8K分辨率配置**:

| 配置项 | 规格 | 说明 |
|-------|------|------|
| 分辨率 | 7680 × 4320 | 8K UHD标准 |
| DPI | 300 | 打印级精度 |
| 图像尺寸 | 25.6 × 14.4 英寸 | DPI=300时生成8K |
| 格式 | PNG | 无损压缩 |
| 压缩级别 | 6 | 平衡文件大小和速度 |
| matplotlib后端 | Agg | 非交互式,节省内存 |

**中文标签映射**:

必须从配置文件或常量定义读取,禁止硬编码:

| 曲线类型 | 标题 | X轴标签 | Y轴标签 | 单位 |
|---------|------|---------|---------|------|
| qh | 流量-扬程 | 流量 Q (m³/h) | 扬程 H (m) | m |
| qp | 流量-功率 | 流量 Q (m³/h) | 功率 P (kW) | kW |
| qeta | 流量-效率 | 流量 Q (m³/h) | 效率 η (%) | % |

**中文字体配置**:

优先使用SimHei(黑体),回退方案: Microsoft YaHei

```python
# matplotlib配置
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
```

**5种图片类型规范**:

| 图片类型 | 文件后缀 | 优先级 | 内容说明 |
|---------|---------|:------:|----------|
| 主曲线图 | _curve.png | P0(必须) | 原始数据散点 + 拟合曲线 + 95%置信带 + 统计信息框 |
| 残差分析图 | _residuals.png | P1(推荐) | 4子图: 残差vs预测、残差vs流量、直方图、QQ图 |
| 置信区间图 | _confidence.png | P2(可选) | 拟合曲线 + 95%/99%置信区间 + 预测区间 |
| 敏感性分析图 | _sensitivity.png | P2(可选) | 各参数变化±10%对曲线的影响 |
| 版本对比图 | _comparison.png | P2(可选) | 当前版本与历史版本曲线对比 |

**图片命名规范**:

格式: `{curve_type_cn}_{method_name}_{version}_{type}.png`

示例:

```
qh_流量扬程_polynomial_3_20250128_143052_curve.png
qh_流量扬程_polynomial_3_20250128_143052_residuals.png
```

命名规则:

1. curve_type_cn: 使用中文名称(流量扬程、流量功率、流量效率)
2. method_name: 拟合方法名称(如polynomial_3)
3. version: 版本号(YYYYMMDD_HHMMSS)
4. type: 图片类型(curve/residuals/confidence/sensitivity/comparison)

**颜色方案**:

必须从配置文件或常量定义读取:

| 元素 | 颜色代码 | 说明 |
|-----|---------|------|
| 原始数据散点 | #3498db | 蓝色,alpha=0.5 |
| 拟合曲线 | #e74c3c | 红色实线 |
| 95%置信带 | #fadbd8 | 浅红色阴影 |
| 99%置信带 | #f5b7b1 | 更浅红色阴影 |
| 网格线 | #bdc3c7 | 浅灰色 |
| 历史版本曲线 | ['#2ecc71', '#9b59b6', '#f39c12', '#1abc9c'] | 绿、紫、橙、青 |

**主曲线图(P0必须实现)元素清单**:

1. 原始数据散点(蓝色,alpha=0.5)
2. 拟合曲线(红色实线)
3. 95%置信带(浅红色阴影)
4. 统计信息框(右上角):
   - R²值
   - RMSE值
   - 数据点数
   - 拟合方法
5. 中文标题和坐标轴标签
6. 浅灰色网格线
7. 图例(位置: 右上角或左下角,避免遮挡数据)

**残差分析图(P1推荐实现)子图布局**:

2×2子图:

```
┌─────────────────────┬─────────────────────┐
│  残差 vs 预测值      │  残差 vs 流量        │
│  (散点图)           │  (散点图)            │
├─────────────────────┼─────────────────────┤
│  残差直方图          │  残差Q-Q图           │
│  (直方图+正态曲线)   │  (理论vs实际)        │
└─────────────────────┴─────────────────────┘
```

子图内容:

1. 左上: 残差 vs 预测值 + 零线(y=0虚线)
2. 右上: 残差 vs 流量 + 零线
3. 左下: 残差直方图 + 正态分布拟合曲线
4. 右下: Q-Q图(理论分位数 vs 实际分位数)

**性能与资源考虑**:

| 图片类型 | 预估文件大小 | 预估生成时间 | 预估内存峰值 |
|---------|-------------|-------------|-------------|
| 主曲线图 | 5-10 MB | 3-5秒 | 500 MB |
| 残差分析图 | 4-8 MB | 3-5秒 | 500 MB |
| 置信区间图 | 4-7 MB | 2-4秒 | 400 MB |
| 敏感性分析图 | 3-6 MB | 2-4秒 | 400 MB |
| 版本对比图 | 4-7 MB | 2-4秒 | 400 MB |

降级策略:

内存不足时自动降级到4K分辨率(3840×2160),记录警告日志

**关键实现要求**:

1. 必须使用matplotlib Agg后端: `matplotlib.use('Agg')`
2. 图片生成后必须及时关闭Figure释放内存: `plt.close(fig)`
3. 禁止硬编码颜色、字体、分辨率等配置,必须从常量或配置读取
4. 图片保存使用相对路径,由OutputPathManager统一管理
5. 生成失败时抛出PlotGenerationError(异常码CF012)
6. P0阶段仅实现plot_curve()主曲线图,P1实现plot_residuals(),P2实现其他3种

##### 5.4.6.7 DeviationPlotter偏差绘图器规范

**职责**: 绘制拟合偏差分析相关图表,用于评估拟合精度的空间分布

**优先级**: P2(可选实现)

**核心功能**:

1. 绘制偏差分布直方图
2. 绘制偏差散点图
3. 绘制偏差趋势图
4. 支持多种偏差定义

**核心接口**:

```python
class DeviationPlotter:
    """偏差绘图器"""
    
    def __init__(self, config: PlotConfig):
        """初始化
        
        Args:
            config: 绘图配置(分辨率、字体、颜色等)
        """
    
    def plot_distribution(
        self,
        deviations: np.ndarray,
        title: str = '偏差分布',
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """绘制偏差分布直方图
        
        Args:
            deviations: 偏差数组
            title: 图表标题
            save_path: 保存路径(可选)
            
        Returns:
            Figure: matplotlib图表对象
        """
    
    def plot_scatter(
        self,
        Q: np.ndarray,
        deviations: np.ndarray,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """绘制偏差散点图(偏差vs流量)
        
        Args:
            Q: 流量数组
            deviations: 偏差数组
            save_path: 保存路径
            
        Returns:
            Figure: matplotlib图表对象
        """
    
    def plot_trend(
        self,
        timestamps: np.ndarray,
        deviations: np.ndarray,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """绘制偏差趋势图(偏差vs时间)
        
        Args:
            timestamps: 时间戳数组
            deviations: 偏差数组
            save_path: 保存路径
            
        Returns:
            Figure: matplotlib图表对象
        """
```

**偏差定义**:

| 偏差类型 | 计算公式 | 适用场景 |
|---------|---------|----------|
| 绝对偏差 | deviation = y_actual - y_predicted | 关注绝对误差大小 |
| 相对偏差 | deviation = (y_actual - y_predicted) / y_actual | 关注相对误差比例 |
| 百分比偏差 | deviation = [(y_actual - y_predicted) / y_actual] × 100% | 报告展示 |

**偏差分布直方图内容**:

1. 直方图(bins=50)
2. 正态分布拟合曲线(红色虚线)
3. 统计信息框:
   - 均值(Mean)
   - 标准差(Std)
   - 最大偏差(Max)
   - 最小偏差(Min)
   - 中位数(Median)
4. 零线(x=0黑色虚线)
5. 中文标签

**偏差散点图内容**:

1. 散点图(蓝色,alpha=0.5)
2. 零线(y=0红色虚线)
3. 趋势线(线性回归,绿色)
4. ±2σ区域(灰色阴影)
5. X轴:流量Q (m³/h)
6. Y轴:偏差(根据偏差类型)
7. 中文标签

**偏差趋势图内容**:

1. 折线图(蓝色)
2. 零线(y=0红色虚线)
3. 滚动均值(7点窗口,橙色)
4. X轴:时间
5. Y轴:偏差
6. 中文标签

**关键实现要求**:

1. 使用与HighResPlotter相同的配置(8K分辨率、中文字体)
2. 支持三种偏差类型切换(通过deviation_type参数)
3. 统计信息框必须动态计算,不能硬编码
4. 图片生成后必须关闭Figure: `plt.close(fig)`
5. 生成失败时抛出PlotGenerationError
6. 适用场景:拟合精度分析、异常值检测、模型改进

##### 5.4.6.8 ComparisonPlotter对比绘图器规范

**职责**: 绘制多版本/多方法/多设备的曲线对比图表

**优先级**: P2(可选实现)

**核心功能**:

1. 绘制版本对比图(同设备不同版本)
2. 绘制方法对比图(同数据不同方法)
3. 绘制设备对比图(不同设备同曲线类型)

**核心接口**:

```python
class ComparisonPlotter:
    """对比绘图器"""
    
    def __init__(self, config: PlotConfig):
        """初始化
        
        Args:
            config: 绘图配置
        """
    
    def plot_version_comparison(
        self,
        device_id: int,
        curve_type: str,
        versions: List[str],
        save_path: Optional[str] = None
    ) -> bytes:
        """绘制版本对比图
        
        Args:
            device_id: 设备ID
            curve_type: 曲线类型(qh/qp/qeta)
            versions: 版本号列表(最多5个)
            save_path: 保存路径
            
        Returns:
            bytes: PNG图片字节流
        """
    
    def plot_method_comparison(
        self,
        device_id: int,
        curve_type: str,
        methods: List[str],
        save_path: Optional[str] = None
    ) -> bytes:
        """绘制方法对比图
        
        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            methods: 拟合方法列表(最多5个)
            save_path: 保存路径
            
        Returns:
            bytes: PNG图片字节流
        """
    
    def plot_device_comparison(
        self,
        device_ids: List[int],
        curve_type: str,
        save_path: Optional[str] = None
    ) -> bytes:
        """绘制设备对比图
        
        Args:
            device_ids: 设备ID列表(最多5个)
            curve_type: 曲线类型
            save_path: 保存路径
            
        Returns:
            bytes: PNG图片字节流
        """
```

**对比图特征**:

1. **颜色方案**(从配置读取,禁止硬编码):
   - 版本1/方法1/设备1: 绿色(#2ecc71)
   - 版本2/方法2/设备2: 紫色(#9b59b6)
   - 版本3/方法3/设备3: 橙色(#f39c12)
   - 版本4/方法4/设备4: 青色(#1abc9c)
   - 版本5/方法5/设备5: 棕色(#d35400)

2. **线型区分**:
   - 最新版本/最佳方法/当前设备: 实线(linewidth=2.5)
   - 历史版本/其他方法/其他设备: 虚线(linewidth=1.5)

3. **图例位置**: 右上角或左下角(自动选择避免遮挡)

4. **对比统计表格**(图表下方):

| 版本/方法/设备 | R² | RMSE | MAE | 数据点数 |
|---------------|----|----- |-----|----------|
| ... | ... | ... | ... | ... |

**版本对比图特殊标注**:

1. 标注版本时间(YYYY-MM-DD HH:MM)
2. 标注关键差异点(曲线交叉点)
3. 高亮最新版本(加粗实线)

**方法对比图特殊标注**:

1. 标注方法名称(中文)
2. 标注最佳方法(R²最高,绿色星标)
3. 标注拟合耗时

**设备对比图特殊标注**:

1. 标注设备名称(从dim_devices读取)
2. 标注设备额定参数(Q_rated, H_rated)
3. 标注归一化曲线(可选)

**关键实现要求**:

1. 最多支持5条曲线对比(超过时抛出ValueError)
2. 从数据库读取对比数据(curve_fit_results表)
3. 使用与HighResPlotter相同的配置
4. 颜色和线型从常量定义读取,禁止硬编码
5. 对比统计表格必须动态生成
6. 生成失败时抛出PlotGenerationError
7. 适用场景:版本演进分析、方法选择决策、设备性能对比

##### 5.4.6.4 OutputPathManager路径管理规范

**职责**: 统一管理拟合结果的输出目录结构、文件命名、路径规范化

**输出目录结构**:

```
{base_path}/
├── qh_流量扬程/
│   ├── 20250128_143052/
│   │   ├── qh_流量扬程_polynomial_3_20250128_143052_curve.png
│   │   ├── qh_流量扬程_polynomial_3_20250128_143052_residuals.png
│   │   ├── qh_流量扬程_polynomial_3_20250128_143052_report.md
│   │   └── ...
│   ├── 20250127_100000/
│   └── ...
├── qp_流量功率/
│   └── ...
└── qeta_流量效率/
    └── ...
```

目录层级说明:

1. 第一层: base_path(从配置读取,如 `/reports/curves`)
2. 第二层: 曲线类型中文名称(qh_流量扬程、qp_流量功率、qeta_流量效率)
3. 第三层: 版本号(YYYYMMDD_HHMMSS)
4. 第四层: 具体文件(图片、报告)

**文件命名模板**:

图片文件:

```
{curve_type_cn}_{method_name}_{version}_{image_type}.png
```

报告文件:

```
{curve_type_cn}_{method_name}_{version}_report.md
```

**路径生成方法**:

必须提供以下方法:

1. `get_version_dir(curve_type, version)`: 获取版本目录路径
2. `get_image_path(curve_type, method_name, version, image_type)`: 获取图片完整路径
3. `get_report_path(curve_type, method_name, version)`: 获取报告完整路径
4. `ensure_dir_exists(path)`: 确保目录存在,不存在则创建

**路径规范化**:

所有路径必须使用pathlib.Path处理,确保跨平台兼容性

**关键实现要求**:

1. base_path必须从配置文件读取,禁止硬编码
2. 使用pathlib.Path替代os.path,确保跨平台
3. 目录不存在时自动创建(mkdir(parents=True, exist_ok=True))
4. 返回的路径必须是绝对路径
5. 曲线类型中文名称映射必须从常量定义读取

##### 5.4.6.5 TemplateManager模板管理规范

**职责**: 管理报告模板,使用Jinja2引擎渲染Markdown报告

**优先级**: P2(可选实现)

**核心功能**:

1. 加载Jinja2模板文件
2. 渲染模板生成Markdown报告
3. 支持自定义模板
4. 模板变量注入

**核心接口**:

```python
class TemplateManager:
    """模板管理器"""
    
    def __init__(self, template_dir: str):
        """初始化
        
        Args:
            template_dir: 模板目录路径(从配置读取)
        """
    
    def load_template(self, template_name: str) -> Template:
        """加载模板文件
        
        Args:
            template_name: 模板文件名(如'report_template.md.j2')
            
        Returns:
            Template: Jinja2模板对象
            
        Raises:
            TemplateNotFoundError: 模板文件不存在时抛出
        """
    
    def render(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
        """渲染模板
        
        Args:
            template_name: 模板文件名
            context: 模板变量字典
            
        Returns:
            str: 渲染后的Markdown内容
            
        Raises:
            TemplateRenderError: 渲染失败时抛出
        """
    
    def get_available_templates(self) -> List[str]:
        """获取可用模板列表
        
        Returns:
            List[str]: 模板文件名列表
        """
```

**内置模板配置**:

| 模板名称 | 文件路径 | 用途 |
|---------|---------|------|
| report_template.md.j2 | templates/report_template.md.j2 | 标准拟合报告 |
| summary_template.md.j2 | templates/summary_template.md.j2 | 摘要报告 |
| comparison_template.md.j2 | templates/comparison_template.md.j2 | 版本对比报告 |

**Jinja2引擎配置**:

```python
# 自动转义关闭(Markdown内容)
autoescape = False

# 模板加载器
loader = FileSystemLoader(template_dir)

# 环境配置
Environment(
    loader=loader,
    autoescape=autoescape,
    trim_blocks=True,      # 移除块后的第一个换行符
    lstrip_blocks=True     # 移除块前的空格和制表符
)
```

**模板变量注入示例**:

```python
context = {
    'curve_type': 'qh',
    'curve_type_cn': '流量-扬程',
    'method_name': 'polynomial_3',
    'version': '20250128_143052',
    'r_squared': 0.9856,
    'rmse': 0.234,
    'parameters': [...],
    'quality_rating': '⭐⭐⭐⭐⭐',
    'images': {
        'curve': './qh_流量扬程_polynomial_3_20250128_143052_curve.png',
        'residuals': './qh_流量扬程_polynomial_3_20250128_143052_residuals.png'
    }
}
```

**关键实现要求**:

1. template_dir必须从配置读取,禁止硬编码
2. 必须使用Jinja2引擎(不重复造轮子): `from jinja2 import Environment, FileSystemLoader`
3. 模板文件不存在时抛出TemplateNotFoundError
4. 渲染失败时抛出TemplateRenderError
5. 支持自定义过滤器(如日期格式化、数值格式化)
6. 模板文件编码必须为UTF-8

##### 5.4.6.6 MarkdownReportGenerator报告生成规范

**职责**: 生成12模块完整的Markdown拟合报告,全中文

**12模块报告结构**:

| 模块序号 | 模块名称 | 优先级 | 内容说明 |
|:-------:|---------|:------:|----------|
| 1 | 报告摘要 | P0 | 一页式快速概览,关键指标表格,质量评级 |
| 2 | 拟合方法说明 | P0 | 方法名称、数学公式、物理意义、优缺点 |
| 3 | 参数估计结果 | P0 | 参数表格(值、单位、含义、95%置信区间) |
| 4 | 统计检验指标 | P0 | R²、RMSE、MAE、MAPE、AIC、BIC及星级评级 |
| 5 | 残差分析 | P1 | 残差统计、正态性检验、异方差检验、自相关检验 |
| 6 | 可视化图表 | P0 | 嵌入8K PNG图片(相对路径引用) |
| 7 | 置信区间分析 | P1 | 参数置信区间、预测置信带表格 |
| 8 | 参数敏感性分析 | P2 | 敏感性系数、影响程度评估图 |
| 9 | 分段性能评估 | P1 | 低/中/高流量段分别统计(R²、MAPE) |
| 10 | 历史对比分析 | P2 | 版本列表、曲线漂移分析、对比结论 |
| 11 | 物理约束验证 | P0 | 单调性、边界条件、曲率验证详情 |
| 12 | 运行建议 | P1 | 最佳效率点、推荐运行范围、注意事项 |

**质量评级标准**:

根据R²和MAPE返回星级评级:

| 评级 | R²阈值 | MAPE阈值 | 星级 | 说明 |
|-----|-------|---------|------|------|
| 优秀 | ≥0.98 | <1.0% | ⭐⭐⭐⭐⭐ | 高精度,可直接使用 |
| 良好 | ≥0.95 | <3.0% | ⭐⭐⭐⭐ | 精度较好,可使用 |
| 一般 | ≥0.90 | <5.0% | ⭐⭐⭐ | 精度一般,需验证 |
| 较差 | ≥0.80 | <10.0% | ⭐⭐ | 精度较差,需改进 |
| 差 | <0.80 | ≥10.0% | ⭐ | 精度差,不建议使用 |

**图片嵌入格式**:

使用Markdown相对路径引用:

```markdown
![主曲线图](./qh_流量扬程_polynomial_3_20250128_143052_curve.png)

![残差分析图](./qh_流量扬程_polynomial_3_20250128_143052_residuals.png)
```

**报告模板**:

使用Jinja2模板引擎,模板文件存放在 `templates/report_template.md.j2`

**关键实现要求**:

1. P0阶段实现模块1、2、3、4、6、11共6个模块
2. 报告文件编码必须为UTF-8
3. 图片路径必须使用相对路径,不能使用绝对路径
4. 数学公式使用LaTeX格式,Markdown渲染器支持
5. 生成失败时抛出ReportGenerationError(异常码CF013)

#### 5.4.7 监控层模块补全 (必须实现)

**用户要求**: 监控模块是特性曲线拟合的重要功能,用于检测曲线退化、漂移,自动触发重拟合

##### 5.4.7.1 DegradationDetector退化检测规范

**职责**: 检测曲线拟合精度是否随时间下降,触发告警

**退化检测阈值**:

| 指标 | 阈值 | 说明 |
|-----|------|------|
| R²下降 | >2% | 当前R² < 基线R² - 0.02时触发告警 |
| RMSE增加 | >10% | 当前RMSE > 基线RMSE × 1.1时触发告警 |
| 趋势显著性水平 | p<0.05 | 使用线性回归检测退化趋势 |

**检测窗口**:

默认30天,可配置

**退化检测逻辑**:

1. 从数据库读取device_id + curve_type的最近30天拟合结果
2. 提取R²和RMSE时间序列
3. 计算基线指标(最早7天的平均值)
4. 计算当前指标(最近7天的平均值)
5. 比较当前指标与基线指标,判断是否超过阈值
6. 使用scipy.stats.linregress检测退化趋势

**返回结果结构**:

```python
{
    "is_degraded": bool,
    "degradation_rate": {
        "r_squared": float,  # R²退化速率(单位: 每天)
        "rmse": float        # RMSE增加速率(单位: 每天)
    },
    "trend": {
        "slope": float,      # 趋势斜率
        "p_value": float,    # 显著性p值
        "significant": bool  # 是否显著(p<0.05)
    },
    "recommendations": [str]  # 建议列表
}
```

**关键实现要求**:

1. 检测窗口天数必须从配置读取,禁止硬编码
2. 退化阈值必须从配置读取
3. 必须使用scipy.stats.linregress进行趋势检验
4. 检测到退化时记录WARNING级别日志
5. 返回的recommendations必须包含具体建议(如"建议重新拟合")

##### 5.4.7.2 DriftDetector漂移检测规范

**职责**: 检测曲线形状(参数)是否发生变化,区分渐变和突变

**漂移检测阈值**:

| 检测类型 | 阈值 | 说明 |
|---------|------|------|
| 参数变化 | >5% | 任一参数变化超过5%时触发告警 |
| 形状差异 | >10% | 曲线面积差异超过10%时触发告警 |
| 突变阈值 | >15% | 单次参数变化超过15%判定为突变 |

**漂移类型**:

| 类型 | 判定条件 | 说明 |
|-----|---------|------|
| gradual_drift | 连续3个版本参数变化>5%,但单次<15% | 渐变漂移 |
| sudden_drift | 单次参数变化>15% | 突变漂移 |
| no_drift | 参数变化<5% | 无漂移 |

**漂移检测逻辑**:

1. 从数据库读取device_id + curve_type的最近N个版本(默认5个)
2. 提取每个版本的拟合系数
3. 计算相邻版本参数变化率: `(param_new - param_old) / param_old`
4. 计算曲线面积差异(使用数值积分)
5. 判断漂移类型

**参数变化计算**:

对于多项式拟合 `y = a0 + a1*x + a2*x^2 + a3*x^3`:

计算每个系数的变化率:

```python
param_changes = {
    'a0': abs(a0_new - a0_old) / abs(a0_old),
    'a1': abs(a1_new - a1_old) / abs(a1_old),
    # ...
}
```

**形状差异计算**:

使用数值积分计算曲线下面积:

```python
from scipy.integrate import simpson

Q_range = np.linspace(Q_min, Q_max, 1000)
area_old = simpson(predict_old(Q_range), Q_range)
area_new = simpson(predict_new(Q_range), Q_range)
shape_diff = abs(area_new - area_old) / abs(area_old)
```

**返回结果结构**:

```python
{
    "is_drifted": bool,
    "drift_type": str,  # "gradual_drift" / "sudden_drift" / "no_drift"
    "param_changes": dict,  # 每个参数的变化率
    "shape_similarity": float,  # 形状相似度(1-shape_diff)
    "possible_causes": [str],  # 可能的漂移原因
    "recommendations": [str]   # 建议列表
}
```

**漂移原因识别规则**:

| 漂移特征 | 可能原因 |
|---------|----------|
| 所有系数同向变化 | 设备整体性能下降 |
| 仅高次系数变化 | 曲线形状变化,可能磨损 |
| 常数项显著变化 | 零流量扬程变化,可能堵塞 |
| 突变漂移 | 设备维修、更换部件 |

**关键实现要求**:

1. 漂移阈值必须从配置读取
2. 必须使用scipy.integrate.simpson计算曲线面积
3. 检测到漂移时记录WARNING级别日志
4. possible_causes必须根据参数变化特征智能推断

##### 5.4.7.3 AutoRefitTrigger自动重拟合触发规范

**职责**: 综合退化和漂移检测结果,决定是否需要重拟合,触发重拟合任务

**触发条件**:

满足以下任一条件触发重拟合:

1. DegradationDetector检测到退化(is_degraded=True)
2. DriftDetector检测到突变漂移(drift_type="sudden_drift")
3. DriftDetector检测到渐变漂移且已持续3个版本以上

**触发决策逻辑**:

```python
if degradation_result['is_degraded']:
    trigger_reason = "检测到精度退化"
    needs_refit = True
elif drift_result['drift_type'] == 'sudden_drift':
    trigger_reason = "检测到曲线突变漂移"
    needs_refit = True
elif drift_result['drift_type'] == 'gradual_drift' and drift_count >= 3:
    trigger_reason = "检测到持续渐变漂移"
    needs_refit = True
else:
    needs_refit = False
```

**重拟合执行模式**:

| 模式 | 说明 | 使用场景 |
|-----|------|----------|
| 手动确认 | auto_refit=False | 生产环境,需人工审核 |
| 自动执行 | auto_refit=True | 测试环境,自动化运维 |

**回调机制**:

支持注册回调函数,在触发重拟合时执行通知:

```python
def on_refit_triggered(device_id, curve_type, reason):
    # 发送邮件通知
    # 发送企业微信消息
    # 记录运维日志
    pass

trigger.register_callback(on_refit_triggered)
```

**重拟合历史记录**:

必须记录每次触发重拟合的历史:

记录内容:

```python
{
    "triggered_at": datetime,
    "device_id": int,
    "curve_type": str,
    "trigger_reason": str,
    "degradation_result": dict,
    "drift_result": dict,
    "refit_executed": bool,
    "new_version": str  # 重拟合后的新版本号
}
```

存储位置: 数据库表 `curve_refit_history`

**关键实现要求**:

1. 必须先调用DegradationDetector和DriftDetector
2. 触发重拟合时记录INFO级别日志
3. auto_refit=True时必须调用CurveFittingPipeline.run()执行重拟合
4. 重拟合历史必须持久化到数据库
5. 支持多个回调函数注册(使用列表存储)

**每个曲线的数据提取要求(重要)**:

**QHCurve (流量-扬程曲线)**:
- 必需指标: `pump_flow_rate` (Q), `pump_head` (H)
- 数据特性: 单调递减 (dH/dQ < 0)
- 数据特征: 
  - 零流量点: H₀ ≈ 1.1~1.3 × H_rated
  - 全范围下凸 (d²H/dQ² > 0)
  - H(Q_max) > 0
- SQL提取示例:
  ```sql
  SELECT ts_bucket,
         MAX(CASE WHEN metric_key = 'pump_flow_rate' THEN value END) AS Q,
         MAX(CASE WHEN metric_key = 'pump_head' THEN value END) AS H
  FROM fact_measurements
  WHERE device_id = ? AND ts_bucket BETWEEN ? AND ?
  GROUP BY ts_bucket
  HAVING Q IS NOT NULL AND H IS NOT NULL
  ```

**QPCurve (流量-功率曲线)**:
- 必需指标: `pump_flow_rate` (Q), `pump_active_power` (P)
- 数据特性: 单调递增 (dP/dQ > 0)
- 数据特征:
  - 零流量点: P₀ ≈ 0.3~0.5 × P_rated (空载功率)
  - 全范围上凸 (d²P/dQ² < 0)
  - P_max ≤ 1.2 × P_rated
  - 能量守恒: P ≈ ρgQH/η
- SQL提取示例:
  ```sql
  SELECT ts_bucket,
         MAX(CASE WHEN metric_key = 'pump_flow_rate' THEN value END) AS Q,
         MAX(CASE WHEN metric_key = 'pump_active_power' THEN value END) AS P
  FROM fact_measurements
  WHERE device_id = ? AND ts_bucket BETWEEN ? AND ?
  GROUP BY ts_bucket
  HAVING Q IS NOT NULL AND P IS NOT NULL
  ```

**QEtaCurve (流量-效率曲线)**:
- 必需指标: `pump_flow_rate` (Q), `pump_efficiency` (η)
- 数据特性: 单峰曲线 (先增后减)
- 数据特征:
  - 零流量点: η(0) = 0
  - 最大流量点: η(Q_max) → 0
  - 值域范围: 0 ≤ η ≤ 1
  - BEP点位置: 0.6×Q_rated < Q_BEP < 1.2×Q_rated
  - 数据转换: pump_efficiency存储为百分比(0-100),需转换为小数(0-1)
- SQL提取示例:
  ```sql
  SELECT ts_bucket,
         MAX(CASE WHEN metric_key = 'pump_flow_rate' THEN value END) AS Q,
         MAX(CASE WHEN metric_key = 'pump_efficiency' THEN value END) AS eta
  FROM fact_measurements
  WHERE device_id = ? AND ts_bucket BETWEEN ? AND ?
  GROUP BY ts_bucket
  HAVING Q IS NOT NULL AND eta IS NOT NULL
  -- 注意: eta值需要除以100转换为小数
  ```

**每个曲线必须包含的7个子模块**:

1. **DataExtractor**: 提取该曲线所需的特定指标数据
   - QHDataExtractor: 提取Q和H
   - QPDataExtractor: 提取Q和P
   - QEtaDataExtractor: 提取Q和η(需转换为小数)

2. **Preprocessor**: 预处理数据
   - 清洗: 删除无效值(Q<0、H<0等)
   - 去重: 删除重复时间戳
   - 异常值处理: 基于物理约束的异常值过滤
   - 运行点筛选: 只保留泵运行状态的数据

3. **Constraints**: 计算物理约束参数
   - QHConstraints: H0, Q_max, K, monotonicity='decreasing'
   - QPConstraints: P0, P_max, monotonicity='increasing'
   - QEtaConstraints: Q_BEP, η_max, 单峰性验证

4. **Normalizer**: 归一化处理
   - Q归一化: Q_norm = Q / Q_rated
   - Y归一化: Y_norm = Y / Y_rated (Y为H/P/η)

5. **MethodSelector**: 方法选择
   - 根据数据质量、数量、分布选择合适的拟合方法

6. **CurveFitter**: 曲线拟合
   - 顺序执行选定的拟合方法
   - 计算拟合指标(R², RMSE, MAE)

7. **Validator**: 验证拟合结果
   - QHValidator: 验证单调性递减、边界、凸性
   - QPValidator: 验证单调性递增、能量守恒
   - QEtaValidator: 验证单峰性、值域范围、BEP位置

**重要说明**:

1. **曲线子模块不是独立模块**: 子模块定义在曲线类文件内或子目录内
2. **数据提取的差异性**: 每个曲线提取的指标不同,数据特性和验证规则也不同
3. **数据特征验证**: 必须在Preprocessor和Validator中验证数据符合该曲线的物理特性

#### 5.4.8 可视化性能与资源管理

**目标**: 优化可视化模块的性能和资源消耗,确保系统稳定运行

##### 5.4.8.1 资源消耗评估

**8K分辨率图片资源消耗**:

| 图片类型 | 预估文件大小 | 预估生成时间 | 预估内存峰值 |
|---------|-------------|-------------|-------------|
| 主曲线图 | 5-10 MB | 3-5秒 | 500 MB |
| 残差分析图 | 4-8 MB | 3-5秒 | 500 MB |
| 置信区间图 | 4-7 MB | 2-4秒 | 400 MB |
| 敏感性分析图 | 3-6 MB | 2-4秒 | 400 MB |
| 版本对比图 | 4-7 MB | 2-4秒 | 400 MB |

**关键资源指标**:

1. **单张图片生成**:
   - 内存峰值: 500 MB(主曲线图和残差分析图)
   - 生成时间: 3-5秒
   - 文件大小: 5-10 MB(PNG压缩级别6)

2. **批量生成(5种图片)**:
   - 总内存峰值: 约800 MB(因为plt.close()释放)
   - 总生成时间: 12-20秒
   - 总文件大小: 20-40 MB

3. **并发生成风险**:
   - 同时生成N张图片内存峰值: 500 MB × N
   - 建议最大并发数: 4(总内存2GB)

**磁盘空间规划**:

单设备单曲线单版本存储空间:

```
单版本存储 = 5种图片 × 8MB + 1个MD报告 × 100KB ≈ 40MB

单设备1年存储(3条曲线,每月更新1次):
= 3曲线 × 12版本 × 40MB ≈ 1.4GB

100台设妇1年存储:
= 100设备 × 1.4GB ≈ 140GB
```

建议磁盘预留空间: 200-300GB(包含历史版本和临时文件)

##### 5.4.8.2 性能优化建议

**matplotlib后端选择**:

```python
import matplotlib
matplotlib.use('Agg')  # 非交互式后端,节省内存
```

**优势**:

- 不需要GUI环境
- 内存消耗降低20-30%
- 支持多线程并发
- 适合服务器环境

**PNG压缩级别调优**:

```python
plt.savefig(
    filepath,
    dpi=300,
    bbox_inches='tight',
    compression_level=6  # 平衡文件大小和速度
)
```

**压缩级别对比**:

| 压缩级别 | 文件大小 | 保存时间 | 说明 |
|:--------:|:--------:|:--------:|------|
| 0 | 15 MB | 0.5秒 | 无压缩,文件过大 |
| 3 | 10 MB | 1.0秒 | 快速压缩 |
| 6 | 7 MB | 2.0秒 | **推荐平衡点** |
| 9 | 6 MB | 4.0秒 | 最大压缩,耗时长 |

**内存释放机制**:

```python
import matplotlib.pyplot as plt

# 生成图片
fig, ax = plt.subplots(figsize=(25.6, 14.4), dpi=300)
# ... 绘图逻辑 ...
plt.savefig(filepath, compression_level=6)

# 关键:必须关闭Figure释放内存
plt.close(fig)
```

**不关闭的后果**:

- 内存泄漏:每张图片500MB内存不释放
- 生成20张图后内存消耗达到10GB
- 最终导致系统OOM(Out of Memory)

**并发控制**:

使用线程池限制并发数:

```python
from concurrent.futures import ThreadPoolExecutor

# 最大并发4个线程,避免内存压力
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(plotter.plot_curve, ...)
        for device_id in device_ids
    ]
    results = [f.result() for f in futures]
```

**缓存策略**:

1. **图片缓存**: 相同版本不重复生成
   - 检查目标文件是否存在
   - 存在且MD5校验通过则跳过

2. **数据缓存**: 曲线点数据缓存
   - 从curve_fit_results.curve_points读取
   - 避免重复计算

##### 5.4.8.3 降级策略

**用户要求注意**: 此处的“降级策略”是指**可视化分辨率降级**,不是拟合方法降级

**内存不足时的分辨率降级**:

| 等级 | 分辨率 | 像素 | DPI | 内存峰值 | 文件大小 | 适用场景 |
|:----:|---------|------|-----|----------|----------|----------|
| 高清 | 7680×4320 | 8K | 300 | 500 MB | 8 MB | **默认首选** |
| 标清 | 3840×2160 | 4K | 300 | 200 MB | 3 MB | 内存<1GB时 |
| 普清 | 1920×1080 | FHD | 150 | 50 MB | 1 MB | 内存<500MB时 |

**降级触发条件**:

1. **主动检测内存**:
```python
import psutil

available_memory = psutil.virtual_memory().available
if available_memory < 1 * 1024**3:  # <1GB
    # 降级到4K
    resolution = (3840, 2160)
    dpi = 300
elif available_memory < 500 * 1024**2:  # <500MB
    # 降级到FHD
    resolution = (1920, 1080)
    dpi = 150
else:
    # 使用8K
    resolution = (7680, 4320)
    dpi = 300
```

2. **捕获MemoryError异常**:
```python
try:
    fig, ax = plt.subplots(figsize=(25.6, 14.4), dpi=300)
    # 绘图逻辑
except MemoryError:
    logger.warning("内存不足,降级到4K分辨率")
    plt.close('all')  # 清理内存
    fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=300)  # 4K
    # 重新绘图
```

**降级日志记录**:

```python
import logging

logger.warning(
    f"可用内存不足({available_memory/1024**3:.2f}GB), "
    f"图片分辨率从8K降级到4K",
    extra={
        'device_id': device_id,
        'curve_type': curve_type,
        'original_resolution': '8K',
        'degraded_resolution': '4K'
    }
)
```

**降级后的质量保障**:

- 4K分辨率仍然满足绝大多数显示需求
- DPI=300保持不变,确保打印质量
- 所有图表元素正常显示
- 中文标签清晰可读

**关键实现要求**:

1. 默认使用8K分辨率,不需要配置
2. 内存不足时自动降级,记录WARNING日志
3. 降级后仍然生成图片,不抛出异常
4. 降级信息必须记录到日志,方便追踪问题
5. 禁止硬编码分辨率,必须从常量定义读取

#### 5.4.7 P2泵组模块补全 (必须实现)

**用户要求**: 所有模块必须实现,包括P2阶段

**注意**: P2模块在P0核心功能稳定后实现

**P2泵组模块清单**:

| 模块 | 文件路径 | 实现要求 | 用途 |
|-----|---------|:-------:|------|
| PumpGroupProcessor | pump_group/pump_group_processor.py | **必须实现** | 泵组类型识别 |
| ParallelSynthesizer | pump_group/parallel_synthesizer.py | **必须实现** | 并联合成 |
| SystemCorrectionModel | pump_group/system_correction_model.py | **必须实现** | 修正系数学习 |

##### 5.4.7.1 SystemCorrectionModel系统修正系数模型规范

**职责**: 从历史运行数据学习泵组修正系数,使理论合成扬程更接近实际值

**修正原理**:

```
修正公式: H_actual = H_theoretical × α(N, Q_total)

其中:
- H_actual: 实际扬程
- H_theoretical: 理论合成扬程
- α: 修正系数(依赖台数N和流量Q_total)

模型类型:
- linear: α = a₀ + a₁N + a₂Q
- polynomial: α = a₀ + a₁N + a₂Q + a₃N² + a₄Q² + a₅NQ
- xgboost: XGBoost回归
```

**训练数据获取规则**:

1. **数据来源**: public.fact_measurements 表
2. **时间范围**: 默认最近30天,建议至少7天
3. **所需字段**:
   - ts_bucket: 时间戳
   - device_id: 设备ID(用于识别泵)
   - flow_rate: 流量 (m³/h)
   - outlet_pressure / inlet_pressure: 出口/进口压力(计算扬程)
   - frequency: 运行频率(变频泵)
   - power: 实际功率 (kW)
4. **数据处理**:
   - 按时间戳分组,计算每个时刻的泵组工况:
     - N: 运行泵台数(flow_rate > 0 的泵数量)
     - Q_total: 总流量 = Σ flow_rate
     - H_actual: 实际扬程 = (outlet_pressure - inlet_pressure) / (ρg)
   - 通过 ParallelSynthesizer 计算理论扬程 H_theoretical
5. **最小数据量**: 默认至少100个有效数据点(min_training_points)
6. **数据质量要求**:
   - 过滤异常值(扬程 < 0 或 > 100m)
   - 过滤流量为0的停机状态
   - 过滤频率过低的启动/停止过渡态

**核心接口**:

```python
class SystemCorrectionModel:
    """系统修正系数模型"""
    
    def __init__(self, config: Optional[CorrectionModelConfig] = None):
        """初始化
        
        Args:
            config: 配置参数,包含:
                - model_type: 'linear' | 'polynomial' | 'xgboost'
                - polynomial_degree: 多项式阶数(默认2)
                - regularization_alpha: 正则化系数(默认1.0)
                - min_training_points: 最小训练点数(默认100)
        """
    
    def fit(
        self,
        station_id: int,
        pump_ids: List[int],
        training_data: Optional[np.ndarray] = None,
        extra_features: Optional[Dict[str, Any]] = None
    ) -> 'SystemCorrectionModel':
        """训练修正模型
        
        Args:
            station_id: 泵站ID
            pump_ids: 泵ID列表
            training_data: 训练数据 [N, Q_total, H_theoretical, H_actual]
            extra_features: 扩展特征字典(用于MIXED_HETEROGENEOUS场景)
            
        Returns:
            self: 支持链式调用
            
        Raises:
            CorrectionModelTrainingError: 训练数据不足或训练失败时抛出
        """
    
    def predict(
        self,
        N: np.ndarray,
        Q: np.ndarray
    ) -> np.ndarray:
        """预测修正系数
        
        Args:
            N: 运行台数数组
            Q: 总流量数组
            
        Returns:
            alpha: 修正系数数组
        """
    
    def apply_correction(
        self,
        H_theoretical: float,
        N: int,
        Q_total: float
    ) -> float:
        """应用修正系数
        
        Args:
            H_theoretical: 理论扬程
            N: 运行台数
            Q_total: 总流量
            
        Returns:
            H_actual: 修正后的实际扬程
        """
    
    def get_training_info(self) -> Dict[str, Any]:
        """获取训练信息
        
        Returns:
            Dict: {
                'data_points': int,
                'train_r2': float,
                'trained_at': str,
                'valid_range': {...}
            }
        """
```

**关键实现要求**:

1. **必须使用sklearn/xgboost**: 不重复造轮子
   - polynomial: sklearn.preprocessing.PolynomialFeatures + sklearn.linear_model.Ridge
   - xgboost: xgboost.XGBRegressor
2. **禁止默认值**: training_data缺失时直接抛出CorrectionModelTrainingError,不使用默认α=1.0
3. **数据不足处理**: 数据点数 < min_training_points 时直接抛出异常,不继续训练
4. **训练状态跟踪**: 必须记录is_fitted状态,predict()调用前检查
5. **有效范围记录**: 必须记录训练数据的N和Q有效范围,预测时警告超出范围
6. **模型持久化**: 支持将模型保存到数据库curve_fit_results.correction_model字段(JSONB)

#### 5.4.8 拟合方法优化策略

**用户明确要求**: 现有落地代码的拟合方法足够,不补充新方法,但必须优化现有方法

**执行策略**:

**保留现有方法**:

- 保留`methods/mathematical/`目录下所有已实现方法
- 保留`methods/physical/`目录下所有已实现方法
- 保留`methods/machine_learning/`目录下所有已实现方法
- 保留`methods/hybrid/`目录下所有已实现方法

**方法清理要求** (强制执行):

1. **删除硬编码**:
   - 移除方法内部的硬编码参数值
   - 所有参数通过构造函数或配置文件传入
   - 示例:删除`tolerance=1e-6`这类硬编码,改为从配置获取

2. **删除默认值**:
   - 移除函数参数的默认值
   - 强制调用方显式提供所有参数
   - 示例:将`def fit(X, y, max_iter=1000)`改为`def fit(X, y, max_iter)`

3. **删除降级策略**:
   - 移除拟合失败后的回退逻辑
   - 失败即抛出异常,不尝试降级方法
   - 示例:删除"拟合失败时使用简单多项式"的回退代码

4. **验证完整性**:
   - 确保每个方法有完整的业务逻辑
   - 确保每个方法有对应的单元测试
   - 删除仅为占位的空方法

**方法注册清理**:

- 删除MethodRegistry中未实现方法的注册
- 仅保留methods/目录下实际存在且完整实现的方法
- 验证注册的方法ID与文件中的实现一致

#### 5.4.7 P2泵组模块补全 (必须实现)

**用户要求**: 所有模块必须实现,包括P2阶段

**P2泵组模块清单**:

| 模块 | 文件路径 | 实现要求 | 用途 |
|-----|---------|:-------:|------|
| PumpGroupProcessor | pump_group/pump_group_processor.py | **必须实现** | 泵组类型识别 |
| ParallelSynthesizer | pump_group/parallel_synthesizer.py | **必须实现** | 并联合成 |
| SystemCorrectionModel | pump_group/system_correction_model.py | **必须实现** | 修正系数学习 |

**注意**: 
- P2模块在P0核心功能稳定后实现
- 必须符合文档定义的接口规范
- 必须有对应的单元测试

### 5.5 管道重构策略

#### 5.5.1 依赖注入强制执行

**目标**: 严格按文档要求实现依赖注入,删除"向后兼容"妥协和默认值

**用户要求**:

- ✅ 不允许有默认值
- ✅ 不要重复造轮子(禁止内部创建依赖)

**构造函数重构**:

**删除的代码模式**:

```python
# ❌ 删除这种"向后兼容"的妥协和默认值
def __init__(
    self,
    method_registry: Optional[Any] = None,  # ❌ 删除Optional和默认值
    result_storage: Optional[Any] = None,   # ❌ 删除Optional和默认值
    cache_manager: Optional[CacheManager] = None,  # ❌ 删除默认值
):
    if method_registry is None:
        self._method_registry = MethodRegistry()  # ❌ 删除自动创建
```

**符合要求的实现**:

```python
def __init__(
    self,
    method_registry: MethodRegistry,        # ✓ 必需参数,无默认值
    result_storage: ResultStorage,          # ✓ 必需参数,无默认值
    cache_manager: CacheManager,            # ✓ 必需参数,无默认值
):
    self._method_registry = method_registry
    self._result_storage = result_storage
    self._cache_manager = cache_manager
```

**关键变化**:

1. 所有参数都是必需的,无Optional
2. 删除所有参数默认值(包括None)
3. 禁止内部创建依赖实例
4. 调用方必须显式提供所有依赖

#### 5.5.2 阶段处理器精简

**目标**: 删除占位处理器,仅保留已完整实现的阶段

**P0阶段处理器保留清单**:

| 阶段 | 处理器方法 | 保留条件 |
|:---:|-----------|----------|
| 1 | _stage_time_window_split | 完整实现且通过测试 |
| 3 | _stage_data_extract | 依赖DataExtractor补全后实现 |
| 4 | _stage_data_clean | 完整实现且通过测试 |
| 6 | _stage_constraint_calc | 依赖ConstraintCalculator补全后实现 |
| 8 | _stage_data_normalize | 完整实现且通过测试 |
| 9 | _stage_method_select | 完整实现且通过测试 |
| 10 | _stage_curve_fit | 完整实现且通过测试 |
| 11 | _stage_result_validate | 完整实现且通过测试 |
| 13 | _stage_result_store | 完整实现且通过测试 |

**删除的处理器**:

| 阶段 | 处理器方法 | 删除理由 |
|:---:|-----------|----------|
| 2 | _stage_scenario_detect | P1功能,暂不实现 |
| 5 | _stage_steady_state_detect | 依赖模块未补全,暂删除 |
| 7 | _stage_freq_normalize | 依赖模块未补全,暂删除 |
| 12 | _stage_historical_eval | 依赖模块未补全,暂删除 |
| 14 | _stage_plot_generation | 移至output模块,不在管道内 |
| 15 | _stage_report_generation | 移至output模块,不在管道内 |

**_stage_handlers字典同步更新**:

删除对应条目,避免运行时调用占位函数。

#### 5.5.3 错误处理系统化

**目标**: 建立完整的异常捕获和错误码体系

**管道级异常处理**:

每个阶段处理器统一异常处理模式:

```python
def _stage_xxx(self, ctx: PipelineContext) -> StageResult:
    try:
        # 业务逻辑
        result = ...
        return StageResult(success=True, data=result)
    except DataExtractionError as e:
        logger.error(f"阶段X失败: {e.error_code} - {e}")
        return StageResult(success=False, error_code=e.error_code, error_message=str(e))
    except Exception as e:
        logger.exception(f"阶段X未预期异常: {e}")
        return StageResult(success=False, error_code="CF999", error_message="内部错误")
```

**错误传播策略**:

- 关键阶段失败:立即终止管道,返回失败结果
- 可选阶段失败:记录警告,继续执行后续阶段

### 5.6 测试体系建立

#### 5.6.1 删除无效测试

**目标**: 删除针对占位函数和已删除模块的测试

**删除测试范围**:

- models.py相关测试
- pump_group/相关测试
- 占位处理器的测试
- 未实现方法的测试

#### 5.6.2 P0核心测试建立

**目标**: 建立P0核心功能的单元测试和端到端测试

**单元测试覆盖**:

| 模块 | 测试文件 | 覆盖率目标 |
|-----|---------|:--------:|
| core.data_structures | test_data_structures.py | 95% |
| curves.qh_curve | test_qh_curve.py | 90% |
| methods.polynomial | test_polynomial.py | 90% |
| constraints.* | test_constraints.py | 90% |
| pipeline.curve_fitting_pipeline | test_pipeline.py | 85% |

**端到端测试**:

建立完整拟合流程测试:

1. 准备测试数据(模拟fact_measurements)
2. 执行完整管道
3. 验证拟合结果正确性
4. 验证数据库存储正确性

### 5.7 执行路径规划

#### 5.7.1 分阶段执行

**阶段1: 代码清理** (优先级最高)

**目标**: 删除所有垃圾代码,建立清洁基线

**执行步骤**:

1. 删除models.py并迁移引用
2. 删除pump_group/目录
3. 删除占位处理器
4. 清理shared/冗余文件
5. 删除对应的无效测试

**验证标准**:

- 代码库无DEPRECATED标记
- 无TODO占位符
- 无未使用的导入
- 测试套件全部通过(即使覆盖率低)

**阶段2: 核心模块补全** (基础建设)

**用户要求**: 所有模块必须完整实现(除拟合方法外)

**目标**: 补全所有缺失模块,建立完整的系统架构

**执行步骤**:

1. 实现core/模块(data_structures, exceptions, enums)
2. 补全shared/共用层模块(9个独立模块)
3. 补全preprocessing/独立模块(4个)
4. 补全constraints/模块(6个)
5. 补全curves/曲线类(3个,每个包含7个子模块)
6. 补全output/模块
7. 补全pump_group/模块(3个,P0后)

**验证标准**:

- 每个模块有对应单元测试
- 模块接口符合文档定义
- 无硬编码假数据
- 无默认值
- 无降级策略

**阶段3: 管道重构** (流程整合)

**目标**: 重构管道实现依赖注入和完整数据流

**执行步骤**:

1. 重构CurveFittingPipeline构造函数(强制依赖注入)
2. 重新实现阶段处理器(集成补全的模块)
3. 建立系统化异常处理
4. 更新阶段执行逻辑

**验证标准**:

- 端到端测试通过
- 完整日志输出
- 异常正确传播

**阶段4: 全模块补全与优化** (全面建设)

**用户要求**: 除拟合方法外,所有模块必须完整实现

**目标**: 实现所有缺失模块,优化现有方法

**执行步骤**:

1. 补全所有preprocessing/独立模块(4个)
2. 补全所有shared/共用层模块(9个)
3. 补全所有constraints/模块(6个)
4. 补全所有curves/曲线类及子模块(3个曲线×7个子模块)
5. 补全output/模块
6. 优化现有拟合方法(清理硬编码、默认值、降级策略)
7. 实现pump_group/模块(3个,P0后)

**验证标准**:

- 所有模块完整实现,无占位
- 所有模块有对应单元测试
- 无硬编码参数
- 无默认值
- 无降级策略
- 16阶段数据流全部正常工作

**阶段5: 测试与验证** (质量保障)

**目标**: 建立完整测试体系

**执行步骤**:

1. 补充单元测试达到90%覆盖率
2. 建立端到端测试套件
3. 使用真实数据验证
4. 性能测试

**验证标准**:

- 单元测试覆盖率≥90%
- 端到端测试覆盖主流程
- 拟合结果符合物理规律

#### 5.7.2 风险控制

**代码删除风险**:

| 风险 | 影响 | 缓解措施 |
|-----|------|----------|
| 误删有用代码 | 功能丢失 | 删除前建立Git分支备份 |
| 引用未清理干净 | 运行时错误 | 使用静态分析工具检查 |
| 测试覆盖不足 | 回归缺陷 | 先建立端到端测试再删除 |

**模块补全风险**:

| 风险 | 影响 | 缓解措施 |
|-----|------|----------|
| 理解文档偏差 | 实现不符合规范 | 每个模块完成后对照文档review |
| 依赖关系复杂 | 集成困难 | 严格遵循依赖层次,禁止循环依赖 |
| 数据库表不存在 | 无法存储结果 | 先验证表结构再实现存储逻辑 |

**重构风险**:

| 风险 | 影响 | 缓解措施 |
|-----|------|----------|
| 破坏现有功能 | 系统不可用 | 采用渐进式重构,保持测试通过 |
| 接口变更影响调用方 | 兼容性问题 | P0阶段允许破坏性变更,清理历史包袱 |

### 5.8 关键决策点

**用户明确要求确认**:

✅ **不要重复造轮子**: 必须复用现有功能,禁止重复实现
✅ **不允许硬编码**: 所有配置必须外部化
✅ **不允许默认值**: 禁止使用默认参数,所有参数必须显式提供
✅ **不允许降级策略**: 禁止实现回退逻辑,失败即中断
✅ **拟合方法现有代码足够**: 不补充新方法,只清理和优化现有方法
✅ **所有其他模块必须实现**: 除拟合方法外,所有模块必须完整实现

**决策1: 是否完全删除pump_group/**

**推荐**: 完全删除

**理由**:

- P0阶段尚未稳定,P2代码价值有限
- 避免维护半成品代码的心智负担
- 文档已充分定义,重新实现成本可控

**决策2: models.py迁移策略**

**推荐**: 立即迁移并删除

**理由**:

- 已明确标记DEPRECATED,继续使用会积累技术债务
- core.data_structures已建立,迁移路径清晰
- 引用点有限,迁移成本低

**决策3: 占位处理器保留还是删除**

**推荐**: 全部删除

**理由**:

- 占位代码无实际价值,反而误导开发
- 删除后管道更清晰,只包含已实现的阶段
- 补全模块后重新实现更符合规范

**决策4: 模块实现范围**

**用户明确要求**: 除拟合方法外,所有模块必须完整实现

**执行策略**:

- **拟合方法**: 保留现有已实现方法,不补充新方法,仅优化清理
- **其他所有模块**: 必须完整实现,包括P0、P1、P2所有阶段
- **共用层**: 9个独立模块全部实现
- **预处理层**: 4个独立模块全部实现
- **约束层**: 6个模块全部实现
- **曲线层**: 3个曲线类全部实现,每个包含7个子模块
- **泵组层**: P2阶段3个模块全部实现

**决策5: 是否保留PLOT_GENERATION和REPORT_GENERATION阶段**

**推荐**: 从管道中移除,放入output模块

**理由**:

- 文档未定义这两个阶段为管道流程
- 图表和报告生成应作为独立功能
- 管道聚焦拟合核心流程

---

## 6. 配置管理系统

### 6.1 配置文件设计

#### 6.1.1 配置存储策略

**核心原则**:曲线拟合的**业务参数**存储在数据库中,**系统配置**复用项目现有配置文件

| 参数类型 | 存储位置 | 说明 |
|---------|---------|------|
| **拟合业务参数** | 数据库三表 | 可按设备/曲线/方法版本化管理 |
| **系统通用配置** | `configs/*.yaml` | 复用项目现有配置 |
| **模块特有配置** | `configs/curve_fitting.yaml` | 仅曲线拟合模块独有配置 |

**禁止事项**:

```yaml
# ❌ 错误:这些参数不应出现在配置文件中
curve_fitting:
  qh:
    validation:
      r_squared_min: 0.95      # ❌ 应存储在数据库
    constraints:
      H0_min: 0                # ❌ 应存储在数据库
```

#### 6.1.2 configs/curve_fitting.yaml

**文件位置**: `configs/curve_fitting.yaml`

**内容**:

```yaml
# 缓存配置(仅内存缓存,禁止Redis)
cache:
  enabled: true
  backend: "memory"
  lru:
    max_size: 1000
    max_memory_mb: 512
  ttl:
    curve_result: 3600
    device_params: 86400

# 并行控制配置
parallel:
  enabled: true
  max_workers: 4
  batch_size: 100
  timeout_seconds: 300

# 数据预处理默认配置
preprocessing:
  min_data_points: 50          # 拟合最小数据点数
  min_extraction_points: 100   # 数据提取建议点数
  max_data_points: 100000
  outlier_detection: "3sigma"
  normalization_enabled: true

# 监控告警配置
monitoring:
  enabled: true
  alerts:
    r_squared_warning: 0.90
    r_squared_critical: 0.80
    fit_time_warning_seconds: 60

# 频率归一化配置
frequency_normalization:
  reference_freq: 50.0     # 参考频率(Hz)
  min_freq: 25.0           # 最小有效频率
  max_freq: 60.0           # 最大有效频率
  default_freq: 50.0       # 默认频率
  std_threshold: 2.0       # 频率波动阈值

# 泵组处理配置
pump_group:
  power_diff_threshold: 0.10
  correction_model:
    model_type: "polynomial"
    polynomial_degree: 2
    regularization_alpha: 1.0
    min_training_points: 100
    validation_ratio: 0.2
```

#### 6.1.3 统一配置访问类

**位置**: `app/services/characteristic_curves/core/config.py`

**设计**:

```python
from dataclasses import dataclass
from functools import lru_cache

@dataclass(frozen=True)
class FrequencyNormalizationConfig:
    """频率归一化配置(不可变)"""
    reference_freq: float = 50.0
    min_freq: float = 25.0
    max_freq: float = 60.0
    default_freq: float = 50.0
    std_threshold: float = 2.0

@dataclass(frozen=True)
class CorrectionModelConfig:
    """修正模型配置(不可变)"""
    model_type: str = "polynomial"
    polynomial_degree: int = 2
    regularization_alpha: float = 1.0
    min_training_points: int = 100
    validation_ratio: float = 0.2

class CurveFittingConfig:
    """曲线拟合配置统一访问类(单例模式)"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    @property
    def frequency(self) -> FrequencyNormalizationConfig:
        """频率归一化配置"""
        return self._frequency
    
    @property
    def pump_group(self) -> PumpGroupConfig:
        """泵组处理配置"""
        return self._pump_group
```

**使用示例**:

```python
config = CurveFittingConfig()
ref_freq = config.frequency.reference_freq  # 50.0
power_threshold = config.pump_group.power_diff_threshold  # 0.10
```

### 6.2 环境变量管理

#### 6.2.1 复用项目现有配置

**核心原则**:曲线拟合模块**复用项目全局环境变量**,不需要单独的.env文件

| 配置项 | 来源 | 说明 |
|-------|------|------|
| 数据库连接 | `configs/database.yaml` | 仅从YAML加载 |
| 日志配置 | `configs/logging.yaml` | 仅从YAML加载 |
| 系统配置 | `configs/system.yaml` | 仅从YAML加载 |

#### 6.2.2 使用app.core.config.loader_new

```python
from pathlib import Path
from app.core.config.loader_new import load_settings, Settings

# 加载全局配置(复用现有加载器)
settings: Settings = load_settings(Path("configs"))

# 数据库连接已在settings中
db_host = settings.database.host
db_port = settings.database.port
```

### 6.3 环境特定配置

#### 6.3.1 开发环境配置

**文件**: `configs/curve_fitting.dev.yaml`

```yaml
cache:
  enabled: true
  lru:
    max_size: 100        # 开发环境较小缓存
    max_memory_mb: 128

parallel:
  enabled: false        # 开发环境禁用并行
  max_workers: 1

monitoring:
  alerts:
    r_squared_warning: 0.85  # 开发环境宽松阈值
```

#### 6.3.2 生产环境配置

**文件**: `configs/curve_fitting.prod.yaml`

```yaml
cache:
  enabled: true
  lru:
    max_size: 1000       # 生产环境大缓存
    max_memory_mb: 512

parallel:
  enabled: true         # 生产环境启用并行
  max_workers: 8
  batch_size: 200

monitoring:
  alerts:
    r_squared_warning: 0.90  # 生产环境严格阈值
```

---

## 7. 数据库基础设施

### 7.1 表结构设计

#### 7.1.1 三表分离架构

**设计原则**:

1. **主表**(curve_fit_results):存储拟合结果元数据
2. **参数表**(curve_fit_params):存储拟合系数和方法参数
3. **指标表**(curve_fit_metrics):存储评估指标(R²、RMSE等)

**优势**:

- 避免JSONB字段过大
- 支持高效的参数查询
- 便于版本管理和回滚

#### 7.1.2 主表: curve_fit_results

**迁移脚本**: `migrations/048_create_curve_fit_results.sql`

**核心字段**:

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 主键 |
| device_id | INTEGER | FK, NULL | 设备ID(泵组曲线时为NULL) |
| curve_type | VARCHAR(50) | NOT NULL | 曲线类型(21种枚举) |
| version | VARCHAR(50) | NOT NULL | 版本号(YYYYMMDD_HHMMSS) |
| method_name | VARCHAR(100) | NOT NULL | 拟合方法ID |
| data_point_count | INTEGER | NULL | 数据点数 |
| physics_validation | JSONB | NULL | 物理约束验证结果 |
| curve_points | JSONB | NULL | 曲线特征点 |
| status | VARCHAR(20) | DEFAULT 'active' | 状态(active/archived/deprecated) |

**P2扩展字段**(泵组支持):

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| station_id | BIGINT | FK | 泵站ID |
| pump_combination | BIGINT[] | NULL | 泵组合(设备ID数组) |
| pump_count | INTEGER | NULL | 泵台数 |
| group_type | VARCHAR(30) | CHECK | 泵组类型 |
| correction_model | JSONB | NULL | 系统修正系数模型 |

**约束**:

```sql
CONSTRAINT chk_results_curve_type
    CHECK (curve_type IN (
        -- 单泵曲线类型
        'qh', 'qp', 'qeta', 'heta', 'peta', 'qnpsh',
        -- 并联泵组曲线类型
        'parallel_qh', 'parallel_qp', 'parallel_qeta',
        -- 台数优化曲线类型
        'n_q', 'n_p', 'n_eta',
        -- 分配曲线类型
        'load_distribution', 'flow_distribution', 'power_distribution',
        -- 控制策略曲线类型
        'start_stop_strategy', 'switching_timing', 'switching_process',
        -- 其他泵组曲线类型
        'optimal_region', 'specific_energy', 'coordination_control'
    ))

-- 单泵/泵组互斥约束
CONSTRAINT chk_results_pump_or_group
    CHECK (
        (device_id IS NOT NULL AND pump_combination IS NULL) OR
        (device_id IS NULL AND pump_combination IS NOT NULL)
    )
```

#### 7.1.3 参数表: curve_fit_params

**迁移脚本**: `migrations/049_create_curve_fit_params.sql`

**核心字段**:

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 主键 |
| result_id | INTEGER | FK | 关联curve_fit_results.id |
| param_category | VARCHAR(50) | NOT NULL | 参数类别 |
| param_key | VARCHAR(100) | NOT NULL | 参数键 |
| param_value | DOUBLE PRECISION | NULL | 数值型参数 |
| param_text | TEXT | NULL | 文本型参数 |

**参数类别**:

| param_category | 说明 | 示例参数 |
|---------------|------|----------|
| fit | 拟合系数 | a0, a1, a2, H0, K |
| method | 方法参数 | degree, lambda, n_estimators |
| correction | 修正系数 | alpha_intercept, alpha_coef_N |
| synthesis | 合成参数 | base_pump_id, synthesis_method |

#### 7.1.4 指标表: curve_fit_metrics

**迁移脚本**: `migrations/050_create_curve_fit_metrics.sql`

**核心字段**:

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 主键 |
| result_id | INTEGER | FK,UNIQUE | 关联curve_fit_results.id(1:1关系) |
| r_squared | DOUBLE PRECISION | CHECK(0≤r²≤1) | 决定系数 |
| rmse | DOUBLE PRECISION | NULL | 均方根误差 |
| mae | DOUBLE PRECISION | NULL | 平均绝对误差 |
| mape | DOUBLE PRECISION | NULL | 平均绝对百分比误差 |

### 7.2 迁移脚本设计

#### 7.2.1 迁移文件命名规范

```
migrations/
├── 048_create_curve_fit_results.sql
├── 049_create_curve_fit_params.sql
├── 050_create_curve_fit_metrics.sql
├── 051_create_curve_fit_views.sql
├── 052_create_learned_constraints.sql
├── 053_create_indexes.sql
└── migration_history_init.sql
```

#### 7.2.2 迁移并发执行保护

**问题**:多个实例同时启动时,可能并发执行数据库迁移

**解决方案**:使用PostgreSQL advisory lock确保迁移串行执行

**实现**:

```sql
-- 在每个迁移脚本开头添加advisory lock
BEGIN;

-- 获取迁移锁(锁ID:999999,迁移编号:48)
SELECT pg_advisory_xact_lock(999999, 48);

-- 检查迁移是否已执行
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM migration_history
        WHERE migration_id = '048_create_curve_fit_results'
    ) THEN
        RAISE NOTICE '迁移048已执行,跳过';
        RETURN;
    END IF;
END $$;

-- 执行迁移SQL
CREATE TABLE IF NOT EXISTS curve_fit_results (...);

-- 记录迁移历史
INSERT INTO migration_history (migration_id, executed_at)
VALUES ('048_create_curve_fit_results', NOW());

COMMIT;
```

**关键点**:

1. Advisory Lock确保同一时刻只有一个实例执行迁移
2. 幂等性检查避免重复执行
3. 事务保护,失败时自动回滚
4. 锁自动释放

#### 7.2.3 migration_history表

**迁移脚本**: `migrations/migration_history_init.sql`

```sql
CREATE TABLE IF NOT EXISTS migration_history (
    id SERIAL PRIMARY KEY,
    migration_id VARCHAR(100) UNIQUE NOT NULL,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    executed_by VARCHAR(100)
);
```

#### 7.2.4 回滚脚本

**文件**: `migrations/048_rollback.sql`

```sql
BEGIN;

DROP TABLE IF EXISTS curve_fit_metrics CASCADE;
DROP TABLE IF EXISTS curve_fit_params CASCADE;
DROP TABLE IF EXISTS curve_fit_results CASCADE;

DELETE FROM migration_history
WHERE migration_id IN (
    '048_create_curve_fit_results',
    '049_create_curve_fit_params',
    '050_create_curve_fit_metrics'
);

COMMIT;
```

### 7.3 索引设计

#### 7.3.1 P0基本索引

**迁移脚本**: `migrations/053_create_indexes.sql`

```sql
-- 按创建时间查询(查询最新版本)
CREATE INDEX IF NOT EXISTS idx_results_created_at
    ON curve_fit_results(created_at DESC);

-- 按状态查询(筛选活跃/归档曲线)
CREATE INDEX IF NOT EXISTS idx_results_status
    ON curve_fit_results(status);

-- 按方法名查询
CREATE INDEX IF NOT EXISTS idx_results_method_name
    ON curve_fit_results(method_name);

-- 复合索引(常见查询模式:device_id + curve_type + status)
CREATE INDEX IF NOT EXISTS idx_results_device_curve_status
    ON curve_fit_results(device_id, curve_type, status)
    WHERE device_id IS NOT NULL;
```

#### 7.3.2 P2扩展索引(泵组支持)

```sql
-- 泵站查询
CREATE INDEX IF NOT EXISTS idx_results_station
    ON curve_fit_results(station_id)
    WHERE station_id IS NOT NULL;

-- 泵组合查询(GIN索引支持数组包含查询)
CREATE INDEX IF NOT EXISTS idx_results_pump_combination
    ON curve_fit_results USING GIN(pump_combination)
    WHERE pump_combination IS NOT NULL;

-- 泵组类型查询
CREATE INDEX IF NOT EXISTS idx_results_group_type
    ON curve_fit_results(group_type)
    WHERE group_type IS NOT NULL;
```

### 7.4 视图设计

#### 7.4.1 最新版本视图

**迁移脚本**: `migrations/051_create_curve_fit_views.sql`

```sql
CREATE OR REPLACE VIEW curve_fit_latest AS
WITH ranked AS (
    SELECT
        r.*,
        m.r_squared,
        m.rmse,
        m.mae,
        m.mape,
        ROW_NUMBER() OVER (
            PARTITION BY r.device_id, r.curve_type
            ORDER BY r.created_at DESC
        ) as rn
    FROM curve_fit_results r
    LEFT JOIN curve_fit_metrics m ON r.id = m.result_id
    WHERE r.status = 'active'
)
SELECT * FROM ranked WHERE rn = 1;
```

#### 7.4.2 完整拟合结果视图

```sql
CREATE OR REPLACE VIEW v_curve_fit_full AS
SELECT
    r.*,
    m.r_squared,
    m.rmse,
    m.mae,
    m.mape,
    (
        SELECT jsonb_object_agg(p.param_key, p.param_value)
        FROM curve_fit_params p
        WHERE p.result_id = r.id AND p.param_category = 'fit'
    ) AS fit_params,
    (
        SELECT jsonb_object_agg(p.param_key, COALESCE(p.param_value::text, p.param_text))
        FROM curve_fit_params p
        WHERE p.result_id = r.id AND p.param_category = 'method'
    ) AS method_params
FROM curve_fit_results r
LEFT JOIN curve_fit_metrics m ON r.id = m.result_id;
```

### 7.5 数据库连接管理

**核心原则**:必须使用项目现有连接池,禁止重复造轮子

**使用方式**:

```python
from app.adapters.db.pool import get_db_session

# 所有数据库操作必须通过连接池
with get_db_session() as session:
    result = session.execute(query)
```

**禁止事项**:

```python
# ❌ 禁止:创建新的数据库连接
import psycopg2
conn = psycopg2.connect(...)

# ❌ 禁止:绕过连接池
from sqlalchemy import create_engine
engine = create_engine(...)
```

---

## 8. CLI命令行接口

### 8.1 CLI设计原则

**目标**:提供简洁易用的命令行工具,支持单设备拟合、批量处理、结果查询和可视化

**技术栈**:
- 基础框架:typer(项目已使用)
- 命令组织:按功能分组(fit/query/plot/report)
- 输出格式:JSON/表格/明细日志

### 8.2 命令结构

```bash
# 主命令入口
python -m app.cli curve-fitting [COMMAND] [OPTIONS]

# 命令组
curve-fitting fit           # 拟合命令组
curve-fitting query         # 查询命令组
curve-fitting plot          # 可视化命令组
curve-fitting report        # 报告生成命令组
curve-fitting batch         # 批量处理命令组
```

### 8.3 拟合命令(fit)

#### 8.3.1 单设备拟合

```bash
# 基本用法
python -m app.cli curve-fitting fit single \
    --device-id 101 \
    --curve-type qh \
    --start-date 2025-12-01 \
    --end-date 2025-12-11

# 指定拟合方法
python -m app.cli curve-fitting fit single \
    --device-id 101 \
    --curve-type qh \
    --method math_polynomial_2

# 指定输出路径
python -m app.cli curve-fitting fit single \
    --device-id 101 \
    --curve-type qh \
    --output-dir ./results/
```

**参数说明**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|:----:|--------|------|
| --device-id | INT | ✓ | - | 设备ID |
| --curve-type | STR | ✓ | - | 曲线类型(qh/qp/qeta) |
| --start-date | DATE | ✗ | 30天前 | 开始日期 |
| --end-date | DATE | ✗ | 今天 | 结束日期 |
| --method | STR | ✗ | 自动选择 | 拟合方法ID |
| --output-dir | PATH | ✗ | ./output | 输出目录 |
| --verbose | FLAG | ✗ | False | 详细日志 |

#### 8.3.2 批量拟合

```bash
# 按设备列表
```bash
python -m app.cli curve-fitting fit batch \
    --device-ids 101,102,103 \
    --curve-types qh,qp \
    --parallel --max-workers 4

# 按泵站拟合所有设备
python -m app.cli curve-fitting fit batch \
    --station-id 1 \
    --curve-types qh,qp,qeta
```

### 8.4 查询命令(query)

#### 8.4.1 查询最新结果

```bash
# 查询单个设备的最新曲线
python -m app.cli curve-fitting query latest \
    --device-id 101 \
    --curve-type qh \
    --format table

# 查询多个设备
python -m app.cli curve-fitting query latest \
    --device-ids 101,102,103 \
    --format json > results.json
```

**输出格式**:

| 格式 | 说明 | 适用场景 |
|------|------|----------|
| table | 表格形式 | 命令行查看 |
| json | JSON格式 | 程序处理 |
| csv | CSV格式 | Excel导入 |

#### 8.4.2 查询历史版本

```bash
python -m app.cli curve-fitting query history \
    --device-id 101 \
    --curve-type qh \
    --limit 10
```

### 8.5 可视化命令(plot)

```bash
# 生成8K高清曲线图
python -m app.cli curve-fitting plot curve \
    --device-id 101 \
    --curve-type qh \
    --output curve.png

# 生成残差分析图
python -m app.cli curve-fitting plot residuals \
    --device-id 101 \
    --curve-type qh \
    --output residuals.png

# 生成所有5种图表
python -m app.cli curve-fitting plot all \
    --device-id 101 \
    --curve-type qh \
    --output-dir ./plots/
```

### 8.6 报告生成命令(report)

```bash
# 生成Markdown报告
python -m app.cli curve-fitting report generate \
    --device-id 101 \
    --curve-type qh \
    --output report.md

# 生成PDF报告(P2可选)
python -m app.cli curve-fitting report generate \
    --device-id 101 \
    --curve-type qh \
    --output report.pdf \
    --format pdf
```

### 8.7 CLI实现架构

**目录结构**:

```
app/cli/
├── __init__.py
├── main.py                  # CLI主入口
└── characteristic_curves/
    ├── __init__.py
    ├── fit_commands.py      # 拟合命令
    ├── query_commands.py    # 查询命令
    ├── plot_commands.py     # 可视化命令
    └── report_commands.py   # 报告命令
```

**示例代码** (fit_commands.py):

```python
import typer
from typing import Optional
from datetime import datetime, timedelta

app = typer.Typer()

@app.command("single")
def fit_single_device(
    device_id: int = typer.Option(..., help="设备ID"),
    curve_type: str = typer.Option(..., help="曲线类型"),
    start_date: Optional[datetime] = typer.Option(None),
    end_date: Optional[datetime] = typer.Option(None),
    method: Optional[str] = typer.Option(None, help="拟合方法ID"),
    output_dir: str = typer.Option("./output"),
    verbose: bool = typer.Option(False, "--verbose", "-v")
):
    """单设备曲线拟合"""
    # 实现逻辑
    pass
```

---

## 9. 部署与运维

### 9.1 Docker部署

#### 9.1.1 docker-compose.yml

```yaml
services:
  pump-station-app:
    image: pump-station:latest
    volumes:
      - ./configs:/app/configs:ro  # 只读挂载配置
      - ./logs:/app/logs           # 日志目录
      - ./output:/app/output       # 输出目录
    # 不需要设置数据库相关环境变量
    # 配置从 configs/*.yaml 加载
```

#### 9.1.2 环境特定配置映射

```yaml
services:
  # 开发环境
  pump-station-dev:
    volumes:
      - ./configs/curve_fitting.dev.yaml:/app/configs/curve_fitting.yaml:ro

  # 生产环境
  pump-station-prod:
    volumes:
      - ./configs/curve_fitting.prod.yaml:/app/configs/curve_fitting.yaml:ro
```

### 9.2 日志配置

#### 9.2.1 复用项目日志系统

**核心原则**:曲线拟合模块**复用项目现有日志系统**

**使用方式**:

```python
from app.core.logging.logger import get_logger

logger = get_logger(__name__)

# 日志输出(中文)
logger.info("开始拟合设备{device_id}的{curve_type}曲线")
logger.warning("数据点数不足,仅{count}个点")
logger.error("拟合失败:{error}", exc_info=True)
```

#### 9.2.2 日志级别使用规范

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| DEBUG | 详细执行流程 | “读取数据库配置” |
| INFO | 关键节点 | “开始拟合”、“拟合成功” |
| WARNING | 潜在问题 | “数据点数不足”、“R²较低” |
| ERROR | 可恢复错误 | “拟合失败,尝试下一个方法” |
| CRITICAL | 不可恢复错误 | “数据库连接失败” |

### 9.3 健康检查

#### 9.3.1 健康检查端点

**位置**: `app/api/health.py`(项目已有)

**检查项**:

1. 数据库连接状态
2. 缓存服务状态
3. 表存在性检查(curve_fit_results)

```python
@app.get("/health/curve-fitting")
async def check_curve_fitting_health():
    checks = {
        "database": await check_database(),
        "tables": await check_tables_exist(),
        "cache": check_cache_status()
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={"status": "healthy" if all_healthy else "unhealthy", "checks": checks}
    )
```

### 9.4 性能监控

#### 9.4.1 关键指标

| 指标 | 阈值 | 监控方式 |
|------|------|----------|
| 拟合耗时 | <60秒 | 日志记录 |
| 数据库查询耗时 | <5秒 | 日志记录 |
| 内存占用 | <2GB | 系统监控 |
| R² | >0.90 | 拟合结果验证 |

#### 9.4.2 性能日志记录

```python
import time
from app.core.logging.logger import get_logger

logger = get_logger(__name__)

def fit_with_timing(device_id, curve_type):
    start_time = time.time()
    
    # 拟合逻辑
    result = perform_fitting(...)
    
    elapsed = time.time() - start_time
    logger.info(
        f"拟合完成: device_id={device_id}, curve_type={curve_type}, "
        f"elapsed={elapsed:.2f}s, r_squared={result.r_squared:.4f}"
    )
    
    if elapsed > 60:
        logger.warning(f"拟合耗时过长: {elapsed:.2f}s > 60s")
    
    return result
```

---

## 10. 测试体系

### 10.1 测试策略

#### 10.1.1 测试金字塔

```
        ┌─────────────────┐
        │   E2E测试(5%)   │  <- 完整流程验证
        └─────────────────┘
      ┌─────────────────────────┐
      │   集成测试(15%)      │  <- 模块间集成
      └─────────────────────────┘
  ┌─────────────────────────────────┐
  │      单元测试(80%)           │  <- 单个函数/类
  └─────────────────────────────────┘
```

#### 10.1.2 测试覆盖率目标

| 模块 | 目标覆盖率 | 优先级 |
|------|:--------:|:----:|
| core/核心模块 | ≥95% | P0 |
| curves/曲线模块 | ≥90% | P0 |
| methods/拟合方法 | ≥90% | P0 |
| constraints/约束层 | ≥90% | P0 |
| pipeline/管道层 | ≥85% | P0 |
| preprocessing/预处理 | ≥85% | P1 |
| shared/共用层 | ≥80% | P1 |

### 10.2 单元测试

#### 10.2.1 测试框架

**技术栈**:
- pytest(项目已使用)
- pytest-cov(覆盖率统计)
- pytest-mock(mock工具)

**目录结构**:

```
tests/
├── __init__.py
├── conftest.py                    # 共享fixture
└── services/
    └── characteristic_curves/
        ├── test_core/
        │   ├── test_data_structures.py
        │   ├── test_exceptions.py
        │   └── test_enums.py
        ├── test_curves/
        │   ├── test_qh_curve.py
        │   ├── test_qp_curve.py
        │   └── test_qeta_curve.py
        ├── test_methods/
        │   └── test_polynomial.py
        ├── test_constraints/
        │   └── test_physics_validator.py
        └── test_pipeline/
            └── test_curve_fitting_pipeline.py
```

#### 10.2.2 测试用例示例

**test_data_structures.py**:

```python
import pytest
from app.services.characteristic_curves.core.data_structures import FitResult

def test_fit_result_creation():
    """Test FitResult 创建"""
    result = FitResult(
        device_id=101,
        curve_type="qh",
        method_name="math_polynomial_2",
        coefficients=[120.5, -0.0015, 0.000002],
        r_squared=0.9856,
        rmse=0.234
    )
    
    assert result.device_id == 101
    assert result.curve_type == "qh"
    assert result.r_squared > 0.98

def test_fit_result_validation():
    """Test FitResult 校验"""
    with pytest.raises(ValueError):
        FitResult(
            device_id=101,
            curve_type="invalid_type",  # 无效类型
            method_name="test"
        )
```

### 10.3 集成测试

#### 10.3.1 测试场景

**场景1:完整的拟合流程**

```python
def test_complete_fitting_pipeline(db_session):
    """测试完整的拟合流程"""
    # 1. 准备测试数据
    device_id = 101
    curve_type = "qh"
    
    # 2. 执行拟合
    pipeline = CurveFittingPipeline(...)
    result = pipeline.run(device_id, curve_type)
    
    # 3. 验证结果
    assert result.status == "success"
    assert result.r_squared > 0.90
    
    # 4. 验证数据库存储
    stored = db_session.query(CurveFitResult).filter_by(
        device_id=device_id,
        curve_type=curve_type
    ).first()
    
    assert stored is not None
    assert stored.status == "active"
```

#### 10.3.2 Mock策略

**原则**:
- Mock外部依赖(数据库、API)
- 不要Mock项目内部代码

```python
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_db_session(mocker):
    """Mock数据库会话"""
    session = MagicMock()
    mocker.patch('app.adapters.db.pool.get_db_session', return_value=session)
    return session
```

### 10.4 端到端(E2E)测试

#### 10.4.1 测试场景

**场景1:单设备单曲线拟合**

```python
def test_e2e_single_device_fitting():
    """端到端测试:单设备拟合"""
    # 使用真实数据库和测试数据
    device_id = 101
    curve_type = "qh"
    
    # 执行完整流程
    result = fit_curve(device_id, curve_type)
    
    # 验证结果
    assert result.status == "success"
    assert result.r_squared > 0.90
    
    # 验证输出文件
    output_dir = Path(f"./output/{curve_type}/{result.version}")
    assert (output_dir / "curve.png").exists()
    assert (output_dir / "report.md").exists()
```

### 10.5 性能测试

#### 10.5.1 基准性能指标

| 场景 | 数据规模 | 目标时间 |
|------|----------|----------|
| 单设备拟合 | 1000点 | <10秒 |
| 批量拟合(10设备) | 1000点/设备 | <60秒 |
| 数据库查询 | - | <1秒 |
| 8K图片生成 | - | <5秒 |

#### 10.5.2 性能测试代码

```python
import pytest
import time

@pytest.mark.performance
def test_fitting_performance():
    """测试拟合性能"""
    device_id = 101
    curve_type = "qh"
    
    start_time = time.time()
    result = fit_curve(device_id, curve_type)
    elapsed = time.time() - start_time
    
    assert elapsed < 10.0, f"拟合耗时{elapsed:.2f}s > 10s"
```

### 10.6 验收标准

#### 10.6.1 功能验收

- [ ] 单设备拟合成功率 ≥ 95%
- [ ] 拟合精度(R²) ≥ 0.90
- [ ] 物理约束验证通过率 = 100%
- [ ] 数据库存储成功率 = 100%
- [ ] 8K图片生成成功率 ≥ 95%

#### 10.6.2 性能验收

- [ ] 单设备拟合耗时 < 10秒
- [ ] 批量拟合(10设备)耗时 < 60秒
- [ ] 数据库查询耗时 < 1秒
- [ ] 内存占用 < 2GB

#### 10.6.3 质量验收

- [ ] 单元测试覆盖率 ≥ 90%
- [ ] 集成测试通过率 = 100%
- [ ] E2E测试通过率 = 100%
- [ ] 代码审查无重大问题
- [ ] 文档完整性 = 100%

---

## 11. 实施检查清单

### 6.1 代码清理检查清单

**废弃代码删除**:

- [ ] 1.1 迁移models.py中的数据结构到core.data_structures
- [ ] 1.2 更新所有引用models.py的导入语句
- [ ] 1.3 删除models.py文件
- [ ] 1.4 验证无models.py残留引用

**占位代码删除**:

- [ ] 2.1 删除_stage_scenario_detect占位处理器
- [ ] 2.2 删除_stage_steady_state_detect占位处理器(如为占位)
- [ ] 2.3 删除_stage_freq_normalize占位处理器(如为占位)
- [ ] 2.4 删除_stage_historical_eval占位处理器(如为占位)
- [ ] 2.5 从_stage_handlers字典移除对应条目
- [ ] 2.6 删除对应的无效测试

**P2代码删除**:

- [ ] 3.1 删除pump_group/整个目录
- [ ] 3.2 删除pipeline中的P2阶段处理器
- [ ] 3.3 删除P2相关数据结构(如已实现)
- [ ] 3.4 删除P2相关测试

**冗余代码清理**:

- [ ] 4.1 检查shared/目录,删除未在文档定义的模块
- [ ] 4.2 删除未被调用的工具函数
- [ ] 4.3 删除重复实现的功能
- [ ] 4.4 清理未使用的导入语句

**验证**:

- [ ] 5.1 运行静态分析工具检查死代码
- [ ] 5.2 确认无DEPRECATED标记
- [ ] 5.3 确认无TODO占位符
- [ ] 5.4 测试套件全部通过

### 6.2 核心模块补全检查清单

**用户要求**: 除拟合方法外,所有模块必须完整实现

**core/模块** (必须实现):

- [ ] 1.1 实现core/data_structures.py(8个数据结构,包括P2)
- [ ] 1.2 实现core/exceptions.py(6个异常类,包括P2)
- [ ] 1.3 实现core/enums.py(所有枚举类型)
- [ ] 1.4 编写core/模块单元测试
- [ ] 1.5 删除所有默认值
- [ ] 1.6 删除所有硬编码

**preprocessing/独立模块** (必须全部实现):

- [ ] 2.1 实现preprocessing/scenario_detector.py(场景识别,9种场景)
- [ ] 2.2 实现preprocessing/device_type_detector.py(设备类型检测)
- [ ] 2.3 实现preprocessing/steady_state_detector.py(稳态识别)
- [ ] 2.4 实现preprocessing/frequency_normalizer.py(频率归一化)
- [ ] 2.5 编写所有预处理模块测试

**shared/共用模块** (必须全部实现):

- [ ] 3.1 实现shared/data_extractor.py(从fact_measurements提取数据):
  - [ ] 3.1.1 实现通用SQL查询模板(适用于QH/QP/QEta)
  - [ ] 3.1.2 实现数据点数验证(≥100个,推荐≥500个,理想≥5000个)
  - [ ] 3.1.3 实现时间跨度验证(≥1天,推荐≥7天,理想≥30天)
  - [ ] 3.1.4 实现流量覆盖范围验证(必须:Q_max≥0.2×Q_rated,推荐:10%-120%,理想:0%-120%)
  - [ ] 3.1.5 实现数据完整性验证(缺失率<5%,推荐<2%)
  - [ ] 3.1.6 实现数据准确性验证(3σ规则,异常值率<3%,推荐<1%)
  - [ ] 3.1.7 实现数据质量报告返回(total_points, time_span_days, Q_range, missing_rate, outlier_rate)
  - [ ] 3.1.8 使用app.adapters.db.pool.get_db_session()获取连接
  - [ ] 3.1.9 数据不满足最小要求时抛出DataExtractionError
  - [ ] 3.1.10 所有阈值从配置文件读取,禁止硬编码
  - [ ] 3.1.11 记录数据质量指标到日志
- [ ] 3.2 实现shared/result_storage.py(三表分离存储):
  - [ ] 3.2.1 实现事务保护的三表写入(curve_fit_results, curve_fit_params, curve_fit_metrics)
  - [ ] 3.2.2 调用CurvePointGenerator生成curve_points曲线特征点(JSONB格式)
  - [ ] 3.2.3 实现版本管理(version格式YYYYMMDD_HHMMSS,status:active/archived/deprecated)
  - [ ] 3.2.4 实现版本更新规则(新版本保存时自动将前一个active改为archived)
  - [ ] 3.2.5 实现版本回滚功能
  - [ ] 3.2.6 实现软删除功能(修改status为deprecated)
  - [ ] 3.2.7 使用app.adapters.db.pool.get_db_session()获取连接
  - [ ] 3.2.8 写入失败时抛出ResultStorageError(异常码CF011)
- [ ] 3.3 实现shared/cache_manager.py(缓存管理)
- [ ] 3.4 实现shared/time_window_splitter.py(时间窗口划分)
- [ ] 3.5 实现shared/batch_processor.py(批处理)
- [ ] 3.6 实现shared/parameter_optimizer.py(参数优化)
- [ ] 3.7 实现shared/historical_data_evaluator.py(历史评估)
- [ ] 3.8 实现shared/time_window_validator.py(时间窗口验证)
- [ ] 3.9 实现shared/curve_point_generator.py(曲线特征点生成):
  - [ ] 3.9.1 实现均匀采样算法(numpy.linspace)
  - [ ] 3.9.2 采样点数从配置读取(默认20个)
  - [ ] 3.9.3 返回JSONB格式数据(sample_count, q_values, y_values, sampling_method, q_range)
  - [ ] 3.9.4 返回的list必须是Python原生类型,不能是numpy数组
- [ ] 3.10 编写所有共用层模块测试

**output/输出模块** (必须实现监控、可视化、报告功能):

- [ ] 3.11 实现output/high_res_plotter.py(8K高分辨率可视化):
  - [ ] 3.11.1 配置8K分辨率(7680×4320, DPI=300, matplotlib Agg后端)
  - [ ] 3.11.2 配置中文字体(SimHei,回退Microsoft YaHei)
  - [ ] 3.11.3 配置中文标签映射(qh:流量-扬程, qp:流量-功率, qeta:流量-效率)
  - [ ] 3.11.4 配置颜色方案(从常量定义读取,禁止硬编码)
  - [ ] 3.11.5 实现plot_curve()主曲线图(P0必须):
    - [ ] 3.11.5.1 原始数据散点(蓝色,alpha=0.5)
    - [ ] 3.11.5.2 拟合曲线(红色实线)
    - [ ] 3.11.5.3 95%置信带(浅红色阴影)
    - [ ] 3.11.5.4 统计信息框(右上角:R²,RMSE,数据点数,拟合方法)
    - [ ] 3.11.5.5 中文标题和坐标轴标签
    - [ ] 3.11.5.6 浅灰色网格线
  - [ ] 3.11.6 实现plot_residuals()残差分析图(P1推荐):
    - [ ] 3.11.6.1 2×2子图布局
    - [ ] 3.11.6.2 左上:残差vs预测值+零线
    - [ ] 3.11.6.3 右上:残差vs流量+零线
    - [ ] 3.11.6.4 左下:残差直方图+正态分布曲线
    - [ ] 3.11.6.5 右下:Q-Q图(理论分位数vs实际分位数)
  - [ ] 3.11.7 实现plot_confidence_band()置信区间图(P2可选)
  - [ ] 3.11.8 实现plot_sensitivity()敏感性分析图(P2可选)
  - [ ] 3.11.9 实现plot_comparison()版本对比图(P2可选)
  - [ ] 3.11.10 图片保存后必须关闭Figure释放内存(plt.close(fig))
  - [ ] 3.11.11 生成失败时抛出PlotGenerationError(异常码CF012)
- [ ] 3.12 实现output/output_path_manager.py(路径管理):
  - [ ] 3.12.1 实现三层目录结构(base_path/曲线类型中文名/版本号/)
  - [ ] 3.12.2 实现get_version_dir()获取版本目录
  - [ ] 3.12.3 实现get_image_path()获取图片路径
  - [ ] 3.12.4 实现get_report_path()获取报告路径
  - [ ] 3.12.5 实现ensure_dir_exists()自动创建目录
  - [ ] 3.12.6 使用pathlib.Path确保跨平台兼容
  - [ ] 3.12.7 base_path从配置读取,禁止硬编码
- [ ] 3.13 实现output/report_generator.py(Markdown报告生成):
  - [ ] 3.13.1 实现模块1:报告摘要(P0必须)
  - [ ] 3.13.2 实现模块2:拟合方法说明(P0必须)
  - [ ] 3.13.3 实现模块3:参数估计结果(P0必须)
  - [ ] 3.13.4 实现模块4:统计检验指标(P0必须)
  - [ ] 3.13.5 实现模块6:可视化图表(相对路径嵌入,P0必须)
  - [ ] 3.13.6 实现模垗11:物理约束验证(P0必须)
  - [ ] 3.13.7 实现模块5:残差分析(P1推荐)
  - [ ] 3.13.8 实现模块7:置信区间分析(P1推荐)
  - [ ] 3.13.9 实现模块9:分段性能评估(P1推荐)
  - [ ] 3.13.10 实现模垗12:运行建议(P1推荐)
  - [ ] 3.13.11 实现模块8:参数敏感性分析(P2可选)
  - [ ] 3.13.12 实现模垗10:历史对比分析(P2可选)
  - [ ] 3.13.13 实现质量评级(根据R²和MAPE返回星级)
  - [ ] 3.13.14 报告文件编码UTF-8
  - [ ] 3.13.15 图片路径使用相对路径
  - [ ] 3.13.16 数学公式使用LaTeX格式
  - [ ] 3.13.17 生成失败时抛出ReportGenerationError(异常码CF013)
  - [ ] 3.13.18 实现TemplateManager集成(P2可选,使用Jinja2模板引擎)
- [ ] 3.14 实现output/template_manager.py(模板管理器,P2可选):
  - [ ] 3.14.1 实现load_template()加载Jinja2模板
  - [ ] 3.14.2 实现render()渲染模板生成Markdown
  - [ ] 3.14.3 实现get_available_templates()获取可用模板列表
  - [ ] 3.14.4 配置Jinja2引擎(autoescape=False, trim_blocks=True, lstrip_blocks=True)
  - [ ] 3.14.5 支持3种内置模板(report/summary/comparison)
  - [ ] 3.14.6 template_dir从配置读取,禁止硬编码
  - [ ] 3.14.7 模板不存在时抛出TemplateNotFoundError
  - [ ] 3.14.8 渲染失败时抛出TemplateRenderError
  - [ ] 3.14.9 模板文件编码UTF-8

**visualization/可视化扩展模块** (P2可选实现):

- [ ] 3.15 实现visualization/deviation_plotter.py(偏差绘图器,P2可选):
  - [ ] 3.15.1 实现plot_distribution()绘制偏差分布直方图
  - [ ] 3.15.2 实现plot_scatter()绘制偏差散点图
  - [ ] 3.15.3 实现plot_trend()绘制偏差趋势图
  - [ ] 3.15.4 支持3种偏差定义(绝对偏差、相对偏差、百分比偏差)
  - [ ] 3.15.5 标注统计信息(均值、标准差、最大偏差、最小偏差、中位数)
  - [ ] 3.15.6 使用与HighResPlotter相同的配置(8K分辨率、中文标签)
  - [ ] 3.15.7 图片生成后必须关闭Figure
  - [ ] 3.15.8 生成失败时抛出PlotGenerationError
- [ ] 3.16 实现visualization/comparison_plotter.py(对比绘图器,P2可选):
  - [ ] 3.16.1 实现plot_version_comparison()绘制版本对比图
  - [ ] 3.16.2 实现plot_method_comparison()绘制方法对比图
  - [ ] 3.16.3 实现plot_device_comparison()绘制设备对比图
  - [ ] 3.16.4 支持最多5条曲线同时对比
  - [ ] 3.16.5 使用5种颜色区分(绿、紫、橙、青、棕,从配置读取)
  - [ ] 3.16.6 标注关键差异点
  - [ ] 3.16.7 生成对比统计表格
  - [ ] 3.16.8 从数据库读取对比数据(curve_fit_results表)
  - [ ] 3.16.9 生成失败时抛出PlotGenerationError

**alerting/告警规则配置系统** (P2可选实现):

- [ ] 3.17 实现alerting/alert_rule_manager.py(告警规则管理器,P2可选):
  - [ ] 3.17.1 从YAML配置加载告警规则(禁止硬编码)
  - [ ] 3.17.2 实现6种核心告警规则:
    - [ ] 3.17.2.1 high_error_rate(错误率>5%,5分钟窗口,critical级别)
    - [ ] 3.17.2.2 fitting_failure_rate(拟合失败率>10%,15分钟窗口,high级别)
    - [ ] 3.17.2.3 database_connection_error(DB连接失败,1分钟窗口,critical级别)
    - [ ] 3.17.2.4 slow_fitting_performance(拟合耗时>30秒,10分钟窗口,medium级别)
    - [ ] 3.17.2.5 low_r_squared(R²<0.9,持续3次,medium级别)
    - [ ] 3.17.2.6 insufficient_data_points(数据点数<100,low级别)
  - [ ] 3.17.3 实现4级告警分级(critical/high/medium/low)
  - [ ] 3.17.4 实现告警触发逻辑(指标采集、阈值比较、时间窗口聚合、状态管理)
  - [ ] 3.17.5 实现告警抑制规则(5分钟去重、维护窗口、告警合并)
  - [ ] 3.17.6 实现3种通知渠道配置(email/sms/webhook)
  - [ ] 3.17.7 实现告警历史记录(持久化到alert_history表)
  - [ ] 3.17.8 实现告警查询接口(按时间、级别、规则查询)
  - [ ] 3.17.9 YAML配置文件必须包含rules/channels/suppression三部分
  - [ ] 3.17.10 配置加载失败时抛出ConfigurationError

**monitoring/监控模块** (必须实现退化和漂移棅测):

- [ ] 3.18 实现monitoring/degradation_detector.py(退化检测):
  - [ ] 3.14.1 实现detect()检测精度退化
  - [ ] 3.14.2 实现R²下降检测(阈值>2%)
  - [ ] 3.14.3 实现RMSE增加检测(阈值>10%)
  - [ ] 3.14.4 实现退化趋势检验(scipy.stats.linregress,p<0.05)
  - [ ] 3.14.5 实现calculate_degradation_rate()计算退化速率
  - [ ] 3.14.6 检测窗口天数从配置读取(默认30天)
  - [ ] 3.14.7 检测到退化记录WARNING日志
  - [ ] 3.14.8 返回结果包含具体建议
- [ ] 3.15 实现monitoring/drift_detector.py(漂移检测):
  - [ ] 3.15.1 实现detect()检测曲线漂移
  - [ ] 3.15.2 实现参数变化计算(阈值>5%)
  - [ ] 3.15.3 实现形状差异计算(scipy.integrate.simpson,阈值>10%)
  - [ ] 3.15.4 实现漂移类型判定(gradual_drift/sudden_drift/no_drift)
  - [ ] 3.15.5 实现compare_curves()对比两个版本曲线
  - [ ] 3.15.6 实现identify_drift_cause()根据参数变化特征智能推断漂移原因
  - [ ] 3.15.7 检测到漂移记录WARNING日志
- [ ] 3.16 实现monitoring/auto_refit_trigger.py(自动重拟合触发):
  - [ ] 3.16.1 实现check_and_trigger()综合退化和漂移结果决定重拟合
  - [ ] 3.16.2 实现触发条件判断(3种情况)
  - [ ] 3.16.3 实现手动确认模式(auto_refit=False)
  - [ ] 3.16.4 实现自动执行模式(auto_refit=True,调用CurveFittingPipeline.run())
  - [ ] 3.16.5 实现register_callback()回调机制(支持多个回调)
  - [ ] 3.16.6 实现get_refit_history()获取重拟合历史
  - [ ] 3.16.7 重拟合历史持久化到数据库表curve_refit_history
  - [ ] 3.16.8 触发重拟合记录INFO日志

**alerting/告警规则配置系统** (P2可选实现):

- [ ] 3.17 实现alerting/alert_rule_manager.py(告警规则管理器,P2可选):
  - [ ] 3.17.1 从YAML配置加载告警规则(禁止硬编码)
  - [ ] 3.17.2 实现6种核心告警规则:
    - [ ] 3.17.2.1 high_error_rate(错误率>5%,5分钟窗口,critical级别)
    - [ ] 3.17.2.2 fitting_failure_rate(拟合失败率>10%,15分钟窗口,high级别)
    - [ ] 3.17.2.3 database_connection_error(DB连接失败,1分钟窗口,critical级别)
    - [ ] 3.17.2.4 slow_fitting_performance(拟合耗时>30秒,10分钟窗口,medium级别)
    - [ ] 3.17.2.5 low_r_squared(R²<0.9,持续3次,medium级别)
    - [ ] 3.17.2.6 insufficient_data_points(数据点数<100,low级别)
  - [ ] 3.17.3 实现4级告警分级:
    - [ ] 3.17.3.1 critical(严重,影响核心功能,立即处理)
    - [ ] 3.17.3.2 high(高,影响部分功能,1小时内处理)
    - [ ] 3.17.3.3 medium(中等,性能下降,4小时内处理)
    - [ ] 3.17.3.4 low(低,提示性告警,1天内处理)
  - [ ] 3.17.4 实现告警触发逻辑:
    - [ ] 3.17.4.1 指标采集(error_rate, fitting_duration等)
    - [ ] 3.17.4.2 阈值比较(超过threshold触发)
    - [ ] 3.17.4.3 时间窗口聚合(window统计)
    - [ ] 3.17.4.4 告警状态管理(firing/resolved)
  - [ ] 3.17.5 实现告警抑制规则:
    - [ ] 3.17.5.1 去重机制(5分钟窗口内相同告警只发送一次)
    - [ ] 3.17.5.2 维护窗口(配置的时间段内不发送告警)
    - [ ] 3.17.5.3 告警合并(同类告警聚合为一条)
  - [ ] 3.17.6 实现3种通知渠道配置:
    - [ ] 3.17.6.1 email(SMTP配置,支持多收件人)
    - [ ] 3.17.6.2 sms(短信网关配置,紧急告警使用)
    - [ ] 3.17.6.3 webhook(企业微信/钉钉/Slack集成)
  - [ ] 3.17.7 实现告警历史记录(持久化到alert_history表)
  - [ ] 3.17.8 实现告警查询接口(按时间、级别、规则查询)
  - [ ] 3.17.9 YAML配置示例:
```yaml
alerting:
  rules:
    - name: "high_error_rate"
      metric: "error_rate"
      threshold: 0.05  # 5%
      window: 300      # 5分钟
      severity: "critical"
      channels: ["email", "sms", "webhook"]
      
    - name: "fitting_failure_rate"
      metric: "fitting_failure_rate"
      threshold: 0.10  # 10%
      window: 900      # 15分钟
      severity: "high"
      channels: ["email", "webhook"]

  channels:
    email:
      smtp_host: "smtp.example.com"
      smtp_port: 587
      from: "alerts@example.com"
      to: ["admin@example.com", "ops@example.com"]
      
    webhook:
      url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
      timeout: 5
      
  suppression:
    dedup_window: 300      # 5分钟去重
    maintenance_windows:
      - start: "02:00"
        end: "04:00"
        days: ["Saturday", "Sunday"]
```

**constraints/模块** (必须全部实现):

- [ ] 4.1 实现constraints/monotonicity.py
- [ ] 4.2 实现constraints/boundary.py
- [ ] 4.3 实现constraints/physics_validator.py
- [ ] 4.4 实现constraints/constraint_calculator.py
- [ ] 4.5 实现constraints/constraint_learner.py
- [ ] 4.6 实现constraints/constraint_parameter_manager.py
- [ ] 4.7 编写所有约束层模块测试

**curves/曲线类** (必须全部实现,包括子模块):

- [ ] 5.1 实现curves/base_curve.py(曲线基类)
- [ ] 5.2 实现curves/qh_curve.py及其7个子模块(Q-H曲线,单调递减):
  - [ ] 5.2.1 QHDataExtractor(提取pump_flow_rate和pump_head,HAVING Q IS NOT NULL AND H IS NOT NULL)
  - [ ] 5.2.2 QHPreprocessor(删除Q<0或H<0,删除异常值,运行点筛选)
  - [ ] 5.2.3 QHConstraints(计算H0≈1.2×H_rated, Q_max, K, monotonicity='decreasing')
  - [ ] 5.2.4 QHNormalizer(Q_norm=Q/Q_rated, H_norm=H/H_rated)
  - [ ] 5.2.5 QHMethodSelector(根据数据质量选择physics_pump_char, math_poly_2等)
  - [ ] 5.2.6 QHCurveFitter(顺序执行方法,计算R²、RMSE、MAE)
  - [ ] 5.2.7 QHValidator(验证dH/dQ<0全范围,d²H/dQ²>0,H(0)≈H0,H(Q_max)>0)
- [ ] 5.3 实现curves/qp_curve.py及其7个子模块(Q-P曲线,单调递增):
  - [ ] 5.3.1 QPDataExtractor(提取pump_flow_rate和pump_active_power,HAVING Q IS NOT NULL AND P IS NOT NULL)
  - [ ] 5.3.2 QPPreprocessor(删除Q<0或P<0,删除异常值)
  - [ ] 5.3.3 QPConstraints(计算P0≈0.15×P_rated, P_max≤1.2×P_rated, monotonicity='increasing')
  - [ ] 5.3.4 QPNormalizer(Q_norm=Q/Q_rated, P_norm=P/P_rated)
  - [ ] 5.3.5 QPMethodSelector(根据数据选择physics_power_eq, math_poly_2等)
  - [ ] 5.3.6 QPCurveFitter(顺序执行方法)
  - [ ] 5.3.7 QPValidator(验证dP/dQ>0,d²P/dQ²<0,P≈ρgQH/η能量守恒)
- [ ] 5.4 实现curves/qeta_curve.py及其7个子模块(Q-η曲线,单峰):
  - [ ] 5.4.1 QEtaDataExtractor(提取pump_flow_rate和pump_efficiency,eta需除以100转为小数,HAVING Q IS NOT NULL AND eta IS NOT NULL)
  - [ ] 5.4.2 QEtaPreprocessor(删除Q<0或η<0或η>1,删除异常值)
  - [ ] 5.4.3 QEtaConstraints(计算Q_BEP, η_max, 验证单峰性,0.6×Q_rated<Q_BEP<1.2×Q_rated)
  - [ ] 5.4.4 QEtaNormalizer(Q_norm=Q/Q_rated, eta保持原值0-1)
  - [ ] 5.4.5 QEtaMethodSelector(优先选择math_stat_gaussian, math_poly_3等)
  - [ ] 5.4.6 QEtaCurveFitter(顺序执行方法)
  - [ ] 5.4.7 QEtaValidator(验证单峰性,η(0)=0,η(Q_max)→0,0≤η≤1,BEP位置合理)
- [ ] 5.5 验证每个曲线的数据提取SQL正确性
- [ ] 5.6 验证每个曲线的物理特性验证逻辑
- [ ] 5.7 编写所有曲线模块测试

**output/模块** (必须实现):

- [ ] 6.1 实现output/result_output.py
- [ ] 6.2 实现output/plotter.py
- [ ] 6.3 编写输出模块测试

**pump_group/模块** (必须实现,P0后):

- [ ] 7.1 实现pump_group/pump_group_processor.py
- [ ] 7.2 实现pump_group/parallel_synthesizer.py
- [ ] 7.3 实现pump_group/system_correction_model.py
- [ ] 7.4 编写泵组模块测试

### 6.3 管道重构检查清单

**依赖注入**:

- [ ] 1.1 重构CurveFittingPipeline构造函数
- [ ] 1.2 将method_registry和result_storage改为必需参数
- [ ] 1.3 删除自动创建依赖的代码
- [ ] 1.4 更新所有实例化CurveFittingPipeline的代码

**阶段处理器重新实现**:

- [ ] 2.1 重新实现_stage_data_extract(集成DataExtractor)
- [ ] 2.2 重新实现_stage_constraint_calc(集成ConstraintCalculator)
- [ ] 2.3 重新实现_stage_steady_state_detect(集成SteadyStateDetector)
- [ ] 2.4 重新实现_stage_freq_normalize(集成FrequencyNormalizer)
- [ ] 2.5 重新实现_stage_historical_eval(集成HistoricalDataEvaluator)
- [ ] 2.6 验证其他处理器完整性

**异常处理**:

- [ ] 3.1 每个处理器添加统一异常处理
- [ ] 3.2 实现错误传播逻辑
- [ ] 3.3 添加完整日志输出
- [ ] 3.4 测试异常场景

**管道执行逻辑**:

- [ ] 4.1 更新_stage_handlers字典
- [ ] 4.2 实现阶段执行顺序控制
- [ ] 4.3 实现条件阶段跳过逻辑
- [ ] 4.4 验证数据在阶段间正确传递

### 6.4 拟合方法优化检查清单

**用户确认**: 现有代码足够,不补充新方法

**方法清理**:

- [ ] 1.1 检查methods/mathematical/下所有文件
- [ ] 1.2 检查methods/physical/下所有文件
- [ ] 1.3 检查methods/machine_learning/下所有文件
- [ ] 1.4 检查methods/hybrid/下所有文件
- [ ] 1.5 识别并删除仅为占位的空方法

**硬编码清理**:

- [ ] 2.1 移除所有方法内部的硬编码参数值
- [ ] 2.2 将硬编码值提取到配置文件
- [ ] 2.3 验证所有参数通过构造函数传入
- [ ] 2.4 确认无magic number残留

**默认值清理**:

- [ ] 3.1 移除所有函数参数的默认值
- [ ] 3.2 移除Optional类型中的默认None
- [ ] 3.3 更新所有调用方,显式传递参数
- [ ] 3.4 验证无默认值残留

**降级策略清理**:

- [ ] 4.1 删除拟合失败后的回退逻辑
- [ ] 4.2 删除"尝试简单方法"的降级代码
- [ ] 4.3 确保失败即抛异常,不尝试恢复
- [ ] 4.4 验证无降级逻辑残留

**方法注册清理**:

- [ ] 5.1 清理MethodRegistry,移除未实现方法注册
- [ ] 5.2 验证注册的方法ID与实际文件一致
- [ ] 5.3 确保每个注册方法都有完整实现
- [ ] 5.4 测试方法选择和调用

### 6.5 测试体系建立检查清单

**无效测试删除**:

- [ ] 1.1 删除models.py相关测试
- [ ] 1.2 删除pump_group相关测试
- [ ] 1.3 删除占位处理器测试
- [ ] 1.4 删除未实现方法测试

**单元测试**:

- [ ] 2.1 core模块测试覆盖率≥95%
- [ ] 2.2 curves模块测试覆盖率≥90%
- [ ] 2.3 methods模块测试覆盖率≥90%
- [ ] 2.4 constraints模块测试覆盖率≥90%
- [ ] 2.5 pipeline模块测试覆盖率≥85%

**端到端测试**:

- [ ] 3.1 准备测试数据
- [ ] 3.2 建立完整拟合流程测试
- [ ] 3.3 验证拟合结果正确性
- [ ] 3.4 验证数据库存储正确性

**验证测试**:

- [ ] 4.1 使用真实数据测试
- [ ] 4.2 验证拟合结果符合物理规律
- [ ] 4.3 性能测试
- [ ] 4.4 边界情况测试

---

## 7. 验证标准

### 7.1 代码质量验证

**代码清洁度**:

- ✓ 无DEPRECATED标记
- ✓ 无TODO占位符
- ✓ 无未使用的导入
- ✓ 无死代码(未被调用的函数/类)
- ✓ 静态分析工具0警告

**架构一致性**:

- ✓ 目录结构符合文档定义
- ✓ 依赖关系符合层次定义
- ✓ 无循环依赖
- ✓ 数据库访问统一使用连接池

**接口规范性**:

- ✓ 所有数据结构符合文档定义
- ✓ 异常类型完整且使用正确错误码
- ✓ 枚举定义完整
- ✓ 类型注解完整

### 7.2 功能完整性验证

**P0阶段数据流** (所有阶段必须实现):

- ✓ 阶段1:时间窗口划分正常工作
- ✓ 阶段2:场景识别正常工作(必须实现)
- ✓ 阶段3:数据提取正常工作
- ✓ 阶段4:数据预处理正常工作
- ✓ 阶段5:稳态识别正常工作(必须实现)
- ✓ 阶段6:约束计算正常工作
- ✓ 阶段7:频率归一化正常工作(必须实现)
- ✓ 阶段8:数据归一化正常工作
- ✓ 阶段9:方法选择正常工作
- ✓ 阶段10:曲线拟合正常工作
- ✓ 阶段11:结果验证正常工作
- ✓ 阶段12:历史评估正常工作(必须实现)
- ✓ 阶段13:结果存储正常工作

**P2阶段数据流** (必须实现):

- ✓ 阶段14:泵组类型识别正常工作
- ✓ 阶段15:并联合成正常工作
- ✓ 阶段16:修正系数学习正常工作

**拟合方法**:

- ✓ 所有保留方法完整实现(非占位)
- ✓ 方法注册正确(仅已实现方法)
- ✓ 方法选择逻辑正确
- ✓ 拟合精度符合要求
- ✓ 无硬编码参数
- ✓ 无默认值
- ✓ 无降级策略

**所有其他模块**:

- ✓ 所有共用层模块完整实现(9个独立模块)
- ✓ 所有预处理层独立模块完整实现(4个独立模块)
- ✓ 所有约束层模块完整实现(6个独立模块)
- ✓ 所有曲线类完整实现(3个曲线类,每个包含7个子模块)
- ✓ 输出模块完整实现
- ✓ 泵组模块完整实现(3个模块,P2阶段)

**端到端流程**:

- ✓ 完整拟合流程可执行
- ✓ 拟合结果正确存储到数据库
- ✓ 异常正确处理和传播
- ✓ 日志完整输出

### 7.3 测试覆盖验证

**覆盖率**:

- ✓ 单元测试覆盖率≥90%
- ✓ 端到端测试覆盖主流程
- ✓ 所有P0核心方法有测试
- ✓ 异常场景有测试

**测试质量**:

- ✓ 测试用例独立可执行
- ✓ 测试数据真实有效
- ✓ 断言完整准确
- ✓ 测试可重复执行

### 7.4 文档一致性验证

**设计文档对照**:

- ✓ 实现与`02_数据流定义.md`一致
- ✓ 实现与`03_核心模块`一致
- ✓ 实现与`04_曲线模块`一致
- ✓ 实现与`05_拟合方法`一致
- ✓ 实现与`06_数据库`一致

**接口规范对照**:

- ✓ 数据结构字段完整
- ✓ 函数签名正确
- ✓ 枚举值完整
- ✓ 异常码正确

---

**文档结束**
