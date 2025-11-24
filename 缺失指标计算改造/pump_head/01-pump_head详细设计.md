# pump_head 详细设计文档

> **文档版本**: v1.0  
> **创建日期**: 2025-11-17  
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

**指标键**: `pump_head`  
**指标名称**: 水泵扬程  
**单位**: m（米）  
**物理意义**: 水泵提升液体的高度，反映水泵做功能力

### 业务背景

水泵扬程是泵站运行的核心指标之一，用于：
- **性能评估**：评估水泵的工作性能和效率
- **能耗分析**：扬程是计算水力功率和效率的基础
- **故障诊断**：扬程异常可能表明水泵或管路故障
- **系统优化**：优化泵站调度策略的关键参数

### 计算挑战

1. **缺失测量**：大部分水泵没有直接的扬程测量
2. **压力传感器缺失**：部分泵没有出口压力传感器
3. **管道损失**：从泵出口到总管存在压力损失
4. **多泵运行**：多泵并联时压力分配复杂
5. **准确度要求**：±1m（用于效率计算和性能评估）

### 依赖指标

| 指标键 | 指标名称 | 用途 | 数据来源 |
|--------|----------|------|----------|
| `pump_inlet_pressure` | 泵进口压力 | 压差计算 | 已计算值 |
| `main_pipeline_outlet_pressure` | 总管出口压力 | 泵出口压力近似 | 传感器测量 |
| `pump_flow_rate` | 泵流量 | 管道损失修正 | 已计算值 |
| `device_running` | 设备运行状态 | 统计运行泵数量 | 传感器测量 |

### 计算方法概览

| 方法ID | 方法名称 | 优先级 | 适用场景 | 准确度 |
|--------|----------|--------|----------|--------|
| PIPE_LOSS_MULTI_PUMP | 压差法（管道损失+多泵修正） | 100 | 有完整数据和参数 | 高（±0.5-1m） |

---

## 计算方法详细设计

### 方法1：压差法（管道损失+多泵修正）- PIPE_LOSS_MULTI_PUMP

#### 物理原理

基于伯努利方程，扬程等于进出口压差除以液体密度和重力加速度。

**核心思想**：
1. 使用总管出口压力作为泵出口压力的基准
2. 通过**管道损失修正**补偿从泵出口到总管的压力损失
3. 通过**多泵运行修正**补偿多泵并联时的压力分配差异

#### 计算公式

```
步骤1：计算管道损失修正
delta_P_pipe = K_pipe_loss × Q²

步骤2：统计当前运行泵数量
N_running = COUNT(device_running = 1) 在同一时刻同一泵站

步骤3：计算多泵运行修正系数
correction_factor = 1 + alpha_multi_pump × N_running / N_total

步骤4：修正后的泵出口压力
P_pump_out = P_main_out × correction_factor + delta_P_pipe

步骤5：计算扬程
H = (P_pump_out - P_pump_in) × 1e6 / (rho × g)

其中：
- P_main_out: 总管出口压力（MPa）
- P_pump_in: 泵进口压力（MPa）
- Q: 泵流量（m³/h）
- N_running: 当前运行泵数量（从数据中统计）
- N_total: 泵站总泵数量（固定值，如6）
- K_pipe_loss: 管道损失系数（MPa/(m³/h)²）- 可优化参数
- alpha_multi_pump: 多泵修正系数（无量纲）- 可优化参数
- rho: 水密度（kg/m³，固定值1000）
- g: 重力加速度（m/s²，固定值9.81）
```

#### 参数说明

| 参数名 | 类型 | 默认值 | 可优化 | 说明 |
|--------|------|--------|--------|------|
| `K_pipe_loss` | float | 0.00001 | 是 | 管道损失系数（MPa/(m³/h)²） |
| `alpha_multi_pump` | float | 0.02 | 是 | 多泵修正系数（无量纲，典型值0.01-0.05） |
| `N_total_pumps` | int | 6 | 否 | 泵站总泵数量（从数据库查询） |
| `rho` | float | 1000.0 | 否 | 水密度（kg/m³） |
| `g` | float | 9.81 | 否 | 重力加速度（m/s²） |

