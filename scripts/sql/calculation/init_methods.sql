-- =====================================================
-- 缺失指标计算功能 - 初始化计算方法注册表
-- =====================================================
-- 创建时间: 2025-09-30
-- 用途: 初始化calculation_method_registry表，录入所有计算方法
-- 方法列表:
--   pump_flow_rate: 6种方法（A-F）
--   pump_head: 1种方法
--   pump_outlet_pressure: 4种方法（A-D）
-- 总计: 11种方法
-- =====================================================

-- =====================================================
-- pump_flow_rate - 泵流量（6种方法）
-- =====================================================

-- 方案A：功率×频率分摊（首选并联近似）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_flow_rate_method_a',
    'pump_flow_rate',
    '功率×频率分摊',
    'A',
    100,  -- 最高优先级
    ARRAY['main_pipeline_flow_rate', 'pump_active_power', 'pump_frequency'],
    '{"min_running_pumps": 2, "description": "并联系统首选，需要至少2台泵运行"}'::jsonb,
    'docs/计算原理和公式.md#方案A',
    'high',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- 方案B：累计量求导（单泵计量可达高精度）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_flow_rate_method_b',
    'pump_flow_rate',
    '累计量求导',
    'B',
    90,
    ARRAY['pump_cumulative_flow'],
    '{"requires_cumulative_flow": true, "description": "单泵计量首选，需要累计流量数据"}'::jsonb,
    'docs/计算原理和公式.md#方案B',
    'high',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- 方案C：单泵运行直接取总管流量
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_flow_rate_method_c',
    'pump_flow_rate',
    '单泵运行直接取总管流量',
    'C',
    80,
    ARRAY['main_pipeline_flow_rate'],
    '{"running_count": {"exact": 1}, "description": "只有该泵运行时可用"}'::jsonb,
    'docs/计算原理和公式.md#方案C',
    'high',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- 方案D：仅功率分摊
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_flow_rate_method_d',
    'pump_flow_rate',
    '仅功率分摊',
    'D',
    70,
    ARRAY['main_pipeline_flow_rate', 'pump_active_power'],
    '{"min_running_pumps": 2, "description": "功率分摊，中等精度"}'::jsonb,
    'docs/计算原理和公式.md#方案D',
    'medium',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- 方案E：仅频率分摊
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_flow_rate_method_e',
    'pump_flow_rate',
    '仅频率分摊',
    'E',
    60,
    ARRAY['main_pipeline_flow_rate', 'pump_frequency'],
    '{"min_running_pumps": 2, "description": "频率分摊，低-中等精度"}'::jsonb,
    'docs/计算原理和公式.md#方案E',
    'medium',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- 方案F：数据驱动回归融合
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_flow_rate_method_f',
    'pump_flow_rate',
    '数据驱动回归融合',
    'F',
    50,
    ARRAY['pump_active_power', 'pump_frequency', 'pump_inlet_pressure'],
    '{"requires_training": true, "description": "长期优化，需要训练数据"}'::jsonb,
    'docs/计算原理和公式.md#方案F',
    'high',
    false  -- 默认禁用，需要训练后启用
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- =====================================================
-- pump_head - 泵扬程（1种方法）
-- =====================================================

-- 主方法：压差计算
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_head_method_main',
    'pump_head',
    '压差计算',
    'MAIN',
    100,
    ARRAY['pump_outlet_pressure', 'pump_inlet_pressure'],
    '{"description": "基于进出口压差计算扬程"}'::jsonb,
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
-- pump_outlet_pressure - 泵出口压力（4种方法）
-- =====================================================

-- 方案A：直接读取（如果有传感器）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_outlet_pressure_method_a',
    'pump_outlet_pressure',
    '直接读取',
    'A',
    100,
    ARRAY[]::TEXT[],  -- 无依赖，直接从fact_measurements读取
    '{"has_sensor": true, "description": "如果有传感器，直接读取"}'::jsonb,
    'docs/计算原理和公式.md#泵出口压力',
    'high',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- 方案B：以总管出口压力代替
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_outlet_pressure_method_b',
    'pump_outlet_pressure',
    '以总管出口压力代替',
    'B',
    90,
    ARRAY['main_pipeline_outlet_pressure'],
    '{"description": "假设泵出口与总管出口压力相近"}'::jsonb,
    'docs/计算原理和公式.md#泵出口压力',
    'medium',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- 方案C：由进口压力与扬程回推
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_outlet_pressure_method_c',
    'pump_outlet_pressure',
    '由进口压力与扬程回推',
    'C',
    80,
    ARRAY['pump_head', 'pump_inlet_pressure'],
    '{"description": "P_out = P_in + ρ·g·H / 1e6"}'::jsonb,
    'docs/计算原理和公式.md#泵出口压力',
    'high',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- 方案D：泵组层面近似
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_outlet_pressure_method_d',
    'pump_outlet_pressure',
    '泵组层面近似',
    'D',
    70,
    ARRAY['pump_group_outlet_pressure'],
    '{"description": "使用泵组出口压力近似"}'::jsonb,
    'docs/计算原理和公式.md#泵出口压力',
    'low',
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
-- SELECT metric_key, COUNT(*) as method_count
-- FROM calculation_method_registry
-- GROUP BY metric_key
-- ORDER BY metric_key;
--
-- 预期结果:
-- pump_flow_rate: 6
-- pump_head: 1
-- pump_outlet_pressure: 4
-- =====================================================



