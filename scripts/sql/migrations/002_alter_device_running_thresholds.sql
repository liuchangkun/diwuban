-- 目的：在保留现有启停阈值表的基础上，增加相位窗口、功率因数与三相不平衡阈值

BEGIN;

ALTER TABLE public.device_running_thresholds
  ADD COLUMN IF NOT EXISTS pf_min double precision,
  ADD COLUMN IF NOT EXISTS pf_max double precision,
  ADD COLUMN IF NOT EXISTS start_pre_secs int,
  ADD COLUMN IF NOT EXISTS start_post_secs int,
  ADD COLUMN IF NOT EXISTS stop_pre_secs int,
  ADD COLUMN IF NOT EXISTS stop_post_secs int,
  ADD COLUMN IF NOT EXISTS imbalance_max_pct double precision;

COMMENT ON TABLE public.device_running_thresholds IS '设备启停判定与相位窗口阈值表。可按设备配置功率/电流/频率阈值、相位窗口、功率因数与三相不平衡容限。';
COMMENT ON COLUMN public.device_running_thresholds.pf_min IS '功率因数最小阈值（下限）。';
COMMENT ON COLUMN public.device_running_thresholds.pf_max IS '功率因数最大阈值（上限）。';
COMMENT ON COLUMN public.device_running_thresholds.start_pre_secs  IS '启动相位：上升沿前窗口秒数。';
COMMENT ON COLUMN public.device_running_thresholds.start_post_secs IS '启动相位：上升沿后窗口秒数。';
COMMENT ON COLUMN public.device_running_thresholds.stop_pre_secs   IS '停止相位：下降沿前窗口秒数。';
COMMENT ON COLUMN public.device_running_thresholds.stop_post_secs  IS '停止相位：下降沿后窗口秒数。';
COMMENT ON COLUMN public.device_running_thresholds.imbalance_max_pct IS '三相不平衡允许最大百分比。';

COMMIT;

