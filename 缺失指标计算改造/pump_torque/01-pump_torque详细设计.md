# pump_torque 详细设计

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5

---

## 📊 指标概述

### 基本信息

| 项目 | 内容 |
|------|------|
| 指标ID | 20 |
| metric_key | pump_torque |
| 中文名称 | 泵扭矩 |
| 英文名称 | Pump Torque |
| 单位 | N·m |
| 设备类型 | pump（水泵，device_id=1-6） |
| 业务重要性 | 高 |

### 业务背景

**定义**：泵扭矩是指泵轴上的转矩，是评估泵机械负载的关键指标。

**业务价值**：
1. **负载监控**：监测泵的实际机械负载
2. **故障诊断**：异常扭矩可能指示机械故障（轴承磨损、叶轮损坏等）
3. **性能评估**：评估泵的机械性能
4. **维护预测**：扭矩变化趋势可用于预测性维护

**计算挑战**：
1. 依赖pump_speed（新实现的指标）
2. 需要两种计算方法互相验证
3. 需要考虑转速和功率的准确性

---

## 📋 依赖指标清单

### 原始测量指标

| metric_id | metric_key | 中文名称 | 单位 | 来源设备 | 必需性 |
|-----------|-----------|---------|------|---------|--------|
| 2 | pump_active_power | 泵有功功率 | kW | device_id=1-6 | 必需 |

### 新实现指标

| metric_id | metric_key | 中文名称 | 单位 | 来源设备 | 必需性 |
|-----------|-----------|---------|------|---------|--------|
| 19 | pump_speed | 泵转速 | rpm | device_id=1-6 | 必需 |

### 已实现指标（method_b使用）

| metric_id | metric_key | 中文名称 | 单位 | 来源设备 | 必需性 |
|-----------|-----------|---------|------|---------|--------|
| 18 | pump_flow_rate | 泵流量 | m³/h | device_id=1-6 | 可选 |
| 17 | pump_head | 泵扬程 | m | device_id=1-6 | 可选 |

### 说明

- **pump_active_power**：泵有功功率，从 `fact_measurements` 表获取
- **pump_speed**：泵转速，新实现，从 `fact_measurements` 表获取
- **pump_flow_rate, pump_head**：用于method_b，已实现

---

## 🔧 计算方法详细设计

### 方法配置总览

| 方法ID | 方法名称 | 优先级 | 依赖指标 | 参数来源 | 适用场景 |
|--------|---------|--------|---------|---------|---------|
| method_a | 功率-转速法 | 100 | pump_active_power, pump_speed | calculation_parameters | 标准工况 |
| method_b | 水力功率法 | 90 | pump_flow_rate, pump_head, pump_speed | calculation_parameters | 交叉验证 |

---

### 方法1：method_a - 功率-转速法

**物理原理**：
扭矩等于功率除以角速度。

**计算公式**：
```
T = P × 60 / (2π × n)
```

**参数说明**：
- `T`：泵扭矩（N·m）
- `P`：泵有功功率（kW），从pump_active_power获取，需转换为W（乘以1000）
- `n`：泵转速（rpm），从pump_speed获取

**公式推导**：
```
T = P / ω  (基本公式，其中ω为角速度，单位rad/s)
ω = 2π × n / 60  (n为转速，单位rpm)
T = P / (2π × n / 60)
  = P × 60 / (2π × n)
  = (P × 1000) × 60 / (2π × n)  (P从kW转换为W)
  = 60000 × P / (2π × n)  (N·m)

简化为：
T = 9549.3 × P / n  (N·m，其中P单位为kW，n单位为rpm)
或
T = P × 60 / (2π × n) × 1000  (N·m)
```

**适用条件**：
- pump_active_power数据可用
- pump_speed数据可用

**优点**：
- 物理意义明确
- 计算简单快速
- 适用于所有工况

**缺点**：
- 依赖pump_speed的准确性

---

### 方法2：method_b - 水力功率法

**物理原理**：
扭矩等于水力功率除以角速度。

