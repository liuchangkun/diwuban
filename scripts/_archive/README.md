# 归档说明（\_archive）

- 本目录用于存放历史脚本/测试等文件，这些文件可能依赖已下线的数据库视图或临时实现（例如：operation_data、v_fully_adaptive_data、device_data、pipeline_data）。
- 归档仅供参考，不再作为生产或开发时的事实来源。
- 如需恢复，请先评估数据库对象是否存在，并优先改造为使用 fact_measurements + 维表 或公有函数（public.get\_*_by_time_range）与报表函数（reporting.get_metrics_*）。
