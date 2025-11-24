# 数据库迁移脚本

**项目**: pump_flow_rate 重构
**创建时间**: 2025-01-14
**最后更新**: 2025-11-15
**状态**: 部分已执行

---

## ⚠️ 重要说明

**calculation_logs 表已被废弃并删除**（2025-11-15）

用户明确表示文件日志已经足够，不需要数据库日志。因此：
- ✅ 已执行回滚脚本 `001_rollback_calculation_logs.sql`
- ✅ 已删除 calculation_logs 表及所有分区
- ✅ 已删除分区维护函数 `maintain_calculation_logs_partitions()`
- ❌ `001_create_calculation_logs.sql` 脚本已废弃，不应再执行

---

## 📋 迁移脚本列表

| 编号 | 脚本文件 | 说明 | 状态 |
|------|----------|------|------|
| 001 | `001_create_calculation_logs.sql` | 创建 calculation_logs 表（分区表） | ❌ 已废弃（2025-11-15） |
| 001-rollback | `001_rollback_calculation_logs.sql` | 删除 calculation_logs 表 | ✅ 已执行（2025-11-15） |
| 002 | `002_delete_garbage_parameters.sql` | 删除 f_thr 和 p_thr 参数 | ✅ 已执行（2025-01-14） |
| 003 | `003_verification_tests.sql` | 验证测试 | ✅ 已执行（2025-01-14） |
| 004 | `004_initialize_parameters.sql` | 初始化参数 | ✅ 已执行（2025-01-14） |

---

## 🚀 执行步骤

### 1. 执行迁移脚本 #001

**目的**: 创建 calculation_logs 表

**执行命令**:
```bash
# 方式1: 使用 psql 命令行
psql -h <host> -U <user> -d <database> -f 001_create_calculation_logs.sql

# 方式2: 使用 Python 脚本
python -m app.cli.database execute-migration --file migrations/001_create_calculation_logs.sql
```

**预期结果**:
- ✅ 创建 calculation_logs 表
- ✅ 创建 5 个索引
- ✅ 创建 30 个分区（今天 + 未来29天）
- ✅ 创建分区维护函数 maintain_calculation_logs_partitions()
- ✅ 输出验证信息

**验证命令**:
```sql
-- 验证表存在
SELECT COUNT(*) FROM pg_tables WHERE tablename = 'calculation_logs';
-- 预期结果: 1

-- 验证分区数量
SELECT COUNT(*) FROM pg_tables WHERE tablename LIKE 'calculation_logs_%';
-- 预期结果: 30

-- 验证索引
SELECT indexname FROM pg_indexes WHERE tablename = 'calculation_logs';
-- 预期结果: 5个索引

-- 验证函数
SELECT proname FROM pg_proc WHERE proname = 'maintain_calculation_logs_partitions';
-- 预期结果: 1
```

---

### 2. 回滚（如果需要）

**警告**: 回滚将删除所有日志数据！

**执行命令**:
```bash
psql -h <host> -U <user> -d <database> -f 001_rollback_calculation_logs.sql
```

---

## 📊 执行记录

### 迁移 #001-rollback（删除 calculation_logs 表）

- **执行时间**: 2025-11-15 01:25
- **执行人**: AI（RIPER-5 协议 - 执行模式）
- **执行命令**: `python scripts/dev/apply_sql.py "缺失指标计算改造/pump_flow_rate/migrations/001_rollback_calculation_logs.sql"`
- **执行结果**: ✅ 成功
- **验证结果**:
  - 主表数量: 0
  - 分区数量: 0
  - 函数数量: 0
- **备注**: 用户明确表示文件日志已足够，删除数据库日志表

### 迁移 #002（删除垃圾参数）

- **执行时间**: 2025-01-14
- **执行人**: AI
- **执行结果**: ✅ 成功
- **验证结果**: f_thr 和 p_thr 参数已删除
- **备注**: 移除硬编码阈值参数

### 迁移 #003（验证测试）

- **执行时间**: 2025-01-14
- **执行人**: AI
- **执行结果**: ✅ 成功
- **验证结果**: 所有验证测试通过
- **备注**: 验证数据库结构正确性

### 迁移 #004（初始化参数）

- **执行时间**: 2025-01-14
- **执行人**: AI
- **执行结果**: ✅ 成功
- **验证结果**: 参数已初始化
- **备注**: 初始化全局参数

---

## 🔧 故障排查

### 问题1: 分区创建失败

**错误信息**: `ERROR: partition "calculation_logs_YYYYMMDD" already exists`

**解决方案**: 
```sql
-- 删除已存在的分区
DROP TABLE IF EXISTS calculation_logs_YYYYMMDD;

-- 重新执行迁移脚本
```

### 问题2: 权限不足

**错误信息**: `ERROR: permission denied for schema public`

**解决方案**: 
```sql
-- 授予权限
GRANT CREATE ON SCHEMA public TO <user>;
```

---

## 📝 注意事项

1. **备份**: 执行迁移前，请先备份数据库
2. **测试环境**: 建议先在测试环境执行，验证无误后再在生产环境执行
3. **权限**: 确保执行用户有 CREATE TABLE、CREATE INDEX、CREATE FUNCTION 权限
4. **分区维护**: 建议设置定时任务，每天执行 `maintain_calculation_logs_partitions()` 函数

---

## 📝 变更说明（2025-11-15）

### calculation_logs 表废弃原因

1. **用户需求**: 用户明确表示"当前的文件日志已经足够，删除这个表"
2. **实际使用情况**: 表已创建但从未被使用
3. **系统简化**: 删除未使用的表可以简化系统，降低维护成本
4. **日志策略**: 文件日志已经提供了完整的追踪能力（trace_id/span_id）

### 已执行的清理工作

1. **数据库层面**:
   - 删除 calculation_logs 表及所有分区
   - 删除 maintain_calculation_logs_partitions() 函数
   - 验证：0个主表，0个分区

2. **代码层面**:
   - 删除 `app/services/calculation/shared/logging_helper.py` 中的 `_write_to_database()` 方法
   - 更新文档字符串：从"写入数据库和文件"改为"写入文件日志"
   - 删除所有相关的 TODO 注释

3. **测试验证**:
   - 端到端测试通过（138个任务，100%成功率）
   - 文件日志正常工作
   - 系统运行正常

---

**下一步**: 所有必要的迁移已完成，可以开始其他指标的重构工作

