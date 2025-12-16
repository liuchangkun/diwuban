# MethodParameterManager 完整设计方案

> **文档版本**: v1.1
> **创建时间**: 2025-09-30
> **最后更新**: 2025-12-01
> **状态**: 计划阶段
> **方案**: 方案B - 分层架构方案

---

## 📋 需求概述

### 核心要求

1. **数据库读取**: 参数优化器必须从数据库中读取优化所需的输入参数（如历史拟合参数、约束参数等）
2. **结果存储**: 优化后的参数结果必须写入数据库，不允许只保存在内存中
3. **历史记录**: 必须保留参数优化的完整历史记录，包括：
   - 优化前的参数值
   - 优化后的参数值
   - 优化时间戳
   - 优化方法/策略
   - 优化效果指标（如改进百分比）
   - 关联的设备ID和曲线类型

### 用户决策

1. **参数存储位置**: 存储在三表分离设计的 `curve_fit_params` 表中（`param_category = 'method'`）
2. **优化触发时机**: 支持三种触发方式
   - 手动触发（CLI命令）
   - 自动触发（拟合失败时）
   - 定期触发（定时任务）
3. **历史记录保留策略**: 只保留改进的记录
4. **参数回滚机制**: 支持回滚，不需要审批，需要日志输出

---

## 🎯 设计方案：分层架构

### 方案概述

保持 `ParameterOptimizer` 作为纯算法工具，创建新的 `MethodParameterManager` 作为管理层，负责数据库读写和历史记录。这与现有的 `ConstraintParameterManager` 设计模式一致。

### 架构分层

```
MethodParameterManager (管理层)
    ↓ 调用
ParameterOptimizer (算法层)
    ↓ 使用
ResultStorage (存储层)
    ↓ 访问
Database (数据层)
```

---

## 📦 组件设计

### 1. MethodParameterManager（新增）

**文件路径**: `app/services/characteristic_curves/shared/method_parameter_manager.py`

**职责**:
- 协调方法参数的优化流程
- 从数据库读取历史最佳参数
- 调用 ParameterOptimizer 进行优化
- 保存优化结果到数据库
- 记录优化历史（仅保留改进的记录）
- 支持参数回滚

**设计模式**: 门面模式（Facade Pattern）

**依赖**:
- `ParameterOptimizer`: 算法工具
- `ResultStorage`: 结果存储器
- `db_pool`: 数据库连接池

**核心方法**:

```python
class MethodParameterManager:
    def __init__(
        self,
        db_pool,
        result_storage: ResultStorage,
        param_optimizer: ParameterOptimizer
    ):
        """初始化方法参数管理器"""
        
    def get_params(
        self,
        device_id: int,
        curve_type: str,
        method_name: str
    ) -> Dict[str, Any]:
        """
        获取方法参数（优先历史最佳，其次默认值）
        
        流程:
        1. 从数据库查询历史最佳参数
        2. 如果存在，返回历史最佳参数
        3. 如果不存在，返回方法默认参数
        """
        
    def optimize_params(
        self,
        device_id: int,
        curve_type: str,
        method_name: str,
        X: np.ndarray,
        y: np.ndarray,
        strategy: str = 'grid_search'
    ) -> Dict[str, Any]:
        """
        优化方法参数
        
        流程:
        1. 获取当前参数（历史最佳或默认）
        2. 调用 ParameterOptimizer 进行优化
        3. 评估优化效果
        4. 如果有改进，保存到数据库并记录历史
        5. 如果无改进，不保存（根据用户要求）
        
        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            method_name: 方法名称
            X: 输入数据
            y: 输出数据
            strategy: 优化策略 ('grid_search', 'bayesian', 'cross_validation')
            
        Returns:
            Dict: 优化结果，包含:
                - old_params: 优化前参数
                - new_params: 优化后参数
                - old_score: 优化前得分
                - new_score: 优化后得分
                - improvement_percentage: 改进百分比
                - is_improved: 是否有改进
                - is_saved: 是否已保存
        """
        
    def save_params(
        self,
        device_id: int,
        curve_type: str,
        method_name: str,
        params: Dict[str, Any],
        score: float,
        optimization_info: Dict[str, Any]
    ) -> None:
        """
        保存优化后的参数到数据库

        流程:
        1. 更新 curve_fit_params 表（param_category='method'）
        2. 记录优化历史到 method_parameter_optimization_history 表
        """

    def get_optimization_history(
        self,
        device_id: int,
        curve_type: str,
        method_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取参数优化历史记录

        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            method_name: 方法名称
            limit: 返回记录数量限制

        Returns:
            List[Dict]: 优化历史记录列表（按时间倒序）
        """

    def rollback_params(
        self,
        device_id: int,
        curve_type: str,
        method_name: str,
        history_id: int
    ) -> Dict[str, Any]:
        """
        回滚参数到历史版本

        流程:
        1. 从 method_parameter_optimization_history 表读取历史参数
        2. 更新 curve_fit_params 表（param_category='method'）
        3. 记录回滚操作到历史表
        4. 输出详细日志

        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            method_name: 方法名称
            history_id: 历史记录ID

        Returns:
            Dict: 回滚结果，包含:
                - old_params: 回滚前参数
                - new_params: 回滚后参数
                - rollback_time: 回滚时间
        """

    def batch_optimize(
        self,
        device_ids: Optional[List[int]] = None,
        curve_types: Optional[List[str]] = None,
        method_names: Optional[List[str]] = None,
        strategy: str = 'grid_search'
    ) -> Dict[str, Any]:
        """
        批量优化多个设备/曲线/方法的参数

        Args:
            device_ids: 设备ID列表（可选，默认所有设备）
            curve_types: 曲线类型列表（可选，默认所有类型）
            method_names: 方法名称列表（可选，默认所有方法）
            strategy: 优化策略

        Returns:
            Dict: 批量优化结果统计，包含:
                - total_count: 总数
                - improved_count: 改进数
                - no_improvement_count: 无改进数
                - failed_count: 失败数
                - results: 详细结果列表
        """
```

