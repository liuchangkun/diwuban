# 删除 device_metric_candidates 表 - 技术规范

**创建日期**: 2025-01-17  
**创建者**: AI Agent  
**任务类型**: 数据库表删除  
**优先级**: P2 - 中等优先级  
**预计耗时**: 30分钟

---

## 📋 任务概述

### 目标
完全删除未使用的 `device_metric_candidates` 表及其所有相关文件和文档引用。

### 背景
- 该表设计用于存储设备指标候选列表以优化计算性能
- 实际从未被使用（3个月，48个备份版本，全部为空）
- 已被 `metric_capability_policy` 表 + 动态查询机制替代
- 无外键依赖，无代码引用，删除风险极低

### 影响范围
- **数据库**: 删除1个表（无数据丢失风险）
- **代码文件**: 删除1个SQL脚本
- **迁移脚本**: 清理6个脚本中的外键约束代码
- **文档**: 更新2个文档
- **备份文件**: 删除48个备份文件

---

## 🎯 执行计划

### 步骤1: 删除数据库表

**SQL语句**:
```sql
-- 检查表是否存在
SELECT to_regclass('public.device_metric_candidates');

-- 删除表（包含级联删除外键约束）
DROP TABLE IF EXISTS public.device_metric_candidates CASCADE;

-- 验证删除成功
SELECT to_regclass('public.device_metric_candidates');  -- 应返回 NULL
```

**验证点**:
- [ ] 表已不存在
- [ ] 无错误信息
- [ ] 外键约束已自动删除

---

### 步骤2: 删除创建脚本

**文件路径**: `scripts/sql/ts_candidates.sql`

**操作**: 完全删除该文件

**验证点**:
- [ ] 文件已删除
- [ ] 无其他脚本引用此文件

---

### 步骤3: 清理迁移脚本中的外键约束代码

**需要修改的文件**:

1. `scripts/sql/validation/P0_add_foreign_keys_to_config_tables.sql`
   - 删除行 179-185（device_metric_candidates 外键添加代码）

2. `scripts/sql/validation/P1_add_foreign_keys_quality_rules.sql`
   - 删除行 179-189（device_metric_candidates 外键添加代码）

3. `scripts/sql/validation/P1_add_foreign_keys_comprehensive.sql`
   - 删除相关的 device_metric_candidates 外键添加代码

4. `scripts/sql/migrations/060_add_foreign_key_constraint.sql`
   - 该文件主要针对 device_running_thresholds，无需修改

5. `docs/缺失计算修复1/04-完整依赖关系深度分析报告.md`
   - 删除行 611（device_metric_candidates 外键建议）

6. `docs/缺失计算修复/03-修复方案/方案7-外键约束级联更新.md`
   - 删除相关的 device_metric_candidates 外键建议

**验证点**:
- [ ] 所有迁移脚本中不再包含 device_metric_candidates 引用
- [ ] 脚本语法正确（无孤立的注释或代码块）

---

### 步骤4: 更新文档

**文件1**: `.memory/数据层/数据表清单.md`
- 删除行 865-889（device_metric_candidates 表的完整章节）
- 更新行 1251（从设备配置表列表中删除）
- 更新行 1288（从设备和指标配置表列表中删除）

**文件2**: `.tasks/数据库表使用情况调查报告-20250117.md`
- 删除行 77-110（device_metric_candidates 调查章节）

**验证点**:
- [ ] 文档中不再包含 device_metric_candidates 引用
- [ ] 文档格式正确（标题层级、列表编号）

---

### 步骤5: 清理备份文件

**目录路径**: `backups/device_metric_candidates/`

**操作**: 删除整个目录（包含48个备份文件）

**验证点**:
- [ ] 目录已删除
- [ ] 无其他备份脚本引用此目录

---

## ✅ 检查清单

