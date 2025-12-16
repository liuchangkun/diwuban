-- ============================================================================
-- 回滚脚本：恢复元数据表为原始两表架构
-- ============================================================================
-- 目标：
--   1. 从数据库备份恢复原始的 dim_metric_metadata 表（56条全局数据）
--   2. 重建 dim_metric_metadata_override 表（空表）
--   3. 恢复原始的 v_effective_metric_metadata 视图
--
-- 警告：
--   - 此脚本会删除所有站点级和设备级的元数据
--   - 只保留全局级的56条数据
--   - 执行前请确保有完整的数据库备份
--
-- 使用场景：
--   - 迁移后发现问题需要回滚
--   - 测试环境验证回滚流程
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
BEGIN
    SELECT COUNT(*) INTO v_metadata_count FROM public.dim_metric_metadata;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE '⚠️  回滚警告';
    RAISE NOTICE '========================================';
    RAISE NOTICE '当前 dim_metric_metadata 表有 % 条记录', v_metadata_count;
    RAISE NOTICE '回滚后将只保留 56 条全局级数据';
    RAISE NOTICE '所有站点级和设备级数据将被删除';
    RAISE NOTICE '========================================';
    
    IF v_metadata_count < 56 THEN
        RAISE EXCEPTION '❌ 数据量异常：少于56条，无法回滚';
    END IF;
END $$;

-- ============================================================================
-- 步骤2：备份当前全局级数据
-- ============================================================================

RAISE NOTICE '步骤2：备份全局级数据...';

DROP TABLE IF EXISTS tmp_global_metadata_backup CASCADE;

CREATE TEMP TABLE tmp_global_metadata_backup AS
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
FROM public.dim_metric_metadata
WHERE station_id IS NULL AND device_id IS NULL;

-- 验证备份
DO $$
DECLARE
    v_backup_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_backup_count FROM tmp_global_metadata_backup;
    IF v_backup_count != 56 THEN
        RAISE EXCEPTION '❌ 全局级数据备份失败：期望56条，实际%条', v_backup_count;
    END IF;
    RAISE NOTICE '✓ 全局级数据备份成功：56条';
END $$;

-- ============================================================================
-- 步骤3：删除视图
-- ============================================================================

RAISE NOTICE '步骤3：删除当前视图...';

DROP VIEW IF EXISTS public.v_effective_metric_metadata CASCADE;

RAISE NOTICE '✓ 视图已删除';

-- ============================================================================
-- 步骤4：删除 dim_metric_metadata 表的外键和主键
-- ============================================================================

RAISE NOTICE '步骤4：删除外键和主键...';

ALTER TABLE public.dim_metric_metadata
    DROP CONSTRAINT IF EXISTS dim_metric_metadata_pkey CASCADE,
    DROP CONSTRAINT IF EXISTS fk_metadata_station CASCADE,
    DROP CONSTRAINT IF EXISTS fk_metadata_device CASCADE;

RAISE NOTICE '✓ 外键和主键已删除';

-- ============================================================================
-- 步骤5：删除 station_id 和 device_id 字段
-- ============================================================================

RAISE NOTICE '步骤5：删除 station_id 和 device_id 字段...';

-- 先删除所有非全局级数据
DELETE FROM public.dim_metric_metadata
WHERE station_id IS NOT NULL OR device_id IS NOT NULL;

-- 删除字段
ALTER TABLE public.dim_metric_metadata
    DROP COLUMN IF EXISTS station_id CASCADE,
    DROP COLUMN IF EXISTS device_id CASCADE;

RAISE NOTICE '✓ station_id 和 device_id 字段已删除';

-- ============================================================================
-- 步骤6：恢复原始主键
-- ============================================================================

RAISE NOTICE '步骤6：恢复原始主键...';

ALTER TABLE public.dim_metric_metadata
    ADD CONSTRAINT dim_metric_metadata_pkey PRIMARY KEY (metric_id);

RAISE NOTICE '✓ 原始主键已恢复';

-- ============================================================================
-- 步骤7：验证数据
-- ============================================================================

RAISE NOTICE '步骤7：验证数据...';

DO $$
DECLARE
    v_final_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_final_count FROM public.dim_metric_metadata;
    
    IF v_final_count != 56 THEN
        RAISE EXCEPTION '❌ 数据验证失败：期望56条，实际%条', v_final_count;
    END IF;
    
    RAISE NOTICE '✓ 数据验证通过：56条全局级数据';
END $$;

-- ============================================================================
-- 步骤8：重建 dim_metric_metadata_override 表
-- ============================================================================

RAISE NOTICE '步骤8：重建 dim_metric_metadata_override 表...';

