# API 路由（自动生成｜含注释）

> 说明：根据 app/api/v1/endpoints/*.py 的 @router 装饰器解析，参数说明来自 Query(..., description=)。


<a id="api.db-health.GET"></a>
## GET /db-health
- 处理函数：`db_health_check`
- 功能说明：系统/数据库健康检查

<a id="api.devices.GET"></a>
## GET /devices
- 处理函数：`get_devices`
- 功能说明：查询设备与基础元数据（分页/筛选）
- 返回模型：`DevicesResponse`
- 参数：
  - `station_id` <Optional[int]>：按泵站ID筛选
  - `status` <Optional[str]>
  - `limit` <int>：返回数量限制
  - `offset` <int>：偏移量

<a id="api.devices.{device_id}.GET"></a>
## GET /devices/{device_id}
- 处理函数：`get_device_detail`
- 功能说明：查询设备详情
- 参数：
  - `device_id` <int>

<a id="api.devices.{device_id}.measurements.GET"></a>
## GET /devices/{device_id}/measurements
- 处理函数：`get_device_measurements`
- 功能说明：设备时间窗度量查询（筛选指标/粒度/分页）
- 返回模型：`TimeSeriesResponse`
- 参数：
  - `device_id` <int>：开始时间（UTC或本地时间，建议UTC）
  - `start_time` <datetime>：开始时间（UTC或本地时间，建议UTC）
  - `end_time` <datetime>：结束时间（必须大于开始时间）
  - `metric_ids` <Optional[List[int]]>：指标ID列表（可选）
  - `granularity` <str>：粒度：auto|hourly|daily
  - `limit` <int>：返回数量限制
  - `offset` <int>：偏移量

<a id="api.devices.{device_id}.raw.GET"></a>
## GET /devices/{device_id}/raw
- 处理函数：`get_device_raw`
- 功能说明：设备近原始数据（wide/long）
- 返回模型：`TimeSeriesResponse`
- 参数：
  - `device_id` <int>：开始时间（UTC或本地时间，建议UTC）
  - `start_time` <datetime>：开始时间（UTC或本地时间，建议UTC）
  - `end_time` <datetime>：结束时间（必须大于开始时间）
  - `limit` <int>：返回数量限制
  - `offset` <int>：偏移量
  - `format` <str>：返回格式：wide|long

<a id="api.health.GET"></a>
## GET /health
- 处理函数：`system_health_check`
- 功能说明：系统/数据库健康检查

<a id="api.performance.GET"></a>
## GET /performance
- 处理函数：`system_performance`
- 功能说明：系统性能指标

<a id="api.pool-stats.GET"></a>
## GET /pool-stats
- 处理函数：`connection_pool_stats`
- 功能说明：连接池统计

<a id="api.stations.{station_id}.measurements.GET"></a>
## GET /stations/{station_id}/measurements
- 处理函数：`get_station_measurements`
- 功能说明：按站点查询时间窗度量（可筛选设备/指标）
- 返回模型：`TimeSeriesResponse`
- 参数：
  - `station_id` <int>：开始时间（UTC或本地时间，建议UTC）
  - `start_time` <datetime>：开始时间（UTC或本地时间，建议UTC）
  - `end_time` <datetime>：结束时间（必须大于开始时间）
  - `device_ids` <Optional[List[int]]>：设备ID列表（可选）
  - `metric_ids` <Optional[List[int]]>：指标ID列表（可选）
  - `granularity` <str>：粒度：auto|hourly|daily
  - `limit` <int>：返回数量限制
  - `offset` <int>：偏移量

<a id="api.stations.{station_id}.raw.GET"></a>
## GET /stations/{station_id}/raw
- 处理函数：`get_station_raw`
- 功能说明：站点近原始数据（wide/long）
- 返回模型：`TimeSeriesResponse`
- 参数：
  - `station_id` <int>：开始时间（UTC或本地时间，建议UTC）
  - `start_time` <datetime>：开始时间（UTC或本地时间，建议UTC）
  - `end_time` <datetime>：结束时间（必须大于开始时间）
  - `limit` <int>：返回数量限制
  - `offset` <int>：偏移量
  - `format` <str>：返回格式：wide|long

---

> 生成器：generate_project_wiki.py｜时间：2025-09-25 08:36
