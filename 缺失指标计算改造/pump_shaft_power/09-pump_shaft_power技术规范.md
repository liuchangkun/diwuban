# pump_shaft_power 技术规范

> **协议**: RIPER-5 计划模式  
> **日期**: 2025-11-22  
> **状态**: 技术规范  
> **参考**: pump_torque实际实现

---

## 📋 目录结构

```
app/services/calculation/metrics/pump_shaft_power/
├── __init__.py                    # 模块入口
├── pipeline.py                    # 流水线编排器
├── data_loader.py                 # 数据加载器
├── data_filter.py                 # 数据过滤器
├── method_selector.py             # 方法选择器
├── calculator.py                  # 计算执行器
├── validator.py                   # 结果验证器
└── methods/
    ├── __init__.py                # 方法模块入口
    └── method_a.py                # 电机效率法
```

---

## 🔧 共享模块接入方案

### 1. SharedServices单例

**位置**: `app/services/calculation/shared/shared_services.py`

**使用方式**:
```python
from app.services.calculation.shared.shared_services import SharedServices

# 获取单例实例
shared_services = SharedServices()

# 访问共享服务
shared_services.scheduler          # 任务调度器
shared_services.data_writer        # 数据写入器
shared_services.parameter_manager  # 参数管理器
shared_services.logger             # 日志记录器
```

**关键约束**:
- ✅ 全局唯一实例（单例模式）
- ✅ 自动初始化所有共享服务
- ✅ 线程安全

---

### 2. ParameterManager（参数管理）

**职责**: 从数据库加载参数配置

**使用方式**:
```python
# 在Pipeline中加载参数
params = shared_services.parameter_manager.get_parameters(
    station_id=station_id,
    device_id=device_id,
    metric_key='pump_shaft_power'
)

# 返回格式
{
    'max_power': 200.0,           # 从calculation_parameters加载
    'max_change_rate': 50.0,      # 从calculation_parameters加载
    'device_params': {            # 从device_rated_params加载
        1: {'eta_motor': 0.92, 'eta_vfd': 0.97},
        2: {'eta_motor': 0.92, 'eta_vfd': 0.97},
        ...
    }
}
```

**参数来源**:
- `calculation_parameters` 表: 全局/泵站/设备级参数
- `device_rated_params` 表: 设备额定参数（eta_motor, eta_vfd）

**三级优先级**: 设备 > 泵站 > 全局

---

### 3. DataWriter（数据写入）

**职责**: 批量写入计算结果到fact_measurements表

**使用方式**:
```python
# 在Pipeline中写入结果
write_result = shared_services.data_writer.write_batch(
    station_id=station_id,
    records=records,  # List[WriteRecord]
    metric_key='pump_shaft_power'
)

# WriteRecord格式
from app.services.calculation.shared.data_writer import WriteRecord

records = [
    WriteRecord(
        ts_bucket=row['ts_bucket'],
        device_id=row['device_id'],
        value=row['pump_shaft_power'],
        quality_code=row['quality_code']
    )
    for _, row in validated_data.iterrows()
]
```

**自适应批量管理**:
- 初始批量大小: 1000条
- 目标写入耗时: 500ms
- 自动调整批量大小

---

### 4. Scheduler（任务调度）

**职责**: 任务分片、并行调度、进度跟踪

**使用方式**:
```python
# 调度单个指标计算
result = shared_services.scheduler.schedule_single_metric(
    metric_key='pump_shaft_power',
    device_ids=[1, 2, 3, 4, 5, 6],
    start_time=datetime(2025, 10, 22, 8, 0, 0),
    end_time=datetime(2025, 10, 23, 7, 0, 0),
    time_chunk_hours=1
)
```

**METRIC_ORDER配置**:
```python
# 文件: app/services/calculation/shared/scheduler.py
METRIC_ORDER = [
    "pump_flow_rate",
    "pump_inlet_pressure",
    "main_pipeline_inlet_pressure",
    "pump_speed",
    "pump_shaft_power",  # ✨ 新增（第5位）
    "pump_head",
    "pump_torque",
    "pump_efficiency",
    "main_pipeline_outlet_pressure",
]
```

---

## 📊 数据库参数配置

### 1. device_rated_params表

**SQL脚本**: `scripts/init_pump_shaft_power_params.sql`

