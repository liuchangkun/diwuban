# pump_speed 验证清单文档

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5  
> **参考文档**: `06-pump_speed测试用例.md`, `07-pump_speed测试脚本.md`

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

### 验证1：pump_frequency数据存在性

**验证目的**：确认pump_frequency数据存在且完整

**验证SQL**：
```sql
-- 检查pump_frequency数据量
SELECT 
    device_id,
    COUNT(*) as record_count,
    MIN(ts_bucket) as min_time,
    MAX(ts_bucket) as max_time,
    MIN(value) as min_value,
    MAX(value) as max_value,
    AVG(value) as avg_value
FROM fact_measurements
WHERE metric_id = 1  -- pump_frequency
  AND device_id IN (1,2,3,4,5,6)
  AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
GROUP BY device_id
ORDER BY device_id;
```

**预期结果**：
- 6个设备都有数据
- 每个设备记录数 > 10000
- 频率值在0-60 Hz范围内

**验证标准**：
- [ ] 所有设备都有数据
- [ ] 数据量符合预期
- [ ] 数据值在合理范围

---

### 验证2：device_rated_params参数完整性

**验证目的**：确认设备参数已正确配置

**验证SQL**：
```sql
-- 检查device_rated_params参数
SELECT 
    device_id,
    param_key,
    value_numeric,
    value_text
FROM device_rated_params
WHERE device_id IN (1,2,3,4,5,6)
ORDER BY device_id, param_key;
```

**预期结果**：
- 每个设备有7个参数
- 参数包括：rated_power, rated_voltage, rated_current, pole_pairs, slip, L_offset, pipe_diameter

**验证标准**：
- [ ] 所有设备都有参数
- [ ] 参数数量正确（7个/设备）
- [ ] 参数值合理

---

### 验证3：calculation_parameters参数完整性

**验证目的**：确认计算参数已正确配置

**验证SQL**：
```sql
-- 检查calculation_parameters参数
SELECT 
    method_id,
    param_key,
    param_value,
    description
FROM calculation_parameters
WHERE metric_key = 'pump_speed'
ORDER BY method_id, param_key;
```

**预期结果**：
- method_a有2个参数（f_ref, n_ref）
- method_b有2个参数（pole_pairs, slip）
- method_c有2个参数（calibration_a, calibration_b）
- validation有4个参数（min_speed, max_speed, physics_tolerance, max_speed_change_rate）

**验证标准**：
- [ ] 所有方法都有参数
- [ ] 参数数量正确
- [ ] 参数值合理

---

### 验证4：mv_device_running_1s物化视图可用性

**验证目的**：确认运行状态物化视图可用

**验证SQL**：
```sql
-- 检查mv_device_running_1s数据
SELECT 
    device_id,
    COUNT(*) as record_count,
    SUM(CASE WHEN running = 1 THEN 1 ELSE 0 END) as running_count,
    SUM(CASE WHEN running = 0 THEN 1 ELSE 0 END) as stopped_count
FROM mv_device_running_1s
WHERE device_id IN (1,2,3,4,5,6)
  AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
GROUP BY device_id
ORDER BY device_id;
```

**预期结果**：
- 6个设备都有数据
- running=1的记录数 > 0

**验证标准**：
- [ ] 所有设备都有运行状态数据
- [ ] running标志正确

---

## 计算结果验证

### 验证5：pump_speed计算结果写入

**验证目的**：确认pump_speed计算结果已写入数据库

**验证SQL**：
```sql
-- 检查pump_speed计算结果
SELECT 
    device_id,
    COUNT(*) as record_count,
    MIN(ts_bucket) as min_time,
    MAX(ts_bucket) as max_time,
    MIN(value) as min_value,
    MAX(value) as max_value,
    AVG(value) as avg_value,
    STDDEV(value) as stddev_value
FROM fact_measurements
WHERE metric_id = 19  -- pump_speed
  AND device_id IN (1,2,3,4,5,6)
  AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
GROUP BY device_id
ORDER BY device_id;
```

