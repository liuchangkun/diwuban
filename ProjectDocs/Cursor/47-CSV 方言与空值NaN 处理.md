---
description: CSV 方言与空值/NaN 处理（换行/分隔/引号/转义、空值/NaN/INF 标准化）
---
# CSV 方言与空值/NaN 处理

## 方言
- 编码 UTF-8、换行 `\r\n`、逗号分隔、首行表头、可选双引号包裹。

## 空值与异常映射
- 视为缺失的令牌：`""`、`NULL/null`、`NaN/nan`、`INF/-INF`、`N/A`；默认丢弃该行（或入隔离区，见 31）。

## 预清洗策略
- 引号失衡/非法字符：尝试修复；失败则落坏行。
- 时间列无法截秒解析：整行入坏行日志。

## LOAD DATA 示例（将空串映射为 NULL）
```sql
LOAD DATA LOCAL INFILE '{file}'
INTO TABLE tmp_raw
CHARACTER SET utf8
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 LINES
(TagName, @dt, @ver, @qual, @val)
SET DataTime = STR_TO_DATE(SUBSTRING_INDEX(@dt, '.', 1), '%Y-%m-%d %H:%i:%s'),
    DataValue = NULLIF(@val, '');
```

## 审计
- 记录无效值行数与样例，输出 `bad_rows.write` 事件（见 10）。