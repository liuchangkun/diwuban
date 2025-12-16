\encoding UTF8
SET client_encoding = 'UTF8';

-- =====================================================================
-- 迁移脚本: 060_alter_device_running_thresholds_phase1.sql
-- 用途: 为device_running_thresholds表添加智能识别所需的18个新字段（阶段1）
-- 创建日期: 2025-10-31
-- 依赖: 009_device_running_thresholds.sql
-- 修订说明: 
--   1. 解决历史数据可用性限制（添加data_days_available字段）
--   2. 解决设备类型数据来源不明确（添加device_type_source字段）
--   3. 支持"人工设置优先，自动识别作为fallback"策略
--   4. 支持数据不足时的降级处理
-- =====================================================================

BEGIN;

-- ========== 1. 设备类型识别字段 ==========

-- 1.1 设备类型（识别结果）
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS device_type TEXT DEFAULT 'unknown'
  CHECK (device_type IN ('vfd', 'soft_start', 'unknown'));

COMMENT ON COLUMN public.device_running_thresholds.device_type IS 
  '设备类型: vfd=变频泵(频率可变45-50Hz), soft_start=软启动泵(频率恒定50Hz), unknown=未识别。优先使用dim_devices.pump_type，如果为NULL则自动识别';

-- 1.2 设备类型来源（新增字段）
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS device_type_source TEXT DEFAULT 'unknown'
  CHECK (device_type_source IN ('config', 'auto', 'unknown'));

COMMENT ON COLUMN public.device_running_thresholds.device_type_source IS 
  '设备类型来源: config=从dim_devices.pump_type读取, auto=自动识别, unknown=未识别';

-- 1.3 是否自动识别
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS device_type_auto_detected BOOLEAN DEFAULT FALSE NOT NULL;

COMMENT ON COLUMN public.device_running_thresholds.device_type_auto_detected IS 
  '是否通过自动识别得到设备类型: TRUE=自动识别, FALSE=配置文件或未识别';

-- ========== 2. 运行模式识别字段 ==========

-- 2.1 运行模式
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS running_mode TEXT DEFAULT 'unknown'
  CHECK (running_mode IN ('continuous', 'frequent', 'occasional', 'unknown'));

COMMENT ON COLUMN public.device_running_thresholds.running_mode IS 
  '运行模式: continuous=持续运行(>80%), frequent=频繁启停(20-80%), occasional=偶尔运行(<20%), unknown=未识别';

-- 2.2 运行时长比例
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS running_time_ratio DOUBLE PRECISION DEFAULT NULL;

COMMENT ON COLUMN public.device_running_thresholds.running_time_ratio IS 
  '历史运行时长比例(0-1): 从最近7天数据计算, 用于判定运行模式';

-- 2.3 数据可用性（新增字段）
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS data_days_available INTEGER DEFAULT NULL;

COMMENT ON COLUMN public.device_running_thresholds.data_days_available IS 
  '实际可用数据天数: 用于评估识别质量, NULL表示未评估。最少需要3天数据进行识别，推荐7天';

-- ========== 3. 自适应时间窗口字段 ==========

-- 3.1 学习到的启动窗口
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS startup_window_secs_learned DOUBLE PRECISION DEFAULT NULL;

COMMENT ON COLUMN public.device_running_thresholds.startup_window_secs_learned IS 
  '学习到的启动窗口(秒): 从历史数据学习的P95启动时长, NULL表示未学习';

-- 3.2 学习到的停止窗口
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS shutdown_window_secs_learned DOUBLE PRECISION DEFAULT NULL;

COMMENT ON COLUMN public.device_running_thresholds.shutdown_window_secs_learned IS 
  '学习到的停止窗口(秒): 从历史数据学习的P95停止时长, NULL表示未学习';

-- 3.3 实际使用的启动窗口
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS startup_window_secs_effective INTEGER DEFAULT 30 NOT NULL;

COMMENT ON COLUMN public.device_running_thresholds.startup_window_secs_effective IS 
  '实际使用的启动窗口(秒): 如果startup_window_secs_learned不为NULL则使用学习值，否则使用默认值30秒';

-- 3.4 实际使用的停止窗口
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS shutdown_window_secs_effective INTEGER DEFAULT 20 NOT NULL;

COMMENT ON COLUMN public.device_running_thresholds.shutdown_window_secs_effective IS 
  '实际使用的停止窗口(秒): 如果shutdown_window_secs_learned不为NULL则使用学习值，否则使用默认值20秒';

-- ========== 4. 启动电流冲击识别字段 ==========

-- 4.1 启动电流冲击倍数
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS startup_inrush_multiplier DOUBLE PRECISION DEFAULT 6.0 NOT NULL;

COMMENT ON COLUMN public.device_running_thresholds.startup_inrush_multiplier IS 
  '启动电流冲击倍数(相对于i_on): 从历史数据学习, 默认值6.0, 典型值5-7倍';

-- 4.2 启动电流冲击持续时间
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS startup_inrush_duration_secs INTEGER DEFAULT 3 NOT NULL;

COMMENT ON COLUMN public.device_running_thresholds.startup_inrush_duration_secs IS 
  '启动电流冲击持续时间(秒): 从历史数据学习, 默认值3秒, 典型值2-5秒';

-- ========== 5. 信号融合策略字段 ==========

-- 5.1 是否使用加权融合
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS use_weighted_fusion BOOLEAN DEFAULT FALSE NOT NULL;

