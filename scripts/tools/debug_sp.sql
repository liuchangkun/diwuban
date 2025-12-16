-- 调试存储过程执行
-- 手动测试阈值学习流程

-- 1. 清空表
TRUNCATE TABLE device_running_thresholds;

-- 2. 插入设备行
INSERT INTO device_running_thresholds (device_id)
SELECT id FROM dim_devices
ON CONFLICT (device_id) DO NOTHING;

SELECT '插入设备行后:' as step, COUNT(*) as row_count FROM device_running_thresholds;

-- 3. 调用电流阈值学习存储过程
CALL sp_refresh_device_running_thresholds_current(NULL, NULL, NULL, NULL);

SELECT '电流阈值学习后:' as step, COUNT(*) as row_count, 
       COUNT(CASE WHEN i_on IS NOT NULL THEN 1 END) as with_i_on
FROM device_running_thresholds;

-- 4. 调用功率阈值学习存储过程
CALL sp_refresh_device_running_thresholds_power(NULL, NULL, NULL, NULL);

SELECT '功率阈值学习后:' as step, COUNT(*) as row_count,
       COUNT(CASE WHEN p_on IS NOT NULL THEN 1 END) as with_p_on
FROM device_running_thresholds;

-- 5. 调用频率阈值学习存储过程
CALL sp_refresh_device_running_thresholds_frequency(NULL, NULL, NULL, NULL);

SELECT '频率阈值学习后:' as step, COUNT(*) as row_count,
       COUNT(CASE WHEN f_on IS NOT NULL THEN 1 END) as with_f_on
FROM device_running_thresholds;

-- 6. 调用时间参数学习存储过程
CALL sp_refresh_device_running_thresholds_timing(NULL, NULL, NULL, NULL);

SELECT '时间参数学习后:' as step, COUNT(*) as row_count,
       COUNT(CASE WHEN grace_hold_secs IS NOT NULL AND grace_hold_secs > 0 THEN 1 END) as with_timing
FROM device_running_thresholds;

-- 7. 查看最终结果
SELECT 
    device_id,
    enable_i, i_on, i_off,
    enable_p, p_on, p_off,
    enable_f, f_on, f_off,
    grace_hold_secs, min_run_secs, min_stop_secs, smoothing_secs,
    updated_by
FROM device_running_thresholds
ORDER BY device_id;

