# API接口清单（完整版）

> 最后更新：2025-09-30
> 更新者：AI（基于实际代码全量扫描）

---

## 时序数据API（data_timeseries.py）

### GET /api/v1/measurements
**文件路径**：app/api/v1/endpoints/data_timeseries.py
**用途**：查询测量数据（已废弃，兼容性保留）
**请求参数**：station_id, device_id, start_time, end_time, limit, offset
**响应**：TimeSeriesResponse（空数据 + 废弃提示）

### GET /api/v1/stations/{station_id}/measurements
**文件路径**：app/api/v1/endpoints/data_timeseries.py
**用途**：查询泵站测量数据（时序）
**路径参数**：station_id (int)
**请求参数**：start_time, end_time, device_ids, metric_ids, granularity, limit, offset
**响应**：TimeSeriesResponse

### GET /api/v1/devices/{device_id}/measurements
**文件路径**：app/api/v1/endpoints/data_timeseries.py
**用途**：查询设备测量数据（时序）
**路径参数**：device_id (int)
**请求参数**：start_time, end_time, metric_ids, granularity, limit, offset
**响应**：TimeSeriesResponse

### GET /api/v1/stations/{station_id}/raw
**文件路径**：app/api/v1/endpoints/data_timeseries.py
**用途**：查询泵站原始数据（不聚合）
**路径参数**：station_id (int)
**请求参数**：start_time, end_time, device_ids, metric_ids, format, limit, offset
**响应**：TimeSeriesResponse（format=wide时返回宽表格式）

---

## 管理API（data_admin.py）

### GET /api/v1/stations
**文件路径**：app/api/v1/endpoints/data_admin.py
**用途**：获取所有泵站的概览信息
**响应**：List[StationSummary]

### GET /api/v1/stations/{station_id}/devices
**文件路径**：app/api/v1/endpoints/data_admin.py
**用途**：获取指定泵站的设备信息
**路径参数**：station_id (str)
**响应**：List[DeviceSummary]

### GET /api/v1/metrics
**文件路径**：app/api/v1/endpoints/data_admin.py
**用途**：获取指标清单
**请求参数**：station_id, device_id（可选）
**响应**：List[MetricInfo]

---

## 监控API（monitoring.py）

### GET /api/v1/monitoring/health
**文件路径**：app/api/v1/endpoints/monitoring.py
**函数名**：`system_health_check()`
**用途**：系统健康检查
**响应**：Dict[str, Any]（包含status、timestamp、checks、services）

**响应示例**：
```json
{
  "status": "healthy",
  "timestamp": "2025-09-30T12:00:00Z",
  "checks": {
    "database": {"healthy": true, "response_time_ms": 15.3},
    "connection_pool": {"healthy": true, "active": 5, "idle": 10},
    "data_quality": {"healthy": true, "recent_data_points": 10000}
  },
  "services": {
    "curve_fitting": {"available": true},
    "optimization": {"available": true},
    "data_import": {"available": true}
  }
}
```

### GET /api/v1/monitoring/db-health
**文件路径**：app/api/v1/endpoints/monitoring.py
**函数名**：`db_health_check()`
**用途**：数据库健康检查
**响应**：Dict[str, Any]（包含healthy、response_time_ms、connection_count）

**响应示例**：
```json
{
  "healthy": true,
  "response_time_ms": 12.5,
  "connection_count": 15,
  "database_version": "PostgreSQL 16.0",
  "timescaledb_version": "2.11.0"
}
```

### GET /api/v1/monitoring/pool-stats
**文件路径**：app/api/v1/endpoints/monitoring.py
**函数名**：`connection_pool_stats()`
**用途**：连接池统计信息
**响应**：Dict[str, Any]（包含pool_size、active、idle、wait_time_ms）

**响应示例**：
```json
{
  "pool_size": 20,
  "active": 5,
  "idle": 15,
  "wait_time_ms": 2.3,
  "total_connections_created": 100,
  "total_connections_closed": 80
}
```

### GET /api/v1/monitoring/performance
**文件路径**：app/api/v1/endpoints/monitoring.py
**函数名**：`system_performance()`
**用途**：系统性能指标
**响应**：Dict[str, Any]（包含cpu_percent、memory_percent、disk_usage）

