-- 051: 计算结果拒绝审计表（双层验证未通过即落此，不入库 fact）
BEGIN;

CREATE TABLE IF NOT EXISTS public.metric_compute_rejects (
  id          bigserial PRIMARY KEY,
  run_id      text NULL,                 -- 计算运行ID（可为UUID或流水号）
  station_id  bigint NOT NULL,
  device_id   bigint NOT NULL,
  metric_id   bigint NOT NULL,
  ts_bucket   timestamptz NOT NULL,      -- 秒级对齐时间
  method_code text NOT NULL,             -- 采用的方法
  stage       text NOT NULL CHECK (stage IN ('physics','curve')),
  reason_code text NULL,                 -- 失败原因编码（如 PHYS_BOUND, CONSERVATION_FAIL, CURVE_MISFIT）
  reason_detail jsonb NULL,              -- 证据：越界值/曲线偏差/参数取值等
  created_at  timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE  public.metric_compute_rejects IS '计算拒绝审计：双层验证未通过的样本在此记录，不写入 fact_measurements。';
COMMENT ON COLUMN public.metric_compute_rejects.stage        IS '失败阶段：physics=物理约束，curve=特性曲线。';
COMMENT ON COLUMN public.metric_compute_rejects.reason_code  IS '失败原因编码，便于统计与对照。';

CREATE INDEX IF NOT EXISTS idx_mcr_metric_dev_ts ON public.metric_compute_rejects(metric_id, device_id, ts_bucket);
CREATE INDEX IF NOT EXISTS idx_mcr_stage_ts      ON public.metric_compute_rejects(stage, ts_bucket);

COMMIT;

