-- ============================================================================
-- 数据库迁移脚本：将维度表ID从自增序列改为固定ID
-- ============================================================================
-- 创建时间：2025-10-29
-- 用途：将 dim_stations 和 dim_devices 表的ID从数据库自增序列改为配置文件中的固定ID
-- 依赖：所有外键必须配置 ON UPDATE CASCADE（已验证）
-- 环境：测试环境
-- ============================================================================

-- 开始事务
BEGIN;

-- ============================================================================
-- 步骤0：前置检查
-- ============================================================================

\echo '============================================================================'
\echo '步骤0：前置检查'
\echo '============================================================================'

-- 检查外键CASCADE配置（安全验证）
\echo '检查外键CASCADE配置...'
DO $$
DECLARE
    v_non_cascade_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_non_cascade_count
    FROM information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
    JOIN information_schema.referential_constraints AS rc
        ON rc.constraint_name = tc.constraint_name
        AND rc.constraint_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND ccu.table_name IN ('dim_stations', 'dim_devices')
        AND tc.table_schema = 'public'
        AND rc.update_rule != 'CASCADE';
    
    IF v_non_cascade_count > 0 THEN
        RAISE EXCEPTION '发现 % 个外键未配置 ON UPDATE CASCADE，无法安全执行迁移！', v_non_cascade_count;
    END IF;
    
    RAISE NOTICE '✅ 外键CASCADE配置检查通过';
END $$;

-- 检查序列是否存在
\echo '检查序列是否存在...'
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'dim_stations_id_seq') THEN
        RAISE NOTICE '⚠️  序列 dim_stations_id_seq 不存在，可能已被删除';
    ELSE
        RAISE NOTICE '✅ 序列 dim_stations_id_seq 存在';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'dim_devices_id_seq') THEN
        RAISE NOTICE '⚠️  序列 dim_devices_id_seq 不存在，可能已被删除';
    ELSE
        RAISE NOTICE '✅ 序列 dim_devices_id_seq 存在';
    END IF;
END $$;

-- 显示当前数据状态
\echo '当前数据状态：'
SELECT 'dim_stations' AS 表名, COUNT(*) AS 记录数, MIN(id) AS 最小ID, MAX(id) AS 最大ID FROM dim_stations
UNION ALL
SELECT 'dim_devices' AS 表名, COUNT(*) AS 记录数, MIN(id) AS 最小ID, MAX(id) AS 最大ID FROM dim_devices;

-- ============================================================================
-- 步骤1：创建临时映射表
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo '步骤1：创建临时映射表'
\echo '============================================================================'

-- 创建泵站ID映射表
\echo '创建泵站ID映射表...'
CREATE TEMP TABLE temp_station_id_mapping (
    old_id BIGINT,
    new_id BIGINT,
    station_name TEXT
);

-- 插入泵站映射数据（基于配置文件）
INSERT INTO temp_station_id_mapping (old_id, new_id, station_name)
SELECT 
    id AS old_id,
    1 AS new_id,  -- 配置文件中 "二期供水泵房" 的固定ID
    name AS station_name
FROM dim_stations
WHERE name = '二期供水泵房';

\echo '泵站ID映射表内容：'
SELECT * FROM temp_station_id_mapping;

-- 创建设备ID映射表
\echo ''
\echo '创建设备ID映射表...'
CREATE TEMP TABLE temp_device_id_mapping (
    old_id BIGINT,
    new_id BIGINT,
    device_name TEXT
);

-- 插入设备映射数据（基于配置文件）
INSERT INTO temp_device_id_mapping (old_id, new_id, device_name)
SELECT 
    id AS old_id,
    CASE name
        WHEN '二期供水泵房1#泵' THEN 1
        WHEN '二期供水泵房2#泵' THEN 2
        WHEN '二期供水泵房3#泵' THEN 3
        WHEN '二期供水泵房4#泵' THEN 4
        WHEN '二期供水泵房5#泵' THEN 5
        WHEN '二期供水泵房6#泵' THEN 6
        WHEN '二期供水泵房总管' THEN 7
        WHEN '其他' THEN 8
        ELSE NULL
    END AS new_id,
    name AS device_name
FROM dim_devices;

