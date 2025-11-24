# pump_shaft_power 实施计划

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5

---

## 📋 实施概述

### 目标

实现 `pump_shaft_power`（泵轴功率）指标的完整计算流水线，包括：
- 1种计算方法（电机效率法）
- 完整的数据加载、过滤、计算、验证流程
- 集成到调度器和数据写入系统

### 时间规划

- **总工期**：1周（5个工作日）
- **开始时间**：第3周周一
- **结束时间**：第3周周五

### 人员配置

- **开发人员**：1人
- **测试人员**：1人（兼职）
- **审核人员**：1人（技术负责人）

---

## 📅 分阶段实施计划

### 阶段1：文档和数据库准备（第1天）

#### 任务1.1：文档创建（2小时）
- [ ] 创建5个文档（详细设计、实施计划、任务跟踪、检查清单、完成追踪）

#### 任务1.2：数据库参数配置（1小时）
- [ ] 验证device_rated_params表已填充（设备1-6，eta_motor, eta_vfd）
- [ ] 验证calculation_parameters表已填充（validation参数）

#### 任务1.3：依赖关系验证（0.5小时）
- [ ] 确认pump_active_power数据存在（metric_id=2, device_id=1-6）
- [ ] 确认mv_device_running_1s表可用
- [ ] 确认无循环依赖

**阶段1总计**：3.5小时

---

### 阶段2：代码实现（第2-3天）

#### 任务2.1：创建目录结构（0.5小时）
- [ ] 创建 `app/services/calculation/metrics/pump_shaft_power/`
- [ ] 创建 `app/services/calculation/metrics/pump_shaft_power/methods/`

#### 任务2.2：实现DataLoader（2.5小时）
- [ ] 创建 `data_loader.py`
- [ ] 实现SQL查询（pump_active_power + running状态）
- [ ] 实现数据透视（长表→宽表）

#### 任务2.3：实现DataFilter（2小时）
- [ ] 创建 `data_filter.py`
- [ ] 使用 `mv_device_running_1s.running` 字段过滤
- [ ] 禁止硬编码阈值

#### 任务2.4：实现MethodSelector（2小时）
- [ ] 创建 `method_selector.py`
- [ ] 定义方法配置（1个方法：method_a）
- [ ] 实现方法选择逻辑（检查eta_motor, eta_vfd参数）

#### 任务2.5：实现Calculator（2.5小时）
- [ ] 创建 `calculator.py`
- [ ] 实现 `_method_a()` - 电机效率法
- [ ] 公式：P_shaft = P_active / (η_motor × η_vfd)
- [ ] 处理每个设备的不同参数

#### 任务2.6：实现Validator（2.5小时）
- [ ] 创建 `validator.py`
- [ ] 实现范围检查（0 <= P_shaft <= 500 kW）
- [ ] 实现效率检查（P_shaft > P_active）
- [ ] 实现异常值检查（相邻时刻变化 < 50 kW/s）

#### 任务2.7：实现Pipeline（2.5小时）
- [ ] 创建 `pipeline.py`
- [ ] 实现 `PumpShaftPowerPipeline` 类
- [ ] 编排所有组件

#### 任务2.8：创建__init__.py（0.5小时）
- [ ] 创建 `__init__.py`
- [ ] 导出 `PumpShaftPowerPipeline`

**阶段2总计**：15小时（约2天）

---

### 阶段3：集成和测试（第4天）

#### 任务3.1：调度器集成（1小时）
- [ ] 更新 `METRIC_ORDER`，添加 `pump_shaft_power`（第3位）

#### 任务3.2：参数管理集成（1小时）
- [ ] 测试ParameterManager加载device_rated_params（eta_motor, eta_vfd）

#### 任务3.3：数据写入集成（1小时）
- [ ] 验证DataWriter写入结果（metric_id=66, device_id=1-6）

#### 任务3.4：单元测试（3小时）
- [ ] 测试所有组件（DataLoader, DataFilter, MethodSelector, Calculator, Validator）

#### 任务3.5：集成测试（2小时）
- [ ] 测试完整流水线（设备1-6，全部时间范围）

**阶段3总计**：8小时

---

### 阶段4：数据质量验证和优化（第5天）

#### 任务4.1：数据质量分析（2小时）
- [ ] 查询计算结果数量
- [ ] 统计质量标记分布
- [ ] 分析异常数据原因

#### 任务4.2：性能优化（2小时）
- [ ] 分析计算耗时
- [ ] 优化SQL查询和批量写入

#### 任务4.3：文档完善（2小时）
- [ ] 更新所有文档
- [ ] 生成数据质量报告

#### 任务4.4：代码审查（2小时）
- [ ] 运行pylint检查（评分>9.0）
- [ ] 运行black格式化

**阶段4总计**：8小时

---

## 📊 工作量统计

| 阶段 | 任务数 | 预计时间 | 占比 |
|------|--------|---------|------|
| 阶段1：文档和数据库准备 | 3 | 3.5小时 | 10.1% |
| 阶段2：代码实现 | 8 | 15小时 | 43.5% |
| 阶段3：集成和测试 | 5 | 8小时 | 23.2% |
| 阶段4：质量验证和优化 | 4 | 8小时 | 23.2% |
| **总计** | **20** | **34.5小时** | **100%** |

---

## ⚠️ 风险评估

### 风险1：device_rated_params参数缺失

**影响**：高  
**概率**：中  
**缓解措施**：
- 在ParameterManager中提供默认值（eta_motor=0.92, eta_vfd=0.97）
- 记录警告日志
- 确保device_rated_params表已填充

### 风险2：效率参数不准确

**影响**：中  
**概率**：中  
**缓解措施**：
- 与现场实测数据对比
- 完善Validator验证规则
- 添加效率检查（P_shaft > P_active）

---

## ✅ 验收标准

1. ✅ 所有文档完整且符合模板要求
2. ✅ 代码实现遵循架构规范，无硬编码
3. ✅ 所有参数从数据库加载（device_rated_params）
4. ✅ 集成到调度器、参数管理、数据写入
5. ✅ METRIC_ORDER配置正确
6. ✅ 单元测试通过率100%
7. ✅ 集成测试通过率100%
8. ✅ 数据质量报告完成
9. ✅ 代码审查通过
10. ✅ 效率检查通过（P_shaft > P_active）

---

**文档结束**

