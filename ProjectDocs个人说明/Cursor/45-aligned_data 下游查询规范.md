______________________________________________________________________

## description: aligned_data 下游查询规范（索引/分区命中、时间窗口扫描、JSON 提取）

# aligned_data 查询规范

## 访问模式（推荐）

- 精确设备+时间窗：

```sql
SELECT standard_time,
       JSON_EXTRACT(data_json, '$.power') AS power,
       JSON_EXTRACT(data_json, '$.pressure') AS pressure
FROM aligned_data
WHERE device_id = ?
  AND standard_time >= ? AND standard_time < ?
ORDER BY standard_time;
```

- 站点聚合：

```sql
SELECT standard_time,
       AVG(CAST(JSON_UNQUOTE(JSON_EXTRACT(data_json, '$.power')) AS DECIMAL(20,2))) AS avg_power
FROM aligned_data FORCE INDEX(idx_station_time)
WHERE station_id = ?
  AND standard_time >= ? AND standard_time < ?
GROUP BY standard_time
ORDER BY standard_time;
```

## 索引与分区命中

- 必须命中 `(device_id, standard_time)` 或 `(station_id, standard_time)`；
- 严禁无时间条件的广泛扫描；
- JSON 提取尽量在过滤后进行，减少扫描数据量。

## 反例（禁止）

- `WHERE JSON_EXTRACT(data_json, '$.power') > 0` 且无时间窗 → 可能全表扫；
- `WHERE standard_time BETWEEN ...` 但无设备/站点 → 历史分区大量扫描。

## 导出建议

- 大窗口导出采用游标分页（按时间），禁止 OFFSET 深翻（见 22）。
