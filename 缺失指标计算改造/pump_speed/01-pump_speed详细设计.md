# pump_speed 详细设计文档

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5

---

## 📋 目录

1. [指标概述](#指标概述)
2. [计算方法详细设计](#计算方法详细设计)
3. [数据获取模块详细设计](#数据获取模块详细设计)
4. [数据过滤模块详细设计](#数据过滤模块详细设计)
5. [方法选择模块详细设计](#方法选择模块详细设计)
6. [计算执行模块详细设计](#计算执行模块详细设计)
7. [结果验证模块详细设计](#结果验证模块详细设计)
8. [参数配置清单](#参数配置清单)
9. [完整数据流示例](#完整数据流示例)
10. [日志输出完整示例](#日志输出完整示例)

---

## 指标概述

### 指标定义

**指标键**: `pump_speed`  
**指标ID**: 19  
**指标名称**: 水泵转速  
**单位**: rpm  
**物理意义**: 水泵转子的旋转速度

### 业务背景

水泵转速是泵站运行的基础参数之一，用于：
- **扭矩计算**：T = P × 60 / (2π × n)
- **振动分析**：转速是振动频率的基础
- **工况优化**：转速与流量、扬程的关系
- **能耗分析**：转速影响泵的效率

### 计算挑战

1. **缺失测量**：大部分水泵没有直接的转速传感器
2. **滑差影响**：异步电机的实际转速低于同步转速
3. **非标准电机**：部分电机可能不是标准4极电机
4. **校准需求**：高精度应用需要现场校准

### 依赖指标

| 指标键 | 指标ID | 指标名称 | 用途 | 数据来源 |
|--------|--------|----------|------|----------|
| `pump_frequency` | 1 | 水泵频率 | 转速计算基础 | 传感器测量 |

### 计算方法概览

| 方法ID | 方法名称 | 优先级 | 适用场景 | 准确度 |
|--------|----------|--------|----------|--------|
| method_a | 频率比例法 | 100 | 标准工况，无校准数据 | 中等 |
| method_b | 极对数法 | 90 | 有极对数和滑差参数 | 高 |
| method_c | 校准系数法 | 80 | 有现场校准数据 | 最高 |

---

## 计算方法详细设计

### 方法1：频率比例法（method_a）

#### 物理原理

基于同步转速与频率的线性关系，忽略滑差影响。

#### 计算公式

```
n = (f / f_ref) × n_ref

参数说明：
- n: 实际转速（rpm）
- f: 实际频率（Hz）
- f_ref: 额定频率（Hz，默认50.0）
- n_ref: 额定转速（rpm，默认1500.0，对应4极电机）
```

#### 依赖数据

**测量数据**：
- `pump_frequency`：水泵频率（Hz）

**配置参数**（calculation_parameters表）：
- `f_ref`：额定频率（Hz，默认50.0）
- `n_ref`：额定转速（rpm，默认1500.0）

#### 适用条件

1. ✅ `pump_frequency` 数据存在
2. ✅ 无需设备特定参数
3. ✅ 适用于标准4极电机

#### 准确度

- **预期准确度**：±2%（忽略滑差）
- **影响因素**：
  - 滑差影响（主要，约2%）
  - 频率测量误差（次要）

#### 特殊处理

**频率为0的处理**：
```python
if f <= 0:
    n = 0.0
    quality_flag = 'valid'  # 停机时转速为0是正常的
```

---

### 方法2：极对数法（method_b）

#### 物理原理

基于异步电机的同步转速公式，考虑滑差影响。

#### 计算公式

```
n = 60 × f / pole_pairs × (1 - slip)

参数说明：
- n: 实际转速（rpm）
- f: 实际频率（Hz）
- pole_pairs: 极对数（默认2，对应4极电机）
- slip: 滑差率（默认0.02，即2%）

推导：
同步转速: n_sync = 60 × f / pole_pairs
实际转速: n = n_sync × (1 - slip)
```

#### 依赖数据

**测量数据**：
- `pump_frequency`：水泵频率（Hz）

**配置参数**（device_rated_params表）：
- `pole_pairs`：极对数（默认2）
- `slip`：滑差率（默认0.02）

#### 适用条件

1. ✅ `pump_frequency` 数据存在
2. ✅ `pole_pairs` 参数已配置
3. ✅ `slip` 参数已配置

#### 准确度

- **预期准确度**：±0.5%
- **影响因素**：
  - 滑差参数准确性（主要）
  - 频率测量误差（次要）

---

### 方法3：校准系数法（method_c）

#### 物理原理

基于现场校准数据，使用线性拟合公式。

#### 计算公式

```
n = calibration_a × f + calibration_b

参数说明：
- n: 实际转速（rpm）
- f: 实际频率（Hz）
- calibration_a: 校准系数a（斜率）
- calibration_b: 校准系数b（截距）
```

#### 依赖数据

**测量数据**：
- `pump_frequency`：水泵频率（Hz）

**配置参数**（calculation_parameters表）：
- `calibration_a`：校准系数a（默认30.0）
- `calibration_b`：校准系数b（默认0.0）
- `calibration_quality`：校准质量（low/medium/high）

#### 适用条件

1. ✅ `pump_frequency` 数据存在
2. ✅ `calibration_a` 和 `calibration_b` 参数已配置
3. ✅ `calibration_quality` 为 'medium' 或 'high'

#### 准确度

- **预期准确度**：±0.2%（高质量校准）
- **影响因素**：
  - 校准数据质量（主要）
  - 频率测量误差（次要）

#### 校准方法

**现场校准步骤**：
1. 使用转速传感器测量实际转速
2. 记录对应的频率值
3. 收集多个工况点（建议10个以上）
4. 使用线性回归拟合：n = a × f + b
5. 更新calibration_a和calibration_b参数
6. 设置calibration_quality为'high'

---

## 数据获取模块详细设计

### 模块职责

**核心职责**：
- 从 `fact_measurements` 表加载 `pump_frequency` 数据
- 从 `mv_device_running_1s` 表加载设备运行状态数据
- **只负责数据获取，不进行任何过滤**（过滤由 DataFilter 负责）
- 返回原始数据（包括停机设备的数据）

**设计原则**：
- ✅ 数据获取与运行状态判断分离
- ✅ 使用单个SQL查询获取所有数据（避免多次查询）
- ✅ 在Python中进行透视操作（将长表转为宽表）
- ✅ 不使用硬编码阈值判断运行状态（使用 `mv_device_running_1s.running` 字段）

### 类定义

```python
class PumpSpeedDataLoader(DataLoader):
    """pump_speed 数据获取模块"""

    def __init__(self, trace_id: Optional[str] = None):
        super().__init__(trace_id)
        self.metric_key = 'pump_speed'

        # 依赖指标配置
        self.dependencies = {
            'pump_frequency': {
                'required': True,
                'level': 'device',  # 设备级指标
                'description': '水泵频率'
            }
        }
```

### SQL查询设计

```sql
WITH metric_ids AS (
    SELECT id, metric_key
    FROM dim_metric_config
    WHERE metric_key = 'pump_frequency'
)
SELECT
    fm.ts_bucket,
    fm.device_id,
    mc.metric_key,
    fm.value,
    COALESCE(dr.running, 0) AS running
FROM fact_measurements fm
JOIN metric_ids mc ON mc.id = fm.metric_id
LEFT JOIN mv_device_running_1s dr
    ON dr.station_id = fm.station_id
   AND dr.device_id = fm.device_id
   AND dr.ts_bucket = fm.ts_bucket
WHERE fm.station_id = %(station_id)s
  AND fm.device_id = %(device_id)s
  AND fm.ts_bucket >= %(start_time)s
  AND fm.ts_bucket < %(end_time)s
ORDER BY fm.ts_bucket
```

### 返回数据格式

```python
DataFrame with columns:
- ts_bucket: 时间戳（秒级）
- device_id: 设备ID
- pump_frequency: 水泵频率（Hz）
- running: 运行状态（0=停止, 1=运行）
```

---

## 数据过滤模块详细设计

### 模块职责

**核心职责**：
- 过滤运行状态数据（仅保留 `running=1` 的数据）
- **强制要求**：必须使用 `mv_device_running_1s.running` 字段
- **严格禁止**：不允许使用任何硬编码阈值（如 f_thr）

### 类定义

```python
class PumpSpeedDataFilter(DataFilter):
    """pump_speed 数据过滤模块"""

    def filter_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        过滤数据（仅保留运行状态的数据）

        Args:
            data: 原始数据（包含running列）

        Returns:
            过滤后的数据
        """
        # 过滤运行状态
        filtered = data[data['running'] == 1].copy()

        self.logger.info(
            "[数据过滤] 运行状态过滤完成",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                '原始行数': len(data),
                '过滤后行数': len(filtered),
                '过滤比例': f"{(1 - len(filtered)/len(data))*100:.1f}%"
            }}
        )

        return filtered
```

---

## 方法选择模块详细设计

### 模块职责

**核心职责**：
- 根据数据可用性和参数配置，选择最合适的计算方法
- 按优先级顺序检查方法可用性（100 → 80）
- 返回方法ID

### 方法配置

```python
METHODS = [
    {
        'id': 'method_c',
        'name': '校准系数法',
        'priority': 80,
        'dependencies': ['pump_frequency'],
        'conditions': {
            'has_params': ['calibration_a', 'calibration_b'],
            'calibration_quality': ['medium', 'high']
        }
    },
    {
        'id': 'method_b',
        'name': '极对数法',
        'priority': 90,
        'dependencies': ['pump_frequency'],
        'conditions': {
            'has_device_params': ['pole_pairs', 'slip']
        }
    },
    {
        'id': 'method_a',
        'name': '频率比例法',
        'priority': 100,
        'dependencies': ['pump_frequency'],
        'conditions': {}
    }
]
```

### 选择逻辑

```python
def select_method(self, data: pd.DataFrame) -> str:
    """选择计算方法（按优先级顺序）"""

    # 按优先级检查每个方法
    for method in sorted(self.METHODS, key=lambda x: x['priority'], reverse=True):
        # 检查依赖
        if not self._check_dependencies(data, method['dependencies']):
            continue

        # 检查条件
        if not self._check_conditions(method['conditions']):
            continue

        # 找到可用方法
        return method['id']

    # 无可用方法
    raise ValueError("无可用的计算方法")
```

---

## 计算执行模块详细设计

### 模块职责

**核心职责**：
- 执行具体的计算逻辑
- 支持多种计算方法
- 返回计算结果

### 类定义

```python
class PumpSpeedCalculator(Calculator):
    """pump_speed 计算执行模块"""

    def calculate(
        self,
        data: pd.DataFrame,
        method_id: str,
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """执行计算"""

        if method_id == 'method_a':
            return self._method_a(data, params)
        elif method_id == 'method_b':
            return self._method_b(data, params)
        elif method_id == 'method_c':
            return self._method_c(data, params)
        else:
            raise ValueError(f"未知的计算方法: {method_id}")
```

### 方法实现

**Method A: 频率比例法**
```python
def _method_a(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
    """频率比例法"""
    f_ref = params['f_ref']  # 50.0
    n_ref = params['n_ref']  # 1500.0

    results = data.copy()
    results['value'] = (results['pump_frequency'] / f_ref) * n_ref
    results['method'] = 'method_a'

    return results
```

**Method B: 极对数法**
```python
def _method_b(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
    """极对数法"""
    pole_pairs = params['pole_pairs']  # 2
    slip = params['slip']  # 0.02

    results = data.copy()
    results['value'] = 60 * results['pump_frequency'] / pole_pairs * (1 - slip)
    results['method'] = 'method_b'

    return results
```

**Method C: 校准系数法**
```python
def _method_c(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
    """校准系数法"""
    calibration_a = params['calibration_a']
    calibration_b = params['calibration_b']

    results = data.copy()
    results['value'] = calibration_a * results['pump_frequency'] + calibration_b
    results['method'] = 'method_c'

    return results
```

---

## 结果验证模块详细设计

### 模块职责

**核心职责**：
- 验证计算结果的合理性
- 标记异常数据
- 生成质量报告

### 验证规则

**规则1：范围检查**
```python
min_speed = 0.0  # rpm
max_speed = 3000.0  # rpm

valid_range = (results['value'] >= min_speed) & (results['value'] <= max_speed)
```

**规则2：物理约束检查**
```python
# 转速与频率的关系检查（粗略）
expected_speed = results['pump_frequency'] * 30  # 假设4极电机
speed_ratio = results['value'] / expected_speed
valid_physics = (speed_ratio >= 0.9) & (speed_ratio <= 1.1)
```

**规则3：异常值检查**
```python
# 相邻时刻转速变化检查
max_change_rate = 100.0  # rpm/s
speed_diff = results['value'].diff().abs()
time_diff = results['ts_bucket'].diff().dt.total_seconds()
change_rate = speed_diff / time_diff
valid_outlier = change_rate <= max_change_rate
```

### 质量标记

```python
results['quality'] = 'valid'
results.loc[~valid_range, 'quality'] = 'out_of_range'
results.loc[~valid_physics, 'quality'] = 'physics_violation'
results.loc[~valid_outlier, 'quality'] = 'outlier'
```

---

## 参数配置清单

### calculation_parameters表

| param_key | param_value | description |
|-----------|-------------|-------------|
| f_ref | 50.0 | 额定频率(Hz) |
| n_ref | 1500.0 | 额定转速(rpm) |
| calibration_a | 30.0 | 校准系数a（默认值） |
| calibration_b | 0.0 | 校准系数b（默认值） |
| calibration_quality | low | 校准质量 |
| min_speed | 0.0 | 最小转速(rpm) |
| max_speed | 3000.0 | 最大转速(rpm) |
| max_speed_change_rate | 100.0 | 最大转速变化率(rpm/s) |

### device_rated_params表

| param_key | value_numeric | description |
|-----------|---------------|-------------|
| pole_pairs | 2 | 极对数 |
| slip | 0.02 | 滑差率 |

---

**文档结束**