```sql
-- 为设备1-6添加eta_motor和eta_vfd参数
INSERT INTO device_rated_params (
    station_id, device_id, param_key, value_numeric, unit, source
) VALUES
    (1, 1, 'eta_motor', 0.92, '-', 'manual'),
    (1, 1, 'eta_vfd', 0.97, '-', 'manual'),
    (1, 2, 'eta_motor', 0.92, '-', 'manual'),
    (1, 2, 'eta_vfd', 0.97, '-', 'manual'),
    (1, 3, 'eta_motor', 0.92, '-', 'manual'),
    (1, 3, 'eta_vfd', 0.97, '-', 'manual'),
    (1, 4, 'eta_motor', 0.92, '-', 'manual'),
    (1, 4, 'eta_vfd', 0.97, '-', 'manual'),
    (1, 5, 'eta_motor', 0.92, '-', 'manual'),
    (1, 5, 'eta_vfd', 0.97, '-', 'manual'),
    (1, 6, 'eta_motor', 0.92, '-', 'manual'),
    (1, 6, 'eta_vfd', 0.97, '-', 'manual')
ON CONFLICT (station_id, device_id, param_key) DO UPDATE
SET value_numeric = EXCLUDED.value_numeric,
    updated_at = CURRENT_TIMESTAMP;
```

---

### 2. calculation_parameters表

```sql
-- 添加pump_shaft_power的验证参数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, 
    param_name, param_value, param_type
) VALUES
    -- 全局参数（data_filter使用）
    (NULL, NULL, 'pump_shaft_power', 'data_filter', 'max_power', 200.0, 'float'),
    
    -- 验证参数
    (NULL, NULL, 'pump_shaft_power', 'validation', 'min_power', 0.0, 'float'),
    (NULL, NULL, 'pump_shaft_power', 'validation', 'max_power', 500.0, 'float'),
    (NULL, NULL, 'pump_shaft_power', 'validation', 'max_change_rate', 50.0, 'float')
ON CONFLICT (station_id, device_id, metric_key, method_id, param_name) DO UPDATE
SET param_value = EXCLUDED.param_value,
    updated_at = CURRENT_TIMESTAMP;
```

---

## 🎯 核心计算公式

### method_a: 电机效率法

**公式**:
```
P_shaft = P_active / (η_motor × η_vfd)
```

**参数**:
- `P_active`: 泵有功功率（kW），从pump_active_power获取
- `η_motor`: 电机效率（无量纲），从device_rated_params获取
- `η_vfd`: 变频器效率（无量纲），从device_rated_params获取
- `P_shaft`: 泵轴功率（kW）

**物理意义**:
- 电机输入功率经过电机和变频器损失后，传递到泵轴的有效功率
- η_motor × η_vfd < 1，因此 P_shaft > P_active

---

## 📝 模块实现规范

### 1. __init__.py

**职责**: 模块入口，导出Pipeline类

```python
"""
pump_shaft_power 指标计算模块

职责：
- 计算泵轴功率（P_shaft = P_active / (η_motor × η_vfd)）
- 使用电机效率法（method_a）
"""

from .pipeline import PumpShaftPowerPipeline

__all__ = ['PumpShaftPowerPipeline']
```

---

### 2. pipeline.py

**职责**: 流水线编排器，管理6阶段执行流程

**关键点**:
- ✅ 使用SharedServices获取参数
- ✅ 按顺序执行6个阶段
- ✅ 记录详细日志（trace_id/span_id）
- ✅ 使用DataWriter写入结果
- ✅ 处理空数据情况

**参考**: `app/services/calculation/metrics/pump_torque/pipeline.py`

**核心流程**:
```python
def execute(self, station_id, device_id, start_time, end_time, task_id):
    # 1. 加载参数
    params = shared_services.parameter_manager.get_parameters(...)

    # 2. DataLoader
    raw_data = loader.load_data(...)
    if raw_data.empty:
        return {'success': True, 'skipped': True}

    # 3. DataFilter
    filtered_data = filter.filter_data(raw_data, params)

    # 4. MethodSelector
    method_id = selector.select_method(filtered_data, params)

    # 5. Calculator
    calculated_data = calculator.calculate(filtered_data, method_id)

    # 6. Validator
    validated_data = validator.validate(calculated_data, method_id)

    # 7. DataWriter
    written_count = shared_services.data_writer.write_batch(...)

    return {'success': True, 'written_count': written_count}
```

---

### 3. data_loader.py

**职责**: 从数据库加载pump_active_power和running状态

