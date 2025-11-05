# prepare_dim 重构技术规范 v2.0

> **创建时间**：2025-01-19
> **模式**：计划模式
> **版本**：v2.0（基于用户确认的需求）

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

---

## 🎯 架构概览

### 任务优先级

| 优先级 | 任务 | 影响 | 复杂度 | 风险 |
|--------|------|------|--------|------|
| ⚡ 最高 | 任务2：实现完整的备份系统 | 数据安全 | 高 | 低 |
| ⚡ 最高 | 任务7：废除旧清空逻辑，创建新清空逻辑 | 避免误删 | 中 | 中 |
| 🔧 高 | 任务3：修复 dim_metric_config 恢复逻辑 | 数据完整性 | 低 | 低 |
| 🔧 高 | 任务4：扩展配置表备份和恢复 | 数据完整性 | 中 | 低 |
| 🔧 高 | 任务5：补全计算方法注册表 | 功能完整性 | 中 | 低 |
| 🔧 高 | 任务1：修复 run_all 流程执行顺序 | 流程正确性 | 低 | 低 |
| 📊 中 | 任务6：修复配置表初始化 | 代码质量 | 低 | 低 |

### 核心设计决策

**用户确认的关键决策**：
1. ✅ **备份触发时机**：每次进入 prepare_dim 都执行备份，与配置选项无关
2. ✅ **恢复触发时机**：只有当 `prepare_dim: true` 时才执行恢复
3. ✅ **metric_calculation_order 处理**：从备份恢复（方案A）
4. ✅ **清空逻辑**：完全废除 `_clear_dependent_tables()`，创建新函数 `_clear_non_backup_tables()`
5. ✅ **代码清理**：删除所有废弃、冗余、垃圾代码

---

## 📝 详细变更计划

### 任务1：修复 run_all 流程执行顺序 ⚡

**文件**：`app/services/run_all/orchestrator.py`

**当前问题**：
- calculation 步骤在 quality_mark 和 presence 之前执行
- 正确顺序应该是：device_running → quality_mark → presence → calculation

**具体更改**：
1. 定位 calculation 代码块（约200行，lines 438-638）
2. 定位 presence 代码块（lines 1320-1385）
3. 使用 str-replace-editor 移动 calculation 代码块到 presence 之后
4. 更新步骤编号注释（7→9, 8→7, 9→8）

**涉及的函数/类**：
- `run_all()` 函数

**依赖关系**：
- 独立任务，不依赖其他任务
- 不影响其他任务

**验证方法**：
- 检查代码块是否完整移动
- 检查步骤编号是否正确更新
- 运行 run_all 流程，验证执行顺序

---

### 任务2：实现完整的备份系统 💾

**文件**：`app/services/ingest/prepare_dim/backup.py`（新建）

**当前问题**：
- 只备份2个表（dim_device_capabilities, dim_metric_metadata_override）
- 使用内存备份，不持久化
- 没有版本管理
- 备份覆盖率仅 11.8%

**目标**：
- 备份17个表到SQL文件
- 支持版本管理（保留60个版本）
- 支持增量备份（只备份变化的表）
- 使用 `INSERT ... ON CONFLICT DO UPDATE` 实现幂等性

**具体更改**：

#### 2.1 创建 BackupManager 类

**类签名**：
```python
class BackupManager:
    """备份管理器"""
    
    def __init__(self, backup_dir: Path = Path("backups"), keep_versions: int = 60):
        """初始化备份管理器"""
        
    def backup_tables(self, cur, tables: List[str]) -> Dict[str, Any]:
        """备份指定的表"""
        
    def restore_table(self, cur, table_name: str, version: int = None) -> Dict[str, Any]:
        """恢复表数据"""
        
    def _table_has_changed(self, cur, table_name: str) -> bool:
        """检测表是否发生变化（行数 + MD5）"""
        
    def _generate_sql_backup(self, cur, table_name: str) -> str:
        """生成SQL备份脚本"""
        
    def _get_next_version(self, table_name: str) -> int:
        """获取下一个版本号"""
        
    def _cleanup_old_versions(self, table_name: str) -> None:
        """清理旧版本（保留最新60个）"""
```

