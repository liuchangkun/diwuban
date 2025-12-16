-- ============================================
-- 自适应SQL脚本：依赖 metric_key 的表
-- ============================================
-- 文件：scripts/sql/adaptive/01_metric_config_related.sql
-- 用途：生成 calculation_method_registry 和 metric_calculation_order
-- 依赖：dim_metric_config 表必须已存在且包含数据
-- 特性：自适应关联，能够适应 dim_metric_config 的 ID 变化和指标增减
-- ============================================

BEGIN;

-- ============================================
-- 表1：calculation_method_registry（计算方法注册表）
-- ============================================
-- 方法统计：
--   pump_flow_rate: 6种方法（A-F）
--   pump_head: 2种方法（MAIN, HEAD_COEF_V1）
--   pump_outlet_pressure: 4种方法（A-D）
--   pump_inlet_pressure: 2种方法（A-B）
--   pump_efficiency: 1种方法（EFF_SIMPLE_V1）
--   pump_speed: 3种方法（A-C）
--   pump_torque: 2种方法（A-B）
--   pump_cumulative_flow: 2种方法（A-B）
--   main_pipeline_outlet_pressure: 3种方法（A-C）
--   main_pipeline_inlet_pressure: 4种方法（A-C, PIN_COEF_V1）
-- 总计：29种方法
-- ============================================

-- 清空表（完全重建）
TRUNCATE TABLE calculation_method_registry CASCADE;

-- ============================================
-- pump_flow_rate - 泵流量（6种方法）
-- ============================================

-- 方案A：功率×频率分摊（首选并联近似）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT 
    'pump_flow_rate_method_a',
    mc.metric_key,
    '功率×频率分摊',
    'A',
    100,
    ARRAY['main_pipeline_flow_rate', 'pump_active_power', 'pump_frequency'],
    '{"min_running_pumps": 2, "description": "并联系统首选，需要至少2台泵运行"}'::jsonb,
    'docs/计算原理和公式.md#方案A',
    'high',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_flow_rate';

-- 方案B：累计量求导（单泵计量可达高精度）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT 
    'pump_flow_rate_method_b',
    mc.metric_key,
    '累计量求导',
    'B',
    90,
    ARRAY['pump_cumulative_flow'],
    '{"requires_cumulative_flow": true, "description": "单泵计量首选，需要累计流量数据"}'::jsonb,
    'docs/计算原理和公式.md#方案B',
    'high',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_flow_rate';

-- 方案C：单泵运行直接取总管流量
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT 
    'pump_flow_rate_method_c',
    mc.metric_key,
    '单泵运行直接取总管流量',
    'C',
    80,
    ARRAY['main_pipeline_flow_rate'],
    '{"running_count": {"exact": 1}, "description": "只有该泵运行时可用"}'::jsonb,
    'docs/计算原理和公式.md#方案C',
    'high',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_flow_rate';

-- 方案D：仅功率分摊
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT 
    'pump_flow_rate_method_d',
    mc.metric_key,
    '仅功率分摊',
    'D',
    70,
    ARRAY['main_pipeline_flow_rate', 'pump_active_power'],
    '{"min_running_pumps": 2, "description": "功率分摊，中等精度"}'::jsonb,
    'docs/计算原理和公式.md#方案D',
    'medium',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_flow_rate';

-- 方案E：仅频率分摊
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT 
    'pump_flow_rate_method_e',
    mc.metric_key,
    '仅频率分摊',
    'E',
    60,
    ARRAY['main_pipeline_flow_rate', 'pump_frequency'],
    '{"min_running_pumps": 2, "description": "频率分摊，低-中等精度"}'::jsonb,
    'docs/计算原理和公式.md#方案E',
    'medium',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_flow_rate';

-- 方案F：数据驱动回归融合
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT 
    'pump_flow_rate_method_f',
    mc.metric_key,
    '数据驱动回归融合',
    'F',
    50,
    ARRAY['pump_active_power', 'pump_frequency', 'pump_inlet_pressure'],
    '{"requires_training": true, "description": "长期优化，需要训练数据"}'::jsonb,
    'docs/计算原理和公式.md#方案F',
    'high',
    FALSE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_flow_rate';

