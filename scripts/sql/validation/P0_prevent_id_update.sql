-- ============================================
-- P0优先级：增强ID稳定性保护
-- ============================================
-- 文件：scripts/sql/validation/P0_prevent_id_update.sql
-- 用途：创建触发器防止意外修改 dim_devices.id 和 dim_stations.id
-- 优先级：P0 - 立即执行
-- 风险：低
-- 执行方式：psql -h localhost -U postgres -d pump_station -f P0_prevent_id_update.sql
-- ============================================

\echo '=========================================='
\echo 'P0优先级：增强ID稳定性保护'
\echo '=========================================='
\echo ''

BEGIN;

-- ============================================
-- 第一步：创建触发器函数
-- ============================================

\echo '【1】创建触发器函数'
\echo '----------------------------------------'

\echo '1.1 创建 prevent_id_update() 函数'
CREATE OR REPLACE FUNCTION prevent_id_update()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.id IS DISTINCT FROM NEW.id THEN
        RAISE EXCEPTION 'Direct ID modification is not allowed for table %. Use migration tools instead. Old ID: %, New ID: %', 
            TG_TABLE_NAME, OLD.id, NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION prevent_id_update() IS '防止直接修改维度表ID的触发器函数。如果检测到ID变化，会抛出异常。';

\echo '✅ prevent_id_update() 函数已创建'

-- ============================================
-- 第二步：为 dim_devices 创建触发器
-- ============================================

\echo ''
\echo '【2】为 dim_devices 创建触发器'
\echo '----------------------------------------'

\echo '2.1 删除旧触发器（如果存在）'
DROP TRIGGER IF EXISTS prevent_dim_devices_id_update ON dim_devices;

\echo '2.2 创建新触发器'
CREATE TRIGGER prevent_dim_devices_id_update
BEFORE UPDATE ON dim_devices
FOR EACH ROW
EXECUTE FUNCTION prevent_id_update();

COMMENT ON TRIGGER prevent_dim_devices_id_update ON dim_devices IS '防止直接修改 dim_devices.id。如需修改ID，请使用专用的迁移工具。';

\echo '✅ dim_devices 的ID保护触发器已创建'

-- ============================================
-- 第三步：为 dim_stations 创建触发器
-- ============================================

\echo ''
\echo '【3】为 dim_stations 创建触发器'
\echo '----------------------------------------'

\echo '3.1 删除旧触发器（如果存在）'
DROP TRIGGER IF EXISTS prevent_dim_stations_id_update ON dim_stations;

\echo '3.2 创建新触发器'
CREATE TRIGGER prevent_dim_stations_id_update
BEFORE UPDATE ON dim_stations
FOR EACH ROW
EXECUTE FUNCTION prevent_id_update();

COMMENT ON TRIGGER prevent_dim_stations_id_update ON dim_stations IS '防止直接修改 dim_stations.id。如需修改ID，请使用专用的迁移工具。';

\echo '✅ dim_stations 的ID保护触发器已创建'

-- ============================================
-- 第四步：验证触发器
-- ============================================

\echo ''
\echo '【4】验证触发器'
\echo '----------------------------------------'

\echo '4.1 查询所有触发器'
SELECT 
    trigger_name AS 触发器名称,
    event_object_table AS 表名,
    action_timing AS 触发时机,
    event_manipulation AS 触发事件,
    action_statement AS 执行函数
FROM information_schema.triggers
WHERE trigger_name IN ('prevent_dim_devices_id_update', 'prevent_dim_stations_id_update')
ORDER BY event_object_table;

-- ============================================
-- 第五步：测试触发器（可选）
-- ============================================

\echo ''
\echo '【5】测试触发器（可选）'
\echo '----------------------------------------'

\echo '5.1 测试 dim_devices 触发器'
DO $$
DECLARE
    test_passed BOOLEAN := FALSE;
