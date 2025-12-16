-- ============================================
-- 数据库表优化 - 阶段3：质量提升
--
-- 功能：
-- 1. 添加 CHECK 约束（参数值范围验证）
-- 2. 添加触发器（自动数据验证）
-- 3. 创建质量检查视图（参数质量、一致性、覆盖率）
--
-- 作者：AI
-- 创建日期：2025-11-09
-- 迁移编号：107
-- ============================================

BEGIN;

-- ============================================
-- 步骤1：添加 CHECK 约束
-- ============================================

-- 1.1 约束：时间有效性验证（effective_from <= effective_to）
ALTER TABLE device_rated_params
ADD CONSTRAINT chk_device_rated_params_effective_dates
CHECK (
  effective_to IS NULL OR 
  effective_from IS NULL OR 
  effective_from <= effective_to
);

COMMENT ON CONSTRAINT chk_device_rated_params_effective_dates ON device_rated_params IS 
'时间有效性验证：effective_from 必须小于等于 effective_to';

-- 1.2 约束：三层参数逻辑验证
-- 全局级：station_id IS NULL AND device_id IS NULL
-- 站点级：station_id IS NOT NULL AND device_id IS NULL
-- 设备级：device_id IS NOT NULL
ALTER TABLE device_rated_params
ADD CONSTRAINT chk_device_rated_params_tier_logic
CHECK (
  (station_id IS NULL AND device_id IS NULL) OR  -- 全局级
  (station_id IS NOT NULL AND device_id IS NULL) OR  -- 站点级
  (device_id IS NOT NULL)  -- 设备级（可以有或没有 station_id）
);

COMMENT ON CONSTRAINT chk_device_rated_params_tier_logic ON device_rated_params IS 
'三层参数逻辑验证：确保参数级别定义正确（全局/站点/设备）';

-- 1.3 约束：单位字段验证（数值参数必须有单位）
ALTER TABLE device_rated_params
ADD CONSTRAINT chk_device_rated_params_unit_presence
CHECK (
  value_numeric IS NULL OR 
  unit IS NOT NULL OR
  param_key IN ('poles_pair', 'eta_motor', 'eta_vfd', 'rated_efficiency', 'C_hazen', 'roughness_rel')
);

COMMENT ON CONSTRAINT chk_device_rated_params_unit_presence ON device_rated_params IS 
'单位字段验证：数值参数必须有单位（无量纲参数除外）';

-- 1.4 约束：来源字段验证（所有参数必须有来源）
ALTER TABLE device_rated_params
ADD CONSTRAINT chk_device_rated_params_source_presence
CHECK (source IS NOT NULL AND source <> '');

COMMENT ON CONSTRAINT chk_device_rated_params_source_presence ON device_rated_params IS 
'来源字段验证：所有参数必须标注来源';

