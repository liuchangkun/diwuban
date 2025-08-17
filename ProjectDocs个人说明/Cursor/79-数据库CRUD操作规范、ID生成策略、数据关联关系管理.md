______________________________________________________________________

## description: 数据库CRUD操作规范、ID生成策略、数据关联关系管理（表操作、主外键、数据一致性）

# 数据库CRUD操作与数据关联规范

## ID生成策略

### 主键生成规则

```sql
-- 站点ID生成（自增，范围预留）
CREATE TABLE stations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    location VARCHAR(200),
    station_type ENUM('PUMP', 'VALVE', 'MONITOR') DEFAULT 'PUMP',
    external_id VARCHAR(50) UNIQUE, -- 外部系统ID
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_type_active (station_type, is_active)
) AUTO_INCREMENT = 1000; -- 从1000开始，预留系统ID

-- 设备ID生成（站点前缀 + 序号）
CREATE TABLE devices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    station_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    device_code VARCHAR(20) NOT NULL UNIQUE, -- 格式：ST{station_id}D{序号}
    device_type ENUM('pump', 'valve', 'sensor', 'controller') NOT NULL,
    pump_type ENUM('fixed_speed', 'variable_frequency', 'soft_start') NULL,
    specifications JSON, -- 设备规格参数
    installation_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    parent_device_id INT NULL, -- 支持设备层级关系
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (station_id) REFERENCES stations(id) ON DELETE RESTRICT,
    FOREIGN KEY (parent_device_id) REFERENCES devices(id) ON DELETE SET NULL,
    UNIQUE KEY uk_station_name (station_id, name),
    UNIQUE KEY uk_device_code (device_code),
    INDEX idx_station_type (station_id, device_type),
    INDEX idx_type_active (device_type, is_active)
) AUTO_INCREMENT = 10000;
```

### ID生成存储过程

```sql
-- 自动生成设备编码
DELIMITER $$
CREATE FUNCTION fn_generate_device_code(p_station_id INT, p_device_type VARCHAR(20))
RETURNS VARCHAR(20)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_sequence_num INT DEFAULT 1;
    DECLARE v_device_code VARCHAR(20);
    DECLARE v_type_prefix VARCHAR(5);

    -- 根据设备类型设置前缀
    CASE p_device_type
        WHEN 'pump' THEN SET v_type_prefix = 'P';
        WHEN 'valve' THEN SET v_type_prefix = 'V';
        WHEN 'sensor' THEN SET v_type_prefix = 'S';
        WHEN 'controller' THEN SET v_type_prefix = 'C';
        ELSE SET v_type_prefix = 'D';
    END CASE;

    -- 查找下一个可用序号
    SELECT COALESCE(MAX(CAST(SUBSTRING(device_code, LENGTH(CONCAT('ST', p_station_id, v_type_prefix)) + 1) AS UNSIGNED)), 0) + 1
    INTO v_sequence_num
    FROM devices
    WHERE station_id = p_station_id
      AND device_code LIKE CONCAT('ST', p_station_id, v_type_prefix, '%');

    -- 生成设备编码：ST{station_id}{type_prefix}{sequence}
    SET v_device_code = CONCAT('ST', p_station_id, v_type_prefix, LPAD(v_sequence_num, 3, '0'));

    RETURN v_device_code;
END$$
DELIMITER ;

-- 设备插入触发器（自动生成编码）
DELIMITER $$
CREATE TRIGGER tr_device_generate_code
    BEFORE INSERT ON devices
    FOR EACH ROW
BEGIN
    IF NEW.device_code IS NULL OR NEW.device_code = '' THEN
        SET NEW.device_code = fn_generate_device_code(NEW.station_id, NEW.device_type);
    END IF;
END$$
DELIMITER ;
```

## 数据关联关系管理

### 站点-设备关系

