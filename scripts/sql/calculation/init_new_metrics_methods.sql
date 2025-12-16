-- =====================================================
-- 缺失指标计算功能 - 初始化新增指标的计算方法
-- =====================================================
-- 创建时间: 2025-10-05
-- 用途: 初始化calculation_method_registry表，录入新增5个指标的计算方法
-- 方法列表:
--   pump_speed: 3种方法（A-C）
--   pump_torque: 2种方法（A-B）
--   main_pipeline_outlet_pressure: 2种方法（A-B）
--   main_pipeline_inlet_pressure: 2种方法（A-B）
--   pump_cumulative_flow: 2种方法（A-B）
-- 总计: 11种方法
-- =====================================================

-- =====================================================
-- pump_speed - 泵转速（3种方法）
-- =====================================================

-- 方法A：相对转速法（推荐用于归一化）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_speed_method_a',
    'pump_speed',
    '相对转速法',
    'A',
    100,  -- 最高优先级
    ARRAY['pump_frequency'],
    '{"description": "用于归一化，适合特性曲线分析"}'::jsonb,
    'docs/计算原理和公式.md#pump_speed方法A',
    'high',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- 方法B：绝对转速法（基于电机学原理）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_speed_method_b',
    'pump_speed',
    '绝对转速法',
    'B',
    90,
    ARRAY['pump_frequency'],
    '{"description": "基于同步电机原理，需要极对数和滑差参数"}'::jsonb,
    'docs/计算原理和公式.md#pump_speed方法B',
    'high',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- 方法C：标定关系法
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_speed_method_c',
    'pump_speed',
    '标定关系法',
    'C',
    80,
    ARRAY['pump_frequency'],
    '{"description": "通过实际测量标定，需要斜率和截距参数"}'::jsonb,
    'docs/计算原理和公式.md#pump_speed方法C',
    'medium',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- =====================================================
-- pump_torque - 泵扭矩（2种方法）
-- =====================================================

-- 方法A：水力功率与转速法（推荐）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_torque_method_a',
    'pump_torque',
    '水力功率与转速法',
    'A',
    100,  -- 最高优先级
    ARRAY['pump_flow_rate', 'pump_head', 'pump_speed'],
    '{"description": "基于水力功率计算，精度高"}'::jsonb,
    'docs/计算原理和公式.md#pump_torque方法A',
    'high',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- 方法B：电功率与频率法
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_torque_method_b',
    'pump_torque',
    '电功率与频率法',
    'B',
    90,
    ARRAY['pump_active_power', 'pump_frequency'],
    '{"description": "基于电功率估算，需要极对数和滑差参数"}'::jsonb,
    'docs/计算原理和公式.md#pump_torque方法B',
    'medium',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- =====================================================
-- main_pipeline_outlet_pressure - 总管出口压力（2种方法）
-- =====================================================

-- 方法A：从泵出口压力推算
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'main_pipeline_outlet_pressure_method_a',
    'main_pipeline_outlet_pressure',
    '从泵出口压力推算',
    'A',
    100,  -- 最高优先级
    ARRAY['pump_outlet_pressure'],
    '{"description": "对于单泵系统或泵组，总管出口压力近似等于泵出口压力"}'::jsonb,
    'docs/计算原理和公式.md#main_pipeline_outlet_pressure方法A',
    'high',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- 方法B：从泵进口压力和扬程推算
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'main_pipeline_outlet_pressure_method_b',
    'main_pipeline_outlet_pressure',
    '从泵进口压力和扬程推算',
    'B',
    90,
    ARRAY['pump_inlet_pressure', 'pump_head'],
    '{"description": "从泵组扬程推算总管出口压力"}'::jsonb,
    'docs/计算原理和公式.md#main_pipeline_outlet_pressure方法B',
    'high',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- =====================================================
-- main_pipeline_inlet_pressure - 总管进口压力（2种方法）
-- =====================================================

-- 方法A：从泵进口压力推算
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'main_pipeline_inlet_pressure_method_a',
    'main_pipeline_inlet_pressure',
    '从泵进口压力推算',
    'A',
    100,  -- 最高优先级
    ARRAY['pump_inlet_pressure'],
    '{"description": "对于单泵系统或泵组，总管进口压力近似等于泵进口压力"}'::jsonb,
    'docs/计算原理和公式.md#main_pipeline_inlet_pressure方法A',
    'high',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- 方法B：从水池液位推算
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'main_pipeline_inlet_pressure_method_b',
    'main_pipeline_inlet_pressure',
    '从水池液位推算',
    'B',
    90,
    ARRAY['pool_liquid_level'],
    '{"description": "从水池液位计算静压"}'::jsonb,
    'docs/计算原理和公式.md#main_pipeline_inlet_pressure方法B',
    'high',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- =====================================================
-- pump_cumulative_flow - 泵累计流量（2种方法）
-- =====================================================

-- 方法A：从瞬时流量积分
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_cumulative_flow_method_a',
    'pump_cumulative_flow',
    '从瞬时流量积分',
    'A',
    100,  -- 最高优先级
    ARRAY['pump_flow_rate'],
    '{"description": "从瞬时流量积分得到累计流量，需要初始值和时间间隔"}'::jsonb,
    'docs/计算原理和公式.md#pump_cumulative_flow方法A',
    'high',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- 方法B：从总管累计流量按比例分摊
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_cumulative_flow_method_b',
    'pump_cumulative_flow',
    '从总管累计流量按比例分摊',
    'B',
    90,
    ARRAY['main_pipeline_cumulative_flow', 'pump_flow_rate', 'main_pipeline_flow_rate'],
    '{"description": "按流量比例分摊总管累计流量"}'::jsonb,
    'docs/计算原理和公式.md#pump_cumulative_flow方法B',
    'medium',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- =====================================================
-- 完成提示
-- =====================================================
SELECT '新增指标计算方法初始化完成！' AS message,
       COUNT(*) AS total_methods
FROM calculation_method_registry
WHERE metric_key IN ('pump_speed', 'pump_torque', 'main_pipeline_outlet_pressure', 
                     'main_pipeline_inlet_pressure', 'pump_cumulative_flow');

