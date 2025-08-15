---
alwaysApply: true
description: aligned_data.data_json 业务 Schema（按设备/泵型约束字段与精度）
---
# aligned_data.data_json 业务 Schema

## 通用
- 列字段：`station_id`（冗余查询用，不写入 data_json）、`device_id`、`standard_time`。
- `data_json` 候选键：见 [30-domain-dictionary.mdc](mdc:.cursor/rules/30-domain-dictionary.mdc)。

## 设备类型约束
- pump（泵）：
  - 变频（variable_frequency）：必填 `frequency`；可选 `power`、`power_factor`、`voltage_*`、`current_*`。
  - 软启动（soft_start）：`frequency` 可无；可选同上。
- pipeline（管道）：
  - 必填至少一项：`pressure`、`flow_rate`、`cumulative_flow`；电气字段通常缺省。

## 精度与类型
- 数值小数位：
  - `frequency`/`power_factor`/`load_rate`/`efficiency`: ≤ 3 位
  - 电压/电流/功率/压力/流量：≤ 2 位
- null 规则：
  - 缺失字段不写入；合并时 null 不覆盖有效值；
  - 对于计算字段，若输入不足产生 null，记录 `calc_missing=true` 日志样本。

## 合并与冲突
- 同一键多来源：按“同秒最早”策略；若差异超阈值（见 33），保留最早并记录 `conflict=true`。