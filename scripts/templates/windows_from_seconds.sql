-- 逐秒状态 → 运行/停机窗口段（带最小段长防抖）
-- 使用方式：替换 <device_id>、<start_ts+08>、<end_ts+08>
-- 建议先执行：SET TIME ZONE 'Asia/Shanghai';

WITH sec AS (
  SELECT ts_bucket, is_running
  FROM public.fn_startstop_windows(<device_id>, '<start_ts+08>','<end_ts+08>')
),
iso AS (
  SELECT ts_bucket, is_running,
         (ROW_NUMBER() OVER (ORDER BY ts_bucket)
        - ROW_NUMBER() OVER (PARTITION BY is_running ORDER BY ts_bucket)) AS grp
  FROM sec
),
segments AS (
  SELECT is_running,
         MIN(ts_bucket) AS seg_start,
         MAX(ts_bucket) AS seg_end,
         EXTRACT(EPOCH FROM (MAX(ts_bucket) - MIN(ts_bucket)))::int + 1 AS seg_len
  FROM iso
  GROUP BY is_running, grp
),
thr AS (
  SELECT COALESCE(min_run_secs,0) AS min_run_secs,
         COALESCE(min_stop_secs,0) AS min_stop_secs
  FROM public.device_running_thresholds
  WHERE device_id = <device_id>
)
SELECT CASE WHEN s.is_running THEN 'run' ELSE 'stop' END AS seg_type,
       s.seg_start, s.seg_end, s.seg_len
FROM segments s, thr
WHERE (s.is_running  AND s.seg_len >= thr.min_run_secs)
   OR (NOT s.is_running AND s.seg_len >= thr.min_stop_secs)
ORDER BY s.seg_start;

