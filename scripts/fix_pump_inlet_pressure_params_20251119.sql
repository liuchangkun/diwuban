-- ============================================================================
-- 修正 pump_inlet_pressure 参数配置
-- 日期: 2025-11-19
-- 说明: 修正公式错误后的参数更新
-- ============================================================================

-- 开始事务
BEGIN;

-- ============================================================================
-- 1. 更新设备级参数: pipe_diameter (0.3 → 0.6)
-- ============================================================================
UPDATE calculation_parameters
SET 
    param_value = '0.6',
    updated_at = NOW(),
    updated_by = 'fix_pump_inlet_pressure_20251119'
WHERE 
    metric_key = 'pump_inlet_pressure'
    AND param_name = 'pipe_diameter'
    AND device_id IN (1, 2, 3, 4, 5, 6);

-- 验证更新
DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO updated_count
    FROM calculation_parameters
    WHERE metric_key = 'pump_inlet_pressure'
      AND param_name = 'pipe_diameter'
      AND device_id IN (1, 2, 3, 4, 5, 6)
      AND param_value = '0.6';
    
    RAISE NOTICE '✓ pipe_diameter 更新完成: % 个设备', updated_count;
    
    IF updated_count != 6 THEN
        RAISE EXCEPTION 'pipe_diameter 更新失败: 期望6个，实际%个', updated_count;
    END IF;
END $$;

-- ============================================================================
-- 2. 更新设备级参数: L_offset (12.0 → 2.25)
-- ============================================================================
UPDATE calculation_parameters
SET 
    param_value = '2.25',
    updated_at = NOW(),
    updated_by = 'fix_pump_inlet_pressure_20251119'
WHERE 
    metric_key = 'pump_inlet_pressure'
    AND param_name = 'L_offset'
    AND device_id IN (1, 2, 3, 4, 5, 6);

-- 验证更新
DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO updated_count
    FROM calculation_parameters
    WHERE metric_key = 'pump_inlet_pressure'
      AND param_name = 'L_offset'
      AND device_id IN (1, 2, 3, 4, 5, 6)
      AND param_value = '2.25';
    
    RAISE NOTICE '✓ L_offset 更新完成: % 个设备', updated_count;
    
    IF updated_count != 6 THEN
        RAISE EXCEPTION 'L_offset 更新失败: 期望6个，实际%个', updated_count;
    END IF;
END $$;

-- ============================================================================
-- 3. 更新全局参数: K_eq (3.0 → 0.65)
-- ============================================================================
UPDATE calculation_parameters
SET 
    param_value = '0.65',
    updated_at = NOW(),
    updated_by = 'fix_pump_inlet_pressure_20251119'
WHERE 
    metric_key = 'pump_inlet_pressure'
    AND param_name = 'K_eq'
    AND device_id IS NULL;

-- 验证更新
DO $$
DECLARE
    updated_count INTEGER;
    new_value TEXT;
BEGIN
    SELECT COUNT(*), MAX(param_value) INTO updated_count, new_value
    FROM calculation_parameters
    WHERE metric_key = 'pump_inlet_pressure'
      AND param_name = 'K_eq'
      AND device_id IS NULL
      AND param_value = '0.65';
    
    RAISE NOTICE '✓ K_eq 更新完成: 新值 = %', new_value;
    
    IF updated_count != 1 THEN
        RAISE EXCEPTION 'K_eq 更新失败: 期望1个，实际%个', updated_count;
    END IF;
END $$;

-- ============================================================================
-- 4. 最终验证：显示所有更新后的参数
-- ============================================================================
DO $$
DECLARE
    rec RECORD;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '参数更新结果汇总';
    RAISE NOTICE '========================================';
    
    FOR rec IN (
        SELECT 
            COALESCE(device_id::text, 'GLOBAL') as device,
            param_name,
            param_value,
            updated_by
        FROM calculation_parameters
        WHERE metric_key = 'pump_inlet_pressure'
          AND param_name IN ('pipe_diameter', 'L_offset', 'K_eq')
        ORDER BY 
            CASE WHEN device_id IS NULL THEN 0 ELSE 1 END,
            device_id,
            param_name
    ) LOOP
        RAISE NOTICE '  % | % = % (by: %)', 
            rec.device, rec.param_name, rec.param_value, rec.updated_by;
    END LOOP;
    
    RAISE NOTICE '========================================';
END $$;

-- 提交事务
COMMIT;

RAISE NOTICE '';
RAISE NOTICE '✅ 所有参数更新成功！';

