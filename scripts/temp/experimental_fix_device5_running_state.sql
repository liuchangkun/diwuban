-- =====================================================================
-- 实验性验证脚本：强制修改运行状态并重新计算
-- 目的：验证"运行状态阈值配置不准确"是否是设备5计算失败的根本原因
-- 日期：2025-11-03
-- ⚠️ 警告：此脚本会修改数据库数据，仅在测试环境中执行
-- =====================================================================

\echo '========================================';
\echo '第1步：备份当前数据';
\echo '========================================';

-- 1.1 创建备份表
DROP TABLE IF EXISTS mv_device_running_1s_backup_20251103;
CREATE TABLE mv_device_running_1s_backup_20251103 AS
SELECT * FROM mv_device_running_1s
WHERE ts_bucket >= '2025-06-01 02:00:00+08'
  AND ts_bucket < '2025-06-01 04:00:00+08';

-- 验证备份
SELECT COUNT(*) as backup_row_count FROM mv_device_running_1s_backup_20251103;

\echo '';
\echo '备份完成！';
\echo '';

\echo '========================================';
\echo '第2步：强制修改运行状态';
\echo '========================================';

-- 2.1 将所有设备的运行状态改为1（运行中）
UPDATE mv_device_running_1s
SET running = 1
WHERE station_id = 1
  AND ts_bucket >= '2025-06-01 02:00:00+08'
  AND ts_bucket < '2025-06-01 04:00:00+08';

\echo '';
\echo '运行状态已强制修改为1（运行中）';
\echo '';

-- 2.2 验证修改结果
\echo '验证设备5的运行状态：';
SELECT 
    COUNT(*) as total_records,
    COUNT(*) FILTER (WHERE running = 1) as running_count,
    COUNT(*) FILTER (WHERE running = 0) as stopped_count
FROM mv_device_running_1s
WHERE device_id = 5
  AND ts_bucket >= '2025-06-01 02:00:00+08'
  AND ts_bucket < '2025-06-01 04:00:00+08';

\echo '';
\echo '验证所有设备的运行状态：';
SELECT 
    device_id,
    COUNT(*) as total_records,
    COUNT(*) FILTER (WHERE running = 1) as running_count,
    COUNT(*) FILTER (WHERE running = 0) as stopped_count
FROM mv_device_running_1s
WHERE station_id = 1
  AND ts_bucket >= '2025-06-01 02:00:00+08'
  AND ts_bucket < '2025-06-01 04:00:00+08'
GROUP BY device_id
ORDER BY device_id;

\echo '';
\echo '========================================';
\echo '第3步：删除设备5的旧计算数据';
\echo '========================================';

-- 3.1 删除设备5的5个失败指标的数据
DELETE FROM fact_measurements
WHERE device_id = 5
  AND metric_id IN (
    SELECT id FROM dim_metric_config 
    WHERE metric_key IN ('pump_flow_rate', 'pump_efficiency', 'pump_speed', 'pump_torque', 'pump_cumulative_flow')
  )
  AND ts_bucket >= '2025-06-01 02:00:00+08'
  AND ts_bucket < '2025-06-01 04:00:00+08';

\echo '';
\echo '旧数据已删除';
\echo '';

-- 3.2 验证删除结果
\echo '验证删除结果（应该返回0行）：';
SELECT 
    dmc.metric_key,
    COUNT(*) as remaining_count
FROM fact_measurements fm
JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
WHERE fm.device_id = 5
  AND dmc.metric_key IN ('pump_flow_rate', 'pump_efficiency', 'pump_speed', 'pump_torque', 'pump_cumulative_flow')
  AND fm.ts_bucket >= '2025-06-01 02:00:00+08'
  AND fm.ts_bucket < '2025-06-01 04:00:00+08'
GROUP BY dmc.metric_key;

\echo '';
\echo '========================================';
\echo '准备工作完成！';
\echo '现在可以运行计算命令：';
\echo 'python -m app.cli.main run-all configs/data_mapping.v2.json';
\echo '========================================';

