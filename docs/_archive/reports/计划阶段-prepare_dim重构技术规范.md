# 计划阶段：prepare_dim 重构技术规范

> **计划时间**: 2025-10-19  
> **任务**: 重新设计和实现 prepare-dim 流程  
> **协议**: RIPER-5（研究-创新-计划-执行-审查）

---

## 📋 项目规则验证

### 已读取的规则文档
- ✅ `规则/核心模块/规则-核心原则.md`
- ✅ `规则/模式模块/规则-模式3-计划.md`
- ✅ `.memory/规则层/项目规则.md`
- ✅ `.memory/规则层/编码规范.md`
- ✅ `.memory/规则层/数据库规范.md`

### 核心规则确认

#### 编码规范
1. ✅ **文件大小限制**：单文件不超过600行（不含注释和空行）
2. ✅ **禁止使用代码占位符**（除非计划明确要求）
3. ✅ **禁止修改不相关的代码**
4. ✅ **所有注释和日志使用中文**
5. ✅ **使用 logging 模块记录日志**
6. ✅ **函数长度不超过50行**（不含注释和空行）
7. ✅ **参数数量不超过5个**

#### 数据库规范
1. ✅ **使用 ON CONFLICT DO UPDATE 实现幂等性**
2. ✅ **必须使用参数化查询**（禁止字符串拼接SQL）
3. ✅ **表名使用小写+下划线，复数形式**
4. ✅ **字段名使用小写+下划线**
5. ✅ **所有表和列必须有中文注释**

#### 设计原则
1. ✅ **单一职责原则（SRP）**：每个模块/类/函数只负责一个功能
2. ✅ **开闭原则（OCP）**：对扩展开放，对修改封闭
3. ✅ **依赖倒置原则（DIP）**：依赖抽象而非具体实现

### 规则验证结果

#### 任务1：修复 run_all 流程执行顺序
- ✅ 符合单一职责原则（只调整顺序，不改变逻辑）
- ✅ 符合开闭原则（不修改现有函数，只调整调用顺序）
- ✅ 不涉及文件大小问题（只移动代码块）
- ✅ 不涉及数据库操作

#### 任务2：修复配置表初始化
- ✅ 符合单一职责原则（函数只负责重建配置表）
- ✅ 使用参数化查询（执行SQL文件）
- ✅ 添加错误处理和日志（使用中文）
- ✅ 返回值类型明确（Dict[str, Any]）

#### 任务3：实现版本化备份系统
- ✅ 符合单一职责原则（BackupManager 只负责备份）
- ✅ 使用参数化查询（生成SQL备份）
- ✅ 文件大小控制（backup.py 预计<300行）
- ✅ 函数长度控制（每个方法<50行）
- ✅ 参数数量控制（<5个）

#### 任务4：补全计算方法注册表
- ✅ 使用 ON CONFLICT DO UPDATE（幂等性）
- ✅ 使用参数化查询（SQL脚本）
- ✅ 添加中文注释（method_name 字段）

---

## 🎯 架构概述

### 任务分解

本次重构分为4个独立任务，按优先级排序：

#### 任务1：修复 run_all 流程执行顺序 ⚡ **最高优先级**
- **目标**：调整 orchestrator.py 中的步骤执行顺序
- **影响范围**：整个数据处理流程
- **风险**：低（只移动代码块，不改变逻辑）

#### 任务2：修复配置表初始化 🔧 **高优先级**
- **目标**：改进 `_rebuild_config_tables()` 函数，添加错误处理和验证
- **影响范围**：计算功能的正常工作
- **风险**：低（改进现有函数）

#### 任务3：实现版本化备份系统 💾 **中优先级**
- **目标**：实现17个表的SQL文件备份，支持版本管理和增量备份
- **影响范围**：数据安全和恢复能力
- **风险**：低（只增加功能，不改变现有逻辑）

#### 任务4：补全计算方法注册表 📊 **中优先级**
- **目标**：补充 `init_methods.sql` 中缺失的14个计算方法
- **影响范围**：计算功能完整性
- **风险**：低（只增加数据）

---

## 📝 详细更改计划

### 任务1：修复 run_all 流程执行顺序

#### 更改1.1：调整 orchestrator.py 中的代码块顺序

**文件**：`app/services/run_all/orchestrator.py`

**理由**：
- 用户要求将 calculation 移到最后执行
- 当前顺序：device_running → calculation → quality_mark → presence
- 目标顺序：device_running → quality_mark → presence → calculation

