-- ============================================
-- 数据库表优化 - 阶段1：快速优化
--
-- 功能：
-- 1. 从 dim_device_capabilities 迁移 rated_power_kw 和 rated_current_a 到 device_rated_params
-- 2. 删除 dim_device_capabilities 的冗余字段
-- 3. 为 device_rated_params 添加常用索引
-- 4. 创建常用查询视图
--
-- 作者：AI
-- 创建日期：2025-11-09
-- 迁移编号：105
-- ============================================

BEGIN;

-- ============================================
-- 步骤1：数据迁移
-- ============================================

-- 1.1 迁移 rated_power_kw 到 device_rated_params
INSERT INTO device_rated_params (
  device_id,
  station_id,
  param_key,
  value_numeric,
  unit,
  source,
  created_at,
  updated_at
)
SELECT
  dc.device_id,
  d.station_id,
  'rated_power' AS param_key,
  dc.rated_power_kw AS value_numeric,
  'kW' AS unit,
  '从 dim_device_capabilities 迁移' AS source,
  NOW() AS created_at,
  NOW() AS updated_at
FROM dim_device_capabilities dc
JOIN dim_devices d ON dc.device_id = d.id
WHERE dc.rated_power_kw IS NOT NULL
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), param_key, COALESCE(effective_from, '1970-01-01'::timestamptz))
DO UPDATE SET
  value_numeric = EXCLUDED.value_numeric,
  unit = EXCLUDED.unit,
  source = EXCLUDED.source,
  updated_at = NOW();

-- 1.2 迁移 rated_current_a 到 device_rated_params
INSERT INTO device_rated_params (
  device_id,
  station_id,
  param_key,
  value_numeric,
  unit,
  source,
  created_at,
  updated_at
)
SELECT
  dc.device_id,
  d.station_id,
  'rated_current' AS param_key,
  dc.rated_current_a AS value_numeric,
  'A' AS unit,
  '从 dim_device_capabilities 迁移' AS source,
  NOW() AS created_at,
  NOW() AS updated_at
FROM dim_device_capabilities dc
JOIN dim_devices d ON dc.device_id = d.id
WHERE dc.rated_current_a IS NOT NULL
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), param_key, COALESCE(effective_from, '1970-01-01'::timestamptz))
DO UPDATE SET
  value_numeric = EXCLUDED.value_numeric,
  unit = EXCLUDED.unit,
  source = EXCLUDED.source,
  updated_at = NOW();

-- ============================================
-- 步骤2：删除冗余字段
-- ============================================

-- 2.1 删除 rated_power_kw 字段
ALTER TABLE dim_device_capabilities DROP COLUMN IF EXISTS rated_power_kw;

-- 2.2 删除 rated_current_a 字段
ALTER TABLE dim_device_capabilities DROP COLUMN IF EXISTS rated_current_a;

-- 2.3 更新表注释
COMMENT ON TABLE dim_device_capabilities IS '设备能力配置表

存储设备的基本能力参数，如变频器配置、频率范围等。

职责边界：
- 存储设备的能力边界（如频率范围）
- 存储设备的功能开关（如是否支持变频）
- 不存储额定参数（已迁移到 device_rated_params）

数据来源：
- 自适应SQL脚本自动填充（scripts/sql/adaptive/02_device_related.sql）
- 根据泵类型自动设置默认值

使用场景：
- 优化算法中的约束条件（频率范围）
- 设备功能判断（是否支持变频）

注意事项：
- 额定功率和额定电流已迁移到 device_rated_params 表
- 使用 UPSERT 策略更新，不再使用 TRUNCATE CASCADE';

-- ============================================
-- 步骤3：添加索引
-- ============================================

-- 3.1 添加 param_key 索引（支持按参数键查询所有设备）
CREATE INDEX IF NOT EXISTS idx_device_rated_params_param_key 
ON device_rated_params(param_key);