**计算公式**：
```
T = ρ × g × Q × H / (2π × n)
```

**参数说明**：
- `T`：泵扭矩（N·m）
- `ρ`：液体密度（kg/m³），默认1000（水）
- `g`：重力加速度（m/s²），默认9.81
- `Q`：泵流量（m³/h），从pump_flow_rate获取，需转换为m³/s（除以3600）
- `H`：泵扬程（m），从pump_head获取
- `n`：泵转速（rpm），从pump_speed获取，需转换为rad/s（乘以2π/60）

**公式推导**：
```
P_h = ρ × g × Q × H  (水力功率，单位W)
T = P_h / ω
  = ρ × g × Q × H / (2π × n / 60)
  = ρ × g × (Q/3600) × H × 60 / (2π × n)
  = ρ × g × Q × H / (2π × n × 60)  (N·m)
```

**参数配置**（calculation_parameters表）：
```json
{
  "metric_key": "pump_torque",
  "method_id": "method_b",
  "param_key": "rho",
  "param_value": 1000.0,
  "param_unit": "kg/m³"
}
{
  "metric_key": "pump_torque",
  "method_id": "method_b",
  "param_key": "g",
  "param_value": 9.81,
  "param_unit": "m/s²"
}
```

**适用条件**：
- pump_flow_rate数据可用
- pump_head数据可用
- pump_speed数据可用

**优点**：
- 基于水力参数，可用于交叉验证
- 物理意义明确

**缺点**：
- 依赖更多指标
- 计算复杂度较高

---

## 📥 数据获取模块设计

### DataLoader类

**职责**：从数据库加载计算所需的数据

**输入参数**：
- `station_id`：泵站ID
- `device_ids`：设备ID列表（1-6）
- `start_time`：开始时间
- `end_time`：结束时间
- `trace_id`：追踪ID

**SQL查询**：
```sql
SELECT 
    fm.ts_bucket,
    fm.device_id,
    fm.metric_id,
    fm.value,
    dr.running
FROM fact_measurements fm
LEFT JOIN mv_device_running_1s dr 
    ON fm.ts_bucket = dr.ts_bucket 
    AND fm.device_id = dr.device_id
WHERE fm.station_id = :station_id
  AND fm.device_id IN (1,2,3,4,5,6)  -- 泵设备
  AND fm.metric_id IN (2, 19, 18, 17)  -- pump_active_power, pump_speed, pump_flow_rate, pump_head
  AND fm.ts_bucket >= :start_time
  AND fm.ts_bucket < :end_time
ORDER BY fm.ts_bucket, fm.device_id
```

**数据透视**：
将长表转换为宽表，每行包含：
- `ts_bucket`：时间戳
- `device_id`：设备ID（1-6）
- `pump_active_power`：泵有功功率（kW）
- `pump_speed`：泵转速（rpm）
- `pump_flow_rate`：泵流量（m³/h，可选）
- `pump_head`：泵扬程（m，可选）
- `running`：运行状态（0/1）

**返回格式**：
```python
pd.DataFrame({
    'ts_bucket': [...],
    'device_id': [...],
    'pump_active_power': [...],
    'pump_speed': [...],
    'pump_flow_rate': [...],  # 可选
    'pump_head': [...],  # 可选
    'running': [...]
})
```

---

## 🔍 数据过滤模块设计

### DataFilter类

**职责**：过滤非运行状态的数据

**过滤逻辑**：
```python
# 使用mv_device_running_1s.running字段
filtered_data = data[data['running'] == 1].copy()
```

**强制约束**：
- ✅ 必须使用 `mv_device_running_1s.running` 字段
- ❌ 严格禁止硬编码阈值（如 f_thr, p_thr）

**日志输出**：
- 原始数据行数
- 过滤后数据行数
- 过滤比例

---

## 🎯 方法选择模块设计

### MethodSelector类

**职责**：根据数据可用性选择最优计算方法

