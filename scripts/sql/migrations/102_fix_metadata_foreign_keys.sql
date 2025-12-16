-- 修复元数据表外键约束
-- 问题：ON DELETE CASCADE 导致清空 dim_devices/dim_stations 时元数据被删除
-- 解决：移除外键约束，因为 dim_metric_metadata 是永久配置表，不应受维度表重建影响

BEGIN;

-- 步骤1：删除现有外键约束
ALTER TABLE public.dim_metric_metadata
    DROP CONSTRAINT IF EXISTS fk_metadata_station CASCADE;

ALTER TABLE public.dim_metric_metadata
    DROP CONSTRAINT IF EXISTS fk_metadata_device CASCADE;

-- 步骤2：添加表注释说明
COMMENT ON TABLE public.dim_metric_metadata IS
'指标元数据表（三级优先级架构，永久配置表）：
- 全局级：station_id=NULL, device_id=NULL（默认值）
- 站点级：station_id=<id>, device_id=NULL（覆盖全局）
- 设备级：station_id=<id>, device_id=<id>（最高优先级）

查询时按优先级排序：设备级 > 站点级 > 全局级

重要特性：
- 永久配置表：不会被 prepare_dim 流程清空或备份
- 无外键约束：不受 dim_devices/dim_stations 重建影响
- 数据完整性：通过应用层验证和唯一索引保证';

COMMENT ON COLUMN public.dim_metric_metadata.station_id IS
'站点ID（NULL表示全局级）- 无外键约束，数据完整性由应用层保证';

COMMENT ON COLUMN public.dim_metric_metadata.device_id IS
'设备ID（NULL表示站点级或全局级）- 无外键约束，数据完整性由应用层保证';

COMMIT;