#### 依赖检查

**必需依赖**：
- `pump_inlet_pressure`（已计算）
- `main_pipeline_outlet_pressure`（测量值）
- `pump_flow_rate`（已计算）
- `device_running`（测量值，用于统计N_running）

**可选依赖**：
- 无

#### 适用条件

```json
{
  "description": "有完整的压力、流量和运行状态数据，使用双重修正优化",
  "has_device_params": ["K_pipe_loss", "alpha_multi_pump", "N_total_pumps"]
}
```

#### 参数物理意义

**K_pipe_loss（管道损失系数）**：
- 反映从泵出口到总管汇合点的压力损失
- 包含：摩擦损失、局部损失（阀门、弯头）
- 与流量的平方成正比（达西-魏斯巴赫公式）
- 典型值：0.00001 - 0.0001 MPa/(m³/h)²

**alpha_multi_pump（多泵修正系数）**：
- 反映多泵并联时的压力分配不均匀性
- 当多台泵运行时，总管压力略高于单泵出口压力
- 典型值：0.01 - 0.05（1% - 5%的修正）
- 运行泵数量越多，修正越大

---

## 数据获取模块详细设计

### 模块职责

**核心职责**：
- 从 `fact_measurements` 表加载计算所需的依赖指标数据
- 从 `mv_device_running_1s` 表加载设备运行状态数据
- **统计同一时刻同一泵站的运行泵数量**（用于多泵修正）
- **只负责数据获取，不进行任何过滤**（过滤由 DataFilter 负责）

**设计原则**：
- ✅ 数据获取与运行状态判断分离
- ✅ 使用单个SQL查询获取所有数据
- ✅ 在Python中进行透视操作（将长表转为宽表）
- ✅ 统计运行泵数量（N_running）

### 类定义

```python
class DataLoader:
    """pump_head 数据获取模块"""

    def __init__(self, trace_id: Optional[str] = None):
        """
        初始化数据加载器

        Args:
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id
        self.metric_key = 'pump_head'

        # 依赖指标配置
        self.dependencies = {
            'pump_inlet_pressure': {
                'required': True,
                'level': 'device',
                'description': '泵进口压力'
            },
            'main_pipeline_outlet_pressure': {
                'required': True,
                'level': 'station',
                'description': '总管出口压力'
            },
            'pump_flow_rate': {
                'required': True,
                'level': 'device',
                'description': '泵流量（用于管道损失修正）'
            }
        }
```

### SQL查询设计

