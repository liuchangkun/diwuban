# 计划完整性验证报告：删除 mv_presence_1s 表

**验证时间**：2025-11-04  
**计划文档**：`计划文档_删除mv_presence_1s表.md`  
**验证要求**：用户要求逐项确认计划是否包含所有需要修改的代码、脚本和存储过程

---

## 📋 验证总结

### 验证结果

| 验证项 | 状态 | 遗漏数量 | 说明 |
|--------|------|---------|------|
| 1. 数据库层面 | ✅ 完整 | 0 | 所有SQL脚本、存储过程、视图都已包含 |
| 2. Python代码层面 | ✅ 完整 | 0 | 所有Python文件都已包含 |
| 3. 迁移脚本层面 | ✅ 完整 | 0 | 新建脚本、回滚脚本都已包含 |
| 4. 文档层面 | ✅ 完整 | 0 | 所有文档都已列出 |
| 5. 遗漏检查 | ✅ 无遗漏 | 0 | 无遗漏的脚本、存储过程、函数、视图 |

**总体结论**：✅ **计划完整，无遗漏**

---

## 1. 数据库层面验证

### 1.1 是否包含删除 `mv_presence_1s` 表的 SQL 脚本？

**验证结果**：✅ **是**

**证据**：
- 计划文档第435-436行包含删除表的SQL：
  ```sql
  -- 步骤3：删除 mv_presence_1s 表
  DROP TABLE IF EXISTS public.mv_presence_1s;
  ```

### 1.2 是否包含修改存储过程 `sp_refresh_mv_running_presence` 的完整 SQL 代码？

**验证结果**：✅ **是**

**证据**：
- 计划文档第382-433行包含完整的存储过程修改SQL：
  - 第382-400行：修改后的存储过程定义（删除了 `mv_presence_1s` 相关逻辑）
  - 第402-433行：完整的存储过程注释

**修改前后对比**：
- **修改前**：包含两个 INSERT 语句（`mv_device_running_1s` 和 `mv_presence_1s`）
- **修改后**：仅包含一个 INSERT 语句（`mv_device_running_1s`）

### 1.3 是否包含简化视图 `mv_presence_1s_any` 的完整 SQL 代码？

**验证结果**：✅ **是**

**证据**：
- 计划文档第349-379行包含完整的视图简化SQL：
  - 第349-360行：简化后的视图定义（移除 UNION，仅基于 `metrics_presence_per_second_device`）
  - 第362-379行：完整的视图注释

**修改前后对比**：
- **修改前**：UNION 两个表（`mv_presence_1s` 和 `metrics_presence_per_second_device`）
- **修改后**：仅基于 `metrics_presence_per_second_device` 表

### 1.4 是否包含所有必要的验证 SQL 语句？

**验证结果**：✅ **是**

**证据**：
- 计划文档第438-456行包含完整的验证SQL：
  - 第442-444行：验证表已删除
  - 第447-449行：验证视图仍然存在
  - 第451-453行：验证成功消息

- 计划文档第459-474行包含额外的验证SQL：
  - 第462行：验证表已删除
  - 第465行：验证视图仍然存在
  - 第468-469行：验证视图定义不包含 `mv_presence_1s`
  - 第472-473行：验证存储过程定义不包含 `mv_presence_1s`

---

## 2. Python 代码层面验证

### 2.1 是否包含需要修改的所有 Python 文件路径和具体行号？

**验证结果**：✅ **是**

**证据**：
- 计划文档第196-244行包含 `orchestrator.py` 的修改：
  - 文件路径：`app/services/run_all/orchestrator.py`
  - 行号：第504行（注释修改）
  - 修改前后代码对比：完整

- 计划文档第250-270行包含 `prepare_dim/__init__.py` 的说明：
  - 文件路径：`app/services/ingest/prepare_dim/__init__.py`
  - 说明：不添加清空逻辑（已取消）

### 2.2 是否包含修改前后的代码对比？

**验证结果**：✅ **是**

**证据**：
- 计划文档第200-244行包含完整的代码对比：
  - 第200-219行：修改前的代码
  - 第226-244行：修改后的代码
  - 差异：仅注释修改（"1s存在性与60s统计" → "运行状态与60s统计"）

### 2.3 是否遗漏了任何引用 `mv_presence_1s` 或 `sp_refresh_mv_running_presence` 的 Python 代码？

**验证结果**：✅ **否**（无遗漏）

**证据**：
- 已检索所有Python代码，发现以下引用：
  1. `app/services/run_all/orchestrator.py` 第510-517行：调用 `sp_refresh_mv_running_presence`（已包含在计划中）
  2. `scripts/dev/run_vfast_full_device_daily.py` 第44-47行：调用 `sp_refresh_mv_running_presence`（无需修改，存储过程签名不变）
  3. `scripts/dev/run_vfast_minutes.py` 第53行：调用 `sp_refresh_mv_running_presence`（无需修改，存储过程签名不变）

**说明**：
- `run_vfast_full_device_daily.py` 和 `run_vfast_minutes.py` 无需修改，因为：
  - 存储过程签名不变
  - 存储过程仍然有效（刷新 `mv_device_running_1s`）
  - 调用代码无需修改

