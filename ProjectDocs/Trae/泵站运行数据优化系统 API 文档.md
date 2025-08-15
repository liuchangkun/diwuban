# 泵站运行数据优化系统 API 文档

## 🔧 如何使用本规范
- 开发：优先按照接口定义先写 Pydantic Schema → 编写路由与业务逻辑 → 对照示例请求/响应自测
- 测试：按路径+方法+场景组织用例，覆盖 2xx/4xx/5xx；验证错误码、字段必选/可选与边界值
- 联调：用统一的请求示例与 Mock 数据；在 Swagger UI 验证示例是否可执行
- 上线清单：接口变更记录、版本号、兼容策略（新增/变更/废弃）、灰度与回滚

---

## 1. API 概述

### 1.1 基本信息
- **API版本**: v1.0
- **基础URL**: `http://localhost:8000/api/v1`

- **数据格式**: JSON
- **字符编码**: UTF-8

### 1.2 通用响应格式
```json
{
  "success": true,
  "code": 200,
  "message": "操作成功",
  "data": {},
  "timestamp": "2025-01-28T10:30:00Z",
  "request_id": "req_123456789"
}
```

### 1.3 错误响应格式
```json
{
  "success": false,
  "code": 400,
  "message": "请求参数错误",
  "error": {
    "type": "ValidationError",
    "details": "字段 'flow_rate' 必须为正数"
  },
  "timestamp": "2025-01-28T10:30:00Z",
  "request_id": "req_123456789"
}
```



## 2. 泵站管理接口

### 2.1 获取泵站列表
```http
GET /stations
```

**查询参数**:
- `page`: 页码（默认: 1）
- `size`: 每页数量（默认: 20）
- `station_type`: 泵站类型（supply/intake）
- `phase`: 期数（phase1/phase2）

**响应**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "station_name": "一期供水泵房",
        "station_code": "PHASE1_SUPPLY",
        "station_type": "supply",
        "phase": "phase1",
        "location": "主厂区东侧",
        "capacity": 1000.0,
        "device_count": 4,
        "status": "active",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-28T10:30:00Z"
      }
    ],
    "total": 3,
    "page": 1,
    "size": 20,
    "pages": 1
  }
}
```

### 2.2 获取泵站详情
```http
GET /stations/{station_id}
```

**路径参数**:
- `station_id`: 泵站ID

**响应**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "station_name": "一期供水泵房",
    "station_code": "PHASE1_SUPPLY",
    "station_type": "supply",
    "phase": "phase1",
    "location": "主厂区东侧",
    "capacity": 1000.0,
    "devices": [
      {
        "id": 1,
        "device_name": "1#加压泵",
        "device_code": "PUMP_01",
        "device_type": "pump",
        "rated_power": 75.0,
        "rated_flow": 200.0,
        "rated_head": 45.0,
        "status": "active"
      }
    ],
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-28T10:30:00Z"
  }
}
```

### 2.3 创建泵站
```http
POST /stations
```

**请求体**:
```json
{
  "station_name": "三期供水泵房",
  "station_code": "PHASE3_SUPPLY",
  "station_type": "supply",
  "phase": "phase3",
  "location": "新厂区北侧",
  "capacity": 1500.0
}
```

## 3. 设备管理接口

### 3.1 获取设备列表
```http
GET /devices
```

**查询参数**:
- `station_id`: 泵站ID
- `device_type`: 设备类型（pump/variable_frequency/soft_start）
- `status`: 设备状态（active/inactive/maintenance）
- `page`: 页码
- `size`: 每页数量

### 3.2 获取设备详情
```http
GET /devices/{device_id}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "station_id": 1,
    "device_name": "1#加压泵",
    "device_code": "PUMP_01",
    "device_type": "pump",
    "device_number": "1",
    "rated_power": 75.0,
    "rated_flow": 200.0,
    "rated_head": 45.0,
    "rated_speed": 2950.0,
    "manufacturer": "格兰富",
    "model": "CR64-2",
    "install_date": "2024-01-15",
    "status": "active",
    "characteristic_curves": [
      {
        "id": 1,
        "curve_type": "head_flow",
        "fitting_method": "polynomial",
        "r_squared": 0.987,
        "is_active": true
      }
    ],
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-28T10:30:00Z"
  }
}
```

### 3.3 更新设备信息
```http
PUT /devices/{device_id}
```

**请求体**:
```json
{
  "device_name": "1#加压泵（已升级）",
  "status": "active",
  "rated_power": 90.0
}
```

## 4. 运行数据接口

### 4.1 获取运行数据
```http
GET /operation-data
```

