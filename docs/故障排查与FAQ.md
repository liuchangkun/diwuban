# 故障排查与FAQ（骨架）

> 来源代码路径：app/main.py、app/cli/main.py、app/core/config/loader*.py、app/adapters/db/*、configs/*.yaml
> 最近校对日期：2025-08-26

## 常见问题
- 无法导入 app 模块：请使用 python -m 运行或设置项目根为工作目录
- 数据库连接失败：检查 configs/database.yaml；使用 `python -m app.cli.main db-ping --verbose`
- run-all 失败：先单步执行 prepare-dim / create-staging / ingest-copy / merge-fact 确认
- 日志未输出：检查 configs/logging.yaml 路由与格式；确认权限

## 排障步骤模板
1) 收集版本与环境信息
2) 重现步骤与输入样本
3) 查看 logs/runs/* 中的 env.json 与 summary.json
4) 提取错误堆栈与 SQL 慢查询

