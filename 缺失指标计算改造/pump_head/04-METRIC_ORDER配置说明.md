# METRIC_ORDER 配置说明

> **文档版本**: v1.0  
> **创建日期**: 2025-11-17  
> **状态**: 配置指南  
> **协议**: RIPER-5

---

## 📋 问题分析

### 问题1：pump_outlet_pressure 是否应该添加到 METRIC_ORDER？

**答案**：❌ **不应该添加**

**原因**：
- `pump_outlet_pressure` 和 `pump_head` 是在**同一个计算函数**中同时计算的
- `pump_outlet_pressure` 是 `pump_head` 计算的**中间结果**，不是独立的计算任务
- Scheduler 会根据 METRIC_ORDER 中的每个指标调用对应的 `calculate_xxx()` 函数
- 如果添加 `pump_outlet_pressure`，Scheduler 会尝试调用不存在的 `calculate_pump_outlet_pressure()` 函数，导致错误

### 问题2：pump_head 和 pump_outlet_pressure 的关系

**关系**：
- `pump_head` 是**主指标**（在 METRIC_ORDER 中）
- `pump_outlet_pressure` 是**副产品指标**（不在 METRIC_ORDER 中）
- 两者在 `calculate_pump_head()` 函数中**同时计算**，**同时写入**数据库

**类比**：
- 就像一个函数返回两个值：`(result1, result2) = calculate()`
- 但 Scheduler 只需要知道调用这个函数，不需要知道它返回了几个值

---

## 📊 依赖关系分析

### pump_head 的依赖

**直接依赖**：
1. `pump_inlet_pressure`（泵进口压力）
2. `main_pipeline_outlet_pressure`（总管出口压力，测量值）
3. `pump_flow_rate`（泵流量）
4. `device_running`（设备运行状态，测量值）

**依赖层级**：
```
pump_head
├── pump_inlet_pressure（计算值）
│   ├── pool_liquid_level（测量值）
│   └── pump_flow_rate（计算值）
├── main_pipeline_outlet_pressure（测量值）
├── pump_flow_rate（计算值）
│   ├── main_pipeline_flow_rate（测量值）
│   ├── pump_active_power（测量值）
│   └── pump_frequency（测量值）
└── device_running（测量值）
```

**计算顺序要求**：
1. 先计算 `pump_flow_rate`（因为 pump_inlet_pressure 和 pump_head 都依赖它）
2. 再计算 `pump_inlet_pressure`（因为 pump_head 依赖它）
3. 最后计算 `pump_head`

---

## ✅ 正确的 METRIC_ORDER 配置

### 当前配置（scheduler.py）

**文件**：`app/services/calculation/shared/scheduler.py`

**正确配置**：
```python
METRIC_ORDER = [
    "pump_flow_rate",          # 1. 水泵流量（基础指标）
    "pump_inlet_pressure",     # 2. 水泵入口压力（依赖 pump_flow_rate）
    "pump_head",               # 3. 水泵扬程（依赖 pump_inlet_pressure, pump_flow_rate）
                               #    同时计算 pump_outlet_pressure
    "pump_efficiency",         # 4. 水泵效率（依赖 pump_flow_rate, pump_head）
    # ... 其他指标
]
```

### 错误配置示例

**❌ 错误1：添加 pump_outlet_pressure**
```python
METRIC_ORDER = [
    "pump_flow_rate",
    "pump_inlet_pressure",
    "pump_outlet_pressure",  # ❌ 错误：会导致 NotImplementedError
    "pump_head",
]
```

**错误原因**：
- Scheduler 会尝试调用 `calculate_pump_outlet_pressure()`
- 但这个函数不存在（pump_outlet_pressure 在 calculate_pump_head() 中计算）
- 导致 `NotImplementedError: 指标 pump_outlet_pressure 的计算器尚未实现`

**❌ 错误2：pump_head 在 pump_inlet_pressure 之前**
```python
METRIC_ORDER = [
    "pump_flow_rate",
    "pump_head",              # ❌ 错误：依赖的 pump_inlet_pressure 还未计算
    "pump_inlet_pressure",
]
```

**错误原因**：
- pump_head 依赖 pump_inlet_pressure
- 如果 pump_head 先计算，pump_inlet_pressure 的数据还不存在
- 导致计算失败或使用旧数据

---

## 🔍 验证方法

### 验证1：检查 METRIC_ORDER

```python
from app.services.calculation.shared.scheduler import Scheduler

scheduler = Scheduler()
print("METRIC_ORDER:", scheduler.METRIC_ORDER)

# 预期输出：
# METRIC_ORDER: ['pump_flow_rate', 'pump_inlet_pressure', 'pump_head', ...]
# 注意：不应该包含 'pump_outlet_pressure'
```

### 验证2：检查计算函数注册

```python
from app.services.calculation.shared.scheduler import Scheduler

scheduler = Scheduler()

# 测试 pump_head 的计算函数
try:
    func = scheduler._get_calculator_func('pump_head')
    print(f"pump_head 计算函数: {func.__name__}")  # 应该输出: calculate_pump_head
except NotImplementedError as e:
    print(f"错误: {e}")

# 测试 pump_outlet_pressure 的计算函数（应该失败）
try:
    func = scheduler._get_calculator_func('pump_outlet_pressure')
    print(f"pump_outlet_pressure 计算函数: {func.__name__}")
except NotImplementedError as e:
    print(f"预期错误: {e}")  # 应该输出: 指标 pump_outlet_pressure 的计算器尚未实现
```

### 验证3：检查数据写入

```sql
-- 验证两个指标的数据量一致
SELECT 
    mc.metric_key,
    COUNT(*) as count,
    MIN(fm.ts_bucket) as start_time,
    MAX(fm.ts_bucket) as end_time
FROM fact_measurements fm
JOIN dim_metric_config mc ON mc.id = fm.metric_id
WHERE fm.device_id = 1
  AND mc.metric_key IN ('pump_outlet_pressure', 'pump_head')
  AND fm.ts_bucket >= '2025-01-01 00:00:00'
GROUP BY mc.metric_key;

-- 预期结果：两个指标的 count 应该相同
```

---

## 📝 总结

### 关键要点

1. **pump_outlet_pressure 不应该添加到 METRIC_ORDER**
   - 它是 pump_head 计算的副产品
   - 没有独立的 calculate_pump_outlet_pressure() 函数

2. **METRIC_ORDER 只包含主指标**
   - pump_flow_rate
   - pump_inlet_pressure
   - pump_head（同时计算 pump_outlet_pressure）

3. **计算顺序必须遵循依赖关系**
   - pump_flow_rate → pump_inlet_pressure → pump_head

4. **两个指标都会写入数据库**
   - pump_outlet_pressure 和 pump_head 都会写入 fact_measurements 表
   - 但只有 pump_head 在 METRIC_ORDER 中

---

## 文档结束

