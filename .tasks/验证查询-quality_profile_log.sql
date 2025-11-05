-- ============================================
-- quality_profile_log 表注释验证查询
-- 
-- 功能：验证注释更新是否成功
-- 创建日期：2025-09-30
-- ============================================

-- ============================================
-- 验证1: 查看更新后的表注释
-- ============================================

SELECT obj_description('public.quality_profile_log'::regclass) AS updated_table_comment;

-- 预期结果: 应显示包含"用途"、"使用场景"、"关联模块"、"数据特征"的详细注释


-- ============================================
-- 验证2: 查看更新后的所有字段注释（详细版）
-- ============================================

SELECT 
    a.attnum AS column_order,
    a.attname AS column_name,
    format_type(a.atttypid, a.atttypmod) AS data_type,
    CASE WHEN a.attnotnull THEN 'NOT NULL' ELSE 'NULL' END AS nullable,
    pg_catalog.col_description('public.quality_profile_log'::regclass, a.attnum) AS comment,
    CASE 
        WHEN pg_catalog.col_description('public.quality_profile_log'::regclass, a.attnum) IS NULL 
        THEN '❌ 缺失' 
        ELSE '✅ 已有' 
    END AS status
FROM pg_catalog.pg_attribute a
WHERE a.attrelid = 'public.quality_profile_log'::regclass
  AND a.attnum > 0
  AND NOT a.attisdropped
ORDER BY a.attnum;

-- 预期结果: 所有11个字段的 status 列都应显示 ✅ 已有


-- ============================================
-- 验证3: 检查注释完整率统计
-- ============================================

SELECT 
    COUNT(*) AS total_columns,
    COUNT(pg_catalog.col_description('public.quality_profile_log'::regclass, a.attnum)) AS commented_columns,
    COUNT(*) - COUNT(pg_catalog.col_description('public.quality_profile_log'::regclass, a.attnum)) AS missing_columns,
    ROUND(
        COUNT(pg_catalog.col_description('public.quality_profile_log'::regclass, a.attnum))::numeric / COUNT(*)::numeric * 100, 
        2
    ) AS completion_rate
FROM pg_catalog.pg_attribute a
WHERE a.attrelid = 'public.quality_profile_log'::regclass
  AND a.attnum > 0
  AND NOT a.attisdropped;

-- 预期结果:
-- total_columns: 11
-- commented_columns: 11
-- missing_columns: 0
-- completion_rate: 100.00


-- ============================================
-- 验证4: 列出所有缺失注释的字段（应为空）
-- ============================================

SELECT 
    a.attname AS missing_comment_column
FROM pg_catalog.pg_attribute a
WHERE a.attrelid = 'public.quality_profile_log'::regclass
  AND a.attnum > 0
  AND NOT a.attisdropped
  AND pg_catalog.col_description('public.quality_profile_log'::regclass, a.attnum) IS NULL;

-- 预期结果: 0 rows (无缺失注释的字段)


-- ============================================
-- 验证5: 检查注释语言（确保全部为中文）
-- ============================================

SELECT 
    a.attname AS column_name,
    pg_catalog.col_description('public.quality_profile_log'::regclass, a.attnum) AS comment,
    CASE 
        WHEN pg_catalog.col_description('public.quality_profile_log'::regclass, a.attnum) ~ '[a-zA-Z]{10,}' 
        THEN '⚠️ 可能包含英文' 
        ELSE '✅ 中文' 
    END AS language_check
FROM pg_catalog.pg_attribute a
WHERE a.attrelid = 'public.quality_profile_log'::regclass
  AND a.attnum > 0
  AND NOT a.attisdropped
  AND pg_catalog.col_description('public.quality_profile_log'::regclass, a.attnum) IS NOT NULL
ORDER BY a.attnum;

-- 预期结果: 所有字段的 language_check 列都应显示 ✅ 中文


-- ============================================
-- 验证6: 对比更新前后的注释变化
-- ============================================

-- 更新前的注释备份（从执行前检查获取）:
-- id: "主键：质量画像日志记录的唯一标识符"
-- created_at: "创建时间：记录创建的时间戳"
-- window_start: NULL
-- window_end: NULL
-- station_id: NULL
-- device_id: "设备ID：画像所属的设备ID"
-- stage: NULL
-- duration_ms: NULL
-- rows_affected: NULL
-- details: NULL
-- code: NULL

-- 更新后应该有9个字段的注释发生变化（7个新增 + 2个优化）


-- ============================================
-- 验证7: 检查特定字段的注释内容
-- ============================================

-- 检查 window_start 字段注释
SELECT 
    'window_start' AS field_name,
    pg_catalog.col_description('public.quality_profile_log'::regclass, 
        (SELECT attnum FROM pg_attribute WHERE attrelid = 'public.quality_profile_log'::regclass AND attname = 'window_start')
    ) AS comment,
    CASE 
        WHEN pg_catalog.col_description('public.quality_profile_log'::regclass, 
            (SELECT attnum FROM pg_attribute WHERE attrelid = 'public.quality_profile_log'::regclass AND attname = 'window_start')
        ) LIKE '%UTC%' AND pg_catalog.col_description('public.quality_profile_log'::regclass, 
            (SELECT attnum FROM pg_attribute WHERE attrelid = 'public.quality_profile_log'::regclass AND attname = 'window_start')
        ) LIKE '%时间窗口%'
        THEN '✅ 符合预期'
        ELSE '❌ 不符合预期'
    END AS validation;

-- 检查 stage 字段注释
SELECT 
    'stage' AS field_name,
    pg_catalog.col_description('public.quality_profile_log'::regclass, 
        (SELECT attnum FROM pg_attribute WHERE attrelid = 'public.quality_profile_log'::regclass AND attname = 'stage')
    ) AS comment,
    CASE 
        WHEN pg_catalog.col_description('public.quality_profile_log'::regclass, 
            (SELECT attnum FROM pg_attribute WHERE attrelid = 'public.quality_profile_log'::regclass AND attname = 'stage')
        ) LIKE '%fwin_build%' AND pg_catalog.col_description('public.quality_profile_log'::regclass, 
            (SELECT attnum FROM pg_attribute WHERE attrelid = 'public.quality_profile_log'::regclass AND attname = 'stage')
        ) LIKE '%update_XXX%'
        THEN '✅ 符合预期'
        ELSE '❌ 不符合预期'
    END AS validation;

-- 检查 code 字段注释
SELECT 
    'code' AS field_name,
    pg_catalog.col_description('public.quality_profile_log'::regclass, 
        (SELECT attnum FROM pg_attribute WHERE attrelid = 'public.quality_profile_log'::regclass AND attname = 'code')
    ) AS comment,
    CASE 
        WHEN pg_catalog.col_description('public.quality_profile_log'::regclass, 
            (SELECT attnum FROM pg_attribute WHERE attrelid = 'public.quality_profile_log'::regclass AND attname = 'code')
        ) LIKE '%触发器%' AND pg_catalog.col_description('public.quality_profile_log'::regclass, 
            (SELECT attnum FROM pg_attribute WHERE attrelid = 'public.quality_profile_log'::regclass AND attname = 'code')
        ) LIKE '%101%'
        THEN '✅ 符合预期'
        ELSE '❌ 不符合预期'
    END AS validation;


-- ============================================
-- 验证完成
-- ============================================

-- 如果所有验证查询都通过，说明注释更新成功！