-- ============================================
-- pump_head - 泵扬程（2种方法）
-- ============================================

-- 方法MAIN：压差计算
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT 
    'pump_head_method_main',
    mc.metric_key,
    '压差计算',
    'MAIN',
    100,
    ARRAY['pump_outlet_pressure', 'pump_inlet_pressure'],
    '{"description": "基于进出口压差计算扬程"}'::jsonb,
    'docs/计算原理和公式.md#泵扬程',
    'high',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_head';

-- 方法HEAD_COEF_V1：压差计算（新版）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT 
    'HEAD_COEF_V1',
    mc.metric_key,
    '压差计算（新版）',
    'HEAD_COEF_V1',
    110,
    ARRAY['pump_outlet_pressure', 'pump_inlet_pressure'],
    '{"description": "H = (P_out - P_in) × 1e6 / (ρ × g)，新版实现"}'::jsonb,
    'docs/计算原理和公式.md#泵扬程',
    'high',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_head';

-- ============================================
-- pump_outlet_pressure - 泵出口压力（4种方法）
-- ============================================

-- 方法A：直接读取
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT 
    'pump_outlet_pressure_method_a',
    mc.metric_key,
    '直接读取',
    'A',
    100,
    ARRAY[]::TEXT[],
    '{"has_sensor": true, "description": "如果有传感器，直接读取"}'::jsonb,
    'docs/计算原理和公式.md#泵出口压力',
    'high',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_outlet_pressure';

-- 方法B：以总管出口压力代替
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT 
    'pump_outlet_pressure_method_b',
    mc.metric_key,
    '以总管出口压力代替',
    'B',
    90,
    ARRAY['main_pipeline_outlet_pressure'],
    '{"description": "假设泵出口与总管出口压力相近"}'::jsonb,
    'docs/计算原理和公式.md#泵出口压力',
    'medium',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_outlet_pressure';

-- 方法C：由进口压力与扬程回推
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT 
    'pump_outlet_pressure_method_c',
    mc.metric_key,
    '由进口压力与扬程回推',
    'C',
    80,
    ARRAY['pump_head', 'pump_inlet_pressure'],
    '{"description": "P_out = P_in + ρ·g·H / 1e6"}'::jsonb,
    'docs/计算原理和公式.md#泵出口压力',
    'high',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_outlet_pressure';

-- 方法D：泵组层面近似
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT 
    'pump_outlet_pressure_method_d',
    mc.metric_key,
    '泵组层面近似',
    'D',
    70,
    ARRAY['pump_group_outlet_pressure'],
    '{"description": "使用泵组出口压力近似"}'::jsonb,
    'docs/计算原理和公式.md#泵出口压力',
    'low',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_outlet_pressure';

-- ============================================
-- pump_inlet_pressure - 泵进口压力（2种方法）
-- ============================================

-- 方法B：从水池液位推算（推荐，优先级最高）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT
    'pump_inlet_pressure_method_b',
    mc.metric_key,
    '从水池液位推算',
    'B',
    100,
    ARRAY['pool_liquid_level'],
    '{"description": "P_in = P_atm + ρ × g × L / 1e6"}'::jsonb,
    NULL,
    'high',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_inlet_pressure';

-- 方法A：使用总管进口压力代替（备选）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT
    'pump_inlet_pressure_method_a',
    mc.metric_key,
    '使用总管进口压力代替',
    'A',
    90,
    ARRAY['main_pipeline_inlet_pressure'],
    '{"description": "假设泵进口与总管进口压力相近（并联系统）"}'::jsonb,
    NULL,
    'medium',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_inlet_pressure';

-- ============================================
-- pump_efficiency - 泵效率（1种方法）
-- ============================================

INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT
    'EFF_SIMPLE_V1',
    mc.metric_key,
    '简化效率估算（基于Q/H/Pe）',
    'EFF_SIMPLE_V1',
    100,
    ARRAY['pump_flow_rate', 'pump_head', 'pump_active_power'],
    '{"description": "η=(ρgQH)/(P_e·η_motor)，裁剪至[0,η_max]"}'::jsonb,
    'docs/计算原理和公式.md#泵效率',
    'medium',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_efficiency';

-- ============================================
-- pump_speed - 泵转速（3种方法）
-- ============================================

-- 方法A：频率比例法
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT
    'pump_speed_method_a',
    mc.metric_key,
    '频率比例法',
    'A',
    100,
    ARRAY['pump_frequency'],
    '{"f_ref": 50, "n_ref": 1500, "description": "n=(f/f_ref)*n_ref"}'::jsonb,
    'docs/计算原理和公式.md#泵转速',
    'medium',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_speed';

-- 方法B：绝对转速法（电机学）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT
    'pump_speed_method_b',
    mc.metric_key,
    '绝对转速法（电机学）',
    'B',
    90,
    ARRAY['pump_frequency'],
    '{"slip": 0.02, "pole_pairs": 2, "description": "n=120*f/P*(1-s)"}'::jsonb,
    'docs/计算原理和公式.md#泵转速',
    'medium',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_speed';

-- 方法C：标定关系法
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT
    'pump_speed_method_c',
    mc.metric_key,
    '标定关系法',
    'C',
    80,
    ARRAY['pump_frequency'],
    '{"description": "n = a × f + b，需要标定参数", "calibration_a": 30.0, "calibration_b": 0.0}'::jsonb,
    'docs/计算原理和公式.md#泵转速',
    'medium',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_speed';

-- ============================================
-- pump_torque - 泵扭矩（2种方法）
-- ============================================

-- 方法A：水力功率与转速法（推荐）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT
    'pump_torque_method_a',
    mc.metric_key,
    '水力功率与转速法（推荐）',
    'A',
    100,
    ARRAY['pump_flow_rate', 'pump_head', 'pump_speed'],
    '{"description": "T=(ρgQH/1000)/(2πn/60)×1000"}'::jsonb,
    'docs/计算原理和公式.md#泵扭矩',
    'medium',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_torque';

-- 方法B：电功率与频率法
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT
    'pump_torque_method_b',
    mc.metric_key,
    '电功率与频率法',
    'B',
    90,
    ARRAY['pump_active_power', 'pump_frequency'],
    '{"slip": 0.02, "pole_pairs": 2, "description": "T = P_in × 1000 / ω，ω = 2π × n / 60，n = 120 × f / P × (1 - s)"}'::jsonb,
    'docs/计算原理和公式.md#泵扭矩',
    'medium',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_torque';

-- ============================================
-- pump_cumulative_flow - 泵累计流量（2种方法）
-- ============================================

-- 方法A：由瞬时流量积分
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT
    'pump_cumulative_flow_method_a',
    mc.metric_key,
    '由瞬时流量积分',
    'A',
    100,
    ARRAY['pump_flow_rate'],
    '{"description": "V(t)=V(t-1)+Q·Δt/3600"}'::jsonb,
    'docs/计算原理和公式.md#泵累计流量',
    'medium',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_cumulative_flow';

-- 方法B：从总管累计流量按比例分摊
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT
    'pump_cumulative_flow_method_b',
    mc.metric_key,
    '从总管累计流量按比例分摊',
    'B',
    90,
    ARRAY['main_pipeline_cumulative_flow', 'pump_flow_rate', 'main_pipeline_flow_rate'],
    '{"description": "V_pump = V_main × (Q_pump / Q_main)"}'::jsonb,
    'docs/计算原理和公式.md#泵累计流量',
    'medium',
    TRUE,
    ARRAY['pump']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_cumulative_flow';

-- ============================================
-- main_pipeline_outlet_pressure - 总管出口压力（3种方法）
-- ============================================

