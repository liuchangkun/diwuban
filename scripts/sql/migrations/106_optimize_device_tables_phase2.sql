-- ============================================
-- 数据库表优化 - 阶段2：功能增强
--
-- 功能：
-- 1. 添加全局级参数（rated_frequency, poles_pair, eta_motor, eta_vfd）
-- 2. 添加站点级参数（ambient_temp, ambient_pressure, pipe_diameter, pipe_length）
-- 3. 为所有现有参数设置 effective_from（启用时间有效性功能）
-- 4. 创建参数更新示例（演示历史版本保留）
-- 5. 验证视图 v_device_rated_params_current 正确过滤
--
-- 作者：AI
-- 创建日期：2025-11-09
-- 迁移编号：106
-- ============================================

BEGIN;

-- ============================================
-- 步骤1：添加全局级参数
-- ============================================

-- 说明：全局级参数适用于所有设备的默认值
-- 特征：station_id IS NULL AND device_id IS NULL

-- 1.1 全局参数：额定频率（中国电网标准50Hz）
INSERT INTO device_rated_params (
  station_id,
  device_id,
  param_key,
  value_numeric,
  unit,
  source,
  effective_from,
  created_at,
  updated_at
)
VALUES (
  NULL,
  NULL,
  'rated_frequency',
  50,
  'Hz',
  '全局默认值（中国电网标准）',
  NOW(),
  NOW(),
  NOW()
)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), param_key, COALESCE(effective_from, '1970-01-01'::timestamptz))
DO UPDATE SET
  value_numeric = EXCLUDED.value_numeric,
  unit = EXCLUDED.unit,
  source = EXCLUDED.source,
  updated_at = NOW();

-- 1.2 全局参数：极对数（1500rpm电机标准）
INSERT INTO device_rated_params (
  station_id,
  device_id,
  param_key,
  value_numeric,
  unit,
  source,
  effective_from,
  created_at,
  updated_at
)
VALUES (
  NULL,
  NULL,
  'poles_pair',
  2,
  NULL,
  '全局默认值（1500rpm电机）',
  NOW(),
  NOW(),
  NOW()
)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), param_key, COALESCE(effective_from, '1970-01-01'::timestamptz))
DO UPDATE SET
  value_numeric = EXCLUDED.value_numeric,
  source = EXCLUDED.source,
  updated_at = NOW();

-- 1.3 全局参数：电机效率（高效电机标准）
INSERT INTO device_rated_params (
  station_id,
  device_id,
  param_key,
  value_numeric,
  unit,
  source,
  effective_from,
  created_at,
  updated_at
)
VALUES (
  NULL,
  NULL,
  'eta_motor',
  0.93,
  NULL,
  '全局默认值（高效电机）',
  NOW(),
  NOW(),
  NOW()
)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), param_key, COALESCE(effective_from, '1970-01-01'::timestamptz))
DO UPDATE SET
  value_numeric = EXCLUDED.value_numeric,
  source = EXCLUDED.source,
  updated_at = NOW();

-- 1.4 全局参数：变频器效率
INSERT INTO device_rated_params (
  station_id,
  device_id,
  param_key,
  value_numeric,
  unit,
  source,
  effective_from,
  created_at,
  updated_at
)
VALUES (
  NULL,
  NULL,
  'eta_vfd',
  0.97,
  NULL,
  '全局默认值（变频器）',
  NOW(),
  NOW(),
  NOW()
)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), param_key, COALESCE(effective_from, '1970-01-01'::timestamptz))
DO UPDATE SET
  value_numeric = EXCLUDED.value_numeric,
  source = EXCLUDED.source,
  updated_at = NOW();

-- ============================================
-- 步骤2：添加站点级参数
-- ============================================

-- 说明：站点级参数适用于同一站点所有设备的共享参数
-- 特征：station_id IS NOT NULL AND device_id IS NULL

-- 2.1 站点参数：环境温度（二期供水泵房）
INSERT INTO device_rated_params (
  station_id,
  device_id,
  param_key,
  value_numeric,
  unit,
  source,
  effective_from,
  created_at,
  updated_at
)
SELECT
  s.id,
  NULL,
  'ambient_temp',
  20.0,
  '°C',
  '站点级参数（环境温度）',
  NOW(),
  NOW(),
  NOW()