```sql
-- 创建站点设备配置视图
CREATE VIEW v_station_device_config AS
SELECT
    s.id as station_id,
    s.name as station_name,
    s.station_type,
    s.location,
    d.id as device_id,
    d.name as device_name,
    d.device_code,
    d.device_type,
    d.pump_type,
    d.specifications,
    d.is_active as device_active,
    d.sort_order,
    pd.name as parent_device_name,
    COUNT(cd.id) as child_device_count
FROM stations s
LEFT JOIN devices d ON s.id = d.station_id
LEFT JOIN devices pd ON d.parent_device_id = pd.id
LEFT JOIN devices cd ON d.id = cd.parent_device_id
WHERE s.is_active = TRUE
GROUP BY s.id, d.id
ORDER BY s.name, d.sort_order, d.name;

-- 设备层级关系查询函数
DELIMITER $$
CREATE FUNCTION fn_get_device_hierarchy(p_device_id INT, p_direction ENUM('UP', 'DOWN'))
RETURNS JSON
READS SQL DATA
BEGIN
    DECLARE v_result JSON DEFAULT JSON_ARRAY();

    IF p_direction = 'UP' THEN
        -- 向上查找父设备
        WITH RECURSIVE device_parents AS (
            SELECT id, name, device_code, parent_device_id, 0 as level
            FROM devices WHERE id = p_device_id
            UNION ALL
            SELECT d.id, d.name, d.device_code, d.parent_device_id, dp.level + 1
            FROM devices d
            JOIN device_parents dp ON d.id = dp.parent_device_id
            WHERE dp.level < 10 -- 防止无限递归
        )
        SELECT JSON_ARRAYAGG(
            JSON_OBJECT('id', id, 'name', name, 'code', device_code, 'level', level)
        ) INTO v_result
        FROM device_parents WHERE level > 0;

    ELSE -- DOWN
        -- 向下查找子设备
        WITH RECURSIVE device_children AS (
            SELECT id, name, device_code, parent_device_id, 0 as level
            FROM devices WHERE id = p_device_id
            UNION ALL
            SELECT d.id, d.name, d.device_code, d.parent_device_id, dc.level + 1
            FROM devices d
            JOIN device_children dc ON d.parent_device_id = dc.id
            WHERE dc.level < 10 -- 防止无限递归
        )
        SELECT JSON_ARRAYAGG(
            JSON_OBJECT('id', id, 'name', name, 'code', device_code, 'level', level)
        ) INTO v_result
        FROM device_children WHERE level > 0;
    END IF;

    RETURN IFNULL(v_result, JSON_ARRAY());
END$$
DELIMITER ;
```

## CRUD操作规范

### 站点管理操作

