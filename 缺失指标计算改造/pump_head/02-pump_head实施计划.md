# pump_head 实施计划

> **文档版本**: v1.0  
> **创建日期**: 2025-11-17  
> **状态**: 计划阶段  
> **协议**: RIPER-5

---

## 📋 目录

1. [实施概述](#实施概述)
2. [目录结构规划](#目录结构规划)
3. [数据库变更](#数据库变更)
4. [代码实施清单](#代码实施清单)
5. [测试计划](#测试计划)
6. [部署计划](#部署计划)

---

## 实施概述

### 实施目标

**核心目标**：
1. 实现 pump_head（水泵扬程）计算功能
2. 同时计算并写入 pump_outlet_pressure（修正后的泵出口压力）
3. 使用方案1+3（管道损失修正 + 多泵运行修正）
4. 准确度目标：±1m

**技术方案**：
- 采用流水线架构（参考 pump_flow_rate 和 pump_inlet_pressure）
- 集成共用模块（SharedServices, ParameterManager, DataWriter）
- 方法配置在代码中定义（不使用 calculation_method_registry 表）
- 两个独立参数：K_pipe_loss 和 alpha_multi_pump

### 实施范围

**包含**：
- ✅ pump_head 计算模块（6个文件）
- ✅ pump_outlet_pressure 同步计算
- ✅ 参数初始化（设备1-6）
- ✅ 单元测试
- ✅ 集成测试

**不包含**：
- ❌ pump_outlet_pressure 独立计算模块（pump_head 计算时自动生成）
- ❌ 参数优化功能（后续实施）
- ❌ 实时监控和验证（用户不需要）

### 依赖关系

**前置依赖**：
- ✅ pump_inlet_pressure 已实现
- ✅ pump_flow_rate 已实现
- ✅ main_pipeline_outlet_pressure 有测量数据
- ✅ device_running 有测量数据
- ✅ SharedServices 已实现

**后续依赖**：
- pump_efficiency（需要 pump_head）
- pump_hydraulic_power（需要 pump_head）

---

## 目录结构规划

### 完整目录结构

```
app/services/calculation/metrics/pump_head/
├── __init__.py                  # 模块入口，导出 calculate_pump_head()
├── pipeline.py                  # 流水线编排（6个阶段）
├── data_loader.py              # 阶段1：数据加载
├── data_filter.py              # 阶段2：数据过滤
├── method_selector.py          # 阶段3：方法选择
├── calculator.py               # 阶段4：计算执行
├── validator.py                # 阶段5：结果验证
└── methods/
    ├── __init__.py
    └── pipe_loss_multi_pump.py  # 方法1：管道损失+多泵修正
```

### 文件说明

| 文件 | 行数估计 | 职责 |
|------|---------|------|
| `__init__.py` | ~60 | 模块入口，适配 Scheduler 接口 |
| `pipeline.py` | ~200 | 流水线编排，调用6个阶段 |
| `data_loader.py` | ~150 | SQL查询，数据透视，统计N_running |
| `data_filter.py` | ~100 | 过滤停机、NaN、异常值 |
| `method_selector.py` | ~120 | 方法选择逻辑 |
| `calculator.py` | ~150 | 调用计算方法，返回两个结果 |
| `validator.py` | ~120 | 验证两个结果的合理性 |
| `methods/pipe_loss_multi_pump.py` | ~100 | 核心计算逻辑 |

**总计**：~1000行代码

---

## 数据库变更

### 变更1：初始化参数（migration）

**文件**：`缺失指标计算改造/pump_head/migrations/001-initialize-parameters.sql`

**内容**：
```sql
-- 1. 全局参数
INSERT INTO calculation_parameters (
    metric_key, param_name, param_value, param_type,
    description, station_id, device_id
) VALUES
    ('pump_head', 'rho', '1000.0', 'float', '水密度（kg/m³）', NULL, NULL),
    ('pump_head', 'g', '9.81', 'float', '重力加速度（m/s²）', NULL, NULL)
ON CONFLICT (metric_key, param_name, station_id, device_id) DO NOTHING;

-- 2. 泵站级参数（泵站16）
INSERT INTO calculation_parameters (
    metric_key, param_name, param_value, param_type,
    description, station_id, device_id
) VALUES
    ('pump_head', 'N_total_pumps', '6', 'int', '泵站总泵数量', 16, NULL)
ON CONFLICT (metric_key, param_name, station_id, device_id) DO NOTHING;

-- 3. 设备级参数（设备1-6）
INSERT INTO calculation_parameters (
    metric_key, param_name, param_value, param_type,
    description, station_id, device_id, is_optimizable
) VALUES
    ('pump_head', 'K_pipe_loss', '0.00001', 'float', '管道损失系数', 16, 1, TRUE),
    ('pump_head', 'alpha_multi_pump', '0.02', 'float', '多泵修正系数', 16, 1, TRUE),
    ('pump_head', 'K_pipe_loss', '0.00001', 'float', '管道损失系数', 16, 2, TRUE),
    ('pump_head', 'alpha_multi_pump', '0.02', 'float', '多泵修正系数', 16, 2, TRUE),
    ('pump_head', 'K_pipe_loss', '0.00001', 'float', '管道损失系数', 16, 3, TRUE),
    ('pump_head', 'alpha_multi_pump', '0.02', 'float', '多泵修正系数', 16, 3, TRUE),
    ('pump_head', 'K_pipe_loss', '0.00001', 'float', '管道损失系数', 16, 4, TRUE),
    ('pump_head', 'alpha_multi_pump', '0.02', 'float', '多泵修正系数', 16, 4, TRUE),
    ('pump_head', 'K_pipe_loss', '0.00001', 'float', '管道损失系数', 16, 5, TRUE),
    ('pump_head', 'alpha_multi_pump', '0.02', 'float', '多泵修正系数', 16, 5, TRUE),
    ('pump_head', 'K_pipe_loss', '0.00001', 'float', '管道损失系数', 16, 6, TRUE),
    ('pump_head', 'alpha_multi_pump', '0.02', 'float', '多泵修正系数', 16, 6, TRUE)
ON CONFLICT (metric_key, param_name, station_id, device_id) DO NOTHING;
```

### 变更2：验证指标配置

**查询**：
```sql
-- 验证 pump_head 和 pump_outlet_pressure 已在 dim_metric_config 表中
SELECT metric_key, unit, unit_display
FROM dim_metric_config
WHERE metric_key IN ('pump_head', 'pump_outlet_pressure');
```

**预期结果**：
```
metric_key              | unit | unit_display
------------------------+------+--------------
pump_head               | M    | 泵扬程
pump_outlet_pressure    | MPa  | 泵出口压力
```

---

## 代码实施清单

### 阶段1：创建目录结构

**任务**：
- [ ] 创建 `app/services/calculation/metrics/pump_head/` 目录
- [ ] 创建 `app/services/calculation/metrics/pump_head/methods/` 目录

### 阶段2：实现核心模块

#### 2.1 __init__.py

**文件**：`app/services/calculation/metrics/pump_head/__init__.py`

**关键点**：
- 导出 `calculate_pump_head()` 函数
- 适配 Scheduler 接口（Task → TaskResult）
- 延迟初始化 Pipeline 实例
- 异常处理和 traceback 记录

**参考**：`app/services/calculation/metrics/pump_flow_rate/__init__.py`

**代码结构**：
```python
"""
pump_head 指标计算模块

提供完整的计算流水线：
- Pipeline: 流水线编排
- DataLoader: 数据加载
- DataFilter: 数据过滤
- MethodSelector: 方法选择
- Calculator: 计算执行
- Validator: 结果验证
"""

from app.services.calculation.metrics.pump_head.pipeline import PumpHeadPipeline
from app.services.calculation.shared.shared_services import SharedServices
from app.services.calculation.shared.scheduler import Task, TaskResult

__all__ = ['PumpHeadPipeline', 'calculate_pump_head']


# 全局流水线实例（延迟初始化）
_pipeline_instance = None


def calculate_pump_head(task: Task) -> TaskResult:
    """
    pump_head 计算函数（适配 Scheduler 接口）

    Args:
        task: 任务对象（包含 station_id, device_id, start_time, end_time, task_id）

    Returns:
        TaskResult: 任务结果
    """
    global _pipeline_instance

    # 延迟初始化流水线（确保 SharedServices 已初始化）
    if _pipeline_instance is None:
        _pipeline_instance = PumpHeadPipeline()

    # 执行流水线
    try:
        result = _pipeline_instance.execute(
            station_id=task.station_id,
            device_id=task.device_id,
            start_time=task.start_time,
            end_time=task.end_time,
            task_id=task.task_id
        )

        # 转换为 TaskResult
        return TaskResult(
            task_id=task.task_id,
            device_id=task.device_id,
            metric_key=task.metric_key,
            success=True,
            results_count=result.get('written_count', 0),
            error_message=None
        )

    except Exception as e:
        import traceback
        return TaskResult(
            task_id=task.task_id,
            device_id=task.device_id,
            metric_key=task.metric_key,
            success=False,
            results_count=0,
            error_message=f"{str(e)}\n{traceback.format_exc()}"
        )
```

#### 2.2 pipeline.py

**文件**：`app/services/calculation/metrics/pump_head/pipeline.py`

**关键点**：
- 6个阶段：DataLoader → DataFilter → MethodSelector → Calculator → Validator → DataWriter
- 集成 SharedServices（ParameterManager, DataWriter）
- **两次调用 DataWriter**：先写 pump_outlet_pressure，再写 pump_head
- 详细日志记录（每个阶段的开始/完成日志）
- 空数据检查（DataLoader返回空数据时跳过计算）

**参考**：`app/services/calculation/metrics/pump_inlet_pressure/pipeline.py`

**SharedServices 集成方式**：
```python
from app.services.calculation.shared.shared_services import SharedServices

# Get shared services（在 execute() 方法中）
shared_services = SharedServices()

# Load parameters
params = shared_services.parameter_manager.get_parameters(
    station_id=station_id,
    device_id=device_id,
    metric_key='pump_head'
)
```

**两次 DataWriter 调用**：
```python
# Stage 6: DataWriter（第一次 - pump_outlet_pressure）
if valid_count > 0:
    from app.services.calculation.shared.data_writer import WriteRecord
    import pytz

    TZ_SH = pytz.timezone('Asia/Shanghai')
    calculated_at = datetime.now(TZ_SH)

    # 写入 pump_outlet_pressure
    records_outlet = []
    for _, row in validated_pump_outlet_pressure.iterrows():
        records_outlet.append(WriteRecord(
            device_id=device_id,
            metric_key='pump_outlet_pressure',
            timestamp=row['ts_bucket'],
            value=float(row['pump_outlet_pressure']),
            quality_code=int(row.get('quality_code', 0)),
            method_id=selected_method,
            calculated_at=calculated_at
        ))

    written_count_outlet = shared_services.data_writer.write(
        records_outlet,
        station_id=station_id
    )

    # 写入 pump_head
    records_head = []
    for _, row in validated_pump_head.iterrows():
        records_head.append(WriteRecord(
            device_id=device_id,
            metric_key='pump_head',
            timestamp=row['ts_bucket'],
            value=float(row['pump_head']),
            quality_code=int(row.get('quality_code', 0)),
            method_id=selected_method,
            calculated_at=calculated_at
        ))

    written_count_head = shared_services.data_writer.write(
        records_head,
        station_id=station_id
    )

    written_count = written_count_outlet + written_count_head
```

**返回值**：
```python
return {
    'written_count': written_count,  # 两个指标的总写入数量
    'task_id': task_id
}
```

#### 2.3 data_loader.py

**文件**：`app/services/calculation/metrics/pump_head/data_loader.py`

**关键点**：
- SQL查询获取4个依赖指标
- 统计运行泵数量（N_running）
- 数据透视（长表 → 宽表）

**参考**：`app/services/calculation/metrics/pump_flow_rate/data_loader.py`

#### 2.4 data_filter.py

**文件**：`app/services/calculation/metrics/pump_head/data_filter.py`

**关键点**：
- 过滤 running=0 的数据
- 过滤 NaN、Inf、负值
- 过滤超出物理范围的值

**参考**：`app/services/calculation/metrics/pump_flow_rate/data_filter.py`

#### 2.5 method_selector.py

**文件**：`app/services/calculation/metrics/pump_head/method_selector.py`

**关键点**：
- 方法配置在代码中定义（METHODS 列表）
- 检查依赖和参数
- 返回选中的方法

**参考**：`app/services/calculation/metrics/pump_flow_rate/method_selector.py`

#### 2.6 calculator.py

**文件**：`app/services/calculation/metrics/pump_head/calculator.py`

**关键点**：
- 调用计算方法
- **返回两个结果**：pump_outlet_pressure_df 和 pump_head_df
- 详细日志

**参考**：`app/services/calculation/metrics/pump_inlet_pressure/calculator.py`

#### 2.7 validator.py

**文件**：`app/services/calculation/metrics/pump_head/validator.py`

**关键点**：
- **验证两个结果**
- 物理范围检查
- 统计分析

**参考**：`app/services/calculation/metrics/pump_inlet_pressure/validator.py`

#### 2.8 methods/pipe_loss_multi_pump.py

**文件**：`app/services/calculation/metrics/pump_head/methods/pipe_loss_multi_pump.py`

**关键点**：
- 核心计算逻辑
- 5个步骤：管道损失修正 → 多泵修正 → 泵出口压力 → 扬程
- 返回两个DataFrame

---

### 阶段3：参数初始化

**任务**：
- [ ] 创建 migration 脚本
- [ ] 执行 migration
- [ ] 验证参数已正确插入

**SQL脚本**：`缺失指标计算改造/pump_head/migrations/001-initialize-parameters.sql`

---

### 阶段4：单元测试

#### 4.1 测试 DataLoader

**文件**：`tests/unit/calculation/metrics/pump_head/test_data_loader.py`

**测试用例**：
- [ ] 测试SQL查询正确性
- [ ] 测试数据透视逻辑
- [ ] 测试N_running统计

#### 4.2 测试 DataFilter

**文件**：`tests/unit/calculation/metrics/pump_head/test_data_filter.py`

**测试用例**：
- [ ] 测试运行状态过滤
- [ ] 测试NaN/Inf过滤
- [ ] 测试范围过滤

#### 4.3 测试 MethodSelector

**文件**：`tests/unit/calculation/metrics/pump_head/test_method_selector.py`

**测试用例**：
- [ ] 测试依赖检查
- [ ] 测试参数检查
- [ ] 测试方法选择逻辑

#### 4.4 测试 Calculator

**文件**：`tests/unit/calculation/metrics/pump_head/test_calculator.py`

**测试用例**：
- [ ] 测试计算公式正确性
- [ ] 测试两个结果的生成
- [ ] 测试边界情况

#### 4.5 测试 Validator

**文件**：`tests/unit/calculation/metrics/pump_head/test_validator.py`

**测试用例**：
- [ ] 测试pump_outlet_pressure验证
- [ ] 测试pump_head验证
- [ ] 测试异常值过滤

---

### 阶段5：集成测试

#### 5.1 端到端测试

**文件**：`tests/integration/calculation/metrics/pump_head/test_pipeline.py`

**测试用例**：
- [ ] 测试完整流水线执行
- [ ] 测试两个指标都正确写入数据库
- [ ] 测试日志输出完整性

#### 5.2 性能测试

**测试场景**：
- [ ] 1小时数据（3600条）
- [ ] 1天数据（86400条）
- [ ] 多设备并行计算

**性能目标**：
- 1小时数据：< 5秒
- 1天数据：< 60秒

---

## 共享模块集成说明

### Scheduler 集成

#### 注册计算函数

**文件**：`app/services/calculation/shared/scheduler.py`

**修改位置**：`_get_calculator_func()` 方法

**添加内容**：
```python
def _get_calculator_func(self, metric_key: str) -> Callable[[Task], TaskResult]:
    """
    获取指标的计算函数

    Args:
        metric_key: 指标键

    Returns:
        计算函数
    """
    # 根据 metric_key 动态加载对应的计算器
    if metric_key == "pump_flow_rate":
        from app.services.calculation.metrics.pump_flow_rate import calculate_pump_flow_rate
        return calculate_pump_flow_rate
    elif metric_key == "pump_inlet_pressure":
        from app.services.calculation.metrics.pump_inlet_pressure import calculate_pump_inlet_pressure
        return calculate_pump_inlet_pressure
    elif metric_key == "pump_head":  # 新增
        from app.services.calculation.metrics.pump_head import calculate_pump_head
        return calculate_pump_head
    else:
        raise NotImplementedError(f"指标 {metric_key} 的计算器尚未实现")
```

#### 配置 METRIC_ORDER

**文件**：`app/services/calculation/shared/scheduler.py`

**修改位置**：`METRIC_ORDER` 列表

**当前配置**：
```python
METRIC_ORDER = [
    "pump_flow_rate",          # 1. 水泵流量（基础指标）
    "pump_inlet_pressure",     # 2. 水泵入口压力
    "pump_outlet_pressure",    # 3. 水泵出口压力（pump_head计算的中间结果）
    "pump_head",               # 4. 水泵扬程（依赖 pump_inlet_pressure, main_pipeline_outlet_pressure, pump_flow_rate）
    "pump_efficiency",         # 5. 水泵效率（依赖 pump_flow_rate, pump_head）
    # ... 其他指标
]
```

**重要说明**：
- `pump_outlet_pressure` 和 `pump_head` 是同时计算的（在同一个 calculate_pump_head() 函数中）
- 但在 METRIC_ORDER 中，只需要添加 `pump_head`
- `pump_outlet_pressure` 不需要单独添加到 METRIC_ORDER，因为它会在 pump_head 计算时自动生成
- **修正**：删除 METRIC_ORDER 中的 `pump_outlet_pressure`，只保留 `pump_head`

**正确配置**：
```python
METRIC_ORDER = [
    "pump_flow_rate",          # 1. 水泵流量（基础指标）
    "pump_inlet_pressure",     # 2. 水泵入口压力
    "pump_head",               # 3. 水泵扬程（同时计算 pump_outlet_pressure）
    "pump_efficiency",         # 4. 水泵效率（依赖 pump_flow_rate, pump_head）
    # ... 其他指标
]
```

---

### ParameterManager 集成

#### 获取参数

**在 pipeline.py 中**：
```python
from app.services.calculation.shared.shared_services import SharedServices

# Get shared services
shared_services = SharedServices()

# Load parameters（三层参数：全局 → 泵站 → 设备）
params = shared_services.parameter_manager.get_parameters(
    station_id=station_id,
    device_id=device_id,
    metric_key='pump_head'
)
```

#### 参数默认值处理

**ParameterManager 自动处理三层参数**：
1. 先查询设备级参数（device_id）
2. 如果不存在，查询泵站级参数（station_id）
3. 如果不存在，查询全局参数（station_id=NULL, device_id=NULL）

**在代码中使用参数**：
```python
# 获取参数（带默认值）
K_pipe_loss = params.get('K_pipe_loss', 0.00001)
alpha_multi_pump = params.get('alpha_multi_pump', 0.02)
N_total_pumps = params.get('N_total_pumps', 6)
rho = params.get('rho', 1000.0)
g = params.get('g', 9.81)
```

---

### DataWriter 集成

#### 获取 DataWriter 实例

**在 pipeline.py 中**：
```python
from app.services.calculation.shared.shared_services import SharedServices

# Get shared services
shared_services = SharedServices()

# 使用 DataWriter
written_count = shared_services.data_writer.write(records, station_id=station_id)
```

#### 写入两个指标

**pump_outlet_pressure（第一次调用）**：
```python
from app.services.calculation.shared.data_writer import WriteRecord
import pytz

TZ_SH = pytz.timezone('Asia/Shanghai')
calculated_at = datetime.now(TZ_SH)

# 构造 pump_outlet_pressure 记录
records_outlet = []
for _, row in validated_pump_outlet_pressure.iterrows():
    records_outlet.append(WriteRecord(
        device_id=device_id,
        metric_key='pump_outlet_pressure',  # 指标键
        timestamp=row['ts_bucket'],
        value=float(row['pump_outlet_pressure']),
        quality_code=int(row.get('quality_code', 0)),
        method_id=selected_method,  # 计算方法ID
        calculated_at=calculated_at  # 计算时间
    ))

# 写入数据库
written_count_outlet = shared_services.data_writer.write(
    records_outlet,
    station_id=station_id
)
```

**pump_head（第二次调用）**：
```python
# 构造 pump_head 记录
records_head = []
for _, row in validated_pump_head.iterrows():
    records_head.append(WriteRecord(
        device_id=device_id,
        metric_key='pump_head',  # 指标键
        timestamp=row['ts_bucket'],
        value=float(row['pump_head']),
        quality_code=int(row.get('quality_code', 0)),
        method_id=selected_method,  # 计算方法ID
        calculated_at=calculated_at  # 计算时间
    ))

# 写入数据库
written_count_head = shared_services.data_writer.write(
    records_head,
    station_id=station_id
)
```

#### metric_id 自动查询

**DataWriter 内部逻辑**：
- DataWriter 会根据 `metric_key` 自动从 `dim_metric_config` 表查询 `metric_id`
- 不需要手动查询 metric_id
- 确保 `pump_outlet_pressure` 和 `pump_head` 已在 `dim_metric_config` 表中配置

**验证查询**：
```sql
SELECT metric_key, id, unit, unit_display
FROM dim_metric_config
WHERE metric_key IN ('pump_outlet_pressure', 'pump_head');
```

---

### SharedServices 单例模式

#### 获取单例

**在任何模块中**：
```python
from app.services.calculation.shared.shared_services import SharedServices

# 获取单例（无论调用多少次，都是同一个实例）
shared_services = SharedServices()
```

#### 使用服务

```python
# 使用 ParameterManager
params = shared_services.parameter_manager.get_parameters(
    station_id=station_id,
    device_id=device_id,
    metric_key='pump_head'
)

# 使用 DataWriter
written_count = shared_services.data_writer.write(records, station_id=station_id)

# 使用 Scheduler（如果需要）
# scheduler = shared_services.scheduler
```

---

## 测试计划

### 测试环境

**数据库**：
- 使用测试数据库（避免污染生产数据）
- 准备测试数据（设备1-6，2025-01-01 00:00:00 - 01:00:00）

**依赖数据**：
- pump_inlet_pressure（已计算）
- pump_flow_rate（已计算）
- main_pipeline_outlet_pressure（测量值）
- device_running（测量值）

### 测试数据准备

```sql
-- 查询测试数据是否完整
SELECT
    device_id,
    COUNT(*) as count,
    MIN(ts_bucket) as start_time,
    MAX(ts_bucket) as end_time
FROM fact_measurements
WHERE station_id = 16
  AND device_id IN (1, 2, 3, 4, 5, 6)
  AND metric_key IN ('pump_inlet_pressure', 'pump_flow_rate')
  AND ts_bucket BETWEEN '2025-01-01 00:00:00' AND '2025-01-01 01:00:00'
GROUP BY device_id
ORDER BY device_id;
```

### 测试执行步骤

1. **单元测试**：
   ```bash
   pytest tests/unit/calculation/metrics/pump_head/ -v
   ```

2. **集成测试**：
   ```bash
   pytest tests/integration/calculation/metrics/pump_head/ -v
   ```

3. **手动验证**：
   ```python
   from app.services.calculation.metrics.pump_head import calculate_pump_head
   from app.services.calculation.shared import Task
   from datetime import datetime

   task = Task(
       task_id='test_001',
       station_id=16,
       device_id=1,
       metric_key='pump_head',
       start_time=datetime(2025, 1, 1, 0, 0, 0),
       end_time=datetime(2025, 1, 1, 1, 0, 0)
   )

   result = calculate_pump_head(task)
   print(f"Success: {result.success}")
   print(f"Results count: {result.results_count}")
   ```

4. **数据验证**：
   ```sql
   -- 验证pump_outlet_pressure写入
   SELECT COUNT(*), MIN(value), MAX(value), AVG(value)
   FROM fact_measurements
   WHERE device_id = 1
     AND metric_key = 'pump_outlet_pressure'
     AND ts_bucket BETWEEN '2025-01-01 00:00:00' AND '2025-01-01 01:00:00';

   -- 验证pump_head写入
   SELECT COUNT(*), MIN(value), MAX(value), AVG(value)
   FROM fact_measurements
   WHERE device_id = 1
     AND metric_key = 'pump_head'
     AND ts_bucket BETWEEN '2025-01-01 00:00:00' AND '2025-01-01 01:00:00';
   ```

---

## 部署计划

### 部署步骤

1. **代码审查**：
   - [ ] 代码符合规范
   - [ ] 所有测试通过
   - [ ] 文档完整

2. **数据库迁移**：
   - [ ] 执行参数初始化脚本
   - [ ] 验证参数正确性
   - [ ] 验证 dim_metric_config 表中已配置 pump_outlet_pressure 和 pump_head

3. **修改 Scheduler 配置**：
   - [ ] 修改 `app/services/calculation/shared/scheduler.py`
   - [ ] 在 `_get_calculator_func()` 方法中添加 pump_head 的导入
   - [ ] **修正 METRIC_ORDER**：删除 `pump_outlet_pressure`，只保留 `pump_head`

**METRIC_ORDER 修正**：
```python
# 修改前（错误）
METRIC_ORDER = [
    "pump_flow_rate",
    "pump_inlet_pressure",
    "pump_outlet_pressure",  # ❌ 删除这一行
    "pump_head",
    "pump_efficiency",
]

# 修改后（正确）
METRIC_ORDER = [
    "pump_flow_rate",          # 1. 水泵流量（基础指标）
    "pump_inlet_pressure",     # 2. 水泵入口压力
    "pump_head",               # 3. 水泵扬程（同时计算 pump_outlet_pressure）
    "pump_efficiency",         # 4. 水泵效率（依赖 pump_flow_rate, pump_head）
]
```

**原因**：
- `pump_outlet_pressure` 和 `pump_head` 是在同一个 `calculate_pump_head()` 函数中同时计算的
- `pump_outlet_pressure` 是 `pump_head` 计算的中间结果，不是独立的计算任务
- 如果在 METRIC_ORDER 中添加 `pump_outlet_pressure`，会导致 Scheduler 尝试调用不存在的 `calculate_pump_outlet_pressure()` 函数

4. **代码部署**：
   - [ ] 合并到主分支
   - [ ] 部署到测试环境
   - [ ] 部署到生产环境

5. **验证**：
   - [ ] 执行测试任务
   - [ ] 检查日志输出
   - [ ] 验证数据写入（两个指标都写入）

**验证计算顺序**：
```python
from app.services.calculation.shared.scheduler import Scheduler

scheduler = Scheduler()
print("METRIC_ORDER:", scheduler.METRIC_ORDER)

# 预期输出：
# METRIC_ORDER: ['pump_flow_rate', 'pump_inlet_pressure', 'pump_head', 'pump_efficiency', ...]
```

**验证数据写入**：
```sql
-- 验证 pump_outlet_pressure 写入
SELECT COUNT(*), MIN(value), MAX(value), AVG(value)
FROM fact_measurements fm
JOIN dim_metric_config mc ON mc.id = fm.metric_id
WHERE fm.device_id = 1
  AND mc.metric_key = 'pump_outlet_pressure'
  AND fm.ts_bucket BETWEEN '2025-01-01 00:00:00' AND '2025-01-01 01:00:00';

-- 验证 pump_head 写入
SELECT COUNT(*), MIN(value), MAX(value), AVG(value)
FROM fact_measurements fm
JOIN dim_metric_config mc ON mc.id = fm.metric_id
WHERE fm.device_id = 1
  AND mc.metric_key = 'pump_head'
  AND fm.ts_bucket BETWEEN '2025-01-01 00:00:00' AND '2025-01-01 01:00:00';

-- 验证两个指标的数据量一致
SELECT
    mc.metric_key,
    COUNT(*) as count
FROM fact_measurements fm
JOIN dim_metric_config mc ON mc.id = fm.metric_id
WHERE fm.device_id = 1
  AND mc.metric_key IN ('pump_outlet_pressure', 'pump_head')
  AND fm.ts_bucket BETWEEN '2025-01-01 00:00:00' AND '2025-01-01 01:00:00'
GROUP BY mc.metric_key;
```

### 回滚计划

如果出现问题：
1. 停止 pump_head 计算任务
2. 回滚代码到上一版本
3. 删除错误的计算结果
4. 分析问题原因

---

## 文档结束

**下一步**：
1. 创建任务追踪表（03-任务完成追踪表.md）
2. 开始代码实施


