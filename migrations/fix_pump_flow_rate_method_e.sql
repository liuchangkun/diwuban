-- 修复 pump_flow_rate_method_e 的条件字段
BEGIN;

UPDATE calculation_method_registry
SET conditions = jsonb_set(
    conditions - 'min_running_pumps',
    '{running_count}',
    to_jsonb((conditions->>'min_running_pumps')::int)
)
WHERE method_id = 'pump_flow_rate_method_e'
  AND conditions ? 'min_running_pumps';

COMMIT;

-- 验证修改
SELECT method_id, conditions
FROM calculation_method_registry
WHERE method_id IN ('pump_flow_rate_method_d', 'pump_flow_rate_method_e');