#### 2.2 备份文件结构

```
backups/
├── dim_device_capabilities/
│   ├── dim_device_capabilities_v1_20250119_120000.sql
│   ├── dim_device_capabilities_v2_20250119_130000.sql
│   └── ...
├── dim_metric_config/
│   ├── dim_metric_config_v1_20250119_120000.sql
│   └── ...
└── ...（17个表，每个表一个目录）
```

#### 2.3 SQL备份格式

```sql
-- 备份表: dim_metric_config
-- 版本: v1
-- 时间: 2025-01-19 12:00:00
-- 行数: 25

INSERT INTO dim_metric_config (
    metric_key, unit, unit_display, decimals_policy, 
    fixed_decimals, value_type, valid_min, valid_max
) VALUES
    ('pump_flow_rate', 'm³/h', 'm³/h', 'auto', 2, 'float', 0, 1000),
    ...
ON CONFLICT (metric_key) DO UPDATE SET
    unit = EXCLUDED.unit,
    unit_display = EXCLUDED.unit_display,
    ...
    updated_at = CURRENT_TIMESTAMP;
```

#### 2.4 变化检测策略

- 检查行数是否变化
- 如果行数相同，计算整表数据的MD5
- 只有MD5不同才备份

**涉及的函数/类**：
- `BackupManager` 类（新建）
- `backup_tables()` 方法
- `restore_table()` 方法
- `_table_has_changed()` 方法
- `_generate_sql_backup()` 方法
- `_get_next_version()` 方法
- `_cleanup_old_versions()` 方法

**依赖关系**：
- 任务3、任务4 依赖此任务
- 任务7 需要在此任务之后执行

**验证方法**：
- 检查备份文件是否正确生成
- 检查版本管理是否正常工作
- 检查增量备份是否正确
- 检查恢复功能是否正常

---

### 任务3：修复 dim_metric_config 恢复逻辑 🔧

**文件**：`app/services/ingest/prepare_dim/__init__.py`

**当前问题**：
- 从SQL文件重新加载（`_reload_metric_config_from_sql()`）
- 会丢失用户手动修改的数据

**目标**：
- 从备份恢复（使用任务2的 BackupManager）

**具体更改**：

#### 3.1 删除 `_reload_metric_config_from_sql()` 函数调用

**位置**：line 1272

**原代码**：
```python
# 重新导入 dim_metric_config 表数据
_reload_metric_config_from_sql(cur, settings)
```

**新代码**：
```python
# 恢复 dim_metric_config（从备份）
backup_manager.restore_table(cur, "dim_metric_config")
```

#### 3.2 删除 `_reload_metric_config_from_sql()` 函数定义

**位置**：lines 66-116

**操作**：完全删除此函数（废弃代码）

**涉及的函数/类**：
- `prepare_dim()` 函数
- `_reload_metric_config_from_sql()` 函数（删除）

**依赖关系**：
- 依赖任务2（BackupManager）

**验证方法**：
- 检查 dim_metric_config 是否从备份恢复
- 检查用户手动修改的数据是否保留

---

### 任务4：扩展配置表备份和恢复 🔧

**文件**：`app/services/ingest/prepare_dim/__init__.py`

**当前问题**：
- 只备份和恢复2个表（dim_device_capabilities, dim_metric_metadata_override）
- 需要扩展到10个配置表

**目标**：
- 备份和恢复10个配置表

**具体更改**：

#### 4.1 替换 `_backup_manual_tables()` 调用

**位置**：line 1255

**原代码**：
```python
backup_data = _backup_manual_tables(cur)
```

**新代码**：
```python
backup_manager = BackupManager()
backup_result = backup_manager.backup_tables(cur, TABLES_TO_BACKUP)
```

#### 4.2 替换 `_restore_manual_tables()` 调用

**位置**：line 1365

**原代码**：
```python
_restore_manual_tables(cur, backup_data)
```