```sql
-- 一次性获取所有数据（包括运行状态和运行泵数量）
WITH metric_ids AS (
    SELECT id, metric_key
    FROM dim_metric_config
    WHERE metric_key IN (
        'pump_inlet_pressure',
        'main_pipeline_outlet_pressure',
        'pump_flow_rate'
    )
),
station_pumps AS (
    -- 获取泵站下所有泵设备
    SELECT id as device_id
    FROM dim_devices
    WHERE station_id = %(station_id)s
      AND type = 'pump'
      AND is_active = true
),
device_data AS (
    -- 获取当前设备的指标数据
    SELECT
        fm.ts_bucket,
        fm.device_id,
        mc.metric_key,
        fm.value
    FROM fact_measurements fm
    JOIN metric_ids mc ON mc.id = fm.metric_id
    WHERE fm.station_id = %(station_id)s
      AND fm.device_id = %(device_id)s
      AND fm.ts_bucket >= %(start_time)s
      AND fm.ts_bucket < %(end_time)s
),
station_data AS (
    -- 获取总管出口压力（泵站级指标）
    SELECT
        fm.ts_bucket,
        fm.value as main_pipeline_outlet_pressure
    FROM fact_measurements fm
    JOIN metric_ids mc ON mc.id = fm.metric_id
    JOIN dim_devices dd ON dd.id = fm.device_id
    WHERE fm.station_id = %(station_id)s
      AND dd.type = 'main_pipeline'
      AND mc.metric_key = 'main_pipeline_outlet_pressure'
      AND fm.ts_bucket >= %(start_time)s
      AND fm.ts_bucket < %(end_time)s
),
running_counts AS (
    -- 统计每个时刻的运行泵数量
    SELECT
        ts_bucket,
        COUNT(*) as N_running
    FROM mv_device_running_1s
    WHERE station_id = %(station_id)s
      AND device_id IN (SELECT device_id FROM station_pumps)
      AND running = 1
      AND ts_bucket >= %(start_time)s
      AND ts_bucket < %(end_time)s
    GROUP BY ts_bucket
)
SELECT
    COALESCE(dd.ts_bucket, sd.ts_bucket) as ts_bucket,
    dd.device_id,
    dd.metric_key,
    dd.value,
    sd.main_pipeline_outlet_pressure,
    dr.running,
    COALESCE(rc.N_running, 0) as N_running
FROM device_data dd
FULL OUTER JOIN station_data sd ON dd.ts_bucket = sd.ts_bucket
LEFT JOIN mv_device_running_1s dr
    ON dr.station_id = %(station_id)s
   AND dr.device_id = %(device_id)s
   AND dr.ts_bucket = COALESCE(dd.ts_bucket, sd.ts_bucket)
LEFT JOIN running_counts rc
    ON rc.ts_bucket = COALESCE(dd.ts_bucket, sd.ts_bucket)
ORDER BY ts_bucket, device_id, metric_key;
```

### 数据透视逻辑

```python
def load_data(
    self,
    station_id: int,
    device_id: int,
    start_time: datetime,
    end_time: datetime
) -> pd.DataFrame:
    """
    加载计算所需的所有数据

    Args:
        station_id: 泵站ID
        device_id: 设备ID
        start_time: 开始时间
        end_time: 结束时间

    Returns:
        DataFrame，包含以下列：
        - ts_bucket: 时间戳
        - device_id: 设备ID
        - pump_inlet_pressure: 泵进口压力（MPa）
        - main_pipeline_outlet_pressure: 总管出口压力（MPa）
        - pump_flow_rate: 泵流量（m³/h）
        - running: 运行状态（0/1）
        - N_running: 当前运行泵数量
    """
    from app.adapters.db import get_connection

    # 执行SQL查询
    with get_connection() as conn:
        df = pd.read_sql(sql, conn, params={
            'station_id': station_id,
            'device_id': device_id,
            'start_time': start_time,
            'end_time': end_time
        })

    # 透视操作（长表 → 宽表）
    df_pivot = df.pivot_table(
        index=['ts_bucket', 'device_id', 'running', 'N_running'],
        columns='metric_key',
        values='value',
        aggfunc='first'
    ).reset_index()

    # 添加总管出口压力（泵站级指标）
    df_pivot['main_pipeline_outlet_pressure'] = df['main_pipeline_outlet_pressure']

    return df_pivot
```

### 返回数据格式

**DataFrame 列**：
- `ts_bucket`: 时间戳（datetime）
- `device_id`: 设备ID（int）
- `pump_inlet_pressure`: 泵进口压力（float，MPa）
- `main_pipeline_outlet_pressure`: 总管出口压力（float，MPa）
- `pump_flow_rate`: 泵流量（float，m³/h）
- `running`: 运行状态（int，0=停止，1=运行）
- `N_running`: 当前运行泵数量（int）

---

## 数据过滤模块详细设计

### 模块职责

**核心职责**：
- 过滤运行状态为停止的数据（running=0）
- 过滤缺失值（NaN）
- 过滤异常值（超出物理范围）
- 记录过滤统计信息

