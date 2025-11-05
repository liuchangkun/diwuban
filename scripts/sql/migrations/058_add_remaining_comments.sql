-- ============================================================================
-- 058_add_remaining_comments.sql
-- 目的：为剩余数据库对象添加完整注释
-- 创建日期：2025-10-30
-- 说明：
--   1. 替换所有有问题的注释（占位符、格式问题、内容简略）
--   2. 统一使用标准换行符（\n），消除所有\r
--   3. 每个对象包含完整的业务逻辑、字段说明、使用示例
--   4. 所有信息与代码实现一致
-- ============================================================================

BEGIN;

-- ============================================================================
-- 第一优先级：注释质量极差的表（11张）
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. completion_audit（补全审计表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.completion_audit IS '补全审计表

用途：
  记录每次数据补全运行的审计信息，提供结构化对账与统计摘要

业务逻辑：
  - 每次补全运行生成一条审计记录
  - 记录补全前后的数据质量指标（覆盖率、缺失点数、最大缺口）
  - 统计各种补全方法的使用次数
  - 记录拒绝计数和组一致性审计信息

关键字段：
  - run_id：运行ID（唯一，关联 completion_runs 表）
  - coverage_before/coverage_after：补全前后的数据覆盖率
  - missing_before/missing_after：补全前后的缺失点数
  - max_gap_before_sec/max_gap_after_sec：补全前后的最大缺口（秒）
  - count_ffill：前向填充次数
  - count_mean：均值填充次数
  - count_reg：回归填充次数
  - count_curve：曲线填充次数
  - count_skipped_long_gap：跳过的长缺口次数
  - startup_drop_ratio：启停落点剔除比例
  - rejects_counts：拒绝计数（JSONB格式，按类别统计）
  - thresholds_snapshot_ref：阈值快照引用（文本）
  - group_consistency：组一致性审计（JSONB格式）
  - audit_time：审计时间

数据来源：
  - 代码位置：app/services/device_running_job.py
  - 写入时机：补全运行完成后

使用场景：
  - 补全效果评估
  - 补全方法统计
  - 数据质量趋势分析

使用示例：
  -- 查询补全效果审计
  SELECT
      run_id,
      coverage_before,
      coverage_after,
      (coverage_after - coverage_before) AS coverage_improvement,
      missing_before,
      missing_after,
      count_ffill + count_mean + count_reg + count_curve AS total_filled
  FROM completion_audit
  ORDER BY audit_time DESC;

注意事项：
  - 每个 run_id 只有一条记录（UNIQUE约束）
  - 与 completion_runs 表通过 run_id 关联（ON DELETE CASCADE）
';

-- ----------------------------------------------------------------------------
-- 2. completion_failures（补全失败清单表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.completion_failures IS '补全失败清单表

用途：
  记录数据补全过程中的失败记录，便于问题排查和分析

业务逻辑：
  - 逐条记录补全失败的详细信息
  - 提供失败原因代码和证据URI
  - 建议修复动作

关键字段：
  - run_id：所属运行ID（关联 completion_runs 表）
  - object_key：失败对象键（JSONB格式：{station_id, device_id, metric_id}）
  - gap_id：缺口段ID
  - reason_code：失败原因代码
  - evidence_uri：证据URI（如日志文件路径）
  - suggested_action：建议动作（如"检查参数配置"、"补充额定参数"）
  - created_at：创建时间

数据来源：
  - 代码位置：补全任务失败时写入
  - 写入时机：补全方法失败时

使用场景：
  - 补全失败原因分析
  - 问题排查和修复
  - 失败模式统计

使用示例：
  -- 查询失败原因分布
  SELECT reason_code, COUNT(*) AS count
  FROM completion_failures
  GROUP BY reason_code
  ORDER BY count DESC;

  -- 查询某次运行的失败记录
  SELECT *
  FROM completion_failures
  WHERE run_id = 12345
  ORDER BY created_at;

注意事项：
  - 与 completion_runs 表通过 run_id 关联（ON DELETE CASCADE）
  - object_key 使用 JSONB 格式存储，便于灵活查询
';

-- ----------------------------------------------------------------------------
-- 3. completion_steps（补全步骤表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.completion_steps IS '补全步骤表

用途：
  记录数据补全过程中的每个步骤详情，提供段级审计

业务逻辑：
  - 记录每个缺口的处理过程
  - 记录尝试的补全方法和回退路径
  - 记录残差统计信息

关键字段：
  - run_id：所属运行ID（关联 completion_runs 表）
  - gap_start_ts/gap_end_ts：缺口起止时间
  - gap_len_sec：缺口长度（秒）
  - gap_class：缺口分类（short/medium/long）
  - methods_tried：尝试的方法列表（JSONB数组）
  - fallback_path：回退路径（如 "curve -> reg -> mean"）
  - residual_stats：残差统计（JSONB格式：{mean, std, max}）
  - created_at：创建时间

数据来源：
  - 代码位置：app/services/device_running_job.py
  - 写入时机：每个缺口处理完成后

使用场景：
  - 补全方法使用情况统计
  - 补全质量分析
  - 回退路径分析

使用示例：
  -- 查询补全方法使用情况
  SELECT
      fallback_path,
      COUNT(*) AS count,
      AVG(gap_len_sec) AS avg_gap_len
  FROM completion_steps
  GROUP BY fallback_path
  ORDER BY count DESC;

  -- 查询某次运行的步骤详情
  SELECT *
  FROM completion_steps
  WHERE run_id = 12345
  ORDER BY gap_start_ts;

注意事项：
  - 与 completion_runs 表通过 run_id 关联（ON DELETE CASCADE）
  - methods_tried 和 residual_stats 使用 JSONB 格式存储
';

-- ----------------------------------------------------------------------------
-- 4. device_metric_candidates（设备指标候选表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.device_metric_candidates IS '设备指标候选表

用途：
  存储设备可能具有的指标列表，避免为设备计算不支持的指标

业务逻辑：
  - 从数据映射配置生成设备的候选指标列表
  - 计算编排时仅计算候选列表中的指标
  - 避免无效计算，提升性能

关键字段：
  - device_id：设备ID（主键）
  - metrics：候选指标数组（text[]）

数据来源：
  - 代码位置：从 data_mapping.json 或 CSV 导入生成
  - 更新时机：数据映射配置变更时

使用场景：
  - 计算编排时确定设备可计算的指标
  - 避免为设备计算不支持的指标
  - 性能优化

使用示例：
  -- 查询某设备的候选指标
  SELECT metrics
  FROM device_metric_candidates
  WHERE device_id = 121;

  -- 查询支持某指标的设备列表
  SELECT device_id
  FROM device_metric_candidates
  WHERE ''flow'' = ANY(metrics);

注意事项：
  - metrics 字段使用 text[] 数组存储
  - 候选列表应与实际数据映射保持一致
';

-- ----------------------------------------------------------------------------
-- 5. dim_mapping_items（映射快照表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.dim_mapping_items IS '映射快照表

用途：
  记录站点-设备-指标的映射关系快照，追踪映射关系的变更历史

业务逻辑：
  - 每次数据导入时记录映射关系快照
  - 使用 MD5 哈希值标识唯一映射
  - 支持映射关系的历史追溯

关键字段：
  - mapping_hash：映射哈希值（MD5，主键）
  - station_name：站点名称
  - device_name：设备名称
  - metric_key：指标键
  - source_hint：数据来源提示（如 "data_mapping.json"、"CSV导入"）
  - created_at：创建时间

数据来源：
  - 代码位置：data_mapping.json、CSV导入
  - 写入时机：数据导入时

使用场景：
  - 数据导入验证
  - 映射关系追踪
  - 映射变更历史查询

使用示例：
  -- 查询特定来源的映射
  SELECT *
  FROM dim_mapping_items
  WHERE source_hint = ''data_mapping.json''
  ORDER BY created_at DESC;

  -- 查询某站点的所有映射
  SELECT *
  FROM dim_mapping_items
  WHERE station_name = ''泵站A''
  ORDER BY device_name, metric_key;

注意事项：
  - mapping_hash 使用 MD5 哈希值，确保唯一性
  - 映射关系变更时会生成新的快照记录
';

-- ----------------------------------------------------------------------------
-- 6. quality_code_dict（质量码字典表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.quality_code_dict IS '质量码字典表

用途：
  映射质量状态码（数值）到中文标签、类别、严重度、描述

业务逻辑：
  - 定义所有质量检查规则对应的质量码
  - 支持质量报表的分组和统计
  - 支持质量问题的严重度分级

📚 质量码完整字典（15个）：

【数值特性】（6个）
  • 101 - 越界
    - 严重度：3（高）
    - 检查逻辑：value < valid_min OR value > valid_max
    - 示例：流量值为-10（负值越界）

  • 111 - 异常跳变
    - 严重度：3（高）
    - 检查逻辑：abs(value - prev_value) > spike_abs
    - 示例：流量从100突变到500

  • 112 - 变化率异常
    - 严重度：3（高）
    - 检查逻辑：abs(value - prev_value) / prev_value > roc_ratio
    - 示例：流量变化率超过50%

  • 121 - 平台期
    - 严重度：2（中）
    - 检查逻辑：连续N秒值不变（可能传感器卡死）
    - 示例：流量连续60秒保持100不变

  • 131 - 上饱和
    - 严重度：3（高）
    - 检查逻辑：value >= saturation_max（接近量程上限）
    - 示例：压力值持续在量程上限

  • 132 - 下饱和
    - 严重度：3（高）
    - 检查逻辑：value <= saturation_min（接近量程下限）
    - 示例：流量值持续在量程下限