**具体更改**：
1. 将 calculation 代码块（行438-638，约200行）移到 presence 代码块之后（行1385之后）
2. 更新注释中的步骤编号
3. 保持所有逻辑不变，只调整顺序

**涉及的函数/类**：
- `run_all()` 函数（主函数）
- 无需修改函数签名

**依赖关系**：
- calculation 依赖 merge_fact（已在前面执行）
- calculation 不依赖 device_running, quality_mark, presence
- 移动后不影响任何功能

**验证方法**：
- 检查代码块是否完整移动
- 检查步骤编号是否正确更新
- 运行 run_all 测试（如果存在）

---

### 任务2：修复配置表初始化

#### 更改2.1：改进 `_rebuild_config_tables()` 函数

**文件**：`app/services/ingest/prepare_dim/__init__.py`

**理由**：
- 当前函数缺少错误处理
- 没有验证执行结果
- SQL文件路径可能不正确

**具体更改**：
1. 修改函数签名：`_rebuild_config_tables(settings, cur) -> Dict[str, Any]`
2. 添加 try-except 错误处理（每个表独立处理）
3. 验证SQL文件路径是否存在
4. 执行SQL后验证行数
5. 返回执行结果字典

**涉及的函数/类**：
- `_rebuild_config_tables(settings: Settings, cur) -> Dict[str, Any]`（修改）
- 无新增函数

**依赖关系**：
- 依赖 SQL 文件：
  - `scripts/sql/calculation/init_methods.sql`
  - `scripts/sql/calculation/init_params.sql`
  - `scripts/migrations/20250829_seed_device_rated_params.sql`
- 依赖 `DependencyAnalyzer` 类

**返回值格式**：
```python
{
    "calculation_method_registry": {"status": "ok", "rows": 11},
    "calculation_parameters": {"status": "ok", "rows": 7},
    "device_rated_params": {"status": "ok", "rows": 13},
    "metric_calculation_order": {"status": "ok", "rows": 9},
}
```

**错误处理策略**：
- 每个表独立处理，一个失败不影响其他表
- 记录错误日志
- 如果验证失败，抛出异常中断流程

**验证方法**：
- 检查返回值格式
- 检查日志输出
- 查询数据库验证行数

---

### 任务3：实现版本化备份系统

#### 更改3.1：创建备份工具模块

**文件**：`app/services/ingest/prepare_dim/backup.py`（新建）

**理由**：
- 将备份逻辑独立到单独模块
- 便于维护和测试
- 复用现有的备份工具函数

**具体更改**：
1. 创建 `BackupManager` 类
2. 实现备份、恢复、版本管理功能
3. 支持增量备份（检测表变化）

**涉及的函数/类**：
- `BackupManager` 类（新建）
  - `__init__(settings, backup_dir="backups")`
  - `backup_tables(cur, tables: List[str]) -> Dict[str, Any]`
  - `restore_table(cur, table_name: str, version: str) -> bool`
  - `_get_next_version(table_name: str) -> str`
  - `_table_has_changed(cur, table_name: str) -> bool`
  - `_backup_single_table(cur, table_name: str, version: str, timestamp: str) -> int`
  - `_cleanup_old_versions(table_name: str, keep_versions: int = 60) -> None`
  - `_generate_sql_backup(cur, table_name: str) -> str`

**依赖关系**：
- 依赖 `pathlib.Path`
- 依赖 `datetime`
- 依赖 `hashlib`（计算校验和）
- 参考 `app/services/system/cleanup.py` 中的 `cleanup_old_backups()` 函数

**备份目录结构**：
```
backups/
├── dim_device_capabilities/
│   ├── dim_device_capabilities_v001_20251019_143025.sql
│   ├── dim_device_capabilities_v002_20251019_150130.sql
│   └── ...（最多60个版本）
├── dim_metric_metadata_override/
│   └── ...
└── ...（共17个表）
```

**备份SQL格式**：
```sql
-- 备份信息
-- 表名: dim_device_capabilities
-- 版本: v001
-- 时间: 2025-10-19 14:30:25
-- 行数: 13
-- 校验和: abc123def456

-- 插入数据（使用 ON CONFLICT DO UPDATE 实现幂等性）
INSERT INTO dim_device_capabilities (device_id, vfd_enabled, freq_min, ...)
VALUES (1, true, 30.0, ...)
ON CONFLICT (device_id) DO UPDATE SET
    vfd_enabled = EXCLUDED.vfd_enabled,
    freq_min = EXCLUDED.freq_min,
    ...;
```

**变化检测策略**：
- 比较行数
- 比较数据校验和（MD5）
- 如果任一变化，则备份

