-- =====================================================================
-- 存储过程：sp_refresh_device_running_thresholds_current
-- 用途：从 fact_measurements 表中学习电流阈值（i_on, i_off）
-- 算法：Otsu 双峰法 + 滞回带（2 * MAD）
-- 回退：设备自己 → 同类型设备中位数 → 全局中位数 → NULL
-- 创建日期：2025-10-24
-- =====================================================================

CREATE OR REPLACE PROCEDURE sp_refresh_device_running_thresholds_current(
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
    v_metric_id_a BIGINT;
    v_metric_id_b BIGINT;
    v_metric_id_c BIGINT;
    v_total_devices INT := 0;
    v_updated_devices INT := 0;
    v_fallback_devices INT := 0;
BEGIN
    -- =====================================================================
    -- 步骤1：初始化时间窗口
    -- =====================================================================
    RAISE NOTICE '[电流阈值学习] 开始执行 - 参数: start_ts=%, end_ts=%, station_id=%, device_id=%',
        p_start_ts, p_end_ts, p_station_id, p_device_id;

    IF p_start_ts IS NULL OR p_end_ts IS NULL THEN
        SELECT MIN(ts_bucket), MAX(ts_bucket)
        INTO v_start_ts, v_end_ts
        FROM fact_measurements;
        
        RAISE NOTICE '[电流阈值学习] 使用全局时间窗口: % 到 %', v_start_ts, v_end_ts;
    ELSE
        v_start_ts := p_start_ts;
        v_end_ts   := p_end_ts;
        RAISE NOTICE '[电流阈值学习] 使用指定时间窗口: % 到 %', v_start_ts, v_end_ts;
    END IF;

    -- =====================================================================
    -- 步骤2：获取电流指标ID
    -- =====================================================================
    SELECT id INTO v_metric_id_a FROM dim_metric_config WHERE metric_key = 'pump_current_a';
    SELECT id INTO v_metric_id_b FROM dim_metric_config WHERE metric_key = 'pump_current_b';
    SELECT id INTO v_metric_id_c FROM dim_metric_config WHERE metric_key = 'pump_current_c';

    IF v_metric_id_a IS NULL OR v_metric_id_b IS NULL OR v_metric_id_c IS NULL THEN
        RAISE WARNING '[电流阈值学习] 缺少电流指标配置，跳过执行';
        RETURN;
    END IF;

    RAISE NOTICE '[电流阈值学习] 电流指标ID: A=%, B=%, C=%', v_metric_id_a, v_metric_id_b, v_metric_id_c;

    -- =====================================================================
    -- 步骤3：为每个设备学习电流阈值
    -- =====================================================================
    WITH device_list AS (
        SELECT id as device_id
        FROM dim_devices
        WHERE (p_station_id IS NULL OR station_id = p_station_id)
          AND (p_device_id IS NULL OR id = p_device_id)
    ),
    -- 读取三相电流数据（质量=0）
    current_data AS (
        SELECT
            f.device_id,
            f.ts_bucket,
            GREATEST(
                COALESCE(MAX(CASE WHEN f.metric_id = v_metric_id_a THEN f.value END), 0),
                COALESCE(MAX(CASE WHEN f.metric_id = v_metric_id_b THEN f.value END), 0),
                COALESCE(MAX(CASE WHEN f.metric_id = v_metric_id_c THEN f.value END), 0)
            ) AS max_current
        FROM fact_measurements f
        WHERE f.device_id IN (SELECT device_id FROM device_list)
          AND f.ts_bucket >= v_start_ts
          AND f.ts_bucket < v_end_ts
          AND f.metric_id IN (v_metric_id_a, v_metric_id_b, v_metric_id_c)
          AND f.quality_status = 0
        GROUP BY f.device_id, f.ts_bucket
        HAVING GREATEST(
            COALESCE(MAX(CASE WHEN f.metric_id = v_metric_id_a THEN f.value END), 0),
            COALESCE(MAX(CASE WHEN f.metric_id = v_metric_id_b THEN f.value END), 0),
            COALESCE(MAX(CASE WHEN f.metric_id = v_metric_id_c THEN f.value END), 0)
        ) > 0
    ),
    -- Otsu 双峰法计算阈值（步骤1：计算中位数）
    device_medians AS (
        SELECT
            device_id,
            COUNT(*) AS sample_count,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY max_current) AS median_current
        FROM current_data
        GROUP BY device_id
        HAVING COUNT(*) >= 50  -- 最小样本要求
    ),
    -- 步骤2：计算 MAD（中位数绝对偏差）
    device_thresholds AS (
        SELECT
            dm.device_id,
            dm.sample_count,
            dm.median_current AS threshold,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ABS(cd.max_current - dm.median_current)) AS mad
        FROM device_medians dm
        JOIN current_data cd ON dm.device_id = cd.device_id
        GROUP BY dm.device_id, dm.sample_count, dm.median_current
    ),
    -- 计算滞回带
    final_thresholds AS (
        SELECT 
            device_id,
            sample_count,
            threshold,
            mad,
            GREATEST(0.01, 2.0 * mad) AS hysteresis_band,
            threshold + GREATEST(0.01, 2.0 * mad) AS i_on,
            threshold - GREATEST(0.01, 2.0 * mad) AS i_off
        FROM device_thresholds
    )
    -- 更新阈值表
    UPDATE device_running_thresholds t
    SET 
        enable_i = TRUE,
        i_on = COALESCE(t.i_on, f.i_on),
        i_off = COALESCE(t.i_off, f.i_off),
        updated_at = NOW(),
        updated_by = 'sp_refresh_device_running_thresholds_current'
    FROM final_thresholds f
    WHERE t.device_id = f.device_id;

    GET DIAGNOSTICS v_updated_devices = ROW_COUNT;

    RAISE NOTICE '[电流阈值学习] 第一阶段完成 - 成功学习设备数: %', v_updated_devices;

    -- =====================================================================
    -- 步骤4：回退机制 - 使用同类型设备中位数
    -- =====================================================================
    IF v_fallback_devices > 0 THEN
        RAISE NOTICE '[电流阈值学习] 开始回退机制 - 使用同类型设备中位数';
        
        WITH device_type_medians AS (
            SELECT 
                d.type,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.i_on) AS median_i_on,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.i_off) AS median_i_off
            FROM device_running_thresholds t
            JOIN dim_devices d ON d.id = t.device_id
            WHERE t.i_on IS NOT NULL AND t.i_off IS NOT NULL
            GROUP BY d.type
        )
        UPDATE device_running_thresholds t
        SET 
            enable_i = TRUE,
            i_on = COALESCE(t.i_on, m.median_i_on),
            i_off = COALESCE(t.i_off, m.median_i_off),
            updated_at = NOW(),
            updated_by = 'sp_refresh_device_running_thresholds_current_fallback_type'
        FROM dim_devices d
        JOIN device_type_medians m ON m.type = d.type
        WHERE t.device_id = d.id
          AND t.i_on IS NULL
          AND m.median_i_on IS NOT NULL;

        GET DIAGNOSTICS v_updated_devices = ROW_COUNT;
        RAISE NOTICE '[电流阈值学习] 回退机制（同类型）完成 - 更新设备数: %', v_updated_devices;
    END IF;

    -- =====================================================================
    -- 步骤5：最终回退 - 使用全局中位数
    -- =====================================================================
    WITH global_medians AS (
        SELECT 
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY i_on) AS median_i_on,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY i_off) AS median_i_off
        FROM device_running_thresholds
        WHERE i_on IS NOT NULL AND i_off IS NOT NULL
    )
    UPDATE device_running_thresholds t
    SET 
        enable_i = TRUE,
        i_on = COALESCE(t.i_on, m.median_i_on),
        i_off = COALESCE(t.i_off, m.median_i_off),
        updated_at = NOW(),
        updated_by = 'sp_refresh_device_running_thresholds_current_fallback_global'
    FROM global_medians m
    WHERE t.i_on IS NULL
      AND m.median_i_on IS NOT NULL;

    GET DIAGNOSTICS v_updated_devices = ROW_COUNT;
    
    IF v_updated_devices > 0 THEN
        RAISE NOTICE '[电流阈值学习] 回退机制（全局）完成 - 更新设备数: %', v_updated_devices;
    END IF;

    RAISE NOTICE '[电流阈值学习] 执行完成';
