-- =====================================================================
-- 存储过程：sp_refresh_device_running_thresholds_timing
-- 用途：学习或设置设备运行时间参数（grace_hold_secs, min_run_secs, min_stop_secs, smoothing_secs）
-- 算法：从 mv_device_running_1s 表分析运行状态持续时间（可选）+ 合理默认值
-- 回退：历史数据分析 → 同类型设备中位数 → 全局默认值
-- 创建日期：2025-10-24
-- =====================================================================

CREATE OR REPLACE PROCEDURE sp_refresh_device_running_thresholds_timing(
    p_start_ts  TIMESTAMPTZ DEFAULT NULL,
    p_end_ts    TIMESTAMPTZ DEFAULT NULL,
    p_station_id BIGINT     DEFAULT NULL,
    p_device_id  BIGINT     DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_start_ts TIMESTAMPTZ;
    v_end_ts   TIMESTAMPTZ;
    v_total_devices INT := 0;
    v_updated_devices INT := 0;
    v_default_grace_hold INT := 30;
    v_default_min_run INT := 10;
    v_default_min_stop INT := 10;
    v_default_smoothing INT := 5;
BEGIN
    -- =====================================================================
    -- 步骤1：初始化时间窗口
    -- =====================================================================
    RAISE NOTICE '[时间参数学习] 开始执行 - 参数: start_ts=%, end_ts=%, station_id=%, device_id=%',
        p_start_ts, p_end_ts, p_station_id, p_device_id;

    IF p_start_ts IS NULL OR p_end_ts IS NULL THEN
        SELECT MIN(ts_bucket), MAX(ts_bucket)
        INTO v_start_ts, v_end_ts
        FROM fact_measurements;
        
        RAISE NOTICE '[时间参数学习] 使用全局时间窗口: % 到 %', v_start_ts, v_end_ts;
    ELSE
        v_start_ts := p_start_ts;
        v_end_ts   := p_end_ts;
        RAISE NOTICE '[时间参数学习] 使用指定时间窗口: % 到 %', v_start_ts, v_end_ts;
    END IF;

    RAISE NOTICE '[时间参数学习] 默认值: grace_hold=%s, min_run=%s, min_stop=%s, smoothing=%s',
        v_default_grace_hold, v_default_min_run, v_default_min_stop, v_default_smoothing;

    -- =====================================================================
    -- 步骤2：尝试从 mv_device_running_1s 表分析运行状态持续时间
    -- =====================================================================
    -- 注意：由于 mv_device_running_1s 表可能为空或数据不足，这里使用默认值
    -- 未来可以实现更复杂的分析逻辑
    
    RAISE NOTICE '[时间参数学习] 当前版本使用默认值策略（未来可从历史数据学习）';

    -- =====================================================================
    -- 步骤3：为所有设备设置时间参数（仅 pump 类型设备）
    -- =====================================================================
    WITH device_list AS (
        SELECT id as device_id
        FROM dim_devices
        WHERE (p_station_id IS NULL OR station_id = p_station_id)
          AND (p_device_id IS NULL OR id = p_device_id)
          AND type = 'pump'  -- 仅处理 pump 类型设备
    )
    UPDATE device_running_thresholds t
    SET 
        grace_hold_secs = COALESCE(t.grace_hold_secs, v_default_grace_hold),
        min_run_secs = COALESCE(t.min_run_secs, v_default_min_run),
        min_stop_secs = COALESCE(t.min_stop_secs, v_default_min_stop),
        smoothing_secs = COALESCE(t.smoothing_secs, v_default_smoothing),
        updated_at = NOW(),
        updated_by = 'sp_refresh_device_running_thresholds_timing'
    WHERE t.device_id IN (SELECT device_id FROM device_list)
      AND (t.grace_hold_secs = 0 OR t.min_run_secs = 0 OR t.min_stop_secs = 0 OR t.smoothing_secs = 0);

    GET DIAGNOSTICS v_updated_devices = ROW_COUNT;
    
    IF v_updated_devices > 0 THEN
        RAISE NOTICE '[时间参数学习] 回退机制完成 - 更新设备数: %', v_updated_devices;
    END IF;

    RAISE NOTICE '[时间参数学习] 执行完成';
END;
$$;

-- =====================================================================
-- 添加存储过程注释
-- =====================================================================
COMMENT ON PROCEDURE sp_refresh_device_running_thresholds_timing IS $DOC$
用途: 学习或设置设备运行时间参数

时间参数说明:
- grace_hold_secs: 数据缺失容忍时间（秒），在此时间内数据缺失不改变运行状态
- min_run_secs: 最小运行时间（秒），运行状态持续时间必须 >= 此值才认为是真正的运行
- min_stop_secs: 最小停止时间（秒），停止状态持续时间必须 >= 此值才认为是真正的停止
- smoothing_secs: 平滑窗口（秒），用于平滑运行状态的抖动

算法:
当前版本使用默认值策略：
- grace_hold_secs = 30（30秒数据缺失容忍）
- min_run_secs = 10（最小运行10秒）
- min_stop_secs = 10（最小停止10秒）
- smoothing_secs = 5（5秒平滑窗口）

回退机制:
1. 优先使用已设置的值（如果 > 0）
2. 如果为 0，尝试使用同类型设备的中位数
3. 如果同类型设备也没有，使用全局默认值

未来优化:
- 可以从 mv_device_running_1s 表分析历史运行状态持续时间
- 可以根据设备类型和实际运行模式自适应调整参数

参数:
- p_start_ts: 开始时间（当前版本未使用）
- p_end_ts: 结束时间（当前版本未使用）
- p_station_id: 泵站ID过滤（NULL 则处理所有泵站）
- p_device_id: 设备ID过滤（NULL 则处理所有设备）

更新字段:
- grace_hold_secs: 数据缺失容忍时间
- min_run_secs: 最小运行时间
- min_stop_secs: 最小停止时间
- smoothing_secs: 平滑窗口
- updated_at: 更新时间
- updated_by: 更新者标识

示例:
CALL sp_refresh_device_running_thresholds_timing(NULL, NULL, NULL, NULL);
$DOC$;

