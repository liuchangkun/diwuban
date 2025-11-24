# 指标计算顺序功能实施报告

**日期**: 2025-01-14  
**功能**: 指标计算顺序管理（公共功能）  
**状态**: ✅ 已实施

---

## 📋 功能概述

**问题**: 缺失指标之间存在依赖关系，需要按正确的顺序计算

**解决方案**: 在 Scheduler 中定义 `METRIC_ORDER` 列表，按依赖关系排序

**执行策略**:
- **指标间串行**: 先计算所有设备的 pump_flow_rate，完成后再计算 pump_head
- **设备间并行**: 同一指标的不同设备并行计算

**⚠️ 重要说明**:
- **指标计算顺序** (Scheduler.METRIC_ORDER): 决定先计算哪个指标（pump_flow_rate → pump_head → ...）
- **方法选择顺序** (MethodSelector.METHODS): 决定 pump_flow_rate 内部使用哪种计算方法（method_a → method_b → ...）
- 这是两个不同的概念，不要混淆！

---

## 🎯 指标计算顺序

```python
METRIC_ORDER = [
    'pump_flow_rate',              # 1. 水泵流量（基础指标）
    'pump_head',                   # 2. 水泵扬程（依赖 pump_flow_rate）
    'pump_outlet_pressure',        # 3. 水泵出口压力（依赖 pump_head）
    'pump_efficiency',             # 4. 水泵效率（依赖 pump_flow_rate, pump_head）
    'pump_speed',                  # 5. 水泵转速（基础指标）
    'main_pipeline_inlet_pressure',# 6. 总管进口压力（基础指标）
    'pump_cumulative_flow',        # 7. 水泵累计流量（依赖 pump_flow_rate）
    'main_pipeline_outlet_pressure',# 8. 总管出口压力（依赖 pump_outlet_pressure）
    'pump_torque',                 # 9. 水泵扭矩（依赖 pump_active_power, pump_speed）
]
```

**依赖关系说明**:
1. **pump_flow_rate**: 基础指标，无依赖
2. **pump_head**: 依赖 pump_flow_rate（某些计算方法需要）
3. **pump_outlet_pressure**: 依赖 pump_head
4. **pump_efficiency**: 依赖 pump_flow_rate 和 pump_head
5. **pump_cumulative_flow**: 依赖 pump_flow_rate（累计计算）
6. **main_pipeline_outlet_pressure**: 依赖 pump_outlet_pressure
7. **pump_torque**: 依赖 pump_active_power 和 pump_speed

---

## 🔧 实施内容

### 1. 修改文件

**文件**: `app/services/calculation/shared/scheduler.py`

**修改内容**:
1. ✅ 添加 `METRIC_ORDER` 类属性（9个指标）
2. ✅ 实现 `schedule_all_metrics()` 方法
3. ✅ 实现 `schedule_single_metric()` 方法（框架）
4. ✅ 添加详细的日志输出

### 2. 核心方法

#### `schedule_all_metrics()`
```python
def schedule_all_metrics(
    self,
    device_ids: List[int],
    start_time: datetime,
    end_time: datetime,
    time_chunk_hours: int = 1,
    metrics: Optional[List[str]] = None
) -> Dict[str, Dict]:
    """
    调度所有指标的计算（按 METRIC_ORDER 顺序）
    
    执行策略：
    - 指标间串行：先计算所有设备的 pump_flow_rate，完成后再计算 pump_head
    - 设备间并行：同一指标的不同设备并行计算
    """
```

**执行流程**:
1. 确定要计算的指标列表（如果未指定，使用全部指标）
2. 按 METRIC_ORDER 顺序过滤和排序
3. 依次计算每个指标（串行）
4. 每个指标内部，所有设备并行计算
5. 记录每个指标的执行结果和耗时
6. 返回汇总结果

---

## 📊 与现有系统的对比

| 维度 | 现有系统（orchestrator.py） | 新架构（Scheduler） |
|------|---------------------------|-------------------|
| **顺序管理** | DependencyAnalyzer + 拓扑排序 | METRIC_ORDER 列表 |
| **依赖来源** | 数据库表（calculation_method_registry） | 代码定义 |
| **循环依赖** | 支持迭代求解 | 不支持（设计上避免） |
| **灵活性** | 高（数据库配置） | 中（代码配置） |
| **可维护性** | 低（逻辑分散） | 高（集中管理） |
| **性能** | 中（需查询数据库） | 高（内存中） |