**查询参数**:
- `station_id`: 泵站ID（必填）
- `device_id`: 设备ID（可选）
- `parameter_type`: 参数类型（可选）
- `start_time`: 开始时间（ISO 8601格式）
- `end_time`: 结束时间（ISO 8601格式）
- `aggregation`: 聚合方式（raw/minute/hour/day）
- `page`: 页码
- `size`: 每页数量（最大1000）

**响应**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "station_id": 1,
        "device_id": 1,
        "tag_name": "_一期_供水泵房_1#加压泵_有功功率_反馈",
        "data_time": "2025-01-28T10:30:00.000Z",
        "data_value": 45.5,
        "parameter_type": "active_power",
        "unit": "kW"
      }
    ],
    "total": 50000,
    "page": 1,
    "size": 100,
    "pages": 500,
    "aggregation": "raw",
    "time_range": {
      "start": "2025-01-28T00:00:00Z",
      "end": "2025-01-28T23:59:59Z"
    }
  }
}
```

### 4.2 批量导入运行数据
```http
POST /operation-data/import
```

**请求体**:
```json
{
  "station_id": 1,
  "device_id": 1,
  "data_source": "csv_file",
  "file_path": "/data/pump_data_20250128.csv",
  "parameter_mapping": {
    "有功功率": "active_power",
    "频率": "frequency",
    "电流": "current"
  },
  "time_column": "DataTime",
  "value_column": "DataValue",
  "tag_column": "TagName"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "import_id": "import_123456",
    "status": "processing",
    "total_records": 10000,
    "processed_records": 0,
    "failed_records": 0,
    "start_time": "2025-01-28T10:30:00Z",
    "estimated_completion": "2025-01-28T10:35:00Z"
  }
}
```

### 4.3 获取导入状态
```http
GET /operation-data/import/{import_id}/status
```

**响应**:
```json
{
  "success": true,
  "data": {
    "import_id": "import_123456",
    "status": "completed",
    "total_records": 10000,
    "processed_records": 9950,
    "failed_records": 50,
    "start_time": "2025-01-28T10:30:00Z",
    "completion_time": "2025-01-28T10:34:30Z",
    "duration_seconds": 270,
    "processing_rate": 37.0,
    "errors": [
      {
        "line": 1523,
        "error": "Invalid timestamp format",
        "data": "2025-13-45 25:70:80"
      }
    ]
  }
}
```

## 5. 特性曲线接口

### 5.1 获取特性曲线列表
```http
GET /characteristic-curves
```

**查询参数**:
- `device_id`: 设备ID
- `curve_type`: 曲线类型（head_flow/efficiency_flow/power_flow/npsh_flow）
- `fitting_method`: 拟合方法
- `min_r_squared`: 最小R²值
- `is_active`: 是否激活

**响应**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "device_id": 1,
        "curve_type": "head_flow",
        "fitting_method": "ensemble",
        "model_parameters": {
          "polynomial": {
            "coefficients": [45.2, -0.0012, -0.000001],
            "degree": 2
          },
          "weights": {
            "polynomial": 0.3,
            "svr": 0.25,
            "rf": 0.25,
            "mlp": 0.2
          }
        },
        "r_squared": 0.987,
        "rmse": 0.45,
        "mae": 0.32,
        "data_points_count": 1500,
        "validation_score": 0.982,
        "is_active": true,
        "fitting_date": "2025-01-28T08:00:00Z"
      }
    ],
    "total": 12,
    "page": 1,
    "size": 20
  }
}
```

### 5.2 拟合特性曲线
```http
POST /characteristic-curves/fit
```

**请求体**:
```json
{
  "device_id": 1,
  "curve_type": "head_flow",
  "fitting_methods": ["polynomial", "svr", "random_forest", "mlp"],
  "data_source": {
    "type": "database",
    "time_range": {
      "start": "2025-01-01T00:00:00Z",
      "end": "2025-01-28T23:59:59Z"
    },
    "filters": {
      "operating_conditions": "normal",
      "exclude_maintenance": true
    }
  },
  "validation": {
    "cross_validation_folds": 5,
    "test_size": 0.2,
    "physics_constraints": true
  },
  "ensemble": {
    "enabled": true,
    "weight_method": "performance_based"
  }
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "fitting_id": "fit_789012",
    "status": "processing",
    "device_id": 1,
    "curve_type": "head_flow",
    "estimated_completion": "2025-01-28T10:45:00Z",
    "progress": {
      "current_method": "polynomial",
      "completed_methods": 0,
      "total_methods": 4,
      "percentage": 5
    }
  }
}
```

