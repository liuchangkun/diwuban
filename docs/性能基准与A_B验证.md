# 性能基准与 A/B 验证

目的：提供统一的性能基线采集、A/B 验证与报告方法，支撑优化迭代与回归评估（以数据库与 scripts/sql 为事实源）。

## 1. 指标与数据源

- 数据源：pg_stat_statements（已启用）
- 关键指标：calls, rows, blk_read_time, blk_write_time, temp_blks_read, temp_blks_written
- 辅助：monitoring.pgss_snapshot（历史快照表）

## 2. 基线采集

- 周期建议：每 30 分钟（由 APScheduler 触发 capture_pgss_snapshot）
- 快速手工：`SELECT monitoring.capture_pgss_snapshot();`
- 数据清理：`SELECT monitoring.cleanup_pgss_snapshot(7);`
- 报告：按关键查询聚合统计，形成阶段性“性能基线”记录

## 3. A/B 验证方法（示例：活跃分区索引）

- 场景：近 7 天活跃分区建立 btree 索引前后，对比查询耗时
- 步骤：
  1. BEFORE：记录 rows_count + duration_ms（monitoring.run_ab_test 的 before）
  1. 执行 `SELECT monitoring.ensure_active_indexes(7);`
  1. AFTER：记录 rows_count + duration_ms（after）
  1. 对比收益并记录到 PLAYBOOKS/性能基准（PERFORMANCE_BENCHMARKS.md）

## 4. 命中率与查询改写

- 视图：monitoring.v_mv_hit_audit（MV vs 事实表的文本命中率评估）
- 目标建议：>60% 的报表/看板查询命中 MV；持续改写查询路径提升命中率

## 5. 报告模板（要点）

- 场景与工作负载描述（时间范围、站点/设备/指标集合）
- 变更项（索引/参数/查询改写）
- 指标对比表（before/after）与结论
- 后续建议与回滚方案
- 参考脚本：scripts/perf_snapshot.sql, scripts/ab_validation.sql, scripts/query_coverage_audit.sql, scripts/mv_hit_audit.sql

## 6. 可选：EXPLAIN/ANALYZE 步骤（更细粒度诊断）

- 在 A/B 两侧分别执行 `EXPLAIN (ANALYZE, BUFFERS)` 记录执行计划、磁盘读写与缓存命中
- 样例：

```
EXPLAIN (ANALYZE, BUFFERS)
SELECT ts_bucket, device_id, metric_id, value
FROM public.fact_measurements
WHERE station_id = 1
  AND ts_bucket BETWEEN '2025-08-16 00:00+00' AND '2025-08-16 03:00+00'
  AND metric_id = ANY(ARRAY[101]);
```

- 报告要点：
  - 计划变更（Seq Scan→Index/Bitmap）
  - Buffers: shared read/write、命中比例
  - Timing：执行时间与节点耗时分布
- 注意：尽量在业务低峰执行；保存计划到报告附件