**预期结果**：
- 6个设备都有计算结果
- 每个设备记录数 > 0
- 转速值在0-3000 rpm范围内

**验证标准**：
- [ ] 所有设备都有计算结果
- [ ] 数据量符合预期
- [ ] 数据值在合理范围

---

### 验证6：pump_speed计算结果正确性

**验证目的**：验证pump_speed计算公式正确

**验证SQL**：
```sql
-- 验证method_a计算正确性（n = (f / f_ref) × n_ref）
SELECT 
    fm_freq.device_id,
    fm_freq.ts_bucket,
    fm_freq.value as pump_frequency,
    fm_speed.value as pump_speed,
    (fm_freq.value / 50.0) * 1500.0 as expected_speed,
    ABS(fm_speed.value - (fm_freq.value / 50.0) * 1500.0) as diff,
    ABS(fm_speed.value - (fm_freq.value / 50.0) * 1500.0) / ((fm_freq.value / 50.0) * 1500.0) as diff_ratio
FROM fact_measurements fm_freq
JOIN fact_measurements fm_speed 
    ON fm_freq.device_id = fm_speed.device_id 
    AND fm_freq.ts_bucket = fm_speed.ts_bucket
WHERE fm_freq.metric_id = 1  -- pump_frequency
  AND fm_speed.metric_id = 19  -- pump_speed
  AND fm_freq.device_id IN (1,2,3,4,5,6)
  AND fm_freq.ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-22 09:00:00'
ORDER BY fm_freq.device_id, fm_freq.ts_bucket
LIMIT 100;
```

**预期结果**：
- diff_ratio < 0.01（差异<1%）

**验证标准**：
- [ ] 计算结果与预期一致
- [ ] 差异在允许范围内

---

### 验证7：pump_speed与pump_frequency的关系

**验证目的**：验证pump_speed与pump_frequency的物理关系（n ≈ 30×f）

**验证SQL**：
```sql
-- 验证物理关系
SELECT
    fm_freq.device_id,
    COUNT(*) as total_count,
    SUM(CASE WHEN ABS(fm_speed.value - 30.0 * fm_freq.value) / (30.0 * fm_freq.value) < 0.1 THEN 1 ELSE 0 END) as valid_count,
    SUM(CASE WHEN ABS(fm_speed.value - 30.0 * fm_freq.value) / (30.0 * fm_freq.value) < 0.1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as valid_ratio
FROM fact_measurements fm_freq
JOIN fact_measurements fm_speed
    ON fm_freq.device_id = fm_speed.device_id
    AND fm_freq.ts_bucket = fm_speed.ts_bucket
WHERE fm_freq.metric_id = 1  -- pump_frequency
  AND fm_speed.metric_id = 19  -- pump_speed
  AND fm_freq.device_id IN (1,2,3,4,5,6)
  AND fm_freq.ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
  AND fm_freq.value > 0  -- 排除零频率
GROUP BY fm_freq.device_id
ORDER BY fm_freq.device_id;
```

**预期结果**：
- valid_ratio > 90%（90%以上的数据符合物理关系）

**验证标准**：
- [ ] 物理关系验证通过率 > 90%

---

## 数据质量验证

### 验证8：pump_speed数据完整性

**验证目的**：验证pump_speed数据无缺失

**验证SQL**：
```sql
-- 检查数据完整性（与pump_frequency对比）
SELECT
    'pump_frequency' as metric,
    device_id,
    COUNT(*) as record_count
FROM fact_measurements
WHERE metric_id = 1
  AND device_id IN (1,2,3,4,5,6)
  AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
GROUP BY device_id

UNION ALL

SELECT
    'pump_speed' as metric,
    device_id,
    COUNT(*) as record_count
FROM fact_measurements
WHERE metric_id = 19
  AND device_id IN (1,2,3,4,5,6)
  AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
GROUP BY device_id

ORDER BY device_id, metric;
```

