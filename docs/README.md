# 文档地图与导航（入口首页）

> 本仓库文档全部为中文；自动生成区块以 HTML 注释标记，运行脚本可一键更新。

## 一、快速入口

- 项目概述与快速开始：docs/项目概述与快速开始.md
- 体系结构总览：docs/体系结构总览.md
- 应用接口说明（API v1）：docs/应用接口说明.md
- 程序工作流程（CLI 全链路）：docs/程序工作流程.md
- 配置说明（含自动快照）：docs/配置说明.md
- 日志规范 与 日志运维：docs/日志规范.md、docs/日志运维.md
- 数据库设计文档（含自动段）：docs/数据库设计文档.md
- 部署运维：docs/部署运维.md

## 二、如何更新“自动区块”

- API 路由清单（API_AUTO）：
  - python scripts/dev/export_api_routes.py
  - python scripts/dev/compose_docs_from_snapshots.py
- 模型字段矩阵（MODELS_AUTO）：
  - python scripts/tools/doc_gen/gen_api_models_md.py
- 配置快照（CONFIG_AUTO）：
  - python scripts/tools/doc_gen/gen_config_md.py
- CLI 帮助（CLI_AUTO）：
  - python scripts/dev/export_cli_help.py
  - python scripts/dev/compose_docs_from_snapshots.py
- 数据库文档（DB_AUTO）：
  - python scripts/dev/gen_db_docs.py
- 日志规范（LOGGING_AUTO）：
  - python scripts/tools/doc_gen/gen_logging_md.py

说明：Windows PowerShell 不支持 "&&"，请逐条执行；所有脚本默认以仓库根目录为工作目录。

## 三、常见定位入口

- 健康检查：/health、/api/v1/monitoring/health
- 日志位置：logs/*.log 或 logs/runs/YYYYMMDD/<job_id>/
- 配置目录：configs/*.yaml（优先级：CLI > ENV > YAML > 默认）
- SQL 与对象：scripts/sql/**、docs/_archive/reports/sql_schema_extract.md

## 四、规范与指南

- 智能助手执行规则（SSOT）：docs/智能助手执行规则.md
- 规则索引（总览导航）：docs/规则索引.md
- 智能助手行为控制：docs/智能助手行为控制.md
- 行为约束：docs/行为约束.md
- 编码规范：docs/编码规范.md
- 测试指南：docs/测试指南.md
- 严格模式-核对清单：docs/严格模式-核对清单.md
- MCP 工具使用指南：docs/MCP工具使用指南.md

若某处链接失效，请以同名文件在 docs 目录下搜索；如有冲突，以代码与配置为准。
