# pump_speed 重构完整检查清单

**创建时间**: 2025-11-22  
**任务ID**: pump_speed_implementation_20251122  
**协议**: RIPER-5 计划模式  
**参考文档**: `02-pump_speed实施计划.md`

---

## 📊 检查清单总览

**总计**: 150+ 个检查项  
**分类**: 数据库准备(15项) + 代码实现(80项) + 集成测试(30项) + 质量验证(25项)

---

## 第一阶段：数据库准备（15项）

### 数据库参数填充（10项）

- [ ] 1. 执行 `device_rated_params_backup_20251122.sql`
- [ ] 2. 验证设备1参数插入成功（7个参数）
- [ ] 3. 验证设备2参数插入成功（7个参数）
- [ ] 4. 验证设备3参数插入成功（7个参数）
- [ ] 5. 验证设备4参数插入成功（7个参数）
- [ ] 6. 验证设备5参数插入成功（7个参数）
- [ ] 7. 验证设备6参数插入成功（7个参数）
- [ ] 8. 执行 `calculation_parameters_backup_20251122.sql`
- [ ] 9. 验证pump_speed参数插入成功（method_a, method_b, method_c, validation）
- [ ] 10. 查询验证：`SELECT COUNT(*) FROM device_rated_params WHERE device_id IN (1,2,3,4,5,6)` = 42

### 依赖数据验证（5项）

- [ ] 11. 查询pump_frequency数据存在：`SELECT COUNT(*) FROM fact_measurements WHERE metric_id=1`
- [ ] 12. 查询mv_device_running_1s表可用：`SELECT COUNT(*) FROM mv_device_running_1s`
- [ ] 13. 验证时间范围：`SELECT MIN(ts_bucket), MAX(ts_bucket) FROM fact_measurements`
- [ ] 14. 验证设备1-6的pump_frequency数据完整性
- [ ] 15. 验证无循环依赖（参考依赖关系验证报告）

---

## 第二阶段：代码实现（80项）

### DataLoader实现（12项）

- [ ] 16. 创建文件 `app/services/calculation/metrics/pump_speed/data_loader.py`
- [ ] 17. 导入必需模块（pandas, logging, datetime, typing）
- [ ] 18. 定义 `DataLoader` 类
- [ ] 19. 实现 `__init__()` 方法（trace_id参数）
- [ ] 20. 实现 `load_data()` 方法签名
- [ ] 21. 实现设备类型检查（仅计算type='pump'的设备）
- [ ] 22. 实现SQL查询（pump_frequency + running状态）
- [ ] 23. 实现数据透视（长表→宽表）
- [ ] 24. 实现返回DataFrame（ts_bucket, device_id, pump_frequency, running）
- [ ] 25. 添加日志输出（开始加载, 数据行数, 耗时）
- [ ] 26. 添加错误处理（try-except）
- [ ] 27. 添加文档字符串（中文）

### DataFilter实现（10项）

- [ ] 28. 创建文件 `app/services/calculation/metrics/pump_speed/data_filter.py`
- [ ] 29. 导入必需模块
- [ ] 30. 定义 `DataFilter` 类
- [ ] 31. 实现 `__init__()` 方法（trace_id参数）
- [ ] 32. 实现 `filter_data()` 方法签名
- [ ] 33. 实现运行状态过滤（data['running'] == 1）
- [ ] 34. 禁止硬编码阈值（代码审查确认）
- [ ] 35. 添加日志输出（原始行数, 过滤后行数, 过滤比例）
- [ ] 36. 添加错误处理
- [ ] 37. 添加文档字符串（中文）

### MethodSelector实现（15项）

- [ ] 38. 创建文件 `app/services/calculation/metrics/pump_speed/method_selector.py`
- [ ] 39. 导入必需模块
- [ ] 40. 定义 `MethodSelector` 类
- [ ] 41. 定义 `METHODS` 列表（3个方法配置）
- [ ] 42. method_a配置：id='method_a', priority=100, dependencies=['pump_frequency']
- [ ] 43. method_b配置：id='method_b', priority=90, conditions={'has_device_params': ['pole_pairs', 'slip']}
- [ ] 44. method_c配置：id='method_c', priority=80, conditions={'calibration_quality': ['medium', 'high']}
- [ ] 45. 实现 `__init__()` 方法（device_params, trace_id参数）
- [ ] 46. 实现 `select_method()` 方法签名
- [ ] 47. 实现按优先级排序逻辑
- [ ] 48. 实现 `_check_dependencies()` 方法
- [ ] 49. 实现 `_check_conditions()` 方法
- [ ] 50. 添加详细日志输出（方法选择过程, 失败原因）
- [ ] 51. 添加错误处理（无可用方法时抛出ValueError）
- [ ] 52. 添加文档字符串（中文）

