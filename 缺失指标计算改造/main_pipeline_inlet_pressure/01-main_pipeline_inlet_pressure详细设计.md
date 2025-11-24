# main_pipeline_inlet_pressure 详细设计

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5

---

## 📊 指标概述

### 基本信息

| 项目 | 内容 |
|------|------|
| 指标ID | 61 |
| metric_key | main_pipeline_inlet_pressure |
| 中文名称 | 总管进口压力 |
| 英文名称 | Main Pipeline Inlet Pressure |
| 单位 | MPa |
| 设备类型 | main_pipeline（总管，device_id=7） |
| 业务重要性 | 高 |

### 业务背景

**定义**：总管进口压力是指水泵出口汇集到总管入口处的压力，反映了泵站整体的出水压力水平。

**业务价值**：
1. **系统监控**：监测泵站整体出水压力，确保供水系统正常运行
2. **压力控制**：为压力控制策略提供关键数据
3. **能效分析**：评估泵站整体能效水平
4. **故障诊断**：异常压力可能指示系统故障

**计算挑战**：
1. 总管进口压力受多个泵的联合影响
2. 需要考虑水池液位的静压贡献
3. 需要考虑管道阻力损失
4. 压力波动可能较大

---

## 📋 依赖指标清单

### 原始测量指标

| metric_id | metric_key | 中文名称 | 单位 | 来源设备 | 必需性 |
|-----------|-----------|---------|------|---------|--------|
| 5 | pool_liquid_level | 水池液位 | m | device_id=8 | 必需 |

### 说明

- **pool_liquid_level**：水池液位，用于计算静压部分
- **数据来源**：从 `fact_measurements` 表获取，metric_id=5, device_id=8

---

## 🔧 计算方法详细设计

### 方法配置总览

| 方法ID | 方法名称 | 优先级 | 依赖指标 | 参数来源 | 适用场景 |
|--------|---------|--------|---------|---------|---------|
| method_b | 静压法 | 100 | pool_liquid_level | calculation_parameters | 标准工况 |
| PIN_COEF_V1 | 等效系数法 | 90 | pool_liquid_level | calculation_parameters | 需要高精度 |

---

### 方法1：method_b - 静压法

**物理原理**：
总管进口压力主要由水池液位产生的静压决定，加上大气压力。

**计算公式**：
```
P_in = P_atm + ρ × g × h / 1e6
```

**参数说明**：
- `P_in`：总管进口压力（MPa）
- `P_atm`：大气压力（MPa），默认0.101325
- `ρ`：水的密度（kg/m³），默认1000
- `g`：重力加速度（m/s²），默认9.81
- `h`：水池液位（m），从pool_liquid_level获取

**参数配置**（calculation_parameters表）：
```json
{
  "metric_key": "main_pipeline_inlet_pressure",
  "method_id": "method_b",
  "param_key": "P_atm",
  "param_value": 0.101325,
  "param_unit": "MPa"
}
{
  "metric_key": "main_pipeline_inlet_pressure",
  "method_id": "method_b",
  "param_key": "rho",
  "param_value": 1000.0,
  "param_unit": "kg/m³"
}
{
  "metric_key": "main_pipeline_inlet_pressure",
  "method_id": "method_b",
  "param_key": "g",
  "param_value": 9.81,
  "param_unit": "m/s²"
}
```

**适用条件**：
- pool_liquid_level数据可用
- 水池液位在合理范围内（0-10m）

**优点**：
- 物理意义明确
- 计算简单快速
- 适用于大多数工况

**缺点**：
- 忽略了管道阻力损失
- 忽略了动压部分
- 精度中等

---

### 方法2：PIN_COEF_V1 - 等效系数法

**物理原理**：
使用多项式拟合水池液位与总管进口压力的关系，考虑了非线性因素。

**计算公式**：
```
P_in = b0 + b1×h + b2×h² + b3×h³
```

**参数说明**：
- `P_in`：总管进口压力（MPa）
- `h`：水池液位（m）
- `b0, b1, b2, b3`：拟合系数，需要现场校准

**参数配置**（calculation_parameters表）：
```json
{
  "metric_key": "main_pipeline_inlet_pressure",
  "method_id": "PIN_COEF_V1",
  "param_key": "b0",
  "param_value": 0.101325,
  "param_unit": "MPa"
}
{
  "metric_key": "main_pipeline_inlet_pressure",
  "method_id": "PIN_COEF_V1",
  "param_key": "b1",
  "param_value": 0.00981,
  "param_unit": "MPa/m"
}
{
  "metric_key": "main_pipeline_inlet_pressure",
  "method_id": "PIN_COEF_V1",
  "param_key": "b2",
  "param_value": 0.0,
  "param_unit": "MPa/m²"
}
{
  "metric_key": "main_pipeline_inlet_pressure",
  "method_id": "PIN_COEF_V1",
  "param_key": "b3",
  "param_value": 0.0,
  "param_unit": "MPa/m³"
}
```