**方法配置**：
```python
METHODS = [
    {
        'id': 'method_a',
        'priority': 100,
        'dependencies': ['pump_active_power', 'pump_speed'],
        'conditions': {}
    },
    {
        'id': 'method_b',
        'priority': 90,
        'dependencies': ['pump_flow_rate', 'pump_head', 'pump_speed'],
        'conditions': {
            'has_calc_params': ['rho', 'g']
        }
    }
]
```

**选择逻辑**：
1. 检查method_a依赖（pump_active_power, pump_speed）
2. 如果method_a可用，返回method_a
3. 否则检查method_b依赖（pump_flow_rate, pump_head, pump_speed）
4. 如果method_b可用，返回method_b
5. 否则返回None

**日志输出**：
- 方法选择过程
- 失败原因（依赖缺失、参数缺失）
- 最终选择的方法

---

## 🧮 计算执行模块设计

### Calculator类

**职责**：执行具体的计算方法

**方法分发**：
```python
def calculate(self, data, method_id, params):
    if method_id == 'method_a':
        return self._method_a(data, params)
    elif method_id == 'method_b':
        return self._method_b(data, params)
    else:
        raise ValueError(f"未知方法: {method_id}")
```

**method_a实现**：
```python
def _method_a(self, data, calc_params):
    # 计算扭矩
    # T = P × 60 / (2π × n) × 1000 (N·m)
    # 或 T = 9549.3 × P / n (N·m)
    P = data['pump_active_power']  # kW
    n = data['pump_speed']  # rpm
    
    T = 9549.3 * P / n  # N·m
    
    result = data.copy()
    result['pump_torque'] = T
    result['method'] = 'method_a'
    
    return result
```

**method_b实现**：
```python
def _method_b(self, data, calc_params):
    # 获取计算参数
    rho = calc_params.get('rho', 1000.0)  # kg/m³
    g = calc_params.get('g', 9.81)  # m/s²
    
    # 计算扭矩
    # T = ρ × g × Q × H / (2π × n × 60) (N·m)
    Q = data['pump_flow_rate']  # m³/h
    H = data['pump_head']  # m
    n = data['pump_speed']  # rpm
    
    import numpy as np
    T = rho * g * Q * H / (2 * np.pi * n * 60)  # N·m
    
    result = data.copy()
    result['pump_torque'] = T
    result['method'] = 'method_b'
    
    return result
```

---

## ✅ 结果验证模块设计

### Validator类

**职责**：验证计算结果的合理性，标记数据质量

**验证规则**：

#### 1. 范围检查
```python
# 泵扭矩合理范围：0 - 10000 N·m
valid_range = (result['pump_torque'] >= 0) & \
              (result['pump_torque'] <= 10000)
```

#### 2. 交叉验证（如果有两种方法的结果）
```python
# 双方法差异应小于10%
if 'pump_torque_method_a' in result.columns and 'pump_torque_method_b' in result.columns:
    deviation = abs(result['pump_torque_method_a'] - result['pump_torque_method_b']) / \
                result['pump_torque_method_a']
    valid_cross = deviation <= 0.10
else:
    valid_cross = True  # 如果只有一种方法，跳过此检查
```

#### 3. 异常值检查
```python
# 相邻时刻扭矩变化应小于500 N·m/s
diff = result['pump_torque'].diff()
valid_outlier = abs(diff) <= 500
```

**质量标记**：
- `valid`：所有检查通过
- `out_of_range`：超出合理范围
- `cross_validation_failed`：交叉验证失败
- `outlier`：异常值

**日志输出**：
- 验证统计（总数、有效数、无效数）
- 异常数量（out_of_range, cross_validation_failed, outlier）
- 质量分布（各质量标记的数量和比例）

---

## 📊 参数配置清单

### calculation_parameters表

| metric_key | method_id | param_key | param_value | param_unit | 说明 |
|-----------|-----------|-----------|-------------|-----------|------|
| pump_torque | method_b | rho | 1000.0 | kg/m³ | 液体密度（水） |
| pump_torque | method_b | g | 9.81 | m/s² | 重力加速度 |
| pump_torque | validation | min_torque | 0.0 | N·m | 最小扭矩 |
| pump_torque | validation | max_torque | 10000.0 | N·m | 最大扭矩 |
| pump_torque | validation | max_deviation | 0.10 | - | 最大偏差（10%） |
| pump_torque | validation | max_change_rate | 500.0 | N·m/s | 最大变化率 |

