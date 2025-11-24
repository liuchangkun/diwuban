# main_pipeline_inlet_pressure 验证清单文档

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5  
> **参考文档**: `06-main_pipeline_inlet_pressure测试用例.md`, `07-main_pipeline_inlet_pressure测试脚本.md`

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

### 验证1：pool_liquid_level数据存在性

**验证目的**：确认pool_liquid_level数据存在且完整

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
WHERE metric_id = 5  -- pool_liquid_level
  AND device_id = 8
  AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
GROUP BY device_id;
```

**预期结果**：
- device_id=8有数据
- 记录数 > 10000
- 液位值在0-10 m范围内

**验证标准**：
- [ ] device_id=8有数据
- [ ] 数据量符合预期
- [ ] 数据值在合理范围

---

### 验证2：calculation_parameters参数完整性

**验证目的**：确认计算参数已正确配置

**验证SQL**：
```sql
SELECT 
    method_id,
    param_key,
    param_value,
    description
FROM calculation_parameters
WHERE metric_key = 'main_pipeline_inlet_pressure'
ORDER BY method_id, param_key;
```

**预期结果**：
- method_b有3个参数（P_atm, rho, g）
- PIN_COEF_V1有4个参数（b0, b1, b2, b3）
- validation有3个参数（min_pressure, max_pressure, physics_tolerance）

**验证标准**：
- [ ] 所有方法都有参数
- [ ] 参数数量正确
- [ ] 参数值合理

---

### 验证3：mv_device_running_1s物化视图可用性

**验证目的**：确认运行状态物化视图可用

**验证SQL**：
```sql
SELECT 
    device_id,
    COUNT(*) as record_count,
    SUM(CASE WHEN running = 1 THEN 1 ELSE 0 END) as running_count,
    SUM(CASE WHEN running = 0 THEN 1 ELSE 0 END) as stopped_count
FROM mv_device_running_1s
WHERE device_id = 7
  AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
GROUP BY device_id;
```

**预期结果**：
- device_id=7有数据
- running=1的记录数 > 0

**验证标准**：
- [ ] device_id=7有运行状态数据
- [ ] running标志正确

---

## 计算结果验证

### 验证4：main_pipeline_inlet_pressure计算结果写入

**验证目的**：确认main_pipeline_inlet_pressure计算结果已写入数据库

**验证SQL**：
```sql
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
WHERE metric_id = 61  -- main_pipeline_inlet_pressure
  AND device_id = 7
  AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
GROUP BY device_id;
```

**预期结果**：
- device_id=7有计算结果
- 记录数 > 0
- 压力值在0-1 MPa范围内

**验证标准**：
- [ ] device_id=7有计算结果
- [ ] 数据量符合预期
- [ ] 数据值在合理范围

---

### 验证5：main_pipeline_inlet_pressure计算结果正确性

**验证目的**：验证main_pipeline_inlet_pressure计算公式正确

**验证SQL**：
```sql
SELECT 
    fm_level.device_id as pool_device_id,
    fm_level.ts_bucket,
    fm_level.value as pool_liquid_level,
    fm_pressure.value as main_pipeline_inlet_pressure,
    0.101325 + 1000.0 * 9.81 * fm_level.value / 1e6 as expected_pressure,
    ABS(fm_pressure.value - (0.101325 + 1000.0 * 9.81 * fm_level.value / 1e6)) as diff,
    ABS(fm_pressure.value - (0.101325 + 1000.0 * 9.81 * fm_level.value / 1e6)) / (0.101325 + 1000.0 * 9.81 * fm_level.value / 1e6) as diff_ratio
FROM fact_measurements fm_level
JOIN fact_measurements fm_pressure 
    ON fm_level.ts_bucket = fm_pressure.ts_bucket
WHERE fm_level.metric_id = 5  -- pool_liquid_level
  AND fm_level.device_id = 8
  AND fm_pressure.metric_id = 61  -- main_pipeline_inlet_pressure
  AND fm_pressure.device_id = 7
  AND fm_level.ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-22 09:00:00'