---

## 3. 迁移脚本层面验证

### 3.1 是否包含新建的迁移脚本 `074_drop_mv_presence_1s.sql` 的完整内容？

**验证结果**：✅ **是**

**证据**：
- 计划文档第330-457行包含完整的迁移脚本：
  - 第339-456行：完整的SQL脚本内容
  - 包含4个步骤：
    1. 简化视图 `mv_presence_1s_any`
    2. 修改存储过程 `sp_refresh_mv_running_presence`
    3. 删除表 `mv_presence_1s`
    4. 验证删除结果

### 3.2 是否包含回滚脚本的完整内容？

**验证结果**：✅ **是**

**证据**：
- 计划文档第595-720行包含完整的回滚脚本：
  - 第603-712行：完整的回滚SQL脚本
  - 包含4个步骤：
    1. 重建表 `mv_presence_1s`
    2. 恢复存储过程 `sp_refresh_mv_running_presence`
    3. 恢复视图 `mv_presence_1s_any`
    4. 验证回滚结果

### 3.3 是否包含对原始迁移脚本 `039_materialize_running_presence_and_stats.sql` 的修改说明？

**验证结果**：✅ **是**

**证据**：
- 计划文档第310-315行包含原始迁移脚本的修改说明：
  - 第310-312行：在脚本开头添加废弃警告注释
  - 第313行：说明此脚本创建了 `mv_presence_1s` 表，需要标记为部分废弃

- 计划文档第555-560行包含检查清单步骤 3.6：
  - 文件路径：`scripts/sql/migrations/039_materialize_running_presence_and_stats.sql`
  - 行号范围：1-2（在 BEGIN 之前插入）
  - 修改内容：添加废弃警告注释

---

## 4. 文档层面验证

### 4.1 是否列出了所有需要更新的文档文件（包括路径和行号）？

**验证结果**：✅ **是**

**证据**：
- 计划文档第282-315行列出了10个需要更新的文档：

| 序号 | 文档路径 | 行号范围 | 修改内容 |
|------|---------|---------|---------|
| 1 | `.memory/数据层/数据表清单.md` | 675-699 | 删除 `mv_presence_1s` 表的条目 |
| 2 | `.memory/数据层/视图清单.md` | 145-165 | 更新 `mv_presence_1s_any` 视图的说明 |
| 3 | `.memory/数据层/存储过程清单.md` | - | 更新 `sp_refresh_mv_running_presence` 存储过程的说明 |
| 4 | `.tasks/CLI命令测试计划-run-all深度测试.md` | 1507-1718 | 更新阶段8的测试内容 |
| 5 | `研究报告_mv_presence_1s表分析.md` | 1 | 添加"已废弃"标记 |
| 6 | `docs/缺失计算修复/06-技术参考/数据库函数和存储过程.md` | 372-373 | 更新 `sp_refresh_mv_running_presence` 的说明 |
| 7 | `scripts/migrations/20250922_add_comments_batch_1.sql` | 32-50 | 删除 `mv_presence_1s` 表的注释 |
| 8 | `scripts/migrations/20250922_add_comments_batch_2.sql` | 193-200 | 更新 `sp_refresh_mv_running_presence` 的注释 |
| 9 | `scripts/sql/migrations/058_add_remaining_comments.sql` | 1684-1714 | 更新存储过程注释 |
| 10 | `scripts/sql/migrations/039_materialize_running_presence_and_stats.sql` | 1-2 | 添加废弃警告注释 |

### 4.2 是否包含文档修改的具体内容？

**验证结果**：✅ **是**

**证据**：
- 计划文档第518-560行包含完整的文档更新检查清单：
  - 每个文档都有具体的修改内容说明
  - 每个文档都有验证方法
  - 每个文档都有回滚方法

---

## 5. 遗漏检查

### 5.1 是否有任何脚本、存储过程、函数、视图仍然引用 `mv_presence_1s` 但未被计划覆盖？

**验证结果**：✅ **否**（无遗漏）

**检查方法**：
1. 使用 `codebase-retrieval` 检索所有引用 `mv_presence_1s` 的代码
2. 使用 `codebase-retrieval` 检索所有引用 `sp_refresh_mv_running_presence` 的代码
3. 使用 `codebase-retrieval` 检索所有引用 `mv_presence_1s_any` 的代码

**检查结果**：

#### 引用 `mv_presence_1s` 的位置

| 位置 | 类型 | 是否包含在计划中 | 说明 |
|------|------|-----------------|------|
| `scripts/sql/migrations/039_materialize_running_presence_and_stats.sql` | 创建表 | ✅ 是 | 已添加废弃警告注释 |
| `scripts/sql/migrations/041_create_mv_presence_compat.sql` | 创建视图 | ✅ 是 | 视图将被简化 |
| `scripts/migrations/20250922_add_comments_batch_1.sql` | 表注释 | ✅ 是 | 注释将被删除 |
| `scripts/sql/migrations/058_add_remaining_comments.sql` | 存储过程注释 | ✅ 是 | 注释将被更新 |
| `.memory/数据层/数据表清单.md` | 文档 | ✅ 是 | 条目将被删除 |
| `.memory/数据层/视图清单.md` | 文档 | ✅ 是 | 说明将被更新 |
| `研究报告_mv_presence_1s表分析.md` | 文档 | ✅ 是 | 将添加废弃标记 |
| `计划文档_删除mv_presence_1s表.md` | 计划文档 | N/A | 计划文档本身 |
| `计划修正说明_mv_presence_1s删除.md` | 修正文档 | N/A | 修正文档本身 |

