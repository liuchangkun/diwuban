-- Schema DDL for database: pump_station_optimization (PostgreSQL 16)
-- NOTE: 本脚本不创建数据库，只创建表与约束。请先连接到已创建的数据库再执行本脚本。
--       例如：\c pump_station_optimization

SET client_min_messages = WARNING;
SET search_path = public;

SET client_encoding = 'UTF8';
BEGIN;


-- 1) 泵站维表
CREATE TABLE IF NOT EXISTS dim_stations (
  id          BIGSERIAL PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,
  extra       JSONB,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- 注释：dim_stations
COMMENT ON TABLE  dim_stations IS '泵站维表：存储泵站主数据';
COMMENT ON COLUMN dim_stations.id         IS '主键';
COMMENT ON COLUMN dim_stations.name       IS '泵站名称（唯一）';
COMMENT ON COLUMN dim_stations.extra      IS '附加信息（JSON）';
COMMENT ON COLUMN dim_stations.created_at IS '创建时间';


-- 2) 设备维表（包含“总管”作为设备）
CREATE TABLE IF NOT EXISTS dim_devices (
  id          BIGSERIAL PRIMARY KEY,
  station_id  BIGINT NOT NULL REFERENCES dim_stations(id),
  name        TEXT NOT NULL,
  type        TEXT NOT NULL,   -- 取值：'pump' | 'main_pipeline'
  pump_type   TEXT,            -- 当 type='pump' 时可取 'variable_frequency' | 'soft_start'，否则必须为 NULL
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

-- 注释：dim_devices
COMMENT ON TABLE  dim_devices IS '设备维表：包含水泵与总管道等设备';
COMMENT ON COLUMN dim_devices.id          IS '主键';
COMMENT ON COLUMN dim_devices.station_id  IS '所属泵站ID（FK dim_stations.id）';
COMMENT ON COLUMN dim_devices.name        IS '设备名称（同站内唯一）';
COMMENT ON COLUMN dim_devices.type        IS '设备类型：pump | main_pipeline';
COMMENT ON COLUMN dim_devices.pump_type   IS '泵型：variable_frequency | soft_start；当类型为总管时须为 NULL';
COMMENT ON COLUMN dim_devices.extra       IS '附加信息（JSON）';
COMMENT ON COLUMN dim_devices.created_at  IS '创建时间';

-- 3) 指标配置维表（来自 data_mapping.json）
CREATE TABLE IF NOT EXISTS dim_metric_config (
  id               BIGSERIAL PRIMARY KEY,
  metric_key       TEXT UNIQUE NOT NULL,  -- 例如：frequency, voltage_b, pressure, flow_rate, kwh
  unit             TEXT NOT NULL,         -- 单位字面量（严格按 mapping），如 Hz, KW/H, Mpa, M3/h
  unit_display     TEXT,

-- 注释：dim_metric_config
COMMENT ON TABLE  dim_metric_config IS '指标配置表：来自 data_mapping.json 的字段与单位等配置';
COMMENT ON COLUMN dim_metric_config.id              IS '主键';
COMMENT ON COLUMN dim_metric_config.metric_key      IS '指标字段键（唯一），如 voltage_b、pressure 等';
COMMENT ON COLUMN dim_metric_config.unit            IS '单位字面量（严格按 mapping）';
COMMENT ON COLUMN dim_metric_config.unit_display    IS '单位显示名（可与 unit 相同）';
COMMENT ON COLUMN dim_metric_config.decimals_policy IS '小数位策略：as_is 或 fixed';
COMMENT ON COLUMN dim_metric_config.fixed_decimals  IS '当策略为 fixed 时的小数位数';
COMMENT ON COLUMN dim_metric_config.value_type      IS '值类型（可选）';
COMMENT ON COLUMN dim_metric_config.valid_min       IS '值最小边界（可选）';
COMMENT ON COLUMN dim_metric_config.valid_max       IS '值最大边界（可选）';
COMMENT ON COLUMN dim_metric_config.created_at      IS '创建时间';

-- 注释：dim_mapping_items（可选）
COMMENT ON TABLE  dim_mapping_items IS 'mapping 快照项：记录 mapping 中的条目，便于版本追踪与绑定';
COMMENT ON COLUMN dim_mapping_items.id            IS '主键';
COMMENT ON COLUMN dim_mapping_items.mapping_hash  IS 'mapping 内容的哈希（或版本号）';
COMMENT ON COLUMN dim_mapping_items.station_name  IS '泵站名称（来自 mapping）';
COMMENT ON COLUMN dim_mapping_items.device_name   IS '设备名称（来自 mapping）';
COMMENT ON COLUMN dim_mapping_items.metric_key    IS '指标字段键（FK dim_metric_config.metric_key）';
COMMENT ON COLUMN dim_mapping_items.source_hint   IS 'mapping 中的源标识（不依赖实际文件路径）';
COMMENT ON COLUMN dim_mapping_items.created_at    IS '创建时间';

-- 6) 设备额定参数（新）
CREATE TABLE IF NOT EXISTS device_rated_params (
  id             BIGSERIAL PRIMARY KEY,
  device_id      BIGINT NOT NULL REFERENCES dim_devices(id) ON DELETE CASCADE,
  param_key      TEXT   NOT NULL,   -- 如：rated_flow, rated_head, rated_power, rated_voltage, rated_current, rated_frequency, pipe_diameter, pressure_rating, material, model
  value_numeric  NUMERIC,           -- 数值型参数（任选其一，至少一个非空）
  value_text     TEXT,              -- 文本型参数（如材质、型号）
  unit           TEXT,              -- 单位字面量（如 M3/h, m, kW, V, A, Hz, MPa, mm）
  source         TEXT,              -- 来源（资料/说明书/配置）
  effective_from TIMESTAMPTZ,       -- 生效开始（可选）
  effective_to   TIMESTAMPTZ,       -- 生效结束（可选）
  created_at     TIMESTAMPTZ DEFAULT now(),
  updated_at     TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT chk_rated_value_presence CHECK (value_numeric IS NOT NULL OR value_text IS NOT NULL),
  CONSTRAINT uq_device_param UNIQUE (device_id, param_key)
);