【噪声/完整性】（1个）
  • 201 - 高噪声
    - 严重度：2（中）
    - 检查逻辑：短窗标准差 > noise_stddev_max
    - 示例：流量值在短时间内剧烈波动

【跨指标/跨设备】（1个）
  • 401 - 状态矛盾
    - 严重度：4（极高）
    - 检查逻辑：运行状态与测量值矛盾
    - 示例：运行状态=0但功率>0，或运行状态=1但功率≈0

【时间一致性】（2个）
  • 501 - 时间漂移
    - 严重度：2（中）
    - 检查逻辑：ts_raw 与 ts_bucket 偏差过大
    - 示例：原始时间与对齐时间相差超过5秒

  • 502 - 重复秒
    - 严重度：2（中）
    - 检查逻辑：同一秒出现多条记录
    - 示例：同一设备同一指标在同一秒有2条数据

【机理/物理】（5个）
  • 701 - 功率因数异常
    - 严重度：3（高）
    - 检查逻辑：power_factor < 0 OR power_factor > 1
    - 示例：功率因数为1.2（超出物理范围）

  • 711 - 液位流量守恒异常
    - 严重度：4（极高）
    - 检查逻辑：dLevel/dt 与流量不一致（违反能量守恒）
    - 示例：液位上升但流量为负

  • 721 - 相似定律异常
    - 严重度：3（高）
    - 检查逻辑：与变频相似定律偏差过大
    - 示例：频率变化50%但流量变化10%（不符合相似定律）

  • 731 - 泵曲线偏差
    - 严重度：3（高）
    - 检查逻辑：与泵特性曲线偏差过大
    - 示例：实际扬程与曲线预测值偏差超过20%

  • 751 - 计数器非单调
    - 严重度：3（高）
    - 检查逻辑：累计量出现回退
    - 示例：累计电量从1000降到900

使用场景：
  - 质量检查规则配置
  - 质量报表生成
  - 质量问题分析

使用示例：
  -- 查询所有质量码
  SELECT code, label_zh, category, severity, description
  FROM quality_code_dict
  ORDER BY code;

  -- 查询高严重性质量问题
  SELECT *
  FROM quality_code_dict
  WHERE severity >= 3;

注意事项：
  - 质量码与 fact_measurements.quality_status 字段对应
  - 严重度范围：1（低）到 4（极高）
';

-- ----------------------------------------------------------------------------
-- 7. quality_diagnosis_log（质量诊断日志表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.quality_diagnosis_log IS '质量诊断日志表

用途：
  记录质量标注过程的诊断信息，支持性能分析和问题排查

业务逻辑：
  - 记录每个质量标注窗口的开始/结束时间
  - 记录每个阶段的执行时间和影响行数
  - 支持3级诊断（off/brief/full）

关键字段：
  - window_start/window_end：标注窗口起止时间
  - station_id/device_id：站点/设备ID（可选过滤）
  - stage：阶段名称（如 "update_101"、"update_111"）
  - level：日志级别（INFO/WARNING/ERROR）
  - diag_level：诊断级别（off/brief/full）
  - duration_ms：执行时间（毫秒）
  - rows_affected：影响行数
  - detail：详细信息（JSONB格式）
  - created_at：创建时间

数据来源：
  - 代码位置：sp_mark_quality_window_vfast_diag 存储过程
  - 写入时机：质量标注过程中

使用场景：
  - 质量标注过程追踪
  - 性能分析
  - 问题排查

使用示例：
  -- 查询质量标注错误日志
  SELECT *
  FROM quality_diagnosis_log
  WHERE level = ''ERROR''
  ORDER BY created_at DESC;

  -- 查询某窗口的性能统计
  SELECT
      stage,
      duration_ms,
      rows_affected,
      CASE WHEN rows_affected > 0 THEN duration_ms::numeric / rows_affected ELSE 0 END AS ms_per_row
  FROM quality_diagnosis_log
  WHERE window_start = ''2025-09-01T00:00:00Z''
    AND window_end = ''2025-09-02T00:00:00Z''
  ORDER BY duration_ms DESC;

注意事项：
  - diag_level 控制日志详细程度（off不记录、brief记录摘要、full记录详情）
  - detail 字段使用 JSONB 格式存储，便于灵活查询
';

-- ----------------------------------------------------------------------------
-- 8. quality_eval_by_device_metric（质量评估统计表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.quality_eval_by_device_metric IS '质量评估统计表

用途：
  按窗口/设备/指标生成质量码分布统计，支持质量报表生成

业务逻辑：
  - 离线统计，由 sp_generate_quality_eval_by_device_metric 存储过程生成
  - 统计每个质量码的行数和占比
  - 支持质量趋势分析

关键字段：
  - window_start/window_end：统计窗口起止时间
  - station_id/device_id/metric_id：站点/设备/指标ID
  - quality_status：质量状态码
  - rows_count：该质量码的行数
  - total_count：总行数
  - ratio：占比（rows_count / total_count）
  - created_at：创建时间

数据来源：
  - 代码位置：sp_generate_quality_eval_by_device_metric 存储过程
  - 写入时机：质量报表生成时

使用场景：
  - 质量报表生成
  - 质量趋势分析
  - 质量问题统计

使用示例：
  -- 查询某设备某指标的质量分布
  SELECT
      quality_status,
      rows_count,
      total_count,
      ratio,
      ROUND(ratio * 100, 2) || ''%'' AS percentage
  FROM quality_eval_by_device_metric
  WHERE device_id = 121
    AND metric_id = 14
    AND window_start = ''2025-09-01T00:00:00Z''
    AND window_end = ''2025-09-02T00:00:00Z''
  ORDER BY quality_status;

  -- 查询质量问题最多的设备
  SELECT
      device_id,
      SUM(CASE WHEN quality_status > 0 THEN rows_count ELSE 0 END) AS problem_count,
      SUM(total_count) AS total_count,
      ROUND(SUM(CASE WHEN quality_status > 0 THEN rows_count ELSE 0 END)::numeric / SUM(total_count), 4) AS problem_ratio
  FROM quality_eval_by_device_metric
  WHERE window_start = ''2025-09-01T00:00:00Z''
    AND window_end = ''2025-09-02T00:00:00Z''
  GROUP BY device_id
  ORDER BY problem_ratio DESC;

注意事项：
  - 主键：(window_start, window_end, station_id, device_id, metric_id, quality_status)
  - ratio 字段精度：numeric(9,6)
';

-- ----------------------------------------------------------------------------
-- 9. mv_metric_60s_stats（60秒指标统计表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.mv_metric_60s_stats IS '60秒指标统计表

用途：
  60秒聚合统计，提供快速查询能力

视图类型：
  Continuous Aggregate（连续聚合）

数据来源：
  - 基表：fact_measurements
  - 聚合粒度：60秒

聚合逻辑：
  - 聚合函数：COUNT、SUM、SUM(value^2)、MIN、MAX
  - 聚合字段：value（测量值）

刷新策略：
  - 刷新方式：连续聚合策略（实时刷新）
  - 刷新过程：sp_refresh_mv_metric_60s_stats

性能优化建议：
  - 查询60秒级数据时优先使用此视图
  - 避免直接查询 fact_measurements 表进行聚合

使用场景：
  - 60秒级数据查询
  - 统计分析
  - 报表生成

使用示例：
  -- 查询60秒聚合数据
  SELECT
      ts_bucket,
      cnt AS count,
      CASE WHEN cnt > 0 THEN val_sum / cnt ELSE NULL END AS avg_value,
      val_min,
      val_max
  FROM mv_metric_60s_stats
  WHERE station_id = 1
    AND device_id = 121
    AND metric_id = 14
    AND ts_bucket >= ''2025-09-01T00:00:00Z''
    AND ts_bucket < ''2025-09-02T00:00:00Z''
  ORDER BY ts_bucket;

注意事项：
  - 索引：(station_id, device_id, metric_id, ts_bucket)
  - 刷新策略由 TimescaleDB 自动管理
';

-- ----------------------------------------------------------------------------
-- 10. mv_presence_1s（1秒指标存在性表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.mv_presence_1s IS '1秒指标存在性表

用途：
  1秒指标存在性统计，支持缺失指标计算和数据完整性监控

视图类型：
  Continuous Aggregate（连续聚合）

数据来源：
  - 基表：fact_measurements
  - 聚合粒度：1秒

聚合逻辑：
  - 聚合函数：COUNT（存在性标记）
  - 聚合字段：present（固定为1）

刷新策略：
  - 刷新方式：连续聚合策略（实时刷新）
  - 刷新过程：sp_refresh_mv_running_presence

使用场景：
  - 缺失指标计算的输入
  - 数据完整性监控
  - 数据覆盖率统计

