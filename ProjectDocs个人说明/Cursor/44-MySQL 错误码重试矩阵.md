______________________________________________________________________

## description: MySQL 错误码重试矩阵（可重试/不可重试、退避策略）

# MySQL 错误码重试矩阵

## 可重试（指数退避，最大重试 N 次）

- 1213 死锁、1205 锁等待超时、2006 MySQL server has gone away、2013 Lost connection。
- 退避建议：初始 200~500ms，乘数 1.5~2.0，抖动 ±20%，最大 5 次（导入阶段 ≤3）。

## 不可重试

- 1064 语法错误、1146 表不存在、1054 列不存在、1364 非空列无默认、1062 唯一键冲突（除非业务允许重试逻辑）。

## 幂等与防重

- 写入路径基于 `(device_id, standard_time)` 幂等合并；
- 若客户端合并，需带 `Idempotency-Key`（或 `trace_id+batch_id+seq`）避免重复影响。

## 日志字段与示例

- 记录：`error_code`、`attempt/max_attempts/backoff_ms`、`sql_op`、SQL 摘要、`trace_id`；

```json
{"event":"db.retry","error_code":1213,"attempt":2,"backoff_ms":450,"sql_op":"INSERT","trace_id":"t-..."}
```
