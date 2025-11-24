# main_pipeline_inlet_pressure 重构完整检查清单

**创建时间**: 2025-11-22  
**任务ID**: main_pipeline_inlet_pressure_implementation_20251122  
**协议**: RIPER-5 计划模式  
**参考文档**: `02-main_pipeline_inlet_pressure实施计划.md`

---

## 📊 检查清单总览

**总计**: 155 个检查项  
**分类**: 数据库准备(10项) + 代码实现(85项) + 集成测试(35项) + 质量验证(25项)

---

## 第一阶段：数据库准备（10项）

### 数据库参数填充（5项）

- [ ] 1. 验证calculation_parameters表已填充（main_pipeline_inlet_pressure相关参数）
- [ ] 2. 验证method_b参数：P_atm=0.101325, rho=1000.0, g=9.81
- [ ] 3. 验证PIN_COEF_V1参数：b0=0.101325, b1=0.00981, b2=0.0, b3=0.0
- [ ] 4. 验证validation参数：min_pressure=0.05, max_pressure=1.0, max_deviation=0.20, max_change_rate=0.05
- [ ] 5. 查询验证：`SELECT COUNT(*) FROM calculation_parameters WHERE metric_key='main_pipeline_inlet_pressure'` >= 11

### 依赖数据验证（5项）

- [ ] 6. 查询pool_liquid_level数据存在：`SELECT COUNT(*) FROM fact_measurements WHERE metric_id=5 AND device_id=8`
- [ ] 7. 查询mv_device_running_1s表可用：`SELECT COUNT(*) FROM mv_device_running_1s WHERE device_id=7`
- [ ] 8. 验证时间范围：`SELECT MIN(ts_bucket), MAX(ts_bucket) FROM fact_measurements WHERE metric_id=5`
- [ ] 9. 验证设备7的running数据完整性
- [ ] 10. 验证无循环依赖（参考依赖关系验证报告）

---

## 第二阶段：代码实现（85项）

### DataLoader实现（15项）

- [ ] 11. 创建文件 `app/services/calculation/metrics/main_pipeline_inlet_pressure/data_loader.py`
- [ ] 12. 导入必需模块（pandas, logging, datetime, typing）
- [ ] 13. 定义 `DataLoader` 类
- [ ] 14. 实现 `__init__()` 方法（trace_id参数）
- [ ] 15. 实现 `load_data()` 方法签名
- [ ] 16. **重要**：SQL查询中pool_liquid_level从device_id=8获取
- [ ] 17. 实现SQL查询（pool_liquid_level + running状态）
- [ ] 18. 实现数据透视（长表→宽表）
- [ ] 19. 实现返回DataFrame（ts_bucket, device_id, pool_liquid_level, running）
- [ ] 20. 添加日志输出（开始加载, 数据行数, 耗时）
- [ ] 21. 添加错误处理（try-except）
- [ ] 22. 添加文档字符串（中文）
- [ ] 23. 验证device_id=8的数据正确加载
- [ ] 24. 验证device_id=7的running状态正确加载
- [ ] 25. 单元测试：测试DataLoader.load_data()

### DataFilter实现（10项）

- [ ] 26. 创建文件 `app/services/calculation/metrics/main_pipeline_inlet_pressure/data_filter.py`
- [ ] 27. 导入必需模块
- [ ] 28. 定义 `DataFilter` 类
- [ ] 29. 实现 `__init__()` 方法（trace_id参数）
- [ ] 30. 实现 `filter_data()` 方法签名
- [ ] 31. 实现运行状态过滤（data['running'] == 1）
- [ ] 32. 禁止硬编码阈值（代码审查确认）
- [ ] 33. 添加日志输出（原始行数, 过滤后行数, 过滤比例）
- [ ] 34. 添加错误处理
- [ ] 35. 添加文档字符串（中文）

### MethodSelector实现（15项）

- [ ] 36. 创建文件 `app/services/calculation/metrics/main_pipeline_inlet_pressure/method_selector.py`
- [ ] 37. 导入必需模块
- [ ] 38. 定义 `MethodSelector` 类
- [ ] 39. 定义 `METHODS` 列表（2个方法配置）
- [ ] 40. method_b配置：id='method_b', priority=100, dependencies=['pool_liquid_level']
- [ ] 41. PIN_COEF_V1配置：id='PIN_COEF_V1', priority=90, conditions={'calibration_quality': ['medium', 'high']}
- [ ] 42. 实现 `__init__()` 方法（params, trace_id参数）
- [ ] 43. 实现 `select_method()` 方法签名
- [ ] 44. 实现按优先级排序逻辑
- [ ] 45. 实现 `_check_dependencies()` 方法
- [ ] 46. 实现 `_check_conditions()` 方法
- [ ] 47. 添加详细日志输出（方法选择过程, 失败原因）
- [ ] 48. 添加错误处理（无可用方法时抛出ValueError）
- [ ] 49. 添加文档字符串（中文）
- [ ] 50. 单元测试：测试MethodSelector.select_method()

