"""
pump_efficiency 数据加载模块
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
                - ts_bucket: 时间戳
                - pump_flow_rate: 泵瞬时流量 (m³/h)
                - pump_head: 泵扬程 (m)
                - pump_active_power: 泵有功功率 (kW)
        """
        self.logger.info(
            "[数据加载] 开始加载数据",
            extra={'extra_data': {
                '泵站ID': station_id,
                '设备ID': device_id,
                '开始时间': start_time.isoformat(),
                '结束时间': end_time.isoformat()
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
                        extra={'extra_data': {'设备ID': device_id}}
                    )
                    return pd.DataFrame()

                device_type, device_name = result

                if device_type != 'pump':
                    self.logger.info(
                        "[数据加载] 跳过非泵设备（pump_efficiency只计算type='pump'的设备）",
                        extra={'extra_data': {
                            '设备ID': device_id,
                            '设备名称': device_name,
                            '设备类型': device_type
                        }}
                    )
                    return pd.DataFrame()

        # SQL查询：加载3个依赖指标
        sql = """
        SELECT
            fm.ts_bucket,
            mc.metric_key,
            fm.value
        FROM fact_measurements fm
        JOIN dim_metric_config mc ON mc.id = fm.metric_id
        WHERE mc.metric_key IN ('pump_flow_rate', 'pump_head', 'pump_active_power')
          AND fm.device_id = %(device_id)s
          AND fm.ts_bucket >= %(start_time)s
          AND fm.ts_bucket < %(end_time)s
        ORDER BY fm.ts_bucket, mc.metric_key
        """

        with get_connection() as conn:
            df_raw = pd.read_sql(
                sql,
                conn,
                params={
                    'device_id': device_id,
                    'start_time': start_time,
                    'end_time': end_time
                }
            )

        if df_raw.empty:
            self.logger.warning(
                "[数据加载] 无数据",
                extra={'extra_data': {
                    '设备ID': device_id,
                    '开始时间': start_time.isoformat(),
                    '结束时间': end_time.isoformat()
                }}
            )
            return pd.DataFrame()

        # 透视：将长表转为宽表
        df_pivot = df_raw.pivot_table(
            index='ts_bucket',
            columns='metric_key',
            values='value',
            aggfunc='first'
        ).reset_index()

        self.logger.info(
            "[数据加载] 数据加载完成",
            extra={'extra_data': {
                '设备ID': device_id,
                '行数': len(df_pivot),
                '列名': list(df_pivot.columns),
                '时间范围': f"{df_pivot['ts_bucket'].min()} ~ {df_pivot['ts_bucket'].max()}" if len(df_pivot) > 0 else "N/A"
            }}
        )

        return df_pivot