### 5.3 获取拟合状态
```http
GET /characteristic-curves/fit/{fitting_id}/status
```

### 5.4 预测曲线值
```http
POST /characteristic-curves/{curve_id}/predict
```

**请求体**:
```json
{
  "input_values": [100, 150, 200, 250, 300],
  "input_parameter": "flow_rate",
  "additional_parameters": {
    "speed": 2950,
    "temperature": 20
  }
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "predictions": [
      {
        "input": 100,
        "predicted_value": 42.5,
        "confidence_interval": [41.8, 43.2],
        "prediction_quality": "high"
      }
    ],
    "curve_info": {
      "curve_type": "head_flow",
      "fitting_method": "ensemble",
      "r_squared": 0.987
    }
  }
}
```

## 6. 数据补齐接口

### 6.1 检测数据缺失
```http
POST /data-completion/detect-gaps
```

**请求体**:
```json
{
  "station_id": 1,
  "device_id": 1,
  "time_range": {
    "start": "2025-01-28T00:00:00Z",
    "end": "2025-01-28T23:59:59Z"
  },
  "expected_interval": 1,
  "parameter_types": ["active_power", "frequency", "current"]
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "gaps_detected": 15,
    "total_missing_points": 3420,
    "gaps": [
      {
        "parameter_type": "active_power",
        "start_time": "2025-01-28T10:15:30Z",
        "end_time": "2025-01-28T10:18:45Z",
        "duration_seconds": 195,
        "missing_points": 195,
        "gap_type": "sensor_failure"
      }
    ],
    "completeness_rate": 96.8,
    "quality_assessment": "good"
  }
}
```

### 6.2 执行数据补齐
```http
POST /data-completion/fill
```

**请求体**:
```json
{
  "station_id": 1,
  "device_id": 1,
  "time_range": {
    "start": "2025-01-28T00:00:00Z",
    "end": "2025-01-28T23:59:59Z"
  },
  "filling_methods": {
    "primary": "physics_based",
    "fallback": "ml_interpolation"
  },
  "parameters": {
    "use_characteristic_curves": true,
    "context_window": 300,
    "confidence_threshold": 0.8
  },
  "validation": {
    "cross_check": true,
    "physics_constraints": true
  }
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "completion_id": "comp_345678",
    "status": "processing",
    "total_gaps": 15,
    "total_missing_points": 3420,
    "estimated_completion": "2025-01-28T10:50:00Z",
    "progress": {
      "completed_gaps": 0,
      "filled_points": 0,
      "percentage": 0
    }
  }
}
```

### 6.3 获取补齐结果
```http
GET /data-completion/{completion_id}/result
```

**响应**:
```json
{
  "success": true,
  "data": {
    "completion_id": "comp_345678",
    "status": "completed",
    "summary": {
      "total_gaps": 15,
      "filled_gaps": 14,
      "failed_gaps": 1,
      "total_points_filled": 3225,
      "success_rate": 93.3
    },
    "method_performance": {
      "physics_based": {
        "gaps_handled": 12,
        "success_rate": 100,
        "average_confidence": 0.89
      },
      "ml_interpolation": {
        "gaps_handled": 2,
        "success_rate": 100,
        "average_confidence": 0.76
      }
    },
    "quality_metrics": {
      "overall_confidence": 0.87,
      "physics_consistency": 0.94,
      "temporal_smoothness": 0.91
    },
    "completion_time": "2025-01-28T10:48:30Z",
    "duration_seconds": 180
  }
}
```

## 7. 优化算法接口

### 7.1 创建优化任务
```http
POST /optimization/tasks
```

**请求体**:
```json
{
  "station_id": 1,
  "optimization_type": "multi_objective",
  "objectives": [
    {
      "name": "energy_efficiency",
      "type": "maximize",
      "weight": 0.4
    },
    {
      "name": "energy_cost",
      "type": "minimize",
      "weight": 0.4
    },
    {
      "name": "equipment_wear",
      "type": "minimize",
      "weight": 0.2
    }
  ],
  "constraints": {
    "flow_demand": {
      "min": 800,
      "max": 1200,
      "unit": "m3/h"
    },
    "pressure_requirement": {
      "min": 0.4,
      "unit": "MPa"
    },
    "pump_limits": {
      "max_simultaneous_pumps": 3,
      "min_operating_frequency": 30,
      "max_operating_frequency": 50
    }
  },
  "algorithms": [
    "genetic_algorithm",
    "particle_swarm",
    "differential_evolution",
    "reinforcement_learning"
  ],
  "time_horizon": {
    "start": "2025-01-29T00:00:00Z",
    "end": "2025-01-29T23:59:59Z",
    "resolution": "hour"
  },
  "optimization_parameters": {
    "population_size": 100,
    "max_generations": 500,
    "convergence_tolerance": 1e-6,
    "timeout_seconds": 300
  }
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "task_id": "opt_456789",
    "status": "queued",
    "station_id": 1,
    "optimization_type": "multi_objective",
    "estimated_duration": 300,
    "created_at": "2025-01-28T10:30:00Z",
    "queue_position": 1
  }
}
```

