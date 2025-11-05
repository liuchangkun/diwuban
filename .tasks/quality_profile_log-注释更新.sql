-- ============================================
-- quality_profile_log 表注释补全脚本
-- 
-- 功能：为 quality_profile_log 表补全所有缺失的字段注释，并丰富表级注释
-- 方案：方案A - 最小化补全方案
-- 创建日期：2025-09-30
-- 执行模式：RIPER-5 协议 - 执行阶段
-- ============================================

-- ============================================
-- 第一部分：表级注释更新（1条）
-- ============================================

COMMENT ON TABLE public.quality_profile_log IS $DOC$
质量过程性能剖析日志（按窗口/阶段记录耗时与行数）

用途: 记录质量标注流程（sp_mark_quality_window_vfast）中每个执行阶段的性能指标，
包括窗口构建、各质量规则更新等阶段的耗时和影响行数。

使用场景:
- 性能监控: 分析质量标注流程的性能瓶颈
- 统计分析: 汇总各质量规则的命中数量（通过rows_affected聚合）
- 故障排查: 定位质量标注过程中的异常阶段

关联模块:
- 写入: sp_mark_quality_window_vfast 存储过程
- 读取: app/services/quality/mark_window.py（质量规则命中统计）
- 读取: scripts/verify_quality_counts.py（质量统计验证）

数据特征:
- 写入频率: 每次质量标注窗口执行时写入约15条记录（对应15个阶段）
- 数据增长: 持续增长，建议定期归档或清理历史数据
$DOC$;

-- ============================================
-- 第二部分：字段注释更新（9条）
-- ============================================

-- 1. window_start - 时间窗口开始时间
COMMENT ON COLUMN public.quality_profile_log.window_start IS 
'时间窗口开始时间（UTC时区，质量标注的起始时间戳）';

-- 2. window_end - 时间窗口结束时间
COMMENT ON COLUMN public.quality_profile_log.window_end IS 
'时间窗口结束时间（UTC时区，质量标注的结束时间戳）';

-- 3. station_id - 泵站ID（外键）
COMMENT ON COLUMN public.quality_profile_log.station_id IS 
'泵站ID（外键，关联dim_stations表，标识质量标注所属的泵站）';

-- 4. device_id - 设备ID（外键，优化注释）
COMMENT ON COLUMN public.quality_profile_log.device_id IS 
'设备ID（外键，关联dim_devices表，标识质量标注所属的设备）';

-- 5. stage - 执行阶段标识
COMMENT ON COLUMN public.quality_profile_log.stage IS 
'执行阶段标识（如fwin_build表示窗口构建，update_XXX表示质量规则XXX的更新阶段）';

-- 6. duration_ms - 执行耗时（毫秒）
COMMENT ON COLUMN public.quality_profile_log.duration_ms IS 
'执行耗时（毫秒，记录该阶段从开始到结束的时间消耗）';

-- 7. rows_affected - 影响行数
COMMENT ON COLUMN public.quality_profile_log.rows_affected IS 
'影响行数（该阶段操作影响的数据行数，如更新质量码的记录数）';

-- 8. details - 详细信息（JSONB，预留字段）
COMMENT ON COLUMN public.quality_profile_log.details IS 
'详细信息（JSONB格式，预留字段，用于存储额外的执行细节，当前未使用）';

-- 9. code - 质量规则代码（触发器自动填充）
COMMENT ON COLUMN public.quality_profile_log.code IS 
'质量规则代码（整数，如101、111、751等，由触发器从stage字段自动解析填充，用于优化查询）';

-- ============================================
-- 第三部分：验证查询
-- ============================================

-- 验证1: 查看更新后的表注释
SELECT obj_description('public.quality_profile_log'::regclass) AS updated_table_comment;

-- 验证2: 查看更新后的所有字段注释
SELECT 
    a.attname AS column_name,
    pg_catalog.col_description('public.quality_profile_log'::regclass, a.attnum) AS updated_comment,
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

-- ============================================
-- 脚本结束
-- ============================================

