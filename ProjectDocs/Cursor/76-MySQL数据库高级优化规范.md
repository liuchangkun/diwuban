---
description: MySQL数据库高级优化规范（配置调优、查询优化、事务管理、锁优化、分区策略）
---
# MySQL数据库高级优化规范

## 服务器配置优化
### 内存配置
```ini
# InnoDB缓冲池（建议设为可用内存的70-80%）
innodb_buffer_pool_size = 8G
innodb_buffer_pool_instances = 8
innodb_buffer_pool_chunk_size = 128M

# 查询缓存（MySQL 8.0已移除）
# query_cache_size = 0
# query_cache_type = OFF

# 排序和连接缓冲
sort_buffer_size = 4M
join_buffer_size = 4M
read_buffer_size = 2M
read_rnd_buffer_size = 2M

# 临时表
tmp_table_size = 128M
max_heap_table_size = 128M
```

### I/O配置
```ini
# InnoDB日志
innodb_log_file_size = 1G
innodb_log_files_in_group = 3
innodb_log_buffer_size = 64M
innodb_flush_log_at_trx_commit = 2

# 数据文件
innodb_file_per_table = ON
innodb_data_file_path = ibdata1:1G:autoextend
innodb_autoextend_increment = 64

# I/O性能
innodb_io_capacity = 2000
innodb_io_capacity_max = 4000
innodb_read_io_threads = 8
innodb_write_io_threads = 8
innodb_use_native_aio = ON
```

### 连接和并发
```ini
# 连接设置
max_connections = 500
max_connect_errors = 1000
connect_timeout = 10
wait_timeout = 28800
interactive_timeout = 28800

# 并发控制
innodb_thread_concurrency = 0
innodb_commit_concurrency = 0
innodb_concurrency_tickets = 5000

# 锁等待
innodb_lock_wait_timeout = 10
lock_wait_timeout = 10
```

## 查询优化策略
### 索引优化
- 复合索引设计原则：
  - 最左前缀原则；
  - 选择性高的列在前；
  - 覆盖索引优于回表查询；
  - 避免冗余索引。

```sql
-- 示例：时间序列数据索引
CREATE INDEX idx_device_time ON aligned_data (device_id, standard_time);
CREATE INDEX idx_station_time ON aligned_data (station_id, standard_time);

-- 覆盖索引
CREATE INDEX idx_cover ON aligned_data (device_id, standard_time, data_quality) 
INCLUDE (data_json);
```

### 查询重写
- 避免SELECT *，明确指定列；
- 使用LIMIT限制结果集大小；
- 优化子查询为JOIN；
- 使用EXISTS替代IN子查询；
- 避免在WHERE中使用函数。

```sql
-- 优化前
SELECT * FROM aligned_data 
WHERE DATE(standard_time) = '2025-01-01';

-- 优化后
SELECT device_id, standard_time, data_json 
FROM aligned_data 
WHERE standard_time >= '2025-01-01 00:00:00' 
  AND standard_time < '2025-01-02 00:00:00'
LIMIT 1000;
```

### 执行计划分析
- 使用EXPLAIN ANALYZE分析查询；
- 关注扫描行数、索引使用情况；
- 优化嵌套循环连接；
- 避免全表扫描。

## 事务管理优化
### 事务隔离级别
```sql
-- 根据业务需求选择合适的隔离级别
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;

-- 长事务检测和处理
SELECT 
  id, user, host, db, command, time, state, info
FROM information_schema.processlist 
WHERE command != 'Sleep' AND time > 300;
```

### 批量操作优化
```sql
-- 批量插入优化
SET SESSION sql_log_bin = 0;
SET SESSION unique_checks = 0;
SET SESSION foreign_key_checks = 0;
SET SESSION autocommit = 0;

-- 分批提交
DELIMITER $$
CREATE PROCEDURE batch_insert()
BEGIN
  DECLARE done INT DEFAULT FALSE;
  DECLARE batch_size INT DEFAULT 10000;
  DECLARE counter INT DEFAULT 0;
  
  -- 批量插入逻辑
  WHILE NOT done DO
    -- 插入操作
    SET counter = counter + 1;
    IF counter % batch_size = 0 THEN
      COMMIT;
      START TRANSACTION;
    END IF;
  END WHILE;
  
  COMMIT;
END$$
DELIMITER ;
```