-- =====================================================
-- 追加：扩展更多指标的计算方法注册（本次由自动化脚本追加）
-- =====================================================

-- pump_efficiency - 泵效率（1种方法，简化基于功率与扬程/流量）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'EFF_SIMPLE_V1',
    'pump_efficiency',
    '简化效率估算（基于Q/H/Pe）',
    'EFF_SIMPLE_V1',
    100,
    ARRAY['pump_flow_rate','pump_head','pump_active_power'],
    '{"description":"η=(ρgQH)/(P_e·η_motor)，裁剪至[0,η_max]"}'::jsonb,
    'docs/计算原理和公式.md#泵效率',
    'medium',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

-- pump_speed - 泵转速（2种方法）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_speed_method_a',
    'pump_speed',
    '频率比例法',
    'A',
    100,
    ARRAY['pump_frequency'],
    '{"description":"n=(f/f_ref)*n_ref","f_ref":50,"n_ref":1500}'::jsonb,
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

INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_speed_method_b',
    'pump_speed',
    '绝对转速法（电机学）',
    'B',
    90,
    ARRAY['pump_frequency'],
    '{"description":"n=120*f/P*(1-s)","pole_pairs":2,"slip":0.02}'::jsonb,
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

-- pump_torque - 泵扭矩（1-2种方法，这里先注册A）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_torque_method_a',
    'pump_torque',
    '水力功率与转速法（推荐）',
    'A',
    100,
    ARRAY['pump_flow_rate','pump_head','pump_speed'],
    '{"description":"T=(ρgQH/1000)/(2πn/60)×1000"}'::jsonb,
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


-- pump_cumulative_flow - 泵累计流量（1种方法：由瞬时流量积分）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'pump_cumulative_flow_method_a',
    'pump_cumulative_flow',
    '由瞬时流量积分',
    'A',
    100,
    ARRAY['pump_flow_rate'],
    '{"description":"V(t)=V(t-1)+Q·Δt/3600"}'::jsonb,
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


-- 确保缺失的指标在 dim_metric_config 中存在（若已存在则忽略）
WITH next_id AS (
    SELECT COALESCE(MAX(id),0)+1 AS nid FROM dim_metric_config
)
INSERT INTO dim_metric_config (id, metric_key, unit, unit_display, value_type, fixed_decimals)
SELECT nid, 'main_pipeline_inlet_pressure','MPa','MPa','float',3 FROM next_id
ON CONFLICT (metric_key) DO NOTHING;

-- =====================================================
-- main_pipeline_outlet_pressure - 总管出口压力（3种方法）
-- =====================================================
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'main_pipeline_outlet_pressure_method_a',
    'main_pipeline_outlet_pressure',
    '由泵出口压力直接近似',
    'A',
    100,
    ARRAY['pump_outlet_pressure'],
    '{"description":"P_main_out≈P_pump_out"}'::jsonb,
    'docs/计算原理和公式.md#总管出口压力',
    'medium',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'main_pipeline_outlet_pressure_method_b',
    'main_pipeline_outlet_pressure',
    '由进口压力与扬程回推',
    'B',
    90,
    ARRAY['pump_inlet_pressure','pump_head'],
    '{"description":"P_out=P_in+ρgH/1e6"}'::jsonb,
    'docs/计算原理和公式.md#总管出口压力',
    'high',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'main_pipeline_outlet_pressure_method_c',
    'main_pipeline_outlet_pressure',
    '多泵出口压力聚合（max）',
    'C',
    80,
    ARRAY['pump_outlet_pressure'],
    '{"description":"P_main_out(t)=max(P_pump_out)"}'::jsonb,
    'docs/计算原理和公式.md#总管出口压力',
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
-- main_pipeline_inlet_pressure - 总管入口压力（3种方法）
-- =====================================================
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'main_pipeline_inlet_pressure_method_a',
    'main_pipeline_inlet_pressure',
    '由泵进口压力直接近似',
    'A',
    100,
    ARRAY['pump_inlet_pressure'],
    '{"description":"P_main_in≈P_pump_in"}'::jsonb,
    'docs/计算原理和公式.md#总管进口压力',
    'medium',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'main_pipeline_inlet_pressure_method_b',
    'main_pipeline_inlet_pressure',
    '由水池液位推算',
    'B',
    90,
    ARRAY['pool_liquid_level'],
    '{"description":"P_main_in=P_atm+ρgL/1e6"}'::jsonb,
    'docs/计算原理和公式.md#总管进口压力',
    'medium',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();

INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled
) VALUES (
    'main_pipeline_inlet_pressure_method_c',
    'main_pipeline_inlet_pressure',
    '多泵进口压力聚合（mean）',
    'C',
    80,
    ARRAY['pump_inlet_pressure'],
    '{"description":"P_main_in(t)=mean(P_pump_in)"}'::jsonb,
    'docs/计算原理和公式.md#总管进口压力',
    'medium',
    true
) ON CONFLICT (metric_key, method_code) DO UPDATE SET
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    updated_at = NOW();
