-- 全量刷新聚合物化视图（小时/日）
BEGIN;
SET LOCAL statement_timeout TO '600000ms'; -- 10min 兜底
COMMIT;

REFRESH MATERIALIZED VIEW reporting.mv_measurements_hourly;
REFRESH MATERIALIZED VIEW reporting.mv_measurements_daily;

