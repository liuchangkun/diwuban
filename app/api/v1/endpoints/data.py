"""
数据查询 API（非时序端点已迁移）
- 本文件仅保留兼容注释；实际业务端点已拆分：
  - data_timeseries.py：全部时序端点（/measurements、/stations/{id}/measurements、/devices/{id}/measurements、/raw）
  - data_admin.py：管理与清单端点（stations/devices 列表、统计、指标清单、导入统计）
"""

from fastapi import APIRouter

# 本文件已瘦身为“兼容占位”。实际端点已迁移：
# - data_timeseries.py：全部时序端点
# - data_admin.py：stations/devices 列表、统计、指标清单、导入统计
router = APIRouter()


# ========================= 新增：原始点位查询接口（不聚合） =========================