**SQL查询**:
```sql
WITH metric_ids AS (
    SELECT id, metric_key
    FROM dim_metric_config
    WHERE metric_key = 'pump_active_power'
)
SELECT
    fm.ts_bucket,
    fm.device_id,
    mc.metric_key,
    fm.value,
    COALESCE(dr.running, 1) AS running
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

**数据透视**:
```python
pivot_data = df.pivot_table(
    index=['ts_bucket', 'device_id', 'running'],
    columns='metric_key',
    values='value',
    aggfunc='first'
).reset_index()
```

**返回格式**:
```python
DataFrame({
    'ts_bucket': [...],
    'device_id': [...],
    'pump_active_power': [...],  # float
    'running': [...]              # int (0/1)
})
```

**设备类型检查**:
```python
# 检查设备类型，只处理type='pump'的设备
cur.execute("SELECT type FROM dim_devices WHERE id = %s", (device_id,))
if device_type != 'pump':
    return pd.DataFrame()  # 返回空数据
```

---

### 4. data_filter.py

**职责**: 过滤无效数据

**过滤逻辑**:
```python
def filter_data(self, data: pd.DataFrame) -> pd.DataFrame:
    # 1. 停机状态过滤（使用running字段）
    data = data[data['running'] == 1]

    # 2. NaN/Inf过滤
    data = data.dropna(subset=['pump_active_power'])
    data = data[~data['pump_active_power'].isin([np.inf, -np.inf])]

    # 3. 负值过滤
    data = data[data['pump_active_power'] >= 0]

    # 4. 异常值过滤（从params获取阈值）
    max_power = self.max_power  # 从__init__传入
    data = data[data['pump_active_power'] <= max_power]

    return data
```

**构造函数**:
```python
def __init__(self, max_power: float, trace_id: Optional[str] = None):
    # 验证必需参数
    if max_power is None:
        raise ValueError("缺少必需参数: max_power")

    self.max_power = max_power
    self.trace_id = trace_id
```

**关键约束**:
- ❌ 严格禁止硬编码阈值
- ✅ 必须从params获取所有阈值
- ✅ 必须使用running字段

---

### 5. method_selector.py

**职责**: 选择计算方法（仅method_a）

**方法配置**:
```python
METHODS = [
    {
        'id': 'method_a',
        'name': '电机效率法',
        'priority': 100,
        'dependencies': ['pump_active_power'],
        'conditions': {
            'has_device_params': ['eta_motor', 'eta_vfd']
        }
    }
]
```

**选择逻辑**:
```python
def select_method(self, data: pd.DataFrame) -> str:
    # 检查pump_active_power列存在
    if 'pump_active_power' not in data.columns:
        raise ValueError("缺少依赖列: pump_active_power")

    # 检查设备参数存在（在Pipeline中已验证）
    # 直接返回method_a
    return 'method_a'
```

---

### 6. calculator.py

**职责**: 执行计算方法

**核心实现**:
```python
def calculate(self, data: pd.DataFrame, method_id: str) -> pd.DataFrame:
    if method_id == 'method_a':
        from .methods import method_a
        result = method_a.calculate(data, self.params)
    else:
        raise ValueError(f"无效的方法ID: {method_id}")

    # 添加method_id列
    result['method_id'] = method_id

    return result
```

---

### 7. validator.py

**职责**: 验证计算结果

**验证规则**:
```python
def validate(self, data: pd.DataFrame, method_id: str) -> pd.DataFrame:
    result = data.copy()

    # 获取验证参数
    max_power = self.params.get('max_power', 500.0)

    # 1. 范围检查
    result['quality_code'] = 0  # 默认高质量
    result.loc[
        (result['pump_shaft_power'] < 0) |
        (result['pump_shaft_power'] > max_power),
        'quality_code'
    ] = 2  # 范围异常

    # 2. 效率检查（关键）
    result.loc[
        result['pump_shaft_power'] <= result['pump_active_power'],
        'quality_code'
    ] = 3  # 效率违反

    # 3. NaN/Inf检查
    result.loc[
        result['pump_shaft_power'].isna() |
        result['pump_shaft_power'].isin([np.inf, -np.inf]),
        'quality_code'
    ] = 2

    # 4. 过滤无效数据
    valid_data = result[result['quality_code'] == 0].copy()

    return valid_data
```

---

### 8. methods/method_a.py

**职责**: 电机效率法实现

```python
def calculate(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """
    电机效率法计算泵轴功率

    公式: P_shaft = P_active / (η_motor × η_vfd)
    """
    result = data.copy()

    # 获取设备参数
    device_params = params.get('device_params', {})
    device_id = data['device_id'].iloc[0]

    eta_motor = device_params.get(device_id, {}).get('eta_motor', 0.92)
    eta_vfd = device_params.get(device_id, {}).get('eta_vfd', 0.97)

    # 计算轴功率
    result['pump_shaft_power'] = (
        result['pump_active_power'] / (eta_motor * eta_vfd)
    )

    return result
```

---

**文档结束**


