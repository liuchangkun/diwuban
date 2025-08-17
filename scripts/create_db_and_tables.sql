-- Create core schema for PostgreSQL 16 (no TimescaleDB)
-- Database name to create separately: diwuban

SET client_min_messages = WARNING;

BEGIN;

-- 1) Stations
CREATE TABLE IF NOT EXISTS public.dim_stations (
  id          BIGSERIAL PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,
  extra       JSONB,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- 2) Devices (including main pipeline as a device)
CREATE TABLE IF NOT EXISTS public.dim_devices (
  id          BIGSERIAL PRIMARY KEY,
  station_id  BIGINT NOT NULL REFERENCES public.dim_stations(id),
  name        TEXT NOT NULL,
  type        TEXT NOT NULL,   -- 'pump' | 'main_pipeline'
  pump_type   TEXT,            -- 'variable_frequency' | 'soft_start' | NULL when type='main_pipeline'
  extra       JSONB,
  created_at  TIMESTAMPTZ DEFAULT now(),
  UNIQUE(station_id, name),
  CONSTRAINT chk_device_type
    CHECK (type IN ('pump','main_pipeline')),
  CONSTRAINT chk_pump_type_when_pump
    CHECK (
      (type = 'pump' AND (pump_type IS NULL OR pump_type IN ('variable_frequency','soft_start')))
      OR
      (type = 'main_pipeline' AND pump_type IS NULL)
    )
);

-- 3) Metric config (one row per metric key from data_mapping.json)
CREATE TABLE IF NOT EXISTS public.dim_metric_config (
  id               BIGSERIAL PRIMARY KEY,
  metric_key       TEXT UNIQUE NOT NULL,  -- e.g., frequency, voltage_b, pressure, flow_rate, kwh
  unit             TEXT NOT NULL,         -- literal from mapping, e.g., Hz, KW/H, Mpa, M3/h
  unit_display     TEXT,
  decimals_policy  TEXT DEFAULT 'as_is',  -- 'as_is' or 'fixed'
  fixed_decimals   SMALLINT,
  value_type       TEXT,
  valid_min        NUMERIC,
  valid_max        NUMERIC,
  created_at       TIMESTAMPTZ DEFAULT now(),
  updated_at       TIMESTAMPTZ DEFAULT now()
);

-- 4) Mapping snapshot items (optional helper for mapping versions)
CREATE TABLE IF NOT EXISTS public.dim_mapping_items (
  id            BIGSERIAL PRIMARY KEY,
  mapping_hash  TEXT NOT NULL,
  station_name  TEXT NOT NULL,
  device_name   TEXT NOT NULL,
  metric_key    TEXT NOT NULL REFERENCES public.dim_metric_config(metric_key),
  source_hint   TEXT NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- 5) Fact table (time-series, second-bucket aligned)
-- Partitioned by RANGE on ts_bucket (weekly); sub-partitions by HASH(station_id) to be created separately when needed
CREATE TABLE IF NOT EXISTS public.fact_measurements (
  id          BIGSERIAL PRIMARY KEY,
  station_id  BIGINT NOT NULL REFERENCES public.dim_stations(id),
  device_id   BIGINT NOT NULL REFERENCES public.dim_devices(id),
  metric_id   BIGINT NOT NULL REFERENCES public.dim_metric_config(id),
  ts_raw      TIMESTAMPTZ NOT NULL,
  ts_bucket   TIMESTAMPTZ NOT NULL,
  value       NUMERIC NOT NULL,
  source_hint TEXT,
  inserted_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (station_id, device_id, metric_id, ts_bucket)
) PARTITION BY RANGE (ts_bucket);

-- Partitioned indexes (definitions on parent; create child indexes when partitions are created)
CREATE INDEX IF NOT EXISTS idx_fm_station_time_device_metric
  ON ONLY public.fact_measurements (station_id, ts_bucket, device_id, metric_id) INCLUDE (value);

CREATE INDEX IF NOT EXISTS idx_fm_device_time
  ON ONLY public.fact_measurements (device_id, ts_bucket);

COMMIT;
