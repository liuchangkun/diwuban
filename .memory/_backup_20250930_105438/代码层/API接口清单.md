# API接口清单

> 最后更新：2025-09-30
> 更新者：AI（已填充）

## 数据管理接口

### POST /api/v1/data/import
**用途**：导入CSV数据  
**请求体**：file, station_id  
**响应**：ImportResult

### GET /api/v1/data/timeseries
**用途**：查询时序数据  
**参数**：device_id, start_time, end_time  
**响应**：时序数据数组

### GET /api/v1/data/aggregated
**用途**：查询聚合数据  
**参数**：station_id, start_time, end_time, granularity  
**响应**：聚合数据数组

## 质量控制接口

### POST /api/v1/quality/check
**用途**：执行质量检查  
**请求体**：device_id, metric_id, start_time, end_time  
**响应**：质量检查结果

### POST /api/v1/quality/mark
**用途**：标注质量问题  
**请求体**：device_id, metric_id, start_time, end_time, quality_code  
**响应**：标注结果

## 曲线拟合接口

### POST /api/v1/curve/fit
**用途**：拟合特性曲线  
**请求体**：device_id, curve_type, data_points  
**响应**：拟合结果和参数

## 系统监控接口

### GET /health
**用途**：健康检查  
**响应**：数据库连接池状态

### GET /api/v1/monitoring/metrics
**用途**：获取系统性能指标  
**响应**：性能指标数据
