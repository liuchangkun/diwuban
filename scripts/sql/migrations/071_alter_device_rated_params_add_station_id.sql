-- 目的：为 device_rated_params 表添加 station_id 字段，支持三级参数体系（全局→泵站→设备）
-- 影响：device_rated_params 表结构变更，需要重建唯一约束
-- 依赖：dim_stations 表必须存在

BEGIN;

-- ============================================================================
-- 步骤1：添加 station_id 字段 + 修改 device_id 允许 NULL
-- ============================================================================
DO $$
BEGIN
    -- 1.1 添加 station_id 字段
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'device_rated_params'
          AND column_name = 'station_id'
    ) THEN
        ALTER TABLE public.device_rated_params
        ADD COLUMN station_id BIGINT;

        RAISE NOTICE '✓ 已添加 station_id 字段';
    ELSE
        RAISE NOTICE '⊙ station_id 字段已存在，跳过';
    END IF;

    -- 1.2 修改 device_id 允许 NULL（支持泵站级和全局级参数）
    ALTER TABLE public.device_rated_params
    ALTER COLUMN device_id DROP NOT NULL;

    RAISE NOTICE '✓ 已修改 device_id 允许 NULL';
END $$;

-- ============================================================================
-- 步骤2：迁移现有数据（从 dim_devices 获取 station_id）
-- ============================================================================
UPDATE public.device_rated_params drp
SET station_id = d.station_id
FROM public.dim_devices d
WHERE drp.device_id = d.id
  AND drp.station_id IS NULL;

-- 验证迁移结果
DO $$
DECLARE
    v_null_count INT;
BEGIN
    SELECT COUNT(*) INTO v_null_count
    FROM public.device_rated_params
    WHERE device_id IS NOT NULL AND station_id IS NULL;
    
    IF v_null_count > 0 THEN
        RAISE WARNING '⚠ 发现 % 行设备级参数的 station_id 仍为 NULL', v_null_count;
    ELSE
        RAISE NOTICE '✓ 所有设备级参数的 station_id 已成功迁移';
    END IF;
END $$;

-- ============================================================================
-- 步骤3：删除旧的唯一约束
-- ============================================================================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_device_param'
          AND conrelid = 'public.device_rated_params'::regclass
    ) THEN
        ALTER TABLE public.device_rated_params 
        DROP CONSTRAINT uq_device_param;
        
        RAISE NOTICE '✓ 已删除旧约束 uq_device_param';
    ELSE
        RAISE NOTICE '⊙ 旧约束 uq_device_param 不存在，跳过';
    END IF;
END $$;

-- ============================================================================
-- 步骤4：添加新的唯一索引（支持三级参数，使用表达式索引）
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = 'device_rated_params'
          AND indexname = 'uq_device_rated_params_3tier'
    ) THEN
        CREATE UNIQUE INDEX uq_device_rated_params_3tier
        ON public.device_rated_params (
            COALESCE(station_id, 0),
            COALESCE(device_id, 0),
            param_key,
            COALESCE(effective_from, '1970-01-01'::timestamptz)
        );

        RAISE NOTICE '✓ 已添加新唯一索引 uq_device_rated_params_3tier';
    ELSE
        RAISE NOTICE '⊙ 新唯一索引 uq_device_rated_params_3tier 已存在，跳过';
    END IF;
END $$;

-- ============================================================================
-- 步骤5：添加外键约束
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_device_rated_params_stations'
          AND conrelid = 'public.device_rated_params'::regclass
    ) THEN
        ALTER TABLE public.device_rated_params 
        ADD CONSTRAINT fk_device_rated_params_stations 
        FOREIGN KEY (station_id) 
        REFERENCES public.dim_stations(id) 
        ON UPDATE CASCADE 
        ON DELETE CASCADE;
        
        RAISE NOTICE '✓ 已添加外键约束 fk_device_rated_params_stations';
    ELSE
        RAISE NOTICE '⊙ 外键约束 fk_device_rated_params_stations 已存在，跳过';
    END IF;
END $$;

-- ============================================================================
-- 步骤6：添加列注释
-- ============================================================================
COMMENT ON COLUMN public.device_rated_params.station_id IS '泵站ID，NULL表示全局参数';

-- ============================================================================
-- 步骤7：插入泵站级参数（管道参数 + 环境参数）
-- ============================================================================

-- 7.1 管道参数（泵站级）
INSERT INTO public.device_rated_params (
    station_id, device_id, param_key, value_numeric, unit, source, created_at, updated_at
)
SELECT 
    1 as station_id,
    NULL as device_id,
    param_key,
    value_numeric,
    unit,
    'migration:071:station_level' as source,
    now() as created_at,
    now() as updated_at
FROM (VALUES
    ('pipe_diameter', 0.8, 'm'),
    ('pipe_length', 500.0, 'm'),
    ('roughness_rel', 0.0002, NULL),
    ('C_hazen', 120.0, NULL)
) AS params(param_key, value_numeric, unit)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), param_key, COALESCE(effective_from, '1970-01-01'::timestamptz))
DO NOTHING;

-- 7.2 环境参数（泵站级）
INSERT INTO public.device_rated_params (
    station_id, device_id, param_key, value_numeric, unit, source, created_at, updated_at
)
SELECT 
    1 as station_id,
    NULL as device_id,
    param_key,
    value_numeric,
    unit,
    'migration:071:station_level' as source,
    now() as created_at,
    now() as updated_at
FROM (VALUES
    ('ambient_temp', 20.0, '°C'),
    ('ambient_pressure', 101.325, 'kPa')
) AS params(param_key, value_numeric, unit)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), param_key, COALESCE(effective_from, '1970-01-01'::timestamptz))
DO NOTHING;

-- ============================================================================
-- 步骤8：验证三级参数体系
-- ============================================================================
DO $$
DECLARE
    v_global_count INT;
    v_station_count INT;
    v_device_count INT;
BEGIN
    -- 统计全局参数
    SELECT COUNT(*) INTO v_global_count
    FROM public.device_rated_params
    WHERE station_id IS NULL AND device_id IS NULL;
    
    -- 统计泵站级参数
    SELECT COUNT(*) INTO v_station_count
    FROM public.device_rated_params
    WHERE station_id IS NOT NULL AND device_id IS NULL;
    
    -- 统计设备级参数
    SELECT COUNT(*) INTO v_device_count
    FROM public.device_rated_params
    WHERE station_id IS NOT NULL AND device_id IS NOT NULL;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE '三级参数体系验证结果：';
    RAISE NOTICE '  全局级参数：% 行', v_global_count;
    RAISE NOTICE '  泵站级参数：% 行', v_station_count;
    RAISE NOTICE '  设备级参数：% 行', v_device_count;
    RAISE NOTICE '  总计：% 行', v_global_count + v_station_count + v_device_count;
    RAISE NOTICE '========================================';
END $$;

COMMIT;

-- ============================================================================
-- 迁移完成
-- ============================================================================
-- 版本：v071
-- 日期：2025-11-02
-- 说明：device_rated_params 表已支持三级参数体系（全局→泵站→设备）
-- 新增泵站级参数：pipe_diameter, pipe_length, roughness_rel, C_hazen, ambient_temp, ambient_pressure
-- ============================================================================