## 锁优化与并发控制
### 锁等待优化
```ini
# 死锁检测
innodb_deadlock_detect = ON
innodb_print_all_deadlocks = ON

# 锁等待超时
innodb_lock_wait_timeout = 10

# 行锁等待
innodb_status_output_locks = ON
```

### 锁粒度控制
```sql
-- 使用适当的锁粒度
-- 读取时使用共享锁
SELECT * FROM aligned_data 
WHERE device_id = 1 LOCK IN SHARE MODE;

-- 更新时使用排他锁
SELECT * FROM aligned_data 
WHERE device_id = 1 FOR UPDATE;

-- 避免长时间持锁
BEGIN;
-- 尽快完成操作
UPDATE aligned_data SET data_json = '{}' WHERE id = 1;
COMMIT;
```

## 分区策略
### 时间分区
```sql
-- 按月分区
CREATE TABLE aligned_data_partitioned (
  id BIGINT AUTO_INCREMENT,
  station_id INT NOT NULL,
  device_id INT NOT NULL,
  standard_time DATETIME NOT NULL,
  data_json JSON,
  data_quality TINYINT DEFAULT 1,
  data_hash VARCHAR(32),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id, standard_time),
  KEY idx_device_time (device_id, standard_time),
  KEY idx_station_time (station_id, standard_time)
) ENGINE=InnoDB
PARTITION BY RANGE (YEAR(standard_time) * 100 + MONTH(standard_time)) (
  PARTITION p202501 VALUES LESS THAN (202502),
  PARTITION p202502 VALUES LESS THAN (202503),
  PARTITION p202503 VALUES LESS THAN (202504),
  -- ... 更多分区
  PARTITION p_future VALUES LESS THAN MAXVALUE
);
```

### 分区维护
```sql
-- 自动添加新分区
DELIMITER $$
CREATE EVENT add_monthly_partition
ON SCHEDULE EVERY 1 MONTH
DO BEGIN
  SET @sql = CONCAT('ALTER TABLE aligned_data_partitioned ADD PARTITION (PARTITION p', 
                   DATE_FORMAT(DATE_ADD(NOW(), INTERVAL 1 MONTH), '%Y%m'),
                   ' VALUES LESS THAN (', 
                   DATE_FORMAT(DATE_ADD(NOW(), INTERVAL 2 MONTH), '%Y%m'),
                   '))');
  PREPARE stmt FROM @sql;
  EXECUTE stmt;
  DEALLOCATE PREPARE stmt;
END$$
DELIMITER ;

-- 清理旧分区
DELIMITER $$
CREATE EVENT drop_old_partition
ON SCHEDULE EVERY 1 MONTH
DO BEGIN
  SET @sql = CONCAT('ALTER TABLE aligned_data_partitioned DROP PARTITION p', 
                   DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 13 MONTH), '%Y%m'));
  PREPARE stmt FROM @sql;
  EXECUTE stmt;
  DEALLOCATE PREPARE stmt;
END$$
DELIMITER ;
```

## JSON优化策略
### JSON索引
```sql
-- 为JSON字段创建虚拟列索引
ALTER TABLE aligned_data 
ADD COLUMN frequency_value DECIMAL(10,3) 
AS (JSON_UNQUOTE(JSON_EXTRACT(data_json, '$.frequency'))) VIRTUAL,
ADD INDEX idx_frequency (frequency_value);

-- 多值索引（MySQL 8.0.17+）
ALTER TABLE aligned_data 
ADD INDEX idx_json_array ((CAST(data_json->'$.tags' AS CHAR(255) ARRAY)));
```