FROM dim_stations s
WHERE s.name = '二期供水泵房'
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), param_key, COALESCE(effective_from, '1970-01-01'::timestamptz))
DO UPDATE SET
  value_numeric = EXCLUDED.value_numeric,
  unit = EXCLUDED.unit,
  source = EXCLUDED.source,
  updated_at = NOW();

-- 2.2 站点参数：环境压力（标准大气压）
INSERT INTO device_rated_params (
  station_id,
  device_id,
  param_key,
  value_numeric,
  unit,
  source,
  effective_from,
  created_at,
  updated_at
)
SELECT
  s.id,
  NULL,
  'ambient_pressure',
  101.325,
  'kPa',
  '站点级参数（标准大气压）',
  NOW(),
  NOW(),
  NOW()
FROM dim_stations s
WHERE s.name = '二期供水泵房'
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), param_key, COALESCE(effective_from, '1970-01-01'::timestamptz))
DO UPDATE SET
  value_numeric = EXCLUDED.value_numeric,
  unit = EXCLUDED.unit,
  source = EXCLUDED.source,
  updated_at = NOW();

-- 2.3 站点参数：管道直径
INSERT INTO device_rated_params (
  station_id,
  device_id,
  param_key,
  value_numeric,
  unit,
  source,
  effective_from,
  created_at,
  updated_at
)
SELECT
  s.id,
  NULL,
  'pipe_diameter',
  0.40,
  'm',
  '站点级参数（管道直径）',
  NOW(),
  NOW(),
  NOW()
FROM dim_stations s
WHERE s.name = '二期供水泵房'
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), param_key, COALESCE(effective_from, '1970-01-01'::timestamptz))
DO UPDATE SET
  value_numeric = EXCLUDED.value_numeric,
  unit = EXCLUDED.unit,
  source = EXCLUDED.source,
  updated_at = NOW();

-- 2.4 站点参数：管道长度
INSERT INTO device_rated_params (
  station_id,
  device_id,
  param_key,
  value_numeric,
  unit,
  source,
  effective_from,
  created_at,
  updated_at
)
SELECT
  s.id,
  NULL,
  'pipe_length',
  150.0,
  'm',
  '站点级参数（管道长度）',
  NOW(),
  NOW(),
  NOW()
FROM dim_stations s
WHERE s.name = '二期供水泵房'
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), param_key, COALESCE(effective_from, '1970-01-01'::timestamptz))
DO UPDATE SET
  value_numeric = EXCLUDED.value_numeric,
  unit = EXCLUDED.unit,
  source = EXCLUDED.source,
  updated_at = NOW();

-- ============================================
-- 步骤3：为大部分现有参数设置 effective_from
-- ============================================

-- 说明：启用时间有效性功能，为所有现有参数设置生效时间
-- 注意：排除设备1的 rated_power（用于演示参数更新）
UPDATE device_rated_params
SET
  effective_from = NOW(),
  updated_at = NOW()
WHERE effective_from IS NULL
  AND NOT (device_id = 1 AND param_key = 'rated_power');

-- ============================================
-- 步骤4：创建参数更新示例（演示历史版本保留）
-- ============================================

-- 说明：演示如何更新参数并保留历史版本
-- 场景：将设备1的 rated_power 从 75kW 更新为 90kW

-- 4.1 为旧版本设置 effective_from 和 effective_to（标记为历史版本）
UPDATE device_rated_params
SET
  effective_from = NOW() - INTERVAL '1 day',  -- 设置为1天前生效
  effective_to = NOW(),                        -- 设置为现在失效
  updated_at = NOW()
WHERE device_id = 1
  AND param_key = 'rated_power'
  AND effective_from IS NULL;