---

### 2. ParameterOptimizer（增强接口）

**文件路径**: `app/services/characteristic_curves/shared/parameter_optimizer.py`

**现有设计**: 保持不变（纯算法工具）

**需要确保的接口**:

```python
class ParameterOptimizer:
    def __init__(self, n_folds: int = 5, random_state: int = 42):
        """初始化参数优化器（无数据库依赖）"""

    def cross_validate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        fit_func: Callable,
        params: Dict[str, Any],
        n_folds: Optional[int] = None
    ) -> Dict[str, Any]:
        """交叉验证评估参数"""

    def grid_search(
        self,
        X: np.ndarray,
        y: np.ndarray,
        fit_func: Callable,
        param_grid: Dict[str, List[Any]]
    ) -> Dict[str, Any]:
        """网格搜索最优参数"""

    def bayesian_optimize(
        self,
        X: np.ndarray,
        y: np.ndarray,
        fit_func: Callable,
        param_bounds: Dict[str, Tuple[float, float]],
        n_iterations: int = 50
    ) -> Dict[str, Any]:
        """贝叶斯优化参数"""
```

**说明**: ParameterOptimizer 保持纯算法工具的定位，不添加数据库依赖。

---

## 🗄️ 数据库设计

### 1. 新增表: method_parameter_optimization_history

**表名**: `method_parameter_optimization_history`

**用途**: 记录方法参数优化历史（仅保留改进的记录）

**表结构**:

```sql
CREATE TABLE method_parameter_optimization_history (
    -- ========== 主键 ==========
    id SERIAL PRIMARY KEY,

    -- ========== 基本信息 ==========
    device_id INTEGER NOT NULL,
    curve_type VARCHAR(50) NOT NULL,
    method_name VARCHAR(100) NOT NULL,

    -- ========== 优化前后参数 ==========
    old_params JSONB,  -- 优化前的参数（首次优化时为NULL）
    new_params JSONB NOT NULL,  -- 优化后的参数

    -- ========== 优化信息 ==========
    optimization_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    optimization_strategy VARCHAR(50) NOT NULL,  -- 'grid_search', 'bayesian', 'cross_validation'
    trigger_reason VARCHAR(50) NOT NULL,  -- 'manual', 'auto_on_failure', 'scheduled', 'rollback'

    -- ========== 优化效果 ==========
    old_score DOUBLE PRECISION,  -- 优化前得分（R²或其他指标）
    new_score DOUBLE PRECISION NOT NULL,  -- 优化后得分
    improvement_percentage DOUBLE PRECISION,  -- 改进百分比

    -- ========== 数据信息 ==========
    data_point_count INTEGER,  -- 用于优化的数据点数量
    data_time_range JSONB,  -- 数据时间范围 {"start": "...", "end": "..."}

    -- ========== 元数据 ==========
    created_by VARCHAR(100),
    notes TEXT,

    -- ========== 约束 ==========
    CONSTRAINT check_curve_type_param_history
        CHECK (curve_type IN ('qh', 'qp', 'qeta', 'heta', 'peta', 'qnpsh')),
    CONSTRAINT check_optimization_strategy
        CHECK (optimization_strategy IN ('grid_search', 'bayesian', 'cross_validation')),
    CONSTRAINT check_trigger_reason_param
        CHECK (trigger_reason IN ('manual', 'auto_on_failure', 'scheduled', 'rollback'))
);

-- 索引
CREATE INDEX idx_param_history_device ON method_parameter_optimization_history(device_id);
CREATE INDEX idx_param_history_curve ON method_parameter_optimization_history(curve_type);
CREATE INDEX idx_param_history_method ON method_parameter_optimization_history(method_name);
CREATE INDEX idx_param_history_time ON method_parameter_optimization_history(optimization_time DESC);
CREATE INDEX idx_param_history_device_curve_method
    ON method_parameter_optimization_history(device_id, curve_type, method_name);

-- 注释
COMMENT ON TABLE method_parameter_optimization_history IS '方法参数优化历史记录（仅保留改进的记录）';
COMMENT ON COLUMN method_parameter_optimization_history.old_params IS '优化前的参数（首次优化时为NULL）';
COMMENT ON COLUMN method_parameter_optimization_history.new_params IS '优化后的参数';
COMMENT ON COLUMN method_parameter_optimization_history.optimization_strategy IS '优化策略：grid_search（网格搜索）、bayesian（贝叶斯优化）、cross_validation（交叉验证）';
COMMENT ON COLUMN method_parameter_optimization_history.trigger_reason IS '触发原因：manual（手动）、auto_on_failure（拟合失败自动触发）、scheduled（定期触发）、rollback（回滚操作）';
COMMENT ON COLUMN method_parameter_optimization_history.improvement_percentage IS '改进百分比：(new_score - old_score) / old_score * 100';
```