-- 3.2 添加 device_id + param_key 复合索引（支持最常见的查询模式）
CREATE INDEX IF NOT EXISTS idx_device_rated_params_device_param 
ON device_rated_params(device_id, param_key)
WHERE device_id IS NOT NULL;

-- 3.3 添加 station_id 部分索引（支持站点级参数查询）
CREATE INDEX IF NOT EXISTS idx_device_rated_params_station 
ON device_rated_params(station_id)
WHERE station_id IS NOT NULL AND device_id IS NULL;

-- 3.4 添加时间有效性索引（支持时间范围查询）
CREATE INDEX IF NOT EXISTS idx_device_rated_params_effective 
ON device_rated_params(effective_from, effective_to);

COMMIT;

-- ============================================
-- 步骤4：创建查询视图（在事务外执行）
-- ============================================

-- 4.1 创建当前有效参数视图
CREATE OR REPLACE VIEW v_device_rated_params_current AS
SELECT 
  id,
  device_id,
  station_id,
  param_key,
  value_numeric,
  value_text,
  unit,
  source,
  effective_from,
  effective_to,
  created_at,
  updated_at
FROM device_rated_params
WHERE (effective_to IS NULL OR effective_to > NOW())
  AND (effective_from IS NULL OR effective_from <= NOW());

COMMENT ON VIEW v_device_rated_params_current IS '当前有效的设备参数视图

只显示当前时间有效的参数（effective_from <= NOW() AND effective_to > NOW()）。

使用场景：
- 查询设备当前的参数配置
- 优化算法中获取设备参数
- 报表生成

示例：
  SELECT * FROM v_device_rated_params_current WHERE device_id = 1001;';

-- 4.2 创建参数+元数据视图
CREATE OR REPLACE VIEW v_device_params_with_metadata AS
SELECT
  drp.id,
  drp.device_id,
  drp.station_id,
  drp.param_key,
  drp.value_numeric,
  drp.value_text,
  drp.unit,
  drp.source,
  drp.effective_from,
  drp.effective_to,
  drp.created_at,
  drp.updated_at,
  -- 参数元数据
  dpm.param_name_cn,
  dpm.param_name_en,
  dpm.category,
  dpm.description,
  dpm.physical_meaning,
  dpm.formula,
  dpm.typical_range,
  dpm.example_value,
  dpm.usage,
  dpm.data_source,
  dpm.code_location,
  dpm.remark AS metadata_remark
FROM device_rated_params drp
LEFT JOIN dim_device_param_metadata dpm ON drp.param_key = dpm.param_key
WHERE (drp.effective_to IS NULL OR drp.effective_to > NOW())
  AND (drp.effective_from IS NULL OR drp.effective_from <= NOW());

COMMENT ON VIEW v_device_params_with_metadata IS '设备参数+元数据视图

联表查询 device_rated_params 和 dim_device_param_metadata，提供参数值和参数元数据。

使用场景：
- 前端UI显示参数（需要中文名称、单位、说明）
- API返回参数详情
- 自动生成参数文档

示例：
  SELECT device_id, param_name_cn, value_numeric, unit, description
  FROM v_device_params_with_metadata
  WHERE device_id = 1001;';