**版本管理策略**：
- 版本号格式：`v<序号>_<时间戳>`
- 序号：3位数字，从001开始递增
- 时间戳：`YYYYMMDD_HHMMSS`
- 保留最新60个版本
- 自动删除旧版本

---

#### 更改3.2：修改 `prepare_dim()` 函数集成备份

**文件**：`app/services/ingest/prepare_dim/__init__.py`

**理由**：
- 在 stage=1 开始时触发备份
- 替换现有的内存备份为文件备份

**具体更改**：
1. 导入 `BackupManager`
2. 在 stage=1 开始时调用 `backup_tables()`
3. 记录备份结果到日志
4. 保留现有的 `_backup_manual_tables()` 和 `_restore_manual_tables()` 函数（用于内存备份）

**涉及的函数/类**：
- `prepare_dim(settings, mapping_path, stage=1)` 函数（修改）

**备份的17个表**：
```python
TABLES_TO_BACKUP = [
    # A类：手动配置表（6个）
    "dim_device_capabilities",
    "dim_metric_metadata_override",
    "pump_characteristic_curves",
    "quality_code_dict",
    "calculation_validation_config",
    "metric_capability_policy",
    # B类：配置表（4个）
    "calculation_parameters",
    "device_rated_params",
    "calculation_method_registry",
    "metric_calculation_order",
    # C类：维度表（1个）
    "dim_metric_config",
    # D类：规则表（6个）
    "metric_rule_auto_baseline",
    "metric_rule_auto_baseline_shadow",
    "metric_quality_rules",
    "metric_quality_rules_shadow",
    "device_running_thresholds",
    "device_running_thresholds_shadow",
]
```

**集成代码位置**：
- 在 `prepare_dim()` 函数的 stage=1 分支开始处
- 在 `_backup_manual_tables()` 调用之前

---

### 任务4：补全计算方法注册表

#### 更改4.1：补充 `init_methods.sql` 脚本

**文件**：`scripts/sql/calculation/init_methods.sql`

**理由**：
- 当前只有11个方法
- 实际实现了25个方法
- 缺少14个方法的注册

**具体更改**：
1. 添加 pump_efficiency 的1个方法
2. 添加 pump_speed 的3个方法
3. 添加 pump_torque 的2个方法
4. 添加 main_pipeline_inlet_pressure 的1个方法
5. 添加 main_pipeline_outlet_pressure 的3个方法（已有，需验证）
6. 添加 pump_cumulative_flow 的2个方法
7. 添加 pump_head 的1个方法（HEAD_COEF_V1，已有，需验证）

**缺失的方法清单**：
1. pump_efficiency: EFF_SIMPLE_V1
2. pump_speed: method_a, method_b, method_c
3. pump_torque: method_a, method_b
4. main_pipeline_inlet_pressure: PIN_COEF_V1
5. pump_cumulative_flow: method_a, method_b

**SQL格式**（参考现有格式）：
```sql
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_efficiency_eff_simple_v1',
    'pump_efficiency',
    '简单效率计算',
    'EFF_SIMPLE_V1',
    100,
    ARRAY['pump_flow_rate', 'pump_head', 'pump_active_power'],
    '{}'::jsonb,
    'docs/计算原理和公式.md#pump_efficiency',
    'medium',
    true
)
ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    formula_ref = EXCLUDED.formula_ref,
    accuracy_level = EXCLUDED.accuracy_level,
    is_enabled = EXCLUDED.is_enabled,
    updated_at = CURRENT_TIMESTAMP;
```

**依赖关系**：
- 需要参考 `app/services/calculation/calculators.py` 中的实现
- 需要参考 `docs/计算原理和公式.md` 中的文档

**验证方法**：
- 执行SQL脚本
- 查询 `calculation_method_registry` 表验证行数
- 检查是否所有方法都已注册

---

## ✅ 实施检查清单

### 任务1：修复 run_all 流程执行顺序

1. **打开文件**：`app/services/run_all/orchestrator.py`
   - 使用 `view` 工具查看行438-638（calculation 代码块）
   - 使用 `view` 工具查看行1320-1385（presence 代码块）

2. **移动 calculation 代码块**：
   - 使用 `str-replace-editor` 工具
   - 将行438-638的代码移到行1385之后
   - 保持代码完整性，不遗漏任何行

3. **更新注释**：
   - 将 calculation 的注释从 "5) 可选后续：缺失指标计算" 改为 "8) 可选后续：缺失指标计算"
   - 将 quality_mark 的注释从 "6) 可选后续：presence 与 quality_mark" 保持不变
   - 将 presence 的注释从 "7) 可选后续：presence" 保持不变

