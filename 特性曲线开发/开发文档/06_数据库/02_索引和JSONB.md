# 特性曲线拟合系统 - 索引和JSONB设计

**版本**: v3.2
**创建日期**: 2025-12-03
**最后更新**: 2025-12-07
**来源**: 原06_数据库和配置设计.md 第3-4章
**状态**: 设计完成

> **v3.2更新日志**：
> - **[P1-1修复]** 添加JSONB字段GIN索引和表达式索引
> - **[P1-2修复]** 添加JSONB字段schema验证策略

---

## 📋 目录

- [1. 索引设计](#1-索引设计)
- [2. JSONB字段结构](#2-jsonb字段结构)
  - [2.1 physics_validation 结构](#21-physics_validation-结构)
  - [2.2 curve_points 结构](#22-curve_points-结构)
  - [2.3 normalization_params 结构](#23-normalization_params-结构)
  - [2.4 constraints 结构](#24-constraints-结构)
  - [2.5 auto_validation_result 结构](#25-auto_validation_result-结构)
  - [2.6 correction_model 结构（含distribution_snapshot）](#26-correction_model-结构p2泵组v30扩展)
  - [2.7 台数特性曲线存储结构【v3.0新增】](#27-台数特性曲线存储结构v30新增)
  - [2.8 泵组最优运行区域存储结构【v3.0新增】](#28-泵组最优运行区域存储结构v30新增)
  - [2.9 比能耗曲线存储结构【v3.0新增】](#29-比能耗曲线存储结构v30新增)
  - [2.10 控制策略曲线存储结构【v3.0新增】](#210-控制策略曲线存储结构v30新增)
- [3. 查询示例](#3-查询示例)

---

## 1. 索引设计

### 1.1 主表索引

```sql
-- 设备+曲线类型查询（最常用）
CREATE INDEX idx_results_device_curve
ON curve_fit_results(device_id, curve_type);

-- 版本查询
CREATE INDEX idx_results_version
ON curve_fit_results(version);

-- 时间范围查询
CREATE INDEX idx_results_created_at
ON curve_fit_results(created_at DESC);

-- 状态过滤（部分索引）
CREATE INDEX idx_results_status
ON curve_fit_results(status)
WHERE status = 'active';

-- 方法名称查询
CREATE INDEX idx_results_method
ON curve_fit_results(method_name);

-- P2扩展：泵组索引
CREATE INDEX idx_results_station
ON curve_fit_results(station_id);

CREATE INDEX idx_results_pump_combination
ON curve_fit_results USING GIN(pump_combination);
```

### 1.2 参数表索引

```sql
-- 结果ID查询（外键）
CREATE INDEX idx_params_result_id
ON curve_fit_params(result_id);

-- 参数类别查询
CREATE INDEX idx_params_category
ON curve_fit_params(param_category);

-- 参数名查询
CREATE INDEX idx_params_key
ON curve_fit_params(param_key);
```

### 1.3 指标表索引

```sql
-- 结果ID查询（外键）
CREATE INDEX idx_metrics_result_id
ON curve_fit_metrics(result_id);

-- R²排序查询
CREATE INDEX idx_metrics_r_squared
ON curve_fit_metrics(r_squared DESC);
```

### 1.4 学习约束表索引

```sql
CREATE INDEX idx_learned_constraints_device
ON learned_constraints(device_id);

CREATE INDEX idx_learned_constraints_applied
ON learned_constraints(is_applied);

CREATE INDEX idx_learned_constraints_created
ON learned_constraints(created_at DESC);
```

### 1.5 JSONB字段索引（v3.1新增）

#### 1.5.1 GIN索引（通用JSONB查询）

```sql
-- physics_validation字段GIN索引
CREATE INDEX idx_results_physics_validation_gin
ON curve_fit_results USING GIN(physics_validation);

-- curve_points字段GIN索引
CREATE INDEX idx_results_curve_points_gin
ON curve_fit_results USING GIN(curve_points);

-- normalization_params字段GIN索引
CREATE INDEX idx_results_normalization_params_gin
ON curve_fit_results USING GIN(normalization_params);

-- constraints字段GIN索引
CREATE INDEX idx_results_constraints_gin
ON curve_fit_results USING GIN(constraints);

-- auto_validation_result字段GIN索引
CREATE INDEX idx_results_auto_validation_gin
ON curve_fit_results USING GIN(auto_validation_result);

-- correction_model字段GIN索引（P2泵组）
CREATE INDEX idx_results_correction_model_gin
ON curve_fit_results USING GIN(correction_model);
```

#### 1.5.2 表达式索引（常用查询路径）

```sql
-- 查询BEP点流量
CREATE INDEX idx_results_bep_q
ON curve_fit_results((curve_points->'bep'->>'Q'));

-- 查询BEP点扬程
CREATE INDEX idx_results_bep_h
ON curve_fit_results((curve_points->'bep'->>'H'));

-- 查询BEP点效率
CREATE INDEX idx_results_bep_eta
ON curve_fit_results((curve_points->'bep'->>'eta'));

-- 查询物理验证总体结果
CREATE INDEX idx_results_physics_valid
ON curve_fit_results((physics_validation->>'overall_valid'));

-- 查询单调性验证结果
CREATE INDEX idx_results_monotonicity_valid
ON curve_fit_results((physics_validation->'monotonicity'->>'is_valid'));

-- 查询归一化频率
CREATE INDEX idx_results_norm_freq
ON curve_fit_results((normalization_params->>'freq_rated'));

-- 查询自动验证通过状态
CREATE INDEX idx_results_auto_validation_passed
ON curve_fit_results((auto_validation_result->>'passed'));
```

#### 1.5.3 索引策略说明

**GIN索引适用场景**：
- 需要查询JSONB内部任意键值对
- 使用`@>`、`?`、`?&`、`?|`等JSONB操作符
- 查询路径不固定或需要灵活查询

**表达式索引适用场景**：
- 查询路径固定且频繁使用
- 需要对提取的值进行排序或范围查询
- 查询性能要求高

**索引维护建议**：
- GIN索引占用空间较大，定期监控索引大小
- 表达式索引只为高频查询路径创建
- 使用`EXPLAIN ANALYZE`验证索引效果
- 定期执行`REINDEX`维护索引性能

---

## 2. JSONB字段结构

### 2.1 physics_validation 结构

```json
{
    "monotonicity": {
        "is_valid": true,
        "ratio": 0.98,
        "expected": "decreasing",
        "violations": []
    },
    "boundary": {
        "H0_valid": true,
        "H0_deviation": 0.05,
        "H0_expected_range": [45.0, 55.0]
    },
    "overall_valid": true,
    "validation_time": "2025-01-28T10:30:00Z"
}
```

### 2.2 curve_points 结构

```json
{
    "bep": {
        "Q": 250.0,
        "H": 45.0,
        "eta": 0.85,
        "P": 35.0
    },
    "shutoff": {
        "Q": 0,
        "H": 55.0
    },
    "max_flow": {
        "Q": 400.0,
        "H": 20.0
    },
    "characteristic_points": [
        {"Q": 100, "H": 52.0, "eta": 0.65},
        {"Q": 200, "H": 48.0, "eta": 0.80},
        {"Q": 300, "H": 38.0, "eta": 0.82}
    ],
    "sampling_points": [
        {"Q": 50, "H": 54.0},
        {"Q": 150, "H": 50.0},
        {"Q": 250, "H": 45.0},
        {"Q": 350, "H": 30.0}
    ]
}
```

### 2.3 normalization_params 结构

```json
{
    "Q_rated": 300.0,
    "H_rated": 45.0,
    "P_rated": 55.0,
    "eta_rated": 0.85,
    "frequency": 50.0,
    "normalized": true,
    "normalization_method": "similarity_law"
}
```

### 2.4 constraints 结构（learned_constraints表）

```json
{
    "H0_min": 42.5,
    "H0_max": 57.3,
    "Q_max": 2100.0,
    "K_min": -0.05,
    "K_max": -0.001,
    "boundary_tolerance": 0.1,
    "monotonicity_tolerance": 0.05
}
```

### 2.5 auto_validation_result 结构

```json
{
    "overall_passed": true,
    "confidence_level": "high",
    "validation_results": {
        "sample_count": {
            "passed": true,
            "reason": "样本数量充足（≥50）"
        },
        "statistical_distribution": {
            "passed": true,
            "details": [
                {"param": "H0", "check": "coefficient_of_variation", "passed": true, "value": 0.048}
            ]
        },
        "deviation_from_rated": {
            "passed": true,
            "details": [
                {"param": "H0", "deviation": 0.111, "threshold": 0.5}
            ]
        }
    },
    "summary": "自动验证通过（置信度：high）"
}
```

### 2.6 correction_model 结构（P2泵组）【v3.0扩展】

```json
{
    "model_type": "linear",
    "coefficients": {
        "alpha_intercept": 0.98,
        "alpha_coef_N": -0.02,
        "alpha_coef_Q": -0.00001
    },
    "formula": "alpha = 0.98 - 0.02*N - 0.00001*Q",
    "r_squared": 0.95,
    "valid_range": {
        "N": [1, 6],
        "Q": [0, 12000]
    },

    "distribution_snapshot": {
        "timestamp": "2025-12-05T10:00:00+08:00",
        "H_system": 35.0,
        "pump_combination": [101, 102, 201],

        "flow_distribution": {
            "101": 0.35,
            "102": 0.32,
            "201": 0.33
        },

        "power_distribution": {
            "101": 0.30,
            "102": 0.45,
            "201": 0.25
        },

        "load_distribution": {
            "101": 0.40,
            "102": 0.41,
            "201": 0.45
        }
    }
}
```

**distribution_snapshot字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | string | 快照生成时间 |
| `H_system` | float | 系统扬程基准 (m) |
| `pump_combination` | array | 运行泵ID列表 |
| `flow_distribution` | object | 各泵流量占比 |
| `power_distribution` | object | 各泵功率占比 |
| `load_distribution` | object | 各泵负荷率 |

### 2.7 台数特性曲线存储结构【v3.0新增】

> 用于存储N-Q、N-P、N-η曲线数据（曲线4-6）

```json
{
    "curve_category": "pump_count_characteristics",
    "generated_at": "2025-12-05T10:00:00+08:00",
    "H_system": 35.0,
    "pump_combination": [101, 102, 103, 104],
    "selection_strategy": "sequential",

    "n_q_curve": {
        "description": "并联台数-流量曲线",
        "data": [
            {"N": 1, "Q_total": 450.0, "selected_pumps": [101]},
            {"N": 2, "Q_total": 880.0, "selected_pumps": [101, 102]},
            {"N": 3, "Q_total": 1290.0, "selected_pumps": [101, 102, 103]},
            {"N": 4, "Q_total": 1680.0, "selected_pumps": [101, 102, 103, 104]}
        ],
        "unit_Q": "m³/h"
    },

    "n_p_curve": {
        "description": "并联台数-功率曲线",
        "data": [
            {"N": 1, "P_total": 55.0, "pump_powers": {"101": 55.0}},
            {"N": 2, "P_total": 108.0, "pump_powers": {"101": 54.0, "102": 54.0}},
            {"N": 3, "P_total": 158.0, "pump_powers": {"101": 53.0, "102": 53.0, "103": 52.0}},
            {"N": 4, "P_total": 205.0, "pump_powers": {"101": 52.0, "102": 52.0, "103": 51.0, "104": 50.0}}
        ],
        "unit_P": "kW"
    },

    "n_eta_curve": {
        "description": "并联台数-效率曲线",
        "data": [
            {"N": 1, "eta_total": 0.78, "eta_per_pump": {"101": 0.78}},
            {"N": 2, "eta_total": 0.76, "eta_per_pump": {"101": 0.77, "102": 0.75}},
            {"N": 3, "eta_total": 0.74, "eta_per_pump": {"101": 0.75, "102": 0.74, "103": 0.73}},
            {"N": 4, "eta_total": 0.72, "eta_per_pump": {"101": 0.73, "102": 0.72, "103": 0.72, "104": 0.71}}
        ],
        "unit_eta": "dimensionless"
    }
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `curve_category` | string | 标识为台数特性曲线 |
| `H_system` | float | 系统扬程基准 (m) |
| `selection_strategy` | string | 泵选择策略：sequential/best_efficiency/lowest_power |
| `n_q_curve.data` | array | N-Q曲线数据点 |
| `selected_pumps` | array | 各台数下选用的泵ID |
| `pump_powers` | object | 各泵功率明细 |
| `eta_per_pump` | object | 各泵效率明细 |

### 2.8 泵组最优运行区域存储结构【v3.0新增】

> 用于存储高效运行区域和最佳效率点（曲线13）

```json
{
    "optimal_region": {
        "description": "泵组高效运行区域",
        "efficiency_threshold": 0.75,
        "H_range": [25.0, 50.0],
        "Q_range": [800.0, 1800.0],
        "scan_step": 1.0,

        "region_points": [
            {"H": 30.0, "Q": 1200.0, "eta": 0.78, "N": 3},
            {"H": 32.0, "Q": 1150.0, "eta": 0.79, "N": 3},
            {"H": 34.0, "Q": 1100.0, "eta": 0.80, "N": 2},
            {"H": 36.0, "Q": 1050.0, "eta": 0.81, "N": 2}
        ],

        "bep": {
            "H": 35.0,
            "Q": 1050.0,
            "eta": 0.82,
            "N": 2,
            "description": "泵组最佳效率点"
        },

        "boundary": {
            "H_min": 28.0,
            "H_max": 42.0,
            "Q_min": 800.0,
            "Q_max": 1600.0
        },

        "generated_at": "2025-12-05T10:00:00+08:00"
    }
}
```

### 2.9 比能耗曲线存储结构【v3.0新增】【v3.1修复P82：键名统一】

> 用于存储比能耗(SEC)随扬程变化的曲线（曲线14）
> ⚠️ v3.1修复P82：JSONB键名从 `specific_energy_curve` 改为 `specific_energy`，与 curve_type 枚举值保持一致

```json
{
    "specific_energy": {
        "description": "泵组比能耗曲线",
        "pump_ids": [101, 102, 103],
        "H_range": [20.0, 60.0],
        "step": 2.0,

        "curve_data": [
            {"H": 20.0, "Q": 1800.0, "P": 180.0, "SEC": 0.100},
            {"H": 25.0, "Q": 1600.0, "P": 175.0, "SEC": 0.109},
            {"H": 30.0, "Q": 1400.0, "P": 170.0, "SEC": 0.121},
            {"H": 35.0, "Q": 1200.0, "P": 155.0, "SEC": 0.129},
            {"H": 40.0, "Q": 1000.0, "P": 145.0, "SEC": 0.145},
            {"H": 45.0, "Q": 800.0, "P": 130.0, "SEC": 0.163}
        ],

        "min_sec": {
            "H": 20.0,
            "Q": 1800.0,
            "P": 180.0,
            "SEC": 0.100,
            "description": "最低比能耗点"
        },

        "avg_sec": 0.128,
        "unit_sec": "kWh/m³",

        "generated_at": "2025-12-05T10:00:00+08:00"
    }
}
```

### 2.10 控制策略曲线存储结构【v3.0新增】

> 用于存储启停策略、切换时机、切换过程、协调控制曲线（曲线10-12, 15）

#### 2.10.1 启停策略曲线（曲线10）

```json
{
    "start_stop_strategy": {
        "description": "泵组启停策略曲线",
        "strategy_type": "efficiency_priority",
        "config": {
            "start_margin": 0.90,
            "stop_margin": 0.80,
            "min_run_time": 300
        },

        "thresholds": {
            "start_2nd": 540.0,
            "start_3rd": 990.0,
            "start_4th": 1440.0,
            "stop_4th": 1080.0,
            "stop_3rd": 720.0,
            "stop_2nd": 360.0
        },

        "priority_sequence": [101, 102, 103, 104],

        "curve_data": [
            {"N": 1, "Q_max": 600.0, "start_next_at": 540.0, "stop_current_at": null},
            {"N": 2, "Q_max": 1100.0, "start_next_at": 990.0, "stop_current_at": 360.0},
            {"N": 3, "Q_max": 1600.0, "start_next_at": 1440.0, "stop_current_at": 720.0},
            {"N": 4, "Q_max": 2000.0, "start_next_at": null, "stop_current_at": 1080.0}
        ],

        "generated_at": "2025-12-05T10:00:00+08:00"
    }
}
```

#### 2.10.2 切换时机曲线（曲线11）

```json
{
    "switching_timing": {
        "description": "泵组切换时机曲线",
        "hysteresis": 50.0,

        "crossover_points": [
            {
                "from_N": 1,
                "to_N": 2,
                "Q_crossover": 550.0,
                "eta_at_crossover": 0.78,
                "description": "1台切换到2台的效率交叉点"
            },
            {
                "from_N": 2,
                "to_N": 3,
                "Q_crossover": 1050.0,
                "eta_at_crossover": 0.76
            },
            {
                "from_N": 3,
                "to_N": 4,
                "Q_crossover": 1550.0,
                "eta_at_crossover": 0.74
            }
        ],

        "switching_zones": [
            {"from_N": 1, "to_N": 2, "Q_min": 500.0, "Q_max": 600.0},
            {"from_N": 2, "to_N": 3, "Q_min": 1000.0, "Q_max": 1100.0},
            {"from_N": 3, "to_N": 4, "Q_min": 1500.0, "Q_max": 1600.0}
        ],

        "generated_at": "2025-12-05T10:00:00+08:00"
    }
}
```

#### 2.10.3 切换过程曲线（曲线12）

```json
{
    "switching_process": {
        "description": "泵组切换过程曲线",
        "action": "stop",
        "pump_changed": [103],
        "pumps_before": [101, 102, 103],
        "pumps_after": [101, 102],

        "trajectory": [
            {"t": 0, "Q": 1200.0, "H": 35.0, "P": 120.0, "status": "before"},
            {"t": 5, "Q": 1150.0, "H": 36.5, "P": 115.0, "status": "transitioning"},
            {"t": 10, "Q": 1050.0, "H": 37.0, "P": 105.0, "status": "transitioning"},
            {"t": 15, "Q": 900.0, "H": 36.0, "P": 90.0, "status": "transitioning"},
            {"t": 20, "Q": 850.0, "H": 35.5, "P": 85.0, "status": "transitioning"},
            {"t": 25, "Q": 820.0, "H": 35.2, "P": 82.0, "status": "transitioning"},
            {"t": 30, "Q": 800.0, "H": 35.0, "P": 80.0, "status": "after"}
        ],

        "max_pressure_surge": 2.0,
        "min_flow_dip": 400.0,
        "stabilization_time": 30.0,

        "generated_at": "2025-12-05T10:00:00+08:00"
    }
}
```

#### 2.10.4 协调控制曲线（曲线15）

```json
{
    "coordination_control": {
        "description": "泵组协调控制曲线",
        "control_strategy": "equal_efficiency",
        "Q_target": 1200.0,
        "H_system": 35.0,

        "frequency_allocation": {
            "101": {
                "frequency": 45.0,
                "Q": 420.0,
                "eta": 0.78,
                "P": 45.0,
                "role": "vfd"
            },
            "102": {
                "frequency": 47.0,
                "Q": 450.0,
                "eta": 0.78,
                "P": 48.0,
                "role": "vfd"
            },
            "103": {
                "frequency": 43.0,
                "Q": 330.0,
                "eta": 0.78,
                "P": 35.0,
                "role": "vfd"
            }
        },

        "total_efficiency": 0.78,
        "total_power": 128.0,
        "Q_achieved": 1200.0,
        "optimization_success": true,

        "alternative_strategies": {
            "equal_load": {
                "total_efficiency": 0.76,
                "total_power": 132.0
            },
            "master_slave": {
                "total_efficiency": 0.74,
                "total_power": 138.0
            }
        },

        "generated_at": "2025-12-05T10:00:00+08:00"
    }
}
```

---

## 3. 查询示例

### 3.1 获取设备最新曲线

```sql
SELECT r.*, m.r_squared, m.rmse
FROM curve_fit_results r
JOIN curve_fit_metrics m ON r.id = m.result_id
WHERE r.device_id = 12345
  AND r.curve_type = 'qh'
  AND r.status = 'active'
ORDER BY r.created_at DESC
LIMIT 1;
```

### 3.2 获取拟合系数

```sql
SELECT p.param_key, p.param_value
FROM curve_fit_params p
WHERE p.result_id = 100
  AND p.param_category = 'fit'
ORDER BY p.param_key;
```

### 3.3 查询高精度拟合结果

```sql
SELECT r.device_id, r.curve_type, m.r_squared
FROM curve_fit_results r
JOIN curve_fit_metrics m ON r.id = m.result_id
WHERE m.r_squared > 0.95
  AND r.status = 'active'
ORDER BY m.r_squared DESC;
```

### 3.4 JSONB查询示例

```sql
-- 查询BEP点
SELECT
    device_id,
    curve_points->'bep'->>'Q' as bep_flow,
    curve_points->'bep'->>'eta' as bep_efficiency
FROM curve_fit_results
WHERE curve_type = 'qeta';

-- 查询物理验证通过的结果
SELECT id, device_id, curve_type
FROM curve_fit_results
WHERE (physics_validation->>'overall_valid')::boolean = true;

-- 查询已应用的约束参数
SELECT
    device_id,
    curve_type,
    constraints,
    auto_validation_result->>'confidence_level' as confidence
FROM learned_constraints
WHERE is_applied = true;
```

### 3.5 v3.0新增JSONB查询示例

```sql
-- 查询台数特性曲线N-Q数据
SELECT
    station_id,
    pump_combination,
    curve_points->'n_q_curve'->'data' as n_q_data,
    curve_points->>'selection_strategy' as strategy
FROM curve_fit_results
WHERE curve_type = 'pump_group'
  AND curve_points->>'curve_category' = 'pump_count_characteristics';

-- 查询泵组最优运行区域BEP
SELECT
    station_id,
    curve_points->'optimal_region'->'bep'->>'Q' as bep_flow,
    curve_points->'optimal_region'->'bep'->>'eta' as bep_efficiency,
    curve_points->'optimal_region'->'bep'->>'N' as bep_pump_count
FROM curve_fit_results
WHERE curve_type = 'pump_group_optimal';

-- 查询启停策略阈值
SELECT
    station_id,
    curve_points->'start_stop_strategy'->'thresholds' as thresholds,
    curve_points->'start_stop_strategy'->'priority_sequence' as priority
FROM curve_fit_results
WHERE curve_type = 'pump_group_control';

-- 查询协调控制频率分配
SELECT
    station_id,
    curve_points->'coordination_control'->>'control_strategy' as strategy,
    curve_points->'coordination_control'->'frequency_allocation' as freq_alloc,
    (curve_points->'coordination_control'->>'total_efficiency')::float as eta
FROM curve_fit_results
WHERE curve_type = 'pump_group_coordination';

-- 查询最低比能耗点【v3.1修复P82：键名和curve_type统一】
SELECT
    station_id,
    curve_points->'specific_energy'->'min_sec'->>'H' as optimal_H,
    curve_points->'specific_energy'->'min_sec'->>'SEC' as min_sec,
    curve_points->'specific_energy'->>'avg_sec' as avg_sec
FROM curve_fit_results
WHERE curve_type = 'specific_energy';
```

### 3.6 使用完整视图查询

```sql
-- 使用 v_curve_fit_full 视图简化查询
SELECT
    device_id,
    curve_type,
    method_name,
    r_squared,
    fit_params->>'a0' as a0,
    fit_params->>'a1' as a1,
    fit_params->>'a2' as a2
FROM v_curve_fit_full
WHERE device_id = 12345
  AND status = 'active';
```

---

## 4. JSONB字段Schema验证（v3.2新增）

### 4.1 验证策略

**双层验证机制**：
1. **应用层验证**（主要）：使用Pydantic模型进行严格的schema验证
2. **数据库层验证**（辅助）：使用CHECK约束进行基本的结构验证

### 4.2 应用层验证（Pydantic）

#### 4.2.1 physics_validation Schema

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class MonotonicityValidation(BaseModel):
    is_valid: bool
    ratio: float = Field(ge=0, le=1)
    expected: str  # "decreasing", "increasing", "single_peak"
    violations: List[dict] = []

class BoundaryValidation(BaseModel):
    H0_valid: bool
    H0_deviation: float
    H0_expected_range: List[float]

class PhysicsValidation(BaseModel):
    monotonicity: MonotonicityValidation
    boundary: BoundaryValidation
    overall_valid: bool
    validation_time: datetime
```

#### 4.2.2 curve_points Schema

```python
class Point(BaseModel):
    Q: float = Field(ge=0)
    H: Optional[float] = Field(ge=0, default=None)
    eta: Optional[float] = Field(ge=0, le=1, default=None)
    P: Optional[float] = Field(ge=0, default=None)

class CurvePoints(BaseModel):
    bep: Optional[Point] = None
    shutoff: Optional[Point] = None
    max_flow: Optional[Point] = None
    characteristic_points: List[Point] = []
    sampling_points: List[Point] = []
```

#### 4.2.3 normalization_params Schema

```python
class NormalizationParams(BaseModel):
    Q_rated: float = Field(gt=0)
    H_rated: float = Field(gt=0)
    P_rated: Optional[float] = Field(gt=0, default=None)
    eta_rated: Optional[float] = Field(gt=0, le=1, default=None)
    freq_rated: float = Field(gt=0, default=50.0)
    freq_actual: Optional[float] = Field(gt=0, default=None)
```

#### 4.2.4 constraints Schema

```python
class Constraints(BaseModel):
    Q_min: Optional[float] = Field(ge=0, default=None)
    Q_max: Optional[float] = Field(ge=0, default=None)
    H_min: Optional[float] = Field(ge=0, default=None)
    H_max: Optional[float] = Field(ge=0, default=None)
    monotonicity: Optional[str] = None  # "decreasing", "increasing", "single_peak"
    convexity: Optional[str] = None  # "concave", "convex"
```

### 4.3 数据库层验证（CHECK约束）

#### 4.3.1 基本结构验证

```sql
-- physics_validation必须包含overall_valid字段
ALTER TABLE curve_fit_results
ADD CONSTRAINT check_physics_validation_structure
CHECK (
    physics_validation IS NULL OR
    physics_validation ? 'overall_valid'
);

-- curve_points的bep点必须包含Q字段
ALTER TABLE curve_fit_results
ADD CONSTRAINT check_curve_points_bep
CHECK (
    curve_points IS NULL OR
    curve_points->'bep' IS NULL OR
    curve_points->'bep' ? 'Q'
);

-- normalization_params必须包含Q_rated和H_rated
ALTER TABLE curve_fit_results
ADD CONSTRAINT check_normalization_params_required
CHECK (
    normalization_params IS NULL OR
    (normalization_params ? 'Q_rated' AND normalization_params ? 'H_rated')
);
```

#### 4.3.2 数值范围验证

```sql
-- BEP点效率必须在0-1之间
ALTER TABLE curve_fit_results
ADD CONSTRAINT check_bep_eta_range
CHECK (
    curve_points IS NULL OR
    curve_points->'bep' IS NULL OR
    curve_points->'bep'->>'eta' IS NULL OR
    (curve_points->'bep'->>'eta')::float BETWEEN 0 AND 1
);

-- 额定流量必须大于0
ALTER TABLE curve_fit_results
ADD CONSTRAINT check_q_rated_positive
CHECK (
    normalization_params IS NULL OR
    normalization_params->>'Q_rated' IS NULL OR
    (normalization_params->>'Q_rated')::float > 0
);

-- 额定扬程必须大于0
ALTER TABLE curve_fit_results
ADD CONSTRAINT check_h_rated_positive
CHECK (
    normalization_params IS NULL OR
    normalization_params->>'H_rated' IS NULL OR
    (normalization_params->>'H_rated')::float > 0
);
```

### 4.4 验证实施建议

**应用层验证（推荐）**：
- ✅ 在数据写入前使用Pydantic模型验证
- ✅ 提供详细的错误信息
- ✅ 支持复杂的业务逻辑验证
- ✅ 易于测试和维护

**数据库层验证（辅助）**：
- ✅ 作为最后一道防线
- ✅ 防止绕过应用层的直接数据库操作
- ⚠️ 只验证关键字段和基本约束
- ⚠️ 避免过于复杂的CHECK约束（影响性能）

**验证流程**：
```python
# 1. 应用层验证
physics_validation_data = {...}
validated_data = PhysicsValidation(**physics_validation_data)

# 2. 转换为JSON并写入数据库
result = CurveFitResult(
    physics_validation=validated_data.dict()
)
session.add(result)
session.commit()  # 数据库层CHECK约束自动验证
```

---

## 5. JSONB向后兼容性策略

### 5.1 JSONB结构变更场景

**常见变更类型**：
1. **新增字段**：在现有JSONB对象中添加新字段
2. **字段重命名**：修改字段名称
3. **字段类型变更**：修改字段的数据类型
4. **嵌套结构调整**：修改JSONB的嵌套层级

### 5.2 向后兼容性原则

**核心原则**：
- ✅ 新增字段必须是可选的（使用COALESCE提供默认值）
- ✅ 查询时必须处理字段不存在的情况
- ✅ 应用层代码必须容忍缺失字段
- ⚠️ 避免字段重命名（使用新字段+数据迁移）
- ⚠️ 避免字段类型变更（使用新字段+数据迁移）

### 5.3 查询兼容性处理

#### 5.3.1 使用COALESCE提供默认值

```sql
-- 查询physics_validation的overall_valid字段，旧数据可能没有此字段
SELECT
    device_id,
    curve_type,
    COALESCE(
        (physics_validation->>'overall_valid')::boolean,
        false  -- 默认值
    ) as overall_valid
FROM curve_fit_results;

-- 查询curve_points的bep点，旧数据可能没有此字段
SELECT
    device_id,
    curve_type,
    COALESCE(
        (curve_points->'bep'->>'Q')::float,
        0.0  -- 默认值
    ) as bep_q
FROM curve_fit_results;
```

#### 5.3.2 使用CASE处理多版本结构

```sql
-- 处理字段重命名的情况（旧字段：is_valid，新字段：overall_valid）
SELECT
    device_id,
    curve_type,
    CASE
        WHEN physics_validation ? 'overall_valid' THEN
            (physics_validation->>'overall_valid')::boolean
        WHEN physics_validation ? 'is_valid' THEN
            (physics_validation->>'is_valid')::boolean
        ELSE
            false
    END as validation_result
FROM curve_fit_results;
```

#### 5.3.3 使用jsonb_set更新旧数据

```sql
-- 为旧数据添加缺失的字段
UPDATE curve_fit_results
SET physics_validation = jsonb_set(
    COALESCE(physics_validation, '{}'::jsonb),
    '{overall_valid}',
    'false'::jsonb,
    true  -- create_missing = true
)
WHERE physics_validation IS NULL
   OR NOT (physics_validation ? 'overall_valid');
```

### 5.4 应用层兼容性处理

#### 5.4.1 Pydantic模型使用Optional和默认值

```python
from pydantic import BaseModel, Field
from typing import Optional

class PhysicsValidation(BaseModel):
    # 旧字段（向后兼容）
    is_valid: Optional[bool] = None

    # 新字段（使用默认值）
    overall_valid: bool = Field(default=False)

    # 新增字段（可选）
    validation_time: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建，处理字段缺失"""
        # 如果新字段不存在，尝试从旧字段获取
        if 'overall_valid' not in data and 'is_valid' in data:
            data['overall_valid'] = data['is_valid']
        return cls(**data)
```

#### 5.4.2 读取时容错处理

```python
def load_physics_validation(jsonb_data: dict) -> PhysicsValidation:
    """加载physics_validation，处理旧版本数据"""
    if not jsonb_data:
        return PhysicsValidation()

    # 使用from_dict处理字段映射
    return PhysicsValidation.from_dict(jsonb_data)
```

### 5.5 数据迁移策略

**渐进式迁移**：
1. **阶段1**：应用层同时支持新旧字段
2. **阶段2**：后台任务逐步更新旧数据
3. **阶段3**：确认所有数据已更新后，移除旧字段支持

**迁移脚本示例**：
```sql
-- 迁移脚本：添加overall_valid字段
-- 文件：scripts/sql/migrations/120_add_overall_valid_to_physics_validation.sql

BEGIN;

-- 获取迁移锁
SELECT pg_advisory_xact_lock(999999, 120);

-- 为所有旧数据添加overall_valid字段
UPDATE curve_fit_results
SET physics_validation = jsonb_set(
    COALESCE(physics_validation, '{}'::jsonb),
    '{overall_valid}',
    COALESCE(physics_validation->'is_valid', 'false'::jsonb),
    true
)
WHERE physics_validation IS NOT NULL
  AND NOT (physics_validation ? 'overall_valid');

-- 记录迁移历史
INSERT INTO migration_history (migration_id, description, executed_at)
VALUES ('120_add_overall_valid_to_physics_validation', 'Add overall_valid field to physics_validation', NOW())
ON CONFLICT (migration_id) DO NOTHING;

COMMIT;
```

---

**相关文档**：
- [01_表结构设计.md](./01_表结构设计.md) - 表结构设计
- [03_配置和迁移.md](./03_配置和迁移.md) - 配置和迁移
- [../04_曲线模块/04_并联泵组曲线.md](../04_曲线模块/04_并联泵组曲线.md) - 并联泵组曲线规格

---

**文档结束**

