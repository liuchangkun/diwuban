# pump_flow_rate 详细设计文档

> **文档版本**: v1.0  
> **创建日期**: 2025-09-30  
> **状态**: 创新阶段 - 详细设计

---

## 📋 目录

1. [指标概述](#指标概述)
2. [数据获取模块（DataLoader）详细设计](#数据获取模块dataloader详细设计)
3. [数据过滤模块（DataFilter）详细设计](#数据过滤模块datafilter详细设计)
4. [方法选择模块（MethodSelector）详细设计](#方法选择模块methodselector详细设计)
5. [计算方法详细设计（6个方法）](#计算方法详细设计6个方法)
6. [结果验证模块（Validator）详细设计](#结果验证模块validator详细设计)
7. [参数配置清单](#参数配置清单)
8. [完整数据流示例](#完整数据流示例)
9. [日志输出完整示例](#日志输出完整示例)
10. [参数优化方案](#参数优化方案)

---

## 指标概述

### 指标定义

**指标键**: `pump_flow_rate`  
**指标名称**: 水泵流量  
**单位**: m³/h  
**物理意义**: 单台水泵的瞬时流量

### 业务背景

水泵流量是泵站运行的核心指标之一，用于：
- 监控单台水泵的运行状态
- 计算水泵效率、扬程等衍生指标
- 优化泵站调度策略

### 计算挑战

1. **缺失测量**：大部分水泵没有直接的流量计
2. **多泵并联**：多台水泵共用一条总管，只有总管流量
3. **运行状态**：需要区分运行和停机状态
4. **分摊策略**：需要根据功率、频率等参数合理分摊总管流量

### 依赖指标

| 指标键 | 指标名称 | 用途 |
|--------|----------|------|
| `main_pipeline_flow_rate` | 总管流量 | 分摊基准 |
| `pump_active_power` | 水泵有功功率 | 分摊权重 |
| `pump_frequency` | 水泵频率 | 分摊权重 |
| `pump_cumulative_flow` | 水泵累计流量 | 导数计算 |

### 计算方法概览

| 方法ID | 方法名称 | 优先级 | 适用场景 |
|--------|----------|--------|----------|
| method_a | 功率×频率分摊 | 100 | 多泵运行，有功率和频率 |
| method_b | 累计流量导数 | 90 | 有累计流量计 |
| method_c | 单泵直接取总管流量 | 80 | 单泵运行 |
| method_d | 功率分摊 | 70 | 多泵运行，只有功率 |
| method_e | 频率分摊 | 60 | 多泵运行，只有频率 |
| method_f | 数据驱动回归 | 50 | 有历史数据 |

---

## 数据获取模块（DataLoader）详细设计

### 模块职责

**核心职责**：
- 从 `fact_measurements` 表加载计算所需的依赖指标数据
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
class PumpFlowRateDataLoader(DataLoader):
    """pump_flow_rate 数据获取模块"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.metric_key = 'pump_flow_rate'

        # 依赖指标配置
        self.dependencies = {
            'main_pipeline_flow_rate': {
                'required': True,
                'level': 'station',  # 泵站级指标
                'description': '总管流量'
            },
            'pump_active_power': {
                'required': True,
                'level': 'device',  # 设备级指标
                'description': '水泵有功功率'
            },
            'pump_frequency': {
                'required': True,
                'level': 'device',  # 设备级指标
                'description': '水泵频率'
            },
            'pump_cumulative_flow': {
                'required': False,  # 可选
                'level': 'device',
                'description': '水泵累计流量'
            }
        }
```

### SQL查询设计

**设计原则**：
- ✅ 使用**单个SQL查询**获取所有数据（避免多次查询）
- ✅ 包含设备运行状态信息（从 `mv_device_running_1s` 表）
- ✅ 不进行任何过滤（返回所有数据，包括停机设备）
- ✅ 移除 `quality_code` 过滤条件（该字段不存在）

#### 单个SQL查询获取所有数据

```sql
-- 一次性获取所有数据（包括运行状态）
WITH metric_ids AS (
    -- 获取需要的指标ID
    SELECT id, metric_key
    FROM dim_metric_config
    WHERE metric_key IN (
        'main_pipeline_flow_rate',
        'pump_active_power',
        'pump_frequency',
        'pump_cumulative_flow'
    )
),
device_ids AS (
    -- 获取泵站下所有设备ID
    SELECT id
    FROM dim_devices
    WHERE station_id = %(station_id)s
)
SELECT
    fm.ts_bucket,
    fm.device_id,
    mc.metric_key,
    fm.value,
    dr.running  -- 运行状态（0=停止, 1=运行, NULL=无数据）
FROM fact_measurements fm
JOIN metric_ids mc ON mc.id = fm.metric_id
JOIN device_ids d ON d.id = fm.device_id
LEFT JOIN mv_device_running_1s dr
    ON dr.station_id = fm.station_id
   AND dr.device_id = fm.device_id
   AND dr.ts_bucket = fm.ts_bucket
WHERE fm.station_id = %(station_id)s
  AND fm.ts_bucket >= %(start_time)s
  AND fm.ts_bucket < %(end_time)s
ORDER BY fm.ts_bucket, fm.device_id, mc.metric_key;
```

**参数**：
- `station_id`: 泵站ID
- `start_time`: 开始时间（UTC）
- `end_time`: 结束时间（UTC）

**返回**：长表格式（Long Format）
- `ts_bucket`: 时间戳（秒级）
- `device_id`: 设备ID
- `metric_key`: 指标键
- `value`: 指标值
- `running`: 运行状态（0=停止, 1=运行, NULL=无数据）

**关键设计点**：
1. ✅ **LEFT JOIN `mv_device_running_1s`**：确保即使没有运行状态数据也能返回指标数据
2. ✅ **不过滤 `running` 字段**：返回所有数据（包括停机设备），由 DataFilter 负责过滤
3. ✅ **移除 `quality_code` 条件**：该字段不存在于 `fact_measurements` 表
4. ✅ **使用 `metric_key` 而非 `metric_id`**：方便后续透视操作

### 数据透视和合并逻辑

**设计原则**：
- ✅ 使用单个SQL查询获取所有数据
- ✅ 在Python中进行透视操作（将长表转为宽表）
- ✅ 保留运行状态信息（用于后续过滤）
- ✅ 返回原始数据（不进行任何过滤）

```python
def load(
    self,
    station_id: int,
    device_id: int,
    start_time: datetime,
    end_time: datetime
) -> pd.DataFrame:
    """
    加载计算所需的所有数据

    参数：
        station_id: 泵站ID
        device_id: 当前设备ID
        start_time: 开始时间（UTC）
        end_time: 结束时间（UTC）

    返回：
        DataFrame with columns:
        - ts_bucket: 时间戳（秒级）
        - device_id: 设备ID
        - main_pipeline_flow_rate: 总管流量
        - pump_active_power: 水泵有功功率
        - pump_frequency: 水泵频率
        - pump_cumulative_flow: 水泵累计流量（可选）
        - running: 运行状态（0=停止, 1=运行, NULL=无数据）
        - other_devices: 其他设备信息（JSON格式，包含device_id、power、frequency）
    """
    from app.adapters.db import get_connection
    from app.core.logging.setup import log_sql, log_activity
    import time

    with log_activity("数据获取", params={'station_id': station_id, 'device_id': device_id}):
        # 单个SQL查询获取所有数据
        sql = """
            WITH metric_ids AS (
                SELECT id, metric_key
                FROM dim_metric_config
                WHERE metric_key IN (
                    'main_pipeline_flow_rate',
                    'pump_active_power',
                    'pump_frequency',
                    'pump_cumulative_flow'
                )
            ),
            device_ids AS (
                SELECT id
                FROM dim_devices
                WHERE station_id = %(station_id)s
            )
            SELECT
                fm.ts_bucket,
                fm.device_id,
                mc.metric_key,
                fm.value,
                dr.running
            FROM fact_measurements fm
            JOIN metric_ids mc ON mc.id = fm.metric_id
            JOIN device_ids d ON d.id = fm.device_id
            LEFT JOIN mv_device_running_1s dr
                ON dr.station_id = fm.station_id
               AND dr.device_id = fm.device_id
               AND dr.ts_bucket = fm.ts_bucket
            WHERE fm.station_id = %(station_id)s
              AND fm.ts_bucket >= %(start_time)s
              AND fm.ts_bucket < %(end_time)s
            ORDER BY fm.ts_bucket, fm.device_id, mc.metric_key
        """

        start = time.time()
        with get_connection() as conn:
            df_raw = pd.read_sql(
                sql,
                conn,
                params={
                    'station_id': station_id,
                    'start_time': start_time,
                    'end_time': end_time
                }
            )

        duration_ms = int((time.time() - start) * 1000)
        log_sql(sql, params={'station_id': station_id},
                duration_ms=duration_ms, rows=len(df_raw))

        logger.info(
            "[数据获取] SQL查询完成",
            extra={'extra_data': {
                '泵站ID': station_id,
                '设备ID': device_id,
                '原始行数': len(df_raw),
                '耗时(ms)': duration_ms
            }}
        )

        if df_raw.empty:
            logger.warning("[数据获取] 无数据", extra={'extra_data': {'station_id': station_id}})
            return pd.DataFrame()

        # 透视操作：将长表转为宽表
        df_pivot = df_raw.pivot_table(
            index=['ts_bucket', 'device_id'],
            columns='metric_key',
            values='value',
            aggfunc='first'  # 每个时间戳+设备+指标只有一个值
        ).reset_index()

        # 合并运行状态（每个时间戳+设备只有一个运行状态）
        df_running = df_raw[['ts_bucket', 'device_id', 'running']].drop_duplicates()
        df_final = df_pivot.merge(df_running, on=['ts_bucket', 'device_id'], how='left')

        # 分离当前设备和其他设备
        df_current = df_final[df_final['device_id'] == device_id].copy()
        df_others = df_final[df_final['device_id'] != device_id].copy()

        # 聚合其他设备数据（按时间戳分组）
        if not df_others.empty:
            df_others_grouped = df_others.groupby('ts_bucket').apply(
                lambda x: x[['device_id', 'pump_active_power', 'pump_frequency', 'running']].to_dict('records')
            ).reset_index(name='other_devices')

            df_current = df_current.merge(df_others_grouped, on='ts_bucket', how='left')
        else:
            df_current['other_devices'] = None

        logger.info(
            "[数据获取] 数据透视完成",
            extra={'extra_data': {
                '设备ID': device_id,
                '当前设备行数': len(df_current),
                '其他设备数': len(df_others['device_id'].unique()) if not df_others.empty else 0,
                '时间跨度(小时)': f"{(df_current['ts_bucket'].max() - df_current['ts_bucket'].min()).total_seconds() / 3600:.2f}" if not df_current.empty else 0
            }}
        )

        return df_current
```

### 数据结构示例

```python
# 返回的 DataFrame 结构
"""
     ts_bucket            device_id  main_pipeline_flow_rate  pump_active_power  pump_frequency  pump_cumulative_flow  running  other_devices
0    2025-09-30 00:00:00  105        150.5                    45.2               48.5            1234.5                1        [{'device_id': 106, 'pump_active_power': 50.3, 'pump_frequency': 49.0, 'running': 1}, ...]
1    2025-09-30 00:00:01  105        151.2                    45.8               48.6            1234.6                1        [{'device_id': 106, 'pump_active_power': 50.5, 'pump_frequency': 49.1, 'running': 1}, ...]
2    2025-09-30 00:00:02  105        150.8                    0.0                0.0             1234.6                0        [{'device_id': 106, 'pump_active_power': 50.2, 'pump_frequency': 49.0, 'running': 1}, ...]
...
"""
```

**关键字段说明**：
- `ts_bucket`: 时间戳（秒级）
- `device_id`: 当前设备ID
- `main_pipeline_flow_rate`: 总管流量（m³/h）
- `pump_active_power`: 水泵有功功率（kW）
- `pump_frequency`: 水泵频率（Hz）
- `pump_cumulative_flow`: 水泵累计流量（m³，可选）
- `running`: **运行状态（0=停止, 1=运行, NULL=无数据）** - 来自 `mv_device_running_1s` 表
- `other_devices`: 其他设备信息（JSON格式）

---

## 数据过滤模块（DataFilter）详细设计

### 模块职责

**核心职责**：
- 过滤无效数据，确保计算输入的质量
- **使用 `mv_device_running_1s.running` 字段过滤停机数据**（不使用硬编码阈值）
- 过滤 NaN、Inf、负值、异常值

**设计原则**：
- ✅ **运行状态判断唯一数据源**：`mv_device_running_1s.running` 字段
- ✅ **不使用硬编码阈值**：移除 `f_thr`、`p_thr` 参数
- ✅ **职责单一**：只负责过滤，不负责数据获取

### 过滤规则

#### 1. 停机状态过滤（最重要）

```python
# 使用 mv_device_running_1s.running 字段过滤停机数据
# running = 0: 停止
# running = 1: 运行
# running = NULL: 无运行状态数据（保守处理：保留）
df = df[df['running'] == 1]
```

**关键设计点**：
- ✅ **唯一数据源**：`mv_device_running_1s.running` 字段
- ✅ **不使用硬编码阈值**：不再使用 `frequency >= 3.0Hz` 或 `power >= 0.5kW` 判断
- ✅ **NULL值处理**：如果 `running` 为 NULL，保守处理（保留数据）

#### 2. NaN/Inf 过滤

```python
# 移除包含 NaN 或 Inf 的行
df = df.dropna(subset=['main_pipeline_flow_rate', 'pump_active_power', 'pump_frequency'])
df = df[~df['main_pipeline_flow_rate'].isin([np.inf, -np.inf])]
df = df[~df['pump_active_power'].isin([np.inf, -np.inf])]
df = df[~df['pump_frequency'].isin([np.inf, -np.inf])]
```

#### 3. 负值过滤

```python
# 移除负值（流量、功率、频率不应为负）
df = df[df['main_pipeline_flow_rate'] >= 0]
df = df[df['pump_active_power'] >= 0]
df = df[df['pump_frequency'] >= 0]
```

#### 4. 异常值过滤（可选）

```python
# 移除超出物理范围的值（从配置加载）
df = df[df['main_pipeline_flow_rate'] <= max_flow]  # 总管流量上限
df = df[df['pump_active_power'] <= max_power]       # 功率上限
df = df[df['pump_frequency'] <= max_freq]           # 频率上限
```

### 类定义

```python
class PumpFlowRateDataFilter(DataFilter):
    """pump_flow_rate 数据过滤模块"""

    def __init__(self, config: Dict):
        super().__init__(config)

        # 异常值阈值（从配置加载）
        self.max_flow = config.get('max_flow', 500)    # 流量上限（m³/h）
        self.max_power = config.get('max_power', 200)  # 功率上限（kW）
        self.max_freq = config.get('max_freq', 50)     # 频率上限（Hz）

        # ❌ 移除：不再使用硬编码阈值判断运行状态
        # self.f_thr = config.get('f_thr', 3.0)  # 频率阈值
        # self.p_thr = config.get('p_thr', 0.5)  # 功率阈值

    def filter(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        过滤无效数据

        参数：
            data: 原始数据（包含 running 字段）

        返回：
            过滤后的数据
        """
        from app.core.logging.setup import log_activity

        with log_activity("数据过滤", params={'原始行数': len(data)}):
            original_count = len(data)

            # 1. 停机状态过滤（使用 mv_device_running_1s.running 字段）
            before_stopped = len(data)
            data = data[data['running'] == 1]  # 只保留运行状态的数据
            stopped_count = before_stopped - len(data)

            # 2. NaN/Inf 过滤
            before_nan = len(data)
            data = data.dropna(subset=['main_pipeline_flow_rate', 'pump_active_power', 'pump_frequency'])
            data = data[~data['main_pipeline_flow_rate'].isin([np.inf, -np.inf])]
            data = data[~data['pump_active_power'].isin([np.inf, -np.inf])]
            data = data[~data['pump_frequency'].isin([np.inf, -np.inf])]
            nan_count = before_nan - len(data)

            # 3. 负值过滤
            before_negative = len(data)
            data = data[data['main_pipeline_flow_rate'] >= 0]
            data = data[data['pump_active_power'] >= 0]
            data = data[data['pump_frequency'] >= 0]
            negative_count = before_negative - len(data)

            # 4. 异常值过滤
            before_outlier = len(data)
            data = data[data['main_pipeline_flow_rate'] <= self.max_flow]
            data = data[data['pump_active_power'] <= self.max_power]
            data = data[data['pump_frequency'] <= self.max_freq]
            outlier_count = before_outlier - len(data)

        final_count = len(data)

        logger.info(
            "[数据过滤] 过滤完成",
            extra={'extra_data': {
                '原始行数': original_count,
                '移除NaN': nan_count,
                '移除负值': negative_count,
                '移除停机': stopped_count,
                '移除异常值': outlier_count,
                '最终行数': final_count,
                '过滤比例': f"{(original_count - final_count) / original_count * 100:.2f}%"
            }}
        )

        return data
```

---

## 方法选择模块（MethodSelector）详细设计

### 模块职责

根据数据可用性和条件，选择最合适的计算方法。

### 方法优先级

| 优先级 | 方法ID | 方法名称 | 依赖条件 | 运行条件 |
|--------|--------|----------|----------|----------|
| 100 | method_a | 功率×频率分摊 | main_flow, power, frequency, other_devices | 运行泵数≥2 |
| 90 | method_b | 累计流量导数 | cumulative_flow | 累计流量有效 |
| 80 | method_c | 单泵直接取总管流量 | main_flow | 运行泵数=1 |
| 70 | method_d | 功率分摊 | main_flow, power, other_devices | 运行泵数≥2 |
| 60 | method_e | 频率分摊 | main_flow, frequency, other_devices | 运行泵数≥2 |
| 50 | method_f | 数据驱动回归 | 历史数据 | 有足够历史样本 |

### 选择逻辑

```python
class PumpFlowRateMethodSelector(MethodSelector):
    """pump_flow_rate 方法选择模块"""

    # 方法配置
    METHODS = [
        {
            'id': 'method_a',
            'name': '功率×频率分摊',
            'priority': 100,
            'dependencies': ['main_flow', 'power', 'frequency', 'other_devices'],
            'conditions': {
                'min_running_pumps': 2
            }
        },
        {
            'id': 'method_b',
            'name': '累计流量导数',
            'priority': 90,
            'dependencies': ['cumulative_flow'],
            'conditions': {
                'cumulative_flow_valid': True
            }
        },
        {
            'id': 'method_c',
            'name': '单泵直接取总管流量',
            'priority': 80,
            'dependencies': ['main_flow'],
            'conditions': {
                'running_pumps': 1
            }
        },
        {
            'id': 'method_d',
            'name': '功率分摊',
            'priority': 70,
            'dependencies': ['main_flow', 'power', 'other_devices'],
            'conditions': {
                'min_running_pumps': 2
            }
        },
        {
            'id': 'method_e',
            'name': '频率分摊',
            'priority': 60,
            'dependencies': ['main_flow', 'frequency', 'other_devices'],
            'conditions': {
                'min_running_pumps': 2
            }
        },
        {
            'id': 'method_f',
            'name': '数据驱动回归',
            'priority': 50,
            'dependencies': ['historical_data'],
            'conditions': {
                'min_samples': 100
            }
        }
    ]

    def select(self, data: pd.DataFrame) -> str:
        """
        选择计算方法

        参数：
            data: 过滤后的数据

        返回：
            方法ID
        """
        logger.info(
            "[方法选择] 开始选择",
            extra={'extra_data': {
                '可用数据行数': len(data)
            }}
        )

        # 按优先级检查每个方法
        for method in sorted(self.METHODS, key=lambda x: x['priority'], reverse=True):
            method_id = method['id']

            # 检查依赖
            dependencies_met = self._check_dependencies(data, method['dependencies'])

            # 检查条件
            conditions_met = self._check_conditions(data, method['conditions'])

            logger.debug(
                "[方法选择] 检查方法",
                extra={'extra_data': {
                    '方法ID': method_id,
                    '方法名称': method['name'],
                    '优先级': method['priority'],
                    '依赖满足': dependencies_met,
                    '条件满足': conditions_met
                }}
            )

            if dependencies_met and conditions_met:
                logger.info(
                    "[方法选择] 选择完成",
                    extra={'extra_data': {
                        '选择方法': method_id,
                        '方法名称': method['name'],
                        '优先级': method['priority']
                    }}
                )
                return method_id

        # 没有合适的方法
        raise ValueError("没有找到合适的计算方法")

    def _check_dependencies(self, data: pd.DataFrame, dependencies: List[str]) -> bool:
        """检查依赖是否满足"""
        for dep in dependencies:
            if dep == 'other_devices':
                # 检查是否有其他设备数据
                if 'other_devices' not in data.columns:
                    return False
                if data['other_devices'].isna().all():
                    return False
            elif dep == 'historical_data':
                # 检查是否有历史数据（这里简化处理）
                return False  # 暂不支持
            else:
                # 检查列是否存在且有有效值
                if dep not in data.columns:
                    return False
                if data[dep].isna().all():
                    return False
        return True

    def _check_conditions(self, data: pd.DataFrame, conditions: Dict) -> bool:
        """检查条件是否满足"""
        for cond_key, cond_value in conditions.items():
            if cond_key == 'min_running_pumps':
                # 计算运行泵数（包括当前设备）
                running_pumps = self._count_running_pumps(data)
                if running_pumps < cond_value:
                    return False
            elif cond_key == 'running_pumps':
                # 精确匹配运行泵数
                running_pumps = self._count_running_pumps(data)
                if running_pumps != cond_value:
                    return False
            elif cond_key == 'cumulative_flow_valid':
                # 检查累计流量是否有效（单调递增）
                if 'cumulative_flow' not in data.columns:
                    return False
                if not self._is_cumulative_flow_valid(data['cumulative_flow']):
                    return False
            elif cond_key == 'min_samples':
                # 检查样本数量
                if len(data) < cond_value:
                    return False
        return True

    def _count_running_pumps(self, data: pd.DataFrame) -> int:
        """
        计算运行泵数

        逻辑：
        1. 当前设备算1台
        2. 统计 other_devices 中运行的设备数
        """
        # 当前设备
        count = 1

        # 其他设备
        if 'other_devices' in data.columns and not data['other_devices'].isna().all():
            # 取第一行的 other_devices（假设同一时间窗口内设备数量不变）
            other_devices = data['other_devices'].iloc[0]
            if other_devices:
                # 统计有功率和频率的设备
                device_ids = set()
                for record in other_devices:
                    device_id = record.get('device_id')
                    metric_key = record.get('metric_key')
                    value = record.get('value', 0)

                    # 判断是否运行（功率≥0.5 或 频率≥3.0）
                    if metric_key == 'pump_active_power' and value >= 0.5:
                        device_ids.add(device_id)
                    elif metric_key == 'pump_frequency' and value >= 3.0:
                        device_ids.add(device_id)

                count += len(device_ids)

        return count

    def _is_cumulative_flow_valid(self, cumulative_flow: pd.Series) -> bool:
        """检查累计流量是否有效（单调递增）"""
        if cumulative_flow.isna().any():
            return False

        # 检查是否单调递增
        diff = cumulative_flow.diff()
        if (diff[1:] < 0).any():  # 跳过第一个NaN
            return False

        return True
```

---

## 计算方法详细设计（6个方法）

### Method A: 功率×频率分摊

#### 原理

根据水泵的功率和频率计算权重，按权重分摊总管流量。

**公式**：

$$
Q_i = Q_{total} \times \frac{P_i^\alpha \times f_i^\beta}{\sum_{j=1}^{n} (P_j^\alpha \times f_j^\beta)}
$$

其中：
- $Q_i$: 设备 $i$ 的流量
- $Q_{total}$: 总管流量
- $P_i$: 设备 $i$ 的功率
- $f_i$: 设备 $i$ 的频率
- $\alpha$: 功率指数（默认1.0）
- $\beta$: 频率指数（默认1.0）
- $n$: 运行泵数量

#### 参数

| 参数名 | 默认值 | 可优化 | 说明 |
|--------|--------|--------|------|
| alpha | 1.0 | ✅ | 功率指数 |
| beta | 1.0 | ✅ | 频率指数 |

**移除的参数**：
- ❌ `f_thr`（频率阈值）- 不再使用硬编码阈值判断运行状态
- ❌ `p_thr`（功率阈值）- 不再使用硬编码阈值判断运行状态

**说明**：运行状态判断已移至 DataFilter 模块，使用 `mv_device_running_1s.running` 字段。

#### 实现

```python
def calculate_method_a(
    data: pd.DataFrame,
    params: Dict[str, float]
) -> pd.Series:
    """
    Method A: 功率×频率分摊

    参数：
        data: 包含 main_pipeline_flow_rate, pump_active_power, pump_frequency, other_devices 的 DataFrame
        params: 参数字典 {alpha, beta}

    返回：
        计算结果（Series）

    注意：
        - 数据已经过 DataFilter 过滤，只包含运行状态的设备
        - 不再使用 f_thr、p_thr 参数判断运行状态
    """
    alpha = params.get('alpha', 1.0)
    beta = params.get('beta', 1.0)

    results = []

    for idx, row in data.iterrows():
        main_flow = row['main_pipeline_flow_rate']
        power = row['pump_active_power']
        frequency = row['pump_frequency']
        other_devices = row['other_devices']

        # 计算当前设备的权重
        weight_current = (power ** alpha) * (frequency ** beta)

        # 计算其他设备的权重总和
        weight_others = 0.0
        if other_devices:
            device_weights = {}
            for record in other_devices:
                device_id = record['device_id']
                power_other = record.get('pump_active_power', 0)
                frequency_other = record.get('pump_frequency', 0)
                running_other = record.get('running', 1)  # 默认为运行状态

                # 只计算运行设备的权重（使用 running 字段）
                if running_other == 1:
                    weight_others += (power_other ** alpha) * (frequency_other ** beta)

        # 计算总权重
        weight_total = weight_current + weight_others

        # 计算当前设备的流量
        if weight_total > 0:
            flow = main_flow * (weight_current / weight_total)
        else:
            flow = 0.0

        results.append(flow)

    return pd.Series(results, index=data.index)
```

**关键改进**：
- ✅ 移除硬编码阈值检查（`p >= p_thr and f >= f_thr`）
- ✅ 使用 `running` 字段判断运行状态（`running_other == 1`）
- ✅ 简化数据结构（直接从 record 获取 power、frequency、running）
- ✅ 数据已经过 DataFilter 过滤，当前设备必然是运行状态

### Method B: 累计流量导数

#### 原理

对累计流量求导数，得到瞬时流量。

**公式**：

$$
Q(t) = \frac{dQ_{cumulative}}{dt} \times 3600
$$

其中：
- $Q(t)$: 瞬时流量（m³/h）
- $Q_{cumulative}$: 累计流量（m³）
- $dt$: 时间间隔（秒）
- 3600: 转换系数（秒→小时）

#### 参数

| 参数名 | 默认值 | 可优化 | 说明 |
|--------|--------|--------|------|
| smooth_window | 5 | ❌ | 平滑窗口大小 |

#### 实现

```python
def calculate_method_b(
    data: pd.DataFrame,
    params: Dict[str, Any]
) -> pd.Series:
    """
    Method B: 累计流量导数

    参数：
        data: 包含 ts, cumulative_flow 的 DataFrame
        params: 参数字典 {smooth_window}

    返回：
        计算结果（Series）
    """
    smooth_window = params.get('smooth_window', 5)

    # 计算时间差（秒）
    data['dt'] = data['ts'].diff().dt.total_seconds()

    # 计算累计流量差
    data['dcum'] = data['cumulative_flow'].diff()

    # 计算瞬时流量（m³/h）
    data['flow'] = (data['dcum'] / data['dt']) * 3600

    # 平滑处理（移动平均）
    data['flow_smooth'] = data['flow'].rolling(
        window=smooth_window,
        min_periods=1,
        center=True
    ).mean()

    # 移除第一行（diff产生的NaN）
    results = data['flow_smooth'].fillna(0)

    return results
```

### Method C: 单泵直接取总管流量

#### 原理

当只有一台泵运行时，该泵的流量等于总管流量。

**公式**：

$$
Q_i = Q_{total}
$$

#### 参数

无

#### 实现

```python
def calculate_method_c(
    data: pd.DataFrame,
    params: Dict[str, Any]
) -> pd.Series:
    """
    Method C: 单泵直接取总管流量

    参数：
        data: 包含 main_flow 的 DataFrame
        params: 参数字典（未使用）

    返回：
        计算结果（Series）
    """
    return data['main_flow'].copy()
```

### Method D: 功率分摊

#### 原理

仅根据功率计算权重，按权重分摊总管流量。

**公式**：

$$
Q_i = Q_{total} \times \frac{P_i^\alpha}{\sum_{j=1}^{n} P_j^\alpha}
$$

#### 参数

| 参数名 | 默认值 | 可优化 | 说明 |
|--------|--------|--------|------|
| alpha | 1.0 | ✅ | 功率指数 |

**移除的参数**：
- ❌ `p_thr`（功率阈值）- 不再使用硬编码阈值判断运行状态

#### 实现

```python
def calculate_method_d(
    data: pd.DataFrame,
    params: Dict[str, float]
) -> pd.Series:
    """
    Method D: 功率分摊

    参数：
        data: 包含 main_pipeline_flow_rate, pump_active_power, other_devices 的 DataFrame
        params: 参数字典 {alpha}

    返回：
        计算结果（Series）

    注意：
        - 数据已经过 DataFilter 过滤，只包含运行状态的设备
        - 不再使用 p_thr 参数判断运行状态
    """
    alpha = params.get('alpha', 1.0)

    results = []

    for idx, row in data.iterrows():
        main_flow = row['main_pipeline_flow_rate']
        power = row['pump_active_power']
        other_devices = row['other_devices']

        # 计算当前设备的权重
        weight_current = power ** alpha

        # 计算其他设备的权重总和
        weight_others = 0.0
        if other_devices:
            for record in other_devices:
                power_other = record.get('pump_active_power', 0)
                running_other = record.get('running', 1)

                # 只计算运行设备的权重（使用 running 字段）
                if running_other == 1:
                    weight_others += power_other ** alpha

        # 计算总权重
        weight_total = weight_current + weight_others

        # 计算当前设备的流量
        if weight_total > 0:
            flow = main_flow * (weight_current / weight_total)
        else:
            flow = 0.0

        results.append(flow)

    return pd.Series(results, index=data.index)
```

### Method E: 频率分摊

#### 原理

仅根据频率计算权重，按权重分摊总管流量。

**公式**：

$$
Q_i = Q_{total} \times \frac{f_i^\beta}{\sum_{j=1}^{n} f_j^\beta}
$$

#### 参数

| 参数名 | 默认值 | 可优化 | 说明 |
|--------|--------|--------|------|
| beta | 1.0 | ✅ | 频率指数 |

**移除的参数**：
- ❌ `f_thr`（频率阈值）- 不再使用硬编码阈值判断运行状态

#### 实现

```python
def calculate_method_e(
    data: pd.DataFrame,
    params: Dict[str, float]
) -> pd.Series:
    """
    Method E: 频率分摊

    参数：
        data: 包含 main_pipeline_flow_rate, pump_frequency, other_devices 的 DataFrame
        params: 参数字典 {beta}

    返回：
        计算结果（Series）

    注意：
        - 数据已经过 DataFilter 过滤，只包含运行状态的设备
        - 不再使用 f_thr 参数判断运行状态
    """
    beta = params.get('beta', 1.0)

    results = []

    for idx, row in data.iterrows():
        main_flow = row['main_pipeline_flow_rate']
        frequency = row['pump_frequency']
        other_devices = row['other_devices']

        # 计算当前设备的权重
        weight_current = frequency ** beta

        # 计算其他设备的权重总和
        weight_others = 0.0
        if other_devices:
            for record in other_devices:
                frequency_other = record.get('pump_frequency', 0)
                running_other = record.get('running', 1)

                # 只计算运行设备的权重（使用 running 字段）
                if running_other == 1:
                    weight_others += frequency_other ** beta

        # 计算总权重
        weight_total = weight_current + weight_others

        # 计算当前设备的流量
        if weight_total > 0:
            flow = main_flow * (weight_current / weight_total)
        else:
            flow = 0.0

        results.append(flow)

    return pd.Series(results, index=data.index)
```

### Method F: 数据驱动回归

#### 原理

使用历史数据训练回归模型，预测流量。

**公式**：

$$
Q = f(P, f, Q_{total}, ...)
$$

其中 $f$ 是机器学习模型（如线性回归、随机森林等）。

#### 参数

| 参数名 | 默认值 | 可优化 | 说明 |
|--------|--------|--------|------|
| model_type | 'linear' | ❌ | 模型类型 |
| min_samples | 100 | ❌ | 最小样本数 |

#### 实现

```python
def calculate_method_f(
    data: pd.DataFrame,
    params: Dict[str, Any]
) -> pd.Series:
    """
    Method F: 数据驱动回归

    参数：
        data: 包含特征的 DataFrame
        params: 参数字典 {model_type, min_samples}

    返回：
        计算结果（Series）

    注意：此方法需要预先训练模型，暂不实现
    """
    raise NotImplementedError("Method F 暂未实现")
```

---

## 结果验证模块（Validator）详细设计

### 模块职责

验证计算结果的合理性，标记或移除无效值。

### 验证规则

#### 1. 范围验证

```python
# 流量应在合理范围内
min_flow = 0.0
max_flow = 200.0  # 单泵流量上限
```

#### 2. 非负验证

```python
# 流量不应为负
valid = (results >= 0)
```

#### 3. NaN/Inf 验证

```python
# 结果不应包含 NaN 或 Inf
valid = ~results.isin([np.nan, np.inf, -np.inf])
```

#### 4. 物理约束验证

```python
# 单泵流量不应超过总管流量
valid = (results <= main_flow * 1.1)  # 允许10%误差
```

### 类定义

```python
class PumpFlowRateValidator(Validator):
    """pump_flow_rate 结果验证模块"""

    def __init__(self, config: Dict):
        super().__init__(config)

        # 验证阈值
        self.min_flow = config.get('min_flow', 0.0)
        self.max_flow = config.get('max_flow', 200.0)
        self.max_ratio = config.get('max_ratio', 1.1)  # 单泵/总管流量最大比例

    def validate(
        self,
        results: pd.Series,
        data: pd.DataFrame
    ) -> Tuple[pd.Series, pd.Series]:
        """
        验证计算结果

        参数：
            results: 计算结果
            data: 原始数据（用于物理约束验证）

        返回：
            (valid_results, is_valid)
            - valid_results: 有效结果（无效值设为NaN）
            - is_valid: 布尔Series，标记每个值是否有效
        """
        logger.info(
            "[结果验证] 开始验证",
            extra={'extra_data': {
                '结果数量': len(results),
                '验证规则': ['范围', '非负', 'NaN/Inf', '物理约束']
            }}
        )

        # 初始化有效性标记
        is_valid = pd.Series([True] * len(results), index=results.index)

        # 1. 范围验证
        range_invalid = (results < self.min_flow) | (results > self.max_flow)
        is_valid &= ~range_invalid

        # 2. 非负验证
        negative_invalid = (results < 0)
        is_valid &= ~negative_invalid

        # 3. NaN/Inf 验证
        nan_inf_invalid = results.isna() | results.isin([np.inf, -np.inf])
        is_valid &= ~nan_inf_invalid

        # 4. 物理约束验证（单泵流量不应超过总管流量）
        if 'main_flow' in data.columns:
            main_flow = data['main_flow']
            physical_invalid = (results > main_flow * self.max_ratio)
            is_valid &= ~physical_invalid

        # 记录无效值
        invalid_count = (~is_valid).sum()
        if invalid_count > 0:
            invalid_indices = results[~is_valid].index
            for idx in invalid_indices[:10]:  # 只记录前10个
                logger.warning(
                    "[结果验证] 发现无效值",
                    extra={'extra_data': {
                        '时间戳': data.loc[idx, 'ts'].isoformat() if 'ts' in data.columns else str(idx),
                        '值': float(results.loc[idx]),
                        '总管流量': float(data.loc[idx, 'main_flow']) if 'main_flow' in data.columns else None,
                        '失败原因': self._get_failure_reason(results.loc[idx], data.loc[idx])
                    }}
                )

        # 创建有效结果（无效值设为NaN）
        valid_results = results.copy()
        valid_results[~is_valid] = np.nan

        logger.info(
            "[结果验证] 验证完成",
            extra={'extra_data': {
                '原始数量': len(results),
                '有效数量': is_valid.sum(),
                '无效数量': invalid_count,
                '有效比例': f"{is_valid.sum() / len(results) * 100:.2f}%"
            }}
        )

        return valid_results, is_valid

    def _get_failure_reason(self, value: float, row: pd.Series) -> str:
        """获取验证失败原因"""
        reasons = []

        if pd.isna(value):
            reasons.append("NaN")
        elif value == np.inf:
            reasons.append("Inf")
        elif value == -np.inf:
            reasons.append("-Inf")

        if value < self.min_flow:
            reasons.append(f"低于最小值({self.min_flow})")
        if value > self.max_flow:
            reasons.append(f"超过最大值({self.max_flow})")

        if 'main_flow' in row:
            main_flow = row['main_flow']
            if value > main_flow * self.max_ratio:
                reasons.append(f"超过总管流量{self.max_ratio}倍")

        return ", ".join(reasons) if reasons else "未知原因"
```

---

## 参数配置清单

### 全局参数（所有方法共用）

| 参数名 | 默认值 | 类型 | 可优化 | 说明 |
|--------|--------|------|--------|------|
| max_flow | 500.0 | float | ❌ | 总管流量上限（m³/h） |
| max_power | 200.0 | float | ❌ | 功率上限（kW） |
| max_freq | 50.0 | float | ❌ | 频率上限（Hz） |

**已移除的全局参数**：
- ❌ `f_thr`（频率阈值）- 不再使用硬编码阈值判断运行状态
- ❌ `p_thr`（功率阈值）- 不再使用硬编码阈值判断运行状态

**说明**：运行状态判断已移至 DataFilter 模块，使用 `mv_device_running_1s.running` 字段。

### Method A 参数

| 参数名 | 默认值 | 类型 | 可优化 | 说明 |
|--------|--------|------|--------|------|
| alpha | 1.0 | float | ✅ | 功率指数 |
| beta | 1.0 | float | ✅ | 频率指数 |

### Method B 参数

| 参数名 | 默认值 | 类型 | 可优化 | 说明 |
|--------|--------|------|--------|------|
| smooth_window | 5 | int | ❌ | 平滑窗口大小 |

### Method C 参数

无

### Method D 参数

| 参数名 | 默认值 | 类型 | 可优化 | 说明 |
|--------|--------|------|--------|------|
| alpha | 1.0 | float | ✅ | 功率指数 |

### Method E 参数

| 参数名 | 默认值 | 类型 | 可优化 | 说明 |
|--------|--------|------|--------|------|
| beta | 1.0 | float | ✅ | 频率指数 |

### Method F 参数

| 参数名 | 默认值 | 类型 | 可优化 | 说明 |
|--------|--------|------|--------|------|
| model_type | 'linear' | str | ❌ | 模型类型 |
| min_samples | 100 | int | ❌ | 最小样本数 |

### 验证参数

| 参数名 | 默认值 | 类型 | 可优化 | 说明 |
|--------|--------|------|--------|------|
| min_flow | 0.0 | float | ❌ | 流量下限（m³/h） |
| max_flow | 200.0 | float | ❌ | 单泵流量上限（m³/h） |
| max_ratio | 1.1 | float | ❌ | 单泵/总管流量最大比例 |

### 参数存储示例

```sql
-- 全局参数（DataFilter 使用）
INSERT INTO calculation_parameters (station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable) VALUES
(NULL, NULL, 'pump_flow_rate', 'global', 'max_flow', '500.0', 'float', FALSE),
(NULL, NULL, 'pump_flow_rate', 'global', 'max_power', '200.0', 'float', FALSE),
(NULL, NULL, 'pump_flow_rate', 'global', 'max_freq', '50.0', 'float', FALSE);

-- ❌ 移除的全局参数：
-- (NULL, NULL, 'pump_flow_rate', 'global', 'f_thr', '3.0', 'float', TRUE),  -- 不再使用
-- (NULL, NULL, 'pump_flow_rate', 'global', 'p_thr', '0.5', 'float', TRUE),  -- 不再使用

-- Method A 参数
INSERT INTO calculation_parameters (station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable) VALUES
(NULL, NULL, 'pump_flow_rate', 'method_a', 'alpha', '1.0', 'float', TRUE),
(NULL, NULL, 'pump_flow_rate', 'method_a', 'beta', '1.0', 'float', TRUE);

-- Method B 参数
INSERT INTO calculation_parameters (station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable) VALUES
(NULL, NULL, 'pump_flow_rate', 'method_b', 'smooth_window', '5', 'int', FALSE);

-- Method D 参数
INSERT INTO calculation_parameters (station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable) VALUES
(NULL, NULL, 'pump_flow_rate', 'method_d', 'alpha', '1.0', 'float', TRUE);

-- Method E 参数
INSERT INTO calculation_parameters (station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable) VALUES
(NULL, NULL, 'pump_flow_rate', 'method_e', 'beta', '1.0', 'float', TRUE);

-- 验证参数
INSERT INTO calculation_parameters (station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable) VALUES
(NULL, NULL, 'pump_flow_rate', 'validator', 'min_flow', '0.0', 'float', FALSE),
(NULL, NULL, 'pump_flow_rate', 'validator', 'max_flow', '200.0', 'float', FALSE),
(NULL, NULL, 'pump_flow_rate', 'validator', 'max_ratio', '1.1', 'float', FALSE);
```

**参数统计**：
- **总参数数**: 14个（移除2个后，从16个减少到14个）
- **可优化参数**: 5个（alpha×2, beta×2, 共4个方法）
- **全局参数**: 3个（max_flow, max_power, max_freq）
- **验证参数**: 3个（min_flow, max_flow, max_ratio）

---

## 完整数据流示例

### 场景描述

- **泵站**: 14号泵站
- **设备**: 105号水泵
- **时间范围**: 2025-09-30 00:00:00 ~ 2025-09-30 01:00:00
- **运行状态**: 2台泵运行（105、106）
- **选择方法**: Method A（功率×频率分摊）

### 步骤1：数据获取

**输入**：
- station_id = 14
- device_id = 105
- start_time = 2025-09-30 00:00:00
- end_time = 2025-09-30 01:00:00

**输出**：
```python
# DataFrame (前3行)
     ts                  main_flow  power  frequency  other_devices
0    2025-09-30 00:00:00  150.5     45.2   48.5       [{'device_id': 106, 'metric_key': 'pump_active_power', 'value': 50.3}, {'device_id': 106, 'metric_key': 'pump_frequency', 'value': 49.0}]
1    2025-09-30 00:00:01  151.2     45.8   48.6       [{'device_id': 106, 'metric_key': 'pump_active_power', 'value': 50.5}, {'device_id': 106, 'metric_key': 'pump_frequency', 'value': 49.1}]
2    2025-09-30 00:00:02  150.8     45.5   48.5       [{'device_id': 106, 'metric_key': 'pump_active_power', 'value': 50.4}, {'device_id': 106, 'metric_key': 'pump_frequency', 'value': 49.0}]
```

### 步骤2：数据过滤

**输入**：上述 DataFrame（3600行）

**过滤统计**：
- 原始行数: 3600
- 移除NaN: 0
- 移除负值: 0
- 移除停机: 0
- 移除异常值: 0
- 最终行数: 3600

**输出**：相同的 DataFrame（无数据被过滤）

### 步骤3：方法选择

**检查过程**：
1. Method A (优先级100)
   - 依赖检查: main_flow ✅, power ✅, frequency ✅, other_devices ✅
   - 条件检查: 运行泵数=2 ≥ 2 ✅
   - **选择此方法** ✅

**输出**：method_id = 'method_a'

### 步骤4：计算执行

**参数**：
- alpha = 1.0
- beta = 1.0

**计算示例（第1行）**：
```python
# 输入
main_flow = 150.5
power_105 = 45.2
frequency_105 = 48.5
power_106 = 50.3
frequency_106 = 49.0
running_106 = 1  # 运行状态

# 计算权重
weight_105 = (45.2 ** 1.0) * (48.5 ** 1.0) = 2192.2
weight_106 = (50.3 ** 1.0) * (49.0 ** 1.0) = 2464.7  # 只计算运行设备
weight_total = 2192.2 + 2464.7 = 4656.9

# 计算流量
flow_105 = 150.5 * (2192.2 / 4656.9) = 70.8 m³/h
```

**输出**：
```python
# Series (前3行)
0    70.8
1    71.2
2    70.9
dtype: float64
```

### 步骤5：结果验证

**验证统计**：
- 原始数量: 3600
- 有效数量: 3600
- 无效数量: 0
- 有效比例: 100.00%

**输出**：
```python
# valid_results (前3行)
0    70.8
1    71.2
2    70.9
dtype: float64

# is_valid (前3行)
0    True
1    True
2    True
dtype: bool
```

### 步骤6：数据写入

**输入**：
- metric_key = 'pump_flow_rate'
- device_id = 105
- results = [70.8, 71.2, 70.9, ...]（3600个值）

**写入过程**：
- 批次1: 1000行，耗时0.5秒，吞吐量2000行/秒
- 批次2: 1000行，耗时0.5秒，吞吐量2000行/秒
- 批次3: 1000行，耗时0.5秒，吞吐量2000行/秒
- 批次4: 600行，耗时0.3秒，吞吐量2000行/秒

**输出**：
- 总行数: 3600
- 批次数: 4
- 总耗时: 1.8秒
- 平均吞吐量: 2000行/秒

---

## 日志输出完整示例

### 完整日志流（单个设备，1小时数据）

```
2025-09-30 00:00:00.123|12345|MainProcess|67890|Thread-1|scheduler.py|schedule|45|INFO|[调度] 开始计算所有指标|{"指标数量": 9, "设备数量": 3, "时间范围": "[2025-09-30 00:00:00, 2025-09-30 01:00:00)", "时间窗口": "1小时", "并发度": 4, "request_id": "calc-pump_flow_rate-105-1727654400"}

2025-09-30 00:00:00.234|12345|MainProcess|67890|Thread-1|scheduler.py|schedule|78|INFO|[调度] 开始计算指标: pump_flow_rate|{"指标": "pump_flow_rate", "设备数量": 3, "任务总数": 3}

2025-09-30 00:00:00.345|12345|MainProcess|67891|Thread-2|pipeline.py|execute|23|INFO|[流水线] 开始执行|{"指标": "pump_flow_rate", "泵站ID": 14, "设备ID": 105, "时间范围": "[2025-09-30 00:00:00, 2025-09-30 01:00:00)"}

2025-09-30 00:00:00.456|12345|MainProcess|67891|Thread-2|data_loader.py|load|56|INFO|[数据获取] 开始加载|{"泵站ID": 14, "设备ID": 105, "时间范围": "[2025-09-30 00:00:00, 2025-09-30 01:00:00)"}

2025-09-30 00:00:01.234|12345|MainProcess|67891|Thread-2|setup.py|log_sql|1153|INFO|[SQL] 执行|{"type": "SQL", "sql": "SELECT ts, value as main_pipeline_flow_rate FROM fact_measurements WHERE ...", "params": {"station_id": 14}, "duration_ms": 778, "rows": 3600, "result": "ok"}

2025-09-30 00:00:01.567|12345|MainProcess|67891|Thread-2|setup.py|log_sql|1153|INFO|[SQL] 执行|{"type": "SQL", "sql": "SELECT ts, metric_key, value FROM fact_measurements WHERE ...", "params": {"device_id": 105}, "duration_ms": 333, "rows": 7200, "result": "ok"}

2025-09-30 00:00:01.890|12345|MainProcess|67891|Thread-2|setup.py|log_sql|1153|INFO|[SQL] 执行|{"type": "SQL", "sql": "SELECT ts, device_id, metric_key, value FROM fact_measurements WHERE ...", "params": {"station_id": 14}, "duration_ms": 323, "rows": 7200, "result": "ok"}

2025-09-30 00:00:02.123|12345|MainProcess|67891|Thread-2|data_loader.py|load|145|INFO|[数据获取] 加载完成|{"设备ID": 105, "原始行数": 3600, "时间跨度": "1.00小时"}

2025-09-30 00:00:02.234|12345|MainProcess|67891|Thread-2|data_filter.py|filter|234|INFO|[数据过滤] 开始过滤|{"原始行数": 3600}

2025-09-30 00:00:02.456|12345|MainProcess|67891|Thread-2|data_filter.py|filter|278|INFO|[数据过滤] 过滤完成|{"原始行数": 3600, "移除NaN": 0, "移除负值": 0, "移除停机": 0, "移除异常值": 0, "最终行数": 3600, "过滤比例": "0.00%"}

2025-09-30 00:00:02.567|12345|MainProcess|67891|Thread-2|method_selector.py|select|123|INFO|[方法选择] 开始选择|{"可用数据行数": 3600}

2025-09-30 00:00:02.678|12345|MainProcess|67891|Thread-2|method_selector.py|select|145|DEBUG|[方法选择] 检查方法|{"方法ID": "method_a", "方法名称": "功率×频率分摊", "优先级": 100, "依赖满足": true, "条件满足": true}

2025-09-30 00:00:02.789|12345|MainProcess|67891|Thread-2|method_selector.py|select|167|INFO|[方法选择] 选择完成|{"选择方法": "method_a", "方法名称": "功率×频率分摊", "优先级": 100}

2025-09-30 00:00:02.890|12345|MainProcess|67891|Thread-2|calculator.py|calculate|89|INFO|[计算执行] 开始计算|{"设备ID": 105, "方法ID": "method_a", "数据行数": 3600, "参数": {"alpha": 1.0, "beta": 1.0}}

2025-09-30 00:00:03.123|12345|MainProcess|67891|Thread-2|calculator.py|calculate|234|INFO|[计算执行] 计算完成|{"设备ID": 105, "方法ID": "method_a", "结果数量": 3600, "结果统计": {"最小值": 65.2, "最大值": 75.8, "平均值": 70.5, "中位数": 70.4}, "耗时秒": 0.233}

2025-09-30 00:00:03.234|12345|MainProcess|67891|Thread-2|validator.py|validate|123|INFO|[结果验证] 开始验证|{"结果数量": 3600, "验证规则": ["范围", "非负", "NaN/Inf", "物理约束"]}

2025-09-30 00:00:03.456|12345|MainProcess|67891|Thread-2|validator.py|validate|189|INFO|[结果验证] 验证完成|{"原始数量": 3600, "有效数量": 3600, "无效数量": 0, "有效比例": "100.00%"}

2025-09-30 00:00:03.567|12345|MainProcess|67891|Thread-2|data_writer.py|write_batch|123|INFO|[数据写入] 开始写入|{"指标": "pump_flow_rate", "设备ID": 105, "总行数": 3600, "初始批量": 1000}

2025-09-30 00:00:04.067|12345|MainProcess|67891|Thread-2|data_writer.py|write_batch|178|INFO|[数据写入] 批次完成|{"设备ID": 105, "批次序号": 1, "批次大小": 1000, "耗时秒": 0.5, "吞吐量": "2000行/秒"}

2025-09-30 00:00:04.567|12345|MainProcess|67891|Thread-2|data_writer.py|write_batch|178|INFO|[数据写入] 批次完成|{"设备ID": 105, "批次序号": 2, "批次大小": 1000, "耗时秒": 0.5, "吞吐量": "2000行/秒"}

2025-09-30 00:00:05.067|12345|MainProcess|67891|Thread-2|data_writer.py|write_batch|178|INFO|[数据写入] 批次完成|{"设备ID": 105, "批次序号": 3, "批次大小": 1000, "耗时秒": 0.5, "吞吐量": "2000行/秒"}

2025-09-30 00:00:05.367|12345|MainProcess|67891|Thread-2|data_writer.py|write_batch|178|INFO|[数据写入] 批次完成|{"设备ID": 105, "批次序号": 4, "批次大小": 600, "耗时秒": 0.3, "吞吐量": "2000行/秒"}

2025-09-30 00:00:05.478|12345|MainProcess|67891|Thread-2|data_writer.py|write_batch|234|INFO|[数据写入] 写入完成|{"指标": "pump_flow_rate", "设备ID": 105, "总行数": 3600, "批次数": 4, "总耗时秒": 1.8, "平均吞吐量": "2000行/秒"}

2025-09-30 00:00:05.589|12345|MainProcess|67891|Thread-2|pipeline.py|execute|123|INFO|[流水线] 执行完成|{"指标": "pump_flow_rate", "设备ID": 105, "选择方法": "method_a", "结果数量": 3600, "写入行数": 3600, "总耗时秒": 5.244}

2025-09-30 00:00:15.678|12345|MainProcess|67890|Thread-1|scheduler.py|schedule|234|INFO|[调度] 指标 pump_flow_rate 计算完成|{"指标": "pump_flow_rate", "成功任务": 3, "失败任务": 0, "总耗时秒": 15.444}
```

---

## 10. 参数优化方案

### 10.1 优化原理

**核心问题**：无法获得实际测量值，如何优化参数？

**解决方案**：基于物理自洽性优化

由于 `pump_flow_rate` 是从总管流量分摊得到的，我们可以利用以下物理约束进行优化：

### 10.2 优化约束

#### 约束1：流量守恒（权重最高）

```python
# 所有泵的流量之和应该等于总管流量
Σ(Q_i) = Q_total

# 误差计算
conservation_error = |Σ(Q_i) - Q_total| / Q_total
```

**权重**: 10.0（最重要的约束）

#### 约束2：功率-流量相关性

```python
# 功率高的泵，流量应该高
correlation(power, flow) → 1.0

# 误差计算
power_corr_error = 1.0 - correlation(power, flow)
```

**权重**: 2.0

#### 约束3：频率-流量相关性

```python
# 频率高的泵，流量应该高
correlation(frequency, flow) → 1.0

# 误差计算
freq_corr_error = 1.0 - correlation(frequency, flow)
```

**权重**: 2.0

#### 约束4：相对一致性

```python
# 相同功率和频率的泵，流量应该相近
for each pair (i, j) where P_i ≈ P_j and f_i ≈ f_j:
    Q_i ≈ Q_j

# 误差计算
consistency_error = Σ|Q_i - Q_j| / Q_avg
```

**权重**: 5.0

### 10.3 优化目标函数

```python
def objective_function(params):
    """
    优化目标：最小化物理不一致性

    Args:
        params: [alpha, beta]  # 方法A的参数

    Returns:
        total_error: 总误差（越小越好）
    """
    alpha, beta = params

    # 使用参数计算所有设备的流量
    flows = []
    for device in devices:
        weight = (device.power ** alpha) * (device.frequency ** beta)
        flow = total_flow * weight / sum_weights
        flows.append(flow)

    # 约束1: 流量守恒误差
    conservation_error = abs(sum(flows) - total_flow) / total_flow

    # 约束2: 功率-流量相关性
    power_corr = correlation(powers, flows)
    power_corr_error = 1.0 - power_corr

    # 约束3: 频率-流量相关性
    freq_corr = correlation(frequencies, flows)
    freq_corr_error = 1.0 - freq_corr

    # 约束4: 相对一致性
    consistency_error = calculate_consistency_error(flows, powers, frequencies)

    # 加权总误差
    total_error = (
        10.0 * conservation_error +
        2.0 * power_corr_error +
        2.0 * freq_corr_error +
        5.0 * consistency_error
    )

    return total_error
```

### 10.4 优化流程

```python
from scipy.optimize import minimize

# 1. 加载历史数据（过去30天）
data = load_historical_data(
    start_time=datetime.now() - timedelta(days=30),
    end_time=datetime.now()
)

# 2. 加载当前参数
current_params = {
    'alpha': 1.0,
    'beta': 1.0
}

# 3. 执行优化
result = minimize(
    objective_function,
    x0=[current_params['alpha'], current_params['beta']],
    bounds=[(0.5, 2.0), (0.5, 2.0)],  # 参数范围约束
    method='L-BFGS-B'
)

optimized_params = {
    'alpha': result.x[0],
    'beta': result.x[1]
}

# 4. 评估优化效果
improvement = evaluate_improvement(current_params, optimized_params, data)

# 5. 如果改进显著（>10%），保存新参数
if improvement['total_error_reduction'] > 0.1:
    save_optimized_parameters(optimized_params)
```

### 10.5 优化频率建议

- **推荐频率**：每月1次
- **数据窗口**：过去30天
- **触发条件**：
  - 定时触发：每月1号凌晨2点
  - 手动触发：通过CLI命令
  - 条件触发：当流量守恒误差 > 5% 时

### 10.6 预期优化效果

基于物理约束的优化，预期可以达到：

| 指标 | 优化前 | 优化后 | 改进幅度 |
|------|--------|--------|----------|
| 流量守恒误差 | 5.2% | 2.1% | ✅ 60% |
| 功率-流量相关性 | 0.85 | 0.92 | ✅ 8% |
| 频率-流量相关性 | 0.82 | 0.90 | ✅ 10% |
| 相对一致性误差 | 12.5% | 6.8% | ✅ 46% |

### 10.7 CLI命令示例

```bash
# 优化 pump_flow_rate 的全局参数
python -m app.cli.optimization optimize-metric \
    --metric pump_flow_rate \
    --method method_a \
    --level global \
    --start-time 2025-09-01T00:00:00 \
    --end-time 2025-09-30T23:59:59

# 优化14号泵站的参数
python -m app.cli.optimization optimize-metric \
    --metric pump_flow_rate \
    --method method_a \
    --level station \
    --station-id 14 \
    --start-time 2025-09-01T00:00:00 \
    --end-time 2025-09-30T23:59:59
```

### 10.8 增强功能

**参数优化器支持6项增强功能**（详见 `06-参数优化器增强设计.md`）：

#### 1. 自适应权重调整

根据14号泵站的数据特点自动调整权重：

```bash
# 如果14号泵站的功率数据区分度高（变异系数>30%）
# 系统会自动增加功率相关性权重：2.0 → 3.0

# 优化时会自动应用
python -m app.cli.optimization optimize-metric \
    --metric pump_flow_rate \
    --method method_a \
    --level station \
    --station-id 14 \
    --start-time 2025-09-01T00:00:00 \
    --end-time 2025-09-30T23:59:59
```

#### 2. 分层优化策略

一次性优化全局、所有泵站、所有设备的参数：

```bash
# 执行分层优化
python -m app.cli.optimization hierarchical-optimize \
    --metric pump_flow_rate \
    --method method_a \
    --start-time 2025-09-01T00:00:00 \
    --end-time 2025-09-30T23:59:59

# 结果：
# - 全局参数: alpha=1.265, beta=0.935
# - 14号泵站: alpha=1.285, beta=0.920 (偏离全局 +1.6%, -1.6%)
# - 105号设备: alpha=1.295, beta=0.915 (偏离泵站 +0.8%, -0.5%)
```

#### 3. 增量优化

日常运维时，只使用最近7天数据进行快速优化：

```bash
# 增量优化（使用最近7天数据）
python -m app.cli.optimization incremental-optimize \
    --metric pump_flow_rate \
    --method method_a \
    --level global \
    --incremental-days 7

# 优势：
# - 计算速度快（数据量减少80%）
# - 可以更频繁地优化（每周一次）
# - 及时响应设备特性变化
```

#### 4. 多目标优化

使用differential_evolution算法，找到Pareto最优解：

```bash
# 多目标优化
python -m app.cli.optimization multi-objective-optimize \
    --metric pump_flow_rate \
    --method method_a \
    --level global \
    --start-time 2025-09-01T00:00:00 \
    --end-time 2025-09-30T23:59:59

# 优势：
# - 平衡多个约束
# - 避免某个约束被过度牺牲
```

#### 5. 参数变化趋势监控

智能判断是否需要优化：

```bash
# 检查是否需要优化
python -m app.cli.optimization check-trigger \
    --metric pump_flow_rate \
    --method method_a \
    --level global

# 触发条件：
# 1. 参数方差 > 0.01（参数变化趋势明显）
# 2. 流量守恒误差 > 5%（计算精度下降）
# 3. 距离上次优化 > 30天（时间过长）
# 4. 数据量增加 > 50%（数据显著增加）
```

#### 6. 跨指标联合优化

联合优化pump_flow_rate、pump_head、pump_efficiency：

```bash
# 联合优化3个相关指标
python -m app.cli.optimization joint-optimize \
    --metrics pump_flow_rate pump_head pump_efficiency \
    --level global \
    --start-time 2025-09-01T00:00:00 \
    --end-time 2025-09-30T23:59:59

# 优势：
# - 利用能量守恒约束：P_hydraulic = ρ × g × Q × H
# - 确保指标间的一致性
# - 提高所有指标的计算精度
```

---

**文档状态**: pump_flow_rate 详细设计完成 ✅（已添加参数优化方案和增强功能）
**下一步**: 等待用户确认，准备进入计划模式

