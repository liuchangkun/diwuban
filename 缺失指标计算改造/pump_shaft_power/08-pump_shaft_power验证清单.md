# pump_shaft_power 验证清单

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5  
> **参考文档**: `01-pump_shaft_power详细设计.md`, `06-pump_shaft_power测试用例.md`

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

### 验证1：pump_active_power数据存在性

**验证目的**：验证pump_active_power数据存在且完整

**验证SQL**：
```sql
SELECT 
    device_id,
    COUNT(*) as record_count,
    MIN(ts_bucket) as min_time,
    MAX(ts_bucket) as max_time,
    MIN(value) as min_value,
    MAX(value) as max_value,
    AVG(value) as avg_value
FROM fact_measurements
WHERE metric_id = 2  -- pump_active_power
  AND device_id IN (1,2,3,4,5,6)
  AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
GROUP BY device_id
ORDER BY device_id;
```

**预期结果**：
- 所有设备（1-6）都有数据
- 每个设备记录数 > 50,000
- 值范围：0-500 kW

**验证标准**：
- [ ] 所有设备都有pump_active_power数据
- [ ] 数据时间范围正确
- [ ] 数据值在合理范围

---

### 验证2：device_rated_params参数完整性

**验证目的**：验证device_rated_params表有必需参数

**验证SQL**：
```sql
SELECT 
    device_id,
    param_key,
    param_value
FROM device_rated_params
WHERE device_id IN (1,2,3,4,5,6)
  AND param_key IN ('eta_motor', 'eta_vfd')
ORDER BY device_id, param_key;
```

**预期结果**：
- 每个设备有2个参数（eta_motor, eta_vfd）
- eta_motor ≈ 0.92
- eta_vfd ≈ 0.97

**验证标准**：
- [ ] 所有设备都有eta_motor和eta_vfd参数
- [ ] 参数值在合理范围（0.8-1.0）

---

### 验证3：mv_device_running_1s可用性

**验证目的**：验证mv_device_running_1s物化视图可用

**验证SQL**：
```sql
SELECT 
    device_id,
    COUNT(*) as record_count,
    SUM(CASE WHEN running = 1 THEN 1 ELSE 0 END) as running_count,
    SUM(CASE WHEN running = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as running_ratio
FROM mv_device_running_1s
WHERE device_id IN (1,2,3,4,5,6)
  AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
GROUP BY device_id
ORDER BY device_id;
```

**预期结果**：
- 所有设备都有running状态数据
- running_ratio > 50%

**验证标准**：
- [ ] mv_device_running_1s可用
- [ ] 所有设备都有running状态

---

## 计算结果验证

### 验证4：pump_shaft_power结果写入

**验证目的**：验证pump_shaft_power计算结果已写入fact_measurements

**验证SQL**：
```sql
SELECT 
    device_id,
    COUNT(*) as record_count,
    MIN(value) as min_value,
    MAX(value) as max_value,
    AVG(value) as avg_value,
    STDDEV(value) as stddev_value
FROM fact_measurements
WHERE metric_id = 66  -- pump_shaft_power
  AND device_id IN (1,2,3,4,5,6)
  AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
GROUP BY device_id
ORDER BY device_id;
```

**预期结果**：
- 所有设备都有pump_shaft_power数据
- 值范围：0-600 kW

**验证标准**：
- [ ] pump_shaft_power数据已写入
- [ ] 数据值在合理范围

---

### 验证5：计算正确性验证

**验证目的**：验证pump_shaft_power计算公式正确

**验证SQL**：
```sql
SELECT 
    fm_active.ts_bucket,
    fm_active.device_id,
    fm_active.value as pump_active_power,
    fm_shaft.value as pump_shaft_power,
    drp_motor.param_value::float as eta_motor,
    drp_vfd.param_value::float as eta_vfd,
    fm_active.value / (drp_motor.param_value::float * drp_vfd.param_value::float) as expected_shaft_power,
    ABS(fm_shaft.value - fm_active.value / (drp_motor.param_value::float * drp_vfd.param_value::float)) / 
        (fm_active.value / (drp_motor.param_value::float * drp_vfd.param_value::float)) as diff_ratio
FROM fact_measurements fm_active
JOIN fact_measurements fm_shaft 
    ON fm_active.ts_bucket = fm_shaft.ts_bucket 
    AND fm_active.device_id = fm_shaft.device_id
JOIN device_rated_params drp_motor 
    ON fm_active.device_id = drp_motor.device_id 
    AND drp_motor.param_key = 'eta_motor'
JOIN device_rated_params drp_vfd 
    ON fm_active.device_id = drp_vfd.device_id 
    AND drp_vfd.param_key = 'eta_vfd'
WHERE fm_active.metric_id = 2  -- pump_active_power
  AND fm_shaft.metric_id = 66  -- pump_shaft_power
  AND fm_active.device_id IN (1,2,3,4,5,6)
  AND fm_active.value > 0
LIMIT 100;
```