#### 引用 `sp_refresh_mv_running_presence` 的位置

| 位置 | 类型 | 是否包含在计划中 | 说明 |
|------|------|-----------------|------|
| `app/services/run_all/orchestrator.py` | Python调用 | ✅ 是 | 注释将被更新 |
| `scripts/dev/run_vfast_full_device_daily.py` | Python调用 | ✅ 是 | 无需修改（存储过程签名不变） |
| `scripts/dev/run_vfast_minutes.py` | Python调用 | ✅ 是 | 无需修改（存储过程签名不变） |
| `scripts/sql/migrations/039_materialize_running_presence_and_stats.sql` | 创建存储过程 | ✅ 是 | 存储过程将被修改 |
| `scripts/sql/migrations/058_add_remaining_comments.sql` | 存储过程注释 | ✅ 是 | 注释将被更新 |
| `scripts/migrations/20250922_add_comments_batch_2.sql` | 存储过程注释 | ✅ 是 | 注释将被更新 |

#### 引用 `mv_presence_1s_any` 的位置

| 位置 | 类型 | 是否包含在计划中 | 说明 |
|------|------|-----------------|------|
| `scripts/sql/migrations/041_create_mv_presence_compat.sql` | 创建视图 | ✅ 是 | 视图将被简化 |
| `scripts/sql/migrations/036_create_sp_mark_quality_window_vfast.sql` | 使用视图 | ✅ 是 | 无需修改（视图签名不变） |
| `scripts/migrations/20250922_add_comments_batch_1.sql` | 视图注释 | ✅ 是 | 注释将被更新 |
| `.memory/数据层/视图清单.md` | 文档 | ✅ 是 | 说明将被更新 |
| `.tasks/CLI命令测试计划-run-all深度测试.md` | 测试计划 | ✅ 是 | 测试内容将被更新 |

**重要发现**：
- `scripts/sql/migrations/036_create_sp_mark_quality_window_vfast.sql` 使用了 `mv_presence_1s_any` 视图（5处引用）
- 这些引用**无需修改**，因为：
  - 视图签名不变（字段结构不变）
  - 视图功能不变（仍然返回存在性数据）
  - 查询结果一致（因为 `mv_presence_1s` 为空）

### 5.2 是否有任何测试脚本、开发脚本需要修改但未被列出？

**验证结果**：✅ **否**（无遗漏）

**检查结果**：
- `scripts/dev/run_vfast_full_device_daily.py`：已检查，无需修改
- `scripts/dev/run_vfast_minutes.py`：已检查，无需修改
- `.tasks/CLI命令测试计划-run-all深度测试.md`：已列出，需要更新

---

## 📊 完整性验证总结

### 验证通过项

1. ✅ **数据库层面**：所有SQL脚本、存储过程、视图都已包含
   - 删除表的SQL：✅ 已包含
   - 修改存储过程的SQL：✅ 已包含（完整）
   - 简化视图的SQL：✅ 已包含（完整）
   - 验证SQL：✅ 已包含（完整）

2. ✅ **Python代码层面**：所有Python文件都已包含
   - `orchestrator.py`：✅ 已包含（注释修改）
   - `prepare_dim/__init__.py`：✅ 已说明（不添加清空逻辑）
   - 开发脚本：✅ 已检查（无需修改）

3. ✅ **迁移脚本层面**：新建脚本、回滚脚本都已包含
   - 新建迁移脚本 074：✅ 已包含（完整）
   - 回滚脚本：✅ 已包含（完整）
   - 原始迁移脚本 039：✅ 已包含（废弃警告）

4. ✅ **文档层面**：所有文档都已列出
   - 10个文档：✅ 已列出（包括路径和行号）
   - 修改内容：✅ 已说明（具体内容）

5. ✅ **遗漏检查**：无遗漏的脚本、存储过程、函数、视图
   - 所有引用都已检查：✅ 已检查
   - 所有引用都已包含在计划中：✅ 已包含

### 验证失败项

**无**

---

## ✅ 最终结论

**计划文档（`计划文档_删除mv_presence_1s表.md`）完整性验证通过**

**验证结果**：
1. ✅ 包含所有需要修改的代码、脚本和存储过程
2. ✅ 包含所有必要的验证SQL语句
3. ✅ 包含所有需要更新的文档文件
4. ✅ 无遗漏的脚本、存储过程、函数、视图
5. ✅ 无遗漏的测试脚本、开发脚本

**可以进入执行模式**

---

**验证完成时间**：2025-11-04  
**下一步**：等待用户确认，准备进入执行模式