```sql
-- 站点创建存储过程
DELIMITER $$
CREATE PROCEDURE sp_create_station(
    IN p_name VARCHAR(100),
    IN p_location VARCHAR(200),
    IN p_station_type ENUM('PUMP', 'VALVE', 'MONITOR'),
    IN p_external_id VARCHAR(50),
    OUT p_station_id INT,
    OUT p_result_code INT,
    OUT p_result_message VARCHAR(255)
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        GET DIAGNOSTICS CONDITION 1
            p_result_code = MYSQL_ERRNO,
            p_result_message = MESSAGE_TEXT;
        ROLLBACK;
    END;

    START TRANSACTION;

    -- 检查名称唯一性
    IF EXISTS (SELECT 1 FROM stations WHERE name = p_name) THEN
        SET p_result_code = 1001;
        SET p_result_message = CONCAT('站点名称已存在: ', p_name);
        ROLLBACK;
    ELSE
        -- 插入新站点
        INSERT INTO stations (name, location, station_type, external_id)
        VALUES (p_name, p_location, p_station_type, p_external_id);

        SET p_station_id = LAST_INSERT_ID();
        SET p_result_code = 0;
        SET p_result_message = '站点创建成功';

        COMMIT;
    END IF;
END$$
DELIMITER ;

-- 站点更新存储过程
DELIMITER $$
CREATE PROCEDURE sp_update_station(
    IN p_station_id INT,
    IN p_name VARCHAR(100),
    IN p_location VARCHAR(200),
    IN p_station_type ENUM('PUMP', 'VALVE', 'MONITOR'),
    IN p_is_active BOOLEAN,
    OUT p_result_code INT,
    OUT p_result_message VARCHAR(255)
)
BEGIN
    DECLARE v_exists INT DEFAULT 0;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        GET DIAGNOSTICS CONDITION 1
            p_result_code = MYSQL_ERRNO,
            p_result_message = MESSAGE_TEXT;
        ROLLBACK;
    END;

    START TRANSACTION;

    -- 检查站点是否存在
    SELECT COUNT(*) INTO v_exists FROM stations WHERE id = p_station_id;

    IF v_exists = 0 THEN
        SET p_result_code = 1002;
        SET p_result_message = CONCAT('站点不存在: ID=', p_station_id);
        ROLLBACK;
    ELSE
        -- 检查新名称的唯一性（如果名称有变化）
        IF EXISTS (SELECT 1 FROM stations WHERE name = p_name AND id != p_station_id) THEN
            SET p_result_code = 1001;
            SET p_result_message = CONCAT('站点名称已被其他站点使用: ', p_name);
            ROLLBACK;
        ELSE
            -- 更新站点信息
            UPDATE stations
            SET name = p_name,
                location = p_location,
                station_type = p_station_type,
                is_active = p_is_active,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = p_station_id;

            SET p_result_code = 0;
            SET p_result_message = '站点更新成功';

            COMMIT;
        END IF;
    END IF;
END$$
DELIMITER ;

-- 站点删除存储过程（软删除）
DELIMITER $$
CREATE PROCEDURE sp_delete_station(
    IN p_station_id INT,
    IN p_force_delete BOOLEAN DEFAULT FALSE,
    OUT p_result_code INT,
    OUT p_result_message VARCHAR(255)
)
BEGIN
    DECLARE v_device_count INT DEFAULT 0;
    DECLARE v_data_count INT DEFAULT 0;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        GET DIAGNOSTICS CONDITION 1
            p_result_code = MYSQL_ERRNO,
            p_result_message = MESSAGE_TEXT;
        ROLLBACK;
    END;

    START TRANSACTION;

    -- 检查是否有关联设备
    SELECT COUNT(*) INTO v_device_count
    FROM devices WHERE station_id = p_station_id AND is_active = TRUE;

    -- 检查是否有历史数据
    SELECT COUNT(*) INTO v_data_count
    FROM aligned_data WHERE station_id = p_station_id LIMIT 1;

    IF v_device_count > 0 AND NOT p_force_delete THEN
        SET p_result_code = 1003;
        SET p_result_message = CONCAT('站点有 ', v_device_count, ' 个活跃设备，无法删除');
        ROLLBACK;
    ELSEIF v_data_count > 0 AND NOT p_force_delete THEN
        SET p_result_code = 1004;
        SET p_result_message = '站点有历史数据，无法删除';
        ROLLBACK;
    ELSE
        -- 软删除或强制删除
        IF p_force_delete THEN
            -- 硬删除（级联删除相关数据）
            DELETE FROM aligned_data WHERE station_id = p_station_id;
            DELETE FROM devices WHERE station_id = p_station_id;
            DELETE FROM stations WHERE id = p_station_id;
        ELSE
            -- 软删除
            UPDATE stations SET is_active = FALSE WHERE id = p_station_id;
            UPDATE devices SET is_active = FALSE WHERE station_id = p_station_id;
        END IF;

        SET p_result_code = 0;
        SET p_result_message = '站点删除成功';
        COMMIT;
    END IF;
END$$
DELIMITER ;
```

### 设备管理操作

