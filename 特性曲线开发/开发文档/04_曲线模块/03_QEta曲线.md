# 特性曲线拟合系统 - Q-η曲线模块

**版本**: v2.6
**创建日期**: 2025-12-03
**最后更新**: 2025-12-07
**来源**: 原04_曲线和方法模块设计.md 第5章
**状态**: P0 核心模块

> **v2.6更新日志**：
> - **[P0-7修复]** 添加DataExtractionError异常导入说明

---

## 📋 曲线模板

> **说明**：本文档作为曲线模块的标准模板，新增曲线时可参照此结构编写。

---

## 1. 曲线概述

### 1.1 基本信息

| 属性 | 值 |
|------|-----|
| **曲线类型** | `qeta` |
| **物理意义** | 流量-效率关系 |
| **单调性** | 单峰 (先增后减) |
| **推荐方法** | `math_stat_gaussian`, `math_poly_3`, `math_poly_4` |
| **文件路径** | `app/services/characteristic_curves/curves/qeta_curve.py` |

### 1.2 物理特性

| 特性 | 描述 |
|------|------|
| **单调性** | 单峰曲线（先增后减） |
| **最高效率点** | BEP (Best Efficiency Point) |
| **零流量点** | η(0) = 0 |
| **最大流量点** | η(Q_max) → 0 |
| **值域范围** | 0 ≤ η ≤ 1 |

**物理公式**：
```
η = (ρ * g * Q * H) / P

其中：
- ρ = 1000 kg/m³（水的密度）
- g = 9.81 m/s²（重力加速度）
- Q：流量（m³/s，注意单位转换）
- H：扬程（m）
- P：功率（W）
```

**典型曲线形状**：
```
η (%)
│
85 │       ╭───╮
   │      ╱     ╲
75 │     ╱       ╲
   │    ╱         ╲
65 │   ╱           ╲
   │  ╱             ╲
55 │ ╱               ╲
   │╱                 ╲
45 └─────────────────────> Q (m³/h)
   0   100  200  300  400
        ↑
       BEP (最佳效率点)
```

### 1.3 数学模型

**高斯模型**（推荐）：
```
η = η_max × exp(-((Q - Q_bep)² / (2σ²)))
```

**二次多项式模型**：
```
η = c₀ + c₁Q + c₂Q²
```

**约束条件**：
- c₂ < 0 (保证单峰)
- 0 ≤ η ≤ 1 (效率范围)

---

## 2. 子模块设计

### 2.1 模块结构

```
QEtaCurve
├── QEtaDataExtractor    # 数据提取器
├── QEtaPreprocessor     # 预处理器
├── QEtaConstraints      # 物理约束
├── QEtaNormalizer       # 归一化器
├── QEtaMethodSelector   # 方法选择器
├── QEtaCurveFitter      # 拟合器
└── QEtaValidator        # 验证器
```

### 2.2 QEtaDataExtractor 数据提取器

| 属性 | 说明 |
|------|------|
| **职责** | 从 fact_measurements 提取 Q-η 数据 |
| **必需指标** | `pump_flow_rate`, `pump_efficiency` |
| **数据来源** | 直接读取 pump_efficiency，无需计算 |

```python
from datetime import datetime
import pandas as pd
import logging
from app.adapters.db.pool import get_connection
from app.services.characteristic_curves.shared.exceptions import DataExtractionError  # v2.6新增

class QEtaDataExtractor:
    """Q-η曲线数据提取器

    直接从 fact_measurements 读取 pump_efficiency 数据，无需现场计算。
    """

    REQUIRED_METRICS = ['pump_flow_rate', 'pump_efficiency']

    def __init__(self):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def extract(
        self,
        device_id: int,
        start_time: datetime,
        end_time: datetime,
        min_points: int = 100  # 数据提取建议点数（v2.6统一修复）
    ) -> pd.DataFrame:
        """
        提取Q-η数据

        Args:
            device_id: 设备ID
            start_time: 开始时间
            end_time: 结束时间
            min_points: 最小数据点数（默认100，对应MIN_EXTRACTION_POINTS）
                       这是数据提取阶段的建议值，确保有足够数据进行筛选
                       实际拟合时会使用MIN_DATA_POINTS(50)进行验证

        Returns:
            DataFrame: 包含ts_bucket, Q, eta列的数据
        """
        sql = """
            SELECT
                ts_bucket,
                MAX(CASE WHEN metric_id = (
                    SELECT id FROM dim_metric_config
                    WHERE metric_key = 'pump_flow_rate'
                ) THEN value END) AS Q,
                MAX(CASE WHEN metric_id = (
                    SELECT id FROM dim_metric_config
                    WHERE metric_key = 'pump_efficiency'
                ) THEN value END) AS eta
            FROM fact_measurements
            WHERE device_id = %(device_id)s
              AND ts_bucket BETWEEN %(start_time)s AND %(end_time)s
            GROUP BY ts_bucket
            HAVING Q IS NOT NULL AND eta IS NOT NULL
            ORDER BY ts_bucket
        """

        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, {
                    'device_id': device_id,
                    'start_time': start_time,
                    'end_time': end_time
                })
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

        data = pd.DataFrame(rows, columns=columns)

        # pump_efficiency 存储为百分比 (0-100)，转换为小数 (0-1)
        data['eta'] = data['eta'] / 100.0

        return data
```

