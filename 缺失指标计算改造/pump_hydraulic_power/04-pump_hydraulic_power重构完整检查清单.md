# pump_hydraulic_power 重构完整检查清单

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **指标ID**: 67  
> **指标名称**: pump_hydraulic_power（泵水力功率）  
> **协议**: RIPER-5 计划模式

---

## 第一阶段：数据库准备（10项）

### 参数配置验证（5项）

- [ ] 1. calculation_parameters表存在rho参数（pump_hydraulic_power, method_a）
- [ ] 2. calculation_parameters表存在g参数（pump_hydraulic_power, method_a）
- [ ] 3. calculation_parameters表存在validation参数（min_power, max_power, max_change_rate）
- [ ] 4. 所有参数值合理（rho=1000.0, g=9.81）
- [ ] 5. 参数单位正确（rho: kg/m³, g: m/s²）

### 依赖数据验证（5项）

- [ ] 6. pump_flow_rate数据存在（metric_id=18, device_id=1-6）
- [ ] 7. pump_head数据存在（metric_id=17, device_id=1-6）
- [ ] 8. mv_device_running_1s表可用
- [ ] 9. 依赖指标数据覆盖全部时间范围
- [ ] 10. 无循环依赖

---

## 第二阶段：代码实现（80项）

### 目录结构（5项）

- [ ] 11. 创建 `app/services/calculation/metrics/pump_hydraulic_power/`
- [ ] 12. 创建 `app/services/calculation/metrics/pump_hydraulic_power/methods/`
- [ ] 13. 创建 `__init__.py`
- [ ] 14. 导出 `PumpHydraulicPowerPipeline`
- [ ] 15. 目录结构符合规范

### DataLoader实现（15项）

- [ ] 16. 创建 `data_loader.py`
- [ ] 17. 定义 `PumpHydraulicPowerDataLoader` 类
- [ ] 18. 实现 `__init__()` 方法
- [ ] 19. 实现 `load()` 方法
- [ ] 20. SQL查询pump_flow_rate（metric_id=18）
- [ ] 21. SQL查询pump_head（metric_id=17）
- [ ] 22. SQL查询running状态（mv_device_running_1s）
- [ ] 23. LEFT JOIN确保数据完整性
- [ ] 24. 设备范围正确（device_id=1-6）
- [ ] 25. 时间范围参数化
- [ ] 26. 数据透视（长表→宽表）
- [ ] 27. 返回DataFrame格式正确
- [ ] 28. 日志输出完整（加载行数、设备数、时间范围）
- [ ] 29. 异常处理完善
- [ ] 30. 文档字符串完整

### DataFilter实现（10项）

- [ ] 31. 创建 `data_filter.py`
- [ ] 32. 定义 `PumpHydraulicPowerDataFilter` 类
- [ ] 33. 实现 `__init__()` 方法
- [ ] 34. 实现 `filter()` 方法
- [ ] 35. 使用 `mv_device_running_1s.running` 字段
- [ ] 36. 禁止硬编码阈值
- [ ] 37. 日志输出完整（原始行数、过滤后行数、过滤比例）
- [ ] 38. 异常处理完善
- [ ] 39. 文档字符串完整
- [ ] 40. 类型注解正确

### MethodSelector实现（10项）

- [ ] 41. 创建 `method_selector.py`
- [ ] 42. 定义 `PumpHydraulicPowerMethodSelector` 类
- [ ] 43. 实现 `__init__()` 方法
- [ ] 44. 实现 `select_method()` 方法
- [ ] 45. 定义方法配置（method_a）
- [ ] 46. 检查pump_flow_rate列存在
- [ ] 47. 检查pump_head列存在
- [ ] 48. 检查rho, g参数存在
- [ ] 49. 日志输出完整（方法选择过程、失败原因）
- [ ] 50. 返回method_a

### Calculator实现（15项）

- [ ] 51. 创建 `calculator.py`
- [ ] 52. 定义 `PumpHydraulicPowerCalculator` 类
- [ ] 53. 实现 `__init__()` 方法
- [ ] 54. 实现 `calculate()` 方法
- [ ] 55. 实现 `_method_a()` 方法
- [ ] 56. 公式正确：P_h = ρ×g×Q×H/1000
- [ ] 57. 从calc_params获取rho
- [ ] 58. 从calc_params获取g
- [ ] 59. 单位转换正确（Q: m³/h, H: m, P_h: kW）
- [ ] 60. 处理缺失参数（使用默认值）
- [ ] 61. 添加method列
- [ ] 62. 日志输出完整（计算行数、方法、参数）
- [ ] 63. 异常处理完善
- [ ] 64. 文档字符串完整
- [ ] 65. 类型注解正确

### Validator实现（15项）

- [ ] 66. 创建 `validator.py`
- [ ] 67. 定义 `PumpHydraulicPowerValidator` 类
- [ ] 68. 实现 `__init__()` 方法
- [ ] 69. 实现 `validate()` 方法
- [ ] 70. 实现范围检查（0 <= P_h <= 400 kW）
- [ ] 71. 实现物理约束检查（P_h < P_shaft，可选）
- [ ] 72. 实现异常值检查（相邻时刻变化 < 40 kW/s）
- [ ] 73. 添加valid_range列
- [ ] 74. 添加valid_physics列
- [ ] 75. 添加valid_outlier列
- [ ] 76. 添加quality列（valid/out_of_range/physics_violation/outlier）
- [ ] 77. 日志输出完整（验证统计、异常数量、质量分布）
- [ ] 78. 异常处理完善
- [ ] 79. 文档字符串完整
- [ ] 80. 类型注解正确

### Pipeline实现（10项）