### 7.2 获取优化任务状态
```http
GET /optimization/tasks/{task_id}/status
```

**响应**:
```json
{
  "success": true,
  "data": {
    "task_id": "opt_456789",
    "status": "running",
    "progress": {
      "current_algorithm": "genetic_algorithm",
      "current_generation": 150,
      "total_generations": 500,
      "percentage": 30,
      "best_objective_value": 0.847,
      "convergence_trend": "improving"
    },
    "algorithms_status": {
      "genetic_algorithm": "running",
      "particle_swarm": "queued",
      "differential_evolution": "queued",
      "reinforcement_learning": "queued"
    },
    "start_time": "2025-01-28T10:32:00Z",
    "estimated_completion": "2025-01-28T10:37:00Z"
  }
}
```

### 7.3 获取优化结果
```http
GET /optimization/tasks/{task_id}/result
```

**响应**:
```json
{
  "success": true,
  "data": {
    "task_id": "opt_456789",
    "status": "completed",
    "optimization_results": {
      "best_solution": {
        "pump_settings": [
          {
            "device_id": 1,
            "operating_frequency": 45.5,
            "start_time": "00:00",
            "stop_time": "08:00"
          },
          {
            "device_id": 2,
            "operating_frequency": 42.0,
            "start_time": "08:00",
            "stop_time": "16:00"
          }
        ],
        "objective_values": {
          "energy_efficiency": 0.89,
          "energy_cost": 1250.5,
          "equipment_wear": 0.15
        },
        "overall_score": 0.847
      },
      "pareto_front": [
        {
          "solution_id": 1,
          "objective_values": {
            "energy_efficiency": 0.89,
            "energy_cost": 1250.5,
            "equipment_wear": 0.15
          }
        }
      ]
    },
    "algorithm_performance": {
      "genetic_algorithm": {
        "best_score": 0.847,
        "convergence_generation": 287,
        "execution_time": 45.2
      },
      "particle_swarm": {
        "best_score": 0.834,
        "convergence_iteration": 156,
        "execution_time": 32.1
      }
    },
    "performance_improvement": {
      "energy_savings": 15.3,
      "cost_reduction": 12.8,
      "efficiency_improvement": 8.5
    },
    "completion_time": "2025-01-28T10:36:45Z",
    "total_duration": 285
  }
}
```

### 7.4 应用优化方案
```http
POST /optimization/tasks/{task_id}/apply
```

**请求体**:
```json
{
  "solution_id": 1,
  "apply_immediately": false,
  "scheduled_start": "2025-01-29T00:00:00Z",
  "validation": {
    "simulate_first": true,
    "safety_checks": true
  },
  "rollback_plan": {
    "enabled": true,
    "trigger_conditions": [
      "efficiency_drop_5_percent",
      "pressure_below_threshold",
      "equipment_alarm"
    ]
  }
}
```

## 8. 系统监控接口

### 8.1 获取系统状态
```http
GET /system/status
```

**响应**:
```json
{
  "success": true,
  "data": {
    "system_health": "healthy",
    "uptime": 86400,
    "version": "1.0.0",
    "services": {
      "api_server": "running",
      "database": "running",
      "data_processor": "running",
      "optimization_engine": "running"
    },
    "performance": {
      "cpu_usage": 45.2,
      "memory_usage": 68.5,
      "disk_usage": 32.1,
      "active_connections": 15
    },
    "data_statistics": {
      "total_stations": 3,
      "total_devices": 15,
      "data_points_today": 1296000,
      "active_optimizations": 2
    }
  }
}
```

### 8.2 获取性能指标
```http
GET /system/metrics
```

**查询参数**:
- `time_range`: 时间范围（1h/6h/24h/7d）
- `metrics`: 指标类型（cpu/memory/disk/network/database）

### 8.3 获取系统日志
```http
GET /system/logs
```

**查询参数**:
- `level`: 日志级别（DEBUG/INFO/WARNING/ERROR）
- `start_time`: 开始时间
- `end_time`: 结束时间
- `component`: 组件名称
- `page`: 页码
- `size`: 每页数量