**预期结果**：
- pump_speed记录数 ≈ pump_frequency记录数（考虑running=1过滤）

**验证标准**：
- [ ] 数据完整性 > 95%

---

### 验证9：pump_speed数据质量分布

**验证目的**：验证pump_speed数据质量标记正确

**验证SQL**：
```sql
-- 检查数据质量分布（需要quality列）
SELECT
    device_id,
    quality,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY device_id) as percentage
FROM fact_measurements
WHERE metric_id = 19  -- pump_speed
  AND device_id IN (1,2,3,4,5,6)
  AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
GROUP BY device_id, quality
ORDER BY device_id, quality;
```

**预期结果**：
- quality='valid'的比例 > 90%
- quality='out_of_range'的比例 < 5%
- quality='physics_violation'的比例 < 5%

**验证标准**：
- [ ] 有效数据比例 > 90%
- [ ] 异常数据比例 < 10%

---

### 验证10：pump_speed异常值检测

**验证目的**：检测pump_speed异常值

**验证SQL**：
```sql
-- 检测异常值（转速突变）
WITH speed_changes AS (
    SELECT
        device_id,
        ts_bucket,
        value as pump_speed,
        LAG(value) OVER (PARTITION BY device_id ORDER BY ts_bucket) as prev_speed,
        value - LAG(value) OVER (PARTITION BY device_id ORDER BY ts_bucket) as speed_change,
        ABS(value - LAG(value) OVER (PARTITION BY device_id ORDER BY ts_bucket)) as abs_speed_change
    FROM fact_measurements
    WHERE metric_id = 19  -- pump_speed
      AND device_id IN (1,2,3,4,5,6)
      AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
)
SELECT
    device_id,
    COUNT(*) as total_count,
    SUM(CASE WHEN abs_speed_change > 100 THEN 1 ELSE 0 END) as outlier_count,
    SUM(CASE WHEN abs_speed_change > 100 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as outlier_ratio,
    MAX(abs_speed_change) as max_change
FROM speed_changes
WHERE prev_speed IS NOT NULL
GROUP BY device_id
ORDER BY device_id;
```

**预期结果**：
- outlier_ratio < 1%（异常值比例<1%）
- max_change < 500 rpm/s

**验证标准**：
- [ ] 异常值比例 < 1%
- [ ] 最大变化率合理

---

## 性能验证

### 验证11：计算性能

**验证目的**：验证计算性能符合要求

**验证方法**：
1. 运行性能测试脚本
2. 记录耗时和吞吐量

**验证命令**：
```bash
pytest tests/performance/metrics/pump_speed/test_pump_speed_performance.py::TestPumpSpeedPerformance::test_large_dataset_performance -v
```

**预期结果**：
- 总耗时 < 60秒
- 吞吐量 > 8000条/秒

**验证标准**：
- [ ] 计算耗时符合要求
- [ ] 吞吐量符合要求

---

### 验证12：批量写入性能

**验证目的**：验证批量写入性能符合要求

**验证SQL**：
```sql
-- 检查写入性能（通过日志表）
SELECT
    metric_key,
    device_id,
    start_time,
    end_time,
    EXTRACT(EPOCH FROM (end_time - start_time)) as duration_seconds,
    records_processed,
    records_processed / EXTRACT(EPOCH FROM (end_time - start_time)) as throughput
FROM calculation_logs
WHERE metric_key = 'pump_speed'
  AND start_time >= '2025-10-22 08:00:00'
ORDER BY start_time DESC
LIMIT 10;
```

**预期结果**：
- throughput > 1000条/秒

**验证标准**：
- [ ] 写入速度 > 1000条/秒

---

### 验证13：内存使用

**验证目的**：验证内存使用合理

**验证方法**：
1. 运行内存测试脚本
2. 记录内存使用

