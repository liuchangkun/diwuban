-- Extend calculation_parameters table to support string parameters
-- Solution 6: Parameter System Fix - Step 3 (Remaining 3 methods)
-- Created: 2025-10-26
-- Version: v1.0

-- Add param_value_text column to support string parameters
ALTER TABLE calculation_parameters
ADD COLUMN IF NOT EXISTS param_value_text TEXT;

-- Add comment to explain the new column
COMMENT ON COLUMN calculation_parameters.param_value_text IS 'String type parameter value (used when param_type=string)';

-- Update param_type to support 'string' type
-- Note: param_type is already TEXT, so no schema change needed

-- Verify the new column
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'calculation_parameters'
  AND column_name = 'param_value_text';

