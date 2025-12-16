# 迁移脚本 108: 修改 calculation_parameters 表的 metric_key 外键约束

## 概述

**迁移编号**: 108  
**创建日期**: 2025-11-14  
**状态**: ✅ 已执行并验证  
**影响范围**: `calculation_parameters` 表的 `metric_key` 外键约束

## 问题背景

### 原始问题

在执行 `prepare_dim` 流程后，`calculation_parameters` 表被完全清空，导致所有优化参数丢失。

### 根本原因

`calculation_parameters` 表的 `metric_key` 外键使用 `ON DELETE CASCADE` 删除规则：

```sql
FOREIGN KEY (metric_key) 
REFERENCES dim_metric_config(metric_key) 
ON UPDATE CASCADE 
ON DELETE CASCADE
```

当 `dim_metric_config` 表被清空时（或任何记录被删除），会触发级联删除，导致 `calculation_parameters` 表中**所有相关行**（包括全局参数）被删除。

### 影响

- **数据丢失**: 所有优化参数（包括全局参数、站点参数、设备参数）被意外删除
- **功能失效**: 计算流程无法从数据库读取配置参数
- **代码保护失效**: 即使代码将 `calculation_parameters` 加入免清空名单，也无法阻止外键 CASCADE 删除

## 解决方案

### 修改内容

将 `calculation_parameters` 表的 `metric_key` 外键从 `ON DELETE CASCADE` 改为 `ON DELETE RESTRICT`：

```sql
FOREIGN KEY (metric_key) 
REFERENCES dim_metric_config(metric_key) 
ON UPDATE CASCADE 
ON DELETE RESTRICT  -- 修改点
```

### 修改理由

1. **保护数据**: `dim_metric_config` 是核心配置表，不应该被轻易删除
2. **防止意外**: 删除指标配置前，必须先清理依赖的参数，防止数据不一致
3. **符合业务逻辑**: 优化参数是永久配置，不应该随指标配置的删除而自动删除
4. **保留合理的 CASCADE**: `device_id` 和 `station_id` 的 CASCADE 仍然保留，因为设备/站点删除时，其参数也应该被删除

### 其他外键约束（未修改）

| 外键 | 删除规则 | 理由 |
|------|---------|------|
| `device_id` | CASCADE | 设备删除时，其参数应该被删除 |
| `station_id` | CASCADE | 站点删除时，其参数应该被删除 |
| `method_id` | NO ACTION | 已经是 NO ACTION，无需修改 |

## 执行步骤

### 1. 执行迁移

```bash
python scripts/tools/execute_migration_108.py
```

**预期输出**:
```
✅ 数据库连接池已初始化
================================================================================
开始执行迁移脚本 108: 修改 calculation_parameters 表的 metric_key 外键约束
================================================================================
📄 读取SQL脚本: ...
🔄 开始执行SQL迁移...
================================================================================
✅ 迁移成功完成！
================================================================================
```

### 2. 验证修改

```bash
python scripts/tools/verify_fk_constraints.py
```

**预期输出**:
```
================================================================================
✅ 所有外键约束验证通过！
================================================================================
📋 验证结果:
  - metric_key 外键: ON DELETE RESTRICT ✅
  - device_id 外键: ON DELETE CASCADE ✅
  - station_id 外键: ON DELETE CASCADE ✅
  - method_id 外键: ON DELETE NO ACTION ✅
```

### 3. 测试 RESTRICT 约束

```bash
python scripts/tools/test_fk_restrict.py
```

**预期输出**:
```
✅ 测试成功: 删除被阻止，RESTRICT 约束生效！
```

### 4. 测试 prepare_dim 保护

```bash
python scripts/tools/test_prepare_dim_protection.py
```

**预期输出**:
```
✅ 测试成功: 全局参数被保护，未被删除！
```

## 回滚方案

如果需要回滚到原始状态（恢复 CASCADE 删除规则）：

```bash
python scripts/tools/execute_migration_108_rollback.py
```

**警告**: 回滚后，`dim_metric_config` 表被清空时会级联删除 `calculation_parameters` 表。

## 验证结果

### 执行日期: 2025-11-14

- ✅ 迁移脚本执行成功
- ✅ 外键约束验证通过
- ✅ RESTRICT 约束测试通过
- ✅ prepare_dim 保护测试通过

### 测试数据

- **全局参数数量**: 48 个
- **执行 prepare_dim 后**: 48 个（完全保留）
- **删除 dim_metric_config 记录**: 被阻止（抛出外键约束错误）

## 影响评估

### 正面影响

1. **数据安全**: 防止意外的级联删除，保护优化参数
2. **业务连续性**: 确保计算流程始终能从数据库读取配置
3. **数据一致性**: 删除指标配置前必须先清理依赖，防止孤立数据

### 潜在影响

1. **删除流程变化**: 如果需要删除 `dim_metric_config` 中的指标，必须先删除 `calculation_parameters` 中的相关参数
2. **测试代码**: 如果测试代码依赖 CASCADE 删除，需要修改测试逻辑

### 风险评估

- **风险等级**: 低
- **影响范围**: 仅影响 `calculation_parameters` 表的 `metric_key` 外键
- **回滚难度**: 简单（执行回滚脚本即可）
- **数据丢失风险**: 无（只是修改约束，不涉及数据变更）

## 相关文件

### 迁移脚本
- `scripts/sql/migrations/108_fix_calculation_parameters_metric_key_fk.sql` - 迁移脚本
- `scripts/sql/migrations/108_fix_calculation_parameters_metric_key_fk_ROLLBACK.sql` - 回滚脚本

### 执行工具
- `scripts/tools/execute_migration_108.py` - 执行迁移
- `scripts/tools/execute_migration_108_rollback.py` - 执行回滚
- `scripts/tools/verify_fk_constraints.py` - 验证外键约束
- `scripts/tools/test_fk_restrict.py` - 测试 RESTRICT 约束
- `scripts/tools/test_prepare_dim_protection.py` - 测试 prepare_dim 保护

### 文档
- `scripts/sql/migrations/108_README.md` - 本文档

## 后续工作

1. ✅ 修改外键约束（已完成）
2. ⏳ 初始化 DataFilter 配置（待执行）
3. ⏳ 实现原始的31步测试改进计划（待执行）
4. ⏳ 移除所有硬编码参数（待执行）

## 参考

- **问题追踪**: calculation_parameters 表被清空问题
- **相关表**: `calculation_parameters`, `dim_metric_config`, `dim_devices`, `dim_stations`
- **相关流程**: `prepare_dim` 流程