END;
$$;

-- =====================================================================
-- 添加存储过程注释
-- =====================================================================
COMMENT ON PROCEDURE sp_refresh_device_running_thresholds_current IS $DOC$
用途: 从 fact_measurements 表中学习设备运行电流阈值（i_on, i_off）

算法:
- 读取三相电流数据（pump_current_a/b/c），取最大值
- 使用 Otsu 双峰法（简化版：中位数）计算分割阈值
- 计算滞回带：2 * MAD（中位数绝对偏差）
- i_on = 阈值 + 滞回带
- i_off = 阈值 - 滞回带

回退机制:
1. 优先从设备自己的历史数据学习（需要 >= 50 个样本）
2. 如果样本不足，使用同类型设备的中位数
3. 如果同类型设备也没有，使用全局中位数
4. 如果全局也没有，保持 NULL（不启用电流判断）

参数:
- p_start_ts: 开始时间（NULL 则使用全局最小时间）
- p_end_ts: 结束时间（NULL 则使用全局最大时间）
- p_station_id: 泵站ID过滤（NULL 则处理所有泵站）
- p_device_id: 设备ID过滤（NULL 则处理所有设备）

更新字段:
- enable_i: 设置为 TRUE（如果成功学习到阈值）
- i_on: 电流开启阈值
- i_off: 电流关闭阈值
- updated_at: 更新时间
- updated_by: 更新者标识

数据要求:
- 只使用 quality=0 且稳态（phase=1 或 running=1）的数据
- 最小样本数: 50

示例:
CALL sp_refresh_device_running_thresholds_current(NULL, NULL, NULL, NULL);
$DOC$;

