# pump_torque 重构完整检查清单

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **指标ID**: 20  
> **指标名称**: pump_torque（泵扭矩）  
> **协议**: RIPER-5 计划模式

---

## 第一阶段：数据库准备（10项）

### 参数配置验证（5项）

- [ ] 1. calculation_parameters表存在rho参数（pump_torque, method_b）
- [ ] 2. calculation_parameters表存在g参数（pump_torque, method_b）
- [ ] 3. calculation_parameters表存在validation参数（min_torque, max_torque, max_deviation, max_change_rate）
- [ ] 4. 所有参数值合理（rho=1000.0, g=9.81）
- [ ] 5. 参数单位正确（rho: kg/m³, g: m/s²）

### 依赖数据验证（5项）

- [ ] 6. pump_active_power数据存在（metric_id=2, device_id=1-6）
- [ ] 7. pump_speed数据存在（metric_id=19, device_id=1-6）
- [ ] 8. pump_flow_rate数据存在（metric_id=18, device_id=1-6，可选）
- [ ] 9. pump_head数据存在（metric_id=17, device_id=1-6，可选）
- [ ] 10. mv_device_running_1s表可用

---

## 第二阶段：代码实现（90项）

### 目录结构（5项）

- [ ] 11. 创建 `app/services/calculation/metrics/pump_torque/`
- [ ] 12. 创建 `app/services/calculation/metrics/pump_torque/methods/`
- [ ] 13. 创建 `__init__.py`
- [ ] 14. 导出 `PumpTorquePipeline`
- [ ] 15. 目录结构符合规范

### DataLoader实现（15项）

- [ ] 16. 创建 `data_loader.py`
- [ ] 17. 定义 `PumpTorqueDataLoader` 类
- [ ] 18. 实现 `__init__()` 方法
- [ ] 19. 实现 `load()` 方法
- [ ] 20. SQL查询pump_active_power（metric_id=2）
- [ ] 21. SQL查询pump_speed（metric_id=19）
- [ ] 22. SQL查询pump_flow_rate（metric_id=18，可选）
- [ ] 23. SQL查询pump_head（metric_id=17，可选）
- [ ] 24. SQL查询running状态（mv_device_running_1s）
- [ ] 25. LEFT JOIN确保数据完整性
- [ ] 26. 设备范围正确（device_id=1-6）
- [ ] 27. 时间范围参数化
- [ ] 28. 数据透视（长表→宽表）
- [ ] 29. 日志输出完整
- [ ] 30. 异常处理完善

### DataFilter实现（10项）

- [ ] 31. 创建 `data_filter.py`
- [ ] 32. 定义 `PumpTorqueDataFilter` 类
- [ ] 33. 实现 `__init__()` 方法
- [ ] 34. 实现 `filter()` 方法
- [ ] 35. 使用 `mv_device_running_1s.running` 字段
- [ ] 36. 禁止硬编码阈值
- [ ] 37. 日志输出完整
- [ ] 38. 异常处理完善
- [ ] 39. 文档字符串完整
- [ ] 40. 类型注解正确

### MethodSelector实现（10项）

- [ ] 41. 创建 `method_selector.py`
- [ ] 42. 定义 `PumpTorqueMethodSelector` 类
- [ ] 43. 实现 `__init__()` 方法
- [ ] 44. 实现 `select_method()` 方法
- [ ] 45. 定义方法配置（method_a, method_b）
- [ ] 46. 检查pump_active_power, pump_speed列存在（method_a）
- [ ] 47. 检查pump_flow_rate, pump_head, pump_speed列存在（method_b）
- [ ] 48. 优先级选择逻辑正确（method_a > method_b）
- [ ] 49. 日志输出完整
- [ ] 50. 返回正确的方法ID

### Calculator实现（20项）

- [ ] 51. 创建 `calculator.py`
- [ ] 52. 定义 `PumpTorqueCalculator` 类
- [ ] 53. 实现 `__init__()` 方法
- [ ] 54. 实现 `calculate()` 方法
- [ ] 55. 实现 `_method_a()` 方法
- [ ] 56. method_a公式正确：T = 9549.3 × P / n
- [ ] 57. method_a单位转换正确（P: kW, n: rpm, T: N·m）
- [ ] 58. 实现 `_method_b()` 方法
- [ ] 59. method_b公式正确：T = ρ×g×Q×H/(2π×n×60)
- [ ] 60. method_b单位转换正确（Q: m³/h, H: m, n: rpm, T: N·m）
- [ ] 61. 从calc_params获取rho, g
- [ ] 62. 处理缺失参数（使用默认值）
- [ ] 63. 添加method列
- [ ] 64. 处理除零错误（n=0）
- [ ] 65. 日志输出完整
- [ ] 66. 异常处理完善
- [ ] 67. 文档字符串完整
- [ ] 68. 类型注解正确
- [ ] 69. 单元测试覆盖method_a
- [ ] 70. 单元测试覆盖method_b

### Validator实现（20项）

