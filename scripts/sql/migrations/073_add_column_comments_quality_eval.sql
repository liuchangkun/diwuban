-- ============================================
-- 为 quality_eval_by_device_metric 表添加列注释
--
-- 功能：补充缺失的7个列注释，符合数据库规范要求
-- 作者：AI Assistant
-- 创建日期：2025-11-04
-- 相关任务：quality_eval_by_device_metric 表字段文档完善
-- ============================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 为 quality_eval_by_device_metric 表添加列注释
-- ----------------------------------------------------------------------------

COMMENT ON COLUMN public.quality_eval_by_device_metric.window_start IS 
'统计窗口起始时间：定义统计时间范围的起点（UTC时区，timestamptz类型），作为主键的一部分确保同一窗口不会重复统计';

COMMENT ON COLUMN public.quality_eval_by_device_metric.window_end IS 
'统计窗口结束时间：定义统计时间范围的终点（UTC时区，timestamptz类型），作为主键的一部分确保同一窗口不会重复统计';

COMMENT ON COLUMN public.quality_eval_by_device_metric.station_id IS 
'泵站ID：评估所属的泵站ID（外键，引用 dim_stations.id，默认值0），作为主键的一部分支持按站点维度统计';

COMMENT ON COLUMN public.quality_eval_by_device_metric.quality_status IS 
'质量状态码：标识数据质量类型（0=正常数据，>0=异常数据，整数类型），作为主键的一部分确保每个质量码的统计独立';

COMMENT ON COLUMN public.quality_eval_by_device_metric.rows_count IS 
'该质量码的行数：统计该质量码在窗口内的数据行数（bigint类型），用于计算占比和质量分析';

COMMENT ON COLUMN public.quality_eval_by_device_metric.total_count IS 
'总行数：该设备×指标在窗口内所有质量码的行数之和（bigint类型），用作占比计算的分母';

COMMENT ON COLUMN public.quality_eval_by_device_metric.ratio IS 
'占比：该质量码的行数占总行数的比例（numeric(9,6)类型，计算公式：rows_count/total_count，取值范围0.000000~1.000000）';

COMMIT;

