-- 修复 pump_inlet_pressure 的 L_offset 参数
-- 问题：L_offset = 2.0 m 太小，导致静压头不足以克服水头损失，泵入口产生负压
-- 解决方案：将 L_offset 从 2.0 m 增加到 12.0 m

-- 更新设备1-6的 L_offset 参数
UPDATE calculation_parameters
SET param_value = 12.0,
    updated_at = NOW(),
    updated_by = 'system_fix_20251118'
WHERE device_id IN (1, 2, 3, 4, 5, 6)
  AND metric_key = 'pump_inlet_pressure'
  AND param_name = 'L_offset'
  AND param_value = 2.0;

-- 验证更新结果
SELECT 
    device_id,
    metric_key,
    method_id,
    param_name,
    param_value,
    updated_at,
    updated_by
FROM calculation_parameters
WHERE device_id IN (1, 2, 3, 4, 5, 6)
  AND metric_key = 'pump_inlet_pressure'
  AND param_name = 'L_offset'
ORDER BY device_id;