### 2. 利用三表分离设计: curve_fit_params

> **重要说明**：根据06_数据库和配置设计.md的三表分离设计，方法参数存储在 `curve_fit_params` 表中，而非旧的单表设计 `characteristic_curve_fits.method_params`。

**表名**: `curve_fit_params`

**存储方式**:
- `param_category = 'method'` 标识方法参数
- 参数以键值对形式存储（`param_key`, `param_value`/`param_text`）

**用途**: 存储当前使用的方法参数（最佳参数）

**更新时机**:
- 参数优化后有改进时更新
- 参数回滚时更新

**查询方式**：通过视图 `v_curve_fit_full` 可获取聚合后的 `method_params` JSONB

---

## 🔄 触发机制设计

### 1. 手动触发（CLI命令）

**命令**: `python -m app.cli.curve optimize-params`

**参数**:
- `--device-id`: 设备ID（必需）
- `--curve-type`: 曲线类型（必需）
- `--method-name`: 方法名称（必需）
- `--strategy`: 优化策略（可选，默认grid_search）
- `--start-time`: 数据开始时间（可选）
- `--end-time`: 数据结束时间（可选）

**示例**:
```bash
python -m app.cli.curve optimize-params \
    --device-id 1 \
    --curve-type qh \
    --method-name math_polynomial_2 \
    --strategy grid_search
```

### 2. 自动触发（拟合失败时）

**触发条件**:
- 拟合结果的 R² < 阈值（如 0.8）
- 拟合结果的 RMSE > 阈值
- 物理约束验证失败

**触发位置**: 在 `QHFitter.fit()` 方法中

**流程**:
1. 拟合完成后检查评估指标
2. 如果不满足质量要求，调用 `MethodParameterManager.optimize_params()`
3. 使用优化后的参数重新拟合
4. 记录自动优化日志

### 3. 定期触发（定时任务）

**调度器**: 使用 APScheduler 或 Celery

**频率**: 每周一次（可配置）

**任务**: `MethodParameterManager.batch_optimize()`

**流程**:
1. 查询所有活跃的设备/曲线/方法组合
2. 对每个组合执行参数优化
3. 生成优化报告
4. 发送通知（可选）

---

## 🔙 参数回滚机制

### 回滚流程

1. **查询历史记录**:
   ```python
   history = manager.get_optimization_history(
       device_id=1,
       curve_type='qh',
       method_name='math_polynomial_2',
       limit=10
   )
   ```

2. **选择回滚版本**: 用户选择历史记录ID

3. **执行回滚**:
   ```python
   result = manager.rollback_params(
       device_id=1,
       curve_type='qh',
       method_name='math_polynomial_2',
       history_id=123
   )
   ```

4. **日志输出**:
   ```
   [参数管理] 参数回滚
   - 设备ID: 1
   - 曲线类型: qh
   - 方法名称: math_polynomial_2
   - 回滚到历史ID: 123
   - 回滚前参数: {...}
   - 回滚后参数: {...}
   - 回滚时间: 2025-09-30 10:30:00
   ```

### 回滚记录

回滚操作也会记录到 `method_parameter_optimization_history` 表：
- `trigger_reason`: 'rollback'
- `old_params`: 回滚前的参数
- `new_params`: 回滚后的参数
- `notes`: 回滚原因说明

---

## 📝 日志规范

### 日志级别

- **INFO**: 正常操作（获取参数、优化成功、保存成功）
- **WARNING**: 无改进（优化后无改进，不保存）
- **ERROR**: 失败操作（优化失败、保存失败）

