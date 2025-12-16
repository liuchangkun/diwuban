"""
数据加载器（DataLoader）

职责：
- 从数据库加载pump_frequency数据
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
    - 从 fact_measurements 表加载 pump_frequency 数据
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
            device_id: 当前设备ID
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            DataFrame with columns:
            - ts_bucket: 时间戳（秒级）
            - device_id: 设备ID
            - pump_frequency: 水泵频率（Hz）
            - running: 运行状态（0=停止, 1=运行, NULL=无数据）
        """
        self.logger.info(
            "[数据加载] 开始加载数据",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '泵站ID': station_id,
                '设备ID': device_id,
                'start_time': str(start_time),
                'end_time': str(end_time)
            }}
        )

        # 检查设备类型：pump_speed 只计算 type='pump' 的设备
        from app.adapters.db.pool import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT type, name FROM dim_devices WHERE id = %s",
                    (device_id,)
                )
                result = cur.fetchone()

                if not result:
                    self.logger.warning(
                        "[数据加载] 设备不存在",
                        extra={'extra_data': {
                            '追踪ID': self.trace_id,
                            '设备ID': device_id
                        }}
                    )
                    return pd.DataFrame()

                device_type, device_name = result

                if device_type != 'pump':
                    self.logger.info(
                        "[数据加载] 跳过非泵设备（pump_speed只计算type='pump'的设备）",
                        extra={'extra_data': {
                            '追踪ID': self.trace_id,
                            '设备ID': device_id,
                            '设备名称': device_name,
                            '设备类型': device_type,
                            '原因': 'pump_speed只计算type=pump的设备'
                        }}
                    )
                    return pd.DataFrame()

        # 单个SQL查询获取所有数据
        sql = """
            WITH metric_ids AS (
                SELECT id, metric_key
                FROM dim_metric_config
                WHERE metric_key = 'pump_frequency'
            )
            SELECT
                fm.ts_bucket,
                fm.device_id,
                fm.value AS pump_frequency,
                COALESCE(dr.running, 1) AS running
            FROM fact_measurements fm
            JOIN metric_ids mc ON mc.id = fm.metric_id
            LEFT JOIN mv_device_running_1s dr
                ON dr.station_id = fm.station_id
               AND dr.device_id = fm.device_id
               AND dr.ts_bucket = fm.ts_bucket
            WHERE fm.station_id = %(station_id)s
              AND fm.device_id = %(device_id)s
              AND fm.ts_bucket >= %(start_time)s
              AND fm.ts_bucket < %(end_time)s
            ORDER BY fm.ts_bucket
        """

        params = {
            '泵站ID': station_id,
            '设备ID': device_id,
            'start_time': start_time,
            'end_time': end_time
        }

        # 执行查询
        # 使用 psycopg 的 cursor 执行查询，然后手动构建 DataFrame
        # 这样可以避免 pandas 的 SQLAlchemy 警告
        import time
        query_start = time.time()

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)

                # 获取列名
                columns = [desc[0] for desc in cur.description]

                # 获取所有数据
                rows = cur.fetchall()

                # 构建 DataFrame
                df = pd.DataFrame(rows, columns=columns)

        query_duration = time.time() - query_start

        self.logger.info(
            "[数据加载] 加载完成",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '加载行数': len(df),
                '耗时（毫秒）': round(query_duration * 1000, 2)
            }}
        )

        return df

