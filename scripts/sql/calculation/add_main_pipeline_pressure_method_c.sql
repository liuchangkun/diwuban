-- 添加main_pipeline压力指标的方法C（泵站级聚合方法）
-- 这些方法用于多泵并联系统的总管压力计算

-- 1. 添加main_pipeline_outlet_pressure_method_c（总管出口压力 - 泵站级聚合）
INSERT INTO calculation_method_registry (
    metric_key,
    method_id,
    method_name,
    method_code,
    priority,
    dependencies,
    formula_ref,
    accuracy_level,
    is_enabled
) VALUES (
    'main_pipeline_outlet_pressure',
    'main_pipeline_outlet_pressure_method_c',
    '多泵出口压力聚合法（泵站级）',
    '从多个泵的出口压力聚合计算总管出口压力。物理意义：并联泵组的总管出口压力由压力最高的泵决定，因此取最大值。适用于多泵并联系统。',
    110,  -- 优先级高于方法A和B
    ARRAY['pump_outlet_pressure'],  -- 需要所有泵的出口压力数据
    'P_main_out = max(P_pump1_out, P_pump2_out, ..., P_pumpN_out)',
    'high',
    true
) ON CONFLICT (method_id)
DO UPDATE SET
    method_name = EXCLUDED.method_name,
    method_code = EXCLUDED.method_code,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    formula_ref = EXCLUDED.formula_ref,
    accuracy_level = EXCLUDED.accuracy_level,
    is_enabled = EXCLUDED.is_enabled,
    updated_at = NOW();

-- 2. 添加main_pipeline_inlet_pressure_method_c（总管进口压力 - 泵站级聚合）
INSERT INTO calculation_method_registry (
    metric_key,
    method_id,
    method_name,
    method_code,
    priority,
    dependencies,
    formula_ref,
    accuracy_level,
    is_enabled
) VALUES (
    'main_pipeline_inlet_pressure',
    'main_pipeline_inlet_pressure_method_c',
    '多泵进口压力聚合法（泵站级）',
    '从多个泵的进口压力聚合计算总管进口压力。物理意义：并联泵组的总管进口压力取各泵进口压力的平均值（因为进口压力相对稳定，各泵进口压力应该接近）。适用于多泵并联系统。',
    110,  -- 优先级高于方法A
    ARRAY['pump_inlet_pressure'],  -- 需要所有泵的进口压力数据
    'P_main_in = mean(P_pump1_in, P_pump2_in, ..., P_pumpN_in)',
    'high',
    true
) ON CONFLICT (method_id)
DO UPDATE SET
    method_name = EXCLUDED.method_name,
    method_code = EXCLUDED.method_code,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    formula_ref = EXCLUDED.formula_ref,
    accuracy_level = EXCLUDED.accuracy_level,
    is_enabled = EXCLUDED.is_enabled,
    updated_at = NOW();

-- 3. 方法C的参数配置
-- 注意：aggregation_method参数在代码中硬编码（出口压力用max，进口压力用mean）
-- 因为calculation_parameters表的param_value字段是numeric类型，不支持字符串
-- 如果需要可配置，可以使用数字编码（0=max, 1=mean）或修改表结构

-- 4. 更新方法A和B的说明，标注为设备级方法

UPDATE calculation_method_registry
SET
    method_code = '从单泵出口压力推算总管出口压力。适用于单泵系统。注意：这是设备级方法，不适用于多泵并联系统，多泵系统应使用方法C。',
    updated_at = NOW()
WHERE metric_key = 'main_pipeline_outlet_pressure'
  AND method_id = 'main_pipeline_outlet_pressure_method_a';

UPDATE calculation_method_registry
SET
    method_code = '从泵进口压力和扬程推算总管出口压力。适用于单泵系统。注意：这是设备级方法，不适用于多泵并联系统，多泵系统应使用方法C。',
    updated_at = NOW()
WHERE metric_key = 'main_pipeline_outlet_pressure'
  AND method_id = 'main_pipeline_outlet_pressure_method_b';

UPDATE calculation_method_registry
SET
    method_code = '从单泵进口压力推算总管进口压力。适用于单泵系统。注意：这是设备级方法，不适用于多泵并联系统，多泵系统应使用方法C。',
    updated_at = NOW()
WHERE metric_key = 'main_pipeline_inlet_pressure'
  AND method_id = 'main_pipeline_inlet_pressure_method_a';

-- 5. 验证更新结果
SELECT
    metric_key,
    method_id,
    method_name,
    priority,
    is_enabled
FROM calculation_method_registry
WHERE metric_key IN ('main_pipeline_outlet_pressure', 'main_pipeline_inlet_pressure')
ORDER BY metric_key, priority DESC;