ORDER BY fm_level.ts_bucket
LIMIT 100;
```

**预期结果**：
- diff_ratio < 0.01（差异<1%）

**验证标准**：
- [ ] 计算结果与预期一致
- [ ] 差异在允许范围内

---

### 验证6：main_pipeline_inlet_pressure与pool_liquid_level的关系

**验证目的**：验证main_pipeline_inlet_pressure与pool_liquid_level的物理关系

**验证SQL**：
```sql
SELECT
    COUNT(*) as total_count,
    SUM(CASE WHEN ABS(fm_pressure.value - (0.101325 + 1000.0 * 9.81 * fm_level.value / 1e6)) / (0.101325 + 1000.0 * 9.81 * fm_level.value / 1e6) < 0.1 THEN 1 ELSE 0 END) as valid_count,
    SUM(CASE WHEN ABS(fm_pressure.value - (0.101325 + 1000.0 * 9.81 * fm_level.value / 1e6)) / (0.101325 + 1000.0 * 9.81 * fm_level.value / 1e6) < 0.1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as valid_ratio
FROM fact_measurements fm_level
JOIN fact_measurements fm_pressure
    ON fm_level.ts_bucket = fm_pressure.ts_bucket
WHERE fm_level.metric_id = 5  -- pool_liquid_level
  AND fm_level.device_id = 8
  AND fm_pressure.metric_id = 61  -- main_pipeline_inlet_pressure
  AND fm_pressure.device_id = 7
  AND fm_level.ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
  AND fm_level.value > 0;
```

**预期结果**：
- valid_ratio > 90%（90%以上的数据符合物理关系）

**验证标准**：
- [ ] 物理关系验证通过率 > 90%

---

## 数据质量验证

### 验证7：main_pipeline_inlet_pressure数据完整性

**验证目的**：验证main_pipeline_inlet_pressure数据无缺失

**验证SQL**：
```sql
SELECT
    'pool_liquid_level' as metric,
    device_id,
    COUNT(*) as record_count
FROM fact_measurements
WHERE metric_id = 5
  AND device_id = 8
  AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
GROUP BY device_id

UNION ALL

SELECT
    'main_pipeline_inlet_pressure' as metric,
    device_id,
    COUNT(*) as record_count
FROM fact_measurements
WHERE metric_id = 61
  AND device_id = 7
  AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
GROUP BY device_id

ORDER BY device_id, metric;
```

**预期结果**：
- main_pipeline_inlet_pressure记录数 ≈ pool_liquid_level记录数（考虑running=1过滤）

**验证标准**：
- [ ] 数据完整性 > 95%

---

### 验证8：main_pipeline_inlet_pressure数据质量分布

**验证目的**：验证main_pipeline_inlet_pressure数据质量标记正确

**验证SQL**：
```sql
SELECT
    device_id,
    quality,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY device_id) as percentage
FROM fact_measurements
WHERE metric_id = 61  -- main_pipeline_inlet_pressure
  AND device_id = 7
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

### 验证9：main_pipeline_inlet_pressure异常值检测

**验证目的**：检测main_pipeline_inlet_pressure异常值

**验证SQL**：
```sql
WITH pressure_changes AS (
    SELECT
        device_id,
        ts_bucket,
        value as main_pipeline_inlet_pressure,
        LAG(value) OVER (PARTITION BY device_id ORDER BY ts_bucket) as prev_pressure,
        value - LAG(value) OVER (PARTITION BY device_id ORDER BY ts_bucket) as pressure_change,
        ABS(value - LAG(value) OVER (PARTITION BY device_id ORDER BY ts_bucket)) as abs_pressure_change
    FROM fact_measurements
    WHERE metric_id = 61  -- main_pipeline_inlet_pressure
      AND device_id = 7
      AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
)
SELECT
    device_id,
    COUNT(*) as total_count,
    SUM(CASE WHEN abs_pressure_change > 0.1 THEN 1 ELSE 0 END) as outlier_count,
    SUM(CASE WHEN abs_pressure_change > 0.1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as outlier_ratio,
    MAX(abs_pressure_change) as max_change
FROM pressure_changes
WHERE prev_pressure IS NOT NULL
GROUP BY device_id;
```