-- 1.5 约束：参数值范围验证（常见参数的合理范围）
ALTER TABLE device_rated_params
ADD CONSTRAINT chk_device_rated_params_value_numeric_range
CHECK (
  value_numeric IS NULL OR
  (
    -- 频率范围：0-100 Hz
    (param_key = 'rated_frequency' AND value_numeric BETWEEN 0 AND 100) OR
    -- 极对数范围：1-10
    (param_key = 'poles_pair' AND value_numeric BETWEEN 1 AND 10) OR
    -- 效率范围：0-1
    (param_key IN ('eta_motor', 'eta_vfd', 'rated_efficiency') AND value_numeric BETWEEN 0 AND 1) OR
    -- 功率范围：0-10000 kW
    (param_key = 'rated_power' AND value_numeric BETWEEN 0 AND 10000) OR
    -- 电流范围：0-10000 A
    (param_key = 'rated_current' AND value_numeric BETWEEN 0 AND 10000) OR
    -- 流量范围：0-10000 m3/h
    (param_key = 'rated_flow' AND value_numeric BETWEEN 0 AND 10000) OR
    -- 扬程范围：0-1000 m
    (param_key = 'rated_head' AND value_numeric BETWEEN 0 AND 1000) OR
    -- 温度范围：-50-100 °C
    (param_key = 'ambient_temp' AND value_numeric BETWEEN -50 AND 100) OR
    -- 压力范围：0-200 kPa
    (param_key = 'ambient_pressure' AND value_numeric BETWEEN 0 AND 200) OR
    -- 管道直径范围：0-10 m
    (param_key = 'pipe_diameter' AND value_numeric BETWEEN 0 AND 10) OR
    -- 管道长度范围：0-10000 m
    (param_key = 'pipe_length' AND value_numeric BETWEEN 0 AND 10000) OR
    -- 海曾-威廉系数范围：50-150
    (param_key = 'C_hazen' AND value_numeric BETWEEN 50 AND 150) OR
    -- 相对粗糙度范围：0-0.1
    (param_key = 'roughness_rel' AND value_numeric BETWEEN 0 AND 0.1) OR
    -- 其他参数不限制
    param_key NOT IN (
      'rated_frequency', 'poles_pair', 'eta_motor', 'eta_vfd', 'rated_efficiency',
      'rated_power', 'rated_current', 'rated_flow', 'rated_head',
      'ambient_temp', 'ambient_pressure', 'pipe_diameter', 'pipe_length',
      'C_hazen', 'roughness_rel'
    )
  )
);

COMMENT ON CONSTRAINT chk_device_rated_params_value_numeric_range ON device_rated_params IS 
'参数值范围验证：确保常见参数的数值在合理范围内';

-- ============================================
-- 步骤2：创建触发器函数
-- ============================================

-- 2.1 触发器函数：验证参数值
CREATE OR REPLACE FUNCTION fn_validate_device_rated_params()
RETURNS TRIGGER AS $$
BEGIN
  -- 验证：设备级参数必须关联有效的设备
  IF NEW.device_id IS NOT NULL THEN
    IF NOT EXISTS (SELECT 1 FROM dim_devices WHERE id = NEW.device_id) THEN
      RAISE EXCEPTION '设备ID % 不存在', NEW.device_id;
    END IF;
  END IF;
  
  -- 验证：站点级参数必须关联有效的站点
  IF NEW.station_id IS NOT NULL AND NEW.device_id IS NULL THEN
    IF NOT EXISTS (SELECT 1 FROM dim_stations WHERE id = NEW.station_id) THEN
      RAISE EXCEPTION '站点ID % 不存在', NEW.station_id;
    END IF;
  END IF;
  
  -- 验证：参数键必须在元数据表中定义
  IF NOT EXISTS (SELECT 1 FROM dim_device_param_metadata WHERE param_key = NEW.param_key) THEN
    RAISE WARNING '参数键 % 未在元数据表中定义', NEW.param_key;
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION fn_validate_device_rated_params() IS
'验证设备参数的有效性（设备ID、站点ID、参数键）';

-- 2.2 创建触发器：插入前验证
CREATE TRIGGER trg_device_rated_params_validate_insert
BEFORE INSERT ON device_rated_params
FOR EACH ROW
EXECUTE FUNCTION fn_validate_device_rated_params();

COMMENT ON TRIGGER trg_device_rated_params_validate_insert ON device_rated_params IS
'插入前验证参数有效性';

-- 2.3 创建触发器：更新前验证
CREATE TRIGGER trg_device_rated_params_validate_update
BEFORE UPDATE ON device_rated_params
FOR EACH ROW
EXECUTE FUNCTION fn_validate_device_rated_params();

COMMENT ON TRIGGER trg_device_rated_params_validate_update ON device_rated_params IS
'更新前验证参数有效性';

-- ============================================
-- 步骤3：创建质量检查视图
-- ============================================

