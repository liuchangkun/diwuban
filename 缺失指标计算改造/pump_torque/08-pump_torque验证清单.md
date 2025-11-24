# pump_torque 验证清单文档

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5  
> **参考文档**: `01-pump_torque详细设计.md`

---

## 📋 目录

1. [数据库验证](#数据库验证)
2. [计算结果验证](#计算结果验证)
3. [数据质量验证](#数据质量验证)
4. [性能验证](#性能验证)
5. [代码质量验证](#代码质量验证)
6. [文档完整性验证](#文档完整性验证)

---

## 数据库验证

### 验证1.1：数据表结构验证

**验证目的**：确认pump_torque数据已正确写入fact_measurements表

**验证SQL**：
```sql
-- 检查pump_torque数据是否存在
SELECT 
    device_id,
    COUNT(*) as record_count,
    MIN(ts_bucket) as min_time,
    MAX(ts_bucket) as max_time
FROM fact_measurements
WHERE metric_id = 20  -- pump_torque
  AND device_id IN (1, 2, 3, 4, 5, 6)
GROUP BY device_id
ORDER BY device_id;
```

**预期结果**：
- 6个设备都有数据
- 每个设备的记录数 > 0
- 时间范围：2025-10-22 08:00:00 ~ 2025-10-23 07:19:37

**验证标准**：
- ✅ 所有设备都有数据
- ✅ 记录数合理（约84,000条/设备）
- ✅ 时间范围正确

---

### 验证1.2：依赖数据完整性验证

**验证目的**：确认pump_active_power和pump_speed依赖数据完整

**验证SQL**：
```sql
-- 检查依赖数据完整性
SELECT 
    fm_t.device_id,
    COUNT(DISTINCT fm_t.ts_bucket) as torque_count,
    COUNT(DISTINCT fm_p.ts_bucket) as power_count,
    COUNT(DISTINCT fm_n.ts_bucket) as speed_count
FROM fact_measurements fm_t
LEFT JOIN fact_measurements fm_p 
    ON fm_t.ts_bucket = fm_p.ts_bucket 
    AND fm_t.device_id = fm_p.device_id 
    AND fm_p.metric_id = 2  -- pump_active_power
LEFT JOIN fact_measurements fm_n 
    ON fm_t.ts_bucket = fm_n.ts_bucket 
    AND fm_t.device_id = fm_n.device_id 
    AND fm_n.metric_id = 19  -- pump_speed
WHERE fm_t.metric_id = 20  -- pump_torque
  AND fm_t.device_id IN (1, 2, 3, 4, 5, 6)
GROUP BY fm_t.device_id
ORDER BY fm_t.device_id;
```

**预期结果**：
- torque_count = power_count = speed_count

**验证标准**：
- ✅ 所有依赖数据完整对齐
- ✅ 无缺失的依赖数据

---

### 验证1.3：数据覆盖率验证

**验证目的**：确认pump_torque数据覆盖率

**验证SQL**：
```sql
-- 检查数据覆盖率
WITH expected_data AS (
    SELECT DISTINCT ts_bucket, device_id
    FROM fact_measurements
    WHERE metric_id = 2  -- pump_active_power
      AND device_id IN (1, 2, 3, 4, 5, 6)
),
actual_data AS (
    SELECT DISTINCT ts_bucket, device_id
    FROM fact_measurements
    WHERE metric_id = 20  -- pump_torque
      AND device_id IN (1, 2, 3, 4, 5, 6)
)
SELECT 
    e.device_id,
    COUNT(e.ts_bucket) as expected_count,
    COUNT(a.ts_bucket) as actual_count,
    ROUND(COUNT(a.ts_bucket)::numeric / COUNT(e.ts_bucket) * 100, 2) as coverage_rate
FROM expected_data e
LEFT JOIN actual_data a ON e.ts_bucket = a.ts_bucket AND e.device_id = a.device_id
GROUP BY e.device_id
ORDER BY e.device_id;
```

**预期结果**：
- coverage_rate > 95%

**验证标准**：
- ✅ 覆盖率 > 95%
- ✅ 所有设备覆盖率一致

---

### 验证1.4：pump_speed依赖验证

**验证目的**：验证pump_speed（新实现指标）数据可用性

**验证SQL**：
```sql
-- 检查pump_speed数据是否存在
SELECT 
    device_id,
    COUNT(*) as record_count,
    MIN(ts_bucket) as min_time,
    MAX(ts_bucket) as max_time
FROM fact_measurements
WHERE metric_id = 19  -- pump_speed
  AND device_id IN (1, 2, 3, 4, 5, 6)
GROUP BY device_id
ORDER BY device_id;
```

**预期结果**：
- 6个设备都有pump_speed数据
- 记录数与pump_torque一致

**验证标准**：
- ✅ pump_speed数据存在
- ✅ 数据量与pump_torque一致

---

## 计算结果验证

### 验证2.1：method_a计算公式验证

**验证目的**：验证method_a计算公式正确性（T = 9549.3 × P / n）

**验证SQL**：
```sql
-- 验证计算公式：T = 9549.3 × P / n
SELECT 
    fm_t.device_id,
    fm_t.ts_bucket,
    fm_p.value as pump_active_power,  -- kW
    fm_n.value as pump_speed,  -- rpm
    fm_t.value as pump_torque,  -- N·m
    ROUND((9549.3 * fm_p.value / fm_n.value)::numeric, 4) as calculated_torque,
    ROUND(ABS(fm_t.value - (9549.3 * fm_p.value / fm_n.value))::numeric, 4) as diff
FROM fact_measurements fm_t
JOIN fact_measurements fm_p 
    ON fm_t.ts_bucket = fm_p.ts_bucket 
    AND fm_t.device_id = fm_p.device_id 
    AND fm_p.metric_id = 2  -- pump_active_power
JOIN fact_measurements fm_n 
    ON fm_t.ts_bucket = fm_n.ts_bucket 
    AND fm_t.device_id = fm_n.device_id 
    AND fm_n.metric_id = 19  -- pump_speed
WHERE fm_t.metric_id = 20  -- pump_torque
  AND fm_t.device_id = 1
  AND fm_n.value > 0  -- 避免除零
ORDER BY fm_t.ts_bucket
LIMIT 10;
```

**预期结果**：
- diff < 0.1 N·m（误差 < 1%）

**验证标准**：
- ✅ 计算公式正确
- ✅ 误差在可接受范围内

---

### 验证2.2：范围验证

**验证目的**：验证pump_torque值在合理范围内

**验证SQL**：
```sql
-- 检查数据范围
SELECT
    device_id,
    COUNT(*) as total_count,
    SUM(CASE WHEN value >= 0 AND value <= 10000 THEN 1 ELSE 0 END) as valid_count,
    SUM(CASE WHEN value < 0 OR value > 10000 THEN 1 ELSE 0 END) as invalid_count,
    ROUND(MIN(value)::numeric, 2) as min_value,
    ROUND(MAX(value)::numeric, 2) as max_value,
    ROUND(AVG(value)::numeric, 2) as avg_value
FROM fact_measurements
WHERE metric_id = 20  -- pump_torque
  AND device_id IN (1, 2, 3, 4, 5, 6)
GROUP BY device_id
ORDER BY device_id;
```

**预期结果**：
- invalid_count = 0
- min_value >= 0 N·m
- max_value <= 10000 N·m

**验证标准**：
- ✅ 所有值在0-10000 N·m范围内
- ✅ 无异常值

---

### 验证2.3：物理关系验证

**验证目的**：验证扭矩与功率、转速的物理关系

**验证SQL**：
```sql
-- 验证物理关系：T = 9549.3 × P / n
SELECT
    fm_t.device_id,
    COUNT(*) as total_count,
    SUM(CASE WHEN ABS(fm_t.value - (9549.3 * fm_p.value / fm_n.value)) / fm_t.value < 0.01 THEN 1 ELSE 0 END) as valid_count,
    SUM(CASE WHEN ABS(fm_t.value - (9549.3 * fm_p.value / fm_n.value)) / fm_t.value >= 0.01 THEN 1 ELSE 0 END) as invalid_count,
    ROUND((SUM(CASE WHEN ABS(fm_t.value - (9549.3 * fm_p.value / fm_n.value)) / fm_t.value < 0.01 THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100), 2) as valid_rate
FROM fact_measurements fm_t
JOIN fact_measurements fm_p
    ON fm_t.ts_bucket = fm_p.ts_bucket
    AND fm_t.device_id = fm_p.device_id
    AND fm_p.metric_id = 2
JOIN fact_measurements fm_n
    ON fm_t.ts_bucket = fm_n.ts_bucket
    AND fm_t.device_id = fm_n.device_id
    AND fm_n.metric_id = 19
WHERE fm_t.metric_id = 20
  AND fm_t.device_id IN (1, 2, 3, 4, 5, 6)
  AND fm_n.value > 0
  AND fm_t.value > 0
GROUP BY fm_t.device_id
ORDER BY fm_t.device_id;
```

**预期结果**：
- valid_rate > 99%

**验证标准**：
- ✅ 物理关系合理（误差 < 1%的比例 > 99%）

---

### 验证2.4：方法一致性验证

**验证目的**：验证method_a和method_b计算结果的一致性（如果两种方法都可用）

**验证SQL**：
```sql
-- 对比两种方法的计算结果
WITH method_a_result AS (
    SELECT
        fm_t.ts_bucket,
        fm_t.device_id,
        fm_t.value as torque_a,
        9549.3 * fm_p.value / fm_n.value as calculated_a
    FROM fact_measurements fm_t
    JOIN fact_measurements fm_p ON fm_t.ts_bucket = fm_p.ts_bucket AND fm_t.device_id = fm_p.device_id AND fm_p.metric_id = 2
    JOIN fact_measurements fm_n ON fm_t.ts_bucket = fm_n.ts_bucket AND fm_t.device_id = fm_n.device_id AND fm_n.metric_id = 19
    WHERE fm_t.metric_id = 20 AND fm_t.device_id = 1 AND fm_n.value > 0
),
method_b_result AS (
    SELECT
        fm_t.ts_bucket,
        fm_t.device_id,
        1000 * 9.81 * (fm_q.value / 3600) * fm_h.value / (2 * 3.14159 * fm_n.value / 60) as calculated_b
    FROM fact_measurements fm_t
    JOIN fact_measurements fm_q ON fm_t.ts_bucket = fm_q.ts_bucket AND fm_t.device_id = fm_q.device_id AND fm_q.metric_id = 18
    JOIN fact_measurements fm_h ON fm_t.ts_bucket = fm_h.ts_bucket AND fm_t.device_id = fm_h.device_id AND fm_h.metric_id = 17
    JOIN fact_measurements fm_n ON fm_t.ts_bucket = fm_n.ts_bucket AND fm_t.device_id = fm_n.device_id AND fm_n.metric_id = 19
    WHERE fm_t.metric_id = 20 AND fm_t.device_id = 1 AND fm_n.value > 0
)
SELECT
    a.device_id,
    COUNT(*) as total_count,
    AVG(ABS(a.calculated_a - b.calculated_b) / a.calculated_a) as avg_diff_rate
FROM method_a_result a
JOIN method_b_result b ON a.ts_bucket = b.ts_bucket AND a.device_id = b.device_id
GROUP BY a.device_id;
```

**预期结果**：
- avg_diff_rate < 0.10（平均差异 < 10%，考虑到效率损失）

**验证标准**：
- ✅ 两种方法结果基本一致

---

## 数据质量验证

### 验证3.1：NULL值检查

**验证目的**：确认无NULL值

**验证SQL**：
```sql
-- 检查NULL值
SELECT
    device_id,
    COUNT(*) as total_count,
    SUM(CASE WHEN value IS NULL THEN 1 ELSE 0 END) as null_count
FROM fact_measurements
WHERE metric_id = 20  -- pump_torque
  AND device_id IN (1, 2, 3, 4, 5, 6)
GROUP BY device_id
ORDER BY device_id;
```

**预期结果**：
- null_count = 0

**验证标准**：
- ✅ 无NULL值

---

### 验证3.2：重复数据检查

**验证目的**：确认无重复数据

**验证SQL**：
```sql
-- 检查重复数据
SELECT
    ts_bucket,
    device_id,
    COUNT(*) as duplicate_count
FROM fact_measurements
WHERE metric_id = 20  -- pump_torque
  AND device_id IN (1, 2, 3, 4, 5, 6)
GROUP BY ts_bucket, device_id
HAVING COUNT(*) > 1;
```

**预期结果**：
- 无结果（无重复数据）

**验证标准**：
- ✅ 无重复数据

---

### 验证3.3：数据一致性检查

**验证目的**：验证数据一致性

**验证SQL**：
```sql
-- 检查数据一致性（同一功率和转速应产生相同扭矩）
SELECT
    fm_p.value as pump_active_power,
    fm_n.value as pump_speed,
    COUNT(DISTINCT fm_t.value) as distinct_torque_count,
    MIN(fm_t.value) as min_torque,
    MAX(fm_t.value) as max_torque
FROM fact_measurements fm_t
JOIN fact_measurements fm_p
    ON fm_t.ts_bucket = fm_p.ts_bucket
    AND fm_t.device_id = fm_p.device_id
    AND fm_p.metric_id = 2
JOIN fact_measurements fm_n
    ON fm_t.ts_bucket = fm_n.ts_bucket
    AND fm_t.device_id = fm_n.device_id
    AND fm_n.metric_id = 19
WHERE fm_t.metric_id = 20
  AND fm_t.device_id = 1
GROUP BY fm_p.value, fm_n.value
HAVING COUNT(DISTINCT fm_t.value) > 1
LIMIT 10;
```

**预期结果**：
- 无结果或差异极小（< 0.1 N·m）

**验证标准**：
- ✅ 数据一致性良好

---

## 性能验证

### 验证4.1：计算性能验证

**验证命令**：
```bash
# 运行性能测试
pytest tests/performance/metrics/pump_torque/test_pump_torque_performance.py::TestPumpTorquePerformance::test_large_dataset_performance -v -s
```

**预期结果**：
- 总耗时 < 60秒
- 吞吐量 > 8000条/秒

**验证标准**：
- ✅ 性能达标

---

### 验证4.2：内存使用验证

**验证命令**：
```bash
# 运行内存测试
pytest tests/performance/metrics/pump_torque/test_pump_torque_performance.py::TestPumpTorquePerformance::test_memory_usage -v -s
```

**预期结果**：
- 内存增量 < 2GB

**验证标准**：
- ✅ 内存使用合理

---

### 验证4.3：数据库写入性能验证

**验证SQL**：
```sql
-- 检查写入性能（通过时间戳分布）
SELECT
    DATE_TRUNC('minute', ts_bucket) as minute_bucket,
    COUNT(*) as records_per_minute
FROM fact_measurements
WHERE metric_id = 20  -- pump_torque
  AND device_id IN (1, 2, 3, 4, 5, 6)
GROUP BY DATE_TRUNC('minute', ts_bucket)
ORDER BY minute_bucket
LIMIT 10;
```

**预期结果**：
- 每分钟写入记录数稳定（约360条，6设备×60秒）

**验证标准**：
- ✅ 写入速度稳定

---

## 代码质量验证

### 验证5.1：单元测试覆盖率

**验证命令**：
```bash
# 运行单元测试并生成覆盖率报告
pytest tests/unit/metrics/pump_torque/ --cov=src/metrics/pump_torque --cov-report=term-missing
```

**预期结果**：
- 覆盖率 > 95%

**验证标准**：
- ✅ 单元测试覆盖率 > 95%

---

### 验证5.2：代码规范检查

**验证命令**：
```bash
# 运行pylint检查
pylint src/metrics/pump_torque/ --rcfile=.pylintrc

# 运行flake8检查
flake8 src/metrics/pump_torque/ --config=.flake8
```

**预期结果**：
- pylint评分 > 9.0
- flake8无错误

**验证标准**：
- ✅ 代码符合规范

---

### 验证5.3：类型检查

**验证命令**：
```bash
# 运行mypy类型检查
mypy src/metrics/pump_torque/ --config-file=mypy.ini
```

**预期结果**：
- 无类型错误

**验证标准**：
- ✅ 类型注解正确

---

## 文档完整性验证

### 验证6.1：文档完整性检查

**验证清单**：
- [ ] 01-pump_torque详细设计.md存在且完整
- [ ] 02-pump_torque数据库设计.md存在且完整
- [ ] 03-pump_torque代码结构.md存在且完整
- [ ] 04-pump_torque重构完整检查清单.md存在且完整
- [ ] 05-pump_torque实施计划.md存在且完整
- [ ] 06-pump_torque测试用例.md存在且完整
- [ ] 07-pump_torque测试脚本.md存在且完整
- [ ] 08-pump_torque验证清单.md存在且完整

**验证标准**：
- ✅ 所有文档存在
- ✅ 所有文档内容完整

---

## 📊 验证清单统计

| 验证类别 | 验证项数 | 验证方法 |
|----------|---------|---------|
| 数据库验证 | 4 | SQL查询 |
| 计算结果验证 | 4 | SQL查询 |
| 数据质量验证 | 3 | SQL查询 |
| 性能验证 | 3 | pytest + SQL |
| 代码质量验证 | 3 | pytest + pylint + mypy |
| 文档完整性验证 | 1 | 文件检查 |
| **总计** | **18** | **多种方法** |

---

## ✅ 总体验收标准

**数据库**：
- [ ] 所有设备数据完整
- [ ] 依赖数据完整对齐（pump_active_power, pump_speed）
- [ ] pump_speed依赖可用（新实现指标）
- [ ] 数据覆盖率 > 95%

**计算结果**：
- [ ] method_a计算公式正确（T = 9549.3 × P / n）
- [ ] 所有值在合理范围内（0-10000 N·m）
- [ ] 物理关系合理（误差 < 1%）
- [ ] 两种方法结果基本一致（如果都可用）

**数据质量**：
- [ ] 无NULL值
- [ ] 无重复数据
- [ ] 数据一致性良好

**性能**：
- [ ] 计算性能达标（< 60秒）
- [ ] 内存使用合理（< 2GB）
- [ ] 写入速度稳定

**代码质量**：
- [ ] 单元测试覆盖率 > 95%
- [ ] 代码符合规范
- [ ] 类型注解正确

**文档**：
- [ ] 所有文档完整

**特殊验证**：
- [ ] pump_speed依赖验证通过（新实现指标）
- [ ] 两种计算方法都可用且结果一致

---

**文档结束**