**适用条件**：
- pool_liquid_level数据可用
- 已完成现场校准（b0-b3参数）

**优点**：
- 可以考虑非线性因素
- 精度更高（如果校准准确）
- 可适应复杂工况

**缺点**：
- 需要现场校准数据
- 参数不准确时精度反而降低

---

## 📥 数据获取模块设计

### DataLoader类

**职责**：从数据库加载计算所需的原始数据

**输入参数**：
- `station_id`：泵站ID
- `device_id`：设备ID（固定为7，总管设备）
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
  AND fm.device_id = 7  -- 总管设备
  AND fm.metric_id IN (5)  -- pool_liquid_level
  AND fm.ts_bucket >= :start_time
  AND fm.ts_bucket < :end_time
ORDER BY fm.ts_bucket, fm.device_id
```

**数据透视**：
将长表转换为宽表，每行包含：
- `ts_bucket`：时间戳
- `device_id`：设备ID（7）
- `pool_liquid_level`：水池液位（m）
- `running`：运行状态（0/1）

**返回格式**：
```python
pd.DataFrame({
    'ts_bucket': [...],
    'device_id': [...],
    'pool_liquid_level': [...],
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
        'id': 'method_b',
        'priority': 100,
        'dependencies': ['pool_liquid_level'],
        'conditions': {}
    },
    {
        'id': 'PIN_COEF_V1',
        'priority': 90,
        'dependencies': ['pool_liquid_level'],
        'conditions': {
            'calibration_quality': ['medium', 'high']
        }
    }
]
```

**选择逻辑**：
1. 按优先级从高到低遍历方法
2. 检查依赖指标是否存在（pool_liquid_level列）
3. 检查条件是否满足（calibration_quality参数）
4. 返回第一个满足条件的方法

**日志输出**：
- 方法选择过程
- 失败原因（依赖缺失、条件不满足）
- 最终选择的方法

---

## 🧮 计算执行模块设计

### Calculator类

**职责**：执行具体的计算方法

**方法分发**：
```python
def calculate(self, data, method_id, params):
    if method_id == 'method_b':
        return self._method_b(data, params)
    elif method_id == 'PIN_COEF_V1':
        return self._PIN_COEF_V1(data, params)
    else:
        raise ValueError(f"未知方法: {method_id}")
```

**method_b实现**：
```python
def _method_b(self, data, params):
    P_atm = params.get('P_atm', 0.101325)
    rho = params.get('rho', 1000.0)
    g = params.get('g', 9.81)
    
    h = data['pool_liquid_level']
    P_in = P_atm + rho * g * h / 1e6
    
    result = data.copy()
    result['main_pipeline_inlet_pressure'] = P_in
    result['method'] = 'method_b'
    return result
```

**PIN_COEF_V1实现**：
```python
def _PIN_COEF_V1(self, data, params):
    b0 = params.get('b0', 0.101325)
    b1 = params.get('b1', 0.00981)
    b2 = params.get('b2', 0.0)
    b3 = params.get('b3', 0.0)
    
    h = data['pool_liquid_level']
    P_in = b0 + b1*h + b2*h**2 + b3*h**3
    
    result = data.copy()
    result['main_pipeline_inlet_pressure'] = P_in
    result['method'] = 'PIN_COEF_V1'
    return result
```

---

## ✅ 结果验证模块设计

### Validator类

**职责**：验证计算结果的合理性，标记数据质量

**验证规则**：

#### 1. 范围检查
```python
# 总管进口压力合理范围：0.05 - 1.0 MPa
valid_range = (result['main_pipeline_inlet_pressure'] >= 0.05) & \
              (result['main_pipeline_inlet_pressure'] <= 1.0)