-- 3.1 视图：参数质量检查（缺失值、异常值）
CREATE OR REPLACE VIEW v_device_params_quality_check AS
WITH device_params AS (
  SELECT
    d.id AS device_id,
    d.name AS device_name,
    d.type AS device_type,
    s.id AS station_id,
    s.name AS station_name,
    drp.param_key,
    drp.value_numeric,
    drp.unit,
    drp.source,
    drp.effective_from,
    drp.effective_to
  FROM dim_devices d
  JOIN dim_stations s ON d.station_id = s.id
  LEFT JOIN device_rated_params drp ON d.id = drp.device_id
    AND (drp.effective_to IS NULL OR drp.effective_to > NOW())
    AND (drp.effective_from IS NULL OR drp.effective_from <= NOW())
  WHERE d.type = 'pump'
)
SELECT
  device_id,
  device_name,
  station_name,
  -- 缺失参数检查
  CASE WHEN param_key IS NULL THEN '缺失所有参数' ELSE NULL END AS 质量问题_缺失,
  -- 异常值检查（示例：功率为0或负数）
  CASE
    WHEN param_key = 'rated_power' AND (value_numeric IS NULL OR value_numeric <= 0) THEN '额定功率异常'
    WHEN param_key = 'rated_flow' AND (value_numeric IS NULL OR value_numeric <= 0) THEN '额定流量异常'
    WHEN param_key = 'rated_head' AND (value_numeric IS NULL OR value_numeric <= 0) THEN '额定扬程异常'
    ELSE NULL
  END AS 质量问题_异常值,
  -- 单位缺失检查
  CASE
    WHEN param_key IN ('rated_power', 'rated_current', 'rated_flow', 'rated_head', 'rated_frequency')
      AND unit IS NULL THEN '单位缺失'
    ELSE NULL
  END AS 质量问题_单位,
  -- 来源缺失检查
  CASE WHEN source IS NULL OR source = '' THEN '来源缺失' ELSE NULL END AS 质量问题_来源,
  param_key,
  value_numeric,
  unit,
  source
FROM device_params
WHERE
  param_key IS NULL OR  -- 缺失参数
  (param_key = 'rated_power' AND (value_numeric IS NULL OR value_numeric <= 0)) OR  -- 功率异常
  (param_key = 'rated_flow' AND (value_numeric IS NULL OR value_numeric <= 0)) OR  -- 流量异常
  (param_key = 'rated_head' AND (value_numeric IS NULL OR value_numeric <= 0)) OR  -- 扬程异常
  (param_key IN ('rated_power', 'rated_current', 'rated_flow', 'rated_head', 'rated_frequency') AND unit IS NULL) OR  -- 单位缺失
  source IS NULL OR source = '';  -- 来源缺失

COMMENT ON VIEW v_device_params_quality_check IS
'参数质量检查视图：检查缺失值、异常值、单位缺失、来源缺失等质量问题';

-- 3.2 视图：参数一致性检查（同站点设备参数差异）
CREATE OR REPLACE VIEW v_device_params_consistency_check AS
WITH station_param_stats AS (
  SELECT
    d.station_id,
    s.name AS station_name,
    drp.param_key,
    COUNT(DISTINCT drp.value_numeric) AS 不同值数量,
    MIN(drp.value_numeric) AS 最小值,
    MAX(drp.value_numeric) AS 最大值,
    AVG(drp.value_numeric) AS 平均值,
    STDDEV(drp.value_numeric) AS 标准差,
    COUNT(drp.device_id) AS 设备数量
  FROM dim_devices d
  JOIN dim_stations s ON d.station_id = s.id
  LEFT JOIN device_rated_params drp ON d.id = drp.device_id
    AND (drp.effective_to IS NULL OR drp.effective_to > NOW())
    AND (drp.effective_from IS NULL OR drp.effective_from <= NOW())
  WHERE d.type = 'pump'
    AND drp.param_key IS NOT NULL
  GROUP BY d.station_id, s.name, drp.param_key
)
SELECT
  station_id,
  station_name,
  param_key,
  不同值数量,
  最小值,
  最大值,
  平均值,
  标准差,
  设备数量,
  CASE
    WHEN 不同值数量 > 1 AND param_key IN ('rated_frequency', 'poles_pair', 'eta_motor', 'eta_vfd')
      THEN '建议使用全局级参数'
    WHEN 不同值数量 > 1 AND param_key IN ('pipe_diameter', 'pipe_length', 'ambient_temp', 'ambient_pressure')
      THEN '建议使用站点级参数'
    WHEN 不同值数量 > 设备数量 / 2
      THEN '参数值差异较大，请检查'
    ELSE NULL
  END AS 一致性建议
