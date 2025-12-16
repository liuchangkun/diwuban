-- Migration: add 'other' device type to chk_device_type
-- Created by Augment Agent

BEGIN;

-- Up: Ensure constraint allows 'other' (and retain existing allowed values)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_device_type' 
          AND conrelid = 'public.dim_devices'::regclass
    ) THEN
        ALTER TABLE public.dim_devices DROP CONSTRAINT chk_device_type;
    END IF;
END $$;

ALTER TABLE public.dim_devices
    ADD CONSTRAINT chk_device_type
    CHECK (type IN ('pump', 'main_pipeline', 'clear_water_pool', 'other'));

COMMIT;

-- Rollback: remove 'other' from allowed set
-- Note: Adjust the allowed set if your original constraint differed
--       from ('pump','main_pipeline','clear_water_pool')

-- Example rollback
-- BEGIN;
-- ALTER TABLE public.dim_devices DROP CONSTRAINT IF EXISTS chk_device_type;
-- ALTER TABLE public.dim_devices
--     ADD CONSTRAINT chk_device_type
--     CHECK (type IN ('pump', 'main_pipeline', 'clear_water_pool'));
-- COMMIT;