```

#### 2. 物理约束检查
```python
# 压力应与液位正相关
# P_in ≈ P_atm + ρ×g×h/1e6
# 允许±20%偏差
expected_P = 0.101325 + 1000 * 9.81 * result['pool_liquid_level'] / 1e6
deviation = abs(result['main_pipeline_inlet_pressure'] - expected_P) / expected_P
valid_physics = deviation <= 0.20
```

#### 3. 异常值检查
```python
# 相邻时刻压力变化应小于0.05 MPa/s
diff = result['main_pipeline_inlet_pressure'].diff()
valid_outlier = abs(diff) <= 0.05
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
| main_pipeline_inlet_pressure | method_b | P_atm | 0.101325 | MPa | 大气压力 |
| main_pipeline_inlet_pressure | method_b | rho | 1000.0 | kg/m³ | 水的密度 |
| main_pipeline_inlet_pressure | method_b | g | 9.81 | m/s² | 重力加速度 |
| main_pipeline_inlet_pressure | PIN_COEF_V1 | b0 | 0.101325 | MPa | 拟合系数0 |
| main_pipeline_inlet_pressure | PIN_COEF_V1 | b1 | 0.00981 | MPa/m | 拟合系数1 |
| main_pipeline_inlet_pressure | PIN_COEF_V1 | b2 | 0.0 | MPa/m² | 拟合系数2 |
| main_pipeline_inlet_pressure | PIN_COEF_V1 | b3 | 0.0 | MPa/m³ | 拟合系数3 |
| main_pipeline_inlet_pressure | validation | min_pressure | 0.05 | MPa | 最小压力 |
| main_pipeline_inlet_pressure | validation | max_pressure | 1.0 | MPa | 最大压力 |
| main_pipeline_inlet_pressure | validation | max_deviation | 0.20 | - | 最大偏差比例 |
| main_pipeline_inlet_pressure | validation | max_change_rate | 0.05 | MPa/s | 最大变化率 |

### device_rated_params表

**不需要**：main_pipeline_inlet_pressure不需要设备级参数

---

## 📈 数据流示例

### 输入数据示例

```python
# DataLoader输出
{
    'ts_bucket': ['2025-10-22 08:00:00', '2025-10-22 08:00:01', ...],
    'device_id': [7, 7, ...],
    'pool_liquid_level': [5.2, 5.21, ...],
    'running': [1, 1, ...]
}
```

### 中间数据示例

```python
# DataFilter输出（过滤running=0的数据）
{
    'ts_bucket': ['2025-10-22 08:00:00', '2025-10-22 08:00:01', ...],
    'device_id': [7, 7, ...],
    'pool_liquid_level': [5.2, 5.21, ...],
    'running': [1, 1, ...]
}

# Calculator输出（添加计算结果和方法标记）
{
    'ts_bucket': ['2025-10-22 08:00:00', '2025-10-22 08:00:01', ...],
    'device_id': [7, 7, ...],
    'pool_liquid_level': [5.2, 5.21, ...],
    'running': [1, 1, ...],
    'main_pipeline_inlet_pressure': [0.152, 0.153, ...],
    'method': ['method_b', 'method_b', ...]
}
```

### 输出数据示例

```python
# Validator输出（添加质量标记）
{
    'ts_bucket': ['2025-10-22 08:00:00', '2025-10-22 08:00:01', ...],
    'device_id': [7, 7, ...],
    'pool_liquid_level': [5.2, 5.21, ...],
    'running': [1, 1, ...],
    'main_pipeline_inlet_pressure': [0.152, 0.153, ...],
    'method': ['method_b', 'method_b', ...],
    'valid_range': [True, True, ...],
    'valid_physics': [True, True, ...],
    'valid_outlier': [True, True, ...],
    'quality': ['valid', 'valid', ...]
}
```

---

## 🔗 依赖关系

### 上游依赖

- **pool_liquid_level**（metric_id=5）：必需，从device_id=8获取

### 下游依赖

- **无**：main_pipeline_inlet_pressure不被其他指标依赖

### 计算顺序

- **METRIC_ORDER位置**：第2位（第一层，仅依赖原始测量数据）

---

## 📝 实施注意事项

### 关键约束

1. **运行状态判断**：必须使用 `mv_device_running_1s.running` 字段，禁止硬编码阈值
2. **参数加载**：所有参数必须从 `calculation_parameters` 表加载，禁止硬编码
3. **设备ID**：main_pipeline_inlet_pressure仅计算device_id=7（总管设备）
4. **数据来源**：pool_liquid_level从device_id=8获取

### 性能优化

1. **SQL优化**：使用索引加速查询（ts_bucket, device_id, metric_id）
2. **批量处理**：使用自适应分片，避免一次加载过多数据
3. **参数缓存**：ParameterManager缓存参数，避免重复查询

### 测试要点

1. **数据完整性**：验证pool_liquid_level数据存在
2. **计算正确性**：验证公式实现正确
3. **质量标记**：验证验证规则正确
4. **性能**：验证计算耗时符合要求（<30秒）

---

## 📚 参考资料

- **架构文档**：`缺失指标计算改造/pump_flow_rate/05-pump_flow_rate详细设计.md`
- **数据库规范**：`.memory/规则层/数据库规范.md`
- **项目规则**：`.memory/规则层/项目规则.md`
- **依赖关系验证**：`缺失指标计算改造/00-依赖关系验证报告.md`

---

**文档结束**