```sql
-- 设备创建存储过程
DELIMITER $$
CREATE PROCEDURE sp_create_device(
    IN p_station_id INT,
    IN p_name VARCHAR(100),
    IN p_device_type ENUM('pump', 'valve', 'sensor', 'controller'),
    IN p_pump_type ENUM('fixed_speed', 'variable_frequency', 'soft_start'),
    IN p_specifications JSON,
    IN p_parent_device_id INT,
    OUT p_device_id INT,
    OUT p_device_code VARCHAR(20),
    OUT p_result_code INT,
    OUT p_result_message VARCHAR(255)
)
BEGIN
    DECLARE v_station_exists INT DEFAULT 0;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        GET DIAGNOSTICS CONDITION 1
            p_result_code = MYSQL_ERRNO,
            p_result_message = MESSAGE_TEXT;
        ROLLBACK;
    END;

    START TRANSACTION;

    -- 检查站点是否存在且活跃
    SELECT COUNT(*) INTO v_station_exists
    FROM stations WHERE id = p_station_id AND is_active = TRUE;

    IF v_station_exists = 0 THEN
        SET p_result_code = 2001;
        SET p_result_message = CONCAT('站点不存在或已停用: ID=', p_station_id);
        ROLLBACK;
    ELSEIF EXISTS (SELECT 1 FROM devices WHERE station_id = p_station_id AND name = p_name) THEN
        SET p_result_code = 2002;
        SET p_result_message = CONCAT('设备名称在该站点已存在: ', p_name);
        ROLLBACK;
    ELSE
        -- 插入新设备（设备编码由触发器自动生成）
        INSERT INTO devices (
            station_id, name, device_type, pump_type,
            specifications, parent_device_id
        ) VALUES (
            p_station_id, p_name, p_device_type, p_pump_type,
            p_specifications, p_parent_device_id
        );

        SET p_device_id = LAST_INSERT_ID();

        -- 获取生成的设备编码
        SELECT device_code INTO p_device_code
        FROM devices WHERE id = p_device_id;

        SET p_result_code = 0;
        SET p_result_message = '设备创建成功';

        COMMIT;
    END IF;
END$$
DELIMITER ;

-- 设备批量创建存储过程
DELIMITER $$
CREATE PROCEDURE sp_batch_create_devices(
    IN p_devices_json JSON,
    OUT p_result_summary JSON
)
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_idx INT DEFAULT 0;
    DECLARE v_device_count INT;
    DECLARE v_success_count INT DEFAULT 0;
    DECLARE v_error_count INT DEFAULT 0;
    DECLARE v_errors JSON DEFAULT JSON_ARRAY();

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        GET DIAGNOSTICS CONDITION 1
            @error_code = MYSQL_ERRNO,
            @error_message = MESSAGE_TEXT;
        SET v_errors = JSON_ARRAY_APPEND(v_errors, '$',
            JSON_OBJECT('index', v_idx, 'error_code', @error_code, 'error_message', @error_message));
        SET v_error_count = v_error_count + 1;
        ROLLBACK;
    END;

    SET v_device_count = JSON_LENGTH(p_devices_json);

    WHILE v_idx < v_device_count DO
        START TRANSACTION;

        SET @device_info = JSON_EXTRACT(p_devices_json, CONCAT('$[', v_idx, ']'));
        SET @station_id = JSON_UNQUOTE(JSON_EXTRACT(@device_info, '$.station_id'));
        SET @name = JSON_UNQUOTE(JSON_EXTRACT(@device_info, '$.name'));
        SET @device_type = JSON_UNQUOTE(JSON_EXTRACT(@device_info, '$.device_type'));
        SET @pump_type = JSON_UNQUOTE(JSON_EXTRACT(@device_info, '$.pump_type'));
        SET @specifications = JSON_EXTRACT(@device_info, '$.specifications');

        INSERT INTO devices (station_id, name, device_type, pump_type, specifications)
        VALUES (@station_id, @name, @device_type, @pump_type, @specifications);

        SET v_success_count = v_success_count + 1;
        COMMIT;

        SET v_idx = v_idx + 1;
    END WHILE;

    SET p_result_summary = JSON_OBJECT(
        'total_count', v_device_count,
        'success_count', v_success_count,
        'error_count', v_error_count,
        'errors', v_errors
    );
END$$
DELIMITER ;
```

