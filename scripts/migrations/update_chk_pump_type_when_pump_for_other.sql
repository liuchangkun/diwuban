-- Update CHECK constraint to allow pump_type=NULL for non-pump device types, including 'clear_water_pool' and 'other'
ALTER TABLE public.dim_devices DROP CONSTRAINT IF EXISTS chk_pump_type_when_pump;
ALTER TABLE public.dim_devices
    ADD CONSTRAINT chk_pump_type_when_pump
    CHECK (
        (type = 'pump' AND (pump_type IS NULL OR pump_type IN ('variable_frequency','soft_start')))
        OR (type IN ('main_pipeline','clear_water_pool','other') AND pump_type IS NULL)
    );