### 执行前检查
- [x] 已确认表无外键依赖
- [x] 已确认表无代码引用
- [x] 已确认表为空（无数据丢失风险）
- [x] 已确认有替代机制（metric_capability_policy）
- [x] 已读取所有规范文档

### 执行中检查
- [ ] 数据库表删除成功
- [ ] 创建脚本删除成功
- [ ] 迁移脚本清理完成
- [ ] 文档更新完成
- [ ] 备份文件清理完成

### 执行后验证
- [ ] 数据库中不存在 device_metric_candidates 表
- [ ] 代码库中无 device_metric_candidates 引用
- [ ] 所有迁移脚本语法正确
- [ ] 文档格式正确

---

## 🔄 回滚方案

如需回滚，执行以下步骤：

1. **恢复表结构**:
```sql
CREATE TABLE IF NOT EXISTS public.device_metric_candidates (
  device_id bigint PRIMARY KEY,
  metrics   text[] NOT NULL
);

COMMENT ON TABLE public.device_metric_candidates IS '设备指标候选表，存储设备可能具有的指标列表';
COMMENT ON COLUMN public.device_metric_candidates.device_id IS '设备ID（外键）';
COMMENT ON COLUMN public.device_metric_candidates.metrics IS '指标键数组（如：[''flow_rate'', ''pressure'', ''power'']）';
```

2. **恢复外键约束**:
```sql
ALTER TABLE device_metric_candidates
ADD CONSTRAINT device_metric_candidates_device_id_fkey
FOREIGN KEY (device_id) REFERENCES dim_devices(id)
ON UPDATE CASCADE ON DELETE CASCADE;
```

3. **恢复文件**: 从Git历史恢复删除的文件

---

## 📊 风险评估

| 风险项 | 风险等级 | 缓解措施 |
|--------|---------|---------|
| 数据丢失 | 🟢 极低 | 表为空，无数据 |
| 功能影响 | 🟢 极低 | 无代码引用 |
| 依赖破坏 | 🟢 极低 | 无外键依赖 |
| 回滚困难 | 🟢 极低 | 表结构简单，易恢复 |

**总体风险**: 🟢 **极低** - 可安全执行

---

## 📝 详细文件修改清单

### 数据库操作

**操作类型**: 执行SQL
**工具**: PostgreSQL客户端或 `query_PostgreSQL` 工具

```sql
-- 步骤1: 验证表当前状态
SELECT
  schemaname,
  tablename,
  tableowner
FROM pg_tables
WHERE tablename = 'device_metric_candidates';

-- 步骤2: 检查外键依赖
SELECT
  tc.table_name AS referencing_table,
  kcu.column_name AS referencing_column,
  ccu.table_name AS referenced_table,
  ccu.column_name AS referenced_column
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND ccu.table_name = 'device_metric_candidates';

-- 步骤3: 删除表
DROP TABLE IF EXISTS public.device_metric_candidates CASCADE;

-- 步骤4: 验证删除成功
SELECT to_regclass('public.device_metric_candidates');  -- 应返回 NULL
```

---

### 文件删除清单

| 文件路径 | 操作 | 工具 |
|---------|------|------|
| `scripts/sql/ts_candidates.sql` | 完全删除 | `remove-files` |
| `backups/device_metric_candidates/` | 删除目录 | `remove-files` |

---

### 文件修改清单

#### 文件1: `scripts/sql/validation/P0_add_foreign_keys_to_config_tables.sql`

**修改位置**: 行 179-185
**修改类型**: 删除代码块
**删除内容**:
```sql
-- device_metric_candidates
ALTER TABLE device_metric_candidates
ADD CONSTRAINT device_metric_candidates_device_id_fkey
FOREIGN KEY (device_id) REFERENCES dim_devices(id)
ON UPDATE CASCADE ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_device_metric_candidates_device_id ON device_metric_candidates(device_id);
```

---

#### 文件2: `scripts/sql/validation/P1_add_foreign_keys_quality_rules.sql`

