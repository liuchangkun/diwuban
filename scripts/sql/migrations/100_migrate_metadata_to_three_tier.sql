-- ============================================================================
-- 迁移脚本：将元数据表改造为三级优先级架构
-- ============================================================================
-- 目标：
--   1. 删除 dim_metric_metadata_override 表
--   2. 改造 dim_metric_metadata 表，添加 station_id 和 device_id 字段
--   3. 修改主键为复合主键 (station_id, device_id, metric_id)
--   4. 生成560条完整数据：56全局 + 56站点 + 448设备
--   5. 所有站点级和设备级数据初始值复制全局级数据
--
-- 执行前提：
--   - dim_metric_metadata 表有56条数据
--   - dim_stations 表有1条记录（station_id=1）
--   - dim_devices 表有8条记录（device_id=1-8）
--
-- 作者：AI Assistant
-- 日期：2025-01-07
-- ============================================================================

BEGIN;

-- ============================================================================
-- 步骤1：前置检查
-- ============================================================================

DO $$
DECLARE
    v_metadata_count INTEGER;
    v_station_count INTEGER;
    v_device_count INTEGER;
BEGIN
    -- 检查 dim_metric_metadata 表数据量
    SELECT COUNT(*) INTO v_metadata_count FROM public.dim_metric_metadata;
    IF v_metadata_count != 56 THEN
        RAISE EXCEPTION '❌ dim_metric_metadata 表数据量不正确：期望56条，实际%条', v_metadata_count;
    END IF;
    RAISE NOTICE '✓ dim_metric_metadata 表数据量正确：56条';
    
    -- 检查 dim_stations 表
    SELECT COUNT(*) INTO v_station_count FROM public.dim_stations;
    IF v_station_count < 1 THEN
        RAISE EXCEPTION '❌ dim_stations 表无数据';
    END IF;
    RAISE NOTICE '✓ dim_stations 表有%条记录', v_station_count;
    
    -- 检查 dim_devices 表
    SELECT COUNT(*) INTO v_device_count FROM public.dim_devices;
    IF v_device_count < 1 THEN
        RAISE EXCEPTION '❌ dim_devices 表无数据';
    END IF;
    RAISE NOTICE '✓ dim_devices 表有%条记录', v_device_count;
END $$;

-- ============================================================================
-- 步骤2：创建临时备份表
-- ============================================================================

RAISE NOTICE '步骤2：创建临时备份表...';

DROP TABLE IF EXISTS tmp_metadata_backup CASCADE;

CREATE TEMP TABLE tmp_metadata_backup AS
SELECT 
    metric_id,
    unit,
    resolution,
    phys_min,
    phys_max,
    saturation_min,
    saturation_max,
    remark,
    updated_at,
    updated_by
FROM public.dim_metric_metadata;

-- 验证备份
DO $$
DECLARE
    v_backup_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_backup_count FROM tmp_metadata_backup;
    IF v_backup_count != 56 THEN
        RAISE EXCEPTION '❌ 备份失败：期望56条，实际%条', v_backup_count;
    END IF;
    RAISE NOTICE '✓ 备份成功：56条记录';
END $$;

-- ============================================================================
-- 步骤3：删除 dim_metric_metadata_override 表
-- ============================================================================

RAISE NOTICE '步骤3：删除 dim_metric_metadata_override 表...';

-- 先删除依赖的视图（稍后会重建）
DROP VIEW IF EXISTS public.v_effective_metric_metadata CASCADE;

-- 删除表
DROP TABLE IF EXISTS public.dim_metric_metadata_override CASCADE;

RAISE NOTICE '✓ dim_metric_metadata_override 表已删除';

-- ============================================================================
-- 步骤4：修改 dim_metric_metadata 表结构
-- ============================================================================

RAISE NOTICE '步骤4：修改 dim_metric_metadata 表结构...';

-- 4.1 添加 station_id 和 device_id 字段
ALTER TABLE public.dim_metric_metadata
    ADD COLUMN station_id bigint NULL,
    ADD COLUMN device_id bigint NULL;

RAISE NOTICE '✓ 已添加 station_id 和 device_id 字段';