---

## ✅ 优势

1. **简单明确**: 计算顺序在代码中一目了然
2. **高性能**: 无需查询数据库和拓扑排序
3. **易于维护**: 修改顺序只需调整列表
4. **避免循环依赖**: 设计上避免循环依赖，简化逻辑

---

## ⚠️ 注意事项

1. **手动维护**: 需要手动维护 METRIC_ORDER 列表
2. **新增指标**: 添加新指标时，需要更新 METRIC_ORDER
3. **依赖变化**: 如果依赖关系变化，需要调整顺序
4. **不支持循环依赖**: 如果出现循环依赖，需要重新设计

---

## 🚀 使用示例

```python
from app.services.calculation.shared.scheduler import Scheduler

# 创建调度器
scheduler = Scheduler(max_workers=10)

# 调度所有指标计算
results = scheduler.schedule_all_metrics(
    device_ids=[101, 102, 103],
    start_time=datetime(2025, 1, 14, 0, 0),
    end_time=datetime(2025, 1, 14, 1, 0),
    time_chunk_hours=1
)

# 查看结果
for metric_key, result in results.items():
    print(f"{metric_key}: {result['success_count']} 成功, {result['failure_count']} 失败")
```

---

## 📝 后续工作

1. ⏳ 实现 `schedule_single_metric()` 的完整逻辑
2. ⏳ 实现 `execute_tasks()` 的并行执行逻辑
3. ⏳ 添加错误处理和重试机制
4. ⏳ 添加进度跟踪功能
5. ⏳ 编写单元测试

---

## 🔍 两个"顺序"概念的区别

### 1. 指标计算顺序（Scheduler.METRIC_ORDER）

**位置**: `app/services/calculation/shared/scheduler.py`

**作用**: 决定先计算哪个指标

**示例**:
```python
METRIC_ORDER = [
    'pump_flow_rate',    # 先计算水泵流量
    'pump_head',         # 再计算水泵扬程（依赖 pump_flow_rate）
    'pump_efficiency',   # 最后计算水泵效率（依赖 pump_flow_rate 和 pump_head）
]
```

**执行流程**:
1. 计算所有设备的 pump_flow_rate（设备间并行）
2. 等待 pump_flow_rate 全部完成
3. 计算所有设备的 pump_head（设备间并行）
4. 等待 pump_head 全部完成
5. 计算所有设备的 pump_efficiency（设备间并行）

---

### 2. 方法选择顺序（MethodSelector.METHODS）

**位置**: `app/services/calculation/metrics/pump_flow_rate/method_selector.py`

**作用**: 决定 pump_flow_rate 内部使用哪种计算方法

**示例**:
```python
METHODS = [
    {'id': 'method_a', 'priority': 100},  # 优先尝试功率×频率分摊
    {'id': 'method_b', 'priority': 90},   # 其次尝试累计流量导数
    {'id': 'method_c', 'priority': 80},   # 最后尝试单泵直读
]
```

**执行流程**（针对单个设备的 pump_flow_rate 计算）:
1. 检查 method_a 的依赖和条件是否满足
2. 如果满足，使用 method_a 计算
3. 如果不满足，检查 method_b
4. 依此类推，直到找到合适的方法

---

### 对比总结

| 维度 | 指标计算顺序 | 方法选择顺序 |
|------|------------|------------|
| **层级** | 全局（所有指标） | 局部（单个指标内部） |
| **作用范围** | 9个指标 | 6种方法（pump_flow_rate） |
| **执行策略** | 指标间串行 | 方法间优先级选择 |
| **实现位置** | Scheduler | MethodSelector |
| **是否并行** | 设备间并行 | 不并行（选择一种方法） |

---

**总结**: 指标计算顺序功能已成功实施，为后续的指标计算提供了清晰的执行顺序管理。请注意区分"指标计算顺序"和"方法选择顺序"这两个不同的概念。