**预期结果**：
- diff_ratio < 0.01（差异<1%）

**验证标准**：
- [ ] 计算结果与预期一致
- [ ] 差异在允许范围内

---

### 验证6：pump_shaft_power与pump_active_power的关系

**验证目的**：验证pump_shaft_power与pump_active_power的物理关系

**验证SQL**：
```sql
SELECT
    COUNT(*) as total_count,
    SUM(CASE WHEN fm_shaft.value >= fm_active.value THEN 1 ELSE 0 END) as valid_count,
    SUM(CASE WHEN fm_shaft.value >= fm_active.value THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as valid_ratio
FROM fact_measurements fm_active
JOIN fact_measurements fm_shaft
    ON fm_active.ts_bucket = fm_shaft.ts_bucket
    AND fm_active.device_id = fm_shaft.device_id
WHERE fm_active.metric_id = 2  -- pump_active_power
  AND fm_shaft.metric_id = 66  -- pump_shaft_power
  AND fm_active.device_id IN (1,2,3,4,5,6)
  AND fm_active.value > 0;
```

**预期结果**：
- valid_ratio > 99%（P_shaft ≥ P_active，因为效率<1）

**验证标准**：
- [ ] 物理关系验证通过率 > 99%

---

## 数据质量验证

### 验证7：pump_shaft_power数据完整性

**验证目的**：验证pump_shaft_power数据无缺失

**验证SQL**：
```sql
SELECT
    'pump_active_power' as metric,
    device_id,
    COUNT(*) as record_count
FROM fact_measurements
WHERE metric_id = 2
  AND device_id IN (1,2,3,4,5,6)
  AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
GROUP BY device_id

UNION ALL

SELECT
    'pump_shaft_power' as metric,
    device_id,
    COUNT(*) as record_count
FROM fact_measurements
WHERE metric_id = 66
  AND device_id IN (1,2,3,4,5,6)
  AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
GROUP BY device_id

ORDER BY device_id, metric;
```

**预期结果**：
- pump_shaft_power记录数 ≈ pump_active_power记录数（考虑running=1过滤）

**验证标准**：
- [ ] 数据完整性 > 95%

---

### 验证8：pump_shaft_power数据质量分布

**验证目的**：验证pump_shaft_power数据质量标记正确

**验证SQL**：
```sql
SELECT
    device_id,
    quality,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY device_id) as percentage
FROM fact_measurements
WHERE metric_id = 66  -- pump_shaft_power
  AND device_id IN (1,2,3,4,5,6)
  AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
GROUP BY device_id, quality
ORDER BY device_id, quality;
```

**预期结果**：
- quality='valid'的比例 > 90%
- quality='out_of_range'的比例 < 5%

**验证标准**：
- [ ] 有效数据比例 > 90%
- [ ] 异常数据比例 < 10%

---

### 验证9：pump_shaft_power异常值检测

**验证目的**：检测pump_shaft_power异常值

**验证SQL**：
```sql
WITH power_changes AS (
    SELECT
        device_id,
        ts_bucket,
        value as pump_shaft_power,
        LAG(value) OVER (PARTITION BY device_id ORDER BY ts_bucket) as prev_power,
        value - LAG(value) OVER (PARTITION BY device_id ORDER BY ts_bucket) as power_change,
        ABS(value - LAG(value) OVER (PARTITION BY device_id ORDER BY ts_bucket)) as abs_power_change
    FROM fact_measurements
    WHERE metric_id = 66  -- pump_shaft_power
      AND device_id IN (1,2,3,4,5,6)
      AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
)
SELECT
    device_id,
    COUNT(*) as total_count,
    SUM(CASE WHEN abs_power_change > 50 THEN 1 ELSE 0 END) as outlier_count,
    SUM(CASE WHEN abs_power_change > 50 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as outlier_ratio,
    MAX(abs_power_change) as max_change
FROM power_changes
WHERE prev_power IS NOT NULL
GROUP BY device_id;
```

**预期结果**：
- outlier_ratio < 1%（异常值比例<1%）
- max_change < 100 kW/s

**验证标准**：
- [ ] 异常值比例 < 1%
- [ ] 最大变化率合理

---

## 性能验证

### 验证10：计算性能

**验证目的**：验证计算性能符合要求

**验证命令**：
```bash
pytest tests/performance/metrics/pump_shaft_power/test_pump_shaft_power_performance.py::TestPumpShaftPowerPerformance::test_large_dataset_performance -v
```

**预期结果**：
- 总耗时 < 60秒
- 吞吐量 > 8000条/秒

**验证标准**：
- [ ] 计算耗时符合要求
- [ ] 吞吐量符合要求

---

### 验证11：批量写入性能

**验证目的**：验证批量写入性能符合要求

