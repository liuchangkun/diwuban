# pump_flow_rate 重构完整检查清单

**创建时间**: 2025-01-14
**任务ID**: pump_flow_rate_refactor_20250114
**协议**: RIPER-5 计划模式
**参考文档**: `11-pump_flow_rate重构任务跟踪.md`

---

## 📊 检查清单总览

**总计**: 150+ 个检查项
**分类**: 数据库改造(25项) + 垃圾代码删除(20项) + 共享层(38项) + 指标专用层(72项)

---

## 第一阶段：数据库改造（25项）

### 创建表和索引（8项）
- [ ] 1. 创建 calculation_logs 表（分区表）
- [ ] 2. 添加 calculation_logs 表注释
- [ ] 3. 添加 calculation_logs 列注释（13个列）
- [ ] 4. 创建索引 idx_calculation_logs_task_id
- [ ] 5. 创建索引 idx_calculation_logs_trace_id
- [ ] 6. 创建索引 idx_calculation_logs_device_id
- [ ] 7. 创建索引 idx_calculation_logs_log_level
- [ ] 8. 创建索引 idx_calculation_logs_extra_data (GIN)

### 创建分区（2项）
- [ ] 9. 创建最近30天的分区（30个分区）
- [ ] 10. 验证分区创建成功（COUNT = 30）

### 创建维护函数（5项）
- [ ] 11. 创建函数 maintain_calculation_logs_partitions()
- [ ] 12. 添加函数注释
- [ ] 13. 测试函数执行（手动调用一次）
- [ ] 14. 验证明天的分区已创建
- [ ] 15. 验证31天前的分区已删除（如果存在）

### 删除垃圾数据（3项）
- [ ] 16. 查询 f_thr 和 p_thr 参数数量
- [ ] 17. 删除 f_thr 和 p_thr 参数
- [ ] 18. 验证删除结果（COUNT = 0）

### 验证和测试（7项）
- [ ] 19. 测试插入日志到 calculation_logs
- [ ] 20. 测试按 task_id 查询日志
- [ ] 21. 测试按 trace_id 查询日志
- [ ] 22. 测试按 device_id 查询日志
- [ ] 23. 测试按 log_level 查询日志
- [ ] 24. 测试 extra_data JSON 查询
- [ ] 25. 测试分区查询性能（EXPLAIN ANALYZE）

---

## 第二阶段：垃圾代码删除（20项）

### calculators.py 修改（11项）
- [ ] 1. 修改 line 60: 移除函数文档中的 f_thr, p_thr 参数说明
- [ ] 2. 删除 line 234: `p_thr = params.get('p_thr', 0.5)`
- [ ] 3. 删除 line 237-238: 功率阈值过滤逻辑
- [ ] 4. 修改 line 237-238: 改为直接计算（无阈值过滤）
- [ ] 5. 添加注释说明数据已在 DataFilter 阶段过滤
- [ ] 6. 修改 line 226: 移除函数文档中的 p_thr 参数说明
- [ ] 7. 修改 line 257: 移除函数文档中的 f_thr 参数说明
- [ ] 8. 删除 line 265: `f_thr = params.get('f_thr', 3.0)`
- [ ] 9. 删除 line 268-269: 频率阈值过滤逻辑
- [ ] 10. 修改 line 268-269: 改为直接计算（无阈值过滤）
- [ ] 11. 添加注释说明数据已在 DataFilter 阶段过滤

### orchestrator.py 标记（4项）
- [ ] 12. 添加 @deprecated 装饰器到 calculate_missing_metrics()
- [ ] 13. 添加废弃警告文档
- [ ] 14. 添加迁移指南
- [ ] 15. 保留原有实现（暂不删除）

### 代码清理（5项）
- [ ] 16. 删除未使用的导入语句（运行 pylint）
- [ ] 17. 删除未使用的辅助函数（运行 pylint）
- [ ] 18. 删除未使用的变量（运行 pylint）
- [ ] 19. 运行 black 格式化代码
- [ ] 20. 运行 isort 排序导入语句

---

## 第三阶段：共享层实施（38项）

### Scheduler 实施（10项）
- [ ] 1. 创建文件 `app/services/calculation/shared/scheduler.py`
- [ ] 2. 定义 Task 数据类（7个字段）
- [ ] 3. 定义 TaskResult 数据类（7个字段）
- [ ] 4. 实现 Scheduler.__init__()
- [ ] 5. 实现 Scheduler.create_tasks()
- [ ] 6. 实现 Scheduler.execute_tasks()
- [ ] 7. 实现 Scheduler.shutdown()
- [ ] 8. 实现 Scheduler._get_station_id()（辅助方法）
- [ ] 9. 添加日志输出（3个位置）
- [ ] 10. 添加错误处理（try-except）

