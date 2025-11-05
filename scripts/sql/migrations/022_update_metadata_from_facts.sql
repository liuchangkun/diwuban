-- ============================================================================
-- 从 fact_measurements 数据计算并更新元数据
-- ============================================================================
-- 目的：基于实际数据自动计算物理边界和饱和阈值
-- 执行时机：在 prepare_dim_stage2 阶段（merge-fact 后）
-- 策略：使用 p01/p99 分位数而非 MIN/MAX，避免异常值影响
-- ============================================================================

-- 步骤1：计算每个指标的统计数据（基于所有设备的数据）
WITH metric_stats AS (
    SELECT 
        metric_id,
        -- 使用分位数避免异常值
        percentile_cont(0.01) WITHIN GROUP (ORDER BY value) AS p01,
        percentile_cont(0.99) WITHIN GROUP (ORDER BY value) AS p99,
        percentile_cont(0.001) WITHIN GROUP (ORDER BY value) AS p001,
        percentile_cont(0.999) WITHIN GROUP (ORDER BY value) AS p999,
        -- 计算实际最小值和最大值（用于参考）
        MIN(value) AS actual_min,
        MAX(value) AS actual_max,
        -- 计算标准差（用于确定安全边距）
        STDDEV(value) AS stddev,
        -- 计数
        COUNT(*) AS sample_count
    FROM public.fact_measurements
    WHERE quality_status IN (0, 1)  -- 只使用 GOOD 和 SUSPECT 数据
      AND value IS NOT NULL
    GROUP BY metric_id
)
-- 步骤2：更新 dim_metric_metadata 表
UPDATE public.dim_metric_metadata AS t
SET 
    -- 物理边界：使用 p01 - 3*stddev 和 p99 + 3*stddev（3-sigma规则）
    -- 确保边界不会过于严格，留有足够的安全边距
    phys_min = CASE 
        WHEN s.stddev > 0 THEN LEAST(s.p01 - 3 * s.stddev, s.actual_min)
        ELSE s.actual_min
    END,
    phys_max = CASE 
        WHEN s.stddev > 0 THEN GREATEST(s.p99 + 3 * s.stddev, s.actual_max)
        ELSE s.actual_max
    END,
    
    -- 饱和阈值：使用 p001 和 p999（更极端的分位数）
    -- 这些值用于检测传感器饱和（接近物理极限）
    saturation_min = s.p001,
    saturation_max = s.p999,
    
    -- 更新时间戳和备注
    updated_at = now(),
    remark = COALESCE(t.remark, '') ||
             CASE
                 WHEN COALESCE(t.remark, '') = '' THEN ''
                 ELSE ' | '
             END ||
             format('自动计算: n=%s, p01=%s, p99=%s, σ=%s',
                    s.sample_count,
                    ROUND(s.p01::numeric, 2),
                    ROUND(s.p99::numeric, 2),
                    ROUND(COALESCE(s.stddev, 0)::numeric, 2))
FROM metric_stats s
WHERE t.metric_id = s.metric_id
  AND s.sample_count >= 100;  -- 只更新有足够样本的指标（至少100个数据点）