COMMENT ON COLUMN public.device_running_thresholds.use_weighted_fusion IS 
  '是否使用加权融合: TRUE=使用加权融合(新算法), FALSE=使用OR逻辑(原算法)。默认FALSE保持向后兼容';

-- 5.2 电流信号权重
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS signal_weight_current DOUBLE PRECISION DEFAULT 0.5 NOT NULL;

COMMENT ON COLUMN public.device_running_thresholds.signal_weight_current IS 
  '电流信号权重: 用于加权融合, 变频泵默认0.4, 软启动泵默认0.6';

-- 5.3 功率信号权重
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS signal_weight_power DOUBLE PRECISION DEFAULT 0.3 NOT NULL;

COMMENT ON COLUMN public.device_running_thresholds.signal_weight_power IS 
  '功率信号权重: 用于加权融合, 变频泵默认0.3, 软启动泵默认0.4';

-- 5.4 频率信号权重
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS signal_weight_frequency DOUBLE PRECISION DEFAULT 0.2 NOT NULL;

COMMENT ON COLUMN public.device_running_thresholds.signal_weight_frequency IS 
  '频率信号权重: 用于加权融合, 变频泵默认0.3, 软启动泵默认0.0（不使用频率）';

-- ========== 6. 阈值学习质量字段 ==========

-- 6.1 阈值学习质量
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS threshold_quality TEXT DEFAULT 'unknown'
  CHECK (threshold_quality IN ('high', 'medium', 'low', 'insufficient', 'unknown'));

COMMENT ON COLUMN public.device_running_thresholds.threshold_quality IS 
  '阈值学习质量: high=7天+数据, medium=3-7天数据, low=1-3天数据, insufficient=<1天数据, unknown=未评估';

-- 6.2 上次完整学习时间
ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS last_full_learning_ts TIMESTAMPTZ DEFAULT NULL;

COMMENT ON COLUMN public.device_running_thresholds.last_full_learning_ts IS 
  '上次完整学习时间: 记录最后一次执行完整学习流程的时间, 用于判断是否需要重新学习';

-- ========== 7. 添加约束 ==========

-- 7.1 权重和约束（允许0.01的误差）
ALTER TABLE public.device_running_thresholds
ADD CONSTRAINT chk_weights_sum 
  CHECK (ABS(signal_weight_current + signal_weight_power + signal_weight_frequency - 1.0) < 0.01);

-- 7.2 时间窗口约束
ALTER TABLE public.device_running_thresholds
ADD CONSTRAINT chk_window_positive
  CHECK (startup_window_secs_effective > 0 AND shutdown_window_secs_effective > 0);

-- 7.3 启动电流冲击约束
ALTER TABLE public.device_running_thresholds
ADD CONSTRAINT chk_inrush_positive
  CHECK (startup_inrush_multiplier > 1.0 AND startup_inrush_duration_secs > 0);

-- 7.4 运行时长比例约束
ALTER TABLE public.device_running_thresholds
ADD CONSTRAINT chk_running_ratio_range
  CHECK (running_time_ratio IS NULL OR (running_time_ratio >= 0 AND running_time_ratio <= 1));

-- 7.5 数据可用性约束
ALTER TABLE public.device_running_thresholds
ADD CONSTRAINT chk_data_days_positive
  CHECK (data_days_available IS NULL OR data_days_available >= 0);

COMMIT;

-- =====================================================================
-- 验证脚本
-- =====================================================================

-- 验证所有新字段已创建
DO $$
DECLARE
    v_column_count INTEGER;
    v_expected_count INTEGER := 18;
BEGIN
    SELECT COUNT(*) INTO v_column_count
    FROM information_schema.columns
    WHERE table_schema = 'public'
        AND table_name = 'device_running_thresholds'
        AND column_name IN (
            'device_type', 'device_type_source', 'device_type_auto_detected',
            'running_mode', 'running_time_ratio', 'data_days_available',
            'startup_window_secs_learned', 'shutdown_window_secs_learned',
            'startup_window_secs_effective', 'shutdown_window_secs_effective',
            'startup_inrush_multiplier', 'startup_inrush_duration_secs',
            'use_weighted_fusion', 'signal_weight_current', 'signal_weight_power', 'signal_weight_frequency',
            'threshold_quality', 'last_full_learning_ts'
        );
    
    IF v_column_count = v_expected_count THEN
        RAISE NOTICE '[验证成功] 所有 % 个新字段已创建', v_expected_count;
    ELSE
        RAISE WARNING '[验证失败] 预期 % 个新字段，实际创建 % 个', v_expected_count, v_column_count;
    END IF;
END $$;

-- 验证所有约束已创建
DO $$
DECLARE
    v_constraint_count INTEGER;
    v_expected_count INTEGER := 5;
BEGIN
    SELECT COUNT(*) INTO v_constraint_count
    FROM information_schema.table_constraints
    WHERE table_schema = 'public'
        AND table_name = 'device_running_thresholds'
        AND constraint_name IN (
            'chk_weights_sum',
            'chk_window_positive',
            'chk_inrush_positive',
            'chk_running_ratio_range',
            'chk_data_days_positive'
        );
    
    IF v_constraint_count = v_expected_count THEN
        RAISE NOTICE '[验证成功] 所有 % 个新约束已创建', v_expected_count;
    ELSE
        RAISE WARNING '[验证失败] 预期 % 个新约束，实际创建 % 个', v_expected_count, v_constraint_count;
    END IF;
END $$;

-- 显示表结构
SELECT 
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name = 'device_running_thresholds'
ORDER BY ordinal_position;

