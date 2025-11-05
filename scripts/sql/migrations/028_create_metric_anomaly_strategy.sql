-- metric_anomaly_strategy：声明各指标在异常判定中的主策略与关键参数来源
-- 层级覆盖：device_id > station_id > global(NULL)
-- 仅存“怎么判”（策略/依赖/分桶/阈值来源），不直接存阈值结果

BEGIN;

CREATE TABLE IF NOT EXISTS public.metric_anomaly_strategy (
  metric_id BIGINT NOT NULL,
  station_id BIGINT NOT NULL DEFAULT 0,
  device_id BIGINT NOT NULL DEFAULT 0,
  strategy TEXT NOT NULL,                -- work_condition | physics | residual | hybrid
  bins JSONB NULL,                       -- 例如 {"f_bin":"1Hz","min_samples":120}
  model JSONB NULL,                      -- 例如 {"residual":"bin_quantile","q":0.95,"mad_k":4}
  deps JSONB NULL,                       -- 例如 ["P","U","PF"]
  hard_bounds_source TEXT NULL,          -- metadata | rules | none
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by TEXT NULL,
  PRIMARY KEY (metric_id, station_id, device_id)
);

COMMENT ON TABLE public.metric_anomaly_strategy IS '异常判定策略声明：为每个指标（可按站/设覆盖）定义采用的判定方法与关键参数来源，不直接存阈值结果。';

COMMIT;

