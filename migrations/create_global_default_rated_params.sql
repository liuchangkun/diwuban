-- 创建全局默认额定参数表
-- 用于没有额定参数的设备使用默认值

CREATE TABLE IF NOT EXISTS global_default_rated_params (
    param_key TEXT PRIMARY KEY,
    default_value NUMERIC NOT NULL,
    param_unit TEXT,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT DEFAULT 'system'
);

-- 插入默认额定参数
INSERT INTO global_default_rated_params (param_key, default_value, param_unit, description, created_by) VALUES
('rated_flow', 400.0, 'm³/h', '默认额定流量', 'manual_fix_6'),
('rated_head', 50.0, 'm', '默认额定扬程', 'manual_fix_6'),
('rated_efficiency', 0.75, '-', '默认额定效率', 'manual_fix_6'),
('rated_frequency', 50.0, 'Hz', '默认额定频率', 'manual_fix_6'),
('poles_pair', 2, '-', '默认极对数', 'manual_fix_6'),
('eta_motor', 0.92, '-', '默认电机效率', 'manual_fix_6'),
('eta_vfd', 0.97, '-', '默认变频器效率', 'manual_fix_6')
ON CONFLICT (param_key) DO UPDATE SET
    default_value = EXCLUDED.default_value,
    param_unit = EXCLUDED.param_unit,
    description = EXCLUDED.description,
    updated_at = NOW(),
    updated_by = EXCLUDED.created_by;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_global_default_rated_params_key 
ON global_default_rated_params(param_key);

-- 添加注释
COMMENT ON TABLE global_default_rated_params IS '全局默认额定参数表（用于没有额定参数的设备）';
COMMENT ON COLUMN global_default_rated_params.param_key IS '参数键（如rated_flow, rated_head等）';
COMMENT ON COLUMN global_default_rated_params.default_value IS '默认值';
COMMENT ON COLUMN global_default_rated_params.param_unit IS '参数单位';
COMMENT ON COLUMN global_default_rated_params.description IS '参数描述';