### Calculator实现（20项）

- [ ] 53. 创建文件 `app/services/calculation/metrics/pump_speed/calculator.py`
- [ ] 54. 导入必需模块
- [ ] 55. 定义 `Calculator` 类
- [ ] 56. 实现 `__init__()` 方法（trace_id参数）
- [ ] 57. 实现 `calculate()` 方法签名（data, method_id, params）
- [ ] 58. 实现方法分发逻辑（if-elif-else）
- [ ] 59. 实现 `_method_a()` 方法签名
- [ ] 60. method_a: 获取参数 f_ref, n_ref
- [ ] 61. method_a: 实现公式 n = (f / f_ref) × n_ref
- [ ] 62. method_a: 处理频率为0的情况（n=0）
- [ ] 63. method_a: 添加method列标记
- [ ] 64. 实现 `_method_b()` 方法签名
- [ ] 65. method_b: 获取参数 pole_pairs, slip
- [ ] 66. method_b: 实现公式 n = 60 × f / pole_pairs × (1 - slip)
- [ ] 67. method_b: 处理频率为0的情况（n=0）
- [ ] 68. method_b: 添加method列标记
- [ ] 69. 实现 `_method_c()` 方法签名
- [ ] 70. method_c: 获取参数 calibration_a, calibration_b
- [ ] 71. method_c: 实现公式 n = a × f + b
- [ ] 72. method_c: 添加method列标记
- [ ] 73. 添加日志输出（方法名称, 计算行数, 耗时）
- [ ] 74. 添加错误处理
- [ ] 75. 添加文档字符串（中文）

### Validator实现（15项）

- [ ] 76. 创建文件 `app/services/calculation/metrics/pump_speed/validator.py`
- [ ] 77. 导入必需模块
- [ ] 78. 定义 `Validator` 类
- [ ] 79. 实现 `__init__()` 方法（params, trace_id参数）
- [ ] 80. 实现 `validate()` 方法签名
- [ ] 81. 实现范围检查（0 <= n <= 3000 rpm）
- [ ] 82. 实现物理约束检查（n ≈ 30×f, ±10%）
- [ ] 83. 实现异常值检查（相邻时刻变化 < 100 rpm/s）
- [ ] 84. 实现质量标记逻辑（valid/out_of_range/physics_violation/outlier）
- [ ] 85. 添加valid_range列
- [ ] 86. 添加valid_physics列
- [ ] 87. 添加valid_outlier列
- [ ] 88. 添加quality列
- [ ] 89. 添加日志输出（验证统计, 异常数量, 质量分布）
- [ ] 90. 添加错误处理
- [ ] 91. 添加文档字符串（中文）

### Pipeline实现（15项）

- [ ] 92. 创建文件 `app/services/calculation/metrics/pump_speed/pipeline.py`
- [ ] 93. 导入必需模块（包括所有组件）
- [ ] 94. 定义 `PumpSpeedPipeline` 类
- [ ] 95. 实现 `__init__()` 方法（初始化所有组件）
- [ ] 96. 实现 `run()` 方法签名（station_id, device_id, start_time, end_time）
- [ ] 97. 生成trace_id（UUID）
- [ ] 98. 调用DataLoader.load_data()
- [ ] 99. 调用DataFilter.filter_data()
- [ ] 100. 调用MethodSelector.select_method()
- [ ] 101. 调用Calculator.calculate()
- [ ] 102. 调用Validator.validate()
- [ ] 103. 返回结果DataFrame
- [ ] 104. 添加性能监控（记录各阶段耗时）
- [ ] 105. 添加错误处理（try-except, 记录到日志）
- [ ] 106. 添加日志输出（trace_id, 各阶段耗时, 结果行数）
- [ ] 107. 添加文档字符串（中文）

### __init__.py实现（3项）

- [ ] 108. 创建文件 `app/services/calculation/metrics/pump_speed/__init__.py`
- [ ] 109. 导入 `PumpSpeedPipeline`
- [ ] 110. 添加模块文档字符串（中文）

---

## 第三阶段：集成测试（30项）

### 调度器集成（5项）

- [ ] 111. 打开文件 `app/services/calculation/shared/scheduler.py`
- [ ] 112. 在METRIC_ORDER列表开头添加 "pump_speed"
- [ ] 113. 验证pump_speed在pump_torque之前
- [ ] 114. 验证pump_speed在pump_flow_rate之前
- [ ] 115. 保存文件并运行格式化（black, isort）

### 参数管理集成（5项）