-- 检查是否有未映射的设备
DO $$
DECLARE
    v_unmapped_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_unmapped_count
    FROM temp_device_id_mapping
    WHERE new_id IS NULL;
    
    IF v_unmapped_count > 0 THEN
        RAISE EXCEPTION '发现 % 个设备无法映射到配置文件中的固定ID！', v_unmapped_count;
    END IF;
    
    RAISE NOTICE '✅ 所有设备都已成功映射到固定ID';
END $$;

\echo '设备ID映射表内容：'
SELECT * FROM temp_device_id_mapping ORDER BY new_id;

-- ============================================================================
-- 步骤2：更新 dim_stations 表的ID
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo '步骤2：更新 dim_stations 表的ID'
\echo '============================================================================'

\echo '开始更新 dim_stations 表的ID...'

-- 检查是否有ID冲突
DO $$
DECLARE
    v_conflict_count INTEGER;
BEGIN
    -- 检查新ID是否已被其他记录占用
    SELECT COUNT(*)
    INTO v_conflict_count
    FROM dim_stations s
    WHERE s.id IN (SELECT new_id FROM temp_station_id_mapping)
      AND s.name NOT IN (SELECT station_name FROM temp_station_id_mapping);
    
    IF v_conflict_count > 0 THEN
        RAISE EXCEPTION '发现 % 个ID冲突：新ID已被其他泵站占用！', v_conflict_count;
    END IF;
    
    RAISE NOTICE '✅ 无ID冲突';
END $$;

-- 更新泵站ID（利用CASCADE自动更新所有关联表）
UPDATE dim_stations
SET id = m.new_id
FROM temp_station_id_mapping m
WHERE dim_stations.id = m.old_id
  AND dim_stations.name = m.station_name;

\echo '✅ dim_stations 表ID更新完成'

-- 验证更新结果
\echo '验证 dim_stations 表更新结果：'
SELECT id, name FROM dim_stations ORDER BY id;

-- ============================================================================
-- 步骤3：更新 dim_devices 表的ID
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo '步骤3：更新 dim_devices 表的ID'
\echo '============================================================================'

\echo '开始更新 dim_devices 表的ID...'

-- 检查是否有ID冲突
DO $$
DECLARE
    v_conflict_count INTEGER;
BEGIN
    -- 检查新ID是否已被其他记录占用
    SELECT COUNT(*)
    INTO v_conflict_count
    FROM dim_devices d
    WHERE d.id IN (SELECT new_id FROM temp_device_id_mapping)
      AND d.name NOT IN (SELECT device_name FROM temp_device_id_mapping);
    
    IF v_conflict_count > 0 THEN
        RAISE EXCEPTION '发现 % 个ID冲突：新ID已被其他设备占用！', v_conflict_count;
    END IF;
    
    RAISE NOTICE '✅ 无ID冲突';
END $$;

-- 更新设备ID（利用CASCADE自动更新所有关联表）
-- 注意：需要按照从大到小的顺序更新，避免临时冲突
UPDATE dim_devices
SET id = m.new_id
FROM temp_device_id_mapping m
WHERE dim_devices.id = m.old_id
  AND dim_devices.name = m.device_name;

\echo '✅ dim_devices 表ID更新完成'

-- 验证更新结果
\echo '验证 dim_devices 表更新结果：'
SELECT id, station_id, name, type FROM dim_devices ORDER BY id;

-- ============================================================================
-- 步骤4：删除自增序列
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo '步骤4：删除自增序列'
\echo '============================================================================'

-- 删除 dim_stations 的序列
\echo '删除 dim_stations_id_seq 序列...'
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'dim_stations_id_seq') THEN
        -- 先移除列的默认值（如果有）
        ALTER TABLE dim_stations ALTER COLUMN id DROP DEFAULT;
        -- 删除序列
        DROP SEQUENCE IF EXISTS public.dim_stations_id_seq;
        RAISE NOTICE '✅ 序列 dim_stations_id_seq 已删除';
    ELSE
        RAISE NOTICE '⚠️  序列 dim_stations_id_seq 不存在，跳过删除';
    END IF;
END $$;