**设计原则**：
- ✅ 只保留 running=1 的数据
- ✅ 检查必需字段是否存在
- ✅ 检查数值是否在合理范围内
- ✅ 记录详细的过滤日志

### 类定义

```python
class DataFilter:
    """pump_head 数据过滤模块"""

    def __init__(self, trace_id: Optional[str] = None):
        """
        初始化数据过滤器

        Args:
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id

        # 物理范围约束
        self.constraints = {
            'pump_inlet_pressure': {'min': 0.0, 'max': 1.0},  # MPa
            'main_pipeline_outlet_pressure': {'min': 0.0, 'max': 2.0},  # MPa
            'pump_flow_rate': {'min': 0.0, 'max': 5000.0},  # m³/h
            'N_running': {'min': 1, 'max': 10}  # 运行泵数量
        }
```

### 过滤逻辑

```python
def filter_data(self, data: pd.DataFrame) -> pd.DataFrame:
    """
    过滤数据

    Args:
        data: 原始数据

    Returns:
        过滤后的数据
    """
    if data.empty:
        return data

    initial_count = len(data)

    # 1. 过滤运行状态
    data_filtered = data[data['running'] == 1].copy()
    running_filtered = initial_count - len(data_filtered)

    # 2. 过滤缺失值
    required_cols = [
        'pump_inlet_pressure',
        'main_pipeline_outlet_pressure',
        'pump_flow_rate',
        'N_running'
    ]
    data_filtered = data_filtered.dropna(subset=required_cols)
    nan_filtered = len(data) - running_filtered - len(data_filtered)

    # 3. 过滤异常值
    for col, constraint in self.constraints.items():
        if col in data_filtered.columns:
            mask = (
                (data_filtered[col] >= constraint['min']) &
                (data_filtered[col] <= constraint['max'])
            )
            data_filtered = data_filtered[mask]

    outlier_filtered = len(data) - running_filtered - nan_filtered - len(data_filtered)

    # 记录过滤统计
    self.logger.info(
        f"[DataFilter] 过滤完成",
        extra={'extra_data': {
            'trace_id': self.trace_id,
            'initial_count': initial_count,
            'running_filtered': running_filtered,
            'nan_filtered': nan_filtered,
            'outlier_filtered': outlier_filtered,
            'final_count': len(data_filtered),
            'filter_ratio': f"{len(data_filtered)/initial_count*100:.1f}%"
        }}
    )

    return data_filtered
```

---

## 方法选择模块详细设计

### 模块职责

**核心职责**：
- 根据数据可用性和参数配置选择计算方法
- 检查依赖指标是否完整
- 检查设备参数是否配置
- 返回选中的方法ID和参数

**设计原则**：
- ✅ 方法配置在代码中定义（不使用 calculation_method_registry 表）
- ✅ 按优先级从高到低尝试
- ✅ 记录详细的选择日志

### 类定义

```python
class MethodSelector:
    """pump_head 方法选择模块"""

    # 方法配置（按优先级从高到低）
    METHODS = [
        {
            'id': 'pipe_loss_multi_pump',
            'name': '压差法（管道损失+多泵修正）',
            'priority': 100,
            'dependencies': [
                'pump_inlet_pressure',
                'main_pipeline_outlet_pressure',
                'pump_flow_rate',
                'N_running'
            ],
            'conditions': {
                'has_device_params': ['K_pipe_loss', 'alpha_multi_pump', 'N_total_pumps']
            }
        }
    ]

    def __init__(self, trace_id: Optional[str] = None):
        """
        初始化方法选择器

        Args:
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id
```

### 选择逻辑

