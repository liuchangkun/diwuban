-- 逐秒状态 → 启动/停机事件清单（切换点）
-- 使用方式：替换 <device_id>、<start_ts+08>、<end_ts+08>
-- 建议先执行：SET TIME ZONE 'Asia/Shanghai';

WITH sec AS (
  SELECT ts_bucket, is_running
  FROM public.fn_startstop_windows(<device_id>, '<start_ts+08>','<end_ts+08>')
),
mark AS (
  SELECT ts_bucket, is_running,
         LAG(is_running) OVER (ORDER BY ts_bucket) AS prev_state
  FROM sec
)
SELECT CASE
         WHEN is_running = true  AND (prev_state = false OR prev_state IS NULL) THEN 'startup'
         WHEN is_running = false AND  prev_state = true  THEN 'shutdown'
       END AS event_type,
       ts_bucket AS event_ts
FROM mark
WHERE (is_running = true  AND (prev_state = false OR prev_state IS NULL))
   OR (is_running = false AND  prev_state = true)
ORDER BY event_ts;

