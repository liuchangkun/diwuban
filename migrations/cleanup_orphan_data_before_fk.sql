-- ============================================
-- 清理孤立数据（在添加外键约束之前）
-- 方案7：外键约束级联更新修复
-- 执行时间：2025-10-26
-- ============================================

BEGIN;

-- 1. 清理optimization_history表中的孤立数据
-- 删除device_id不存在于dim_devices表中的记录
DELETE FROM optimization_history
WHERE device_id NOT IN (SELECT id FROM dim_devices);

-- 2. 清理pump_characteristic_curves表中的孤立数据
-- 删除device_id不存在于dim_devices表中的记录
DELETE FROM pump_characteristic_curves
WHERE device_id NOT IN (SELECT id FROM dim_devices);

COMMIT;

-- 验证清理结果
SELECT 'optimization_history' AS table_name, COUNT(*) AS orphan_count
FROM optimization_history oh
LEFT JOIN dim_devices d ON oh.device_id = d.id
WHERE oh.device_id IS NOT NULL AND d.id IS NULL

UNION ALL

SELECT 'pump_characteristic_curves', COUNT(*)
FROM pump_characteristic_curves pcc
LEFT JOIN dim_devices d ON pcc.device_id = d.id
WHERE pcc.device_id IS NOT NULL AND d.id IS NULL;

