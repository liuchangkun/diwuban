-- =====================================================
-- 缺失指标计算功能 - 补充计算方法注册表
-- =====================================================
-- 创建时间: 2025-01-19
-- 用途: 补充 init_methods.sql 中缺失的5个计算方法
-- 方法列表:
--   pump_speed: method_c（标定关系法）
--   pump_torque: method_b（电功率与频率法）
--   pump_cumulative_flow: method_b（从总管累计流量按比例分摊）
--   pump_head: HEAD_COEF_V1（新的泵扬程计算方法）
--   main_pipeline_inlet_pressure: PIN_COEF_V1（新的总管进口压力计算方法）
-- 总计: 5种方法
-- =====================================================

-- =====================================================
-- pump_speed - 泵转速（补充 method_c）
-- =====================================================

-- 方法C：标定关系法
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_speed_method_c',
    'pump_speed',
    '标定关系法',
    'C',
    80,  -- 优先级低于 method_a 和 method_b
    ARRAY['pump_frequency'],
    '{"description": "n = a × f + b，需要标定参数", "calibration_a": 30.0, "calibration_b": 0.0}'::jsonb,
    'docs/计算原理和公式.md#泵转速',
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
-- pump_torque - 泵扭矩（补充 method_b）
-- =====================================================

-- 方法B：电功率与频率法
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_torque_method_b',
    'pump_torque',
    '电功率与频率法',
    'B',
    90,  -- 优先级低于 method_a
    ARRAY['pump_active_power', 'pump_frequency'],
    '{"description": "T = P_in × 1000 / ω，ω = 2π × n / 60，n = 120 × f / P × (1 - s)", "pole_pairs": 2, "slip": 0.02}'::jsonb,
    'docs/计算原理和公式.md#泵扭矩',
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
-- pump_cumulative_flow - 泵累计流量（补充 method_b）
-- =====================================================

-- 方法B：从总管累计流量按比例分摊
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_cumulative_flow_method_b',
    'pump_cumulative_flow',
    '从总管累计流量按比例分摊',
    'B',
    90,  -- 优先级低于 method_a
    ARRAY['main_pipeline_cumulative_flow', 'pump_flow_rate', 'main_pipeline_flow_rate'],
    '{"description": "V_pump = V_main × (Q_pump / Q_main)"}'::jsonb,
    'docs/计算原理和公式.md#泵累计流量',
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
-- pump_head - 泵扬程（补充 HEAD_COEF_V1）
-- =====================================================

-- HEAD_COEF_V1：新的泵扬程计算方法（替代 method_main）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'HEAD_COEF_V1',
    'pump_head',
    '压差计算（新版）',
    'HEAD_COEF_V1',
    110,  -- 优先级高于 method_main
    ARRAY['pump_outlet_pressure', 'pump_inlet_pressure'],
    '{"description": "H = (P_out - P_in) × 1e6 / (ρ × g)，新版实现"}'::jsonb,
    'docs/计算原理和公式.md#泵扬程',
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
-- main_pipeline_inlet_pressure - 总管进口压力（补充 PIN_COEF_V1）
-- =====================================================

-- PIN_COEF_V1：新的总管进口压力计算方法
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'PIN_COEF_V1',
    'main_pipeline_inlet_pressure',
    '综合计算（新版）',
    'PIN_COEF_V1',
    110,  -- 优先级高于 method_a, method_b, method_c
    ARRAY['pump_inlet_pressure', 'pool_liquid_level'],
    '{"description": "综合多种数据源计算总管进口压力，新版实现"}'::jsonb,
    'docs/计算原理和公式.md#总管进口压力',
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
-- 验证查询
-- =====================================================
-- SELECT metric_key, method_code, method_name, priority
-- FROM calculation_method_registry
-- WHERE metric_key IN ('pump_speed', 'pump_torque', 'pump_cumulative_flow', 'pump_head', 'main_pipeline_inlet_pressure')
-- ORDER BY metric_key, priority DESC;
--
-- 预期结果:
-- pump_speed: A, B, C (3个)
-- pump_torque: A, B (2个)
-- pump_cumulative_flow: A, B (2个)
-- pump_head: HEAD_COEF_V1, MAIN (2个)
-- main_pipeline_inlet_pressure: PIN_COEF_V1, A, B, C (4个)
-- =====================================================