```python
def select_method(
    self,
    data: pd.DataFrame,
    params: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    选择计算方法

    Args:
        data: 过滤后的数据
        params: 参数配置

    Returns:
        选中的方法配置，如果没有合适的方法则返回None
    """
    if data.empty:
        self.logger.warning("[MethodSelector] 数据为空，无法选择方法")
        return None

    # 获取可用的列
    available_cols = set(data.columns)

    # 按优先级尝试每个方法
    for method in self.METHODS:
        # 检查依赖
        dependencies = set(method['dependencies'])
        if not dependencies.issubset(available_cols):
            missing = dependencies - available_cols
            self.logger.debug(
                f"[MethodSelector] 方法 {method['id']} 缺少依赖: {missing}"
            )
            continue

        # 检查参数
        required_params = method['conditions'].get('has_device_params', [])
        if not all(p in params for p in required_params):
            missing_params = [p for p in required_params if p not in params]
            self.logger.debug(
                f"[MethodSelector] 方法 {method['id']} 缺少参数: {missing_params}"
            )
            continue

        # 选中此方法
        self.logger.info(
            f"[MethodSelector] 选中方法: {method['name']}",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'method_id': method['id'],
                'priority': method['priority']
            }}
        )
        return method

    # 没有合适的方法
    self.logger.warning(
        "[MethodSelector] 没有合适的计算方法",
        extra={'extra_data': {
            'trace_id': self.trace_id,
            'available_cols': list(available_cols),
            'available_params': list(params.keys())
        }}
    )
    return None
```

---

## 计算执行模块详细设计

### 模块职责

**核心职责**：
- 执行选中的计算方法
- **先计算修正后的泵出口压力（pump_outlet_pressure）**
- **再计算扬程（pump_head）**
- 返回两个结果

**设计原则**：
- ✅ 计算逻辑清晰，步骤明确
- ✅ 记录详细的计算日志
- ✅ 返回两个指标的结果

### 类定义

```python
class Calculator:
    """pump_head 计算执行模块"""

    def __init__(self, trace_id: Optional[str] = None):
        """
        初始化计算器

        Args:
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id
```

### 计算逻辑

```python
def calculate(
    self,
    data: pd.DataFrame,
    method: Dict[str, Any],
    params: Dict[str, Any]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    执行计算

    Args:
        data: 过滤后的数据
        method: 选中的方法配置
        params: 参数配置

    Returns:
        (pump_outlet_pressure_df, pump_head_df): 两个结果DataFrame
    """
    if method['id'] == 'pipe_loss_multi_pump':
        return self._calculate_pipe_loss_multi_pump(data, params)
    else:
        raise ValueError(f"未知的方法: {method['id']}")

def _calculate_pipe_loss_multi_pump(
    self,
    data: pd.DataFrame,
    params: Dict[str, Any]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    方法1：压差法（管道损失+多泵修正）

    Args:
        data: 输入数据
        params: 参数配置

    Returns:
        (pump_outlet_pressure_df, pump_head_df)
    """
    # 获取参数
    K_pipe_loss = params.get('K_pipe_loss', 0.00001)
    alpha_multi_pump = params.get('alpha_multi_pump', 0.02)
    N_total_pumps = params.get('N_total_pumps', 6)
    rho = params.get('rho', 1000.0)
    g = params.get('g', 9.81)

    # 步骤1：计算管道损失修正
    delta_P_pipe = K_pipe_loss * (data['pump_flow_rate'] ** 2)

    # 步骤2：计算多泵运行修正系数
    correction_factor = 1 + alpha_multi_pump * data['N_running'] / N_total_pumps

    # 步骤3：修正后的泵出口压力
    P_pump_out = (
        data['main_pipeline_outlet_pressure'] * correction_factor +
        delta_P_pipe
    )

    # 步骤4：计算扬程
    H = (P_pump_out - data['pump_inlet_pressure']) * 1e6 / (rho * g)

    # 构造结果DataFrame
    pump_outlet_pressure_df = pd.DataFrame({
        'ts_bucket': data['ts_bucket'],
        'device_id': data['device_id'],
        'value': P_pump_out,
        'metric_key': 'pump_outlet_pressure'
    })

    pump_head_df = pd.DataFrame({
        'ts_bucket': data['ts_bucket'],
        'device_id': data['device_id'],
        'value': H,
        'metric_key': 'pump_head'
    })

    # 记录计算统计
    self.logger.info(
        "[Calculator] 计算完成",
        extra={'extra_data': {
            'trace_id': self.trace_id,
            'method': 'pipe_loss_multi_pump',
            'count': len(data),
            'pump_outlet_pressure_range': f"{P_pump_out.min():.3f} - {P_pump_out.max():.3f} MPa",
            'pump_head_range': f"{H.min():.1f} - {H.max():.1f} m",
            'avg_N_running': f"{data['N_running'].mean():.1f}"
        }}
    )

    return pump_outlet_pressure_df, pump_head_df
```