**验证SQL**：
```sql
SELECT
    metric_key,
    device_id,
    start_time,
    end_time,
    EXTRACT(EPOCH FROM (end_time - start_time)) as duration_seconds,
    records_processed,
    records_processed / EXTRACT(EPOCH FROM (end_time - start_time)) as throughput
FROM calculation_logs
WHERE metric_key = 'pump_shaft_power'
  AND start_time >= '2025-10-22 08:00:00'
ORDER BY start_time DESC
LIMIT 10;
```

**预期结果**：
- throughput > 1000条/秒

**验证标准**：
- [ ] 写入速度 > 1000条/秒

---

### 验证12：内存使用

**验证目的**：验证内存使用合理

**验证命令**：
```bash
pytest tests/performance/metrics/pump_shaft_power/test_pump_shaft_power_performance.py::TestPumpShaftPowerPerformance::test_memory_usage -v
```

**预期结果**：
- 内存增量 < 2GB

**验证标准**：
- [ ] 内存使用 < 2GB

---

## 代码质量验证

### 验证13：代码规范检查

**验证目的**：验证代码符合PEP 8规范

**验证命令**：
```bash
pylint app/services/calculation/metrics/pump_shaft_power/ --rcfile=.pylintrc
black --check app/services/calculation/metrics/pump_shaft_power/
isort --check-only app/services/calculation/metrics/pump_shaft_power/
```

**预期结果**：
- pylint评分 > 9.0
- black检查通过
- isort检查通过

**验证标准**：
- [ ] pylint评分 > 9.0
- [ ] black格式化通过
- [ ] isort排序通过

---

### 验证14：测试覆盖率

**验证目的**：验证测试覆盖率符合要求

**验证命令**：
```bash
pytest tests/unit/metrics/pump_shaft_power/ tests/integration/metrics/pump_shaft_power/ \
    --cov=app/services/calculation/metrics/pump_shaft_power \
    --cov-report=term-missing \
    --cov-fail-under=90
```

**预期结果**：
- 覆盖率 > 90%

**验证标准**：
- [ ] 单元测试覆盖率 > 95%
- [ ] 集成测试覆盖率 > 90%
- [ ] 总体覆盖率 > 90%

---

### 验证15：文档字符串完整性

**验证目的**：验证所有类和方法有文档字符串

**验证命令**：
```bash
pydocstyle app/services/calculation/metrics/pump_shaft_power/
```

**预期结果**：
- 所有类和方法都有文档字符串

**验证标准**：
- [ ] 所有类有文档字符串
- [ ] 所有公共方法有文档字符串
- [ ] 文档字符串格式正确

---

## 文档完整性验证

### 验证16：文档完整性

**验证目的**：验证所有文档已完成

**验证清单**：
- [ ] 01-pump_shaft_power详细设计.md（已完成）
- [ ] 02-pump_shaft_power实施计划.md（已完成）
- [ ] 03-pump_shaft_power重构任务跟踪.md（已完成）
- [ ] 04-pump_shaft_power重构完整检查清单.md（已完成）
- [ ] 05-任务完成追踪表.md（已完成）
- [ ] 06-pump_shaft_power测试用例.md（已完成）
- [ ] 07-pump_shaft_power测试脚本.md（已完成）
- [ ] 08-pump_shaft_power验证清单.md（已完成）

**验证标准**：
- [ ] 所有8个文档已完成
- [ ] 文档内容完整
- [ ] 文档格式正确

---

## 📊 验证清单统计

| 验证类型 | 验证项数 | 验证方法 |
|----------|---------|---------|
| 数据库验证 | 3 | SQL查询 |
| 计算结果验证 | 3 | SQL查询 |
| 数据质量验证 | 3 | SQL查询 |
| 性能验证 | 3 | pytest + SQL |
| 代码质量验证 | 3 | pylint + pytest |
| 文档完整性验证 | 1 | 手动检查 |
| **总计** | **16** | **混合方法** |

---

## ✅ 总体验收标准

**数据库准备**：
- [ ] pump_active_power数据存在且完整
- [ ] device_rated_params参数完整
- [ ] mv_device_running_1s可用

**计算结果**：
- [ ] pump_shaft_power计算结果已写入
- [ ] 计算结果正确性验证通过
- [ ] 物理关系验证通过

**数据质量**：
- [ ] 数据完整性 > 95%
- [ ] 有效数据比例 > 90%
- [ ] 异常值比例 < 1%

**性能指标**：
- [ ] 计算耗时 < 60秒
- [ ] 批量写入速度 > 1000条/秒
- [ ] 内存使用 < 2GB

**代码质量**：
- [ ] pylint评分 > 9.0
- [ ] 测试覆盖率 > 90%
- [ ] 文档字符串完整

**文档完整性**：
- [ ] 所有8个文档已完成

---

**文档结束**