**新代码**：
```python
config_tables = [
    "dim_device_capabilities",
    "dim_metric_metadata_override",
    "pump_characteristic_curves",
    "quality_code_dict",
    "calculation_validation_config",
    "metric_capability_policy",
    "calculation_parameters",
    "device_rated_params",
    "calculation_method_registry",
    "metric_calculation_order",
]
for table in config_tables:
    backup_manager.restore_table(cur, table)
```

#### 4.3 删除 `_backup_manual_tables()` 和 `_restore_manual_tables()` 函数

**位置**：lines 305-498

**操作**：完全删除这两个函数（废弃代码）

#### 4.4 删除 `_rebuild_config_tables()` 调用

**位置**：line 1370

**原因**：配置表已经从备份恢复，不需要重建

**注意**：metric_calculation_order 从备份恢复（用户确认方案A）

**涉及的函数/类**：
- `prepare_dim()` 函数
- `_backup_manual_tables()` 函数（删除）
- `_restore_manual_tables()` 函数（删除）
- `_rebuild_config_tables()` 函数（保留，但不调用）

**依赖关系**：
- 依赖任务2（BackupManager）

**验证方法**：
- 检查10个配置表是否正确恢复
- 检查 metric_calculation_order 是否从备份恢复

---

### 任务5：补全计算方法注册表 📊

**文件**：`scripts/sql/calculation/init_methods_补充.sql`（新建）

**当前问题**：
- 25个方法已实现，11个已注册，14个未注册

**目标**：
- 注册所有25个计算方法到 calculation_method_registry 表

**具体更改**：

#### 5.1 创建新的SQL文件

**文件名**：`scripts/sql/calculation/init_methods_补充.sql`

**内容**：14个缺失方法的注册SQL

**缺失的14个方法**：
1. pump_head: HEAD_COEF_V1
2. pump_efficiency: EFF_SIMPLE_V1
3. pump_speed: method_a, method_b, method_c
4. pump_torque: method_a, method_b
5. main_pipeline_outlet_pressure: method_a, method_b, method_c
6. main_pipeline_inlet_pressure: PIN_COEF_V1
7. pump_cumulative_flow: method_a, method_b

#### 5.2 SQL模板

```sql
-- pump_head: HEAD_COEF_V1
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'HEAD_COEF_V1',
    'pump_head',
    '扬程系数化方法',
    'HEAD_COEF_V1',
    110,
    ARRAY['pump_outlet_pressure', 'pool_liquid_level', 'pump_flow_rate', 'main_pipeline_flow_rate'],
    '{"description": "基于系数的扬程计算"}'::jsonb,
    'docs/计算原理和公式.md#pump_head',
    'high',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = CURRENT_TIMESTAMP;

-- ... 其他13个方法 ...
```

**涉及的函数/类**：
- 无（纯SQL脚本）

**依赖关系**：
- 独立任务，不依赖其他任务

**验证方法**：
- 执行SQL脚本
- 查询 calculation_method_registry 表，确认25个方法都已注册
- 检查 CALCULATOR_REGISTRY 中的 method_id 是否与数据库一致

---

### 任务6：修复配置表初始化 🔧

**文件**：`app/services/ingest/prepare_dim/__init__.py`

**当前问题**：
- 无错误处理
- 无路径验证
- 无结果验证
- 无返回值

**目标**：
- 添加错误处理和验证
- 返回执行结果

**具体更改**：

#### 6.1 修改函数签名

**原签名**：
```python
def _rebuild_config_tables(settings: Settings, cur) -> None:
```

**新签名**：
```python
def _rebuild_config_tables(settings: Settings, cur) -> Dict[str, Any]:
```

#### 6.2 添加错误处理和验证

**示例**：
```python
result = {}

# 1. 重建 calculation_method_registry
try:
    sql_file = Path("scripts/sql/calculation/init_methods.sql")
    if not sql_file.exists():
        raise FileNotFoundError(f"SQL文件不存在: {sql_file}")
    
    sql_content = sql_file.read_text(encoding="utf-8")
    cur.execute(sql_content)
    
    # 验证结果
    cur.execute("SELECT COUNT(*) FROM calculation_method_registry")
    row_count = cur.fetchone()[0]
    
    if row_count == 0:
        raise ValueError("calculation_method_registry 表为空")
    
    result["calculation_method_registry"] = {"status": "ok", "rows": row_count}
    _act.info(f"[重建配置表] calculation_method_registry 已重建：{row_count}行")
    
except Exception as e:
    result["calculation_method_registry"] = {"status": "error", "error": str(e)}
    _act.error(f"[重建配置表] calculation_method_registry 重建失败: {e}")
    raise  # 抛出异常中断流程

# 2-4. 类似处理其他表...

return result
```