### 数据查询优化

```sql
-- 设备数据查询优化视图
CREATE VIEW v_device_latest_data AS
SELECT
    d.id as device_id,
    d.name as device_name,
    d.device_code,
    d.device_type,
    s.name as station_name,
    ad.standard_time as latest_time,
    ad.data_json,
    ad.data_quality,
    TIMESTAMPDIFF(SECOND, ad.standard_time, NOW()) as data_age_seconds
FROM devices d
JOIN stations s ON d.station_id = s.id
LEFT JOIN (
    SELECT device_id,
           standard_time,
           data_json,
           data_quality,
           ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY standard_time DESC) as rn
    FROM aligned_data
    WHERE standard_time >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
) ad ON d.id = ad.device_id AND ad.rn = 1
WHERE d.is_active = TRUE AND s.is_active = TRUE;

-- 分页查询函数
DELIMITER $$
CREATE PROCEDURE sp_get_devices_paginated(
    IN p_station_id INT,
    IN p_device_type VARCHAR(20),
    IN p_is_active BOOLEAN,
    IN p_page_size INT DEFAULT 20,
    IN p_page_number INT DEFAULT 1,
    OUT p_total_count INT
)
BEGIN
    DECLARE v_offset INT;

    SET v_offset = (p_page_number - 1) * p_page_size;

    -- 获取总数
    SELECT COUNT(*) INTO p_total_count
    FROM devices d
    JOIN stations s ON d.station_id = s.id
    WHERE (p_station_id IS NULL OR d.station_id = p_station_id)
      AND (p_device_type IS NULL OR d.device_type = p_device_type)
      AND (p_is_active IS NULL OR d.is_active = p_is_active)
      AND s.is_active = TRUE;

    -- 分页查询结果
    SELECT
        d.id,
        d.station_id,
        s.name as station_name,
        d.name as device_name,
        d.device_code,
        d.device_type,
        d.pump_type,
        d.specifications,
        d.is_active,
        d.created_at,
        d.updated_at
    FROM devices d
    JOIN stations s ON d.station_id = s.id
    WHERE (p_station_id IS NULL OR d.station_id = p_station_id)
      AND (p_device_type IS NULL OR d.device_type = p_device_type)
      AND (p_is_active IS NULL OR d.is_active = p_is_active)
      AND s.is_active = TRUE
    ORDER BY s.name, d.sort_order, d.name
    LIMIT p_page_size OFFSET v_offset;
END$$
DELIMITER ;
```

## 数据一致性保证

### 外键约束和级联操作

```sql
-- 添加完整的外键约束
ALTER TABLE devices
ADD CONSTRAINT fk_devices_station
FOREIGN KEY (station_id) REFERENCES stations(id)
ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE devices
ADD CONSTRAINT fk_devices_parent
FOREIGN KEY (parent_device_id) REFERENCES devices(id)
ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE aligned_data
ADD CONSTRAINT fk_aligned_data_station
FOREIGN KEY (station_id) REFERENCES stations(id)
ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE aligned_data
ADD CONSTRAINT fk_aligned_data_device
FOREIGN KEY (device_id) REFERENCES devices(id)
ON DELETE RESTRICT ON UPDATE CASCADE;
```

### 数据完整性检查函数