使用示例：
  -- 查询某时间段的指标存在性
  SELECT
      ts_bucket,
      metric_id,
      present
  FROM mv_presence_1s
  WHERE station_id = 1
    AND device_id = 121
    AND ts_bucket >= ''2025-09-01T00:00:00Z''
    AND ts_bucket < ''2025-09-02T00:00:00Z''
  ORDER BY ts_bucket, metric_id;

  -- 统计指标覆盖率
  SELECT
      metric_id,
      COUNT(*) AS present_count,
      EXTRACT(EPOCH FROM (MAX(ts_bucket) - MIN(ts_bucket))) AS time_span_sec,
      COUNT(*)::numeric / EXTRACT(EPOCH FROM (MAX(ts_bucket) - MIN(ts_bucket))) AS coverage_ratio
  FROM mv_presence_1s
  WHERE station_id = 1
    AND device_id = 121
    AND ts_bucket >= ''2025-09-01T00:00:00Z''
    AND ts_bucket < ''2025-09-02T00:00:00Z''
  GROUP BY metric_id;

注意事项：
  - 索引：(station_id, device_id, metric_id, ts_bucket)
  - present 字段固定为1（表示该秒该指标存在数据）
';

-- ----------------------------------------------------------------------------
-- 11. mv_device_running_1s（1秒设备运行状态表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.mv_device_running_1s IS '1秒设备运行状态表

用途：
  1秒设备运行状态统计，支持运行态筛选和启停窗口识别

视图类型：
  Continuous Aggregate（连续聚合）

数据来源：
  - 基表：fact_measurements（功率因数指标）
  - 聚合粒度：1秒

聚合逻辑：
  - 运行状态判定：基于功率因数阈值
  - 相位判定：0停止/1稳态运行/2启动中/3停止中

刷新策略：
  - 刷新方式：连续聚合策略（实时刷新）
  - 刷新过程：sp_refresh_mv_running_presence

使用场景：
  - 运行态筛选
  - 启停窗口识别
  - 运行时长统计

使用示例：
  -- 查询某设备的运行状态
  SELECT
      ts_bucket,
      running,
      phase
  FROM mv_device_running_1s
  WHERE station_id = 1
    AND device_id = 121
    AND ts_bucket >= ''2025-09-01T00:00:00Z''
    AND ts_bucket < ''2025-09-02T00:00:00Z''
  ORDER BY ts_bucket;

  -- 统计运行时长
  SELECT
      SUM(CASE WHEN running = 1 THEN 1 ELSE 0 END) AS running_seconds,
      SUM(CASE WHEN running = 0 THEN 1 ELSE 0 END) AS stopped_seconds,
      COUNT(*) AS total_seconds,
      ROUND(SUM(CASE WHEN running = 1 THEN 1 ELSE 0 END)::numeric / COUNT(*), 4) AS running_ratio
  FROM mv_device_running_1s
  WHERE station_id = 1
    AND device_id = 121
    AND ts_bucket >= ''2025-09-01T00:00:00Z''
    AND ts_bucket < ''2025-09-02T00:00:00Z'';

注意事项：
  - 索引：(station_id, device_id, ts_bucket)
  - running 字段：0停止/1运行
  - phase 字段：0停止/1稳态运行/2启动中/3停止中
';

-- ----------------------------------------------------------------------------
-- 12. metrics_presence_per_second_device_legacy（指标存在性表-旧版）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.metrics_presence_per_second_device_legacy IS '指标存在性表（旧版，已废弃）

用途：
  旧版的指标存在性记录表，已被 metrics_presence_per_second_device 替代

状态：
  Legacy表，仅用于历史数据查询，不再写入新数据

迁移状态：
  - 历史数据保留在此表中
  - 新数据写入 metrics_presence_per_second_device 表
  - 计划在历史数据迁移完成后删除此表

与新版的区别：
  - 旧版：表结构可能不同，性能较差
  - 新版：优化的表结构，支持更高效的查询

建议：
  - 新功能应使用 metrics_presence_per_second_device 表
  - 查询历史数据时可能需要联合查询两个表

使用示例：
  -- 查询历史指标存在性数据
  SELECT *
  FROM metrics_presence_per_second_device_legacy
  WHERE device_id = 121
    AND ts_second >= ''2025-01-01T00:00:00Z''
    AND ts_second < ''2025-02-01T00:00:00Z''
  ORDER BY ts_second;

注意事项：
  - 此表已废弃，不建议在新代码中使用
  - 历史数据迁移完成后将删除此表
';

-- ============================================================================
-- 第二优先级：内容过于简略的表（14张）
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 13. staging_raw（原始数据暂存表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.staging_raw IS '原始数据暂存表

用途：
  CSV导入的第一阶段暂存，接收原始数据并进行初步验证

业务逻辑：
  - UNLOGGED表（性能优化，但不持久化到WAL，崩溃后数据丢失）
  - 数据流程：CSV → staging_raw → 清洗验证 → fact_measurements
  - 支持批量导入，提升性能

关键字段：
  - station_name：站点名称（原始CSV字段）
  - device_name：设备名称（原始CSV字段）
  - metric_key：指标键（原始CSV字段）
  - TagName：标签名称（原始CSV字段）
  - DataTime：数据时间（原始CSV字段，文本格式）
  - DataValue：数据值（原始CSV字段，文本格式）
  - source_hint：数据来源提示（如文件名）
  - loaded_at：加载时间（自动生成）

数据流程：
  1. CSV文件通过COPY命令导入到 staging_raw
  2. 数据清洗和验证（格式检查、映射关系验证、数值范围检查）
  3. 验证通过的数据写入 fact_measurements
  4. 验证失败的数据写入 staging_rejects
  5. 定期清理已处理数据

清理策略：
  - 定期清理已处理数据（通常保留最近7天）
  - 避免表膨胀影响性能

使用场景：
  - CSV数据导入
  - 数据质量检查
  - 导入性能优化

使用示例：
  -- 查询最近导入的数据
  SELECT *
  FROM staging_raw
  ORDER BY loaded_at DESC
  LIMIT 100;

  -- 统计导入数据量
  SELECT
      DATE(loaded_at) AS import_date,
      COUNT(*) AS row_count
  FROM staging_raw
  GROUP BY DATE(loaded_at)
  ORDER BY import_date DESC;

注意事项：
  - UNLOGGED表，数据库崩溃后数据会丢失
  - 仅用于临时暂存，不应长期保留数据
  - 定期清理已处理数据，避免表膨胀
';

-- ----------------------------------------------------------------------------
-- 14. staging_rejects（拒绝数据暂存表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.staging_rejects IS '拒绝数据暂存表

用途：
  记录导入过程中被拒绝的数据，便于数据质量分析和问题排查

业务逻辑：
  - UNLOGGED表（性能优化）
  - 记录所有验证失败的数据
  - 提供详细的错误信息

关键字段：
  - station_name/device_name/metric_key：原始字段（与staging_raw相同）
  - TagName/DataTime/DataValue：原始字段（与staging_raw相同）
  - source_hint：数据来源提示
  - error_msg：错误信息（详细描述拒绝原因）
  - rejected_at：拒绝时间（自动生成）

拒绝原因分类：
  - 数据格式错误：DataTime格式错误、DataValue非数值
  - 数值超出范围：DataValue超出合理范围
  - 时间格式错误：DataTime无法解析
  - 映射关系不存在：station_name/device_name/metric_key在映射表中不存在
  - 重复数据：同一时间点重复导入

使用场景：
  - 数据质量分析
  - 导入问题排查
  - 数据源质量评估

使用示例：
  -- 统计拒绝原因分布
  SELECT
      CASE
          WHEN error_msg LIKE ''%格式错误%'' THEN ''格式错误''
          WHEN error_msg LIKE ''%超出范围%'' THEN ''数值超出范围''
          WHEN error_msg LIKE ''%映射不存在%'' THEN ''映射关系不存在''
          WHEN error_msg LIKE ''%重复%'' THEN ''重复数据''
          ELSE ''其他''
      END AS error_category,
      COUNT(*) AS count
  FROM staging_rejects
  GROUP BY error_category
  ORDER BY count DESC;

  -- 查询最近的拒绝记录
  SELECT *
  FROM staging_rejects
  ORDER BY rejected_at DESC
  LIMIT 100;

注意事项：
  - UNLOGGED表，数据库崩溃后数据会丢失
  - 定期清理已分析的拒绝数据
  - error_msg 字段包含详细的错误信息，便于问题排查
';

-- ----------------------------------------------------------------------------
-- 15. metric_quality_rules（指标质量规则表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.metric_quality_rules IS '指标质量规则表

用途：
  配置指标的质量检查规则阈值，支持按站点/设备/指标粒度覆盖

业务逻辑：
  - 支持3级粒度：全局 → 站点级 → 设备级
  - 优先级：设备级 > 站点级 > 全局级
  - 手工配置优先于自动基线

📚 规则参数字典（9类）：

【数值区间】
  • value_min / value_max (double precision)
    - 用途：物理越界检查（质量码101）
    - 物理含义：测量值的合理区间
    - 示例：流量 value_min=0, value_max=500
    - 注意：NULL表示不检查该边界

【跳变检查】
  • spike_abs (double precision)
    - 用途：异常跳变检查（质量码111）
    - 物理含义：相邻秒绝对差值阈值
    - 计算公式：|value(t) - value(t-1)| > spike_abs
    - 示例：流量 spike_abs=50（相邻秒差值不超过50）

