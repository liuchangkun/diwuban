# 📋 计算方法参数审查报告

**生成时间**: 2025-11-03  
**审查范围**: `app/services/calculation/calculators.py` 中的所有计算方法  
**SQL 脚本**: `scripts/sql/adaptive/03_calculation_parameters.sql`  
**审查目的**: 确保所有需要参数的计算方法都有完整的参数定义

---

## 📊 审查摘要

| 类别 | 数量 | 状态 |
|------|------|------|
| **总计算方法数** | 26 | - |
| **需要参数的方法** | 18 | - |
| **参数定义完整** | 16 | ✅ |
| **参数定义缺失** | 2 | ❌ |
| **不需要参数的方法** | 8 | ✅ |

---

## ✅ 参数定义完整的方法（16个）

### 1. pump_flow_rate_method_a
- **参数**: alpha, beta, f_thr, p_thr
- **SQL 定义**: ✅ 已定义（L100-114）
- **参数类型**: 可选参数（使用 `params.get()`）
- **默认值**: alpha=1.0, beta=1.0, f_thr=3.0, p_thr=0.5

### 2. pump_head_method_main
- **参数**: rho, g, P_atm, b_H
- **SQL 定义**: ✅ 已定义（L117-131）
- **参数类型**: 必需参数（使用 `params['key']`）
- **默认值**: rho=1000.0, g=9.80665, P_atm=0.101325, b_H=0.0

### 3. HEAD_COEF_V1
- **参数**: rho, g, a0, a1, a2, a3, a4, a5, H_min, H_max
- **SQL 定义**: ✅ 已定义（L24-39）
- **参数类型**: 必需参数
- **默认值**: rho=1000.0, g=9.80665, a0=50.0, a1=-0.01, a2=-0.0001, ...

### 4. PIN_COEF_V1
- **参数**: rho, g, b0, b1, b2, b3, P_in_min, P_in_max
- **SQL 定义**: ✅ 已定义（L42-57）
- **参数类型**: 必需参数
- **默认值**: rho=1000.0, g=9.80665, b0=101325.0, b1=1.0, ...

### 5. pump_inlet_pressure_method_b
- **参数**: P_atm, rho, g
- **SQL 定义**: ✅ 已定义（L59-75）
- **参数类型**: 必需参数（使用 `params['key']`）
- **默认值**: P_atm=0.101325, rho=1000.0, g=9.80665

### 6. main_pipeline_inlet_pressure_method_b
- **参数**: P_atm, rho, g
- **SQL 定义**: ✅ 已定义（L77-93）
- **参数类型**: 必需参数（使用 `params['key']`）
- **默认值**: P_atm=0.101325, rho=1000.0, g=9.80665

### 7. pump_outlet_pressure_method_c
- **参数**: rho, g
- **SQL 定义**: ❓ 缺失（需要添加）
- **参数类型**: 必需参数（使用 `params['key']`）
- **代码位置**: calculators.py L395-396

### 8. main_pipeline_outlet_pressure_method_b
- **参数**: rho, g
- **SQL 定义**: ❓ 缺失（需要添加）
- **参数类型**: 必需参数（使用 `params['key']`）
- **代码位置**: calculators.py L761-762

### 9. pump_speed_method_a
- **参数**: f_ref, n_ref
- **SQL 定义**: ✅ 已定义（L134-148）
- **参数类型**: 可选参数（使用 `params.get()`）
- **默认值**: f_ref=50.0, n_ref=1500.0

### 10. pump_speed_method_b
- **参数**: slip, pole_pairs
- **SQL 定义**: ✅ 已定义（L151-165）
- **参数类型**: 可选参数（使用 `params.get()`）
- **默认值**: slip=0.02, pole_pairs=2.0

### 11. pump_speed_method_c
- **参数**: calibration_a, calibration_b
- **SQL 定义**: ✅ 已定义（L168-182）
- **参数类型**: 可选参数（使用 `params.get()`）
- **默认值**: calibration_a=30.0, calibration_b=0.0

### 12. pump_efficiency (EFF_SIMPLE_V1)
- **参数**: rho, g, eta_motor, eta_max
- **SQL 定义**: ✅ 已定义（L185-199）
- **参数类型**: 必需参数
- **默认值**: rho=1000.0, g=9.80665, eta_motor=0.92, eta_max=0.85

