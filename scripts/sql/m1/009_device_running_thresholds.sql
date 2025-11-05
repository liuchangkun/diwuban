\encoding UTF8
SET client_encoding = 'UTF8';

-- object: device_running_thresholds
-- purpose: thresholds for per-second running detection (enable signals, on/off hysteresis, hold, min segment, smoothing)
-- fields:
--   device_id: dim_devices.id
--   enable_i/p/f: whether to use current/power/frequency (soft-start pumps usually disable frequency)
--   *_on/*_off: open/close thresholds (on >= off) to create a band and resist residual values
--   grace_hold_secs: when all enabled signals missing in a second, carry previous state up to N seconds (0 to disable)
--   min_run_secs/min_stop_secs: minimal run/stop segment length for debouncing in window aggregation (per-second output unaffected)
--   smoothing_secs: optional smoothing window seconds (0 = no smoothing)
-- created_at: 2025-09-03

CREATE TABLE IF NOT EXISTS public.device_running_thresholds (
  device_id            bigint PRIMARY KEY,
  enable_i             boolean NOT NULL DEFAULT true,
  enable_p             boolean NOT NULL DEFAULT true,
  enable_f             boolean NOT NULL DEFAULT true,

  i_on                 double precision,
  i_off                double precision,
  p_on                 double precision,
  p_off                double precision,
  f_on                 double precision,
  f_off                double precision,

  grace_hold_secs      integer NOT NULL DEFAULT 0,
  min_run_secs         integer NOT NULL DEFAULT 0,
  min_stop_secs        integer NOT NULL DEFAULT 0,
  smoothing_secs       integer NOT NULL DEFAULT 0,

  updated_at           timestamptz NOT NULL DEFAULT now(),
  updated_by           text
);

ALTER TABLE public.device_running_thresholds
  ADD CONSTRAINT chk_i_hysteresis CHECK (NOT enable_i OR (i_on IS NOT NULL AND i_off IS NOT NULL AND i_on >= i_off)),
  ADD CONSTRAINT chk_p_hysteresis CHECK (NOT enable_p OR (p_on IS NOT NULL AND p_off IS NOT NULL AND p_on >= p_off)),
  ADD CONSTRAINT chk_f_hysteresis CHECK (NOT enable_f OR (f_on IS NOT NULL AND f_off IS NOT NULL AND f_on >= f_off)),
  ADD CONSTRAINT chk_nonneg_hold  CHECK (grace_hold_secs >= 0 AND min_run_secs >= 0 AND min_stop_secs >= 0 AND smoothing_secs >= 0);

