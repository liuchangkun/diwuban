# SCHEMA_AND_DB（表结构与数据库）

## 1. 选型建议
- 默认 PostgreSQL + TimescaleDB；也可 ClickHouse/DuckDB 视场景替换。

## 2. 表与键（建议）
- stations(id, name, meta)
- devices(id, station_id, name, type, pump_type, meta)
- metrics(id, name, unit, kind)
- raw_timeseries(device_id, metric_id, ts_utc, ts_local, value, src_file, src_row, ingest_at)
- aligned_timeseries(station_id, device_id, metric_id, ts_utc, ts_local, value, grid, version)
- derived_timeseries(station_id, device_id, metric_id, ts_utc, ts_local, value, formula, version)
- model_fits(scope, scope_id, model_type, input_metrics, hyperparams, train_range, valid_range, fit_artifacts, created_at)
- fit_curves(scope, scope_id, curve_type, x_name, y_name, equation, params, goodness, constraints, version)
- optimization_results(scope, scope_id, objective, constraints, method, result, created_at)

唯一键：raw_timeseries (device_id, metric_id, ts_utc) UPSERT。

## 3. 版本化与溯源
- 对齐/派生/拟合结果携带 version；参数变化 version+1。
- 所有表包含 run_id/ingest_at 供追溯。

## 4. 性能与索引
- 时序列索引：ts_utc；分区/压缩按站或设备划分。
- 批量写入、连接池、重试与幂等。

## 5. 安全
- 连接字符串来自环境变量；禁止提交真实密钥。
