# main_pipeline_inlet_pressure 实施计划

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5

---

## 📋 实施概述

### 目标

实现 `main_pipeline_inlet_pressure`（总管进口压力）指标的完整计算流水线，包括：
- 2种计算方法（静压法、等效系数法）
- 完整的数据加载、过滤、计算、验证流程
- 集成到调度器和数据写入系统

### 时间规划

- **总工期**：1周（5个工作日）
- **开始时间**：第2周周一
- **结束时间**：第2周周五

### 人员配置

- **开发人员**：1人
- **测试人员**：1人（兼职）
- **审核人员**：1人（技术负责人）

---

## 📅 分阶段实施计划

### 阶段1：文档和数据库准备（第1天）

#### 任务1.1：文档创建
- [ ] 创建目录 `缺失指标计算改造/main_pipeline_inlet_pressure/`
- [ ] 创建 `01-main_pipeline_inlet_pressure详细设计.md` ✅
- [ ] 创建 `02-main_pipeline_inlet_pressure实施计划.md` ✅
- [ ] 创建 `03-main_pipeline_inlet_pressure重构任务跟踪.md`
- [ ] 创建 `04-main_pipeline_inlet_pressure重构完整检查清单.md`
- [ ] 创建 `05-任务完成追踪表.md`

**预计时间**：2小时

#### 任务1.2：数据库参数配置
- [ ] 验证calculation_parameters表已填充（main_pipeline_inlet_pressure相关参数）
- [ ] 验证参数查询成功（method_b, PIN_COEF_V1, validation）

**预计时间**：0.5小时

#### 任务1.3：依赖关系验证
- [ ] 确认 `pool_liquid_level` 数据存在（metric_id=5, device_id=8）
- [ ] 确认 `mv_device_running_1s` 表可用
- [ ] 确认无循环依赖（main_pipeline_inlet_pressure不被其他指标依赖）

**预计时间**：0.5小时

**阶段1总计**：3小时

---

### 阶段2：代码实现（第2-3天）

#### 任务2.1：创建目录结构
- [ ] 创建 `app/services/calculation/metrics/main_pipeline_inlet_pressure/`
- [ ] 创建 `app/services/calculation/metrics/main_pipeline_inlet_pressure/methods/`

**预计时间**：0.5小时

#### 任务2.2：实现DataLoader
- [ ] 创建 `data_loader.py`
- [ ] 实现 `load_data()` 方法
- [ ] 实现SQL查询（pool_liquid_level + running状态）
- [ ] 注意：pool_liquid_level从device_id=8获取
- [ ] 实现数据透视（长表→宽表）
- [ ] 添加日志输出

**预计时间**：2.5小时

#### 任务2.3：实现DataFilter
- [ ] 创建 `data_filter.py`
- [ ] 实现 `filter_data()` 方法
- [ ] 使用 `mv_device_running_1s.running` 字段过滤
- [ ] 禁止硬编码阈值
- [ ] 添加日志输出

**预计时间**：2小时

#### 任务2.4：实现MethodSelector
- [ ] 创建 `method_selector.py`
- [ ] 定义方法配置（METHODS列表，2个方法）
- [ ] 实现 `select_method()` 方法
- [ ] 实现依赖检查逻辑
- [ ] 实现条件检查逻辑（calibration_quality）
- [ ] 添加详细日志输出

**预计时间**：2.5小时

#### 任务2.5：实现Calculator
- [ ] 创建 `calculator.py`
- [ ] 实现 `calculate()` 方法（方法分发）
- [ ] 实现 `_method_b()` - 静压法
- [ ] 实现 `_PIN_COEF_V1()` - 等效系数法
- [ ] 添加日志输出

**预计时间**：3小时

#### 任务2.6：实现Validator
- [ ] 创建 `validator.py`
- [ ] 实现 `validate()` 方法
- [ ] 实现范围检查（0.05 - 1.0 MPa）
- [ ] 实现物理约束检查（P_in ≈ P_atm + ρ×g×h/1e6, ±20%）
- [ ] 实现异常值检查（相邻时刻变化 < 0.05 MPa/s）
- [ ] 实现质量标记
- [ ] 添加日志输出

**预计时间**：3小时

#### 任务2.7：实现Pipeline
- [ ] 创建 `pipeline.py`
- [ ] 实现 `MainPipelineInletPressurePipeline` 类
- [ ] 实现 `run()` 方法（编排所有组件）
- [ ] 实现错误处理
- [ ] 添加性能监控
- [ ] 添加日志输出

**预计时间**：2.5小时

#### 任务2.8：创建__init__.py
- [ ] 创建 `__init__.py`
- [ ] 导出 `MainPipelineInletPressurePipeline`

**预计时间**：0.5小时