CREATE INDEX IF NOT EXISTS idx_rated_params_device ON device_rated_params(device_id);

-- 注释：device_rated_params
COMMENT ON TABLE  device_rated_params IS '设备额定参数：按设备存放名称牌/额定参数，支持数值与文本';
COMMENT ON COLUMN device_rated_params.id             IS '主键';
COMMENT ON COLUMN device_rated_params.device_id      IS '设备ID（FK dim_devices.id）';
COMMENT ON COLUMN device_rated_params.param_key      IS '参数键，例如 rated_flow/rated_head/rated_power/pipe_diameter 等';
COMMENT ON COLUMN device_rated_params.value_numeric  IS '数值型参数值（与 value_text 至少一个非空）';
COMMENT ON COLUMN device_rated_params.value_text     IS '文本型参数值（与 value_numeric 至少一个非空）';
COMMENT ON COLUMN device_rated_params.unit           IS '单位字面量，如 M3/h、m、kW、V、A、Hz、MPa、mm';
COMMENT ON COLUMN device_rated_params.source         IS '参数来源（资料/说明书/配置）';
COMMENT ON COLUMN device_rated_params.effective_from IS '参数生效开始时间（可选）';
COMMENT ON COLUMN device_rated_params.effective_to   IS '参数生效结束时间（可选）';
COMMENT ON COLUMN device_rated_params.created_at     IS '创建时间';
COMMENT ON COLUMN device_rated_params.updated_at     IS '更新时间';


COMMENT ON COLUMN dim_metric_config.updated_at      IS '更新时间';

  decimals_policy  TEXT DEFAULT 'as_is',  -- 'as_is' 或 'fixed'
  fixed_decimals   SMALLINT,
  value_type       TEXT,
  valid_min        NUMERIC,
  valid_max        NUMERIC,
  created_at       TIMESTAMPTZ DEFAULT now(),
  updated_at       TIMESTAMPTZ DEFAULT now()
);

-- 4) mapping 快照项（可选，便于记录版本与导入绑定）
CREATE TABLE IF NOT EXISTS dim_mapping_items (
  id            BIGSERIAL PRIMARY KEY,
  mapping_hash  TEXT NOT NULL,
  station_name  TEXT NOT NULL,
  device_name   TEXT NOT NULL,
  metric_key    TEXT NOT NULL REFERENCES dim_metric_config(metric_key),
  source_hint   TEXT NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- 5) 事实表（按秒对齐；按周范围分区，子分区按 station_id 哈希）