**预期结果**：
- outlier_ratio < 1%（异常值比例<1%）
- max_change < 0.2 MPa/s

**验证标准**：
- [ ] 异常值比例 < 1%
- [ ] 最大变化率合理

---

## 性能验证

### 验证10：计算性能

**验证目的**：验证计算性能符合要求

**验证方法**：
1. 运行性能测试脚本
2. 记录耗时和吞吐量

**验证命令**：
```bash
pytest tests/performance/metrics/main_pipeline_inlet_pressure/test_main_pipeline_inlet_pressure_performance.py::TestMainPipelineInletPressurePerformance::test_large_dataset_performance -v
```

**预期结果**：
- 总耗时 < 30秒
- 吞吐量 > 2000条/秒

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
WHERE metric_key = 'main_pipeline_inlet_pressure'
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

**验证方法**：
1. 运行内存测试脚本
2. 记录内存使用

**验证命令**：
```bash
pytest tests/performance/metrics/main_pipeline_inlet_pressure/test_main_pipeline_inlet_pressure_performance.py::TestMainPipelineInletPressurePerformance::test_memory_usage -v
```

**预期结果**：
- 内存增量 < 1GB

**验证标准**：
- [ ] 内存使用 < 1GB

---

## 代码质量验证

### 验证13：代码规范检查

**验证目的**：验证代码符合PEP 8规范

**验证命令**：
```bash
# pylint检查
pylint app/services/calculation/metrics/main_pipeline_inlet_pressure/ --rcfile=.pylintrc

# black格式化检查
black --check app/services/calculation/metrics/main_pipeline_inlet_pressure/

# isort导入排序检查
isort --check-only app/services/calculation/metrics/main_pipeline_inlet_pressure/
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
pytest tests/unit/metrics/main_pipeline_inlet_pressure/ tests/integration/metrics/main_pipeline_inlet_pressure/ \
    --cov=app/services/calculation/metrics/main_pipeline_inlet_pressure \
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
pydocstyle app/services/calculation/metrics/main_pipeline_inlet_pressure/
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

### 验证16：文档完整性

**验证目的**：验证所有文档已完成

**验证清单**：
- [ ] 01-main_pipeline_inlet_pressure详细设计.md（已完成）
- [ ] 02-main_pipeline_inlet_pressure实施计划.md（已完成）
- [ ] 03-main_pipeline_inlet_pressure重构任务跟踪.md（已完成）
- [ ] 04-main_pipeline_inlet_pressure重构完整检查清单.md（已完成）
- [ ] 05-任务完成追踪表.md（已完成）
- [ ] 06-main_pipeline_inlet_pressure测试用例.md（已完成）
- [ ] 07-main_pipeline_inlet_pressure测试脚本.md（已完成）
- [ ] 08-main_pipeline_inlet_pressure验证清单.md（已完成）

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
- [ ] pool_liquid_level数据存在且完整
- [ ] calculation_parameters参数完整
- [ ] mv_device_running_1s可用

**计算结果**：
- [ ] main_pipeline_inlet_pressure计算结果已写入
- [ ] 计算结果正确性验证通过
- [ ] 物理关系验证通过

**数据质量**：
- [ ] 数据完整性 > 95%
- [ ] 有效数据比例 > 90%
- [ ] 异常值比例 < 1%

**性能指标**：
- [ ] 计算耗时 < 30秒
- [ ] 批量写入速度 > 1000条/秒
- [ ] 内存使用 < 1GB

**代码质量**：
- [ ] pylint评分 > 9.0
- [ ] 测试覆盖率 > 90%
- [ ] 文档字符串完整

**文档完整性**：
- [ ] 所有8个文档已完成

---

**文档结束**

