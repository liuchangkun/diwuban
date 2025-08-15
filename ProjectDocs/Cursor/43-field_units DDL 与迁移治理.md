---
description: field_units DDL 与迁移治理（版本化、灰度与回滚、审计）
---
# field_units DDL 与迁移治理

## 版本化
- 所有 DDL 变更用版本化脚本（命名：`V<YYYYMMDD>__desc.sql`）。

## 发布
- 先在 staging 执行并校验；prod 灰度发布；失败立即回滚（保留备份）。

## 审计
- 记录执行人/时间/脚本校验和；与变更单关联。

## 数据
- 初始化与更新脚本应幂等（使用 `INSERT IGNORE` 或 `ON DUPLICATE KEY UPDATE`）。