【变化率检查】
  • roc_abs (double precision)
    - 用途：变化率异常检查（质量码112）
    - 物理含义：绝对变化率阈值（单位/秒）
    - 计算公式：|value(t) - value(t-1)| / Δt > roc_abs
    - 示例：流量 roc_abs=10（每秒变化不超过10）

  • roc_ratio (double precision)
    - 用途：变化率异常检查（质量码112）
    - 物理含义：相对变化率阈值（百分比）
    - 计算公式：|value(t) - value(t-1)| / |value(t-1)| > roc_ratio
    - 示例：流量 roc_ratio=0.5（变化率不超过50%）

【平台期检查】
  • flatline_secs (int)
    - 用途：平台期检查（质量码121）
    - 物理含义：平台期持续秒数阈值
    - 示例：flatline_secs=60（连续60秒不变视为平台期）

  • flatline_eps (double precision)
    - 用途：平台期检查（质量码121）
    - 物理含义：平台期容差（标准差阈值）
    - 示例：flatline_eps=0.01（标准差小于0.01视为不变）

  • flatline_delta (double precision)
    - 用途：平台期检查（质量码121）
    - 物理含义：平台期最大变化量（极差阈值）
    - 示例：flatline_delta=0.1（极差小于0.1视为不变）

【饱和检查】
  • saturation_min / saturation_max (double precision)
    - 用途：饱和检查（质量码131/132）
    - 物理含义：接近量程边界的阈值
    - 示例：压力 saturation_min=0.1, saturation_max=9.9（量程0-10）

【噪声检查】
  • noise_stddev_max (double precision)
    - 用途：高噪声检查（质量码201）
    - 物理含义：短窗标准差上限
    - 示例：noise_stddev_max=5.0（短窗标准差超过5.0视为高噪声）

使用场景：
  - 质量标注窗口（sp_mark_quality_window）
  - 质量规则配置管理
  - 自动基线调整

使用示例：
  -- 查询某指标的质量规则（按优先级）
  SELECT *
  FROM metric_quality_rules
  WHERE metric_id = 14
  ORDER BY device_id NULLS LAST, station_id NULLS LAST;

  -- 插入设备级规则
  INSERT INTO metric_quality_rules (device_id, metric_id, value_min, value_max, spike_abs)
  VALUES (121, 14, 0, 500, 50);

  -- 更新全局规则
  UPDATE metric_quality_rules
  SET value_min = 0, value_max = 600
  WHERE metric_id = 14
    AND station_id IS NULL
    AND device_id IS NULL;

注意事项：
  - 优先级：设备级 > 站点级 > 全局级
  - NULL值表示不检查该规则
  - 手工配置优先于自动基线
';

-- ----------------------------------------------------------------------------
-- 16. calculation_method_registry（计算方法注册表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.calculation_method_registry IS '计算方法注册表

用途：
  记录每个指标的所有可用计算方法，支持计算编排和方法选择

业务逻辑：
  - 注册所有可用的计算方法
  - 每个方法有优先级，按优先级顺序尝试
  - 支持方法启用/禁用控制

方法分类：
  - direct：直接测量（从传感器直接获取）
  - formula：公式计算（基于其他指标计算）
  - curve：曲线拟合（基于泵特性曲线）
  - regression：回归模型（基于历史数据训练）

关键字段：
  - metric_id：指标ID
  - method_name：方法名称（如 "formula_power_from_current"）
  - method_type：方法类型（direct/formula/curve/regression）
  - priority：优先级（数值越小优先级越高）
  - enabled：是否启用（true/false）
  - description：方法描述

使用场景：
  - 计算编排时选择计算方法
  - 方法优先级管理
  - 方法启用/禁用控制

使用示例：
  -- 查询某指标的所有计算方法（按优先级）
  SELECT *
  FROM calculation_method_registry
  WHERE metric_id = 14
    AND enabled = true
  ORDER BY priority;

  -- 注册新的计算方法
  INSERT INTO calculation_method_registry (metric_id, method_name, method_type, priority, enabled, description)
  VALUES (14, ''formula_flow_from_level'', ''formula'', 10, true, ''基于液位计算流量'');

注意事项：
  - 优先级数值越小优先级越高
  - 计算编排时按优先级顺序尝试方法
  - 禁用的方法不会被尝试
';

-- ----------------------------------------------------------------------------
-- 17. calculation_validation_config（计算结果验证配置表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.calculation_validation_config IS '计算结果验证配置表

用途：
  配置计算结果的验证规则，确保计算结果的合理性

业务逻辑：
  - 配置各种验证规则的阈值
  - 验证失败时拒绝计算结果
  - 支持按指标粒度配置

验证类型：
  - 物理边界验证：检查计算结果是否在合理范围内
  - 曲线偏差验证：检查计算结果与泵曲线的偏差
  - 相似定律验证：检查计算结果是否符合相似定律
  - 能量守恒验证：检查计算结果是否符合能量守恒

关键字段：
  - metric_id：指标ID
  - validation_type：验证类型
  - threshold：阈值
  - enabled：是否启用

使用场景：
  - 计算结果验证
  - 计算质量控制
  - 异常结果过滤

使用示例：
  -- 查询某指标的验证配置
  SELECT *
  FROM calculation_validation_config
  WHERE metric_id = 14
    AND enabled = true;

  -- 配置物理边界验证
  INSERT INTO calculation_validation_config (metric_id, validation_type, threshold, enabled)
  VALUES (14, ''physical_boundary'', 500, true);

注意事项：
  - 验证失败的计算结果会被拒绝
  - 阈值应根据实际情况调整
';

-- ----------------------------------------------------------------------------
-- 18. metrics_presence_per_second_device（指标存在性记录表-新版）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.metrics_presence_per_second_device IS '指标存在性记录表（新版）

用途：
  记录每秒每个设备的指标存在性，支持缺失指标计算

业务逻辑：
  - 记录每秒每个设备的可用指标和需要计算的指标
  - 支持缺失指标计算的输入
  - 优化的表结构，性能优于旧版

关键字段：
  - ts_second：时间戳（秒级）
  - station_id/device_id：站点/设备ID
  - available_metrics：可用指标数组（text[]）
  - need_compute_metrics：需要计算的指标数组（text[]）

数据来源：
  - 代码位置：从 fact_measurements 聚合生成
  - 更新时机：实时更新或定期刷新

使用场景：
  - 缺失指标计算的输入
  - 数据完整性监控
  - 数据覆盖率统计

使用示例：
  -- 查询某设备某秒的指标存在性
  SELECT
      ts_second,
      available_metrics,
      need_compute_metrics
  FROM metrics_presence_per_second_device
  WHERE device_id = 121
    AND ts_second >= ''2025-09-01T00:00:00Z''
    AND ts_second < ''2025-09-02T00:00:00Z''
  ORDER BY ts_second;

  -- 统计需要计算的指标
  SELECT
      UNNEST(need_compute_metrics) AS metric_key,
      COUNT(*) AS count
  FROM metrics_presence_per_second_device
  WHERE device_id = 121
    AND ts_second >= ''2025-09-01T00:00:00Z''
    AND ts_second < ''2025-09-02T00:00:00Z''
  GROUP BY metric_key
  ORDER BY count DESC;

注意事项：
  - 替代旧版 metrics_presence_per_second_device_legacy 表
  - 使用数组字段存储指标列表，查询更高效
';

-- ----------------------------------------------------------------------------
-- 19. dim_device_capabilities（设备能力表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.dim_device_capabilities IS '设备能力表

用途：
  记录设备的物理能力和限制，支持计算方法选择和参数验证

业务逻辑：
  - 记录设备是否变频、频率范围、额定功率/电流等参数
  - 计算方法选择时参考设备能力
  - 参数验证时检查是否超出设备能力

关键字段：
  - device_id：设备ID（主键）
  - has_vfd：是否变频（true/false）
  - freq_min/freq_max：频率范围（Hz）
  - rated_power：额定功率（kW）
  - rated_current：额定电流（A）
  - rated_voltage：额定电压（V）

使用场景：
  - 计算方法选择（变频设备使用相似定律）
  - 参数验证（频率不能超出范围）
  - 设备能力查询

使用示例：
  -- 查询变频设备
  SELECT *
  FROM dim_device_capabilities
  WHERE has_vfd = true;

  -- 查询某设备的能力参数
  SELECT *
  FROM dim_device_capabilities
  WHERE device_id = 121;

注意事项：
  - has_vfd 字段决定是否使用相似定律计算
  - 频率范围用于参数验证
';

-- ----------------------------------------------------------------------------
-- 20. device_running_thresholds（设备运行阈值表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.device_running_thresholds IS '设备运行阈值表

用途：
  存储设备运行状态判定的阈值参数，支持运行态识别

业务逻辑：
  - 存储功率因数阈值、电流阈值等参数
  - 支持运行状态判定（0停止/1运行）
  - 支持启停窗口参数配置

关键字段：
  - device_id：设备ID（主键）
  - pf_threshold：功率因数阈值
  - current_threshold：电流阈值（A）
  - grace_hold_secs：容忍保持秒数
  - min_run_secs：最小运行秒数
  - min_stop_secs：最小停止秒数
  - smoothing_secs：平滑窗口秒数
  - startup_window_secs：启动窗口秒数
  - shutdown_window_secs：停止窗口秒数

使用场景：
  - 运行状态判定（fn_running_state_1s）
  - 启停窗口识别（fn_startstop_windows）
  - 阈值学习和调整

