# pump_shaft_power 详细设计

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5

---

## 📊 指标概述

### 基本信息

| 项目 | 内容 |
|------|------|
| 指标ID | 66 |
| metric_key | pump_shaft_power |
| 中文名称 | 泵轴功率 |
| 英文名称 | Pump Shaft Power |
| 单位 | kW |
| 设备类型 | pump（水泵，device_id=1-6） |
| 业务重要性 | 高 |

### 业务背景

**定义**：泵轴功率是指电机传递到泵轴上的机械功率，是电机输出功率扣除传动损失后的有效功率。

**业务价值**：
1. **能效分析**：计算泵效率的关键参数（η = P_h / P_shaft）
2. **设备监控**：监测泵的实际负载情况
3. **故障诊断**：异常轴功率可能指示机械故障
4. **成本核算**：评估泵的实际能耗

**计算挑战**：
1. 需要准确的电机效率和变频器效率参数
2. 效率参数随负载率变化
3. 需要考虑传动方式（直驱、变频驱动）

---

## 📋 依赖指标清单

### 原始测量指标

| metric_id | metric_key | 中文名称 | 单位 | 来源设备 | 必需性 |
|-----------|-----------|---------|------|---------|--------|
| 2 | pump_active_power | 泵有功功率 | kW | device_id=1-6 | 必需 |

### 说明

- **pump_active_power**：泵的有功功率（电机输入功率），从 `fact_measurements` 表获取

---

## 🔧 计算方法详细设计

### 方法配置总览

| 方法ID | 方法名称 | 优先级 | 依赖指标 | 参数来源 | 适用场景 |
|--------|---------|--------|---------|---------|---------|
| method_a | 电机效率法 | 100 | pump_active_power | device_rated_params | 标准工况 |

---

### 方法1：method_a - 电机效率法

**物理原理**：
泵轴功率等于电机输入功率扣除电机损失和变频器损失。

**计算公式**：
```
P_shaft = P_active / (η_motor × η_vfd)
```

**参数说明**：
- `P_shaft`：泵轴功率（kW）
- `P_active`：泵有功功率（kW），从pump_active_power获取
- `η_motor`：电机效率（无量纲），从device_rated_params获取
- `η_vfd`：变频器效率（无量纲），从device_rated_params获取

**参数配置**（device_rated_params表）：
```json
{
  "device_id": 1,
  "param_key": "eta_motor",
  "value_numeric": 0.92,
  "unit": "-"
}
{
  "device_id": 1,
  "param_key": "eta_vfd",
  "value_numeric": 0.97,
  "unit": "-"
}
```

**适用条件**：
- pump_active_power数据可用
- eta_motor和eta_vfd参数已配置

**优点**：
- 物理意义明确
- 计算简单快速
- 适用于大多数工况

**缺点**：
- 忽略了效率随负载率的变化
- 需要准确的效率参数

---

## 📥 数据获取模块设计

### DataLoader类

**职责**：从数据库加载计算所需的原始数据

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
  AND fm.metric_id IN (2)  -- pump_active_power
  AND fm.ts_bucket >= :start_time
  AND fm.ts_bucket < :end_time