- [ ] 81. 创建 `pipeline.py`
- [ ] 82. 定义 `PumpHydraulicPowerPipeline` 类
- [ ] 83. 实现 `__init__()` 方法
- [ ] 84. 实现 `run()` 方法
- [ ] 85. 编排所有组件（DataLoader → DataFilter → MethodSelector → Calculator → Validator）
- [ ] 86. 传递参数正确
- [ ] 87. 日志输出完整（每个步骤的输入输出）
- [ ] 88. 异常处理完善
- [ ] 89. 文档字符串完整
- [ ] 90. 类型注解正确

---

## 第三阶段：集成测试（35项）

### 调度器集成（5项）

- [ ] 91. 更新 `METRIC_ORDER`，添加 `pump_hydraulic_power`（第8位）
- [ ] 92. 验证计算顺序正确（在pump_flow_rate和pump_head之后）
- [ ] 93. 验证无循环依赖
- [ ] 94. 测试调度器运行
- [ ] 95. 日志输出正确

### 参数管理集成（5项）

- [ ] 96. ParameterManager加载calculation_parameters（rho, g）
- [ ] 97. 参数缓存正常工作
- [ ] 98. 参数合并正确（全局→泵站→设备）
- [ ] 99. 测试参数加载
- [ ] 100. 日志输出正确

### 数据写入集成（5项）

- [ ] 101. DataWriter写入结果（metric_id=67, device_id=1-6）
- [ ] 102. 批量写入性能正常（>1000条/秒）
- [ ] 103. 数据完整性验证
- [ ] 104. 测试数据写入
- [ ] 105. 日志输出正确

### 单元测试（10项）

- [ ] 106. 测试DataLoader（正常情况）
- [ ] 107. 测试DataLoader（异常情况）
- [ ] 108. 测试DataFilter（正常情况）
- [ ] 109. 测试DataFilter（异常情况）
- [ ] 110. 测试MethodSelector（正常情况）
- [ ] 111. 测试Calculator（method_a）
- [ ] 112. 测试Calculator（单位转换）
- [ ] 113. 测试Validator（范围检查）
- [ ] 114. 测试Validator（异常值检查）
- [ ] 115. 测试Pipeline（完整流程）

### 集成测试（10项）

- [ ] 116. 测试设备1（全部时间范围）
- [ ] 117. 测试设备2（全部时间范围）
- [ ] 118. 测试设备3（全部时间范围）
- [ ] 119. 测试设备4（全部时间范围）
- [ ] 120. 测试设备5（全部时间范围）
- [ ] 121. 测试设备6（全部时间范围）
- [ ] 122. 验证计算结果数量
- [ ] 123. 验证质量标记分布
- [ ] 124. 验证公式正确性（与已知数据对比）
- [ ] 125. 验证性能指标（计算耗时<30秒）

---

## 第四阶段：质量验证（25项）

### 数据质量分析（10项）

- [ ] 126. 查询计算结果总数
- [ ] 127. 统计各设备结果数量
- [ ] 128. 统计质量标记分布（valid, out_of_range, physics_violation, outlier）
- [ ] 129. 分析out_of_range原因
- [ ] 130. 分析physics_violation原因
- [ ] 131. 分析outlier原因
- [ ] 132. 验证覆盖率（应接近100%）
- [ ] 133. 验证有效率（应>95%）
- [ ] 134. 生成数据质量报告
- [ ] 135. 记录异常数据示例

### 性能优化（5项）

- [ ] 136. 分析计算耗时（各组件耗时）
- [ ] 137. 优化SQL查询（索引、分区）
- [ ] 138. 优化批量写入（批次大小）
- [ ] 139. 验证性能提升
- [ ] 140. 记录性能指标到calculation_performance_metrics表

### 文档完善（5项）

- [ ] 141. 更新 `01-pump_hydraulic_power详细设计.md`（补充实际实现细节）
- [ ] 142. 更新 `03-pump_hydraulic_power重构任务跟踪.md`（更新任务状态）
- [ ] 143. 完成 `05-任务完成追踪表.md`（记录完成时间）
- [ ] 144. 生成数据质量报告（独立文档）
- [ ] 145. 生成性能测试报告（独立文档）

### 代码审查（5项）

- [ ] 146. 运行pylint检查（无错误, 评分>9.0）
- [ ] 147. 运行black格式化（所有文件）
- [ ] 148. 运行isort排序导入语句（所有文件）
- [ ] 149. 检查文档字符串完整性（所有类和方法）
- [ ] 150. 检查日志输出完整性（所有关键步骤）

---

## 📊 检查清单统计

| 阶段 | 检查项数 | 占比 |
|------|---------|------|
| 第一阶段：数据库准备 | 10 | 6.7% |
| 第二阶段：代码实现 | 80 | 53.3% |
| 第三阶段：集成测试 | 35 | 23.3% |
| 第四阶段：质量验证 | 25 | 16.7% |
| **总计** | **150** | **100%** |

---

## ✅ 验收标准

**代码质量**：
- [ ] 所有文件符合PEP 8规范
- [ ] pylint评分 > 9.0
- [ ] 无硬编码阈值
- [ ] 所有参数从数据库加载

**测试覆盖**：
- [ ] 单元测试通过率 100%
- [ ] 集成测试通过率 100%
- [ ] 数据质量报告完成

**性能要求**：
- [ ] 计算耗时 < 30秒（全部时间范围）
- [ ] 批量写入速度 > 1000条/秒
- [ ] 内存使用 < 1GB

**文档完整性**：
- [ ] 所有5个文档完成
- [ ] 所有检查项完成
- [ ] 数据质量报告完成
- [ ] 性能测试报告完成

**数据正确性**：
- [ ] 公式单位转换正确
- [ ] 覆盖率接近100%
- [ ] 有效率>95%

---

**文档结束**

