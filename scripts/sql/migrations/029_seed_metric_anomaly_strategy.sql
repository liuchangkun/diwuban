BEGIN;

-- 全局策略映射（station_id=0, device_id=0），频率分桶1Hz，最小样本1
-- strategy: work_condition | physics | residual | hybrid

INSERT INTO public.metric_anomaly_strategy
  (metric_id, station_id, device_id, strategy, bins, model, deps, hard_bounds_source, enabled, updated_by)
VALUES
  -- work_condition
  (1, 0, 0, 'work_condition', '{"f_bin":"1Hz","min_samples":1}'::jsonb, NULL, NULL, 'none', TRUE, 'augment'),
  (64, 0, 0, 'work_condition', '{"f_bin":"1Hz","min_samples":1}'::jsonb, NULL, NULL, 'none', TRUE, 'augment'),
  (65, 0, 0, 'work_condition', '{"f_bin":"1Hz","min_samples":1}'::jsonb, NULL, NULL, 'none', TRUE, 'augment'),

  -- physics
  (2, 0, 0, 'physics', NULL, NULL, NULL, 'metadata', TRUE, 'augment'),
  (4, 0, 0, 'physics', NULL, NULL, NULL, 'metadata', TRUE, 'augment'),
  (6, 0, 0, 'physics', NULL, NULL, NULL, 'metadata', TRUE, 'augment'),
  (10, 0, 0, 'physics', NULL, NULL, '["PF_range"]'::jsonb, 'metadata', TRUE, 'augment'),
  (9, 0, 0, 'physics', NULL, NULL, '["monotonic"]'::jsonb, 'metadata', TRUE, 'augment'),
  (15, 0, 0, 'physics', NULL, NULL, '["monotonic"]'::jsonb, 'metadata', TRUE, 'augment'),
  (63, 0, 0, 'physics', NULL, NULL, '["monotonic"]'::jsonb, 'metadata', TRUE, 'augment'),

  -- residual（分段分位/回归残差）
  (21, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (22, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (23, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (24, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (25, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (26, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (27, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (28, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (35, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (36, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (37, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (38, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (39, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (40, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (41, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (42, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (29, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.9,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (30, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.9,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (31, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.9,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (32, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.9,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (33, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.9,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (34, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.9,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (43, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.9,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (44, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.9,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (45, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.9,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (46, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.9,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (47, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.9,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (48, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.9,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (49, 0, 0, 'residual', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.9,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),

  -- hybrid（工况+物理+残差）
  (3, 0, 0, 'hybrid',  '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["U","I","P","PF","f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (5, 0, 0, 'hybrid',  '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["U","I","P","PF","f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (7, 0, 0, 'hybrid',  '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["U","I","P","PF","f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (8, 0, 0, 'hybrid',  '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["U","I","P","PF","f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (11, 0, 0, 'hybrid', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f","Q"]'::jsonb, 'metadata', TRUE, 'augment'),
  (12, 0, 0, 'hybrid', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f","Q"]'::jsonb, 'metadata', TRUE, 'augment'),
  (13, 0, 0, 'hybrid', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f","Q"]'::jsonb, 'metadata', TRUE, 'augment'),
  (61, 0, 0, 'hybrid', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f","Q"]'::jsonb, 'metadata', TRUE, 'augment'),
  (16, 0, 0, 'hybrid', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f","Q"]'::jsonb, 'metadata', TRUE, 'augment'),
  (14, 0, 0, 'hybrid', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (62, 0, 0, 'hybrid', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (17, 0, 0, 'hybrid', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.9,"mad_k":4}'::jsonb,  '["f","Q","H"]'::jsonb, 'metadata', TRUE, 'augment'),
  (19, 0, 0, 'hybrid', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["f"]'::jsonb, 'metadata', TRUE, 'augment'),
  (20, 0, 0, 'hybrid', '{"f_bin":"1Hz","min_samples":1}'::jsonb, '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb, '["P","speed"]'::jsonb, 'metadata', TRUE, 'augment')
ON CONFLICT (metric_id, station_id, device_id)
DO UPDATE SET
  strategy = EXCLUDED.strategy,
  bins = EXCLUDED.bins,
  model = EXCLUDED.model,
  deps = EXCLUDED.deps,
  hard_bounds_source = EXCLUDED.hard_bounds_source,
  enabled = EXCLUDED.enabled,
  updated_at = now(),
  updated_by = EXCLUDED.updated_by;

COMMIT;

