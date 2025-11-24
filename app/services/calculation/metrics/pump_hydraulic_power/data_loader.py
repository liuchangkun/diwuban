"""
pump_hydraulic_power DataLoader模块

职责：从数据库加载计算所需的依赖指标数据
"""

import pandas as pd
from datetime import datetime
from typing import Optional
from app.adapters.db import get_connection


class DataLoader:
    """数据加载器"""

    def __init__(self, trace_id: str = ""):
        """
        初始化DataLoader

        Args:
            trace_id: 追踪ID
        """
        self.trace_id = trace_id

    def load(
        self,
        station_id: int,
        device_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """
        加载计算所需的依赖指标数据

        Args:
            station_id: 泵站ID
            device_id: 设备ID
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            pd.DataFrame: 包含pump_flow_rate和pump_head的数据
        """
        print(f"[{self.trace_id}] [DataLoader] 开始加载数据...")
        print(f"  - station_id: {station_id}")
        print(f"  - device_id: {device_id}")
        print(f"  - start_time: {start_time}")
        print(f"  - end_time: {end_time}")

        # SQL查询：加载pump_flow_rate和pump_head
        sql = """
        SELECT
            fm.ts_bucket,
            fm.device_id,
            fm.metric_id,
            fm.value,
            dr.running
        FROM fact_measurements fm
        LEFT JOIN mv_device_running_1s dr
            ON fm.ts_bucket = dr.ts_bucket
            AND fm.device_id = dr.device_id
        WHERE fm.station_id = %(station_id)s
          AND fm.device_id = %(device_id)s
          AND fm.metric_id IN (14, 17)  -- pump_flow_rate(14), pump_head(17)
          AND fm.ts_bucket >= %(start_time)s
          AND fm.ts_bucket < %(end_time)s
        ORDER BY fm.ts_bucket, fm.device_id
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

        print(f"  - 原始数据行数: {len(df)}")

        if df.empty:
            print(f"  - ⚠️ 未找到数据")
            return pd.DataFrame()

        # 数据透视：将长表转换为宽表
        df_pivot = df.pivot_table(
            index=['ts_bucket', 'device_id', 'running'],
            columns='metric_id',
            values='value',
            aggfunc='first'
        ).reset_index()

        # 重命名列
        df_pivot.columns.name = None
        df_pivot = df_pivot.rename(columns={
            14: 'pump_flow_rate',
            17: 'pump_head'
        })

        # 确保必需列存在
        for col in ['pump_flow_rate', 'pump_head']:
            if col not in df_pivot.columns:
                df_pivot[col] = None

        print(f"  - 透视后数据行数: {len(df_pivot)}")
        print(f"  - 列: {list(df_pivot.columns)}")

        # 显示样本数据
        if not df_pivot.empty:
            sample = df_pivot.head(3)
            print(f"  - 样本数据（前3行）:")
            for idx, row in sample.iterrows():
                print(f"    {row['ts_bucket']} | device={row['device_id']} | "
                      f"Q={row['pump_flow_rate']:.2f} m³/h | H={row['pump_head']:.2f} m | "
                      f"running={row['running']}")

        return df_pivot