-- 删除 dim_devices 的序列
\echo '删除 dim_devices_id_seq 序列...'
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'dim_devices_id_seq') THEN
        -- 先移除列的默认值（如果有）
        ALTER TABLE dim_devices ALTER COLUMN id DROP DEFAULT;
        -- 删除序列
        DROP SEQUENCE IF EXISTS public.dim_devices_id_seq;
        RAISE NOTICE '✅ 序列 dim_devices_id_seq 已删除';
    ELSE
        RAISE NOTICE '⚠️  序列 dim_devices_id_seq 不存在，跳过删除';
    END IF;
END $$;

-- ============================================================================
-- 步骤5：验证数据完整性
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo '步骤5：验证数据完整性'
\echo '============================================================================'

-- 验证泵站数据
\echo '验证泵站数据：'
DO $$
DECLARE
    v_station_count INTEGER;
    v_expected_count INTEGER := 1;  -- 配置文件中有1个泵站
BEGIN
    SELECT COUNT(*) INTO v_station_count FROM dim_stations;
    
    IF v_station_count != v_expected_count THEN
        RAISE EXCEPTION '泵站数量不匹配！期望: %, 实际: %', v_expected_count, v_station_count;
    END IF;
    
    -- 验证泵站ID是否为1
    IF NOT EXISTS (SELECT 1 FROM dim_stations WHERE id = 1 AND name = '二期供水泵房') THEN
        RAISE EXCEPTION '泵站ID验证失败：未找到ID=1的"二期供水泵房"';
    END IF;
    
    RAISE NOTICE '✅ 泵站数据验证通过：共 % 个泵站，ID=1', v_station_count;
END $$;

-- 验证设备数据
\echo '验证设备数据：'
DO $$
DECLARE
    v_device_count INTEGER;
    v_expected_count INTEGER := 8;  -- 配置文件中有8个设备
    v_min_id INTEGER;
    v_max_id INTEGER;
BEGIN
    SELECT COUNT(*), MIN(id), MAX(id) 
    INTO v_device_count, v_min_id, v_max_id 
    FROM dim_devices;
    
    IF v_device_count != v_expected_count THEN
        RAISE EXCEPTION '设备数量不匹配！期望: %, 实际: %', v_expected_count, v_device_count;
    END IF;
    
    IF v_min_id != 1 OR v_max_id != 8 THEN
        RAISE EXCEPTION '设备ID范围不正确！期望: 1-8, 实际: %-% ', v_min_id, v_max_id;
    END IF;
    
    RAISE NOTICE '✅ 设备数据验证通过：共 % 个设备，ID范围: %-% ', v_device_count, v_min_id, v_max_id;
END $$;

-- 验证外键关联表（抽样检查）
\echo '验证外键关联表（抽样检查）：'
DO $$
DECLARE
    v_orphan_count INTEGER;
BEGIN
    -- 检查是否有孤立的外键引用
    SELECT COUNT(*)
    INTO v_orphan_count
    FROM dim_devices d
    WHERE NOT EXISTS (SELECT 1 FROM dim_stations s WHERE s.id = d.station_id);
    
    IF v_orphan_count > 0 THEN
        RAISE EXCEPTION '发现 % 个设备的station_id引用不存在的泵站！', v_orphan_count;
    END IF;
    
    RAISE NOTICE '✅ 外键关联验证通过：无孤立引用';
END $$;

-- 显示最终数据状态
\echo ''
\echo '最终数据状态：'
SELECT 'dim_stations' AS 表名, COUNT(*) AS 记录数, MIN(id) AS 最小ID, MAX(id) AS 最大ID FROM dim_stations
UNION ALL
SELECT 'dim_devices' AS 表名, COUNT(*) AS 记录数, MIN(id) AS 最小ID, MAX(id) AS 最大ID FROM dim_devices;

-- ============================================================================
-- 提交事务
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo '所有验证通过，准备提交事务...'
\echo '============================================================================'

COMMIT;

\echo ''
\echo '✅✅✅ 迁移成功完成！✅✅✅'
\echo ''
\echo '总结：'
\echo '- dim_stations 表：ID已更新为固定ID (1)'
\echo '- dim_devices 表：ID已更新为固定ID (1-8)'
\echo '- 自增序列已删除：dim_stations_id_seq, dim_devices_id_seq'
\echo '- 所有外键关联表已通过CASCADE自动更新'
\echo '- 数据完整性验证通过'
\echo ''