-- 4.3 创建设备完整信息视图
CREATE OR REPLACE VIEW v_device_complete_info AS
SELECT
  d.id AS device_id,
  d.name AS device_name,
  d.type AS device_type,
  s.id AS station_id,
  s.name AS station_name,
  -- 设备能力
  dc.vfd_enabled,
  dc.freq_min,
  dc.freq_max,
  dc.remark AS capabilities_remark,
  -- 常用参数（透视）
  MAX(CASE WHEN drp.param_key = 'rated_frequency' THEN drp.value_numeric END) AS rated_frequency,
  MAX(CASE WHEN drp.param_key = 'poles_pair' THEN drp.value_numeric END) AS poles_pair,
  MAX(CASE WHEN drp.param_key = 'rated_efficiency' THEN drp.value_numeric END) AS rated_efficiency,
  MAX(CASE WHEN drp.param_key = 'rated_flow' THEN drp.value_numeric END) AS rated_flow,
  MAX(CASE WHEN drp.param_key = 'rated_head' THEN drp.value_numeric END) AS rated_head,
  MAX(CASE WHEN drp.param_key = 'rated_power' THEN drp.value_numeric END) AS rated_power,
  MAX(CASE WHEN drp.param_key = 'rated_current' THEN drp.value_numeric END) AS rated_current,
  MAX(CASE WHEN drp.param_key = 'eta_motor' THEN drp.value_numeric END) AS eta_motor,
  MAX(CASE WHEN drp.param_key = 'eta_vfd' THEN drp.value_numeric END) AS eta_vfd
FROM dim_devices d
JOIN dim_stations s ON d.station_id = s.id
LEFT JOIN dim_device_capabilities dc ON d.id = dc.device_id
LEFT JOIN device_rated_params drp ON d.id = drp.device_id
  AND (drp.effective_to IS NULL OR drp.effective_to > NOW())
  AND (drp.effective_from IS NULL OR drp.effective_from <= NOW())
WHERE d.type = 'pump'
GROUP BY
  d.id, d.name, d.type,
  s.id, s.name,
  dc.vfd_enabled, dc.freq_min, dc.freq_max, dc.remark;

COMMENT ON VIEW v_device_complete_info IS '设备完整信息视图

联表查询 dim_devices、dim_stations、dim_device_capabilities、device_rated_params，
提供设备的完整信息（基本信息 + 能力 + 常用参数）。

使用场景：
- 设备详情页面
- 优化算法获取设备完整配置
- 报表生成

注意事项：
- 只包含泵类型设备（type = ''pump''）
- 参数使用透视（CASE WHEN）展开为列
- 只显示当前有效的参数

示例：
  SELECT * FROM v_device_complete_info WHERE device_id = 1001;';

-- ============================================
-- 迁移完成
-- ============================================

-- 验证数据迁移结果
DO $$
DECLARE
  migrated_power_count INT;
  migrated_current_count INT;
BEGIN
  -- 统计迁移的 rated_power 数量
  SELECT COUNT(*) INTO migrated_power_count
  FROM device_rated_params
  WHERE param_key = 'rated_power'
    AND source = '从 dim_device_capabilities 迁移';

  -- 统计迁移的 rated_current 数量
  SELECT COUNT(*) INTO migrated_current_count
  FROM device_rated_params
  WHERE param_key = 'rated_current'
    AND source = '从 dim_device_capabilities 迁移';

  -- 输出迁移结果
  RAISE NOTICE '✅ 数据迁移完成：';
  RAISE NOTICE '  - rated_power: % 条记录', migrated_power_count;
  RAISE NOTICE '  - rated_current: % 条记录', migrated_current_count;
  RAISE NOTICE '✅ 字段删除完成：';
  RAISE NOTICE '  - dim_device_capabilities.rated_power_kw 已删除';
  RAISE NOTICE '  - dim_device_capabilities.rated_current_a 已删除';
  RAISE NOTICE '✅ 索引创建完成：';
  RAISE NOTICE '  - idx_device_rated_params_param_key';
  RAISE NOTICE '  - idx_device_rated_params_device_param';
  RAISE NOTICE '  - idx_device_rated_params_station';
  RAISE NOTICE '  - idx_device_rated_params_effective';
  RAISE NOTICE '✅ 视图创建完成：';
  RAISE NOTICE '  - v_device_rated_params_current';
  RAISE NOTICE '  - v_device_params_with_metadata';
  RAISE NOTICE '  - v_device_complete_info';
  RAISE NOTICE '';
  RAISE NOTICE '🎉 阶段1优化完成！';
END $$;