BEGIN
    -- 尝试修改ID（应该失败）
    BEGIN
        UPDATE dim_devices SET id = 9999 WHERE id = 1;
        RAISE EXCEPTION 'Test failed: ID update should have been prevented';
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLERRM LIKE '%Direct ID modification is not allowed%' THEN
                RAISE NOTICE '✅ dim_devices 触发器测试通过：成功阻止ID修改';
                test_passed := TRUE;
            ELSE
                RAISE EXCEPTION 'Test failed with unexpected error: %', SQLERRM;
            END IF;
    END;
    
    IF NOT test_passed THEN
        RAISE EXCEPTION 'Test failed';
    END IF;
END $$;

\echo ''
\echo '5.2 测试 dim_stations 触发器'
DO $$
DECLARE
    test_passed BOOLEAN := FALSE;
BEGIN
    -- 尝试修改ID（应该失败）
    BEGIN
        UPDATE dim_stations SET id = 9999 WHERE id = 1;
        RAISE EXCEPTION 'Test failed: ID update should have been prevented';
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLERRM LIKE '%Direct ID modification is not allowed%' THEN
                RAISE NOTICE '✅ dim_stations 触发器测试通过：成功阻止ID修改';
                test_passed := TRUE;
            ELSE
                RAISE EXCEPTION 'Test failed with unexpected error: %', SQLERRM;
            END IF;
    END;
    
    IF NOT test_passed THEN
        RAISE EXCEPTION 'Test failed';
    END IF;
END $$;

-- ============================================
-- 第六步：创建临时禁用触发器的函数（管理员使用）
-- ============================================

\echo ''
\echo '【6】创建管理员工具函数'
\echo '----------------------------------------'

\echo '6.1 创建临时禁用触发器的函数'
CREATE OR REPLACE FUNCTION admin_disable_id_protection()
RETURNS void AS $$
BEGIN
    ALTER TABLE dim_devices DISABLE TRIGGER prevent_dim_devices_id_update;
    ALTER TABLE dim_stations DISABLE TRIGGER prevent_dim_stations_id_update;
    RAISE NOTICE '⚠️ ID保护触发器已禁用。请在完成操作后立即重新启用！';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION admin_disable_id_protection() IS '临时禁用ID保护触发器（仅供管理员使用）。使用后必须立即调用 admin_enable_id_protection() 重新启用。';

\echo '✅ admin_disable_id_protection() 函数已创建'

\echo ''
\echo '6.2 创建重新启用触发器的函数'
CREATE OR REPLACE FUNCTION admin_enable_id_protection()
RETURNS void AS $$
BEGIN
    ALTER TABLE dim_devices ENABLE TRIGGER prevent_dim_devices_id_update;
    ALTER TABLE dim_stations ENABLE TRIGGER prevent_dim_stations_id_update;
    RAISE NOTICE '✅ ID保护触发器已重新启用';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION admin_enable_id_protection() IS '重新启用ID保护触发器。';

\echo '✅ admin_enable_id_protection() 函数已创建'

-- ============================================
-- 第七步：提交事务
-- ============================================

\echo ''
\echo '【7】提交事务'
\echo '----------------------------------------'

COMMIT;

\echo '✅ 所有触发器和管理员工具已成功创建并提交'

\echo ''
\echo '=========================================='
\echo '执行完成'
\echo '=========================================='
\echo ''
\echo '总结：'
\echo '- 已创建 prevent_id_update() 触发器函数'
\echo '- 已为 dim_devices 创建ID保护触发器'
\echo '- 已为 dim_stations 创建ID保护触发器'
\echo '- 已创建管理员工具函数（临时禁用/启用触发器）'
\echo '- 所有触发器测试通过'
\echo ''
\echo '使用说明：'
\echo '1. 正常情况下，任何尝试修改ID的操作都会被阻止'
\echo '2. 如需修改ID，请使用专用的迁移工具'
\echo '3. 管理员可以使用以下函数临时禁用/启用触发器：'
\echo '   - SELECT admin_disable_id_protection();  -- 禁用'
\echo '   - SELECT admin_enable_id_protection();   -- 启用'
\echo '4. ⚠️ 禁用触发器后必须立即重新启用！'
\echo ''

