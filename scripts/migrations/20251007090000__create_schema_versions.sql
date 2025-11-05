-- ============================================
-- 迁移脚本：创建 schema_versions 表（版本治理）
-- 日期：2025-10-07 09:00:00
-- 说明：仅作为迁移文件基线，当前不执行。请由DBA或自动化在受控环境中执行。
-- 合规：中文注释；事务包裹与幂等保护；命名与项目数据库规范一致。
-- ============================================

-- 注意：本文件仅作为“迁移脚本文本”，不会由本工具执行DDL。
--       实际执行时请确保具备合适权限与变更窗口。

-- 建议DDL（供执行时参考）：
-- BEGIN;
-- CREATE TABLE IF NOT EXISTS public.schema_versions (
--     version_id TEXT PRIMARY KEY,
--     applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
--     applied_by TEXT NOT NULL,
--     description TEXT NOT NULL,
--     checksum TEXT NOT NULL
-- );
-- COMMENT ON TABLE public.schema_versions IS 'Schema 版本记录表（用于记录已应用的迁移版本、校验与操作者）';
-- COMMENT ON COLUMN public.schema_versions.version_id IS '版本ID（常用时间戳前缀 + 描述）';
-- COMMENT ON COLUMN public.schema_versions.applied_at IS '应用时间（UTC）';
-- COMMENT ON COLUMN public.schema_versions.applied_by IS '执行人（数据库角色或自动化标识）';
-- COMMENT ON COLUMN public.schema_versions.description IS '版本描述（中文）';
-- COMMENT ON COLUMN public.schema_versions.checksum IS '脚本校验码（防篡改）';
-- COMMIT;