-- 4.2 插入新版本（新的 rated_power 值）
INSERT INTO device_rated_params (
  station_id,
  device_id,
  param_key,
  value_numeric,
  unit,
  source,
  effective_from,
  effective_to,
  created_at,
  updated_at
)
SELECT
  d.station_id,
  d.id,
  'rated_power',
  90,
  'kW',
  '参数更新示例（从75kW更新为90kW）',
  NOW(),
  NULL,
  NOW(),
  NOW()
FROM dim_devices d
WHERE d.id = 1;

-- ============================================
-- 步骤5：验证视图 v_device_rated_params_current
-- ============================================

-- 说明：验证视图正确过滤历史参数，只显示当前有效参数

-- 5.1 验证全局级参数（应该有4条）
DO $$
DECLARE
  global_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO global_count
  FROM v_device_rated_params_current
  WHERE station_id IS NULL AND device_id IS NULL;

  IF global_count <> 4 THEN
    RAISE EXCEPTION '全局级参数数量错误：期望4条，实际%条', global_count;
  END IF;

  RAISE NOTICE '✓ 全局级参数验证通过：%条', global_count;
END $$;

-- 5.2 验证站点级参数（应该有4条）
DO $$
DECLARE
  station_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO station_count
  FROM v_device_rated_params_current
  WHERE station_id IS NOT NULL AND device_id IS NULL;

  IF station_count <> 4 THEN
    RAISE EXCEPTION '站点级参数数量错误：期望4条，实际%条', station_count;
  END IF;

  RAISE NOTICE '✓ 站点级参数验证通过：%条', station_count;
END $$;

-- 5.3 验证设备1的 rated_power 只有1条当前记录（新版本90kW）
DO $$
DECLARE
  current_power NUMERIC;
  history_count INTEGER;
BEGIN
  -- 检查当前值
  SELECT value_numeric INTO current_power
  FROM v_device_rated_params_current
  WHERE device_id = 1 AND param_key = 'rated_power';

  IF current_power <> 90 THEN
    RAISE EXCEPTION '设备1的当前rated_power错误：期望90，实际%', current_power;
  END IF;

  -- 检查历史记录数量（应该有2条：旧版本75kW + 新版本90kW）
  SELECT COUNT(*) INTO history_count
  FROM device_rated_params
  WHERE device_id = 1 AND param_key = 'rated_power';

  IF history_count <> 2 THEN
    RAISE EXCEPTION '设备1的rated_power历史记录数量错误：期望2条，实际%条', history_count;
  END IF;

  RAISE NOTICE '✓ 参数历史版本验证通过：当前值=%kW，历史记录=%条', current_power, history_count;
END $$;

-- 5.4 验证所有参数都已设置 effective_from
DO $$
DECLARE
  null_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO null_count
  FROM device_rated_params
  WHERE effective_from IS NULL;

  IF null_count > 0 THEN
    RAISE EXCEPTION 'effective_from未设置的参数数量：%条', null_count;
  END IF;

  RAISE NOTICE '✓ 时间有效性验证通过：所有参数都已设置effective_from';
END $$;

COMMIT;

-- ============================================
-- 回滚脚本（如需回滚，请执行以下语句）
-- ============================================

/*
BEGIN;

-- 删除全局级参数
DELETE FROM device_rated_params
WHERE station_id IS NULL AND device_id IS NULL
  AND param_key IN ('rated_frequency', 'poles_pair', 'eta_motor', 'eta_vfd');

-- 删除站点级参数
DELETE FROM device_rated_params
WHERE station_id IS NOT NULL AND device_id IS NULL
  AND param_key IN ('ambient_temp', 'ambient_pressure', 'pipe_diameter', 'pipe_length');

-- 删除设备1的新版本 rated_power（90kW）
DELETE FROM device_rated_params
WHERE device_id = 1 AND param_key = 'rated_power' AND value_numeric = 90;

-- 恢复设备1的旧版本 rated_power（75kW）
UPDATE device_rated_params
SET effective_to = NULL, updated_at = NOW()
WHERE device_id = 1 AND param_key = 'rated_power' AND value_numeric = 75;

-- 清除所有 effective_from（如果需要）
-- UPDATE device_rated_params SET effective_from = NULL, updated_at = NOW();

COMMIT;
*/


