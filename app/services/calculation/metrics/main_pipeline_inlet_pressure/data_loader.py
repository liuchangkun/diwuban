"""
数据加载器（DataLoader）

职责：
- 从数据库加载pool_liquid_level数据（来自device_id=8）
- JOIN mv_device_running_1s 获取运行状态
- 返回结构化数据（宽表格式）
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime
import pandas as pd
import logging

from app.core.logging.setup import log_sql


class DataLoader:
    """
    数据加载器
    
    职责：
    - 从 fact_measurements 表加载 pool_liquid_level 数据（metric_id=5, device_id=8）
    - 从 mv_device_running_1s 表加载设备运行状态数据
    - 只负责数据获取，不进行任何过滤（过滤由 DataFilter 负责）
    - 返回原始数据（包括停机设备的数据）
    """
    
    def __init__(self, trace_id: Optional[str] = None):
        """
        初始化数据加载器
        
        Args:
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id
    
    def load_data(
        self,
        station_id: int,
        device_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """
        加载计算所需的所有数据
        
        Args:
            station_id: 泵站ID
            device_id: 当前设备ID（应为7，总管设备）
            start_time: 开始时间
            end_time: 结束时间
        
        Returns:
            DataFrame with columns:
            - ts_bucket: 时间戳（秒级）
            - device_id: 设备ID（7）
            - pool_liquid_level: 水池液位（m，来自device_id=8）
            - running: 运行状态（0=停止, 1=运行, NULL=无数据）
        """
        self.logger.info(
            "[数据加载] 开始加载数据",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'station_id': station_id,
                'device_id': device_id,
                'start_time': str(start_time),
                'end_time': str(end_time)
            }}
        )
        
        # 检查设备类型：main_pipeline_inlet_pressure 只计算 device_id=7（总管设备）
        from app.adapters.db.pool import get_connection
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT type FROM dim_devices WHERE id = %s",
                    (device_id,)
                )
                row = cur.fetchone()
                if not row:
                    self.logger.warning(
                        f"[数据加载] 设备不存在: device_id={device_id}",
                        extra={'extra_data': {'trace_id': self.trace_id}}
                    )
                    return pd.DataFrame(columns=['ts_bucket', 'device_id', 'pool_liquid_level', 'running'])
                
                device_type = row[0]
                if device_type != 'main_pipeline':
                    self.logger.warning(
                        f"[数据加载] 设备类型不匹配: device_id={device_id}, type={device_type}, 期望type='main_pipeline'",
                        extra={'extra_data': {'trace_id': self.trace_id}}
                    )
                    return pd.DataFrame(columns=['ts_bucket', 'device_id', 'pool_liquid_level', 'running'])
        
        # 构建SQL查询
        # 注意：pool_liquid_level来自device_id=8，但running状态来自device_id=7
        sql = """
        SELECT
            fm.ts_bucket,
            %s as device_id,  -- 使用device_id=7（总管设备）
            fm.value as pool_liquid_level,
            dr.running
        FROM fact_measurements fm
        LEFT JOIN mv_device_running_1s dr
            ON fm.ts_bucket = dr.ts_bucket
            AND dr.device_id = %s  -- running状态来自device_id=7
        WHERE fm.station_id = %s
          AND fm.device_id = 8  -- pool_liquid_level来自device_id=8
          AND fm.metric_id = 18  -- pool_liquid_level的metric_id
          AND fm.ts_bucket >= %s
          AND fm.ts_bucket < %s
        ORDER BY fm.ts_bucket
        """
        
        params = (device_id, device_id, station_id, start_time, end_time)

        # 执行查询（使用cursor-based方法避免pandas警告）
        import time
        query_start = time.time()

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)

                # 获取列名
                columns = [desc[0] for desc in cur.description]

                # 获取所有数据
                rows = cur.fetchall()

                # 构建DataFrame
                df = pd.DataFrame(rows, columns=columns)

        query_duration_ms = int((time.time() - query_start) * 1000)

        # 记录SQL
        log_sql(
            sql,
            params={'device_id': device_id, 'station_id': station_id, 'start_time': start_time, 'end_time': end_time},
            duration_ms=query_duration_ms,
            rows=len(df)
        )

        self.logger.info(
            "[数据加载] 加载完成",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'loaded_rows': len(df),
                'duration_ms': query_duration_ms
            }}
        )
        
        return df

