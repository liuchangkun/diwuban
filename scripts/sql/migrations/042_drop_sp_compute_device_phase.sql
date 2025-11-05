-- 042_drop_sp_compute_device_phase.sql
-- 目的：下线旧的 sp_compute_device_phase 过程（已由 mv_device_running_1s 相位列替代）
-- 说明：仅清理过程本体；不影响现有 V1 架构

BEGIN;

-- 安全删除（存在才删），签名必须匹配
DROP PROCEDURE IF EXISTS public.sp_compute_device_phase(timestamptz, timestamptz, bigint);

COMMIT;