**涉及的函数/类**：
- `_rebuild_config_tables()` 函数

**依赖关系**：
- 独立任务，不依赖其他任务

**验证方法**：
- 检查函数是否返回正确的结果字典
- 检查错误处理是否正常工作
- 检查验证逻辑是否正确

---

### 任务7：废除旧清空逻辑，创建新清空逻辑 ⚠️

**文件**：`app/services/ingest/prepare_dim/__init__.py`

**当前问题**：
- `_clear_dependent_tables()` 函数错误地清空了很多在备份列表中的表
- 这是严重问题，必须完全废除

**目标**：
- 完全删除 `_clear_dependent_tables()` 函数
- 创建新函数 `_clear_non_backup_tables()`，只清空不在备份列表中的表

**具体更改**：

#### 7.1 删除 `_clear_dependent_tables()` 函数

**位置**：lines 500-581

**操作**：完全删除此函数（废弃代码）

#### 7.2 创建 `_clear_non_backup_tables()` 函数

**函数签名**：
```python
def _clear_non_backup_tables(cur) -> int:
    """
    清空不在备份列表中的表
    
    只清空以下表：
    - fact_measurements（所有历史数据）
    - completion_runs, completion_steps（审计数据）
    - dim_devices（设备维度表）
    - dim_stations（站点维度表）
    - dim_mapping_items（映射表）
    
    不清空备份列表中的17个表。
    
    Returns:
        清空的总行数
    """
```

**清空顺序**（避免外键约束冲突）：
1. fact_measurements（叶子节点）
2. completion_runs, completion_steps（叶子节点）
3. dim_devices（依赖 dim_stations）
4. dim_stations（根节点）
5. dim_mapping_items（叶子节点）

**不应该清空的表**（17个备份表）：
- dim_device_capabilities
- dim_metric_metadata_override
- pump_characteristic_curves
- quality_code_dict
- calculation_validation_config
- metric_capability_policy
- calculation_parameters
- device_rated_params
- calculation_method_registry
- metric_calculation_order
- dim_metric_config
- metric_rule_auto_baseline
- metric_rule_auto_baseline_shadow
- metric_quality_rules
- metric_quality_rules_shadow
- device_running_thresholds
- device_running_thresholds_shadow

#### 7.3 更新 `prepare_dim()` 函数调用

**位置**：line 1262

**原代码**：
```python
total_deleted = _clear_dependent_tables(cur)
```

**新代码**：
```python
total_deleted = _clear_non_backup_tables(cur)
```

**涉及的函数/类**：
- `_clear_dependent_tables()` 函数（删除）
- `_clear_non_backup_tables()` 函数（新建）
- `prepare_dim()` 函数

**依赖关系**：
- 应该在任务2之后执行（确保备份系统已实现）

**验证方法**：
- 检查只清空了5个表（fact_measurements, completion_runs, completion_steps, dim_devices, dim_stations, dim_mapping_items）
- 检查17个备份表没有被清空
- 检查清空顺序是否正确（避免外键约束冲突）

---

## 📋 实施检查清单

### 任务1：修复 run_all 流程执行顺序（4项）
- [ ] 1.1 打开 `app/services/run_all/orchestrator.py`，查看 calculation 代码块（lines 438-638）
- [ ] 1.2 使用 str-replace-editor 移动 calculation 代码块到 presence 之后（line 1385+）
- [ ] 1.3 更新步骤编号注释（7→9, 8→7, 9→8）
- [ ] 1.4 验证修改：检查代码块是否完整移动，无重复或遗漏

