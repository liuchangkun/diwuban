# pump_shaft_power 执行检查清单

> **协议**: RIPER-5 执行模式  
> **日期**: 2025-11-22  
> **状态**: 执行前检查清单  
> **参考**: 技术规范09

---

## 阶段1：数据库准备（10项）

### 参数初始化（5项）

- [ ] 1.1 创建参数初始化SQL脚本 `scripts/init_pump_shaft_power_params.sql`
- [ ] 1.2 执行SQL脚本，插入device_rated_params（eta_motor, eta_vfd，设备1-6）
- [ ] 1.3 执行SQL脚本，插入calculation_parameters（max_power, max_change_rate）
- [ ] 1.4 验证参数插入成功（查询device_rated_params表）
- [ ] 1.5 验证参数插入成功（查询calculation_parameters表）

### 依赖验证（5项）

- [ ] 1.6 验证pump_active_power数据存在（metric_id=2, device_id=1-6）
- [ ] 1.7 验证mv_device_running_1s表可用
- [ ] 1.8 验证dim_metric_config已配置（metric_id=66）
- [ ] 1.9 验证设备类型正确（device_id=1-6, type='pump'）
- [ ] 1.10 验证无循环依赖

---

## 阶段2：代码实现（80项）

### 目录结构（5项）

- [ ] 2.1 创建目录 `app/services/calculation/metrics/pump_shaft_power/`
- [ ] 2.2 创建目录 `app/services/calculation/metrics/pump_shaft_power/methods/`
- [ ] 2.3 创建文件 `__init__.py`（导出PumpShaftPowerPipeline）
- [ ] 2.4 创建文件 `methods/__init__.py`（导出method_a）
- [ ] 2.5 验证目录结构符合规范

### DataLoader实现（15项）

- [ ] 2.6 创建文件 `data_loader.py`
- [ ] 2.7 定义DataLoader类
- [ ] 2.8 实现__init__(trace_id)方法
- [ ] 2.9 实现load_data()方法
- [ ] 2.10 SQL查询pump_active_power（metric_key='pump_active_power'）
- [ ] 2.11 LEFT JOIN mv_device_running_1s获取running状态
- [ ] 2.12 设备类型检查（type='pump'）
- [ ] 2.13 数据透视（长表→宽表）
- [ ] 2.14 返回DataFrame格式正确（ts_bucket, device_id, pump_active_power, running）
- [ ] 2.15 日志输出完整（加载行数、查询耗时）
- [ ] 2.16 异常处理完善
- [ ] 2.17 文档字符串完整
- [ ] 2.18 类型注解正确
- [ ] 2.19 使用log_sql记录SQL查询
- [ ] 2.20 处理空数据情况

### DataFilter实现（10项）

- [ ] 2.21 创建文件 `data_filter.py`
- [ ] 2.22 定义DataFilter类
- [ ] 2.23 实现__init__(max_power, trace_id)方法
- [ ] 2.24 验证必需参数存在性（max_power不能为None）
- [ ] 2.25 实现filter_data()方法
- [ ] 2.26 使用running字段过滤（data['running'] == 1）
- [ ] 2.27 过滤NaN/Inf值
- [ ] 2.28 过滤负值
- [ ] 2.29 过滤异常值（pump_active_power <= max_power）
- [ ] 2.30 日志输出完整（原始行数、过滤后行数、过滤比例）

### MethodSelector实现（10项）

- [ ] 2.31 创建文件 `method_selector.py`
- [ ] 2.32 定义MethodSelector类
- [ ] 2.33 实现__init__(params, trace_id)方法
- [ ] 2.34 定义METHODS配置（method_a）
- [ ] 2.35 实现select_method()方法
- [ ] 2.36 检查pump_active_power列存在
- [ ] 2.37 检查device_params存在（eta_motor, eta_vfd）
- [ ] 2.38 返回method_a
- [ ] 2.39 日志输出完整（方法选择过程）
- [ ] 2.40 异常处理完善

### Calculator实现（10项）

- [ ] 2.41 创建文件 `calculator.py`
- [ ] 2.42 定义Calculator类
- [ ] 2.43 实现__init__(params, trace_id)方法
- [ ] 2.44 实现calculate()方法
- [ ] 2.45 调用method_a.calculate()
- [ ] 2.46 添加method_id列
- [ ] 2.47 日志输出完整（计算行数、计算耗时、统计信息）
- [ ] 2.48 异常处理完善
- [ ] 2.49 文档字符串完整
- [ ] 2.50 类型注解正确

### Validator实现（10项）

- [ ] 2.51 创建文件 `validator.py`
- [ ] 2.52 定义Validator类
- [ ] 2.53 实现__init__(params, trace_id)方法
- [ ] 2.54 实现validate()方法
- [ ] 2.55 范围检查（0 <= P_shaft <= max_power）
- [ ] 2.56 效率检查（P_shaft > P_active）
- [ ] 2.57 NaN/Inf检查
- [ ] 2.58 添加quality_code列（0=有效, 2=范围异常, 3=效率违反）
- [ ] 2.59 过滤无效数据（quality_code == 0）
- [ ] 2.60 日志输出完整（验证统计、质量分布）

### Pipeline实现（10项）

