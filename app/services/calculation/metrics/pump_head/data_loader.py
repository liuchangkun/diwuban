"""
pump_head 数据加载模块
"""

import pandas as pd
from datetime import datetime
import logging
from app.adapters.db.pool import get_connection


class DataLoader:
    """数据加载器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def load(
        self,
        station_id: int,
        device_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """
        加载计算所需的数据

        Args:
            station_id: 泵站ID
            device_id: 设备ID
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            pd.DataFrame: 包含所有依赖指标的数据
        """
        self.logger.info(
            "[数据加载] 开始加载数据",
            extra={'extra_data': {
                'station_id': station_id,
                'device_id': device_id,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }}
        )

        # 检查设备类型
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT type, name FROM dim_devices WHERE id = %s", (device_id,))
                result = cur.fetchone()

                if not result:
                    self.logger.warning(
                        "[数据加载] 设备不存在",
                        extra={'extra_data': {'device_id': device_id}}
                    )
                    return pd.DataFrame()

                device_type, device_name = result

                if device_type != 'pump':
                    self.logger.info(
                        "[数据加载] 跳过非泵设备（pump_head只计算type='pump'的设备）",
                        extra={'extra_data': {
                            'device_id': device_id,
                            'device_name': device_name,
                            'device_type': device_type
                        }}
                    )
                    return pd.DataFrame()

        # SQL查询：加载4个依赖指标 + 运行状态
        # 注意：main_pipeline_outlet_pressure 来自总管设备（device_id=7），其他指标来自当前泵设备
        sql = """
        WITH base_data AS (
            SELECT
                fm.ts_bucket,
                fm.device_id,
                mc.metric_key,
                fm.value
            FROM fact_measurements fm
            JOIN dim_metric_config mc ON mc.id = fm.metric_id
            WHERE fm.ts_bucket BETWEEN %(start_time)s AND %(end_time)s
              AND mc.metric_key IN (
                  'pump_inlet_pressure',
                  'main_pipeline_outlet_pressure',
                  'pump_flow_rate'
              )
              AND (
                  (mc.metric_key IN ('pump_inlet_pressure', 'pump_flow_rate') AND fm.device_id = %(device_id)s)
                  OR (mc.metric_key = 'main_pipeline_outlet_pressure')
              )
        ),
        running_status AS (
            SELECT
                ts_bucket,
                device_id,
                running
            FROM mv_device_running_1s
            WHERE device_id = %(device_id)s
              AND ts_bucket BETWEEN %(start_time)s AND %(end_time)s
        ),
        running_count AS (
            SELECT
                rs.ts_bucket,
                COUNT(*) FILTER (WHERE rs.running = 1) as N_running
            FROM mv_device_running_1s rs
            JOIN dim_devices d ON d.id = rs.device_id
            WHERE d.station_id = %(station_id)s
              AND d.type = 'pump'
              AND rs.ts_bucket BETWEEN %(start_time)s AND %(end_time)s
            GROUP BY rs.ts_bucket
        )
        SELECT
            bd.ts_bucket,
            MAX(CASE WHEN bd.metric_key = 'pump_inlet_pressure' AND bd.device_id = %(device_id)s THEN bd.value END) as pump_inlet_pressure,
            MAX(CASE WHEN bd.metric_key = 'main_pipeline_outlet_pressure' THEN bd.value END) as main_pipeline_outlet_pressure,
            MAX(CASE WHEN bd.metric_key = 'pump_flow_rate' AND bd.device_id = %(device_id)s THEN bd.value END) as pump_flow_rate,
            rs.running,
            rc.N_running
        FROM base_data bd
        LEFT JOIN running_status rs ON rs.ts_bucket = bd.ts_bucket
        LEFT JOIN running_count rc ON rc.ts_bucket = bd.ts_bucket
        GROUP BY bd.ts_bucket, rs.running, rc.N_running
        ORDER BY bd.ts_bucket
        """

        with get_connection() as conn:
            df = pd.read_sql(
                sql,
                conn,
                params={
                    'station_id': station_id,
                    'device_id': device_id,
                    'start_time': start_time,
                    'end_time': end_time
                }
            )

        self.logger.info(
            "[数据加载] 数据加载完成",
            extra={'extra_data': {
                'total_rows': len(df),
                'columns': list(df.columns)
            }}
        )

        return df