```sql
-- 数据完整性检查函数
DELIMITER $$
CREATE FUNCTION fn_check_data_integrity()
RETURNS JSON
READS SQL DATA
BEGIN
    DECLARE v_result JSON DEFAULT JSON_OBJECT();
    DECLARE v_orphan_devices INT DEFAULT 0;
    DECLARE v_orphan_data INT DEFAULT 0;
    DECLARE v_missing_stations INT DEFAULT 0;
    DECLARE v_circular_references INT DEFAULT 0;

    -- 检查孤立设备（站点不存在或已停用）
    SELECT COUNT(*) INTO v_orphan_devices
    FROM devices d
    LEFT JOIN stations s ON d.station_id = s.id
    WHERE s.id IS NULL OR s.is_active = FALSE;

    -- 检查孤立数据（设备不存在或已停用）
    SELECT COUNT(DISTINCT ad.device_id) INTO v_orphan_data
    FROM aligned_data ad
    LEFT JOIN devices d ON ad.device_id = d.id
    WHERE d.id IS NULL OR d.is_active = FALSE;

    -- 检查缺失的站点数据
    SELECT COUNT(*) INTO v_missing_stations
    FROM aligned_data ad
    LEFT JOIN stations s ON ad.station_id = s.id
    WHERE s.id IS NULL;

    -- 检查设备循环引用
    WITH RECURSIVE device_hierarchy AS (
        SELECT id, parent_device_id, CONCAT(',', id, ',') as path, 0 as level
        FROM devices
        WHERE parent_device_id IS NOT NULL
        UNION ALL
        SELECT d.id, d.parent_device_id, CONCAT(dh.path, d.id, ','), dh.level + 1
        FROM devices d
        JOIN device_hierarchy dh ON d.parent_device_id = dh.id
        WHERE dh.level < 10 AND FIND_IN_SET(d.id, dh.path) = 0
    )
    SELECT COUNT(*) INTO v_circular_references
    FROM device_hierarchy
    WHERE FIND_IN_SET(parent_device_id, path) > 0;

    SET v_result = JSON_OBJECT(
        'orphan_devices', v_orphan_devices,
        'orphan_data_devices', v_orphan_data,
        'missing_station_data', v_missing_stations,
        'circular_device_references', v_circular_references,
        'check_timestamp', NOW()
    );

    RETURN v_result;
END$$
DELIMITER ;

-- 数据修复存储过程
DELIMITER $$
CREATE PROCEDURE sp_repair_data_integrity(
    IN p_repair_type ENUM('ORPHAN_DEVICES', 'ORPHAN_DATA', 'MISSING_STATIONS', 'ALL'),
    OUT p_repair_summary JSON
)
BEGIN
    DECLARE v_orphan_devices_fixed INT DEFAULT 0;
    DECLARE v_orphan_data_fixed INT DEFAULT 0;
    DECLARE v_missing_stations_fixed INT DEFAULT 0;

    START TRANSACTION;

    IF p_repair_type IN ('ORPHAN_DEVICES', 'ALL') THEN
        -- 停用孤立设备
        UPDATE devices d
        LEFT JOIN stations s ON d.station_id = s.id
        SET d.is_active = FALSE
        WHERE (s.id IS NULL OR s.is_active = FALSE) AND d.is_active = TRUE;

        SET v_orphan_devices_fixed = ROW_COUNT();
    END IF;

    IF p_repair_type IN ('ORPHAN_DATA', 'ALL') THEN
        -- 删除孤立数据（谨慎操作）
        DELETE ad FROM aligned_data ad
        LEFT JOIN devices d ON ad.device_id = d.id
        WHERE d.id IS NULL OR d.is_active = FALSE;

        SET v_orphan_data_fixed = ROW_COUNT();
    END IF;

    IF p_repair_type IN ('MISSING_STATIONS', 'ALL') THEN
        -- 删除缺失站点的数据
        DELETE ad FROM aligned_data ad
        LEFT JOIN stations s ON ad.station_id = s.id
        WHERE s.id IS NULL;

        SET v_missing_stations_fixed = ROW_COUNT();
    END IF;

    SET p_repair_summary = JSON_OBJECT(
        'orphan_devices_fixed', v_orphan_devices_fixed,
        'orphan_data_records_removed', v_orphan_data_fixed,
        'missing_station_records_removed', v_missing_stations_fixed,
        'repair_timestamp', NOW()
    );

    COMMIT;
END$$
DELIMITER ;
```