-- 方法A：由泵出口压力直接近似
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT
    'main_pipeline_outlet_pressure_method_a',
    mc.metric_key,
    '由泵出口压力直接近似',
    'A',
    100,
    ARRAY['pump_outlet_pressure'],
    '{"description": "P_main_out≈P_pump_out"}'::jsonb,
    'docs/计算原理和公式.md#总管出口压力',
    'medium',
    TRUE,
    ARRAY['main_pipeline']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'main_pipeline_outlet_pressure';

-- 方法B：由进口压力与扬程回推
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT
    'main_pipeline_outlet_pressure_method_b',
    mc.metric_key,
    '由进口压力与扬程回推',
    'B',
    90,
    ARRAY['pump_inlet_pressure', 'pump_head'],
    '{"description": "P_out=P_in+ρgH/1e6"}'::jsonb,
    'docs/计算原理和公式.md#总管出口压力',
    'high',
    TRUE,
    ARRAY['main_pipeline']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'main_pipeline_outlet_pressure';

-- 方法C：多泵出口压力聚合（max）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT
    'main_pipeline_outlet_pressure_method_c',
    mc.metric_key,
    '多泵出口压力聚合（max）',
    'C',
    80,
    ARRAY['pump_outlet_pressure'],
    '{"description": "P_main_out(t)=max(P_pump_out)"}'::jsonb,
    'docs/计算原理和公式.md#总管出口压力',
    'medium',
    TRUE,
    ARRAY['main_pipeline']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'main_pipeline_outlet_pressure';

-- ============================================
-- main_pipeline_inlet_pressure - 总管进口压力（4种方法）
-- ============================================

-- 方法A：由泵进口压力直接近似
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT
    'main_pipeline_inlet_pressure_method_a',
    mc.metric_key,
    '由泵进口压力直接近似',
    'A',
    100,
    ARRAY['pump_inlet_pressure'],
    '{"description": "P_main_in≈P_pump_in"}'::jsonb,
    'docs/计算原理和公式.md#总管进口压力',
    'medium',
    TRUE,
    ARRAY['main_pipeline']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'main_pipeline_inlet_pressure';

-- 方法B：由水池液位推算
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT
    'main_pipeline_inlet_pressure_method_b',
    mc.metric_key,
    '由水池液位推算',
    'B',
    90,
    ARRAY['pool_liquid_level'],
    '{"description": "P_main_in=P_atm+ρgL/1e6"}'::jsonb,
    'docs/计算原理和公式.md#总管进口压力',
    'medium',
    TRUE,
    ARRAY['main_pipeline']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'main_pipeline_inlet_pressure';

-- 方法C：多泵进口压力聚合（mean）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT
    'main_pipeline_inlet_pressure_method_c',
    mc.metric_key,
    '多泵进口压力聚合（mean）',
    'C',
    80,
    ARRAY['pump_inlet_pressure'],
    '{"description": "P_main_in(t)=mean(P_pump_in)"}'::jsonb,
    'docs/计算原理和公式.md#总管进口压力',
    'medium',
    TRUE,
    ARRAY['main_pipeline']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'main_pipeline_inlet_pressure';

-- 方法PIN_COEF_V1：综合计算（新版）
INSERT INTO calculation_method_registry (
    method_id, metric_key, method_name, method_code, priority,
    dependencies, conditions, formula_ref, accuracy_level, is_enabled, allowed_device_types
)
SELECT
    'PIN_COEF_V1',
    mc.metric_key,
    '综合计算（新版）',
    'PIN_COEF_V1',
    110,
    ARRAY['pump_inlet_pressure', 'pool_liquid_level'],
    '{"description": "综合多种数据源计算总管进口压力，新版实现"}'::jsonb,
    'docs/计算原理和公式.md#总管进口压力',
    'high',
    TRUE,
    ARRAY['main_pipeline']::TEXT[]
FROM dim_metric_config mc
WHERE mc.metric_key = 'main_pipeline_inlet_pressure';

-- ============================================
-- 表2：metric_calculation_order（指标计算顺序）
-- ============================================
-- 注意：此表通常由 DependencyAnalyzer.save_to_database() 生成
-- 这里提供基础的顺序定义，实际使用时可能需要Python代码动态生成