## 9. 数据分析接口

### 9.1 生成运行报告
```http
POST /analytics/reports
```

**请求体**:
```json
{
  "report_type": "efficiency_analysis",
  "station_id": 1,
  "time_range": {
    "start": "2025-01-01T00:00:00Z",
    "end": "2025-01-28T23:59:59Z"
  },
  "analysis_options": {
    "include_trends": true,
    "include_comparisons": true,
    "include_recommendations": true
  },
  "output_format": "pdf"
}
```

### 9.2 获取统计数据
```http
GET /analytics/statistics
```

**查询参数**:
- `station_id`: 泵站ID
- `metric`: 统计指标（efficiency/energy_consumption/operating_hours）
- `aggregation`: 聚合方式（daily/weekly/monthly）
- `time_range`: 时间范围

## 11. WebSocket 实时接口

### 11.1 实时数据订阅
```javascript
// WebSocket连接
const ws = new WebSocket('ws://localhost:8000/ws/realtime');

// 订阅消息
ws.send(JSON.stringify({
  "action": "subscribe",
  "channels": [
    "station.1.data",
    "optimization.status",
    "system.alerts"
  ],

}));

// 接收实时数据
ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

**实时数据格式**:
```json
{
  "channel": "station.1.data",
  "timestamp": "2025-01-28T10:30:00Z",
  "data": {
    "device_id": 1,
    "parameters": {
      "active_power": 45.5,
      "frequency": 49.8,
      "efficiency": 0.87
    }
  }
}
```

## 12. 错误代码说明

| 错误代码 | HTTP状态码 | 说明 |
|---------|-----------|------|
| 1001 | 400 | 请求参数错误 |

| 1004 | 404 | 资源不存在 |
| 1005 | 409 | 资源冲突 |
| 1006 | 422 | 数据验证失败 |
| 1007 | 429 | 请求频率过高 |
| 2001 | 500 | 内部服务器错误 |
| 2002 | 502 | 数据库连接错误 |
| 2003 | 503 | 服务暂时不可用 |
| 2004 | 504 | 请求超时 |
| 3001 | 400 | 数据导入格式错误 |
| 3002 | 400 | 特性曲线拟合失败 |
| 3003 | 400 | 优化算法收敛失败 |
| 3004 | 400 | 数据补齐失败 |

## 13. 限流规则

| 接口类型 | 限制 | 时间窗口 |
|---------|------|----------|
| 查询接口 | 100次/IP | 1分钟 |
| 数据导入 | 5次/IP | 1分钟 |
| 优化任务 | 3次/IP | 1小时 |
| 报告生成 | 10次/IP | 1小时 |

## 14. SDK 示例

### 14.1 Python SDK
```python
from pump_station_client import PumpStationClient

# 初始化客户端
client = PumpStationClient(
    base_url="http://localhost:8000/api/v1",
    username="admin",
    password="password123"
)

# 获取泵站列表
stations = client.stations.list()

# 获取运行数据
data = client.operation_data.get(
    station_id=1,
    start_time="2025-01-28T00:00:00Z",
    end_time="2025-01-28T23:59:59Z"
)

# 拟合特性曲线
fitting_task = client.curves.fit(
    device_id=1,
    curve_type="head_flow",
    methods=["polynomial", "svr", "mlp"]
)

# 创建优化任务
opt_task = client.optimization.create(
    station_id=1,
    objectives=["energy_efficiency", "cost_minimization"],
    constraints={"flow_demand": {"min": 800, "max": 1200}}
)
```

### 14.2 JavaScript SDK
```javascript
import { PumpStationAPI } from 'pump-station-sdk';

// 初始化API客户端
const api = new PumpStationAPI({
  baseURL: 'http://localhost:8000/api/v1',
  username: 'admin',
  password: 'password123'
});

// 获取实时数据
const realTimeData = await api.operationData.getRealTime({
  stationId: 1,
  parameters: ['active_power', 'frequency', 'efficiency']
});

// 订阅实时更新
api.realtime.subscribe('station.1.data', (data) => {
  console.log('Real-time update:', data);
});

// 创建优化任务
const optimization = await api.optimization.create({
  stationId: 1,
  type: 'multi_objective',
  objectives: [
    { name: 'energy_efficiency', type: 'maximize', weight: 0.6 },
    { name: 'energy_cost', type: 'minimize', weight: 0.4 }
  ]
});
```

---

**文档版本**: v1.0  
**最后更新**: 2025-01-28  
**维护团队**: 泵站优化系统开发团队