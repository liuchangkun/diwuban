-- ============================================================================
-- 迁移脚本：calculation_validation_config 表结构升级
-- ============================================================================
-- 目的：将旧的 param_name/param_value 结构迁移到新的 JSONB params 结构
-- 作者：AI Assistant
-- 日期：2025-10-05
-- ============================================================================

BEGIN;

-- 1. 备份现有数据到临时表
DROP TABLE IF EXISTS calculation_validation_config_backup;
CREATE TABLE calculation_validation_config_backup AS 
SELECT * FROM calculation_validation_config;

SELECT '✓ 步骤1：备份现有数据完成，共 ' || COUNT(*) || ' 行' as status
FROM calculation_validation_config_backup;

-- 2. 删除旧表
DROP TABLE IF EXISTS calculation_validation_config CASCADE;

SELECT '✓ 步骤2：删除旧表完成' as status;

-- 3. 创建新表结构
CREATE TABLE calculation_validation_config (
    id BIGSERIAL PRIMARY KEY,
    station_id BIGINT,  -- NULL表示全局配置
    device_id BIGINT,   -- NULL表示站点级配置
    metric_key TEXT NOT NULL,
    validator_type TEXT NOT NULL,  -- 'range', 'non_negative', 'efficiency', 'power_consistency', 'pressure', 'speed', 'torque'
    params JSONB,  -- 存储所有参数，如 {"min": 0, "max": 100, "tolerance": 0.15}
    is_enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100,  -- 验证优先级，数字越小优先级越高
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 创建唯一索引（支持COALESCE）
CREATE UNIQUE INDEX uq_validation_config
ON calculation_validation_config (
    COALESCE(station_id, 0),
    COALESCE(device_id, 0),
    metric_key,
    validator_type
);

-- 创建索引
CREATE INDEX idx_validation_config_station ON calculation_validation_config(station_id) WHERE station_id IS NOT NULL;
CREATE INDEX idx_validation_config_device ON calculation_validation_config(device_id) WHERE device_id IS NOT NULL;
CREATE INDEX idx_validation_config_metric ON calculation_validation_config(metric_key);
CREATE INDEX idx_validation_config_type ON calculation_validation_config(validator_type);
CREATE INDEX idx_validation_config_enabled ON calculation_validation_config(is_enabled) WHERE is_enabled = TRUE;
CREATE INDEX idx_validation_config_params ON calculation_validation_config USING GIN(params);

-- 添加注释
COMMENT ON TABLE calculation_validation_config IS '计算结果验证配置表';
COMMENT ON COLUMN calculation_validation_config.station_id IS '站点ID，NULL表示全局配置';
COMMENT ON COLUMN calculation_validation_config.device_id IS '设备ID，NULL表示站点级配置';
COMMENT ON COLUMN calculation_validation_config.metric_key IS '指标键';
COMMENT ON COLUMN calculation_validation_config.validator_type IS '验证器类型';
COMMENT ON COLUMN calculation_validation_config.params IS '验证参数（JSONB格式）';
COMMENT ON COLUMN calculation_validation_config.is_enabled IS '是否启用';
COMMENT ON COLUMN calculation_validation_config.priority IS '验证优先级（数字越小优先级越高）';

SELECT '✓ 步骤3：创建新表结构完成' as status;

-- 4. 迁移数据（如果备份表中有数据）
-- 将旧的 param_name/param_value 格式转换为 JSONB
DO $$
DECLARE
    backup_count INTEGER;
    migrated_count INTEGER := 0;
BEGIN
    SELECT COUNT(*) INTO backup_count FROM calculation_validation_config_backup;
    
    IF backup_count > 0 THEN
        -- 聚合同一配置的多个参数到JSONB
        INSERT INTO calculation_validation_config (
            station_id,
            device_id,
            metric_key,
            validator_type,
            params,
            is_enabled,
            priority,
            created_at,
            updated_at
        )
        SELECT 
            station_id,
            device_id,
            metric_key,
            validator_type,
            jsonb_object_agg(param_name, param_value) as params,
            BOOL_AND(enabled) as is_enabled,  -- 所有参数都启用才算启用
            100 as priority,
            MIN(created_at) as created_at,
            MAX(updated_at) as updated_at
        FROM calculation_validation_config_backup
        GROUP BY station_id, device_id, metric_key, validator_type;
        
        GET DIAGNOSTICS migrated_count = ROW_COUNT;
        
        RAISE NOTICE '✓ 步骤4：数据迁移完成，迁移 % 条配置', migrated_count;
    ELSE
        RAISE NOTICE '✓ 步骤4：无数据需要迁移';
    END IF;
END $$;

-- 5. 验证迁移结果
SELECT '✓ 步骤5：迁移验证' as status;
SELECT 
    '  - 备份表行数: ' || (SELECT COUNT(*) FROM calculation_validation_config_backup) as info
UNION ALL
SELECT 
    '  - 新表行数: ' || (SELECT COUNT(*) FROM calculation_validation_config)
UNION ALL
SELECT 
    '  - 新表指标数: ' || (SELECT COUNT(DISTINCT metric_key) FROM calculation_validation_config);

-- 6. 创建触发器：自动更新 updated_at
CREATE OR REPLACE FUNCTION update_validation_config_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_validation_config_updated_at
    BEFORE UPDATE ON calculation_validation_config
    FOR EACH ROW
    EXECUTE FUNCTION update_validation_config_updated_at();

SELECT '✓ 步骤6：创建触发器完成' as status;

COMMIT;

-- 显示最终结果
SELECT '========================================' as separator;
SELECT '迁移完成！' as result;
SELECT '========================================' as separator;
SELECT 
    'calculation_validation_config 表已升级到新结构' as info
UNION ALL
SELECT 
    '- 使用 JSONB 存储参数'
UNION ALL
SELECT 
    '- 支持层级配置（全局/站点/设备）'
UNION ALL
SELECT 
    '- 字段名称已统一（enabled → is_enabled）';