FROM station_param_stats
WHERE 不同值数量 > 1  -- 只显示有差异的参数
ORDER BY station_name, param_key;

COMMENT ON VIEW v_device_params_consistency_check IS
'参数一致性检查视图：检查同站点设备的参数差异，提供优化建议';

-- 3.3 视图：参数覆盖率检查（每个设备应有的参数）
CREATE OR REPLACE VIEW v_device_params_coverage_check AS
WITH required_params AS (
  SELECT param_key
  FROM dim_device_param_metadata
  WHERE category IN ('额定运行参数', '效率参数')
),
device_param_coverage AS (
  SELECT
    d.id AS device_id,
    d.name AS device_name,
    d.type AS device_type,
    s.name AS station_name,
    rp.param_key AS 必需参数,
    drp.param_key AS 实际参数,
    CASE WHEN drp.param_key IS NULL THEN '缺失' ELSE '已有' END AS 参数状态
  FROM dim_devices d
  JOIN dim_stations s ON d.station_id = s.id
  CROSS JOIN required_params rp
  LEFT JOIN device_rated_params drp ON d.id = drp.device_id
    AND rp.param_key = drp.param_key
    AND (drp.effective_to IS NULL OR drp.effective_to > NOW())
    AND (drp.effective_from IS NULL OR drp.effective_from <= NOW())
  WHERE d.type = 'pump'
)
SELECT
  device_id,
  device_name,
  station_name,
  必需参数,
  参数状态,
  COUNT(*) OVER (PARTITION BY device_id) AS 必需参数总数,
  SUM(CASE WHEN 参数状态 = '已有' THEN 1 ELSE 0 END) OVER (PARTITION BY device_id) AS 已有参数数,
  ROUND(
    SUM(CASE WHEN 参数状态 = '已有' THEN 1 ELSE 0 END) OVER (PARTITION BY device_id) * 100.0 /
    COUNT(*) OVER (PARTITION BY device_id),
    2
  ) AS 覆盖率百分比
FROM device_param_coverage
WHERE 参数状态 = '缺失'  -- 只显示缺失的参数
ORDER BY device_name, 必需参数;

COMMENT ON VIEW v_device_params_coverage_check IS
'参数覆盖率检查视图：检查每个设备的必需参数是否完整';

COMMIT;

-- ============================================
-- 回滚脚本（如需回滚，请执行以下语句）
-- ============================================

/*
BEGIN;

-- 删除视图
DROP VIEW IF EXISTS v_device_params_coverage_check;
DROP VIEW IF EXISTS v_device_params_consistency_check;
DROP VIEW IF EXISTS v_device_params_quality_check;

-- 删除触发器
DROP TRIGGER IF EXISTS trg_device_rated_params_validate_update ON device_rated_params;
DROP TRIGGER IF EXISTS trg_device_rated_params_validate_insert ON device_rated_params;

-- 删除触发器函数
DROP FUNCTION IF EXISTS fn_validate_device_rated_params();

-- 删除约束
ALTER TABLE device_rated_params DROP CONSTRAINT IF EXISTS chk_device_rated_params_value_numeric_range;
ALTER TABLE device_rated_params DROP CONSTRAINT IF EXISTS chk_device_rated_params_source_presence;
ALTER TABLE device_rated_params DROP CONSTRAINT IF EXISTS chk_device_rated_params_unit_presence;
ALTER TABLE device_rated_params DROP CONSTRAINT IF EXISTS chk_device_rated_params_tier_logic;
ALTER TABLE device_rated_params DROP CONSTRAINT IF EXISTS chk_device_rated_params_effective_dates;

COMMIT;
*/