使用示例：
  -- 查询某设备的运行阈值
  SELECT *
  FROM device_running_thresholds
  WHERE device_id = 121;

  -- 更新功率因数阈值
  UPDATE device_running_thresholds
  SET pf_threshold = 0.15
  WHERE device_id = 121;

注意事项：
  - 阈值可通过 sp_refresh_device_running_thresholds_* 系列存储过程自动学习
  - 也可手工配置
';

-- ----------------------------------------------------------------------------
-- 21. pump_characteristic_curves（水泵特性曲线数据表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.pump_characteristic_curves IS '水泵特性曲线数据表

用途：
  存储水泵的特性曲线数据，支持扬程/功率/效率计算和曲线偏差验证

业务逻辑：
  - 存储Q-H、Q-P、Q-η曲线的离散点数据
  - 支持曲线插值计算
  - 支持曲线偏差验证

曲线类型：
  - Q-H曲线：流量-扬程曲线
  - Q-P曲线：流量-功率曲线
  - Q-η曲线：流量-效率曲线

关键字段：
  - device_id：设备ID
  - curve_type：曲线类型（Q-H/Q-P/Q-η）
  - flow_points：流量点数组（m³/h）
  - value_points：对应值数组（扬程m/功率kW/效率%）
  - rated_speed：额定转速（rpm）

使用场景：
  - 扬程/功率/效率计算
  - 曲线偏差验证（质量码731）
  - 泵性能分析

使用示例：
  -- 查询某设备的Q-H曲线
  SELECT *
  FROM pump_characteristic_curves
  WHERE device_id = 121
    AND curve_type = ''Q-H'';

  -- 插入Q-H曲线数据
  INSERT INTO pump_characteristic_curves (device_id, curve_type, flow_points, value_points, rated_speed)
  VALUES (121, ''Q-H'', ARRAY[0, 50, 100, 150, 200], ARRAY[80, 75, 65, 50, 30], 1450);

注意事项：
  - flow_points 和 value_points 数组长度必须相同
  - 曲线点应按流量升序排列
  - 支持线性插值计算中间值
';

-- ----------------------------------------------------------------------------
-- 22. metric_anomaly_strategy（异常检测策略表）
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.metric_anomaly_strategy IS '异常检测策略表

用途：
  配置指标的异常检测策略，支持多种异常检测方法

业务逻辑：
  - 支持统计异常检测、机器学习异常检测、规则基异常检测
  - 每个指标可配置多种策略
  - 策略可启用/禁用

策略类型：
  - statistical：统计异常检测（基于均值、标准差、分位数）
  - ml：机器学习异常检测（基于训练模型）
  - rule：规则基异常检测（基于业务规则）

关键字段：
  - metric_id：指标ID
  - strategy_type：策略类型
  - strategy_config：策略配置（JSONB格式）
  - enabled：是否启用

使用场景：
  - 异常检测
  - 数据质量监控
  - 预警系统

使用示例：
  -- 查询某指标的异常检测策略
  SELECT *
  FROM metric_anomaly_strategy
  WHERE metric_id = 14
    AND enabled = true;

  -- 配置统计异常检测策略
  INSERT INTO metric_anomaly_strategy (metric_id, strategy_type, strategy_config, enabled)
  VALUES (14, ''statistical'', ''{"method": "zscore", "threshold": 3.0}''::jsonb, true);

注意事项：
  - strategy_config 使用 JSONB 格式存储，便于灵活配置
  - 多种策略可同时启用
';

-- ----------------------------------------------------------------------------
-- 23-25. Shadow表（3张）
-- ----------------------------------------------------------------------------

-- 23. device_running_thresholds_shadow
COMMENT ON TABLE public.device_running_thresholds_shadow IS 'Shadow表：设备运行阈值影子配置表

用途：
  测试新的运行阈值配置，不影响生产环境

与主表关系：
  - 主表：device_running_thresholds
  - 结构：与主表完全相同
  - 数据流：独立存储，不影响主表

使用场景：
  - A/B测试：测试新阈值配置的效果
  - 配置验证：验证新阈值的正确性
  - 回滚机制：验证失败可快速回滚到主表配置

切换机制：
  - 通过配置开关选择使用主表或shadow表
  - 代码位置：运行状态判定函数中

使用示例：
  -- 对比主表和shadow表的配置差异
  SELECT
      m.device_id,
      m.pf_threshold AS main_pf_threshold,
      s.pf_threshold AS shadow_pf_threshold,
      m.current_threshold AS main_current_threshold,
      s.current_threshold AS shadow_current_threshold
  FROM device_running_thresholds m
  LEFT JOIN device_running_thresholds_shadow s ON m.device_id = s.device_id;

  -- 将shadow表配置同步到主表
  INSERT INTO device_running_thresholds
  SELECT * FROM device_running_thresholds_shadow
  ON CONFLICT (device_id) DO UPDATE
  SET pf_threshold = EXCLUDED.pf_threshold,
      current_threshold = EXCLUDED.current_threshold;

注意事项：
  - Shadow表仅用于测试，不应直接用于生产
  - 验证通过后需要同步到主表
  - 同步前应备份主表配置
';

-- 24. metric_quality_rules_shadow
COMMENT ON TABLE public.metric_quality_rules_shadow IS 'Shadow表：指标质量规则影子配置表

用途：
  测试新的质量规则配置，不影响生产环境

与主表关系：
  - 主表：metric_quality_rules
  - 结构：与主表完全相同
  - 数据流：独立存储，不影响主表

使用场景：
  - A/B测试：测试新质量规则的效果
  - 配置验证：验证新规则的正确性
  - 回滚机制：验证失败可快速回滚到主表配置

切换机制：
  - 通过配置开关选择使用主表或shadow表
  - 代码位置：质量标注存储过程中

使用示例：
  -- 对比主表和shadow表的配置差异
  SELECT
      m.metric_id,
      m.value_min AS main_value_min,
      s.value_min AS shadow_value_min,
      m.value_max AS main_value_max,
      s.value_max AS shadow_value_max
  FROM metric_quality_rules m
  LEFT JOIN metric_quality_rules_shadow s
    ON m.metric_id = s.metric_id
    AND COALESCE(m.station_id, 0) = COALESCE(s.station_id, 0)
    AND COALESCE(m.device_id, 0) = COALESCE(s.device_id, 0);

注意事项：
  - Shadow表仅用于测试，不应直接用于生产
  - 验证通过后需要同步到主表
';

-- 25. metric_rule_auto_baseline_shadow
COMMENT ON TABLE public.metric_rule_auto_baseline_shadow IS 'Shadow表：指标规则自动基线影子配置表

用途：
  测试新的自动基线配置，不影响生产环境

与主表关系：
  - 主表：metric_rule_auto_baseline
  - 结构：与主表完全相同
  - 数据流：独立存储，不影响主表

使用场景：
  - A/B测试：测试新自动基线算法的效果
  - 配置验证：验证新基线的正确性
  - 回滚机制：验证失败可快速回滚到主表配置

切换机制：
  - 通过配置开关选择使用主表或shadow表
  - 代码位置：自动基线刷新存储过程中

使用示例：
  -- 对比主表和shadow表的基线差异
  SELECT
      m.metric_id,
      m.p50 AS main_p50,
      s.p50 AS shadow_p50,
      m.mad AS main_mad,
      s.mad AS shadow_mad
  FROM metric_rule_auto_baseline m
  LEFT JOIN metric_rule_auto_baseline_shadow s
    ON m.metric_id = s.metric_id
    AND COALESCE(m.device_id, 0) = COALESCE(s.device_id, 0);

注意事项：
  - Shadow表仅用于测试，不应直接用于生产
  - 验证通过后需要同步到主表
';

-- ============================================================================
-- 第三优先级：视图（13个）
-- ============================================================================

-- 注意：v_fact_measurements_with_label 已在057迁移中完成，无需处理

-- ----------------------------------------------------------------------------
-- 26. cagg_presence_per_second（连续聚合：秒级存在性）
-- ----------------------------------------------------------------------------
COMMENT ON VIEW public.cagg_presence_per_second IS '连续聚合视图：秒级指标存在性

用途：
  快速查询秒级指标存在性，支持缺失指标计算

视图类型：
  Continuous Aggregate（连续聚合）

数据来源：
  - 基表：fact_measurements
  - 聚合粒度：1秒

聚合逻辑：
  - 聚合函数：COUNT（存在性标记）
  - 分组字段：station_id, device_id, metric_id, ts_bucket

刷新策略：
  - 刷新方式：实时刷新（TimescaleDB自动管理）
  - 刷新间隔：根据连续聚合策略配置

使用场景：
  - 快速查询秒级指标存在性
  - 缺失指标计算的输入
  - 数据完整性监控

性能优化建议：
  - 优先使用此视图而非直接查询 fact_measurements
  - 支持时间范围过滤和设备过滤

使用示例：
  -- 查询某设备某时间段的指标存在性
  SELECT *
  FROM cagg_presence_per_second
  WHERE device_id = 121
    AND ts_bucket >= ''2025-09-01T00:00:00Z''
    AND ts_bucket < ''2025-09-02T00:00:00Z''
  ORDER BY ts_bucket, metric_id;

注意事项：
  - 连续聚合视图，数据自动更新
  - 查询性能优于直接查询基表