ORDER BY fm.ts_bucket, fm.device_id
```

**数据透视**：
将长表转换为宽表，每行包含：
- `ts_bucket`：时间戳
- `device_id`：设备ID（1-6）
- `pump_active_power`：泵有功功率（kW）
- `running`：运行状态（0/1）

**返回格式**：
```python
pd.DataFrame({
    'ts_bucket': [...],
    'device_id': [...],
    'pump_active_power': [...],
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

**职责**：根据数据可用性和参数配置选择最优计算方法

**方法配置**：
```python
METHODS = [
    {
        'id': 'method_a',
        'priority': 100,
        'dependencies': ['pump_active_power'],
        'conditions': {
            'has_device_params': ['eta_motor', 'eta_vfd']
        }
    }
]
```

**选择逻辑**：
1. 检查依赖指标是否存在（pump_active_power列）
2. 检查设备参数是否存在（eta_motor, eta_vfd）
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
def _method_a(self, data, device_params):
    # 获取设备参数（每个设备可能不同）
    result = data.copy()
    
    for device_id in data['device_id'].unique():
        mask = data['device_id'] == device_id
        eta_motor = device_params.get(device_id, {}).get('eta_motor', 0.92)
        eta_vfd = device_params.get(device_id, {}).get('eta_vfd', 0.97)
        
        P_active = data.loc[mask, 'pump_active_power']
        P_shaft = P_active / (eta_motor * eta_vfd)
        
        result.loc[mask, 'pump_shaft_power'] = P_shaft
    
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
# 泵轴功率合理范围：0 - 500 kW
valid_range = (result['pump_shaft_power'] >= 0) & \
              (result['pump_shaft_power'] <= 500)
```

#### 2. 效率检查
```python
# 轴功率应大于有功功率（η_motor × η_vfd < 1）
# P_shaft > P_active
valid_efficiency = result['pump_shaft_power'] > result['pump_active_power']
```

#### 3. 异常值检查
```python
# 相邻时刻轴功率变化应小于50 kW/s
diff = result['pump_shaft_power'].diff()
valid_outlier = abs(diff) <= 50
```

**质量标记**：
- `valid`：所有检查通过
- `out_of_range`：超出合理范围
- `efficiency_violation`：违反效率约束
- `outlier`：异常值

**日志输出**：
- 验证统计（总数、有效数、无效数）
- 异常数量（out_of_range, efficiency_violation, outlier）
- 质量分布（各质量标记的数量和比例）

---

## 📊 参数配置清单

### device_rated_params表

| device_id | param_key | value_numeric | unit | 说明 |
|-----------|-----------|---------------|------|------|
| 1 | eta_motor | 0.92 | - | 电机效率 |
| 1 | eta_vfd | 0.97 | - | 变频器效率 |
| 2 | eta_motor | 0.92 | - | 电机效率 |
| 2 | eta_vfd | 0.97 | - | 变频器效率 |
| ... | ... | ... | ... | ... |
| 6 | eta_motor | 0.92 | - | 电机效率 |
| 6 | eta_vfd | 0.97 | - | 变频器效率 |

### calculation_parameters表

| metric_key | method_id | param_key | param_value | param_unit | 说明 |
|-----------|-----------|-----------|-------------|-----------|------|
| pump_shaft_power | validation | min_power | 0.0 | kW | 最小轴功率 |
| pump_shaft_power | validation | max_power | 500.0 | kW | 最大轴功率 |
| pump_shaft_power | validation | max_change_rate | 50.0 | kW/s | 最大变化率 |

---

## 📈 数据流示例

### 输入数据示例

```python
# DataLoader输出
{
    'ts_bucket': ['2025-10-22 08:00:00', '2025-10-22 08:00:01', ...],
    'device_id': [1, 1, ...],
    'pump_active_power': [85.2, 85.5, ...],
    'running': [1, 1, ...]
}
```

### 输出数据示例

```python
# Validator输出（添加质量标记）
{
    'ts_bucket': ['2025-10-22 08:00:00', '2025-10-22 08:00:01', ...],
    'device_id': [1, 1, ...],
    'pump_active_power': [85.2, 85.5, ...],
    'running': [1, 1, ...],
    'pump_shaft_power': [95.5, 95.8, ...],
    'method': ['method_a', 'method_a', ...],
    'valid_range': [True, True, ...],
    'valid_efficiency': [True, True, ...],
    'valid_outlier': [True, True, ...],
    'quality': ['valid', 'valid', ...]
}
```

---

## 🔗 依赖关系

### 上游依赖

- **pump_active_power**（metric_id=2）：必需，从device_id=1-6获取

### 下游依赖

- **pump_torque**（metric_id=20）：可能依赖pump_shaft_power（method_a）

### 计算顺序

- **METRIC_ORDER位置**：第3位（第一层，仅依赖原始测量数据）

---

**文档结束**

