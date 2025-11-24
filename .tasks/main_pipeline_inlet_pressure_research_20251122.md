# main_pipeline_inlet_pressure 研究任务

> **任务ID**: main_pipeline_inlet_pressure_research_20251122  
> **创建时间**: 2025-11-22  
> **协议**: RIPER-5 研究模式  
> **状态**: 已完成

---

## 📋 任务概述

**目标**: 研究 main_pipeline_inlet_pressure 指标的开发状态，识别已完成和待完成的功能模块

**背景**: 
- 已完成指标: pump_flow_rate, pump_inlet_pressure, pump_head, pump_efficiency
- 当前指标: main_pipeline_inlet_pressure（总管进口压力）
- 参考模板: pump_flow_rate 的实际实现

---

## 📊 研究发现

### 1. 已完成的功能模块

#### 1.1 文档完整性 ✅
- [x] 01-main_pipeline_inlet_pressure详细设计.md（531行）
- [x] 02-main_pipeline_inlet_pressure实施计划.md（288行）
- [x] 03-main_pipeline_inlet_pressure重构任务跟踪.md（278行）
- [x] 04-main_pipeline_inlet_pressure重构完整检查清单.md（300行）
- [x] 05-任务完成追踪表.md（305行）

**状态**: 所有5个文档已创建，框架完整

#### 1.2 代码实现完整性 ✅

**目录结构**:
```
app/services/calculation/metrics/main_pipeline_inlet_pressure/
├── __init__.py ✅
├── data_loader.py ✅
├── data_filter.py ✅
├── method_selector.py ✅
├── calculator.py ✅
├── validator.py ✅
├── pipeline.py ✅
└── methods/
    ├── __init__.py ✅
    ├── method_b.py ✅
    └── pin_coef_v1.py ✅
```

**所有核心模块已实现**:
- ✅ DataLoader: 从数据库加载 pool_liquid_level（device_id=8）
- ✅ DataFilter: 使用 running 字段过滤（处理NULL值）
- ✅ MethodSelector: 2个方法配置（PIN_COEF_V1, method_b）
- ✅ Calculator: 方法分发和计算逻辑
- ✅ Validator: 4种验证规则（范围、物理约束、异常值、NaN/Inf）
- ✅ Pipeline: 完整流水线编排
- ✅ Methods: method_b（静压法）和 PIN_COEF_V1（多项式拟合法）

#### 1.3 数据库准备 ✅
- ✅ calculation_parameters 表已填充（11条参数记录）
- ✅ pool_liquid_level 数据存在（metric_id=18, device_id=8, 83609条记录）
- ✅ mv_device_running_1s 表可用

---

### 2. 待完成的功能模块

#### 2.1 调度器集成 ❌
**文件**: `app/services/calculation/shared/scheduler.py`

**待执行**:
- [ ] 在 METRIC_ORDER 列表中添加 "main_pipeline_inlet_pressure"
- [ ] 确认计算顺序正确（应在第2位，仅依赖原始测量数据）

#### 2.2 测试验证 ❌
**待执行**:
- [ ] 单元测试（DataLoader, DataFilter, MethodSelector, Calculator, Validator）
- [ ] 集成测试（端到端流水线测试）
- [ ] 数据质量分析（计算结果验证）

#### 2.3 性能优化 ❌
**待执行**:
- [ ] 性能测试（计算耗时分析）
- [ ] SQL查询优化
- [ ] 批量写入优化

---

## 🔍 关键技术细节

### 数据来源特殊性
- **pool_liquid_level**: 从 device_id=8 获取（metric_id=18）
- **running状态**: 从 device_id=7 获取（总管设备）
- **计算结果**: 写入 device_id=7（metric_id=61）

### 运行状态处理
- 总管设备（device_id=7）没有 running 状态（NULL值）
- DataFilter 处理: `(data['running'] == 1) | (data['running'].isna())`
- 保留 running=1 或 running=NULL 的数据

### 计算方法
1. **method_b（静压法）**: P_in = P_atm + ρ×g×h/1e6
2. **PIN_COEF_V1（多项式拟合法）**: P_in = b0 + b1×h + b2×h² + b3×h³

---

## 📝 需要澄清的问题

### 问题1: 调度器集成位置
**问题**: main_pipeline_inlet_pressure 应该在 METRIC_ORDER 的哪个位置？

**分析**:
- 依赖关系: 仅依赖 pool_liquid_level（原始测量数据）
- 建议位置: 第2位（第一层计算指标）
- 参考: pump_inlet_pressure 也在第一层

**需要确认**: 用户是否同意此位置？

### 问题2: 测试策略
**问题**: 是否需要先运行测试再集成到调度器？

**建议**: 
1. 先运行单元测试验证各模块正确性
2. 再运行集成测试验证端到端流程
3. 最后集成到调度器

**需要确认**: 用户是否同意此顺序？

---

## 📈 完成度评估

| 阶段 | 完成度 | 说明 |
|------|--------|------|
| 文档准备 | 100% | 所有5个文档已创建 |
| 代码实现 | 100% | 所有10个文件已实现 |
| 数据库准备 | 100% | 参数和数据已就绪 |
| 调度器集成 | 0% | 待执行 |
| 测试验证 | 0% | 待执行 |
| 性能优化 | 0% | 待执行 |
| **总体** | **60%** | 核心功能已完成，待集成和测试 |

---

**研究完成时间**: 2025-11-22