### Calculator实现（20项）

- [ ] 51. 创建文件 `app/services/calculation/metrics/main_pipeline_inlet_pressure/calculator.py`
- [ ] 52. 导入必需模块
- [ ] 53. 定义 `Calculator` 类
- [ ] 54. 实现 `__init__()` 方法（trace_id参数）
- [ ] 55. 实现 `calculate()` 方法签名（data, method_id, params）
- [ ] 56. 实现方法分发逻辑（if-elif-else）
- [ ] 57. 实现 `_method_b()` 方法签名
- [ ] 58. method_b: 获取参数 P_atm, rho, g
- [ ] 59. method_b: 实现公式 P_in = P_atm + ρ×g×h/1e6
- [ ] 60. method_b: 添加method列标记
- [ ] 61. 实现 `_PIN_COEF_V1()` 方法签名
- [ ] 62. PIN_COEF_V1: 获取参数 b0, b1, b2, b3
- [ ] 63. PIN_COEF_V1: 实现公式 P_in = b0 + b1×h + b2×h² + b3×h³
- [ ] 64. PIN_COEF_V1: 添加method列标记
- [ ] 65. 添加日志输出（方法名称, 计算行数, 耗时）
- [ ] 66. 添加错误处理
- [ ] 67. 添加文档字符串（中文）
- [ ] 68. 单元测试：测试Calculator._method_b()
- [ ] 69. 单元测试：测试Calculator._PIN_COEF_V1()
- [ ] 70. 验证计算结果合理性（0.05 - 1.0 MPa）

### Validator实现（15项）

- [ ] 71. 创建文件 `app/services/calculation/metrics/main_pipeline_inlet_pressure/validator.py`
- [ ] 72. 导入必需模块
- [ ] 73. 定义 `Validator` 类
- [ ] 74. 实现 `__init__()` 方法（params, trace_id参数）
- [ ] 75. 实现 `validate()` 方法签名
- [ ] 76. 实现范围检查（0.05 <= P_in <= 1.0 MPa）
- [ ] 77. 实现物理约束检查（P_in ≈ P_atm + ρ×g×h/1e6, ±20%）
- [ ] 78. 实现异常值检查（相邻时刻变化 < 0.05 MPa/s）
- [ ] 79. 实现质量标记逻辑（valid/out_of_range/physics_violation/outlier）
- [ ] 80. 添加valid_range列
- [ ] 81. 添加valid_physics列
- [ ] 82. 添加valid_outlier列
- [ ] 83. 添加quality列
- [ ] 84. 添加日志输出（验证统计, 异常数量, 质量分布）
- [ ] 85. 添加错误处理
- [ ] 86. 添加文档字符串（中文）

### Pipeline实现（15项）

- [ ] 87. 创建文件 `app/services/calculation/metrics/main_pipeline_inlet_pressure/pipeline.py`
- [ ] 88. 导入必需模块（包括所有组件）
- [ ] 89. 定义 `MainPipelineInletPressurePipeline` 类
- [ ] 90. 实现 `__init__()` 方法（初始化所有组件）
- [ ] 91. 实现 `run()` 方法签名（station_id, device_id, start_time, end_time）
- [ ] 92. **重要**：确保device_id=7（总管设备）
- [ ] 93. 生成trace_id（UUID）
- [ ] 94. 调用DataLoader.load_data()
- [ ] 95. 调用DataFilter.filter_data()
- [ ] 96. 调用MethodSelector.select_method()
- [ ] 97. 调用Calculator.calculate()
- [ ] 98. 调用Validator.validate()
- [ ] 99. 返回结果DataFrame
- [ ] 100. 添加性能监控（记录各阶段耗时）
- [ ] 101. 添加错误处理（try-except, 记录到日志）
- [ ] 102. 添加日志输出（trace_id, 各阶段耗时, 结果行数）
- [ ] 103. 添加文档字符串（中文）

### __init__.py实现（3项）

- [ ] 104. 创建文件 `app/services/calculation/metrics/main_pipeline_inlet_pressure/__init__.py`
- [ ] 105. 导入 `MainPipelineInletPressurePipeline`
- [ ] 106. 添加模块文档字符串（中文）

---

## 第三阶段：集成测试（35项）

### 调度器集成（5项）

- [ ] 107. 打开文件 `app/services/calculation/shared/scheduler.py`
- [ ] 108. 在METRIC_ORDER列表第2位添加 "main_pipeline_inlet_pressure"
- [ ] 109. 验证main_pipeline_inlet_pressure在pump_flow_rate之前
- [ ] 110. 验证main_pipeline_inlet_pressure在pump_speed之后
- [ ] 111. 保存文件并运行格式化（black, isort）

### 参数管理集成（10项）

