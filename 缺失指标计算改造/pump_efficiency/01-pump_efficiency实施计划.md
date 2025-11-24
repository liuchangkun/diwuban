# pump_efficiency 实施计划

> **创建时间**: 2025-11-17  
> **状态**: 计划阶段  
> **方法**: 方案1 - 功率-流量-扬程法

---

## 📋 实施概述

### 目标
实现 pump_efficiency（水泵效率）计算，使用新架构（与 pump_flow_rate、pump_inlet_pressure、pump_head 相同的模块化架构）。

### 计算公式
```
η = (ρ × g × Q × H) / (P_e × 1000)
```

**输入**：
- `pump_flow_rate`: Q (m³/h) - 泵瞬时流量
- `pump_head`: H (m) - 泵扬程
- `pump_active_power`: P_e (kW) - 泵有功功率

**输出**：
- `pump_efficiency`: η (0-1) - 泵效率

**物理常数**：
- `ρ` = 1000.0 kg/m³ - 水密度
- `g` = 9.81 m/s² - 重力加速度

### 核心约束
- ✅ 使用新架构（模块化设计）
- ❌ 禁止使用旧架构代码
- ❌ 禁止修改禁用表（calculation_method_registry, metric_calculation_order, metric_capability_policy）
- ✅ 只能修改 calculation_parameters 表

---

## 📊 实施阶段

### 阶段1：规划和设计 ✅
- [x] 创建实施计划文档
- [x] 确定计算公式和依赖关系
- [x] 设计目录结构
- [x] 设计测试验证方案

### 阶段2：创建目录结构 ⏳
- [ ] 创建 `app/services/calculation/metrics/pump_efficiency/` 目录
- [ ] 创建核心文件（8个文件）
- [ ] 创建 methods 子目录

### 阶段3：实现计算逻辑 ⏳
- [ ] 实现 DataLoader（加载依赖数据）
- [ ] 实现 DataFilter（过滤无效数据）
- [ ] 实现 MethodSelector（方法选择器）
- [ ] 实现 Calculator（计算方法）
- [ ] 实现 Validator（结果验证）
- [ ] 实现 DataWriter（数据写入）
- [ ] 实现 Pipeline（流程编排）

### 阶段4：配置参数 ⏳
- [ ] 在 calculation_parameters 表中配置物理常数
- [ ] 配置验证阈值

### 阶段5：测试验证 ⏳
- [ ] 创建测试脚本
- [ ] 运行测试（2025-10-22 16:00 ~ 2025-10-23 15:00，设备 1-6）
- [ ] 验证数据加载完整性
- [ ] 验证计算结果合理性
- [ ] 验证数据库写入成功
- [ ] 生成质量分析报告

### 阶段6：文档和总结 ⏳
- [ ] 更新实施计划进度
- [ ] 生成实施报告
- [ ] 生成数据质量分析报告

---

## 📁 需要创建的文件清单

### 核心模块文件（8个）
1. `app/services/calculation/metrics/pump_efficiency/__init__.py`
2. `app/services/calculation/metrics/pump_efficiency/data_loader.py`
3. `app/services/calculation/metrics/pump_efficiency/data_filter.py`
4. `app/services/calculation/metrics/pump_efficiency/method_selector.py`
5. `app/services/calculation/metrics/pump_efficiency/calculator.py`
6. `app/services/calculation/metrics/pump_efficiency/validator.py`
7. `app/services/calculation/metrics/pump_efficiency/pipeline.py`
8. `app/services/calculation/metrics/pump_efficiency/data_writer.py`

### 计算方法文件（1个）
9. `app/services/calculation/metrics/pump_efficiency/methods/__init__.py`
10. `app/services/calculation/metrics/pump_efficiency/methods/power_flow_head.py`

### 测试脚本（1个）
11. `scripts/python/test_pump_efficiency.py`

### SQL脚本（1个）
12. `scripts/sql/configure_pump_efficiency_parameters.sql`

**总计**: 12个文件

---

## 🔧 详细设计

### 1. DataLoader 设计