4. **验证修改**：
   - 使用 `view` 工具查看修改后的文件
   - 确认代码块顺序正确
   - 确认没有遗漏或重复的代码

---

### 任务2：修复配置表初始化

5. **打开文件**：`app/services/ingest/prepare_dim/__init__.py`
   - 使用 `view` 工具查看行583-624（`_rebuild_config_tables()` 函数）

6. **修改函数签名**：
   - 将返回类型从 `-> None` 改为 `-> Dict[str, Any]`

7. **添加错误处理和验证**：
   - 为每个表添加 try-except 块
   - 验证SQL文件路径是否存在
   - 执行SQL后查询行数验证
   - 记录详细日志
   - 返回执行结果字典

8. **验证修改**：
   - 使用 `view` 工具查看修改后的函数
   - 确认错误处理逻辑正确
   - 确认返回值格式正确

---

### 任务3：实现版本化备份系统

9. **创建备份工具模块**：
   - 创建文件 `app/services/ingest/prepare_dim/backup.py`
   - 实现 `BackupManager` 类
   - 实现所有必需的方法

10. **实现 `backup_tables()` 方法**：
    - 遍历17个表
    - 检测表是否有变化
    - 生成SQL备份文件
    - 保存到对应目录
    - 清理旧版本

11. **实现 `_generate_sql_backup()` 方法**：
    - 查询表数据
    - 生成 INSERT ... ON CONFLICT DO UPDATE 语句
    - 添加备份信息注释
    - 返回SQL字符串

12. **实现 `_table_has_changed()` 方法**：
    - 查询当前行数
    - 计算当前数据校验和
    - 与上次备份比较
    - 返回是否有变化

13. **实现 `_cleanup_old_versions()` 方法**：
    - 列出所有版本文件
    - 按时间戳排序
    - 保留最新60个版本
    - 删除旧版本

14. **修改 `prepare_dim()` 函数**：
    - 导入 `BackupManager`
    - 在 stage=1 开始时调用 `backup_tables()`
    - 记录备份结果到日志

15. **验证备份功能**：
    - 运行 prepare_dim(stage=1)
    - 检查 backups/ 目录是否创建
    - 检查SQL文件是否生成
    - 检查SQL文件格式是否正确

---

### 任务4：补全计算方法注册表

16. **打开文件**：`scripts/sql/calculation/init_methods.sql`
    - 使用 `view` 工具查看现有内容

17. **补充缺失的方法**：
    - 添加 pump_efficiency: EFF_SIMPLE_V1
    - 添加 pump_speed: method_a, method_b, method_c
    - 添加 pump_torque: method_a, method_b
    - 添加 main_pipeline_inlet_pressure: PIN_COEF_V1
    - 添加 pump_cumulative_flow: method_a, method_b

18. **验证SQL脚本**：
    - 使用 `view` 工具查看修改后的文件
    - 确认所有方法都已添加
    - 确认SQL语法正确

19. **执行SQL脚本**：
    - 运行 prepare_dim(stage=1) 或手动执行SQL
    - 查询 `calculation_method_registry` 表验证行数
    - 确认所有方法都已注册

---

## 🔍 验证计划

### 单元测试
- 为 `BackupManager` 类编写单元测试
- 测试备份、恢复、版本管理功能
- 测试变化检测逻辑

### 集成测试
- 运行完整的 run_all 流程
- 验证执行顺序是否正确
- 验证配置表是否正确初始化
- 验证备份文件是否正确生成

### 手动测试
- 检查 backups/ 目录结构
- 检查SQL文件内容
- 检查日志输出
- 检查数据库表数据

---

## 📊 风险评估

### 任务1：修复 run_all 流程执行顺序
- **风险等级**：低
- **潜在问题**：代码块移动时可能遗漏部分代码
- **缓解措施**：仔细检查代码块边界，使用 view 工具验证

### 任务2：修复配置表初始化
- **风险等级**：低
- **潜在问题**：SQL文件路径可能不正确
- **缓解措施**：验证文件路径，添加详细日志

### 任务3：实现版本化备份系统
- **风险等级**：中
- **潜在问题**：备份文件可能很大，占用磁盘空间
- **缓解措施**：实现版本清理机制，保留最新60个版本

### 任务4：补全计算方法注册表
- **风险等级**：低
- **潜在问题**：方法依赖关系可能不正确
- **缓解措施**：参考代码实现和文档，验证依赖关系

---

**计划阶段完成** ✅

准备进入执行模式，按照检查清单逐项实施。

