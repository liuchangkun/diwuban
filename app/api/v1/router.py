from fastapi import APIRouter
from app.api.v1.endpoints import data, monitoring

api_v1_router = APIRouter()

api_v1_router.include_router(data.router, prefix="/data", tags=["data"])
api_v1_router.include_router(
    monitoring.router, prefix="/monitoring", tags=["monitoring"]
)
