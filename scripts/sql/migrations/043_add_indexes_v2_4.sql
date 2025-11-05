-- V2-4 存储与索引策略（首批索引）
-- 说明：本迁移聚焦质量阶段高频读路径（602/503 等）与窗口扫描，优先减少全表扫描与随机 IO。
-- 注意：apply_sql_file.py 会在单事务中执行，故本文件不使用 CONCURRENTLY 关键字。

-- 1) fact_measurements：时间扫描 + 常用过滤（qs=0）
CREATE INDEX IF NOT EXISTS idx_fm_brin_ts
ON public.fact_measurements
USING BRIN (ts_bucket)
WITH (pages_per_range=128);

-- 复合索引（station/device/metric/time），服务质量阶段常见窗口读写
CREATE INDEX IF NOT EXISTS idx_fm_s_d_m_t
ON public.fact_measurements (station_id, device_id, metric_id, ts_bucket);

-- 2) presence 基表优化：为 metrics_presence_per_second_device 增加 (s,d,t) 索引
-- 说明：mv_presence_1s_any 为视图，不可直接建索引；对基表 (station_id, device_id, ts_second) 建索引，改善连接计划
CREATE INDEX IF NOT EXISTS idx_mpps_s_d_t
ON public.metrics_presence_per_second_device (station_id, device_id, ts_second);

-- 3) mv_device_running_1s：时间范围扫描（供多规则与注入 fwin 复用）
CREATE INDEX IF NOT EXISTS idx_run_brin
ON public.mv_device_running_1s
USING BRIN (station_id, device_id, ts_bucket);

-- 回滚提示（如需回滚，执行以下 DROP）
-- DROP INDEX IF EXISTS public.idx_fm_brin_ts;
-- DROP INDEX IF EXISTS public.idx_fm_s_d_m_t;
-- DROP INDEX IF EXISTS public.idx_mpps_s_d_t;
-- DROP INDEX IF EXISTS public.idx_run_brin;

