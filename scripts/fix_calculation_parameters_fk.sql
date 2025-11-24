-- ============================================
-- 修复 calculation_parameters 表的外键约束
-- ============================================
-- 目的：将 device_id 和 station_id 外键从 ON DELETE CASCADE 改为 ON DELETE RESTRICT
-- 原因：防止 prepare_dim 流程清空 dim_devices 表时级联删除设备级参数
-- 日期：2025-11-24
-- ============================================

BEGIN;

-- 1. 修改 device_id 外键约束
ALTER TABLE calculation_parameters
DROP CONSTRAINT IF EXISTS calculation_parameters_device_id_fkey,
ADD CONSTRAINT calculation_parameters_device_id_fkey
    FOREIGN KEY (device_id) REFERENCES dim_devices(id)
    ON UPDATE CASCADE 
    ON DELETE RESTRICT;

-- 2. 修改 station_id 外键约束
ALTER TABLE calculation_parameters
DROP CONSTRAINT IF EXISTS calculation_parameters_station_id_fkey,
ADD CONSTRAINT calculation_parameters_station_id_fkey
    FOREIGN KEY (station_id) REFERENCES dim_stations(id)
    ON UPDATE CASCADE 
    ON DELETE RESTRICT;

-- 3. 验证修改结果
DO $$
DECLARE
    device_fk_action CHAR(1);
    station_fk_action CHAR(1);
    metric_fk_action CHAR(1);
BEGIN
    -- 检查 device_id 外键
    SELECT confdeltype INTO device_fk_action
    FROM pg_constraint
    WHERE conrelid = 'calculation_parameters'::regclass
      AND conname = 'calculation_parameters_device_id_fkey';
    
    -- 检查 station_id 外键
    SELECT confdeltype INTO station_fk_action
    FROM pg_constraint
    WHERE conrelid = 'calculation_parameters'::regclass
      AND conname = 'calculation_parameters_station_id_fkey';
    
    -- 检查 metric_key 外键
    SELECT confdeltype INTO metric_fk_action
    FROM pg_constraint
    WHERE conrelid = 'calculation_parameters'::regclass
      AND conname = 'calculation_parameters_metric_key_fkey';
    
    -- 验证结果
    IF device_fk_action != 'r' THEN
        RAISE EXCEPTION 'device_id 外键修改失败：期望 RESTRICT (r)，实际 %', device_fk_action;
    END IF;
    
    IF station_fk_action != 'r' THEN
        RAISE EXCEPTION 'station_id 外键修改失败：期望 RESTRICT (r)，实际 %', station_fk_action;
    END IF;
    
    IF metric_fk_action != 'r' THEN
        RAISE EXCEPTION 'metric_key 外键修改失败：期望 RESTRICT (r)，实际 %', metric_fk_action;
    END IF;
    
    RAISE NOTICE '✅ 外键约束修改成功！';
    RAISE NOTICE '   - device_id: RESTRICT';
    RAISE NOTICE '   - station_id: RESTRICT';
    RAISE NOTICE '   - metric_key: RESTRICT';
END $$;

COMMIT;