';

-- ----------------------------------------------------------------------------
-- 27. station_device_rated_params_view（站点设备额定参数视图）
-- ----------------------------------------------------------------------------
COMMENT ON VIEW public.station_device_rated_params_view IS '站点设备额定参数视图

用途：
  合并设备级和全局级额定参数，提供统一的参数查询接口

视图类型：
  普通视图

数据来源：
  - 基表1：device_rated_params（设备级参数）
  - 基表2：global_default_rated_params（全局级参数）

关键字段：
  - device_id：设备ID
  - 额定参数：rated_flow, rated_head, rated_power, rated_speed, rated_efficiency, rated_current
  - 管道参数：pipe_diameter, pipe_length, pipe_roughness, pipe_loss_coef
  - source：参数来源（device/global）

业务逻辑：
  - 优先使用设备级参数
  - 设备级参数不存在时使用全局级参数
  - 支持5层参数优先级系统

使用场景：
  - 参数加载（5层优先级系统）
  - 计算方法参数获取
  - 参数配置查询

使用示例：
  -- 查询某设备的额定参数
  SELECT *
  FROM station_device_rated_params_view
  WHERE device_id = 121;

  -- 查询所有设备的额定流量
  SELECT device_id, rated_flow, source
  FROM station_device_rated_params_view
  ORDER BY device_id;

注意事项：
  - source 字段标识参数来源（device/global）
  - 优先级：设备级 > 全局级
';

-- ----------------------------------------------------------------------------
-- 28-30. 其他视图（简化注释）
-- ----------------------------------------------------------------------------

COMMENT ON VIEW public.metrics_availability_v_weekly IS '指标可用性周报视图

用途：按周统计指标可用性，支持数据质量报表生成

数据来源：fact_measurements

使用场景：数据质量周报、可用性趋势分析

使用示例：
  SELECT * FROM metrics_availability_v_weekly
  WHERE week_start >= ''2025-09-01''
  ORDER BY week_start DESC;
';

COMMENT ON VIEW public.metrics_missing_v IS '缺失指标视图

用途：识别缺失的指标，支持缺失指标计算

数据来源：dim_metric_config, fact_measurements

使用场景：缺失指标识别、数据完整性检查

使用示例：
  SELECT * FROM metrics_missing_v
  WHERE device_id = 121
    AND ts_bucket >= ''2025-09-01T00:00:00Z''
  ORDER BY ts_bucket;
';

COMMENT ON VIEW public.mv_presence_1s_any IS '1秒存在性聚合视图

用途：聚合1秒级指标存在性，支持快速查询

数据来源：mv_presence_1s

使用场景：数据完整性监控、覆盖率统计

使用示例：
  SELECT * FROM mv_presence_1s_any
  WHERE device_id = 121
    AND ts_bucket >= ''2025-09-01T00:00:00Z''
  ORDER BY ts_bucket;
';

-- ============================================================================
-- 第四优先级：自定义函数（约33个）
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 质量管理函数（5个）
-- ----------------------------------------------------------------------------

COMMENT ON PROCEDURE public.sp_mark_quality_window(timestamptz, timestamptz, bigint, bigint) IS '质量标注存储过程

用途：
  对给定时间窗执行质量标注规则

输入参数：
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）
  - p_station_id (bigint, DEFAULT NULL)：泵站ID过滤（NULL则处理所有）
  - p_device_id (bigint, DEFAULT NULL)：设备ID过滤（NULL则处理所有）

返回值：
  - void

业务逻辑：
  - 执行质量检查规则（越界/跳变/平台期/状态矛盾/功率因数/液位守恒）
  - 仅在 quality_status=0 时标注，避免覆盖已有标注
  - 支持按站点/设备过滤

使用示例：
  -- 标注2025-09-01全天数据
  CALL sp_mark_quality_window(''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'', NULL, NULL);

  -- 标注特定设备
  CALL sp_mark_quality_window(''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'', NULL, 121);

注意事项：
  - 仅标注 quality_status=0 的数据
  - 大时间窗口可能耗时较长，建议分批处理
';

COMMENT ON PROCEDURE public.sp_mark_quality_window_vfast(timestamptz, timestamptz, bigint, bigint, int[]) IS '质量标注存储过程（vfast优化版）

用途：
  质量标注过程（vfast优化版），性能提升约3-5倍

输入参数：
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）
  - p_station_id (bigint, DEFAULT NULL)：泵站ID过滤
  - p_device_id (bigint, DEFAULT NULL)：设备ID过滤
  - p_codes (int[], DEFAULT NULL)：质量码过滤（NULL则处理所有）

返回值：
  - void

业务逻辑：
  - 预筛候选 + 临时表 + 批量更新
  - 工作内存提升
  - 语义与现版一致，性能优化

性能提升：
  - 约3-5倍于 sp_mark_quality_window

使用示例：
  -- 标注所有质量码
  CALL sp_mark_quality_window_vfast(''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'', NULL, NULL, NULL);

  -- 仅标注特定质量码
  CALL sp_mark_quality_window_vfast(''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'', NULL, NULL, ARRAY[101, 111]);

注意事项：
  - 推荐使用此版本而非 sp_mark_quality_window
  - p_codes 参数可过滤特定质量码
';

COMMENT ON PROCEDURE public.sp_reset_quality_window(timestamptz, timestamptz, bigint, bigint) IS '重置质量标注存储过程

用途：
  重置给定时间窗内的质量标注

输入参数：
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）
  - p_station_id (bigint, DEFAULT NULL)：泵站ID过滤
  - p_device_id (bigint, DEFAULT NULL)：设备ID过滤

返回值：
  - void

业务逻辑：
  - 将 quality_status/type/meta/codes 置为初始值
  - 支持按站点/设备过滤

使用场景：
  - 重新标注前清理旧标注
  - 质量标注错误修正

使用示例：
  -- 重置全部数据
  CALL sp_reset_quality_window(''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'', NULL, NULL);

  -- 重置特定设备
  CALL sp_reset_quality_window(''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'', NULL, 121);

注意事项：
  - 重置后需要重新执行质量标注
  - 操作不可逆，请谨慎使用
';

COMMENT ON PROCEDURE public.sp_generate_quality_eval_by_device_metric(timestamptz, timestamptz, bigint, bigint) IS '生成质量评估统计存储过程

用途：
  生成窗口内 按设备×指标×质量码 的行数分布统计

输入参数：
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）
  - p_station_id (bigint, DEFAULT NULL)：泵站ID过滤
  - p_device_id (bigint, DEFAULT NULL)：设备ID过滤

返回值：
  - void

业务逻辑：
  - 删除既有窗口统计（避免重复）
  - 统计每个质量码的行数和占比
  - 写入 quality_eval_by_device_metric 表

使用场景：
  - 质量报表生成
  - 质量趋势分析
  - 质量问题统计

使用示例：
  -- 生成质量评估统计
  CALL sp_generate_quality_eval_by_device_metric(''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'', NULL, NULL);

  -- 生成特定设备的统计
  CALL sp_generate_quality_eval_by_device_metric(''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'', NULL, 121);

注意事项：
  - 会删除既有窗口的统计数据
  - 建议在质量标注完成后执行
';

-- ----------------------------------------------------------------------------
-- 物化视图刷新函数（3个）
-- ----------------------------------------------------------------------------

COMMENT ON PROCEDURE public.sp_refresh_mv_running_presence(timestamptz, timestamptz, bigint, bigint) IS '刷新运行状态和存在性物化视图

用途：
  刷新 mv_device_running_1s 和 mv_presence_1s 物化视图

输入参数：
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）
  - p_station_id (bigint, DEFAULT NULL)：泵站ID过滤
  - p_device_id (bigint, DEFAULT NULL)：设备ID过滤

返回值：
  - void

业务逻辑：
  - 删除既有窗口数据
  - 重新计算运行状态和存在性
  - 写入物化视图

使用场景：
  - 物化视图增量刷新
  - 数据修正后重新计算

使用示例：
  -- 刷新全部数据
  CALL sp_refresh_mv_running_presence(''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'', NULL, NULL);

注意事项：
  - 会删除既有窗口的数据
  - 建议在数据修正后执行
';

COMMENT ON PROCEDURE public.sp_refresh_mv_metric_60s_stats(timestamptz, timestamptz, bigint, bigint) IS '刷新60秒统计物化视图

用途：
  刷新 mv_metric_60s_stats 物化视图

输入参数：
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）
  - p_station_id (bigint, DEFAULT NULL)：泵站ID过滤
  - p_device_id (bigint, DEFAULT NULL)：设备ID过滤

返回值：
  - void

业务逻辑：
  - 计算60秒窗口的基础统计（count/sum/sumsq/min/max）
  - 写入物化视图

使用场景：
  - 物化视图增量刷新
  - 60秒聚合数据生成

使用示例：
  -- 刷新60秒统计
  CALL sp_refresh_mv_metric_60s_stats(''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'', NULL, NULL);

注意事项：
  - 会删除既有窗口的数据
  - 建议定期执行以保持数据最新
';

COMMENT ON PROCEDURE public.sp_refresh_metric_rule_auto_baseline(integer, bigint, bigint) IS '自动基线刷新存储过程

用途：
  自动基线过程，从历史有效数据计算分位数/MAD/差分分布