## 性能优化索引

### 关键索引设计

```sql
-- 站点表索引
CREATE INDEX idx_stations_name_active ON stations(name, is_active);
CREATE INDEX idx_stations_type_active ON stations(station_type, is_active);
CREATE INDEX idx_stations_external_id ON stations(external_id);

-- 设备表索引
CREATE INDEX idx_devices_station_type ON devices(station_id, device_type, is_active);
CREATE INDEX idx_devices_code ON devices(device_code);
CREATE INDEX idx_devices_parent ON devices(parent_device_id);
CREATE INDEX idx_devices_type_active ON devices(device_type, is_active);

-- 数据表索引优化
CREATE INDEX idx_aligned_data_device_time ON aligned_data(device_id, standard_time DESC);
CREATE INDEX idx_aligned_data_station_time ON aligned_data(station_id, standard_time DESC);
CREATE INDEX idx_aligned_data_quality_time ON aligned_data(data_quality, standard_time DESC);

-- 复合索引for常用查询
CREATE INDEX idx_devices_station_active_type ON devices(station_id, is_active, device_type);
CREATE INDEX idx_aligned_data_station_device_time ON aligned_data(station_id, device_id, standard_time DESC);
```

## 操作权限和安全

### 角色权限管理

```sql
-- 创建操作角色
CREATE ROLE 'pump_admin', 'pump_operator', 'pump_viewer';

-- 管理员权限（完全访问）
GRANT ALL PRIVILEGES ON pump_monitoring_db.stations TO 'pump_admin';
GRANT ALL PRIVILEGES ON pump_monitoring_db.devices TO 'pump_admin';
GRANT ALL PRIVILEGES ON pump_monitoring_db.aligned_data TO 'pump_admin';

-- 操作员权限（读写数据，但不能修改站点设备配置）
GRANT SELECT, INSERT, UPDATE ON pump_monitoring_db.aligned_data TO 'pump_operator';
GRANT SELECT ON pump_monitoring_db.stations TO 'pump_operator';
GRANT SELECT ON pump_monitoring_db.devices TO 'pump_operator';

-- 查看器权限（只读）
GRANT SELECT ON pump_monitoring_db.* TO 'pump_viewer';

-- 存储过程权限
GRANT EXECUTE ON PROCEDURE pump_monitoring_db.sp_create_station TO 'pump_admin';
GRANT EXECUTE ON PROCEDURE pump_monitoring_db.sp_create_device TO 'pump_admin';
GRANT EXECUTE ON PROCEDURE pump_monitoring_db.sp_get_devices_paginated TO 'pump_operator', 'pump_viewer';
```

## 使用指南和最佳实践

### 操作清单

- [ ] 部署所有表结构和索引
- [ ] 创建ID生成函数和触发器
- [ ] 部署CRUD存储过程
- [ ] 设置外键约束
- [ ] 创建查询优化视图
- [ ] 配置角色和权限
- [ ] 测试数据完整性检查
- [ ] 验证批量操作性能
- [ ] 设置定期完整性检查任务
- [ ] 编写操作手册和故障排除指南

### 性能建议

1. **批量操作**：使用批量插入/更新存储过程
1. **分页查询**：大结果集使用分页避免内存问题
1. **索引维护**：定期分析和优化索引使用
1. **数据归档**：及时归档历史数据保持性能
1. **监控慢查询**：定期检查和优化慢查询
1. **连接池**：使用连接池管理数据库连接
1. **事务控制**：保持事务简短避免长时间锁定
1. **缓存策略**：对频繁查询的数据实施缓存