### 任务2：实现完整的备份系统（7项）
- [ ] 2.1 创建 `app/services/ingest/prepare_dim/backup.py` 文件
- [ ] 2.2 实现 `BackupManager` 类和 `backup_tables()` 方法
- [ ] 2.3 实现 `_generate_sql_backup()` 方法（生成SQL INSERT语句）
- [ ] 2.4 实现 `_table_has_changed()` 方法（检测表变化：行数 + MD5）
- [ ] 2.5 实现 `_get_next_version()` 方法（获取下一个版本号）
- [ ] 2.6 实现 `_cleanup_old_versions()` 方法（清理旧版本，保留60个）
- [ ] 2.7 实现 `restore_table()` 方法（从备份恢复表数据）

### 任务3：修复 dim_metric_config 恢复逻辑（2项）
- [ ] 3.1 删除 `_reload_metric_config_from_sql()` 函数定义（lines 66-116）
- [ ] 3.2 修改 `prepare_dim()` 函数，使用 `backup_manager.restore_table()` 恢复 dim_metric_config（line 1272）

### 任务4：扩展配置表备份和恢复（4项）
- [ ] 4.1 删除 `_backup_manual_tables()` 函数定义（lines 305-355）
- [ ] 4.2 删除 `_restore_manual_tables()` 函数定义（lines 358-498）
- [ ] 4.3 修改 `prepare_dim()` 函数，使用 `backup_manager.backup_tables()` 备份17个表（line 1255）
- [ ] 4.4 修改 `prepare_dim()` 函数，使用 `backup_manager.restore_table()` 恢复10个配置表（line 1365）

### 任务5：补全计算方法注册表（3项）
- [ ] 5.1 创建 `scripts/sql/calculation/init_methods_补充.sql` 文件
- [ ] 5.2 添加14个缺失方法的注册SQL
- [ ] 5.3 验证SQL脚本：执行并检查 calculation_method_registry 表是否有25个方法

### 任务6：修复配置表初始化（3项）
- [ ] 6.1 修改 `_rebuild_config_tables()` 函数签名，添加返回值 `-> Dict[str, Any]`
- [ ] 6.2 为每个表添加错误处理、路径验证、结果验证
- [ ] 6.3 验证修改：检查函数是否返回正确的结果字典

### 任务7：废除旧清空逻辑，创建新清空逻辑（4项）
- [ ] 7.1 删除 `_clear_dependent_tables()` 函数定义（lines 500-581）
- [ ] 7.2 创建 `_clear_non_backup_tables()` 函数（只清空5个表）
- [ ] 7.3 修改 `prepare_dim()` 函数，调用 `_clear_non_backup_tables()`（line 1262）
- [ ] 7.4 验证修改：检查只清空了5个表，17个备份表没有被清空

**总计**：27个检查清单项

---

## ✅ 验证计划

### 功能验证
1. 运行 prepare_dim(stage=1)，检查备份是否正确生成
2. 运行 prepare_dim(stage=1)，检查配置表是否正确恢复
3. 运行 prepare_dim(stage=2)，检查规则表是否正确生成
4. 运行 run_all 流程，检查执行顺序是否正确

### 数据完整性验证
1. 检查备份文件是否包含所有数据
2. 检查恢复后的数据是否与备份一致
3. 检查17个备份表是否没有被清空
4. 检查 calculation_method_registry 表是否有25个方法

### 性能验证
1. 检查备份过程的耗时
2. 检查恢复过程的耗时
3. 检查增量备份是否正常工作

---

## ⚠️ 风险评估

### 风险1：备份文件占用大量磁盘空间
- **缓解措施**：自动清理旧版本（保留60个）；增量备份
- **监控**：监控备份目录大小

### 风险2：恢复过程可能失败
- **缓解措施**：使用 `ON CONFLICT DO UPDATE` 实现幂等性；在事务中执行恢复
- **验证**：验证恢复后的行数

### 风险3：清空顺序错误导致外键约束冲突
- **缓解措施**：按依赖顺序清空（从叶子到根）；使用 `DELETE` 而非 `TRUNCATE`
- **验证**：测试清空逻辑

---

**文档结束**

