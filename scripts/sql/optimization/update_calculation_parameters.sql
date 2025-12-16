-- =====================================================
-- 更新calculation_parameters表以支持参数优化
-- =====================================================
-- 用途：添加参数优化相关字段
-- 作者：System
-- 创建时间：2025-10-05
-- =====================================================

-- 添加置信度字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'calculation_parameters' 
        AND column_name = 'confidence_score'
    ) THEN
        ALTER TABLE calculation_parameters 
        ADD COLUMN confidence_score NUMERIC DEFAULT 0.5;
        
        COMMENT ON COLUMN calculation_parameters.confidence_score IS '参数置信度（0-1），越高表示参数越可靠';
    END IF;
END $$;

-- 添加最后优化时间字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'calculation_parameters' 
        AND column_name = 'last_optimized_at'
    ) THEN
        ALTER TABLE calculation_parameters 
        ADD COLUMN last_optimized_at TIMESTAMPTZ;
        
        COMMENT ON COLUMN calculation_parameters.last_optimized_at IS '最后一次优化时间';
    END IF;
END $$;

-- 添加优化次数字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'calculation_parameters' 
        AND column_name = 'optimization_count'
    ) THEN
        ALTER TABLE calculation_parameters 
        ADD COLUMN optimization_count INT DEFAULT 0;
        
        COMMENT ON COLUMN calculation_parameters.optimization_count IS '参数优化次数';
    END IF;
END $$;

-- 添加参数下界字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'calculation_parameters' 
        AND column_name = 'param_min'
    ) THEN
        ALTER TABLE calculation_parameters 
        ADD COLUMN param_min NUMERIC;
        
        COMMENT ON COLUMN calculation_parameters.param_min IS '参数最小值（约束下界）';
    END IF;
END $$;

-- 添加参数上界字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'calculation_parameters' 
        AND column_name = 'param_max'
    ) THEN
        ALTER TABLE calculation_parameters 
        ADD COLUMN param_max NUMERIC;
        
        COMMENT ON COLUMN calculation_parameters.param_max IS '参数最大值（约束上界）';
    END IF;
END $$;

-- 创建索引（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'calculation_parameters' 
        AND indexname = 'idx_calc_params_optimizable'
    ) THEN
        CREATE INDEX idx_calc_params_optimizable 
        ON calculation_parameters (is_optimizable) 
        WHERE is_optimizable = TRUE;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'calculation_parameters' 
        AND indexname = 'idx_calc_params_last_optimized'
    ) THEN
        CREATE INDEX idx_calc_params_last_optimized 
        ON calculation_parameters (last_optimized_at);
    END IF;
END $$;

-- 验证更新
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'calculation_parameters'
  AND column_name IN (
      'confidence_score', 
      'last_optimized_at', 
      'optimization_count',
      'param_min',
      'param_max',
      'is_optimizable',
      'optimization_history'
  )
ORDER BY column_name;

COMMIT;