输入参数：
  - p_lookback_days (integer)：回溯天数
  - p_station_id (bigint, DEFAULT NULL)：泵站ID过滤
  - p_device_id (bigint, DEFAULT NULL)：设备ID过滤

返回值：
  - void

业务逻辑：
  - 从历史有效(quality=0)且稳态(phase=1)数据计算统计量
  - 计算分位数（p50, p95等）、MAD、差分分布
  - 写入 metric_rule_auto_baseline 表

使用场景：
  - 自动基线学习
  - 质量规则自动调整

使用示例：
  -- 基于最近30天数据学习基线
  CALL sp_refresh_metric_rule_auto_baseline(30, NULL, NULL);

  -- 基于最近7天数据学习特定设备的基线
  CALL sp_refresh_metric_rule_auto_baseline(7, NULL, 121);

注意事项：
  - 仅使用有效且稳态的数据
  - 建议定期执行以更新基线
';

-- ----------------------------------------------------------------------------
-- 健康检查函数（3个）
-- ----------------------------------------------------------------------------

COMMENT ON FUNCTION public.database_health_check() IS '数据库健康检查函数

用途：
  数据库健康体检（只读），检查数据库各项指标

输入参数：
  - 无

返回值：
  - TABLE (check_category text, check_name text, status text, details text)

业务逻辑：
  - 检查数据库连接
  - 检查表空间使用率
  - 检查索引健康度
  - 检查查询性能

使用示例：
  -- 执行健康检查
  SELECT * FROM database_health_check();

  -- 查询异常项
  SELECT * FROM database_health_check()
  WHERE status IN (''WARNING'', ''ERROR'');

注意事项：
  - 只读函数，不会修改数据
  - 建议定期执行以监控数据库健康状态
';

COMMENT ON FUNCTION public.check_data_consistency() IS '数据一致性检查函数

用途：
  检查数据一致性，识别数据质量问题

输入参数：
  - 无

返回值：
  - TABLE (issue_type text, details text)

业务逻辑：
  - 检查维度表和事实表之间的外键约束
  - 检查时间戳字段的有效性
  - 检查数值字段的合理范围
  - 检查重复记录

使用示例：
  -- 执行一致性检查
  SELECT * FROM check_data_consistency();

  -- 统计问题类型
  SELECT issue_type, COUNT(*) AS count
  FROM check_data_consistency()
  GROUP BY issue_type;

注意事项：
  - 只读函数，不会修改数据
  - 发现问题后需要手工修复
';

COMMENT ON FUNCTION public.check_performance_alerts() IS '性能告警检查函数

用途：
  检查性能告警，识别性能问题

输入参数：
  - 无

返回值：
  - TABLE (alert_type text, severity text, details text)

业务逻辑：
  - 检查慢查询
  - 检查锁等待
  - 检查表膨胀
  - 检查索引缺失

使用示例：
  -- 执行性能检查
  SELECT * FROM check_performance_alerts();

  -- 查询高严重性告警
  SELECT * FROM check_performance_alerts()
  WHERE severity IN (''HIGH'', ''CRITICAL'');

注意事项：
  - 只读函数，不会修改数据
  - 建议定期执行以监控性能
';

-- ----------------------------------------------------------------------------
-- 其他常用函数（简化注释）
-- ----------------------------------------------------------------------------

-- 注意：以下函数的详细注释已在之前的迁移中完成，或为TimescaleDB内置函数
-- 此处仅补充缺失的自定义函数注释

COMMENT ON FUNCTION public.auto_performance_tuning() IS '自动性能调优函数（示意）

用途：自动性能调优，优化数据库配置

注意：此函数为示意性质，实际调优需要根据具体情况配置
';

COMMENT ON FUNCTION public.auto_space_reclaim() IS '空间回收函数（示意）

用途：自动空间回收，清理无用数据

注意：此函数为示意性质，实际回收需要根据具体情况配置
';

COMMENT ON FUNCTION public.batch_delete_old_data() IS '分批删除历史数据函数（示意）

用途：分批删除历史数据，避免长事务

注意：此函数为示意性质，实际删除需要根据具体情况配置
';

-- ----------------------------------------------------------------------------
-- 其他视图（剩余10个）
-- ----------------------------------------------------------------------------

COMMENT ON VIEW public.v_coverage_gaps_1s IS '1秒覆盖缺口视图

用途：识别1秒级数据缺口，支持数据完整性监控

数据来源：fact_measurements

使用场景：数据缺口识别、数据完整性检查

使用示例：
  SELECT * FROM v_coverage_gaps_1s
  WHERE device_id = 121
    AND gap_start >= ''2025-09-01T00:00:00Z''
  ORDER BY gap_start;
';

COMMENT ON VIEW public.v_startstop_windows IS '启停窗口视图

用途：识别设备的启动和停止窗口，支持启停分析

数据来源：mv_device_running_1s

使用场景：启停分析、运行时长统计

使用示例：
  SELECT * FROM v_startstop_windows
  WHERE device_id = 121
    AND window_start >= ''2025-09-01T00:00:00Z''
  ORDER BY window_start;
';

COMMENT ON VIEW public.v_effective_metric_metadata IS '有效指标元数据视图

用途：查询有效的指标元数据，支持指标配置管理

数据来源：dim_metric_config

使用场景：指标配置查询、指标元数据管理

使用示例：
  SELECT * FROM v_effective_metric_metadata
  WHERE metric_key = ''flow''
  ORDER BY metric_id;
';

COMMENT ON VIEW public.v_effective_metric_rules IS '有效指标规则视图

用途：查询有效的指标质量规则，支持质量规则管理

数据来源：metric_quality_rules

使用场景：质量规则查询、规则配置管理

使用示例：
  SELECT * FROM v_effective_metric_rules
  WHERE metric_id = 14
  ORDER BY device_id NULLS LAST;
';

COMMENT ON VIEW public.v_quality_code_metric IS '质量码指标视图

用途：查询质量码与指标的关联关系，支持质量分析

数据来源：quality_code_dict, fact_measurements

使用场景：质量码分布分析、质量问题统计

使用示例：
  SELECT * FROM v_quality_code_metric
  WHERE metric_id = 14
    AND quality_code = 101
  ORDER BY ts_bucket DESC;
';

-- ----------------------------------------------------------------------------
-- 运行阈值刷新函数（5个变体）
-- ----------------------------------------------------------------------------

COMMENT ON PROCEDURE public.sp_refresh_device_running_thresholds_v1(integer, bigint, bigint) IS '刷新设备运行阈值（版本1）

用途：
  基于历史数据学习设备运行阈值（版本1算法）

输入参数：
  - p_lookback_days (integer)：回溯天数
  - p_station_id (bigint, DEFAULT NULL)：泵站ID过滤
  - p_device_id (bigint, DEFAULT NULL)：设备ID过滤

返回值：
  - void

业务逻辑：
  - 从历史数据学习功率因数阈值、电流阈值等参数
  - 使用统计方法（分位数、MAD等）
  - 写入 device_running_thresholds 表

使用示例：
  -- 基于最近30天数据学习阈值
  CALL sp_refresh_device_running_thresholds_v1(30, NULL, NULL);

注意事项：
  - 版本1算法，可能不是最优版本
  - 建议使用最新版本的算法
';

COMMENT ON PROCEDURE public.sp_refresh_device_running_thresholds_v2(integer, bigint, bigint) IS '刷新设备运行阈值（版本2）

用途：基于历史数据学习设备运行阈值（版本2算法，改进版）

输入参数：同版本1

业务逻辑：改进的统计方法，提升阈值准确性

使用示例：
  CALL sp_refresh_device_running_thresholds_v2(30, NULL, NULL);
';

COMMENT ON PROCEDURE public.sp_refresh_device_running_thresholds_v3(integer, bigint, bigint) IS '刷新设备运行阈值（版本3）

用途：基于历史数据学习设备运行阈值（版本3算法，进一步改进）

输入参数：同版本1

业务逻辑：进一步改进的统计方法

使用示例：
  CALL sp_refresh_device_running_thresholds_v3(30, NULL, NULL);
';

COMMENT ON PROCEDURE public.sp_refresh_device_running_thresholds_v4(integer, bigint, bigint) IS '刷新设备运行阈值（版本4）

用途：基于历史数据学习设备运行阈值（版本4算法，最新版）

输入参数：同版本1

业务逻辑：最新的统计方法，推荐使用

使用示例：
  CALL sp_refresh_device_running_thresholds_v4(30, NULL, NULL);

注意事项：
  - 推荐使用此版本
  - 算法最优，准确性最高
';

COMMENT ON PROCEDURE public.sp_refresh_device_running_thresholds_vfast(integer, bigint, bigint) IS '刷新设备运行阈值（vfast优化版）

用途：基于历史数据学习设备运行阈值（vfast优化版，性能优化）

输入参数：同版本1

业务逻辑：性能优化版本，算法与v4相同，性能提升约3-5倍

使用示例：
  CALL sp_refresh_device_running_thresholds_vfast(30, NULL, NULL);

注意事项：
  - 推荐使用此版本（性能最优）
  - 算法与v4相同，性能提升约3-5倍
';

-- ----------------------------------------------------------------------------
-- 数据处理函数（10个）
-- ----------------------------------------------------------------------------