- [ ] 112. 测试ParameterManager.get_parameters('main_pipeline_inlet_pressure', 'method_b')
- [ ] 113. 验证返回P_atm=0.101325, rho=1000.0, g=9.81
- [ ] 114. 测试ParameterManager.get_parameters('main_pipeline_inlet_pressure', 'PIN_COEF_V1')
- [ ] 115. 验证返回b0=0.101325, b1=0.00981, b2=0.0, b3=0.0
- [ ] 116. 测试ParameterManager.get_parameters('main_pipeline_inlet_pressure', 'validation')
- [ ] 117. 验证返回min_pressure=0.05, max_pressure=1.0
- [ ] 118. 验证返回max_deviation=0.20, max_change_rate=0.05
- [ ] 119. 测试参数缓存功能
- [ ] 120. 测试参数不存在时的默认值处理
- [ ] 121. 测试参数更新后的缓存刷新

### 数据写入集成（5项）

- [ ] 122. 测试DataWriter.write_results()
- [ ] 123. 验证metric_id=61
- [ ] 124. 验证device_id=7（总管设备）
- [ ] 125. 验证数据写入fact_measurements表
- [ ] 126. 验证批量写入性能（>1000条/秒）

### 单元测试（10项）

- [ ] 127. 测试DataLoader.load_data()（模拟数据）
- [ ] 128. 验证pool_liquid_level从device_id=8加载
- [ ] 129. 测试DataFilter.filter_data()（running=1过滤）
- [ ] 130. 测试MethodSelector.select_method()（method_b选择）
- [ ] 131. 测试MethodSelector.select_method()（PIN_COEF_V1选择）
- [ ] 132. 测试Calculator._method_b()（公式正确性）
- [ ] 133. 测试Calculator._PIN_COEF_V1()（公式正确性）
- [ ] 134. 测试Validator.validate()（范围检查）
- [ ] 135. 测试Validator.validate()（物理约束检查）
- [ ] 136. 测试Validator.validate()（异常值检查）

### 集成测试（5项）

- [ ] 137. 测试完整流水线（设备7, 2025-10-22 08:00:00 到 2025-10-23 07:19:37）
- [ ] 138. 验证计算结果写入数据库
- [ ] 139. 验证数据量符合预期（约8万条）
- [ ] 140. 验证计算耗时符合预期（<30秒）
- [ ] 141. 验证pool_liquid_level数据来源正确（device_id=8）

---

## 第四阶段：质量验证（25项）

### 数据质量分析（10项）

- [ ] 142. 查询计算结果数量：`SELECT COUNT(*) FROM fact_measurements WHERE metric_id=61`
- [ ] 143. 统计设备7数据量
- [ ] 144. 统计各方法使用比例：`SELECT method, COUNT(*) FROM ... GROUP BY method`
- [ ] 145. 统计质量标记分布：`SELECT quality, COUNT(*) FROM ... GROUP BY quality`
- [ ] 146. 分析out_of_range数据原因
- [ ] 147. 分析physics_violation数据原因
- [ ] 148. 分析outlier数据原因
- [ ] 149. 生成数据质量报告
- [ ] 150. 对比不同方法的计算结果差异
- [ ] 151. 验证压力范围合理性（0.05-1.0 MPa）

### 性能优化（5项）

- [ ] 152. 分析计算耗时分布（DataLoader, DataFilter, Calculator, Validator）
- [ ] 153. 优化SQL查询（添加索引, 优化JOIN）
- [ ] 154. 优化批量写入（调整batch_size）
- [ ] 155. 调整自适应分片参数（time_chunk_hours）

- [ ] 156. 记录性能指标到calculation_performance_metrics表

### 文档完善（5项）

- [ ] 157. 更新 `01-main_pipeline_inlet_pressure详细设计.md`（补充实际实现细节）
- [ ] 158. 更新 `03-main_pipeline_inlet_pressure重构任务跟踪.md`（更新任务状态）
- [ ] 159. 完成 `05-任务完成追踪表.md`（记录完成时间）
- [ ] 160. 生成数据质量报告（独立文档）
- [ ] 161. 生成性能测试报告（独立文档）

### 代码审查（5项）

- [ ] 162. 运行pylint检查（无错误, 评分>9.0）
- [ ] 163. 运行black格式化（所有文件）
- [ ] 164. 运行isort排序导入语句（所有文件）
- [ ] 165. 检查文档字符串完整性（所有类和方法）
- [ ] 166. 检查日志输出完整性（所有关键步骤）

---

## 📊 检查清单统计

| 阶段 | 检查项数 | 占比 |
|------|---------|------|
| 第一阶段：数据库准备 | 10 | 6.0% |
| 第二阶段：代码实现 | 96 | 57.8% |
| 第三阶段：集成测试 | 35 | 21.1% |
| 第四阶段：质量验证 | 25 | 15.1% |
| **总计** | **166** | **100%** |

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
- [ ] pool_liquid_level从device_id=8正确加载
- [ ] 计算结果写入device_id=7
- [ ] 无数据混淆

---

**文档结束**