**修改位置**: 行 179-189
**修改类型**: 删除代码块
**删除内容**:
```sql
-- device_metric_candidates
ALTER TABLE device_metric_candidates
ADD CONSTRAINT device_metric_candidates_device_id_fkey
FOREIGN KEY (device_id) REFERENCES dim_devices(id)
ON UPDATE CASCADE ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_device_metric_candidates_device_id ON device_metric_candidates(device_id);
```

---

#### 文件3: `scripts/sql/validation/P1_add_foreign_keys_comprehensive.sql`

**修改位置**: 需要先查看文件确定具体行号
**修改类型**: 删除 device_metric_candidates 相关的外键约束代码
**搜索关键词**: `device_metric_candidates`

---

#### 文件4: `.memory/数据层/数据表清单.md`

**修改位置1**: 行 865-889
**修改类型**: 删除整个章节
**删除内容**: `### device_metric_candidates` 章节（包含表结构、字段说明、索引等）

**修改位置2**: 行 1251
**修改类型**: 从列表中删除
**删除内容**: `- device_metric_candidates`

**修改位置3**: 行 1288
**修改类型**: 从列表中删除
**删除内容**: `- device_metric_candidates`

---

#### 文件5: `.tasks/数据库表使用情况调查报告-20250117.md`

**修改位置**: 行 77-110
**修改类型**: 删除整个章节
**删除内容**: `### 2. device_metric_candidates` 章节

---

#### 文件6: `docs/缺失计算修复1/04-完整依赖关系深度分析报告.md`

**修改位置**: 行 611
**修改类型**: 删除示例行
**删除内容**: 包含 `device_metric_candidates` 的外键建议示例

---

#### 文件7: `docs/缺失计算修复/03-修复方案/方案7-外键约束级联更新.md`

**修改位置**: 需要先查看文件确定具体行号
**修改类型**: 删除 device_metric_candidates 相关的外键建议
**搜索关键词**: `device_metric_candidates`

---

## 🔍 验证步骤

### 数据库验证

```sql
-- 验证1: 表不存在
SELECT to_regclass('public.device_metric_candidates');
-- 预期结果: NULL

-- 验证2: 无外键约束残留
SELECT constraint_name
FROM information_schema.table_constraints
WHERE constraint_name LIKE '%device_metric_candidates%';
-- 预期结果: 0 rows

-- 验证3: 无索引残留
SELECT indexname
FROM pg_indexes
WHERE indexname LIKE '%device_metric_candidates%';
-- 预期结果: 0 rows
```

### 代码库验证

```bash
# 验证1: 无文件引用
grep -r "device_metric_candidates" scripts/sql/ --exclude-dir=_archive
# 预期结果: 无输出

# 验证2: 无文档引用
grep -r "device_metric_candidates" .memory/ --exclude-dir=_archive
# 预期结果: 无输出

# 验证3: 文件已删除
ls scripts/sql/ts_candidates.sql
# 预期结果: No such file or directory

# 验证4: 备份目录已删除
ls backups/device_metric_candidates/
# 预期结果: No such file or directory
```

---

## 📌 注意事项

1. **执行顺序**: 必须严格按照步骤1-5的顺序执行
2. **验证要求**: 每个步骤完成后必须执行验证
3. **错误处理**: 如遇错误立即停止，报告问题
4. **用户确认**: 每个步骤完成后请求用户确认
5. **禁止偏离**: 100%忠实执行本计划，任何修正必须报告

---

## 🎯 成功标准

- ✅ 数据库中不存在 device_metric_candidates 表
- ✅ 所有外键约束和索引已删除
- ✅ 创建脚本已删除
- ✅ 迁移脚本中无 device_metric_candidates 引用
- ✅ 文档中无 device_metric_candidates 引用
- ✅ 备份文件已清理
- ✅ 所有验证步骤通过

---

**文档结束 - 计划阶段完成**


