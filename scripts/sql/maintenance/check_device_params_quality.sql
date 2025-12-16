-- ============================================
-- 设备参数质量检查脚本
--
-- 功能：
-- 1. 检查参数质量问题（缺失值、异常值、单位缺失、来源缺失）
-- 2. 检查参数一致性问题（同站点设备参数差异）
-- 3. 检查参数覆盖率问题（必需参数缺失）
--
-- 使用方法：
--   psql -h localhost -U postgres -d pump_station_optimization -f scripts/sql/maintenance/check_device_params_quality.sql
--
-- 或在 psql 中执行：
--   \i scripts/sql/maintenance/check_device_params_quality.sql
--
-- 作者：AI
-- 创建日期：2025-11-09
-- ============================================

\echo '============================================'
\echo '设备参数质量检查报告'
\echo '生成时间：' `date`
\echo '============================================'
\echo ''

-- ============================================
-- 检查1：参数质量问题
-- ============================================

\echo '【检查1】参数质量问题（缺失值、异常值、单位缺失、来源缺失）'
\echo '--------------------------------------------'

SELECT 
  COUNT(*) AS 质量问题总数
FROM v_device_params_quality_check;

\echo ''
\echo '详细问题列表：'

SELECT 
  device_name AS 设备名称,
  station_name AS 站点名称,
  param_key AS 参数键,
  质量问题_缺失,
  质量问题_异常值,
  质量问题_单位,
  质量问题_来源,
  value_numeric AS 参数值,
  unit AS 单位,
  source AS 来源
FROM v_device_params_quality_check
ORDER BY device_name, param_key;

\echo ''
\echo '--------------------------------------------'
\echo ''

-- ============================================
-- 检查2：参数一致性问题
-- ============================================

\echo '【检查2】参数一致性问题（同站点设备参数差异）'
\echo '--------------------------------------------'

SELECT 
  COUNT(*) AS 一致性问题总数
FROM v_device_params_consistency_check
WHERE 一致性建议 IS NOT NULL;

\echo ''
\echo '详细问题列表：'

SELECT 
  station_name AS 站点名称,
  param_key AS 参数键,
  不同值数量,
  最小值,
  最大值,
  平均值,
  ROUND(标准差::numeric, 4) AS 标准差,
  设备数量,
  一致性建议
FROM v_device_params_consistency_check
ORDER BY station_name, param_key;

\echo ''
\echo '--------------------------------------------'
\echo ''

-- ============================================
-- 检查3：参数覆盖率问题
-- ============================================

\echo '【检查3】参数覆盖率问题（必需参数缺失）'
\echo '--------------------------------------------'

SELECT 
  COUNT(DISTINCT device_id) AS 缺失参数的设备数
FROM v_device_params_coverage_check;

\echo ''
\echo '详细问题列表：'

SELECT 
  device_name AS 设备名称,
  station_name AS 站点名称,
  必需参数,
  参数状态,
  覆盖率百分比 || '%' AS 覆盖率
FROM v_device_params_coverage_check
ORDER BY device_name, 必需参数;

\echo ''
\echo '--------------------------------------------'
\echo ''

-- ============================================
-- 检查4：约束违反检查
-- ============================================

\echo '【检查4】约束违反检查（潜在的数据质量问题）'
\echo '--------------------------------------------'

-- 4.1 检查时间有效性违反
\echo '4.1 时间有效性违反（effective_from > effective_to）：'

SELECT 
  COUNT(*) AS 违反数量
FROM device_rated_params
WHERE effective_from IS NOT NULL 
  AND effective_to IS NOT NULL 
  AND effective_from > effective_to;

-- 4.2 检查三层参数逻辑违反
\echo ''
\echo '4.2 三层参数逻辑违反：'

SELECT 
  COUNT(*) AS 违反数量
FROM device_rated_params
WHERE NOT (
  (station_id IS NULL AND device_id IS NULL) OR
  (station_id IS NOT NULL AND device_id IS NULL) OR
  (device_id IS NOT NULL)
);

-- 4.3 检查参数值范围违反（示例：效率参数）
\echo ''
\echo '4.3 效率参数范围违反（应在0-1之间）：'

SELECT 
  param_key AS 参数键,
  COUNT(*) AS 违反数量,
  MIN(value_numeric) AS 最小值,
  MAX(value_numeric) AS 最大值
FROM device_rated_params
WHERE param_key IN ('eta_motor', 'eta_vfd', 'rated_efficiency')
  AND (value_numeric < 0 OR value_numeric > 1)
GROUP BY param_key;

\echo ''
\echo '--------------------------------------------'
\echo ''

-- ============================================
-- 检查5：统计摘要
-- ============================================

\echo '【检查5】统计摘要'
\echo '--------------------------------------------'

SELECT 
  '总参数数' AS 统计项,
  COUNT(*)::text AS 数值
FROM device_rated_params
UNION ALL
SELECT 
  '全局级参数',
  COUNT(*)::text
FROM device_rated_params
WHERE station_id IS NULL AND device_id IS NULL
UNION ALL
SELECT 
  '站点级参数',
  COUNT(*)::text
FROM device_rated_params
WHERE station_id IS NOT NULL AND device_id IS NULL
UNION ALL
SELECT 
  '设备级参数',
  COUNT(*)::text
FROM device_rated_params
WHERE device_id IS NOT NULL
UNION ALL
SELECT 
  '已设置effective_from',
  COUNT(*)::text
FROM device_rated_params
WHERE effective_from IS NOT NULL
UNION ALL
SELECT 
  '已设置effective_to（历史版本）',
  COUNT(*)::text
FROM device_rated_params
WHERE effective_to IS NOT NULL;

\echo ''
\echo '============================================'
\echo '检查完成'
\echo '============================================'

