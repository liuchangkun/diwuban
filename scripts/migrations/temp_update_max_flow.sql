-- 临时更新 max_flow 参数（从 500 调整为 5000）
-- 原因：实际单泵流量可以达到 2700+ m³/h，500 的阈值过小

UPDATE calculation_parameters
SET param_value = '5000.0',
    updated_at = NOW(),
    updated_by = 'manual_fix'
WHERE metric_key = 'pump_flow_rate'
  AND method_id = 'data_filter'
  AND param_name = 'max_flow';

-- 验证更新
SELECT 
    id,
    metric_key,
    method_id,
    param_name,
    param_value,
    updated_at,
    updated_by
FROM calculation_parameters
WHERE metric_key = 'pump_flow_rate'
  AND method_id = 'data_filter'
  AND param_name = 'max_flow';