- [ ] 116. 测试ParameterManager.get_parameters('pump_speed', 'method_a')
- [ ] 117. 验证返回f_ref=50.0, n_ref=1500.0
- [ ] 118. 测试ParameterManager.get_parameters('pump_speed', 'method_b', device_id=1)
- [ ] 119. 验证返回pole_pairs=2, slip=0.02
- [ ] 120. 测试参数缓存功能

### 数据写入集成（5项）

- [ ] 121. 测试DataWriter.write_results()
- [ ] 122. 验证metric_id=19
- [ ] 123. 验证数据写入fact_measurements表
- [ ] 124. 验证批量写入性能（>1000条/秒）
- [ ] 125. 查询验证：`SELECT COUNT(*) FROM fact_measurements WHERE metric_id=19`

### 单元测试（10项）

- [ ] 126. 测试DataLoader.load_data()（模拟数据）
- [ ] 127. 测试DataFilter.filter_data()（running=1过滤）
- [ ] 128. 测试MethodSelector.select_method()（method_a选择）
- [ ] 129. 测试MethodSelector.select_method()（method_b选择）
- [ ] 130. 测试MethodSelector.select_method()（method_c选择）
- [ ] 131. 测试Calculator._method_a()（公式正确性）
- [ ] 132. 测试Calculator._method_b()（公式正确性）
- [ ] 133. 测试Calculator._method_c()（公式正确性）
- [ ] 134. 测试Validator.validate()（范围检查）
- [ ] 135. 测试Validator.validate()（物理约束检查）

### 集成测试（5项）

- [ ] 136. 测试完整流水线（设备1, 2025-10-22 08:00:00 到 2025-10-23 07:19:37）
- [ ] 137. 测试完整流水线（设备2-6）
- [ ] 138. 验证计算结果写入数据库
- [ ] 139. 验证数据量符合预期（约50万条）
- [ ] 140. 验证计算耗时符合预期（<60秒）

---

## 第四阶段：质量验证（25项）

### 数据质量分析（10项）

- [ ] 141. 查询计算结果数量：`SELECT COUNT(*) FROM fact_measurements WHERE metric_id=19`
- [ ] 142. 统计各设备数据量分布
- [ ] 143. 统计各方法使用比例：`SELECT method, COUNT(*) FROM ... GROUP BY method`
- [ ] 144. 统计质量标记分布：`SELECT quality, COUNT(*) FROM ... GROUP BY quality`
- [ ] 145. 分析out_of_range数据原因
- [ ] 146. 分析physics_violation数据原因
- [ ] 147. 分析outlier数据原因
- [ ] 148. 生成数据质量报告
- [ ] 149. 对比不同方法的计算结果差异
- [ ] 150. 验证转速范围合理性（0-1500 rpm）

### 性能优化（5项）

- [ ] 151. 分析计算耗时分布（DataLoader, DataFilter, Calculator, Validator）
- [ ] 152. 优化SQL查询（添加索引, 优化JOIN）
- [ ] 153. 优化批量写入（调整batch_size）
- [ ] 154. 调整自适应分片参数（time_chunk_hours）
- [ ] 155. 记录性能指标到calculation_performance_metrics表

### 文档完善（5项）

- [ ] 156. 更新 `01-pump_speed详细设计.md`（补充实际实现细节）
- [ ] 157. 更新 `03-pump_speed重构任务跟踪.md`（更新任务状态）
- [ ] 158. 完成 `05-任务完成追踪表.md`（记录完成时间）
- [ ] 159. 生成数据质量报告（独立文档）
- [ ] 160. 生成性能测试报告（独立文档）

### 代码审查（5项）

- [ ] 161. 运行pylint检查（无错误, 评分>9.0）
- [ ] 162. 运行black格式化（所有文件）
- [ ] 163. 运行isort排序导入语句（所有文件）
- [ ] 164. 检查文档字符串完整性（所有类和方法）
- [ ] 165. 检查日志输出完整性（所有关键步骤）

---

## 📊 检查清单统计

| 阶段 | 检查项数 | 占比 |
|------|---------|------|
| 第一阶段：数据库准备 | 15 | 9.1% |
| 第二阶段：代码实现 | 95 | 57.6% |
| 第三阶段：集成测试 | 30 | 18.2% |
| 第四阶段：质量验证 | 25 | 15.1% |
| **总计** | **165** | **100%** |

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
- [ ] 计算耗时 < 60秒（全部时间范围）
- [ ] 批量写入速度 > 1000条/秒
- [ ] 内存使用 < 2GB

**文档完整性**：
- [ ] 所有5个文档完成
- [ ] 所有检查项完成
- [ ] 数据质量报告完成
- [ ] 性能测试报告完成

---

**文档结束**


