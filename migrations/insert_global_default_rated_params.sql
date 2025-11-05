-- Insert default rated parameters
INSERT INTO global_default_rated_params (param_key, default_value, param_unit, description, created_by) VALUES
('rated_flow', 400.0, 'm3/h', 'Default rated flow', 'manual_fix_6'),
('rated_head', 50.0, 'm', 'Default rated head', 'manual_fix_6'),
('rated_efficiency', 0.75, '-', 'Default rated efficiency', 'manual_fix_6'),
('rated_frequency', 50.0, 'Hz', 'Default rated frequency', 'manual_fix_6'),
('poles_pair', 2, '-', 'Default poles pair', 'manual_fix_6'),
('eta_motor', 0.92, '-', 'Default motor efficiency', 'manual_fix_6'),
('eta_vfd', 0.97, '-', 'Default VFD efficiency', 'manual_fix_6')
ON CONFLICT (param_key) DO UPDATE SET
    default_value = EXCLUDED.default_value,
    param_unit = EXCLUDED.param_unit,
    description = EXCLUDED.description,
    updated_at = NOW();