### 日志格式

```python
self._logger.info(
    "[参数管理] 参数优化完成",
    extra={"extra_data": {
        "设备ID": device_id,
        "曲线类型": curve_type,
        "方法名称": method_name,
        "优化策略": strategy,
        "优化前得分": old_score,
        "优化后得分": new_score,
        "改进百分比": improvement_percentage,
        "是否保存": is_saved
    }}
)
```

---

## ✅ 实施检查清单

### 阶段1: 数据库设计
- [ ] 创建 `method_parameter_optimization_history` 表
- [ ] 创建索引
- [ ] 添加表和列注释
- [ ] 验证约束条件

### 阶段2: MethodParameterManager 实现
- [ ] 实现 `__init__()` 方法
- [ ] 实现 `get_params()` 方法
- [ ] 实现 `optimize_params()` 方法
- [ ] 实现 `save_params()` 方法
- [ ] 实现 `get_optimization_history()` 方法
- [ ] 实现 `rollback_params()` 方法
- [ ] 实现 `batch_optimize()` 方法
- [ ] 添加完整的日志输出
- [ ] 添加错误处理
- [ ] 添加类型注解
- [ ] 添加 Docstring

### 阶段3: 触发机制实现
- [ ] 实现 CLI 命令（手动触发）
- [ ] 在 Fitter 中集成自动触发逻辑
- [ ] 实现定时任务（定期触发）
- [ ] 添加触发日志

### 阶段4: 测试
- [ ] 单元测试：MethodParameterManager 各方法
- [ ] 集成测试：与 ParameterOptimizer 协作
- [ ] 集成测试：与 ResultStorage 协作
- [ ] 集成测试：数据库读写
- [ ] 端到端测试：手动触发流程
- [ ] 端到端测试：自动触发流程
- [ ] 端到端测试：定期触发流程
- [ ] 端到端测试：参数回滚流程

### 阶段5: 文档更新
- [ ] 更新 `02_核心模块详细设计.md`
- [ ] 更新 `06_数据库和配置设计.md`
- [ ] 创建使用手册
- [ ] 创建 API 文档

---

## 🔍 关键设计决策记录

### 决策1: 只保留改进的记录

**原因**: 用户要求只保留改进的记录

**实现**: 在 `optimize_params()` 方法中，只有当 `new_score > old_score` 时才调用 `save_params()`

**影响**: 历史表只包含成功的优化记录，便于追踪改进历史

### 决策2: 参数存储在 curve_fit_params 表

**原因**: 用户选择选项1，但需与06文档三表分离设计保持一致

**实现**: 更新 `curve_fit_params` 表（`param_category='method'`），通过视图 `v_curve_fit_full` 获取聚合的 `method_params`

**影响**:
- 优点：符合三表分离设计，数据结构清晰，易于扩展
- 缺点：需要通过 result_id 关联主表

### 决策3: 支持三种触发方式

**原因**: 用户要求支持手动+自动+定期

**实现**:
- 手动：CLI 命令
- 自动：在 Fitter 中集成
- 定期：定时任务

**影响**: 系统更灵活，适应不同场景

### 决策4: 回滚不需要审批

**原因**: 用户要求不需要审批，只需要日志

**实现**: `rollback_params()` 方法直接执行回滚，输出详细日志

**影响**: 操作更快捷，但需要依赖日志审计

---

## 📊 与现有架构的一致性

### 与 ConstraintParameterManager 的对比

| 维度 | ConstraintParameterManager | MethodParameterManager |
|------|---------------------------|------------------------|
| **职责** | 管理约束参数 | 管理方法参数 |
| **设计模式** | 门面模式 | 门面模式 |
| **依赖** | ConstraintLearner, ParameterOptimizer | ParameterOptimizer, ResultStorage |
| **历史表** | constraint_change_history | method_parameter_optimization_history |
| **触发方式** | 手动、定期 | 手动、自动、定期 |
| **保留策略** | 保留所有记录 | 只保留改进的记录 |

**一致性**: 两者都采用门面模式，都依赖 ParameterOptimizer 作为算法工具，设计理念一致。

---

## 🚀 下一步行动

1. **用户确认**: 确认设计方案无误
2. **进入执行模式**: 开始实施
3. **优先级**:
   - 高优先级：数据库表、MethodParameterManager 核心方法
   - 中优先级：触发机制、测试
   - 低优先级：文档更新

---

## 📝 版本历史

| 版本 | 日期 | 修改内容 |
|------|------|---------|
| v1.0 | 2025-09-30 | 初始版本 |
| v1.1 | 2025-12-01 | 第六阶段质量检查修复：将 `characteristic_curve_fits.method_params` 更新为三表分离设计 `curve_fit_params` 表，与06文档保持一致 |

---

**文档结束**

