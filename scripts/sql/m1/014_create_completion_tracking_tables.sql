\encoding UTF8
SET client_encoding = 'UTF8';

-- 落地补齐追踪表（运行级/步骤级/审计级/失败清单）
-- 仅结构与基础索引；业务写入由上层负责。时间类型统一 timestamptz。

-- 1) 运行级：completion_runs
CREATE TABLE IF NOT EXISTS public.completion_runs (
  run_id                bigserial PRIMARY KEY,
  station_id            bigint      NOT NULL REFERENCES public.dim_stations(id),
  device_id             bigint      NOT NULL REFERENCES public.dim_devices(id),
  start_ts              timestamptz NOT NULL,
  end_ts                timestamptz NOT NULL,
  code_version          text,
  imputation_version    text,
  config_snapshot       jsonb,
  thresholds_snapshot   jsonb,
  rows_read             bigint,
  duration_ms           integer,
  steps_total           integer,
  rerun_policy          text CHECK (rerun_policy IN ('append','overwrite','skip')),
  parent_run_id         bigint REFERENCES public.completion_runs(run_id) ON DELETE SET NULL,
  superseded_by_run_id  bigint REFERENCES public.completion_runs(run_id) ON DELETE SET NULL,
  idempotency_key       text,
  group_context         jsonb,
  status_reason         text,
  error_code            text,
  created_at            timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE  public.completion_runs IS '追踪表-运行级：一次补全/识别运行的总体信息与快照';
COMMENT ON COLUMN public.completion_runs.station_id IS '泵站ID';
COMMENT ON COLUMN public.completion_runs.device_id IS '设备ID';
COMMENT ON COLUMN public.completion_runs.start_ts IS '运行起';
COMMENT ON COLUMN public.completion_runs.end_ts IS '运行止';
COMMENT ON COLUMN public.completion_runs.config_snapshot IS '配置快照（jsonb）';
COMMENT ON COLUMN public.completion_runs.thresholds_snapshot IS '阈值快照（jsonb）';

CREATE INDEX IF NOT EXISTS idx_completion_runs_station_start ON public.completion_runs (station_id, start_ts);
CREATE INDEX IF NOT EXISTS idx_completion_runs_device_start  ON public.completion_runs (device_id, start_ts);
CREATE INDEX IF NOT EXISTS idx_completion_runs_status_ctime  ON public.completion_runs (status_reason, created_at);

-- 2) 步骤级：completion_steps
CREATE TABLE IF NOT EXISTS public.completion_steps (
  id                   bigserial PRIMARY KEY,
  run_id               bigint      NOT NULL REFERENCES public.completion_runs(run_id) ON DELETE CASCADE,
  device_id            bigint      NOT NULL REFERENCES public.dim_devices(id),
  metric_id            bigint      NOT NULL REFERENCES public.dim_metric_config(id),
  gap_id               bigint,
  gap_start_ts         timestamptz,
  gap_end_ts           timestamptz,
  gap_len_sec          integer,
  gap_class            text,
  in_startstop_window  boolean,
  methods_tried        jsonb,
  fallback_path        text,
  confidence_reason    text[],
  residual_stats       jsonb,
  step_duration_ms     integer,
  rows_considered      bigint,
  data_source          text CHECK (data_source IN ('original','derived')),
  created_at           timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE  public.completion_steps IS '追踪表-步骤级：按 gap/步骤记录方法与耗时等细节';
CREATE INDEX IF NOT EXISTS idx_completion_steps_run            ON public.completion_steps (run_id);
CREATE INDEX IF NOT EXISTS idx_completion_steps_dev_metric_gap ON public.completion_steps (device_id, metric_id, gap_start_ts);
CREATE INDEX IF NOT EXISTS idx_completion_steps_gapid          ON public.completion_steps (gap_id);

-- 3) 审计级：completion_audit（每个 run 一条为主）
CREATE TABLE IF NOT EXISTS public.completion_audit (
  id                     bigserial PRIMARY KEY,
  run_id                 bigint NOT NULL UNIQUE REFERENCES public.completion_runs(run_id) ON DELETE CASCADE,
  coverage_before        numeric,
  coverage_after         numeric,
  missing_before         bigint,
  missing_after          bigint,
  max_gap_before_sec     integer,
  max_gap_after_sec      integer,
  count_ffill            integer,
  count_mean             integer,
  count_reg              integer,
  count_curve            integer,
  count_skipped_long_gap integer,
  startup_drop_ratio     numeric,
  rejects_counts         jsonb,
  thresholds_snapshot_ref text,
  group_consistency      jsonb,
  audit_time             timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE  public.completion_audit IS '追踪表-审计级：对运行进行结构化对账与统计摘要';
CREATE INDEX IF NOT EXISTS idx_completion_audit_time ON public.completion_audit (audit_time);

-- 4) 失败清单：completion_failures（可选逐条失败证据）
CREATE TABLE IF NOT EXISTS public.completion_failures (
  id              bigserial PRIMARY KEY,
  run_id          bigint      NOT NULL REFERENCES public.completion_runs(run_id) ON DELETE CASCADE,
  object_key      jsonb,   -- {station_id, device_id, metric_id}
  gap_id          bigint,
  reason_code     text,
  evidence_uri    text,
  suggested_action text,
  created_at      timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE  public.completion_failures IS '追踪表-失败清单：按对象/缺口沉淀失败原因与证据';
CREATE INDEX IF NOT EXISTS idx_completion_failures_run  ON public.completion_failures (run_id);
CREATE INDEX IF NOT EXISTS idx_completion_failures_gap  ON public.completion_failures (gap_id);

