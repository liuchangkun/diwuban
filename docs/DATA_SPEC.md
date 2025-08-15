# DATA_SPEC（数据文件规范）

目标：明确 data/ 下 CSV 的通用规范，保障可解析、可对齐、可追踪。

## 1. 文件编码与分隔
- 编码优先 UTF-8（自动探测失败回退 GBK），逗号分隔。
- 允许带表头；必须包含时间列与至少一个数值列。

## 2. 时间列
- 推荐列名：`时间`/`timestamp`/`采集时间`/`记录时间`；若无明确列名，默认第一列为时间。
- 支持多格式解析；解析失败则记录并跳过该文件。
- 时区：默认视为 Asia/Shanghai，入库统一转换为 UTC。

## 3. 数值列与单位
- 数值统一转为浮点（或 Decimal），非法/空值设为 NULL 并记录。
- 单位参考：pressure=kPa, flow_rate=m3/h, voltage=V, current=A, power=kW, energy=kWh, frequency=Hz。
- 累计量（kWh、累计流量）不可做插值，仅做阶梯保持。

## 4. 结构与整形
- 多数值列转为 tidy：列名→`metric`，值→`value`。
- 标准字段：`station_id, device_id, metric, ts_local, ts_utc, value, src_file, src_row`。

## 5. 质量与异常
- 去重：同一 `device+metric+timestamp` 保留最新。
- 非法时间/单位/数值：记录审计日志并跳过。

## 6. 溯源
- 保留 `src_file` 与 `src_row`，并在入库与可视化中可回溯。