---

## 结果验证模块详细设计

### 模块职责

**核心职责**：
- 验证计算结果的合理性
- 过滤异常值（NaN、Inf、负值、超出范围）
- 记录验证统计信息

**设计原则**：
- ✅ 物理范围检查
- ✅ 统计分析
- ✅ 详细日志

### 类定义

```python
class Validator:
    """pump_head 结果验证模块"""

    def __init__(self, trace_id: Optional[str] = None):
        """
        初始化验证器

        Args:
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id

        # 物理范围约束
        self.constraints = {
            'pump_outlet_pressure': {'min': 0.0, 'max': 2.0},  # MPa
            'pump_head': {'min': 0.0, 'max': 100.0}  # m
        }
```

### 验证逻辑

```python
def validate(
    self,
    pump_outlet_pressure_df: pd.DataFrame,
    pump_head_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    验证计算结果

    Args:
        pump_outlet_pressure_df: 泵出口压力结果
        pump_head_df: 扬程结果

    Returns:
        (validated_pump_outlet_pressure_df, validated_pump_head_df)
    """
    # 验证泵出口压力
    pump_outlet_pressure_validated = self._validate_metric(
        pump_outlet_pressure_df,
        'pump_outlet_pressure'
    )

    # 验证扬程
    pump_head_validated = self._validate_metric(
        pump_head_df,
        'pump_head'
    )

    return pump_outlet_pressure_validated, pump_head_validated

def _validate_metric(
    self,
    df: pd.DataFrame,
    metric_key: str
) -> pd.DataFrame:
    """
    验证单个指标

    Args:
        df: 结果DataFrame
        metric_key: 指标键

    Returns:
        验证后的DataFrame
    """
    if df.empty:
        return df

    initial_count = len(df)

    # 1. 过滤 NaN 和 Inf
    df_valid = df[~df['value'].isna()].copy()
    df_valid = df_valid[~df_valid['value'].isin([np.inf, -np.inf])]
    nan_inf_filtered = initial_count - len(df_valid)

    # 2. 过滤负值
    df_valid = df_valid[df_valid['value'] >= 0]
    negative_filtered = initial_count - nan_inf_filtered - len(df_valid)

    # 3. 过滤超出范围的值
    constraint = self.constraints[metric_key]
    df_valid = df_valid[
        (df_valid['value'] >= constraint['min']) &
        (df_valid['value'] <= constraint['max'])
    ]
    range_filtered = initial_count - nan_inf_filtered - negative_filtered - len(df_valid)

    # 记录验证统计
    self.logger.info(
        f"[Validator] {metric_key} 验证完成",
        extra={'extra_data': {
            'trace_id': self.trace_id,
            'metric_key': metric_key,
            'initial_count': initial_count,
            'nan_inf_filtered': nan_inf_filtered,
            'negative_filtered': negative_filtered,
            'range_filtered': range_filtered,
            'final_count': len(df_valid),
            'valid_ratio': f"{len(df_valid)/initial_count*100:.1f}%",
            'value_range': f"{df_valid['value'].min():.3f} - {df_valid['value'].max():.3f}",
            'value_mean': f"{df_valid['value'].mean():.3f}"
        }}
    )

    return df_valid
```

