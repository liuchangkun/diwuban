-- ============================================
-- 修复 pump_inlet_pressure 参数
--
-- 功能：修复泵入口压力计算的参数错误
-- 作者：AI
-- 创建日期：2025-09-30
-- ============================================

-- 问题说明：
-- 1. K_eq = 10.0 太大，应该是 3.0（用户确认）
-- 2. L_offset = 2.5m 错误，应该是 2.0m（用户确认）
-- 3. 代码公式已从减法改为加法（h_static = pool_level + L_offset）

BEGIN;

-- 1. 更新全局 K_eq：10.0 → 3.0
UPDATE calculation_parameters 
SET param_value = '3.0', 
    updated_at = NOW(), 
    updated_by = 'fix_pump_inlet_pressure_formula'
WHERE metric_key = 'pump_inlet_pressure' 
  AND param_name = 'K_eq' 
  AND station_id IS NULL 
  AND device_id IS NULL;

-- 验证更新
SELECT id, metric_key, param_name, param_value, station_id, device_id, updated_at, updated_by
FROM calculation_parameters
WHERE metric_key = 'pump_inlet_pressure' 
  AND param_name = 'K_eq' 
  AND station_id IS NULL 
  AND device_id IS NULL;

-- 2. 更新所有设备的 L_offset：2.5 → 2.0
UPDATE calculation_parameters 
SET param_value = '2.0', 
    updated_at = NOW(), 
    updated_by = 'fix_pump_inlet_pressure_formula'
WHERE metric_key = 'pump_inlet_pressure' 
  AND param_name = 'L_offset' 
  AND device_id IN (1, 2, 3, 4, 5, 6);

-- 验证更新
SELECT id, metric_key, param_name, param_value, station_id, device_id, updated_at, updated_by
FROM calculation_parameters
WHERE metric_key = 'pump_inlet_pressure' 
  AND param_name = 'L_offset' 
  AND device_id IN (1, 2, 3, 4, 5, 6)
ORDER BY device_id;

COMMIT;

-- ============================================
-- 回滚脚本（如果需要）
-- ============================================
/*
BEGIN;

-- 回滚 K_eq
UPDATE calculation_parameters 
SET param_value = '10.0', 
    updated_at = NOW(), 
    updated_by = 'rollback'
WHERE metric_key = 'pump_inlet_pressure' 
  AND param_name = 'K_eq' 
  AND station_id IS NULL 
  AND device_id IS NULL;

-- 回滚 L_offset
UPDATE calculation_parameters 
SET param_value = '2.5', 
    updated_at = NOW(), 
    updated_by = 'rollback'
WHERE metric_key = 'pump_inlet_pressure' 
  AND param_name = 'L_offset' 
  AND device_id IN (1, 2, 3, 4, 5, 6);

COMMIT;
*/

