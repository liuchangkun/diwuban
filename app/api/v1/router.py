from fastapi import APIRouter

from app.api.v1.endpoints import data_admin, data_timeseries, logs, monitoring

api_v1_router = APIRouter()

# 数据端点（拆分后注册）：
api_v1_router.include_router(
    data_admin.router, prefix="/data", tags=["data"]
)  # 管理与清单
api_v1_router.include_router(
    data_timeseries.router, prefix="/data", tags=["data"]
)  # 时序

# 其它端点
api_v1_router.include_router(
    monitoring.router, prefix="/monitoring", tags=["monitoring"]
)
api_v1_router.include_router(logs.router, prefix="/logs", tags=["logs"])