**响应示例**：
```json
{
  "cpu_percent": 45.2,
  "memory_percent": 62.8,
  "disk_usage": {
    "total_gb": 500,
    "used_gb": 320,
    "free_gb": 180,
    "percent": 64.0
  },
  "process_info": {
    "pid": 12345,
    "threads": 10,
    "open_files": 50
  }
}
```

### GET /api/v1/monitoring/devices
**文件路径**：app/api/v1/endpoints/monitoring.py
**函数名**：`get_devices()`
**用途**：获取设备状态列表
**请求参数**：
- `station_id` (Optional[int]): 按泵站ID筛选
- `status` (Optional[str]): 按状态筛选 (online/offline/warning)
- `limit` (int): 返回数量限制 (默认100, 最大1000)
- `offset` (int): 分页偏移量 (默认0)

**响应**：DevicesResponse

**响应示例**：
```json
{
  "devices": [
    {
      "device_id": 101,
      "device_name": "1号泵",
      "station_id": 1,
      "station_name": "主泵站",
      "status": "online",
      "last_seen": "2025-09-30T12:00:00Z",
      "metrics": {
        "flow_rate": 120.5,
        "pressure": 0.45,
        "power": 55.2
      }
    }
  ],
  "total": 50,
  "online_count": 45,
  "offline_count": 3,
  "warning_count": 2
}
```

### GET /api/v1/monitoring/devices/{device_id}
**文件路径**：app/api/v1/endpoints/monitoring.py
**函数名**：`get_device_detail()`
**用途**：获取设备详细信息
**路径参数**：
- `device_id` (int): 设备ID

**响应**：Dict[str, Any]（包含设备详细状态、历史数据趋势等）

**响应示例**：
```json
{
  "device_id": 101,
  "device_name": "1号泵",
  "station_id": 1,
  "station_name": "主泵站",
  "status": "online",
  "last_seen": "2025-09-30T12:00:00Z",
  "current_metrics": {
    "flow_rate": 120.5,
    "pressure": 0.45,
    "power": 55.2,
    "efficiency": 0.85
  },
  "trends": {
    "flow_rate_24h": [115.2, 118.3, 120.5],
    "power_24h": [52.1, 54.3, 55.2]
  },
  "alerts": [
    {
      "type": "warning",
      "message": "效率略低于正常范围",
      "timestamp": "2025-09-30T11:30:00Z"
    }
  ]
}
```

---

## 数据导入API（data_admin.py）

### POST /api/v1/import/csv
**文件路径**：app/api/v1/endpoints/data_admin.py
**用途**：导入CSV文件
**请求体**：
- file (UploadFile): CSV文件
- station_id (str): 泵站ID
- source_hint (Optional[str]): 数据来源提示

**响应**：Dict[str, Any]（包含success、imported_rows、rejected_rows、errors）

---

## 统计API（data_admin.py）

### GET /api/v1/stats/import
**文件路径**：app/api/v1/endpoints/data_admin.py
**用途**：获取导入统计信息
**请求参数**：
- start_date (Optional[date]): 开始日期
- end_date (Optional[date]): 结束日期

**响应**：Dict[str, Any]（包含total_imports、total_rows、success_rate）

---

## 文档完成状态

✅ **时序数据API**：4个端点
- GET /api/v1/measurements（已废弃）
- GET /api/v1/stations/{id}/measurements
- GET /api/v1/devices/{id}/measurements
- GET /api/v1/stations/{id}/raw

✅ **管理API**：3个端点
- GET /api/v1/stations
- GET /api/v1/stations/{id}/devices
- GET /api/v1/metrics

✅ **监控API**：6个端点（新增4个）
- GET /api/v1/monitoring/health
- GET /api/v1/monitoring/db-health ← 新增
- GET /api/v1/monitoring/pool-stats ← 新增
- GET /api/v1/monitoring/performance ← 新增
- GET /api/v1/monitoring/devices
- GET /api/v1/monitoring/devices/{id} ← 新增

✅ **数据导入API**：1个端点
- POST /api/v1/import/csv

✅ **统计API**：1个端点
- GET /api/v1/stats/import

**总计**：15个核心API端点（从11个增加到15个）

---

## 更新历史

- **2025-09-30 12:20**：全量更新，补充了4个缺失的监控API端点（db-health、pool-stats、performance、devices/{id}），包含15个核心API端点的详细信息（路径、用途、请求参数、响应格式、响应示例）
- **2025-09-30 10:00**：初始版本，包含11个核心API端点
