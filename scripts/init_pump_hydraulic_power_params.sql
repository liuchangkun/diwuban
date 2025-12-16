-- ============================================
-- pump_hydraulic_power 参数初始化脚本
-- ============================================
-- 用途：初始化pump_hydraulic_power计算所需的所有参数
-- 创建日期：2025-11-23
-- 协议：RIPER-5 执行模式
-- ============================================

-- ============================================
-- 1. calculation_parameters表：计算参数
-- ============================================
-- 添加pump_hydraulic_power的计算参数和验证参数

INSERT INTO calculation_parameters (
    station_id,
    device_id,
    metric_key,
    param_name,
    param_value,
    param_type
) VALUES
    -- 计算参数（全局）
    (NULL, NULL, 'pump_hydraulic_power', 'rho', 1000.0, 'float'),
    (NULL, NULL, 'pump_hydraulic_power', 'g', 9.81, 'float'),

    -- 验证参数（全局）
    (NULL, NULL, 'pump_hydraulic_power', 'min_power', 0.0, 'float'),
    (NULL, NULL, 'pump_hydraulic_power', 'max_power', 500.0, 'float')
ON CONFLICT (station_id, device_id, metric_key, param_name)
DO UPDATE SET
    param_value = EXCLUDED.param_value,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 2. 验证参数插入
-- ============================================

-- 验证calculation_parameters
SELECT
    metric_key,
    param_name,
    param_value,
    param_type,
    station_id,
    device_id
FROM calculation_parameters
WHERE metric_key = 'pump_hydraulic_power'
ORDER BY param_name;

-- ============================================
-- 3. 参数说明
-- ============================================

/*
calculation_parameters参数说明：

计算参数：
- rho: 液体密度（kg/m³），默认1000.0（水）
- g: 重力加速度（m/s²），默认9.81

验证参数：
- min_power: 水力功率最小值（kW），默认0.0
- max_power: 水力功率最大值（kW），默认500.0

计算公式：
P_h = ρ × g × Q × H / 3600000 (kW)

其中：
- Q: 泵流量（m³/h），从pump_flow_rate获取
- H: 泵扬程（m），从pump_head获取
- 3600000 = 3600（m³/h → m³/s）× 1000（W → kW）

物理约束：
- P_h ≥ 0（水力功率不能为负）
- P_h < P_shaft（水力功率小于轴功率）
- 典型值：Q=1000 m³/h, H=30 m → P_h ≈ 81.75 kW

示例计算：
Q = 1000 m³/h, H = 30 m
P_h = 1000 × 9.81 × 1000 × 30 / 3600000
    = 294300000 / 3600000
    = 81.75 kW
*/