-- 4.2 添加外键约束
ALTER TABLE public.dim_metric_metadata
    ADD CONSTRAINT fk_metadata_station 
        FOREIGN KEY (station_id) REFERENCES public.dim_stations(id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_metadata_device 
        FOREIGN KEY (device_id) REFERENCES public.dim_devices(id) ON DELETE CASCADE;

RAISE NOTICE '✓ 已添加外键约束';

-- 4.3 删除旧主键
ALTER TABLE public.dim_metric_metadata
    DROP CONSTRAINT IF EXISTS dim_metric_metadata_pkey CASCADE;

RAISE NOTICE '✓ 已删除旧主键';

-- 4.4 创建新的复合主键
ALTER TABLE public.dim_metric_metadata
    ADD CONSTRAINT dim_metric_metadata_pkey 
        PRIMARY KEY (station_id, device_id, metric_id);

RAISE NOTICE '✓ 已创建新的复合主键 (station_id, device_id, metric_id)';

-- ============================================================================
-- 步骤5：迁移现有数据（设置为全局级）
-- ============================================================================

RAISE NOTICE '步骤5：迁移现有数据为全局级...';

-- 现有56条数据的 station_id 和 device_id 都设置为 NULL（全局级）
UPDATE public.dim_metric_metadata
SET station_id = NULL, device_id = NULL;

-- 验证
DO $$
DECLARE
    v_global_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_global_count
    FROM public.dim_metric_metadata
    WHERE station_id IS NULL AND device_id IS NULL;

    IF v_global_count != 56 THEN
        RAISE EXCEPTION '❌ 全局级数据迁移失败：期望56条，实际%条', v_global_count;
    END IF;
    RAISE NOTICE '✓ 全局级数据迁移成功：56条';
END $$;

-- ============================================================================
-- 步骤6：生成站点级数据（56条）
-- ============================================================================

RAISE NOTICE '步骤6：生成站点级数据...';

INSERT INTO public.dim_metric_metadata (
    station_id, device_id, metric_id,
    unit, resolution, phys_min, phys_max,
    saturation_min, saturation_max, remark,
    updated_at, updated_by
)
SELECT
    1 AS station_id,              -- 站点ID=1
    NULL AS device_id,             -- 设备ID=NULL（站点级）
    metric_id,
    unit,
    resolution,
    phys_min,
    phys_max,
    saturation_min,
    saturation_max,
    remark,
    now() AS updated_at,
    'migration_script' AS updated_by
FROM tmp_metadata_backup;

-- 验证
DO $$
DECLARE
    v_station_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_station_count
    FROM public.dim_metric_metadata
    WHERE station_id = 1 AND device_id IS NULL;

    IF v_station_count != 56 THEN
        RAISE EXCEPTION '❌ 站点级数据生成失败：期望56条，实际%条', v_station_count;
    END IF;
    RAISE NOTICE '✓ 站点级数据生成成功：56条';
END $$;

-- ============================================================================
-- 步骤7：生成设备级数据（448条 = 8设备 × 56指标）
-- ============================================================================

RAISE NOTICE '步骤7：生成设备级数据...';

INSERT INTO public.dim_metric_metadata (
    station_id, device_id, metric_id,
    unit, resolution, phys_min, phys_max,
    saturation_min, saturation_max, remark,
    updated_at, updated_by
)
SELECT
    d.station_id,                  -- 从 dim_devices 获取 station_id
    d.id AS device_id,             -- 设备ID
    t.metric_id,
    t.unit,
    t.resolution,
    t.phys_min,
    t.phys_max,
    t.saturation_min,
    t.saturation_max,
    t.remark,
    now() AS updated_at,
    'migration_script' AS updated_by
FROM tmp_metadata_backup t
CROSS JOIN public.dim_devices d;

-- 验证
DO $$
DECLARE
    v_device_count INTEGER;
    v_expected_count INTEGER;
    v_actual_device_count INTEGER;
BEGIN
    -- 获取设备数量
    SELECT COUNT(*) INTO v_actual_device_count FROM public.dim_devices;
    v_expected_count := v_actual_device_count * 56;

    SELECT COUNT(*) INTO v_device_count
    FROM public.dim_metric_metadata
    WHERE device_id IS NOT NULL;

    IF v_device_count != v_expected_count THEN
        RAISE EXCEPTION '❌ 设备级数据生成失败：期望%条，实际%条', v_expected_count, v_device_count;
    END IF;
    RAISE NOTICE '✓ 设备级数据生成成功：%条（%个设备 × 56指标）', v_device_count, v_actual_device_count;
END $$;

-- ============================================================================
-- 步骤8：验证数据完整性
-- ============================================================================

RAISE NOTICE '步骤8：验证数据完整性...';

DO $$
DECLARE
    v_total_count INTEGER;
    v_global_count INTEGER;
    v_station_count INTEGER;
    v_device_count INTEGER;
    v_expected_total INTEGER;
    v_actual_device_count INTEGER;
BEGIN
    -- 获取设备数量
    SELECT COUNT(*) INTO v_actual_device_count FROM public.dim_devices;
    v_expected_total := 56 + 56 + (v_actual_device_count * 56);

    -- 总记录数
    SELECT COUNT(*) INTO v_total_count FROM public.dim_metric_metadata;

    -- 全局级
    SELECT COUNT(*) INTO v_global_count
    FROM public.dim_metric_metadata
    WHERE station_id IS NULL AND device_id IS NULL;

    -- 站点级
    SELECT COUNT(*) INTO v_station_count
    FROM public.dim_metric_metadata
    WHERE station_id IS NOT NULL AND device_id IS NULL;

    -- 设备级
    SELECT COUNT(*) INTO v_device_count
    FROM public.dim_metric_metadata
    WHERE device_id IS NOT NULL;

    RAISE NOTICE '========================================';
    RAISE NOTICE '数据完整性验证结果：';
    RAISE NOTICE '========================================';
    RAISE NOTICE '总记录数：% / % (期望)', v_total_count, v_expected_total;
    RAISE NOTICE '全局级：% / 56 (期望)', v_global_count;
    RAISE NOTICE '站点级：% / 56 (期望)', v_station_count;
    RAISE NOTICE '设备级：% / % (期望)', v_device_count, v_actual_device_count * 56;
    RAISE NOTICE '========================================';

    IF v_total_count != v_expected_total THEN
        RAISE EXCEPTION '❌ 总记录数不正确';
    END IF;

    IF v_global_count != 56 THEN
        RAISE EXCEPTION '❌ 全局级数据不完整';
    END IF;

    IF v_station_count != 56 THEN
        RAISE EXCEPTION '❌ 站点级数据不完整';
    END IF;

    IF v_device_count != v_actual_device_count * 56 THEN
        RAISE EXCEPTION '❌ 设备级数据不完整';
    END IF;

    RAISE NOTICE '✓ 数据完整性验证通过';
END $$;

-- ============================================================================
-- 步骤9：创建索引优化查询性能
-- ============================================================================

RAISE NOTICE '步骤9：创建索引...';

-- 为常用查询创建索引
CREATE INDEX IF NOT EXISTS idx_metadata_metric_id
    ON public.dim_metric_metadata(metric_id);

CREATE INDEX IF NOT EXISTS idx_metadata_station_metric
    ON public.dim_metric_metadata(station_id, metric_id)
    WHERE station_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_metadata_device_metric
    ON public.dim_metric_metadata(device_id, metric_id)
    WHERE device_id IS NOT NULL;

RAISE NOTICE '✓ 索引创建成功';

-- ============================================================================
-- 步骤10：删除临时表
-- ============================================================================

RAISE NOTICE '步骤10：清理临时表...';

DROP TABLE IF EXISTS tmp_metadata_backup;

RAISE NOTICE '✓ 临时表已删除';

-- ============================================================================
-- 步骤11：添加表注释
-- ============================================================================

RAISE NOTICE '步骤11：添加表注释...';

COMMENT ON TABLE public.dim_metric_metadata IS
'指标元数据表（三级优先级架构）：
- 全局级：station_id=NULL, device_id=NULL（默认值）
- 站点级：station_id=<id>, device_id=NULL（覆盖全局）
- 设备级：station_id=<id>, device_id=<id>（最高优先级）

查询时按优先级排序：设备级 > 站点级 > 全局级';

COMMENT ON COLUMN public.dim_metric_metadata.station_id IS
'站点ID（NULL表示全局级）';

COMMENT ON COLUMN public.dim_metric_metadata.device_id IS
'设备ID（NULL表示站点级或全局级）';

RAISE NOTICE '✓ 表注释已添加';

-- ============================================================================
-- 完成
-- ============================================================================

RAISE NOTICE '========================================';
RAISE NOTICE '✅ 迁移完成！';
RAISE NOTICE '========================================';
RAISE NOTICE '表结构已改造为三级优先级架构';
RAISE NOTICE '数据已生成：56全局 + 56站点 + 448设备 = 560条';
RAISE NOTICE '下一步：执行 101_alter_v_effective_metric_metadata.sql 修改视图';
RAISE NOTICE '========================================';

COMMIT;

-- ============================================================================
-- 验证查询（执行后可运行）
-- ============================================================================

-- 查看数据分布
-- SELECT
--     CASE
--         WHEN station_id IS NULL AND device_id IS NULL THEN '全局级'
--         WHEN station_id IS NOT NULL AND device_id IS NULL THEN '站点级'
--         WHEN device_id IS NOT NULL THEN '设备级'
--     END AS level,
--     COUNT(*) as count
-- FROM public.dim_metric_metadata
-- GROUP BY
--     CASE
--         WHEN station_id IS NULL AND device_id IS NULL THEN '全局级'
--         WHEN station_id IS NOT NULL AND device_id IS NULL THEN '站点级'
--         WHEN device_id IS NOT NULL THEN '设备级'
--     END
-- ORDER BY
--     CASE
--         WHEN station_id IS NULL AND device_id IS NULL THEN 1
--         WHEN station_id IS NOT NULL AND device_id IS NULL THEN 2
--         WHEN device_id IS NOT NULL THEN 3
--     END;

-- 测试三级优先级查询
-- SELECT
--     metric_id,
--     station_id,
--     device_id,
--     resolution,
--     phys_min,
--     phys_max
-- FROM public.dim_metric_metadata
-- WHERE metric_id = 1
--   AND (device_id = 1 OR device_id IS NULL)
--   AND (station_id = 1 OR station_id IS NULL)
-- ORDER BY (device_id IS NOT NULL) DESC, (station_id IS NOT NULL) DESC
-- LIMIT 1;

