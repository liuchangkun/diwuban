-- ============================================================================
-- 视图修改脚本：简化 v_effective_metric_metadata 视图
-- ============================================================================
-- 目标：
--   1. 删除旧的视图定义（基于两表合并）
--   2. 创建新的视图定义（直接映射单表）
--   3. 保持输出字段顺序和名称不变，确保向后兼容
--
-- 依赖：
--   - 必须在 100_migrate_metadata_to_three_tier.sql 执行后运行
--   - dim_metric_metadata 表已改造为三级优先级架构
--
-- 作者：AI Assistant
-- 日期：2025-01-07
-- ============================================================================

BEGIN;

-- ============================================================================
-- 步骤1：删除旧视图
-- ============================================================================

RAISE NOTICE '步骤1：删除旧视图...';

DROP VIEW IF EXISTS public.v_effective_metric_metadata CASCADE;

RAISE NOTICE '✓ 旧视图已删除';

-- ============================================================================
-- 步骤2：创建新视图（简化版）
-- ============================================================================

RAISE NOTICE '步骤2：创建新视图...';

CREATE OR REPLACE VIEW public.v_effective_metric_metadata AS
SELECT 
    station_id,
    device_id,
    metric_id,
    unit,
    resolution,
    phys_min,
    phys_max,
    saturation_min,
    saturation_max
FROM public.dim_metric_metadata;

RAISE NOTICE '✓ 新视图已创建';

-- ============================================================================
-- 步骤3：添加视图注释
-- ============================================================================

RAISE NOTICE '步骤3：添加视图注释...';

COMMENT ON VIEW public.v_effective_metric_metadata IS 
'有效指标元数据视图（三级优先级架构）：
- 直接映射 dim_metric_metadata 表
- 支持三级优先级查询：设备级 > 站点级 > 全局级
- 查询时使用 LEFT JOIN LATERAL + ORDER BY 实现优先级

典型查询模式：
  LEFT JOIN LATERAL (
    SELECT resolution, phys_min, phys_max
    FROM v_effective_metric_metadata vm
    WHERE vm.metric_id = f.metric_id
      AND (vm.device_id = f.device_id OR vm.device_id IS NULL)
      AND (vm.station_id = f.station_id OR vm.station_id IS NULL)
    ORDER BY (vm.device_id IS NOT NULL) DESC, (vm.station_id IS NOT NULL) DESC
    LIMIT 1
  ) meta ON TRUE

注意事项：
- 视图返回所有560条记录（56全局 + 56站点 + 448设备）
- 查询时必须使用 ORDER BY 和 LIMIT 1 确保优先级正确
- 字段顺序与原视图保持一致，确保向后兼容';

RAISE NOTICE '✓ 视图注释已添加';

-- ============================================================================
-- 步骤4：验证视图
-- ============================================================================

RAISE NOTICE '步骤4：验证视图...';

DO $$
DECLARE
    v_view_count INTEGER;
    v_expected_count INTEGER;
    v_device_count INTEGER;
BEGIN
    -- 获取设备数量
    SELECT COUNT(*) INTO v_device_count FROM public.dim_devices;
    v_expected_count := 56 + 56 + (v_device_count * 56);
    
    -- 查询视图记录数
    SELECT COUNT(*) INTO v_view_count FROM public.v_effective_metric_metadata;
    
    IF v_view_count != v_expected_count THEN
        RAISE EXCEPTION '❌ 视图记录数不正确：期望%条，实际%条', v_expected_count, v_view_count;
    END IF;
    
    RAISE NOTICE '✓ 视图验证通过：%条记录', v_view_count;
END $$;

-- ============================================================================
-- 完成
-- ============================================================================

RAISE NOTICE '========================================';
RAISE NOTICE '✅ 视图修改完成！';
RAISE NOTICE '========================================';
RAISE NOTICE '视图已简化为直接映射 dim_metric_metadata 表';
RAISE NOTICE '查询性能已优化（无JOIN操作）';
RAISE NOTICE '向后兼容性已保持（字段顺序和名称不变）';
RAISE NOTICE '下一步：修改 prepare_dim 代码，移除备份逻辑';
RAISE NOTICE '========================================';

COMMIT;

-- ============================================================================
-- 验证查询（执行后可运行）
-- ============================================================================

-- 查看视图结构
-- \d+ public.v_effective_metric_metadata

-- 测试三级优先级查询（设备级）
-- SELECT * FROM public.v_effective_metric_metadata
-- WHERE metric_id = 1
--   AND (device_id = 1 OR device_id IS NULL)
--   AND (station_id = 1 OR station_id IS NULL)
-- ORDER BY (device_id IS NOT NULL) DESC, (station_id IS NOT NULL) DESC
-- LIMIT 1;

-- 测试三级优先级查询（站点级，假设设备2没有设备级数据）
-- SELECT * FROM public.v_effective_metric_metadata
-- WHERE metric_id = 1
--   AND (device_id = 999 OR device_id IS NULL)  -- 不存在的设备
--   AND (station_id = 1 OR station_id IS NULL)
-- ORDER BY (device_id IS NOT NULL) DESC, (station_id IS NOT NULL) DESC
-- LIMIT 1;

-- 测试三级优先级查询（全局级）
-- SELECT * FROM public.v_effective_metric_metadata
-- WHERE metric_id = 1
--   AND (device_id = 999 OR device_id IS NULL)  -- 不存在的设备
--   AND (station_id = 999 OR station_id IS NULL)  -- 不存在的站点
-- ORDER BY (device_id IS NOT NULL) DESC, (station_id IS NOT NULL) DESC
-- LIMIT 1;