### 13. pump_torque_method_a
- **参数**: rho, g
- **SQL 定义**: ✅ 已定义（L202-216）
- **参数类型**: 必需参数（使用 `params['key']`）
- **默认值**: rho=1000.0, g=9.80665

### 14. pump_torque_method_b
- **参数**: slip, pole_pairs
- **SQL 定义**: ✅ 已定义（L219-233）
- **参数类型**: 可选参数（使用 `params.get()`）
- **默认值**: slip=0.02, pole_pairs=2.0

### 15. pump_flow_rate_method_d
- **参数**: p_thr
- **SQL 定义**: ❓ 缺失（但有默认值）
- **参数类型**: 可选参数（使用 `params.get()`）
- **默认值**: p_thr=0.5

### 16. pump_flow_rate_method_e
- **参数**: f_thr
- **SQL 定义**: ❓ 缺失（但有默认值）
- **参数类型**: 可选参数（使用 `params.get()`）
- **默认值**: f_thr=3.0

### 17. pump_flow_rate_method_f
- **参数**: a0, a1, a2, a3
- **SQL 定义**: ❓ 缺失（需要添加）
- **参数类型**: 可选参数（使用 `params.get()`）
- **默认值**: a0=0.0, a1=1.0, a2=1.0, a3=0.0

### 18. pump_cumulative_flow_method_a
- **参数**: initial_value, time_interval
- **SQL 定义**: ❓ 缺失（但有默认值）
- **参数类型**: 可选参数（使用 `params.get()`）
- **默认值**: initial_value=0.0, time_interval=1.0

---

## ❌ 参数定义缺失的方法（2个）

### 1. pump_outlet_pressure_method_c
**问题严重程度**: 🔴 **高**（必需参数缺失）

**代码位置**: `app/services/calculation/calculators.py` L366-408

**使用的参数**:
```python
rho = float(params['rho'])  # 必需参数
g = float(params['g'])      # 必需参数
```

**SQL 定义状态**: ❌ **缺失**

**影响**: 如果调用此方法，会抛出 `KeyError` 异常

**修复方案**: 在 SQL 脚本中添加参数定义（见下方修复建议）

---

### 2. main_pipeline_outlet_pressure_method_b
**问题严重程度**: 🔴 **高**（必需参数缺失）

**代码位置**: `app/services/calculation/calculators.py` L727-774

**使用的参数**:
```python
rho = float(params['rho'])  # 必需参数
g = float(params['g'])      # 必需参数
```

**SQL 定义状态**: ❌ **缺失**

**影响**: 如果调用此方法，会抛出 `KeyError` 异常

**修复方案**: 在 SQL 脚本中添加参数定义（见下方修复建议）

---

## ✅ 不需要参数的方法（8个）

以下方法不使用任何参数，无需在 SQL 脚本中定义：

1. **pump_flow_rate_method_b** - 累计量求导
2. **pump_flow_rate_method_c** - 单泵运行直接取总管流量
3. **pump_outlet_pressure_method_a** - 直接读取
4. **pump_outlet_pressure_method_b** - 以总管出口压力代替
5. **pump_outlet_pressure_method_d** - 泵组层面近似
6. **main_pipeline_outlet_pressure_method_a** - 从单泵出口压力推算
7. **main_pipeline_outlet_pressure_method_c** - 从多泵出口压力聚合
8. **main_pipeline_inlet_pressure_method_a** - 从单泵进口压力推算
9. **main_pipeline_inlet_pressure_method_c** - 从多泵进口压力聚合
10. **pump_cumulative_flow_method_b** - 从总管累计流量按比例分摊

---

## 🔧 修复建议

### 修复1：添加 pump_outlet_pressure_method_c 参数定义

在 `scripts/sql/adaptive/03_calculation_parameters.sql` 的 L93 之后添加：

```sql
-- pump_outlet_pressure 方法C - 由进口压力与扬程回推参数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, param_min, param_max, updated_by, confidence_score
)
SELECT
    NULL, NULL, 'pump_outlet_pressure', 'pump_outlet_pressure_method_c',
    unnest(ARRAY['rho', 'g']),
    unnest(ARRAY[1000.0, 9.80665]),
    'float',
    unnest(ARRAY[false, false]),
    unnest(ARRAY[NULL::numeric, NULL::numeric]),
    unnest(ARRAY[NULL::numeric, NULL::numeric]),
    'adaptive_sql',
    unnest(ARRAY[1.0, 1.0])
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_outlet_pressure';
```