### 2.3 QEtaConstraints 物理约束

| 约束类型 | 条件 | 说明 |
|---------|------|------|
| **单峰性** | 存在唯一最大值点 | BEP点 |
| **边界-零流量** | η(0) = 0 | 零流量效率为0 |
| **边界-最大流量** | η(Q_max) → 0 | 效率趋近0 |
| **值域** | 0 ≤ η ≤ 1 | 效率范围 |
| **BEP位置** | 0.6*Q_rated < Q_BEP < 1.2*Q_rated | BEP在合理范围 |

**约束计算**：
```python
class QEtaConstraints:
    def calculate(self, data: pd.DataFrame, device_params: Dict) -> Dict:
        """
        计算约束参数

        输出: Dict{Q_BEP, eta_max, Q_rated, eta_rated, unimodal, efficiency_range}
        """
        Q_rated = device_params['rated_flow']
        eta_rated = device_params.get('rated_efficiency', 0.8)

        # 从数据中找到BEP
        idx_max = data['eta'].idxmax()
        Q_BEP = data.loc[idx_max, 'Q']
        eta_max = data.loc[idx_max, 'eta']

        return {
            'Q_BEP': Q_BEP,
            'eta_max': eta_max,
            'Q_rated': Q_rated,
            'eta_rated': eta_rated,
            'unimodal': True,
            'efficiency_range': (0, 1)
        }
```

### 2.4 QEtaValidator 验证器

| 验证项 | 标准 | 说明 |
|--------|------|------|
| **精度** | R² > 0.90 | 拟合优度（效率曲线噪声较大） |
| **误差** | RMSE < 3% | 均方根误差 |
| **单峰性** | 存在唯一BEP | 物理约束 |
| **值域** | 0 ≤ η ≤ 1 | 效率范围 |

---

## 3. 数据流详细

### 3.1 简化版9阶段流程

> **📋 阶段映射说明**：本节描述的是简化版9阶段流程，对应权威13阶段的核心步骤。
> 权威13阶段定义请参见 [02_数据流定义.md](../02_架构设计/02_数据流定义.md)。
>
> | 简化阶段 | 对应权威阶段 | 说明 |
> |:--------:|:------------:|------|
> | 阶段1 | 阶段3 | 数据提取 |
> | 阶段2 | 阶段4 | 数据清洗 |
> | 阶段3 | 阶段6 | 约束计算 |
> | 阶段4 | 阶段8 | 标准化 |
> | 阶段5 | 阶段9 | 方法选择 |
> | 阶段6 | 阶段10 | 拟合 |
> | 阶段7 | 阶段11 | 验证 |
> | 阶段8 | 阶段12 | 历史评估 |
> | 阶段9 | 阶段13 | 存储 |