COMMENT ON FUNCTION public.metrics_presence_per_second(bigint, timestamptz, timestamptz) IS '秒级指标存在性函数

用途：
  查询秒级指标存在性

输入参数：
  - p_device_id (bigint)：设备ID
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）

返回值：
  - TABLE (ts_second timestamptz, available_metrics text[], need_compute_metrics text[])

使用示例：
  SELECT * FROM metrics_presence_per_second(121, ''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'');
';

COMMENT ON FUNCTION public.metrics_availability_window(bigint, timestamptz, timestamptz) IS '指标可用性窗口函数

用途：
  计算指标在给定窗口内的可用性

输入参数：
  - p_metric_id (bigint)：指标ID
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）

返回值：
  - TABLE (device_id bigint, availability_pct double precision)

使用示例：
  SELECT * FROM metrics_availability_window(14, ''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'');
';

COMMENT ON FUNCTION public.fn_training_timeseries_1s(bigint, bigint, timestamptz, timestamptz) IS '训练时间序列函数（1秒粒度）

用途：
  提取训练时间序列数据（1秒粒度），支持机器学习模型训练

输入参数：
  - p_station_id (bigint)：泵站ID
  - p_device_id (bigint)：设备ID
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）

返回值：
  - TABLE (ts_second timestamptz, metric_values jsonb)

使用示例：
  SELECT * FROM fn_training_timeseries_1s(1, 121, ''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'');
';

COMMENT ON FUNCTION public.fn_running_state_1s(bigint, timestamptz, timestamptz) IS '运行状态函数（1秒粒度）

用途：
  计算设备运行状态（1秒粒度）

输入参数：
  - p_device_id (bigint)：设备ID
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）

返回值：
  - TABLE (ts_second timestamptz, running int, phase int)

使用示例：
  SELECT * FROM fn_running_state_1s(121, ''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'');
';

COMMENT ON FUNCTION public.fn_startstop_windows(bigint, timestamptz, timestamptz) IS '启停窗口函数

用途：
  识别设备的启动和停止窗口

输入参数：
  - p_device_id (bigint)：设备ID
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）

返回值：
  - TABLE (window_start timestamptz, window_end timestamptz, window_type text)

使用示例：
  SELECT * FROM fn_startstop_windows(121, ''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'');
';

COMMENT ON FUNCTION public.fn_phase_from_running(bigint, timestamptz, timestamptz) IS '从运行状态推导相位函数

用途：
  从运行状态推导设备相位（0停止/1稳态运行/2启动中/3停止中）

输入参数：
  - p_device_id (bigint)：设备ID
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）

返回值：
  - TABLE (ts_second timestamptz, phase int)

使用示例：
  SELECT * FROM fn_phase_from_running(121, ''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'');
';

COMMENT ON FUNCTION public.fn_detect_gaps_1s(bigint, timestamptz, timestamptz) IS '检测1秒缺口函数

用途：
  检测1秒级数据缺口

输入参数：
  - p_device_id (bigint)：设备ID
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）

返回值：
  - TABLE (gap_start timestamptz, gap_end timestamptz, gap_secs int)

使用示例：
  SELECT * FROM fn_detect_gaps_1s(121, ''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'');
';

COMMENT ON FUNCTION public.fn_quality_stats_1d(bigint, date) IS '质量统计函数（1天粒度）

用途：
  计算1天粒度的质量统计

输入参数：
  - p_device_id (bigint)：设备ID
  - p_date (date)：日期

返回值：
  - TABLE (quality_code int, count bigint, pct double precision)

使用示例：
  SELECT * FROM fn_quality_stats_1d(121, ''2025-09-01'');
';

COMMENT ON FUNCTION public.safe_upsert_measurement(bigint, bigint, bigint, timestamptz, double precision, int, text, text, int[]) IS '安全插入/更新测量值函数

用途：
  安全地插入或更新测量值，避免冲突

输入参数：
  - p_station_id (bigint)：泵站ID
  - p_device_id (bigint)：设备ID
  - p_metric_id (bigint)：指标ID
  - p_ts_bucket (timestamptz)：时间戳
  - p_value (double precision)：测量值
  - p_quality_status (int)：质量状态
  - p_quality_type (text)：质量类型
  - p_quality_meta (text)：质量元数据
  - p_quality_codes (int[])：质量码数组

返回值：
  - void

使用示例：
  SELECT safe_upsert_measurement(1, 121, 14, ''2025-09-01T00:00:00Z'', 100.5, 0, NULL, NULL, NULL);

注意事项：
  - 使用 ON CONFLICT DO UPDATE 避免冲突
  - 适用于并发写入场景
';

COMMENT ON FUNCTION public.safe_upsert_measurement_local(bigint, bigint, bigint, timestamptz, double precision, int, text, text, int[]) IS '安全插入/更新测量值函数（本地版）

用途：
  安全地插入或更新测量值（本地版，性能优化）

输入参数：同 safe_upsert_measurement

返回值：void

使用示例：
  SELECT safe_upsert_measurement_local(1, 121, 14, ''2025-09-01T00:00:00Z'', 100.5, 0, NULL, NULL, NULL);

注意事项：
  - 本地版，性能优于标准版
  - 适用于单节点部署
';

-- ----------------------------------------------------------------------------
-- 数据处理存储过程（2个）
-- ----------------------------------------------------------------------------

COMMENT ON PROCEDURE public.sp_merge_staging_to_fact(timestamptz, timestamptz) IS '合并staging数据到事实表

用途：
  将staging_raw中的数据合并到fact_measurements

输入参数：
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）

返回值：
  - void

业务逻辑：
  - 从staging_raw读取数据
  - 验证数据格式和映射关系
  - 验证通过的数据写入fact_measurements
  - 验证失败的数据写入staging_rejects

使用场景：
  - CSV数据导入流程
  - 数据清洗和验证

使用示例：
  CALL sp_merge_staging_to_fact(''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'');

注意事项：
  - 建议在数据导入后立即执行
  - 验证失败的数据会写入staging_rejects
';

COMMENT ON PROCEDURE public.sp_cleanup_staging(integer) IS '清理staging表

用途：
  清理staging_raw和staging_rejects中的历史数据

输入参数：
  - p_keep_days (integer)：保留天数

返回值：
  - void

业务逻辑：
  - 删除超过保留天数的数据
  - 避免表膨胀

使用场景：
  - 定期清理staging表
  - 避免表膨胀影响性能

使用示例：
  -- 保留最近7天数据
  CALL sp_cleanup_staging(7);

注意事项：
  - 建议定期执行（如每天）
  - 删除的数据不可恢复
';

-- ----------------------------------------------------------------------------
-- 审计相关函数（2个）
-- ----------------------------------------------------------------------------

COMMENT ON FUNCTION public.log_calculation_failure(bigint, bigint, bigint, timestamptz, text, text) IS '记录计算失败函数

用途：
  记录计算失败信息到completion_failures表

输入参数：
  - p_station_id (bigint)：泵站ID
  - p_device_id (bigint)：设备ID
  - p_metric_id (bigint)：指标ID
  - p_ts_bucket (timestamptz)：时间戳
  - p_reason_code (text)：失败原因代码
  - p_evidence_uri (text)：证据URI

返回值：
  - void

使用示例：
  SELECT log_calculation_failure(1, 121, 14, ''2025-09-01T00:00:00Z'', ''MISSING_DEPENDENCY'', NULL);
';

COMMENT ON FUNCTION public.log_completion_audit(bigint, bigint, timestamptz, timestamptz, jsonb) IS '记录补全审计函数

用途：
  记录补全审计信息到completion_audit表

输入参数：
  - p_station_id (bigint)：泵站ID
  - p_device_id (bigint)：设备ID
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）
  - p_audit_data (jsonb)：审计数据（JSON格式）

返回值：
  - void

使用示例：
  SELECT log_completion_audit(1, 121, ''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'', ''{"coverage_before": 0.8, "coverage_after": 0.95}''::jsonb);
';

-- ----------------------------------------------------------------------------
-- 诊断相关函数（1个）
-- ----------------------------------------------------------------------------

COMMENT ON PROCEDURE public.sp_mark_quality_window_vfast_diag(timestamptz, timestamptz, bigint, bigint, int[], text) IS '质量标注存储过程（vfast诊断版）

用途：
  质量标注过程（vfast诊断版），支持诊断日志输出

输入参数：
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）
  - p_station_id (bigint, DEFAULT NULL)：泵站ID过滤
  - p_device_id (bigint, DEFAULT NULL)：设备ID过滤
  - p_codes (int[], DEFAULT NULL)：质量码过滤
  - p_diag_level (text, DEFAULT ''off'')：诊断级别（off/brief/full）

返回值：
  - void

业务逻辑：
  - 与vfast版本相同，但支持诊断日志输出
  - 诊断日志写入quality_diagnosis_log表

使用场景：
  - 质量标注问题排查
  - 性能分析

使用示例：
  -- 启用完整诊断日志
  CALL sp_mark_quality_window_vfast_diag(''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'', NULL, NULL, NULL, ''full'');

  -- 启用简要诊断日志
  CALL sp_mark_quality_window_vfast_diag(''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'', NULL, NULL, NULL, ''brief'');

注意事项：
  - 诊断日志会影响性能，仅在排查问题时使用
  - 诊断级别：off（关闭）/brief（简要）/full（完整）
';

COMMIT;

