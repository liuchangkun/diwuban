BEGIN;

-- 启用 timescaledb 扩展（如已存在则忽略）
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 将 fact_measurements 转换为 hypertable（时间列 ts_bucket，空间分区 device_id）
-- 注意：唯一约束包含 (station_id, device_id, metric_id, ts_bucket)，已覆盖时间与空间分区列，满足要求
SELECT
  create_hypertable(
    relation => 'public.fact_measurements',
    time_column_name => 'ts_bucket',
    partitioning_column => 'device_id',
    number_partitions => 8,
    create_default_indexes => false,
    if_not_exists => true,
    chunk_time_interval => INTERVAL '1 day'
  );

COMMIT;