CREATE TABLE IF NOT EXISTS public.dim_metric_metadata_override (
    rule_id bigserial PRIMARY KEY,
    station_id bigint NULL REFERENCES public.dim_stations(id) ON DELETE CASCADE,
    device_id bigint NULL REFERENCES public.dim_devices(id) ON DELETE CASCADE,
    metric_id bigint NOT NULL REFERENCES public.dim_metric_config(id) ON DELETE CASCADE,
    resolution double precision NULL,
    phys_min double precision NULL,
    phys_max double precision NULL,
    saturation_min double precision NULL,
    saturation_max double precision NULL,
    remark text NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by text NULL,
    CONSTRAINT uk_override_scope UNIQUE (station_id, device_id, metric_id)
);

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_override_station_metric
    ON public.dim_metric_metadata_override(station_id, metric_id)
    WHERE station_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_override_device_metric
    ON public.dim_metric_metadata_override(device_id, metric_id)
    WHERE device_id IS NOT NULL;

-- 添加注释
COMMENT ON TABLE public.dim_metric_metadata_override IS
'指标元数据覆盖表：为特定站点/设备提供定制化的元数据覆盖';

RAISE NOTICE '✓ dim_metric_metadata_override 表已重建（空表）';

-- ============================================================================
-- 步骤9：恢复原始视图
-- ============================================================================

RAISE NOTICE '步骤9：恢复原始视图...';

CREATE OR REPLACE VIEW public.v_effective_metric_metadata AS
WITH base AS (
  SELECT metric_id, unit, resolution, phys_min, phys_max, saturation_min, saturation_max
  FROM public.dim_metric_metadata
),
-- 设备级覆盖
od AS (
  SELECT device_id, metric_id, resolution, phys_min, phys_max, saturation_min, saturation_max
  FROM public.dim_metric_metadata_override WHERE device_id IS NOT NULL
),
-- 站点级覆盖
os AS (
  SELECT station_id, metric_id, resolution, phys_min, phys_max, saturation_min, saturation_max
  FROM public.dim_metric_metadata_override WHERE device_id IS NULL AND station_id IS NOT NULL
)
SELECT
  COALESCE(od.device_id, NULL) AS device_id,
  COALESCE(os.station_id, NULL) AS station_id,
  b.metric_id,
  b.unit,
  COALESCE(od.resolution, os.resolution, b.resolution) AS resolution,
  COALESCE(od.phys_min,   os.phys_min,   b.phys_min)   AS phys_min,
  COALESCE(od.phys_max,   os.phys_max,   b.phys_max)   AS phys_max,
  COALESCE(od.saturation_min, os.saturation_min, b.saturation_min) AS saturation_min,
  COALESCE(od.saturation_max, os.saturation_max, b.saturation_max) AS saturation_max
FROM base b
LEFT JOIN os ON os.metric_id=b.metric_id
LEFT JOIN od ON od.metric_id=b.metric_id;

COMMENT ON VIEW public.v_effective_metric_metadata IS
'有效指标元数据视图：按优先级(设备>站点>全局)合并覆盖，供算法统一读取。';

RAISE NOTICE '✓ 原始视图已恢复';

-- ============================================================================
-- 步骤10：验证视图
-- ============================================================================

RAISE NOTICE '步骤10：验证视图...';

DO $$
DECLARE
    v_view_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_view_count FROM public.v_effective_metric_metadata;

    IF v_view_count != 56 THEN
        RAISE EXCEPTION '❌ 视图验证失败：期望56条，实际%条', v_view_count;
    END IF;

    RAISE NOTICE '✓ 视图验证通过：56条记录';
END $$;

-- ============================================================================
-- 步骤11：删除临时表
-- ============================================================================

RAISE NOTICE '步骤11：清理临时表...';

DROP TABLE IF EXISTS tmp_global_metadata_backup;

RAISE NOTICE '✓ 临时表已删除';

-- ============================================================================
-- 完成
-- ============================================================================

RAISE NOTICE '========================================';
RAISE NOTICE '✅ 回滚完成！';
RAISE NOTICE '========================================';
RAISE NOTICE '已恢复为原始两表架构：';
RAISE NOTICE '  - dim_metric_metadata: 56条全局数据';
RAISE NOTICE '  - dim_metric_metadata_override: 空表';
RAISE NOTICE '  - v_effective_metric_metadata: 原始视图';
RAISE NOTICE '========================================';

COMMIT;

-- ============================================================================
-- 验证查询（执行后可运行）
-- ============================================================================

-- 验证表结构
-- \d public.dim_metric_metadata
-- \d public.dim_metric_metadata_override

-- 验证数据量
-- SELECT COUNT(*) FROM public.dim_metric_metadata;
-- SELECT COUNT(*) FROM public.dim_metric_metadata_override;
-- SELECT COUNT(*) FROM public.v_effective_metric_metadata;

