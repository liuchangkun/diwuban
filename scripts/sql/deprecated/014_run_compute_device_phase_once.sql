BEGIN;
SET LOCAL statement_timeout TO '300000ms';
-- deprecated: one-shot call for device_phase (kept for archive only)
CALL public.sp_compute_device_phase('2025-02-27T18:00:00Z','2025-02-27T20:00:00Z', NULL);
COMMIT;