**职责**: 加载依赖数据（pump_flow_rate, pump_head, pump_active_power）

**SQL查询**:
```sql
SELECT
    fm.ts_raw,
    fm.device_id,
    mc.metric_key,
    fm.value
FROM fact_measurements fm
JOIN dim_metric_config mc ON mc.id = fm.metric_id
WHERE mc.metric_key IN ('pump_flow_rate', 'pump_head', 'pump_active_power')
  AND fm.device_id = %(device_id)s
  AND fm.ts_raw >= %(start_time)s
  AND fm.ts_raw < %(end_time)s
ORDER BY fm.ts_raw
```

**返回数据结构**:
```python
DataFrame with columns:
- ts_raw: 时间戳
- pump_flow_rate: 泵瞬时流量 (m³/h)
- pump_head: 泵扬程 (m)
- pump_active_power: 泵有功功率 (kW)
```

### 2. DataFilter 设计

**过滤规则**:
1. 移除 NaN/Inf 值
2. 移除负值（流量、扬程、功率不应为负）
3. 移除功率为0的数据（避免除零错误）
4. 移除异常值（超出物理范围）

### 3. MethodSelector 设计

**方法配置**:
```python
METHODS = [
    {
        'id': 'power_flow_head',
        'name': '功率-流量-扬程法',
        'priority': 100,
        'dependencies': ['pump_flow_rate', 'pump_head', 'pump_active_power'],
        'conditions': {}  # 无特殊条件
    }
]
```

### 4. Calculator 设计

**计算公式**:
```python
# 步骤1: 将流量从 m³/h 转换为 m³/s
Q_s = Q / 3600

# 步骤2: 计算水力功率 (W)
P_h = ρ × g × Q_s × H

# 步骤3: 计算效率
η = P_h / (P_e × 1000)

# 步骤4: 裁剪到合理范围
η = clip(η, eta_min, eta_max)
```

### 5. Validator 设计

**验证规则**:
1. 效率范围: 0.3 ≤ η ≤ 0.95
2. 非 NaN/Inf
3. 非负值

---

## 📊 参数配置

### 物理常数（全局级别）
| 参数名 | 值 | 单位 | 说明 |
|--------|-----|------|------|
| rho | 1000.0 | kg/m³ | 水密度 |
| g | 9.81 | m/s² | 重力加速度 |

### 验证阈值（全局级别）
| 参数名 | 值 | 说明 |
|--------|-----|------|
| eta_min | 0.30 | 最小效率阈值 |
| eta_max | 0.95 | 最大效率阈值 |

---

## 🧪 测试验证方案

### 测试范围
- **时间**: 2025-10-22 16:00:00 ~ 2025-10-23 15:00:00（23小时）
- **设备**: 1, 2, 3, 4, 5, 6（6台泵）

### 验证指标
1. **数据加载完整性**: 所有依赖数据是否完整加载
2. **计算结果合理性**: 效率值是否在 0.3-0.95 范围内
3. **数据库写入成功**: 是否成功写入 fact_measurements 表
4. **数据质量**: 有效值比例、平均效率、效率分布

### 预期结果
- 数据加载成功率: 100%
- 计算成功率: > 95%
- 效率范围: 0.3 ~ 0.9
- 平均效率: 0.6 ~ 0.8

---

## 📝 进度跟踪

| 阶段 | 状态 | 完成时间 | 备注 |
|------|------|----------|------|
| 阶段1: 规划和设计 | ✅ 完成 | 2025-11-17 | 实施计划已创建 |
| 阶段2: 创建目录结构 | ⏳ 进行中 | - | - |
| 阶段3: 实现计算逻辑 | ⏳ 待开始 | - | - |
| 阶段4: 配置参数 | ⏳ 待开始 | - | - |
| 阶段5: 测试验证 | ⏳ 待开始 | - | - |
| 阶段6: 文档和总结 | ⏳ 待开始 | - | - |

---

**文档状态**: 实施计划已创建 ✅  
**下一步**: 开始阶段2 - 创建目录结构