**验证命令**：
```bash
pytest tests/performance/metrics/pump_speed/test_pump_speed_performance.py::TestPumpSpeedPerformance::test_memory_usage -v
```

**预期结果**：
- 内存增量 < 2GB

**验证标准**：
- [ ] 内存使用 < 2GB

---

## 代码质量验证

### 验证14：代码规范检查

**验证目的**：验证代码符合PEP 8规范

**验证命令**：
```bash
# pylint检查
pylint app/services/calculation/metrics/pump_speed/ --rcfile=.pylintrc

# black格式化检查
black --check app/services/calculation/metrics/pump_speed/

# isort导入排序检查
isort --check-only app/services/calculation/metrics/pump_speed/
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

### 验证15：测试覆盖率

**验证目的**：验证测试覆盖率符合要求

**验证命令**：
```bash
pytest tests/unit/metrics/pump_speed/ tests/integration/metrics/pump_speed/ \
    --cov=app/services/calculation/metrics/pump_speed \
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

### 验证16：文档字符串完整性

**验证目的**：验证所有类和方法有文档字符串

**验证命令**：
```bash
# 使用pydocstyle检查
pydocstyle app/services/calculation/metrics/pump_speed/
```

**预期结果**：
- 所有类和方法都有文档字符串
- 文档字符串符合Google风格

**验证标准**：
- [ ] 所有类有文档字符串
- [ ] 所有公共方法有文档字符串
- [ ] 文档字符串格式正确

---

## 文档完整性验证

### 验证17：文档完整性

**验证目的**：验证所有文档已完成

**验证清单**：
- [ ] 01-pump_speed详细设计.md（已完成）
- [ ] 02-pump_speed实施计划.md（已完成）
- [ ] 03-pump_speed重构任务跟踪.md（已完成）
- [ ] 04-pump_speed重构完整检查清单.md（已完成）
- [ ] 05-任务完成追踪表.md（已完成）
- [ ] 06-pump_speed测试用例.md（已完成）
- [ ] 07-pump_speed测试脚本.md（已完成）
- [ ] 08-pump_speed验证清单.md（已完成）

**验证标准**：
- [ ] 所有8个文档已完成
- [ ] 文档内容完整
- [ ] 文档格式正确

---

### 验证18：数据质量报告

**验证目的**：生成数据质量报告

**报告内容**：
1. 数据完整性统计
2. 数据质量分布
3. 异常值分析
4. 物理关系验证
5. 性能指标统计

**验证标准**：
- [ ] 数据质量报告已生成
- [ ] 报告内容完整
- [ ] 报告格式清晰

---

### 验证19：性能测试报告

**验证目的**：生成性能测试报告

**报告内容**：
1. 计算耗时统计
2. 吞吐量统计
3. 内存使用统计
4. 性能瓶颈分析
5. 优化建议

**验证标准**：
- [ ] 性能测试报告已生成
- [ ] 报告内容完整
- [ ] 报告格式清晰

---

## 📊 验证清单统计

| 验证类型 | 验证项数 | 验证方法 |
|----------|---------|---------|
| 数据库验证 | 4 | SQL查询 |
| 计算结果验证 | 3 | SQL查询 |
| 数据质量验证 | 3 | SQL查询 |
| 性能验证 | 3 | pytest + SQL |
| 代码质量验证 | 3 | pylint + pytest |
| 文档完整性验证 | 3 | 手动检查 |
| **总计** | **19** | **混合方法** |

---

## ✅ 总体验收标准

**数据库准备**：
- [ ] pump_frequency数据存在且完整
- [ ] device_rated_params参数完整
- [ ] calculation_parameters参数完整
- [ ] mv_device_running_1s可用

**计算结果**：
- [ ] pump_speed计算结果已写入
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
- [ ] 数据质量报告已生成
- [ ] 性能测试报告已生成

---

**文档结束**

