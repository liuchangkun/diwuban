# ENGINEERING_STANDARDS（工程与编码规范）

本文件由 PROJECT_RULES.md 第 13 章抽取并扩展，作为工程协作的主参考。

## 1. 语言与版本
- Python ≥ 3.9；优先 `pathlib`；禁止访问 `venv/.venv/env`。

## 2. 目录/模块组织
- 建议目录：`src/`、`scripts/`、`tests/`、`config/`、`rules/`、`data/`、`docs/`。
- 分层模块：`ingest/align/validate/derive/fit/optimize/viz`。

## 3. 依赖与环境
- 统一包管理与锁定；敏感信息由环境变量/密钥管理器提供；提供 `.env.sample`。

## 4. 风格与检查
- Black + isort + Ruff/Flake8 + mypy；Docstring（Google/NumPy）。
- 命名规范：snake_case/PascalCase/UPPER_CASE。

## 5. 类型与数据模型
- 公共 API 全量类型标注；关键结构用 `dataclasses`/Pydantic。
- DataFrame 字段：`station_id, device_id, metric, ts_local, ts_utc, value`。

## 6. 异常与错误处理
- 自定义异常：IngestError/AlignError/ValidationError/DeriveError/FitError/OptimizeError。
- 边界捕获+结构化日志，内部 fail fast，并给出可操作建议。

## 7. 日志
- 统一 logging，字段含 run_id/version/station/device/metric/time_range/row_count。

## 8. 配置与参数
- 规则参数来自 `rules/rules.yml`，禁止硬编码数据路径/单位换算。

## 9. I/O 与性能
- CSV 显式 encoding/parse_dates/dtype/na_values；大文件分块；批量写入幂等。

## 10. 时间与时区
- tz-aware；本地 Asia/Shanghai、库内 UTC；对齐前先转换。

## 11. 数值与单位
- isfinite 检查；分母阈值；压力默认 kPa，MPa→×1000。

## 12. DataFrame 约定
- 避免就地修改；输出含 grid/version；累计量阶梯保持。

## 13. 测试与覆盖率
- pytest；关键模块 ≥ 80%；边界/异常必测。

## 14. 提交与评审
- Conventional Commits；PR 勾选合规清单与附报告。

## 15. 安全与合规
- 数据脱敏；生产改动需审批；默认只读。

## 16. 可追溯与复现
- run_id + 固定随机种子；参数变化 version+1 并记录。

