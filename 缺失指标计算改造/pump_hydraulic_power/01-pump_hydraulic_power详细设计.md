# pump_hydraulic_power 详细设计

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5

---

## 📊 指标概述

### 基本信息

| 项目 | 内容 |
|------|------|
| 指标ID | 67 |
| metric_key | pump_hydraulic_power |
| 中文名称 | 泵水力功率 |
| 英文名称 | Pump Hydraulic Power |
| 单位 | kW |
| 设备类型 | pump（水泵，device_id=1-6） |
| 业务重要性 | 高 |

### 业务背景

**定义**：泵水力功率是指泵传递给液体的有效功率，是评估泵实际做功能力的关键指标。

**业务价值**：
1. **效率计算**：计算泵效率的分子（η = P_h / P_shaft）
2. **性能评估**：评估泵的实际输出能力
3. **能效分析**：分析泵的能量转换效率
4. **故障诊断**：异常水力功率可能指示水力部件故障

**计算挑战**：
1. 依赖已实现的指标（pump_flow_rate, pump_head）
2. 需要准确的流量和扬程数据
3. 需要考虑流体密度和重力加速度

---

## 📋 依赖指标清单

### 已实现指标

| metric_id | metric_key | 中文名称 | 单位 | 来源设备 | 必需性 |
|-----------|-----------|---------|------|---------|--------|
| 18 | pump_flow_rate | 泵流量 | m³/h | device_id=1-6 | 必需 |
| 17 | pump_head | 泵扬程 | m | device_id=1-6 | 必需 |

### 说明

- **pump_flow_rate**：泵流量，已实现，从 `fact_measurements` 表获取
- **pump_head**：泵扬程，已实现，从 `fact_measurements` 表获取

---

## 🔧 计算方法详细设计

### 方法配置总览

| 方法ID | 方法名称 | 优先级 | 依赖指标 | 参数来源 | 适用场景 |
|--------|---------|--------|---------|---------|---------|
| method_a | 流量-扬程法 | 100 | pump_flow_rate, pump_head | calculation_parameters | 标准工况 |

---

### 方法1：method_a - 流量-扬程法

**物理原理**：
泵水力功率等于单位时间内泵传递给液体的能量，由流量和扬程决定。

**计算公式**：
```
P_h = ρ × g × Q × H / 1000
```

**参数说明**：
- `P_h`：泵水力功率（kW）
- `ρ`：液体密度（kg/m³），默认1000（水）
- `g`：重力加速度（m/s²），默认9.81
- `Q`：泵流量（m³/h），从pump_flow_rate获取，需转换为m³/s（除以3600）
- `H`：泵扬程（m），从pump_head获取

**公式推导**：
```
P_h = ρ × g × Q × H  (单位：W)
    = ρ × g × (Q/3600) × H  (Q从m³/h转换为m³/s)
    = ρ × g × Q × H / 3600  (W)
    = ρ × g × Q × H / 3600 / 1000  (kW)
    = ρ × g × Q × H / 3600000  (kW)

简化为：
P_h = ρ × g × Q × H / 1000  (kW，其中Q单位为m³/h)
注：分母1000包含了单位转换（3600）和W→kW转换（1000）的简化
```

**参数配置**（calculation_parameters表）：
```json
{
  "metric_key": "pump_hydraulic_power",
  "method_id": "method_a",
  "param_key": "rho",
  "param_value": 1000.0,
  "param_unit": "kg/m³"
}
{
  "metric_key": "pump_hydraulic_power",
  "method_id": "method_a",
  "param_key": "g",
  "param_value": 9.81,
  "param_unit": "m/s²"
}
```

**适用条件**：
- pump_flow_rate数据可用
- pump_head数据可用

**优点**：
- 物理意义明确
- 计算简单快速
- 适用于所有工况

**缺点**：
- 依赖pump_flow_rate和pump_head的准确性

---

## 📥 数据获取模块设计

### DataLoader类

**职责**：从数据库加载计算所需的已实现指标数据

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
  AND fm.metric_id IN (18, 17)  -- pump_flow_rate, pump_head
  AND fm.ts_bucket >= :start_time
  AND fm.ts_bucket < :end_time
ORDER BY fm.ts_bucket, fm.device_id
```

**数据透视**：
将长表转换为宽表，每行包含：
- `ts_bucket`：时间戳
- `device_id`：设备ID（1-6）
- `pump_flow_rate`：泵流量（m³/h）
- `pump_head`：泵扬程（m）
- `running`：运行状态（0/1）

**返回格式**：
```python
pd.DataFrame({
    'ts_bucket': [...],
    'device_id': [...],
    'pump_flow_rate': [...],
    'pump_head': [...],
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
        'dependencies': ['pump_flow_rate', 'pump_head'],
        'conditions': {
            'has_calc_params': ['rho', 'g']
        }
    }
]
```

**选择逻辑**：
1. 检查依赖指标是否存在（pump_flow_rate, pump_head列）
2. 检查计算参数是否存在（rho, g）
3. 返回method_a（唯一方法）

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
    else:
        raise ValueError(f"未知方法: {method_id}")
```