---

## 参数配置清单

### 全局参数（所有设备共享）

| 参数名 | 默认值 | 类型 | 可优化 | 说明 |
|--------|--------|------|--------|------|
| `rho` | 1000.0 | float | 否 | 水密度（kg/m³） |
| `g` | 9.81 | float | 否 | 重力加速度（m/s²） |

### 泵站级参数

| 参数名 | 默认值 | 类型 | 可优化 | 说明 |
|--------|--------|------|--------|------|
| `N_total_pumps` | 6 | int | 否 | 泵站总泵数量 |

### 设备级参数（可优化）

| 参数名 | 默认值 | 类型 | 可优化 | 说明 |
|--------|--------|------|--------|------|
| `K_pipe_loss` | 0.00001 | float | 是 | 管道损失系数（MPa/(m³/h)²） |
| `alpha_multi_pump` | 0.02 | float | 是 | 多泵修正系数（无量纲） |

### 参数存储（calculation_parameters 表）

```sql
-- 全局参数
INSERT INTO calculation_parameters (
    metric_key, param_name, param_value, param_type,
    description, station_id, device_id
) VALUES
    ('pump_head', 'rho', '1000.0', 'float', '水密度（kg/m³）', NULL, NULL),
    ('pump_head', 'g', '9.81', 'float', '重力加速度（m/s²）', NULL, NULL);

-- 泵站级参数（泵站16）
INSERT INTO calculation_parameters (
    metric_key, param_name, param_value, param_type,
    description, station_id, device_id
) VALUES
    ('pump_head', 'N_total_pumps', '6', 'int', '泵站总泵数量', 16, NULL);

-- 设备级参数（设备1-6）
INSERT INTO calculation_parameters (
    metric_key, param_name, param_value, param_type,
    description, station_id, device_id, is_optimizable
) VALUES
    ('pump_head', 'K_pipe_loss', '0.00001', 'float', '管道损失系数', 16, 1, TRUE),
    ('pump_head', 'alpha_multi_pump', '0.02', 'float', '多泵修正系数', 16, 1, TRUE),
    ('pump_head', 'K_pipe_loss', '0.00001', 'float', '管道损失系数', 16, 2, TRUE),
    ('pump_head', 'alpha_multi_pump', '0.02', 'float', '多泵修正系数', 16, 2, TRUE),
    -- ... 设备3-6类似
;
```

---

## 完整数据流示例

### 输入数据

```python
# DataLoader 返回的数据
"""
     ts_bucket            device_id  pump_inlet_pressure  main_pipeline_outlet_pressure  pump_flow_rate  running  N_running
0    2025-01-01 00:00:00  1          0.111                0.420                          518.0           1        3
1    2025-01-01 00:00:01  1          0.112                0.421                          520.0           1        3
2    2025-01-01 00:00:02  1          0.110                0.419                          515.0           1        2
"""
```

### 参数配置

```python
params = {
    'K_pipe_loss': 0.00001,
    'alpha_multi_pump': 0.02,
    'N_total_pumps': 6,
    'rho': 1000.0,
    'g': 9.81
}
```

### 计算过程

```python
# 第1行数据计算示例
P_in = 0.111  # MPa
P_main_out = 0.420  # MPa
Q = 518.0  # m³/h
N_running = 3
N_total = 6

# 步骤1：管道损失修正
delta_P_pipe = 0.00001 × 518.0² = 0.00268 MPa

# 步骤2：多泵运行修正系数
correction_factor = 1 + 0.02 × 3 / 6 = 1.01

# 步骤3：修正后的泵出口压力
P_pump_out = 0.420 × 1.01 + 0.00268 = 0.4242 + 0.00268 = 0.42688 MPa

# 步骤4：计算扬程
H = (0.42688 - 0.111) × 1e6 / (1000 × 9.81)
H = 0.31588 × 1e6 / 9810
H = 32.2 m
```