---

## 🔗 依赖关系

### 上游依赖

- **pump_active_power**（metric_id=2）：必需，原始测量
- **pump_speed**（metric_id=19）：必需，新实现
- **pump_flow_rate**（metric_id=18）：可选，已实现
- **pump_head**（metric_id=17）：可选，已实现

### 下游依赖

- 无

### 计算顺序

- **METRIC_ORDER位置**：第7位（第二层，依赖pump_speed）

---

## 📈 数据流示例

### 输入数据示例

```python
# DataLoader输出
{
    'ts_bucket': ['2025-10-22 08:00:00', '2025-10-22 08:00:01', ...],
    'device_id': [1, 1, ...],
    'pump_active_power': [85.2, 85.5, ...],  # kW
    'pump_speed': [1485.0, 1486.0, ...],  # rpm
    'pump_flow_rate': [1800.0, 1805.0, ...],  # m³/h (可选)
    'pump_head': [25.5, 25.6, ...],  # m (可选)
    'running': [1, 1, ...]
}
```

### 输出数据示例（method_a）

```python
# Validator输出（添加质量标记）
{
    'ts_bucket': ['2025-10-22 08:00:00', '2025-10-22 08:00:01', ...],
    'device_id': [1, 1, ...],
    'pump_active_power': [85.2, 85.5, ...],
    'pump_speed': [1485.0, 1486.0, ...],
    'running': [1, 1, ...],
    'pump_torque': [548.2, 549.1, ...],  # N·m
    'method': ['method_a', 'method_a', ...],
    'valid_range': [True, True, ...],
    'valid_outlier': [True, True, ...],
    'quality': ['valid', 'valid', ...]
}
```

### 输出数据示例（method_b）

```python
# Validator输出（添加质量标记）
{
    'ts_bucket': ['2025-10-22 08:00:00', '2025-10-22 08:00:01', ...],
    'device_id': [1, 1, ...],
    'pump_flow_rate': [1800.0, 1805.0, ...],
    'pump_head': [25.5, 25.6, ...],
    'pump_speed': [1485.0, 1486.0, ...],
    'running': [1, 1, ...],
    'pump_torque': [545.8, 546.7, ...],  # N·m
    'method': ['method_b', 'method_b', ...],
    'valid_range': [True, True, ...],
    'valid_outlier': [True, True, ...],
    'quality': ['valid', 'valid', ...]
}
```

---

## 🔄 Pipeline流程设计

### PumpTorquePipeline类

**职责**：编排所有组件，执行完整的计算流水线

**流程图**：
```
DataLoader → DataFilter → MethodSelector → Calculator → Validator → 返回结果
```

**实现示例**：
```python
class PumpTorquePipeline:
    def __init__(self, db_manager, param_manager, trace_id):
        self.data_loader = PumpTorqueDataLoader(db_manager, trace_id)
        self.data_filter = PumpTorqueDataFilter(trace_id)
        self.method_selector = PumpTorqueMethodSelector(trace_id)
        self.calculator = PumpTorqueCalculator(trace_id)
        self.validator = PumpTorqueValidator(param_manager, trace_id)
        self.trace_id = trace_id

    def run(self, station_id, device_ids, start_time, end_time, params):
        # 1. 加载数据
        data = self.data_loader.load(station_id, device_ids, start_time, end_time)

        # 2. 过滤数据
        filtered_data = self.data_filter.filter(data)

        # 3. 选择方法
        method_id = self.method_selector.select_method(filtered_data, params)

        # 4. 执行计算
        calculated_data = self.calculator.calculate(filtered_data, method_id, params)

        # 5. 验证结果
        validated_data = self.validator.validate(calculated_data, params)

        return validated_data
```

---

**文档结束**

