# 项目规则（PROJECT_RULES 索引）

本文件为总纲与索引。中文文档地图请参见：docs/文档地图与导航.md。
核心中文文档：

- 体系结构总览.md（现状）
- 架构落地计划_v1.md（仅 32/33/34/35/37）
- 表结构与数据库.md（UTC 秒级对齐/分区/MV/索引）
- 数据库函数参考.md（写入契约/查询接口）
- 测试指南.md（APScheduler/对齐回归）
- 数据质量与校验.md（骨架）

以下为总原则与成功标准摘要：

项目目录：D:/Augment/diwuban。
虚拟环境目录：D:/Augment/diwuban/.venv。

## 1. 总体约束与声明

- 数据库选型：PostgreSQL 16（无 TimescaleDB）
- 调度：APScheduler（不使用 Windows 计划任务）
- 中间件：不使用 Docker/Kafka；可选 Redis 3.0.504（轻量任务/状态缓存）
- 唯一事实源：数据库与 scripts/sql；文档与实现不一致时，以数据库/脚本为准

## 2. 配置与映射

- 唯一事实来源：`config/data_mapping.json` 是数据-设备-测点映射的唯一来源；代码严禁硬编码数据文件路径与设备/测点。
- 可扩展：新增站/设备/测点仅需更新映射文件，代码按模式加载。
- 标识规范：
  - `station_id` 由顶层键（如“二期供水泵房”）规范化生成。
  - `device_id` 由子键（如“二期供水泵房1#泵”）规范化生成。
  - `metric` 采用统一命名：`frequency, voltage_a, current_a, power, kwh, pressure, flow_rate, cumulative_flow, power_factor, ...`。
  -

## 2. 文件解析与编码

- 编码自动识别：优先 UTF-8（含/不含 BOM），失败回退 GBK；失败记录审计并跳过。
- CSV 规范：自动识别分隔符（逗号优先），必须包含时间列与至少一列数值；多数值列转为 tidy 格式。
- 时间列识别：优先匹配列名（`时间/timestamp/采集时间/记录时间` 等）；不明确时尝试第一列多格式解析。
- 单位与数值处理：
  - 数值统一为浮点（或 decimal），非法值设为 NULL 并记录。
  - 单位统一：流量（m3/h）、压力（MPa 或 kPa，需确认）、电压（V）、电流（A）、功率（kW）、电度（kWh）、频率（Hz）；若源单位不同在配置中注明并换算。
- 去重与排序：按 `timestamp` 去重（device+metric 唯一），时间升序。

## 3. 时区与时间对齐（数据库写入边界）

- 入库与写入：全部 UTC 存储，并对齐到整秒（ts_bucket = date_trunc('second', ts_utc)）
- 主键与合并：PRIMARY KEY(station_id, device_id, metric_id, ts_bucket)，同秒 UPSERT 合并
- 兜底约束：CHECK(date_trunc('second', ts_bucket) = ts_bucket)；父表与分区 NOT VALID，后续 VALIDATE
- 函数边界：safe_upsert_measurement（UTC）、safe_upsert_measurement_local（本地时间+泵站 tz）
- 分析层对齐/插值：作为后续分析策略，避免与入库边界混淆

## 4. 入库与表结构（实际实施：PostgreSQL 16）

- **实际表设计**（已实施）：
  - `dim_stations(id, name, extra, created_at)` - 泵站维表
  - `dim_devices(id, station_id, name, type, pump_type, extra, created_at)` - 设备维表（含总管）
  - `dim_metric_config(id, metric_key, unit, unit_display, decimals_policy, fixed_decimals, value_type, valid_min, valid_max, created_at, updated_at)` - 指标配置表
  - `device_rated_params(id, device_id, param_key, value_numeric, value_text, unit, source, effective_from, effective_to, created_at, updated_at)` - 设备额定参数表
  - `fact_measurements(id, station_id, device_id, metric_id, ts_raw, ts_bucket, value, source_hint, inserted_at)` - 时序数据事实表
  - `dim_mapping_items(id, mapping_hash, station_name, device_name, metric_key, source_hint, created_at)` - mapping快照表
- **分区策略**：fact_measurements 按周 RANGE 分区；叶子分区按需维护活跃索引
- **唯一键**：PRIMARY KEY(station_id, device_id, metric_id, ts_bucket)
- **频繁CRUD优化**：
  - 存储参数优化：fillfactor=70，autovacuum 参数调优
  - 索引策略：父表 BRIN(ts_bucket) + 叶子分区 btree(station_id, device_id, metric_id, ts_bucket) INCLUDE(value)
  - 并发控制：SELECT FOR UPDATE NOWAIT 避免锁等待
- **风险控制**：数据一致性、性能监控、存储管理的完整解决方案
  - 数据一致性：事务管理 + 并发控制 + 自动检查
  - 性能监控：实时指标 + 自动告警 + 自动调优
  - 存储管理：智能VACUUM + 空间回收 + 膨胀监控

## 5. 数据质量与校验

- 基础校验：
  - 累计量（kWh/累计流量）非递减，否则标记“归零/复位/换表”，切分周期。
  - 合理范围：为每测点设置硬/软阈值（软阈报警但保留，硬阈置 NULL）。
  - 缺失比率：统计每设备/测点缺失，超过阈值（如 30%）的区段在拟合与优化中剔除。
  - 离群：IQR/MAD 或滑窗 z-score 标记离群；保留原值，在质量标签中记录。
- 交叉校验：
  - 电功率关系：`S ≈ √3·U·I`，`P ≈ S·PF`；U/I/P/PF 交叉验证。
  - 水力功率：`P_h = ρ·g·Q·H` 与电功率（扣效率）对比。
  - 累计量增量与瞬时量积分一致性校验（ΔkWh、Δ累计流量 vs 积分）。
- 审计日志：记录每次入库/对齐/派生/拟合/优化的参数、范围、指标与异常摘要。

## 6. 扩展文档（占位）

- 本章及后续“拟合/优化/可视化/工程细则/附录”等内容暂不纳入当前规则总纲；待相关实现落地后，再从各自中文文档回链到本总纲。
- 当前请以以下文档为准：
  - docs/体系结构总览.md、docs/架构落地计划_v1.md（仅 32/33/34/35/37）
  - docs/表结构与数据库.md、docs/数据库函数参考.md、docs/泵站时间对齐实现.md
  - docs/表结构明细_附录.md、docs/逐函数详解_附录.md

## 7. 成功标准（DoD，精简）

- 入库成功率 > 98%；对齐完整度 > 95%；文档/PLAYBOOKS 同步更新

## 8. 技术选型与约束（现状）

- PostgreSQL 16（无 TimescaleDB）
- APScheduler（不使用 Windows 计划任务）
- 不使用 Docker/Kafka；可选 Redis 3.0.504（轻量任务/状态缓存）
- 唯一事实源：数据库与 scripts/sql；文档与实现不一致时，以数据库/脚本为准

（本文件到此为止，其余工程细则与附录请参考各子文档。）