### 输出数据

```python
# pump_outlet_pressure 结果
"""
     ts_bucket            device_id  value     metric_key
0    2025-01-01 00:00:00  1          0.42688   pump_outlet_pressure
1    2025-01-01 00:00:01  1          0.42810   pump_outlet_pressure
2    2025-01-01 00:00:02  1          0.42350   pump_outlet_pressure
"""

# pump_head 结果
"""
     ts_bucket            device_id  value  metric_key
0    2025-01-01 00:00:00  1          32.2   pump_head
1    2025-01-01 00:00:01  1          32.3   pump_head
2    2025-01-01 00:00:02  1          31.9   pump_head
"""
```

---

## 日志输出完整示例

### 数据加载阶段

```
[INFO] [DataLoader] SQL查询完成
  extra_data: {
    '泵站ID': 16,
    '设备ID': 1,
    '原始行数': 3600,
    '耗时(ms)': 125
  }

[INFO] [DataLoader] 数据透视完成
  extra_data: {
    '设备ID': 1,
    '当前设备行数': 3600,
    '时间跨度(小时)': 1.00
  }
```

### 数据过滤阶段

```
[INFO] [DataFilter] 过滤完成
  extra_data: {
    'trace_id': 'task_12345',
    'initial_count': 3600,
    'running_filtered': 120,
    'nan_filtered': 5,
    'outlier_filtered': 2,
    'final_count': 3473,
    'filter_ratio': '96.5%'
  }
```

### 方法选择阶段

```
[INFO] [MethodSelector] 选中方法: 压差法（管道损失+多泵修正）
  extra_data: {
    'trace_id': 'task_12345',
    'method_id': 'pipe_loss_multi_pump',
    'priority': 100
  }
```

### 计算执行阶段

```
[INFO] [Calculator] 计算完成
  extra_data: {
    'trace_id': 'task_12345',
    'method': 'pipe_loss_multi_pump',
    'count': 3473,
    'pump_outlet_pressure_range': '0.410 - 0.435 MPa',
    'pump_head_range': '30.5 - 33.2 m',
    'avg_N_running': '2.8'
  }
```

### 结果验证阶段

```
[INFO] [Validator] pump_outlet_pressure 验证完成
  extra_data: {
    'trace_id': 'task_12345',
    'metric_key': 'pump_outlet_pressure',
    'initial_count': 3473,
    'nan_inf_filtered': 0,
    'negative_filtered': 0,
    'range_filtered': 0,
    'final_count': 3473,
    'valid_ratio': '100.0%',
    'value_range': '0.410 - 0.435',
    'value_mean': '0.422'
  }

[INFO] [Validator] pump_head 验证完成
  extra_data: {
    'trace_id': 'task_12345',
    'metric_key': 'pump_head',
    'initial_count': 3473,
    'nan_inf_filtered': 0,
    'negative_filtered': 0,
    'range_filtered': 0,
    'final_count': 3473,
    'valid_ratio': '100.0%',
    'value_range': '30.5 - 33.2',
    'value_mean': '31.8'
  }
```

### 数据写入阶段

```
[INFO] [DataWriter] 写入完成
  extra_data: {
    'trace_id': 'task_12345',
    'metric_key': 'pump_outlet_pressure',
    'written_count': 3473,
    '耗时(ms)': 245
  }

[INFO] [DataWriter] 写入完成
  extra_data: {
    'trace_id': 'task_12345',
    'metric_key': 'pump_head',
    'written_count': 3473,
    '耗时(ms)': 238
  }
```

---

## 文档结束

**下一步**：
1. 创建实施计划文档（02-pump_head实施计划.md）
2. 创建任务追踪表（03-任务完成追踪表.md）
3. 创建数据库迁移脚本（migrations/001-initialize-parameters.sql）
4. 实施代码开发


