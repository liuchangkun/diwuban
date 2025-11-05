-- ============================================
-- 自适应SQL脚本：dim_metric_metadata_override
-- ============================================
-- 文件：scripts/sql/adaptive/04_metadata_override.sql
-- 用途：生成 dim_metric_metadata_override
-- 依赖：dim_stations, dim_devices, dim_metric_config
-- 特性：自适应关联，使用 metric_id 关联 dim_metric_config
-- 注意：此表通常为手动配置表，当前脚本仅提供示例，实际使用时应从备份恢复
-- ============================================

BEGIN;

-- ============================================
-- dim_metric_metadata_override（指标元数据覆盖）
-- ============================================

-- 清空表（完全重建）
-- 注意：如果此表包含重要的手动配置数据，应该从备份恢复而不是重建
-- TRUNCATE TABLE dim_metric_metadata_override CASCADE;

-- ============================================
-- 示例：为特定设备的特定指标设置物理范围
-- ============================================
-- 注意：以下示例代码已注释，实际使用时应根据需求启用

-- 示例1：为所有泵的 pump_frequency 设置物理范围
-- INSERT INTO dim_metric_metadata_override (
--     station_id, device_id, metric_id, 
--     resolution, phys_min, phys_max, 
--     saturation_min, saturation_max, remark
-- )
-- SELECT 
--     s.id,
--     d.id,
--     mc.id,
--     0.01,
--     0.0,
--     50.0,
--     0.0,
--     50.0,
--     '自适应SQL脚本生成 - 泵频率范围'
-- FROM dim_devices d
-- JOIN dim_stations s ON d.station_id = s.id
-- JOIN dim_metric_config mc ON mc.metric_key = 'pump_frequency'
-- WHERE d.type = 'pump';

-- 示例2：为特定站点的特定设备设置指标范围
-- INSERT INTO dim_metric_metadata_override (
--     station_id, device_id, metric_id, 
--     resolution, phys_min, phys_max, 
--     saturation_min, saturation_max, remark
-- )
-- SELECT 
--     s.id,
--     d.id,
--     mc.id,
--     0.01,
--     0.0,
--     100.0,
--     0.0,
--     100.0,
--     '自适应SQL脚本生成 - 特定设备的指标范围'
-- FROM dim_devices d
-- JOIN dim_stations s ON d.station_id = s.id
-- JOIN dim_metric_config mc ON mc.metric_key = 'pump_active_power'
-- WHERE s.name = '二期供水泵房' AND d.name = '二期供水泵房1#泵';

-- 示例3：为所有变频泵的 pump_frequency 设置范围
-- INSERT INTO dim_metric_metadata_override (
--     station_id, device_id, metric_id, 
--     resolution, phys_min, phys_max, 
--     saturation_min, saturation_max, remark
-- )
-- SELECT 
--     s.id,
--     d.id,
--     mc.id,
--     0.01,
--     25.0,
--     50.0,
--     25.0,
--     50.0,
--     '自适应SQL脚本生成 - 变频泵频率范围'
-- FROM dim_devices d
-- JOIN dim_stations s ON d.station_id = s.id
-- JOIN dim_metric_config mc ON mc.metric_key = 'pump_frequency'
-- WHERE d.pump_type = 'variable_frequency';

-- ============================================
-- 说明
-- ============================================
-- dim_metric_metadata_override 表通常包含手动配置的数据，
-- 这些数据是根据实际设备特性和现场情况设置的。
-- 
-- 建议的使用方式：
-- 1. 从备份恢复此表（推荐）
-- 2. 如果需要重新生成，请根据实际需求启用上述示例代码
-- 3. 如果需要添加新的覆盖规则，请参考上述示例代码的模式
-- 
-- 自适应关联的关键点：
-- - 使用 JOIN dim_metric_config mc ON mc.metric_key = '...' 获取 metric_id
-- - 使用 JOIN dim_stations s ON d.station_id = s.id 关联站点
-- - 使用 WHERE s.name = '...' AND d.name = '...' 定位特定设备
-- - 使用 WHERE d.type = '...' 或 d.pump_type = '...' 批量处理同类设备
-- ============================================

COMMIT;

