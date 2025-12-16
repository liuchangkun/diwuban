BEGIN;

COMMENT ON TABLE public.metric_anomaly_strategy IS '异常判定策略声明：为每个指标（可按站/设覆盖）定义采用的判定方法与关键参数来源，不直接存阈值结果。';

COMMENT ON COLUMN public.metric_anomaly_strategy.metric_id IS '指标ID（dim_metric_config.id）';
COMMENT ON COLUMN public.metric_anomaly_strategy.station_id IS '站点ID（0 表示全局策略）';
COMMENT ON COLUMN public.metric_anomaly_strategy.device_id IS '设备ID（0 表示全局策略；设备级优先于站级与全局）';
COMMENT ON COLUMN public.metric_anomaly_strategy.strategy IS '判定策略：work_condition | physics | residual | hybrid';
COMMENT ON COLUMN public.metric_anomaly_strategy.bins IS '分桶配置，例如 {"f_bin":"1Hz","min_samples":1}';
COMMENT ON COLUMN public.metric_anomaly_strategy.model IS '模型与阈值配置，例如 {"residual":"bin_quantile","q":0.95,"mad_k":4}';
COMMENT ON COLUMN public.metric_anomaly_strategy.deps IS '依赖变量清单，例如 ["P","U","PF","f"]';
COMMENT ON COLUMN public.metric_anomaly_strategy.hard_bounds_source IS '硬边界来源：metadata|rules|none（仅用于101物理越界）';
COMMENT ON COLUMN public.metric_anomaly_strategy.enabled IS '是否启用该策略';
COMMENT ON COLUMN public.metric_anomaly_strategy.updated_at IS '更新时间戳';
COMMENT ON COLUMN public.metric_anomaly_strategy.updated_by IS '最后更新者标识';

COMMIT;