```
阶段1: 数据提取 [QEtaDataExtractor] (对应权威阶段3)
┌─────────────────────────────────────────────────────────────────────────────┐
│ 输入: device_id, start_time, end_time                                       │
│ 处理:                                                                       │
│   1. 查询 fact_measurements 表                                              │
│   2. 直接提取 pump_flow_rate (Q) 和 pump_efficiency (η) 指标                │
│   3. 按时间戳聚合数据                                                        │
│ 输出: DataFrame[ts_bucket, Q, eta]                                          │
│ 预期数据量: 100-10000行                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
阶段2: 数据清洗 [QEtaPreprocessor]
┌─────────────────────────────────────────────────────────────────────────────┐
│ 输入: DataFrame[ts_bucket, Q, eta]                                          │
│ 处理:                                                                       │
│   1. 删除无效值（Q<0 或 eta<0 或 eta>1）                                     │
│   2. 删除异常值（3σ原则，效率数据噪声较大）                                    │
│   3. 删除重复值                                                              │
│   4. 运行点筛选                                                              │
│ 输出: DataFrame[Q, eta]（清洗后）                                            │
│ 预期数据保留率: 75-90%（效率数据噪声较大）                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
阶段3: 约束计算 [QEtaConstraints]
┌─────────────────────────────────────────────────────────────────────────────┐
│ 输入: DataFrame[Q, eta], device_params                                      │
│ 处理:                                                                       │
│   1. 计算 Q_BEP（最佳效率点流量）: 找到η最大值对应的Q                         │
│   2. 计算 eta_max（最大效率）: η的最大值                                     │
│   3. 验证单峰性约束: 只有一个峰值                                            │
│   4. 验证效率范围: 0 < η < 1                                                │
│   5. 验证BEP位置: 0.6*Q_rated < Q_BEP < 1.2*Q_rated                         │
│ 输出: Dict{Q_BEP, eta_max, Q_rated, eta_rated, unimodal, efficiency_range}  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
阶段4: 归一化 [QEtaNormalizer]
┌─────────────────────────────────────────────────────────────────────────────┐
│ 输入: DataFrame[Q, eta], constraints                                        │
│ 处理:                                                                       │
│   1. Q归一化: Q_norm = Q / Q_rated                                          │
│   2. eta归一化: eta_norm = eta / eta_max                                    │
│   3. 记录归一化参数                                                          │
│ 输出: DataFrame[Q_norm, eta_norm], norm_params                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
阶段5-9: 与QHCurve相同（方法选择、拟合、验证、历史评估、存储）

**重要说明（v2.6修复）**：
- 阶段6拟合采用**顺序执行**策略，与QH曲线保持一致
- 详细流程见 `01_QH曲线.md` 阶段6定义
- 执行策略：顺序执行所有选定方法，按优先级顺序，找到满足条件的方法即可停止
```

---

## 4. 主类实现

```python
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd
import logging

class QEtaCurve(BaseCurve):
    """Q-η曲线（流量-效率）模块"""

    curve_type = 'qeta'
    monotonicity = 'unimodal'
    recommended_methods = ['math_stat_gaussian', 'math_poly_3', 'math_poly_4']

    def _init_submodules(self) -> None:
        """初始化Q-η曲线专用子模块"""
        self._extractor = QEtaDataExtractor()
        self._preprocessor = QEtaPreprocessor()
        self._constraints = QEtaConstraints()
        self._normalizer = QEtaNormalizer()
        self._fitter = QEtaCurveFitter(method_registry=self._get_method_registry())
        self._validator = QEtaValidator()
        self._method_selector = MethodSelector(
            curve_type='qeta',
            recommended_methods=self.recommended_methods
        )

    def extract_data(self, device_id: int, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        return self._extractor.extract(device_id, start_time, end_time)

    def preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        clean_data, _ = self._preprocessor.preprocess(data)
        return clean_data

    def calculate_constraints(self, data: pd.DataFrame, device_params: Dict[str, Any]) -> Dict[str, Any]:
        return self._constraints.calculate(data, device_params)
```

---

## 5. 使用示例

```python
from app.services.characteristic_curves.curves import QEtaCurve
from datetime import datetime

# 创建曲线实例
qeta_curve = QEtaCurve(
    storage=result_storage,
    cache=cache_manager,
    batch_processor=batch_processor,
    parameter_optimizer=parameter_optimizer,
    historical_evaluator=historical_evaluator
)

# 执行拟合
result = qeta_curve.fit(
    device_id=1,
    start_time=datetime(2025, 1, 1),
    end_time=datetime(2025, 1, 25),
    methods=['math_stat_gaussian', 'math_poly_3']
)

print(f"最佳方法: {result.method_name}")
print(f"R²: {result.r_squared:.4f}")
print(f"BEP流量: {result.coefficients.get('q_bep')}")
print(f"最高效率: {result.coefficients.get('eta_max')}")

# 预测效率
Q_values = [100, 200, 300, 400]
for Q in Q_values:
    eta = qeta_curve.predict(Q)
    print(f"Q={Q} m³/h → η={eta:.2%}")
```

---

**相关文档**：
- [00_曲线基类.md](./00_曲线基类.md) - 曲线基类设计
- [05_拟合方法/01_数学方法.md](../05_拟合方法/01_数学方法.md) - 数学方法

---

**文档结束**