**method_a实现**：
```python
def _method_a(self, data, calc_params):
    # 获取计算参数
    rho = calc_params.get('rho', 1000.0)  # kg/m³
    g = calc_params.get('g', 9.81)  # m/s²
    
    # 计算水力功率
    # P_h = ρ × g × Q × H / 1000 (kW)
    # 其中Q单位为m³/h，H单位为m
    Q = data['pump_flow_rate']  # m³/h
    H = data['pump_head']  # m
    
    P_h = rho * g * Q * H / 1000.0  # kW
    
    result = data.copy()
    result['pump_hydraulic_power'] = P_h
    result['method'] = 'method_a'
    
    return result
```

---

## ✅ 结果验证模块设计

### Validator类

**职责**：验证计算结果的合理性，标记数据质量

**验证规则**：

#### 1. 范围检查
```python
# 泵水力功率合理范围：0 - 400 kW
valid_range = (result['pump_hydraulic_power'] >= 0) & \
              (result['pump_hydraulic_power'] <= 400)
```

#### 2. 物理约束检查
```python
# 水力功率应小于轴功率（如果轴功率已计算）
# P_h < P_shaft
# 注：此检查需要pump_shaft_power数据，可选
if 'pump_shaft_power' in result.columns:
    valid_physics = result['pump_hydraulic_power'] < result['pump_shaft_power']
else:
    valid_physics = True  # 如果没有轴功率数据，跳过此检查
```

#### 3. 异常值检查
```python
# 相邻时刻水力功率变化应小于40 kW/s
diff = result['pump_hydraulic_power'].diff()
valid_outlier = abs(diff) <= 40
```

**质量标记**：
- `valid`：所有检查通过
- `out_of_range`：超出合理范围
- `physics_violation`：违反物理约束
- `outlier`：异常值

**日志输出**：
- 验证统计（总数、有效数、无效数）
- 异常数量（out_of_range, physics_violation, outlier）
- 质量分布（各质量标记的数量和比例）

---

## 📊 参数配置清单

### calculation_parameters表

| metric_key | method_id | param_key | param_value | param_unit | 说明 |
|-----------|-----------|-----------|-------------|-----------|------|
| pump_hydraulic_power | method_a | rho | 1000.0 | kg/m³ | 液体密度（水） |
| pump_hydraulic_power | method_a | g | 9.81 | m/s² | 重力加速度 |
| pump_hydraulic_power | validation | min_power | 0.0 | kW | 最小水力功率 |
| pump_hydraulic_power | validation | max_power | 400.0 | kW | 最大水力功率 |
| pump_hydraulic_power | validation | max_change_rate | 40.0 | kW/s | 最大变化率 |

---

## 📈 数据流示例

### 输入数据示例

```python
# DataLoader输出
{
    'ts_bucket': ['2025-10-22 08:00:00', '2025-10-22 08:00:01', ...],
    'device_id': [1, 1, ...],
    'pump_flow_rate': [1800.0, 1805.0, ...],  # m³/h
    'pump_head': [25.5, 25.6, ...],  # m
    'running': [1, 1, ...]
}
```

### 输出数据示例

```python
# Validator输出（添加质量标记）
{
    'ts_bucket': ['2025-10-22 08:00:00', '2025-10-22 08:00:01', ...],
    'device_id': [1, 1, ...],
    'pump_flow_rate': [1800.0, 1805.0, ...],
    'pump_head': [25.5, 25.6, ...],
    'running': [1, 1, ...],
    'pump_hydraulic_power': [124.5, 125.0, ...],  # kW
    'method': ['method_a', 'method_a', ...],
    'valid_range': [True, True, ...],
    'valid_physics': [True, True, ...],
    'valid_outlier': [True, True, ...],
    'quality': ['valid', 'valid', ...]
}
```

---

## 🔗 依赖关系

### 上游依赖

- **pump_flow_rate**（metric_id=18）：必需，已实现
- **pump_head**（metric_id=17）：必需，已实现

### 下游依赖

- **pump_efficiency**（metric_id=21）：可能依赖pump_hydraulic_power

### 计算顺序

- **METRIC_ORDER位置**：第8位（第三层，依赖已实现的指标）

---

**文档结束**

