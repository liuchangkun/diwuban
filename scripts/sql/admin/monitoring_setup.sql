-- 监控增强一键脚本（需超级用户）
-- 目标：在低开销前提下，看见 DB 函数/触发器/视图在工作；仅慢>200ms输出计划

\echo 'Step 1/6: 显示当前版本与关键配置'
SHOW server_version;
SHOW shared_preload_libraries;
SHOW track_functions;

\echo 'Step 2/6: 开启扩展（pg_stat_statements）'
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

\echo 'Step 3/6: 建议的运行时参数（可热加载）'
-- 函数统计（含触发器函数）
ALTER SYSTEM SET track_functions = 'pl';
-- auto_explain 慢阈值与输出内容
ALTER SYSTEM SET auto_explain.log_min_duration = '200ms';
ALTER SYSTEM SET auto_explain.log_analyze = 'on';
ALTER SYSTEM SET auto_explain.log_buffers = 'on';
ALTER SYSTEM SET auto_explain.log_format = 'text';
-- 可选：慢 SQL 原文
-- ALTER SYSTEM SET log_min_duration_statement = '200ms';

\echo 'Step 4/6: 若未启用预加载库，请在配置文件添加后重启（此脚本不修改 shared_preload_libraries）'
-- 请在 postgresql.conf 加入：
--   shared_preload_libraries = 'pg_stat_statements,auto_explain'
-- 然后重启数据库

\echo 'Step 5/6: 重新加载配置（热加载生效项）'
SELECT pg_reload_conf();

\echo 'Step 6/6: 验证'
SELECT * FROM pg_stat_statements LIMIT 1;
SELECT schemaname, funcname, calls, total_time, self_time
FROM pg_stat_user_functions
ORDER BY total_time DESC
LIMIT 20;

