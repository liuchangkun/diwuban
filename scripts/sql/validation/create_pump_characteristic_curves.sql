-- =====================================================
-- 水泵特性曲线表
-- =====================================================
-- 用途：存储水泵的特性曲线数据（Q-H、Q-P、Q-η曲线）
-- 作者：System
-- 创建时间：2025-10-05
-- =====================================================

-- 删除已存在的表（如果需要重建）
DROP TABLE IF EXISTS pump_characteristic_curves CASCADE;

-- 创建水泵特性曲线表
CREATE TABLE pump_characteristic_curves (
    id SERIAL PRIMARY KEY,
    device_id INT NOT NULL,
    curve_type TEXT NOT NULL,
    speed NUMERIC,  -- 转速（rpm），NULL表示额定转速
    frequency NUMERIC,  -- 频率（Hz），NULL表示额定频率
    flow_rate NUMERIC NOT NULL,  -- 流量（m³/h）
    value NUMERIC NOT NULL,  -- 对应值（扬程m/功率kW/效率%）
    source TEXT,  -- 数据来源（'manufacturer', 'measured', 'calibrated'）
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 约束
    CONSTRAINT chk_curve_type CHECK (curve_type IN ('Q-H', 'Q-P', 'Q-eta')),
    CONSTRAINT chk_flow_rate CHECK (flow_rate >= 0),
    CONSTRAINT chk_value CHECK (value >= 0),  -- 允许0值（如零流量时的效率）
    CONSTRAINT chk_source CHECK (source IS NULL OR source IN ('manufacturer', 'measured', 'calibrated'))
);

-- 创建唯一索引（防止重复数据）
CREATE UNIQUE INDEX idx_pump_curves_unique 
ON pump_characteristic_curves (
    device_id, 
    curve_type, 
    COALESCE(speed, -1),  -- 使用-1表示NULL
    COALESCE(frequency, -1),  -- 使用-1表示NULL
    flow_rate
);

-- 创建普通索引（优化查询）
CREATE INDEX idx_pump_curves_device_type 
ON pump_characteristic_curves (device_id, curve_type);

CREATE INDEX idx_pump_curves_device_speed 
ON pump_characteristic_curves (device_id, speed);

CREATE INDEX idx_pump_curves_device_frequency 
ON pump_characteristic_curves (device_id, frequency);

-- 创建自动更新updated_at的触发器
CREATE OR REPLACE FUNCTION update_pump_curves_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_pump_curves_updated_at
BEFORE UPDATE ON pump_characteristic_curves
FOR EACH ROW
EXECUTE FUNCTION update_pump_curves_updated_at();

-- 添加表注释
COMMENT ON TABLE pump_characteristic_curves IS '水泵特性曲线数据表，存储Q-H、Q-P、Q-η曲线';
COMMENT ON COLUMN pump_characteristic_curves.id IS '主键';
COMMENT ON COLUMN pump_characteristic_curves.device_id IS '设备ID';
COMMENT ON COLUMN pump_characteristic_curves.curve_type IS '曲线类型：Q-H（流量-扬程）、Q-P（流量-功率）、Q-eta（流量-效率）';
COMMENT ON COLUMN pump_characteristic_curves.speed IS '转速（rpm），NULL表示额定转速';
COMMENT ON COLUMN pump_characteristic_curves.frequency IS '频率（Hz），NULL表示额定频率';
COMMENT ON COLUMN pump_characteristic_curves.flow_rate IS '流量（m³/h）';
COMMENT ON COLUMN pump_characteristic_curves.value IS '对应值：扬程（m）、功率（kW）或效率（%）';
COMMENT ON COLUMN pump_characteristic_curves.source IS '数据来源：manufacturer（厂家）、measured（实测）、calibrated（校准）';
COMMENT ON COLUMN pump_characteristic_curves.created_at IS '创建时间';
COMMENT ON COLUMN pump_characteristic_curves.updated_at IS '更新时间';

-- 插入示例数据（设备ID=1的水泵）
-- Q-H曲线（流量-扬程）
INSERT INTO pump_characteristic_curves (device_id, curve_type, speed, frequency, flow_rate, value, source) VALUES
(1, 'Q-H', 1450, 50, 0, 32.0, 'manufacturer'),
(1, 'Q-H', 1450, 50, 50, 31.5, 'manufacturer'),
(1, 'Q-H', 1450, 50, 100, 30.5, 'manufacturer'),
(1, 'Q-H', 1450, 50, 150, 29.0, 'manufacturer'),
(1, 'Q-H', 1450, 50, 200, 27.0, 'manufacturer'),
(1, 'Q-H', 1450, 50, 250, 24.5, 'manufacturer'),
(1, 'Q-H', 1450, 50, 300, 21.5, 'manufacturer'),
(1, 'Q-H', 1450, 50, 350, 18.0, 'manufacturer'),
(1, 'Q-H', 1450, 50, 400, 14.0, 'manufacturer');

-- Q-P曲线（流量-功率）
INSERT INTO pump_characteristic_curves (device_id, curve_type, speed, frequency, flow_rate, value, source) VALUES
(1, 'Q-P', 1450, 50, 0, 15.0, 'manufacturer'),
(1, 'Q-P', 1450, 50, 50, 18.5, 'manufacturer'),
(1, 'Q-P', 1450, 50, 100, 22.0, 'manufacturer'),
(1, 'Q-P', 1450, 50, 150, 25.5, 'manufacturer'),
(1, 'Q-P', 1450, 50, 200, 29.0, 'manufacturer'),
(1, 'Q-P', 1450, 50, 250, 32.5, 'manufacturer'),
(1, 'Q-P', 1450, 50, 300, 36.0, 'manufacturer'),
(1, 'Q-P', 1450, 50, 350, 39.5, 'manufacturer'),
(1, 'Q-P', 1450, 50, 400, 43.0, 'manufacturer');

-- Q-η曲线（流量-效率）
INSERT INTO pump_characteristic_curves (device_id, curve_type, speed, frequency, flow_rate, value, source) VALUES
(1, 'Q-eta', 1450, 50, 0, 0.0, 'manufacturer'),
(1, 'Q-eta', 1450, 50, 50, 55.0, 'manufacturer'),
(1, 'Q-eta', 1450, 50, 100, 72.0, 'manufacturer'),
(1, 'Q-eta', 1450, 50, 150, 82.0, 'manufacturer'),
(1, 'Q-eta', 1450, 50, 200, 85.0, 'manufacturer'),
(1, 'Q-eta', 1450, 50, 250, 83.0, 'manufacturer'),
(1, 'Q-eta', 1450, 50, 300, 78.0, 'manufacturer'),
(1, 'Q-eta', 1450, 50, 350, 70.0, 'manufacturer'),
(1, 'Q-eta', 1450, 50, 400, 60.0, 'manufacturer');

-- 验证数据
SELECT 
    device_id,
    curve_type,
    COUNT(*) as point_count,
    MIN(flow_rate) as min_flow,
    MAX(flow_rate) as max_flow,
    MIN(value) as min_value,
    MAX(value) as max_value
FROM pump_characteristic_curves
GROUP BY device_id, curve_type
ORDER BY device_id, curve_type;

COMMIT;

