-- =====================================================
-- 更新pump_characteristic_curves表以支持曲线优化
-- =====================================================
-- 用途：添加曲线优化相关字段
-- 作者：System
-- 创建时间：2025-10-05
-- =====================================================

-- 添加曲线版本号字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'pump_characteristic_curves' 
        AND column_name = 'curve_version'
    ) THEN
        ALTER TABLE pump_characteristic_curves 
        ADD COLUMN curve_version INT DEFAULT 1;
        
        COMMENT ON COLUMN pump_characteristic_curves.curve_version IS '曲线版本号，每次优化后递增';
    END IF;
END $$;

-- 添加曲线质量分数字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'pump_characteristic_curves' 
        AND column_name = 'quality_score'
    ) THEN
        ALTER TABLE pump_characteristic_curves 
        ADD COLUMN quality_score NUMERIC;
        
        COMMENT ON COLUMN pump_characteristic_curves.quality_score IS '曲线质量分数（0-1），基于拟合误差和样本数';
    END IF;
END $$;

-- 添加样本数量字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'pump_characteristic_curves' 
        AND column_name = 'sample_count'
    ) THEN
        ALTER TABLE pump_characteristic_curves 
        ADD COLUMN sample_count INT DEFAULT 0;
        
        COMMENT ON COLUMN pump_characteristic_curves.sample_count IS '用于拟合的样本数量';
    END IF;
END $$;

-- 添加最后优化时间字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'pump_characteristic_curves' 
        AND column_name = 'last_optimized_at'
    ) THEN
        ALTER TABLE pump_characteristic_curves 
        ADD COLUMN last_optimized_at TIMESTAMPTZ;
        
        COMMENT ON COLUMN pump_characteristic_curves.last_optimized_at IS '最后一次优化时间';
    END IF;
END $$;

-- 添加优化方法字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'pump_characteristic_curves' 
        AND column_name = 'optimization_method'
    ) THEN
        ALTER TABLE pump_characteristic_curves 
        ADD COLUMN optimization_method TEXT;
        
        COMMENT ON COLUMN pump_characteristic_curves.optimization_method IS '优化方法（polynomial, spline, manual等）';
    END IF;
END $$;

-- 创建索引（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'pump_characteristic_curves' 
        AND indexname = 'idx_pump_curves_version'
    ) THEN
        CREATE INDEX idx_pump_curves_version 
        ON pump_characteristic_curves (device_id, curve_type, curve_version DESC);
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'pump_characteristic_curves' 
        AND indexname = 'idx_pump_curves_last_optimized'
    ) THEN
        CREATE INDEX idx_pump_curves_last_optimized 
        ON pump_characteristic_curves (last_optimized_at);
    END IF;
END $$;

-- 验证更新
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'pump_characteristic_curves'
  AND column_name IN (
      'curve_version', 
      'quality_score', 
      'sample_count',
      'last_optimized_at',
      'optimization_method'
  )
ORDER BY column_name;

COMMIT;