- [ ] 71. 创建 `validator.py`
- [ ] 72. 定义 `PumpTorqueValidator` 类
- [ ] 73. 实现 `__init__()` 方法
- [ ] 74. 实现 `validate()` 方法
- [ ] 75. 实现范围检查（0 <= T <= 10000 N·m）
- [ ] 76. 实现交叉验证（双方法差异<10%）
- [ ] 77. 实现异常值检查（相邻时刻变化<500 N·m/s）
- [ ] 78. 添加valid_range列
- [ ] 79. 添加valid_cross列
- [ ] 80. 添加valid_outlier列
- [ ] 81. 添加quality列（valid/out_of_range/cross_validation_failed/outlier）
- [ ] 82. 处理单方法情况（跳过交叉验证）
- [ ] 83. 处理双方法情况（执行交叉验证）
- [ ] 84. 记录交叉验证统计
- [ ] 85. 日志输出完整
- [ ] 86. 异常处理完善
- [ ] 87. 文档字符串完整
- [ ] 88. 类型注解正确
- [ ] 89. 单元测试覆盖范围检查
- [ ] 90. 单元测试覆盖交叉验证

### Pipeline实现（10项）

- [ ] 91. 创建 `pipeline.py`
- [ ] 92. 定义 `PumpTorquePipeline` 类
- [ ] 93. 实现 `__init__()` 方法
- [ ] 94. 实现 `run()` 方法
- [ ] 95. 编排所有组件
- [ ] 96. 传递参数正确
- [ ] 97. 日志输出完整
- [ ] 98. 异常处理完善
- [ ] 99. 文档字符串完整
- [ ] 100. 类型注解正确

---

## 第三阶段：集成测试（35项）

### 调度器集成（5项）

- [ ] 101. 更新 `METRIC_ORDER`，添加 `pump_torque`（第7位）
- [ ] 102. 验证计算顺序正确（在pump_speed之后）
- [ ] 103. 验证无循环依赖
- [ ] 104. 测试调度器运行
- [ ] 105. 日志输出正确

### 参数管理集成（5项）

- [ ] 106. ParameterManager加载calculation_parameters（rho, g）
- [ ] 107. 参数缓存正常工作
- [ ] 108. 参数合并正确
- [ ] 109. 测试参数加载
- [ ] 110. 日志输出正确

### 数据写入集成（5项）

- [ ] 111. DataWriter写入结果（metric_id=20, device_id=1-6）
- [ ] 112. 批量写入性能正常（>1000条/秒）
- [ ] 113. 数据完整性验证
- [ ] 114. 测试数据写入
- [ ] 115. 日志输出正确

### 单元测试（10项）

- [ ] 116. 测试DataLoader（正常情况）
- [ ] 117. 测试DataLoader（异常情况）
- [ ] 118. 测试DataFilter（正常情况）
- [ ] 119. 测试MethodSelector（method_a优先）
- [ ] 120. 测试MethodSelector（method_b备选）
- [ ] 121. 测试Calculator（method_a）
- [ ] 122. 测试Calculator（method_b）
- [ ] 123. 测试Validator（范围检查）
- [ ] 124. 测试Validator（交叉验证）
- [ ] 125. 测试Pipeline（完整流程）

### 集成测试（10项）

- [ ] 126. 测试设备1（全部时间范围）
- [ ] 127. 测试设备2（全部时间范围）
- [ ] 128. 测试设备3（全部时间范围）
- [ ] 129. 测试设备4（全部时间范围）
- [ ] 130. 测试设备5（全部时间范围）
- [ ] 131. 测试设备6（全部时间范围）
- [ ] 132. 验证计算结果数量
- [ ] 133. 验证质量标记分布
- [ ] 134. 验证交叉验证通过率（>90%）
- [ ] 135. 验证性能指标（计算耗时<30秒）

---

## 第四阶段：质量验证（25项）

### 数据质量分析（10项）

- [ ] 136. 查询计算结果总数
- [ ] 137. 统计各设备结果数量
- [ ] 138. 统计质量标记分布
- [ ] 139. 分析out_of_range原因
- [ ] 140. 分析cross_validation_failed原因
- [ ] 141. 分析outlier原因
- [ ] 142. 验证覆盖率（应接近100%）
- [ ] 143. 验证有效率（应>95%）
- [ ] 144. 生成数据质量报告
- [ ] 145. 记录异常数据示例

### 性能优化（5项）

- [ ] 146. 分析计算耗时
- [ ] 147. 优化SQL查询
- [ ] 148. 优化批量写入
- [ ] 149. 验证性能提升
- [ ] 150. 记录性能指标

### 文档完善（5项）

- [ ] 151. 更新详细设计文档
- [ ] 152. 更新任务跟踪文档
- [ ] 153. 完成任务完成追踪表
- [ ] 154. 生成数据质量报告
- [ ] 155. 生成性能测试报告

### 代码审查（5项）

- [ ] 156. 运行pylint检查（评分>9.0）
- [ ] 157. 运行black格式化
- [ ] 158. 运行isort排序导入语句
- [ ] 159. 检查文档字符串完整性
- [ ] 160. 检查日志输出完整性

---

## 📊 检查清单统计

| 阶段 | 检查项数 | 占比 |
|------|---------|------|
| 第一阶段：数据库准备 | 10 | 6.3% |
| 第二阶段：代码实现 | 90 | 56.2% |
| 第三阶段：集成测试 | 35 | 21.9% |
| 第四阶段：质量验证 | 25 | 15.6% |
| **总计** | **160** | **100%** |

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
- [ ] 计算耗时 < 30秒
- [ ] 批量写入速度 > 1000条/秒
- [ ] 内存使用 < 1GB

**文档完整性**：
- [ ] 所有5个文档完成
- [ ] 所有检查项完成
- [ ] 数据质量报告完成
- [ ] 性能测试报告完成

**数据正确性**：
- [ ] 双方法计算正确
- [ ] 交叉验证通过率>90%
- [ ] 覆盖率接近100%
- [ ] 有效率>95%

---

**文档结束**