### JSON查询优化
```sql
-- 避免在JSON字段上使用函数
-- 优化前
SELECT * FROM aligned_data 
WHERE JSON_EXTRACT(data_json, '$.frequency') > 50;

-- 优化后（使用虚拟列）
SELECT * FROM aligned_data 
WHERE frequency_value > 50;

-- 批量JSON更新
UPDATE aligned_data 
SET data_json = JSON_SET(data_json, '$.updated', NOW())
WHERE device_id = 1 AND standard_time >= '2025-01-01';
```

## 监控与维护
### 性能监控
```sql
-- 监控慢查询
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;
SET GLOBAL log_queries_not_using_indexes = 'ON';

-- 监控锁等待
SELECT 
  r.trx_id waiting_trx_id,
  r.trx_mysql_thread_id waiting_thread,
  r.trx_query waiting_query,
  b.trx_id blocking_trx_id,
  b.trx_mysql_thread_id blocking_thread,
  b.trx_query blocking_query
FROM information_schema.innodb_lock_waits w
JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id
JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id;

-- 监控缓冲池命中率
SELECT 
  (1 - (Innodb_buffer_pool_reads / Innodb_buffer_pool_read_requests)) * 100 
  AS buffer_pool_hit_rate
FROM 
  (SELECT variable_value AS Innodb_buffer_pool_reads 
   FROM performance_schema.global_status 
   WHERE variable_name = 'Innodb_buffer_pool_reads') AS reads,
  (SELECT variable_value AS Innodb_buffer_pool_read_requests 
   FROM performance_schema.global_status 
   WHERE variable_name = 'Innodb_buffer_pool_read_requests') AS requests;
```

### 定期维护
```sql
-- 表优化
OPTIMIZE TABLE aligned_data;

-- 索引统计更新
ANALYZE TABLE aligned_data;

-- 碎片整理
ALTER TABLE aligned_data ENGINE=InnoDB;

-- 检查表一致性
CHECK TABLE aligned_data;
```

## 高可用配置
### 主从复制
```ini
# 主库配置
log-bin = mysql-bin
server-id = 1
binlog-format = ROW
sync_binlog = 1
innodb_flush_log_at_trx_commit = 1

# 从库配置
server-id = 2
read-only = 1
relay-log = relay-bin
log-slave-updates = 1
```

### 故障恢复
```sql
-- 主从状态检查
SHOW MASTER STATUS;
SHOW SLAVE STATUS\G

-- 跳过复制错误
SET GLOBAL sql_slave_skip_counter = 1;
START SLAVE;

-- 重置复制
STOP SLAVE;
RESET SLAVE ALL;
CHANGE MASTER TO ...;
START SLAVE;
```

## 安全与权限
### 用户权限管理
```sql
-- 创建专用用户
CREATE USER 'pump_import'@'%' IDENTIFIED BY 'secure_password';

-- 最小权限原则
GRANT SELECT, INSERT, UPDATE ON pump_monitoring_db.aligned_data TO 'pump_import'@'%';
GRANT CREATE TEMPORARY TABLES ON pump_monitoring_db.* TO 'pump_import'@'%';
GRANT FILE ON *.* TO 'pump_import'@'%';

-- 定期轮换密码
ALTER USER 'pump_import'@'%' IDENTIFIED BY 'new_password';
```

### 连接安全
```ini
# SSL配置
ssl-ca = ca.pem
ssl-cert = server-cert.pem
ssl-key = server-key.pem
require_secure_transport = ON

# 连接限制
max_user_connections = 50
max_connections_per_hour = 1000
```

## 性能调优检查清单
- [ ] 服务器配置优化完成
- [ ] 索引策略验证通过
- [ ] 查询执行计划分析完成
- [ ] 事务大小和隔离级别适当
- [ ] 锁等待时间在可接受范围
- [ ] 分区策略实施（如需要）
- [ ] JSON优化策略应用
- [ ] 监控指标配置完成
- [ ] 定期维护任务设置
- [ ] 高可用配置验证
- [ ] 安全权限检查完成