### DataWriter 实施（9项）
- [ ] 11. 创建文件 `app/services/calculation/shared/data_writer.py`
- [ ] 12. 定义 WriteRecord 数据类（5个字段）
- [ ] 13. 实现 DataWriter.__init__()
- [ ] 14. 实现 DataWriter.write()
- [ ] 15. 实现 DataWriter._write_batch()
- [ ] 16. 实现 DataWriter._adjust_batch_size()
- [ ] 17. 添加日志输出（3个位置）
- [ ] 18. 添加性能监控（记录耗时）
- [ ] 19. 添加冲突处理（ON CONFLICT DO UPDATE）

### ParameterManager 实施（10项）
- [ ] 20. 创建文件 `app/services/calculation/shared/parameter_manager.py`
- [ ] 21. 实现 ParameterManager.__init__()
- [ ] 22. 定义默认参数字典（移除 f_thr 和 p_thr）
- [ ] 23. 实现 ParameterManager.get_params()
- [ ] 24. 实现 ParameterManager._load_params_from_db()
- [ ] 25. 实现 ParameterManager._get_default_params()
- [ ] 26. 实现 ParameterManager.update_params()
- [ ] 27. 实现 ParameterManager.clear_cache()
- [ ] 28. 添加日志输出（2个位置）
- [ ] 29. 添加缓存机制（_cache 字典）

### SharedServices 实施（6项）
- [ ] 30. 创建文件 `app/services/calculation/shared/shared_services.py`
- [ ] 31. 实现 SharedServices.__new__()（单例模式）
- [ ] 32. 实现 SharedServices.__init__()（延迟初始化）
- [ ] 33. 实现 SharedServices.get_instance()
- [ ] 34. 实现 SharedServices.shutdown()
- [ ] 35. 添加日志输出（2个位置）

### 共享层集成（3项）
- [ ] 36. 创建文件 `app/services/calculation/shared/__init__.py`
- [ ] 37. 导出 Scheduler, DataWriter, ParameterManager, SharedServices
- [ ] 38. 导出 Task, TaskResult, WriteRecord 数据类

---

## 第四阶段：指标专用层实施（72项）

### Pipeline 实施（8项）
- [ ] 39. 创建目录 `app/services/calculation/metrics/pump_flow_rate/`
- [ ] 40. 创建文件 `pipeline.py`
- [ ] 41. 实现 PumpFlowRatePipeline.__init__()
- [ ] 42. 实现 PumpFlowRatePipeline.execute()
- [ ] 43. 实现 PumpFlowRatePipeline._to_results()
- [ ] 44. 生成 trace_id（格式：trace_{device_id}_{timestamp}）
- [ ] 45. 添加日志输出（3个位置：开始、完成、失败）
- [ ] 46. 添加错误处理（try-except）

### DataLoader 实施（8项）
- [ ] 47. 创建文件 `data_loader.py`
- [ ] 48. 实现 DataLoader.__init__()
- [ ] 49. 实现 DataLoader.load()
- [ ] 50. 实现 SQL查询（LEFT JOIN mv_device_running_1s）
- [ ] 51. 加载4个依赖指标（main_flow, power, frequency, cumulative_flow）
- [ ] 52. 加载其他设备数据（用于分摊计算）
- [ ] 53. 添加日志输出（SQL执行时间、行数、JOIN结果）
- [ ] 54. 生成 span_id（格式：span_data_loader_{uuid}）

### DataFilter 实施（8项）
- [ ] 55. 创建文件 `data_filter.py`
- [ ] 56. 实现 DataFilter.__init__()
- [ ] 57. 实现 DataFilter.filter()
- [ ] 58. 使用 running=1 过滤（移除硬编码阈值）
- [ ] 59. 移除 NaN 和负值
- [ ] 60. 添加日志输出（过滤统计）
- [ ] 61. 生成 span_id（格式：span_data_filter_{uuid}）
- [ ] 62. 添加注释说明移除了硬编码阈值

### MethodSelector 实施（10项）
- [ ] 63. 创建文件 `method_selector.py`
- [ ] 64. 实现 MethodSelector.__init__()
- [ ] 65. 定义6种方法配置（优先级、依赖、条件）
- [ ] 66. 实现 MethodSelector.select()
- [ ] 67. 实现 MethodSelector._check_dependencies()
- [ ] 68. 实现 MethodSelector._check_conditions()
- [ ] 69. 实现 MethodSelector._count_running_pumps()
- [ ] 70. 实现 MethodSelector._is_cumulative_flow_valid()
- [ ] 71. 添加日志输出（可用指标、依赖检查、条件检查、选择原因）
- [ ] 72. 生成 span_id（格式：span_method_selector_{uuid}）

**（续）详见 11-pump_flow_rate重构任务跟踪.md 第四部分**

---

## 📝 使用说明

1. **按顺序执行**: 严格按照阶段顺序执行（数据库 → 垃圾代码 → 共享层 → 指标专用层）
2. **逐项检查**: 每完成一项，勾选对应的复选框
3. **验证测试**: 每个阶段完成后，运行对应的测试验证
4. **记录问题**: 如遇到问题，记录在任务跟踪文档中
5. **请求确认**: 每个阶段完成后，请求用户确认再进入下一阶段

---

**文档结束**