CREATE TABLE IF NOT EXISTS fact_measurements (
  id          BIGSERIAL,
  station_id  BIGINT NOT NULL REFERENCES dim_stations(id),
  device_id   BIGINT NOT NULL REFERENCES dim_devices(id),
  metric_id   BIGINT NOT NULL REFERENCES dim_metric_config(id),
  ts_raw      TIMESTAMPTZ NOT NULL,
  ts_bucket   TIMESTAMPTZ NOT NULL,  -- 对齐到秒：date_trunc('second', ts_raw)
  value       NUMERIC NOT NULL,
  source_hint TEXT,
  inserted_at TIMESTAMPTZ DEFAULT now(),

-- 注释：fact_measurements（父表）
COMMENT ON TABLE  fact_measurements IS '事实表：按 1 秒对齐的时序数据，按周分区+station_id 子分区';
COMMENT ON COLUMN fact_measurements.id          IS '行ID（非主键，仅作标识）';
COMMENT ON COLUMN fact_measurements.station_id  IS '泵站ID（FK dim_stations.id）';
COMMENT ON COLUMN fact_measurements.device_id   IS '设备ID（FK dim_devices.id）';
COMMENT ON COLUMN fact_measurements.metric_id   IS '指标ID（FK dim_metric_config.id）';
COMMENT ON COLUMN fact_measurements.ts_raw      IS '原始时间戳（本地时区解析入库）';
COMMENT ON COLUMN fact_measurements.ts_bucket   IS '对齐到秒的时间戳（date_trunc(''second'', ts_raw)）';
COMMENT ON COLUMN fact_measurements.value       IS '数值（按 CSV 原始小数位；不换算单位）';
COMMENT ON COLUMN fact_measurements.source_hint IS '来源标识（来自 mapping）';
COMMENT ON COLUMN fact_measurements.inserted_at IS '入库时间';

  PRIMARY KEY (station_id, device_id, metric_id, ts_bucket)
) PARTITION BY RANGE (ts_bucket);

-- 父表索引定义（注意：分区子表需要各自建立本地索引）
CREATE INDEX IF NOT EXISTS idx_fm_station_time_device_metric
  ON ONLY fact_measurements (station_id, ts_bucket, device_id, metric_id) INCLUDE (value);

CREATE INDEX IF NOT EXISTS idx_fm_device_time
  ON ONLY fact_measurements (device_id, ts_bucket);

COMMIT;

-- ============================================================================
-- 可选：自动创建“周分区 + station_id 哈希子分区”的帮助过程（建议保留）
-- 使用方式见脚本底部示例 DO 块
-- ============================================================================

CREATE OR REPLACE FUNCTION ensure_week_partition(
  p_week_start date,        -- 周起始（含），建议为周一
  p_modulus     int  DEFAULT 16,  -- station_id 哈希分片数（8~32）
  p_schema      text DEFAULT 'public'
) RETURNS void AS $$
DECLARE
  v_parent    text := p_schema || '.fact_measurements';
  v_part_name text := p_schema || '.fact_measurements_' || to_char(p_week_start,'IYYY"w"IW');
  v_sql       text;
  i           int;
BEGIN
  -- 创建周分区（若不存在）
  v_sql := format('CREATE TABLE IF NOT EXISTS %s PARTITION OF %s FOR VALUES FROM (%L) TO (%L) PARTITION BY HASH (station_id);',
                  v_part_name, v_parent, p_week_start::timestamptz, (p_week_start + 7)::timestamptz);
  EXECUTE v_sql;

  -- 创建哈希子分区
  FOR i IN 0..(p_modulus-1) LOOP
    v_sql := format('CREATE TABLE IF NOT EXISTS %s_p%s PARTITION OF %s FOR VALUES WITH (MODULUS %s, REMAINDER %s);',
                    v_part_name, i, v_part_name, p_modulus, i);
    EXECUTE v_sql;

    -- 本地索引
    v_sql := format('CREATE INDEX IF NOT EXISTS idx_fm_s_t_d_m_%s_p%s ON %s_p%s (station_id, ts_bucket, device_id, metric_id) INCLUDE (value);',
                    to_char(p_week_start,'IYYY"w"IW'), i, v_part_name, i);
    EXECUTE v_sql;

    v_sql := format('CREATE INDEX IF NOT EXISTS idx_fm_dev_t_%s_p%s ON %s_p%s (device_id, ts_bucket);',
                    to_char(p_week_start,'IYYY"w"IW'), i, v_part_name, i);
    EXECUTE v_sql;
  END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 示例：创建本周及未来 12 周分区（如不需要可注释掉）
DO $$
DECLARE
  v_monday date := date_trunc('week', now())::date;  -- ISO 周一
  k int;
BEGIN
  FOR k IN 0..12 LOOP
    PERFORM ensure_week_partition(v_monday + (k*7));
  END LOOP;
END;
$$;
