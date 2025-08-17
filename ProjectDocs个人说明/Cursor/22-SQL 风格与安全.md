# SQL 风格与安全

## 参数化

- 严禁字符串拼接构造可执行 SQL；使用参数化与占位符。

## 事务与隔离

- 避免长事务；必要时分批提交；隔离级别按需而定，默认 REPEATABLE READ。

## 分区与索引

- 查询走索引；分区键对齐 `standard_time` 范围；禁止无谓全表扫描。

## 审核清单

- 关键 DDL/DML 需在评审中明确性能与一致性影响。
- 查询走索引；分区键对齐 `standard_time` 范围；禁止无谓全表扫描。

## 审核清单

- 关键 DDL/DML 需在评审中明确性能与一致性影响。

## 附加规范与示例

### 参数化示例（Python，PyMySQL）

```python
sql = """
SELECT standard_time, JSON_EXTRACT(data_json, '$.power') AS power
FROM aligned_data
WHERE device_id=%s AND standard_time>=%s AND standard_time<%s
ORDER BY standard_time
"""
cursor.execute(sql, (device_id, since_dt, until_dt))
```

### 反例（禁止）

```python
cursor.execute(f"... WHERE device_id={device_id} AND standard_time>='{since_dt}' ...")
```

### EXPLAIN/ANALYZE 示例

```sql
EXPLAIN ANALYZE
SELECT standard_time
FROM aligned_data FORCE INDEX(idx_station_time)
WHERE station_id=? AND standard_time BETWEEN ? AND ?
ORDER BY standard_time;
```

### 慢查询整改 SOP（摘要）

- 确认谓词是否命中 `(device_id, standard_time)` 或 `(station_id, standard_time)` 索引
- 增加时间窗限制；避免 JSON 过滤在大范围数据上执行
- 必要时改写为“先筛后取”的子查询或物化中间结果