**阶段2总计**：16.5小时（约2天）

---

### 阶段3：集成和测试（第4天）

#### 任务3.1：调度器集成
- [ ] 更新 `app/services/calculation/shared/scheduler.py`
- [ ] 在 `METRIC_ORDER` 中添加 `main_pipeline_inlet_pressure`（第2位）
- [ ] 验证计算顺序正确（在pump_flow_rate之前）

**预计时间**：1小时

#### 任务3.2：参数管理集成
- [ ] 验证 `ParameterManager` 可正确加载参数
- [ ] 测试method_b参数（P_atm, rho, g）
- [ ] 测试PIN_COEF_V1参数（b0, b1, b2, b3）
- [ ] 测试参数缓存

**预计时间**：1小时

#### 任务3.3：数据写入集成
- [ ] 验证 `DataWriter` 可正确写入结果
- [ ] 确认 `metric_id=61`
- [ ] 确认 `device_id=7`（总管设备）
- [ ] 测试批量写入性能

**预计时间**：1小时

#### 任务3.4：单元测试
- [ ] 测试 DataLoader（模拟数据，注意device_id=8）
- [ ] 测试 DataFilter（运行状态过滤）
- [ ] 测试 MethodSelector（方法选择逻辑）
- [ ] 测试 Calculator（2种方法）
- [ ] 测试 Validator（验证规则）

**预计时间**：3小时

#### 任务3.5：集成测试
- [ ] 测试完整流水线（端到端）
- [ ] 测试设备7（总管设备）
- [ ] 测试时间范围：2025-10-22 08:00:00 到 2025-10-23 07:19:37
- [ ] 验证计算结果写入数据库

**预计时间**：2小时

**阶段3总计**：8小时

---

### 阶段4：数据质量验证和优化（第5天）

#### 任务4.1：数据质量分析
- [ ] 查询计算结果数量
- [ ] 统计各方法使用比例
- [ ] 统计质量标记分布
- [ ] 分析异常数据原因

**预计时间**：2小时

#### 任务4.2：性能优化
- [ ] 分析计算耗时
- [ ] 优化SQL查询
- [ ] 优化批量写入
- [ ] 调整自适应分片参数

**预计时间**：2小时

#### 任务4.3：文档完善
- [ ] 更新详细设计文档
- [ ] 更新任务跟踪文档
- [ ] 完成检查清单
- [ ] 生成数据质量报告

**预计时间**：2小时

#### 任务4.4：代码审查
- [ ] 代码规范检查（pylint）
- [ ] 代码格式化（black, isort）
- [ ] 文档字符串检查
- [ ] 日志输出检查

**预计时间**：2小时

**阶段4总计**：8小时

---

## 📊 工作量统计

| 阶段 | 任务数 | 预计时间 | 占比 |
|------|--------|---------|------|
| 阶段1：文档和数据库准备 | 3 | 3小时 | 8.4% |
| 阶段2：代码实现 | 8 | 16.5小时 | 46.5% |
| 阶段3：集成和测试 | 5 | 8小时 | 22.5% |
| 阶段4：数据质量验证和优化 | 4 | 8小时 | 22.5% |
| **总计** | **20** | **35.5小时** | **100%** |

---

## ⚠️ 风险评估

### 风险1：pool_liquid_level数据来源不同

**影响**：中  
**概率**：低  
**描述**：pool_liquid_level从device_id=8获取，而main_pipeline_inlet_pressure计算结果写入device_id=7  
**缓解措施**：
- 在DataLoader中明确指定device_id=8查询pool_liquid_level
- 在Pipeline中明确指定device_id=7写入结果
- 添加单元测试验证数据来源正确

### 风险2：calibration_quality参数缺失

**影响**：低  
**概率**：中  
**描述**：PIN_COEF_V1方法需要calibration_quality参数，可能未配置  
**缓解措施**：
- 在MethodSelector中提供默认值（'low'）
- 记录警告日志
- 使用method_b作为默认方法

### 风险3：计算结果与预期不符

**影响**：中  
**概率**：中  
**缓解措施**：
- 完善Validator验证规则
- 添加物理约束检查
- 与现场实测数据对比

---

## ✅ 验收标准

1. ✅ 所有文档完整且符合模板要求
2. ✅ 代码实现遵循架构规范，无硬编码
3. ✅ 所有参数从数据库加载
4. ✅ 集成到调度器、参数管理、数据写入
5. ✅ METRIC_ORDER配置正确
6. ✅ 单元测试通过率100%
7. ✅ 集成测试通过率100%
8. ✅ 数据质量报告完成
9. ✅ 代码审查通过
10. ✅ pool_liquid_level数据来源正确（device_id=8）
11. ✅ 计算结果写入正确（device_id=7）

---

**文档结束**

