-- =====================================================
-- 优先级1.1修复 - 步骤2：更新 metric_calculation_order
-- =====================================================
-- 说明：更新 pump_inlet_pressure 的依赖关系和计算顺序
-- 执行时间：2025-10-25
-- 执行人员：AI Agent (manual_fix_1.1_step2)
-- =====================================================

BEGIN;

-- 更新 pump_inlet_pressure 的依赖关系
-- 注意：depends_on 只包含优先级最高的方法（方法B）的依赖，即 pool_liquid_level
-- 不包含 main_pipeline_inlet_pressure，避免循环依赖
UPDATE metric_calculation_order
SET
    depends_on = ARRAY['pool_liquid_level'],
    priority = 1,
    order_index = 1,
    updated_at = NOW()
WHERE metric_key = 'pump_inlet_pressure';

COMMIT;

-- =====================================================
-- 验证查询
-- =====================================================
-- 验证更新成功
-- SELECT metric_key, depends_on, priority, order_index
-- FROM metric_calculation_order
-- WHERE metric_key = 'pump_inlet_pressure';

-- 预期结果：
-- depends_on=['pool_liquid_level']
-- priority=1
-- order_index=1（不再是0）