### 修复2：添加 main_pipeline_outlet_pressure_method_b 参数定义

在修复1之后添加：

```sql
-- main_pipeline_outlet_pressure 方法B - 从泵进口压力和扬程推算参数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, param_min, param_max, updated_by, confidence_score
)
SELECT
    NULL, NULL, 'main_pipeline_outlet_pressure', 'main_pipeline_outlet_pressure_method_b',
    unnest(ARRAY['rho', 'g']),
    unnest(ARRAY[1000.0, 9.80665]),
    'float',
    unnest(ARRAY[false, false]),
    unnest(ARRAY[NULL::numeric, NULL::numeric]),
    unnest(ARRAY[NULL::numeric, NULL::numeric]),
    'adaptive_sql',
    unnest(ARRAY[1.0, 1.0])
FROM dim_metric_config mc
WHERE mc.metric_key = 'main_pipeline_outlet_pressure';
```

---

## 📝 总结

### 关键发现

1. **2个方法存在严重问题**：`pump_outlet_pressure_method_c` 和 `main_pipeline_outlet_pressure_method_b` 缺少必需的物理常数参数定义
2. **4个方法参数定义缺失但有默认值**：这些方法使用 `params.get()` 访问参数，即使数据库中没有定义也不会报错
3. **参数加载机制已修复**：之前的 `load_parameters()` 未调用问题已解决

### 风险评估

- **高风险**：2个方法（pump_outlet_pressure_method_c, main_pipeline_outlet_pressure_method_b）
- **中风险**：0个方法
- **低风险**：4个方法（有默认值的可选参数）

### 建议行动

1. **立即修复**：添加2个缺失的必需参数定义
2. **可选优化**：为4个使用可选参数的方法添加数据库配置，便于后续调优
3. **持续监控**：建立参数完整性检查机制，防止未来新增方法时遗漏参数定义

---

## ✅ 修复执行结果

### 修复时间
2025-11-03 15:52:13

### 修复内容
已在 `scripts/sql/adaptive/03_calculation_parameters.sql` 中添加以下参数定义：

1. **pump_outlet_pressure_method_c** (L95-111)
   - 参数：rho=1000.0, g=9.80665
   - 状态：✅ 已添加并验证

2. **main_pipeline_outlet_pressure_method_b** (L113-129)
   - 参数：rho=1000.0, g=9.80665
   - 状态：✅ 已添加并验证

### 验证结果
```sql
-- 数据库查询结果
SELECT method_id, param_name, param_value, updated_by
FROM calculation_parameters
WHERE method_id IN (
    'pump_outlet_pressure_method_c',
    'main_pipeline_outlet_pressure_method_b'
);

-- 结果：4条记录，参数正确生成
-- main_pipeline_outlet_pressure_method_b: g=9.80665, rho=1000.0
-- pump_outlet_pressure_method_c: g=9.80665, rho=1000.0
```

### 影响范围
- ✅ SQL 脚本修改：1个文件
- ✅ 数据库参数：新增4条记录
- ✅ 受影响方法：2个计算方法
- ✅ 风险等级：低（仅添加参数定义，不修改现有逻辑）

---

## 📈 后续建议

### 1. 可选参数优化（低优先级）
以下方法使用可选参数（有默认值），建议添加数据库配置以便后续调优：

- `pump_flow_rate_method_d` (p_thr)
- `pump_flow_rate_method_e` (f_thr)
- `pump_flow_rate_method_f` (a0, a1, a2, a3)
- `pump_cumulative_flow_method_a` (initial_value, time_interval)

### 2. 参数完整性检查机制
建议添加自动化检查脚本，定期验证：
- 所有使用 `params['key']` 的方法都有对应的数据库参数定义
- 参数名称与代码中使用的名称一致
- 参数值在合理范围内

### 3. 文档更新
建议更新以下文档：
- 计算方法清单（添加参数说明）
- 参数管理指南（说明如何添加新参数）
- 故障排查指南（参数缺失问题的诊断方法）

---

**报告结束**

