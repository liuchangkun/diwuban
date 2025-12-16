-- 修复pump_characteristic_curves表的source约束，添加'optimized'值

-- 删除旧约束
ALTER TABLE pump_characteristic_curves DROP CONSTRAINT IF EXISTS chk_source;

-- 添加新约束（包含'optimized'）
ALTER TABLE pump_characteristic_curves 
ADD CONSTRAINT chk_source CHECK (source IS NULL OR source IN ('manufacturer', 'measured', 'calibrated', 'optimized'));

-- 验证
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'pump_characteristic_curves'::regclass 
  AND conname = 'chk_source';