-- 清空表
TRUNCATE TABLE metric_calculation_order CASCADE;

-- 插入基础指标（无依赖）
INSERT INTO metric_calculation_order (
    metric_key, depends_on, priority, order_index, is_circular, circular_group
)
SELECT
    mc.metric_key,
    ARRAY[]::TEXT[],
    100,
    0,
    FALSE,
    NULL
FROM dim_metric_config mc
WHERE mc.metric_key IN (
    'pump_frequency', 'pump_voltage_a', 'pump_voltage_b', 'pump_voltage_c',
    'pump_current_a', 'pump_current_b', 'pump_current_c',
    'pump_active_power', 'pump_reactive_power', 'pump_apparent_power',
    'pump_power_factor', 'pump_inlet_pressure', 'pump_cumulative_flow',
    'main_pipeline_flow_rate', 'pool_liquid_level'
)
ON CONFLICT (metric_key) DO UPDATE SET
    depends_on = EXCLUDED.depends_on,
    order_index = EXCLUDED.order_index,
    updated_at = NOW();

-- 插入一级依赖指标
INSERT INTO metric_calculation_order (
    metric_key, depends_on, priority, order_index, is_circular, circular_group
)
SELECT
    mc.metric_key,
    ARRAY['pump_frequency']::TEXT[],
    100,
    10,
    FALSE,
    NULL
FROM dim_metric_config mc
WHERE mc.metric_key IN ('pump_speed')
ON CONFLICT (metric_key) DO UPDATE SET
    depends_on = EXCLUDED.depends_on,
    order_index = EXCLUDED.order_index,
    updated_at = NOW();

-- 插入二级依赖指标（pump_flow_rate）
INSERT INTO metric_calculation_order (
    metric_key, depends_on, priority, order_index, is_circular, circular_group
)
SELECT
    mc.metric_key,
    ARRAY['main_pipeline_flow_rate', 'pump_active_power', 'pump_frequency']::TEXT[],
    100,
    20,
    FALSE,
    NULL
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_flow_rate'
ON CONFLICT (metric_key) DO UPDATE SET
    depends_on = EXCLUDED.depends_on,
    order_index = EXCLUDED.order_index,
    updated_at = NOW();

-- 插入二级依赖指标（pump_outlet_pressure, pump_head）
INSERT INTO metric_calculation_order (
    metric_key, depends_on, priority, order_index, is_circular, circular_group
)
SELECT
    mc.metric_key,
    ARRAY['pump_outlet_pressure', 'pump_inlet_pressure']::TEXT[],
    100,
    20,
    FALSE,
    NULL
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_head'
ON CONFLICT (metric_key) DO UPDATE SET
    depends_on = EXCLUDED.depends_on,
    order_index = EXCLUDED.order_index,
    updated_at = NOW();

-- 插入三级依赖指标（pump_efficiency, pump_torque）
INSERT INTO metric_calculation_order (
    metric_key, depends_on, priority, order_index, is_circular, circular_group
)
SELECT
    mc.metric_key,
    ARRAY['pump_flow_rate', 'pump_head', 'pump_active_power']::TEXT[],
    100,
    30,
    FALSE,
    NULL
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_efficiency'
ON CONFLICT (metric_key) DO UPDATE SET
    depends_on = EXCLUDED.depends_on,
    order_index = EXCLUDED.order_index,
    updated_at = NOW();

INSERT INTO metric_calculation_order (
    metric_key, depends_on, priority, order_index, is_circular, circular_group
)
SELECT
    mc.metric_key,
    ARRAY['pump_flow_rate', 'pump_head', 'pump_speed']::TEXT[],
    100,
    30,
    FALSE,
    NULL
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_torque'
ON CONFLICT (metric_key) DO UPDATE SET
    depends_on = EXCLUDED.depends_on,
    order_index = EXCLUDED.order_index,
    updated_at = NOW();

COMMIT;

