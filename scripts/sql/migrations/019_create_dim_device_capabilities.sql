-- 设备能力表（是否变频、频率范围、额定参数等）
-- 目的：为启停阈值与分工况建模提供设备能力信息

BEGIN;

CREATE TABLE IF NOT EXISTS public.dim_device_capabilities (
  device_id bigint PRIMARY KEY REFERENCES public.dim_devices(id),
  vfd_enabled boolean NULL,
  freq_min double precision NULL,
  freq_max double precision NULL,
  rated_power_kw double precision NULL,
  rated_current_a double precision NULL,
  remark text NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_by text NULL
);

COMMENT ON TABLE public.dim_device_capabilities IS '设备能力表：记录是否变频(VFD)、频率范围、额定功率/电流等参数。';
COMMENT ON COLUMN public.dim_device_capabilities.device_id IS '设备ID（关联 dim_devices.id）。';
COMMENT ON COLUMN public.dim_device_capabilities.vfd_enabled IS '是否为变频驱动设备（VFD）。';
COMMENT ON COLUMN public.dim_device_capabilities.freq_min IS '变频最小频率（Hz）。';
COMMENT ON COLUMN public.dim_device_capabilities.freq_max IS '变频最大频率（Hz）。';
COMMENT ON COLUMN public.dim_device_capabilities.rated_power_kw IS '额定功率（kW）。';
COMMENT ON COLUMN public.dim_device_capabilities.rated_current_a IS '额定电流（A）。';
COMMENT ON COLUMN public.dim_device_capabilities.remark IS '中文备注与口径说明。';
COMMENT ON COLUMN public.dim_device_capabilities.updated_at IS '更新时间（自动）。';
COMMENT ON COLUMN public.dim_device_capabilities.updated_by IS '更新人（可空）。';

COMMIT;