- [ ] 2.61 创建文件 `pipeline.py`
- [ ] 2.62 定义PumpShaftPowerPipeline类
- [ ] 2.63 实现__init__()方法
- [ ] 2.64 实现execute()方法
- [ ] 2.65 使用SharedServices获取参数
- [ ] 2.66 按顺序执行6个阶段（DataLoader → DataFilter → MethodSelector → Calculator → Validator → DataWriter）
- [ ] 2.67 处理空数据情况（返回skipped=True）
- [ ] 2.68 使用DataWriter写入结果
- [ ] 2.69 日志输出完整（每个阶段的输入输出、耗时）
- [ ] 2.70 异常处理完善

### method_a实现（10项）

- [ ] 2.71 创建文件 `methods/method_a.py`
- [ ] 2.72 定义calculate()函数
- [ ] 2.73 公式正确：P_shaft = P_active / (η_motor × η_vfd)
- [ ] 2.74 从params获取device_params
- [ ] 2.75 获取当前设备的eta_motor
- [ ] 2.76 获取当前设备的eta_vfd
- [ ] 2.77 计算pump_shaft_power列
- [ ] 2.78 返回结果DataFrame
- [ ] 2.79 文档字符串完整（公式、参数说明）
- [ ] 2.80 类型注解正确

---

## 阶段3：集成和测试（35项）

### METRIC_ORDER更新（5项）

- [ ] 3.1 打开文件 `app/services/calculation/shared/scheduler.py`
- [ ] 3.2 在METRIC_ORDER中添加pump_shaft_power（pump_speed之后）
- [ ] 3.3 验证计算顺序正确
- [ ] 3.4 验证无循环依赖
- [ ] 3.5 保存文件

### 参数管理集成（5项）

- [ ] 3.6 测试ParameterManager加载device_rated_params（eta_motor, eta_vfd）
- [ ] 3.7 测试ParameterManager加载calculation_parameters（max_power, max_change_rate）
- [ ] 3.8 验证参数合并正确（设备 > 泵站 > 全局）
- [ ] 3.9 验证参数缓存正常工作
- [ ] 3.10 验证缺失参数时抛出异常

### 数据写入集成（5项）

- [ ] 3.11 测试DataWriter写入结果（metric_id=66, device_id=1-6）
- [ ] 3.12 验证WriteRecord格式正确
- [ ] 3.13 验证批量写入性能（>1000条/秒）
- [ ] 3.14 验证数据完整性（查询fact_measurements表）
- [ ] 3.15 验证quality_code正确写入

### 单元测试（10项）

- [ ] 3.16 测试DataLoader（正常情况）
- [ ] 3.17 测试DataLoader（设备类型不匹配）
- [ ] 3.18 测试DataFilter（正常情况）
- [ ] 3.19 测试DataFilter（缺失参数）
- [ ] 3.20 测试MethodSelector（正常情况）
- [ ] 3.21 测试Calculator（method_a）
- [ ] 3.22 测试Validator（范围检查）
- [ ] 3.23 测试Validator（效率检查）
- [ ] 3.24 测试Pipeline（完整流程）
- [ ] 3.25 测试Pipeline（空数据）

### 集成测试（10项）

- [ ] 3.26 测试设备1（1小时时间范围）
- [ ] 3.27 测试设备2（1小时时间范围）
- [ ] 3.28 测试设备3（1小时时间范围）
- [ ] 3.29 测试设备4（1小时时间范围）
- [ ] 3.30 测试设备5（1小时时间范围）
- [ ] 3.31 测试设备6（1小时时间范围）
- [ ] 3.32 测试所有设备（全部时间范围）
- [ ] 3.33 验证计算结果数量
- [ ] 3.34 验证质量标记分布
- [ ] 3.35 验证效率检查通过（P_shaft > P_active）

---

## 阶段4：质量验证（25项）

### 数据质量分析（10项）

- [ ] 4.1 查询计算结果总数
- [ ] 4.2 统计各设备结果数量
- [ ] 4.3 统计质量标记分布（quality_code=0/2/3）
- [ ] 4.4 分析范围异常原因
- [ ] 4.5 分析效率违反原因
- [ ] 4.6 验证覆盖率（应接近100%）
- [ ] 4.7 验证有效率（应>95%）
- [ ] 4.8 生成数据质量报告
- [ ] 4.9 记录异常数据示例
- [ ] 4.10 验证P_shaft > P_active（所有有效数据）

### 性能优化（5项）

- [ ] 4.11 分析计算耗时（各组件耗时）
- [ ] 4.12 优化SQL查询（索引、分区）
- [ ] 4.13 优化批量写入（批次大小）
- [ ] 4.14 验证性能提升
- [ ] 4.15 记录性能指标

### 文档完善（5项）

- [ ] 4.16 更新01-pump_shaft_power详细设计.md
- [ ] 4.17 更新03-pump_shaft_power重构任务跟踪.md
- [ ] 4.18 完成05-任务完成追踪表.md
- [ ] 4.19 生成数据质量报告
- [ ] 4.20 生成性能测试报告

### 代码审查（5项）

- [ ] 4.21 运行pylint检查（评分>9.0）
- [ ] 4.22 运行black格式化
- [ ] 4.23 运行isort排序导入语句
- [ ] 4.24 检查文档字符串完整性
- [ ] 4.25 检查日志输出完整性

---

## 📊 检查清单统计

| 阶段 | 检查项数 | 占比 |
|------|---------|------|
| 阶段1：数据库准备 | 10 | 6.7% |
| 阶段2：代码实现 | 80 | 53.3% |
| 阶段3：集成和测试 | 35 | 23.3% |
| 阶段4：质量验证 | 25 | 16.7% |
| **总计** | **150** | **100%** |

---

**执行检查清单完成**

