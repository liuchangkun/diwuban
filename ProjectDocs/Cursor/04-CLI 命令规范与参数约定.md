---
description: CLI 命令规范与参数约定
---
# CLI 规范

## 入口
- 命令入口：`app/cli.py`。

## 核心命令与语义
- `verify-mapping`：校验映射与 DB 名称一致；发现不一致直接失败（退出码 2），输出人类与机器可读摘要（见 48）。
- `init-units`：创建并初始化 `field_units`；重复执行幂等；失败退出码 5。
- `import-file --path ... [--batch-size 50000] [--dry-run]`：单文件导入。
- `import-station --name "二期供水泵房" [--concurrency 4] [--resume] [--since 2025-02-01] [--until 2025-02-28]`：按泵站导入。
- `import-all [--concurrency 4] [--since ...] [--until ...] [--resume]`：全量导入。

## 行为约定
- `--dry-run`：执行校验与计划生成，不落库；输出影响评估与门禁报告（见 40/48）。
- `--resume`：从 `state/` 断点继续；若检测到配置/映射变化，要求先 `verify-mapping` 通过。
- 时间窗：`--since/--until` 均含边界语义：`[since, until)`。

## 退出码映射（对齐 48）
- 0 成功、1 配置/参数错误、2 Schema/映射失败、3 文件路径错误、4 DB 连接失败、5 导入/对齐失败、6 门禁/性能不达标终止、99 未知错误。

## 示例
```bash
python -m app.cli verify_mapping --mapping configs/data_mapping.json --schema configs/data_mapping_schema.json
python -m app.cli init_units --sql sql/field_units_init.sql
python -m app.cli import_station --name "二期供水泵房" --concurrency 4 --since 2025-02-01 --until 2025-02-28 --dry-run
```

## 帮助文案规范
- 每个子命令必须包含用途、参数说明、默认值与示例；
- 对失败场景给出 `hint` 与相关规则链接（mdc）。