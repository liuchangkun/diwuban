-- 回滚参数初始化

BEGIN;

-- 删除所有 pump_flow_rate 的全局参数
DELETE FROM calculation_parameters
WHERE metric_key = 'pump_flow_rate'
  AND station_id IS NULL
  AND device_id IS NULL;

-- 验证删除
DO $$
DECLARE
    param_count INT;
BEGIN
    SELECT COUNT(*) INTO param_count
    FROM calculation_parameters
    WHERE metric_key = 'pump_flow_rate'
      AND station_id IS NULL
      AND device_id IS NULL;
    
    IF param_count > 0 THEN
        RAISE EXCEPTION '回滚失败：仍有%个参数未删除', param_count;
    END IF;
    
    RAISE NOTICE '✅ 回滚成功：所有全局参数已删除';
END $$;

COMMIT;

