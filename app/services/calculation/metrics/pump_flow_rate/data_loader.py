"""
数据加载器（DataLoader）

职责：
- 从数据库加载原始数据
- JOIN mv_device_running_1s 获取运行状态
- 返回结构化数据（宽表格式）
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime
import pandas as pd
import time
import logging
import warnings

from app.core.logging.setup import log_sql


class DataLoader:
    """
    数据加载器

    职责：
    - 从 fact_measurements 表加载计算所需的依赖指标数据
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
            - main_pipeline_flow_rate: 总管流量
            - pump_active_power: 水泵有功功率
            - pump_frequency: 水泵频率
            - pump_cumulative_flow: 水泵累计流量（可选）
            - running: 运行状态（0=停止, 1=运行, NULL=无数据）
            - other_devices: 其他设备信息（JSON格式）
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

        # 检查设备类型：pump_flow_rate 只计算 type='pump' 的设备
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
                        "[数据加载] 跳过非泵设备（pump_flow_rate只计算type='pump'的设备）",
                        extra={'extra_data': {
                            '追踪ID': self.trace_id,
                            '设备ID': device_id,
                            '设备名称': device_name,
                            '设备类型': device_type,
                            '原因': 'pump_flow_rate只计算type=pump的设备'
                        }}
                    )
                    return pd.DataFrame()

        # 单个SQL查询获取所有数据
        sql = """
            WITH metric_ids AS (
                SELECT id, metric_key
                FROM dim_metric_config
                WHERE metric_key IN (
                    'main_pipeline_flow_rate',
                    'pump_active_power',
                    'pump_frequency',
                    'pump_cumulative_flow',
                    'main_pipeline_outlet_pressure'  -- 用于出水判断
                )
            ),
            device_ids AS (
                SELECT id
                FROM dim_devices
                WHERE station_id = %(station_id)s
            )
            SELECT
                fm.ts_bucket,
                fm.device_id,
                mc.metric_key,
                fm.value,
                COALESCE(dr.running, 1) AS running  -- 处理 NULL：主管道设备没有运行状态，默认为1
            FROM fact_measurements fm
            JOIN metric_ids mc ON mc.id = fm.metric_id
            JOIN device_ids d ON d.id = fm.device_id
            LEFT JOIN mv_device_running_1s dr
                ON dr.station_id = fm.station_id
               AND dr.device_id = fm.device_id
               AND dr.ts_bucket = fm.ts_bucket
            WHERE fm.station_id = %(station_id)s
              AND fm.ts_bucket >= %(start_time)s
              AND fm.ts_bucket < %(end_time)s
            ORDER BY fm.ts_bucket, fm.device_id, mc.metric_key
        """

        start = time.time()

        # 执行SQL查询
        # 使用 psycopg 连接执行查询（pandas 会发出警告，但这是正确的做法）
        # 注意：我们不使用 SQLAlchemy 引擎，因为项目使用自定义连接池
        from app.adapters.db.pool import get_connection

        with get_connection() as conn:
            # 使用 psycopg 的 cursor 执行查询，然后手动构建 DataFrame
            # 这样可以避免 pandas 的 SQLAlchemy 警告
            with conn.cursor() as cur:
                cur.execute(sql, {
                    '泵站ID': station_id,
                    'start_time': start_time,
                    'end_time': end_time
                })

                # 获取列名
                columns = [desc[0] for desc in cur.description]

                # 获取所有数据
                rows = cur.fetchall()

                # 构建 DataFrame
                df_raw = pd.DataFrame(rows, columns=columns)

        duration_ms = int((time.time() - start) * 1000)

        log_sql(
            sql,
            params={'泵站ID': station_id, 'start_time': start_time, 'end_time': end_time},
            duration_ms=duration_ms,
            rows=len(df_raw)
        )

        self.logger.info(
            "[数据加载] SQL查询完成",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '泵站ID': station_id,
                '设备ID': device_id,
                'raw_rows': len(df_raw),
                '耗时（毫秒）': duration_ms
            }}
        )

        if df_raw.empty:
            self.logger.warning(
                "[数据加载] 无数据",
                extra={'extra_data': {
                    '追踪ID': self.trace_id,
                    '泵站ID': station_id,
                    '设备ID': device_id
                }}
            )
            return pd.DataFrame()

        # 透视操作：将长表转为宽表
        df_pivot = df_raw.pivot_table(
            index=['ts_bucket', 'device_id'],
            columns='metric_key',
            values='value',
            aggfunc='first'  # 每个时间戳+设备+指标只有一个值
        ).reset_index()

        # 合并运行状态（每个时间戳+设备只有一个运行状态）
        df_running = df_raw[['ts_bucket', 'device_id', 'running']].drop_duplicates()
        df_final = df_pivot.merge(df_running, on=['ts_bucket', 'device_id'], how='left')

        # 分离当前设备、主管道设备和其他设备
        df_current = df_final[df_final['device_id'] == device_id].copy()

        # 查找主管道设备（通常是设备7，类型为 main_pipeline）
        # 主管道设备有 main_pipeline_flow_rate 数据
        df_main_pipeline = df_final[df_final['main_pipeline_flow_rate'].notna()].copy()

        # 如果当前设备没有 main_pipeline_flow_rate，从主管道设备获取
        if 'main_pipeline_flow_rate' not in df_current.columns or df_current['main_pipeline_flow_rate'].isna().all():
            if not df_main_pipeline.empty:
                # 只取主管道的 main_pipeline_flow_rate 列
                df_main_flow = df_main_pipeline[['ts_bucket', 'main_pipeline_flow_rate']].drop_duplicates('ts_bucket')
                # 合并到当前设备数据
                df_current = df_current.merge(df_main_flow, on='ts_bucket', how='left', suffixes=('', '_main'))
                # 如果有重复列，使用主管道的数据
                if 'main_pipeline_flow_rate_main' in df_current.columns:
                    df_current['main_pipeline_flow_rate'] = df_current['main_pipeline_flow_rate_main']
                    df_current = df_current.drop(columns=['main_pipeline_flow_rate_main'])

        # 如果当前设备没有 main_pipeline_outlet_pressure，从主管道设备获取（用于出水判断）
        if 'main_pipeline_outlet_pressure' not in df_current.columns or df_current['main_pipeline_outlet_pressure'].isna().all():
            if not df_main_pipeline.empty and 'main_pipeline_outlet_pressure' in df_main_pipeline.columns:
                df_main_pressure = df_main_pipeline[['ts_bucket', 'main_pipeline_outlet_pressure']].drop_duplicates('ts_bucket')
                df_current = df_current.merge(df_main_pressure, on='ts_bucket', how='left', suffixes=('', '_main'))
                if 'main_pipeline_outlet_pressure_main' in df_current.columns:
                    df_current['main_pipeline_outlet_pressure'] = df_current['main_pipeline_outlet_pressure_main']
                    df_current = df_current.drop(columns=['main_pipeline_outlet_pressure_main'])

        # 其他设备（排除当前设备和主管道设备）
        df_others = df_final[
            (df_final['device_id'] != device_id) &
            (df_final['main_pipeline_flow_rate'].isna())  # 排除主管道设备
        ].copy()

        # 聚合其他设备数据（按时间戳分组）
        if not df_others.empty:
            # 使用 include_groups=False 避免 FutureWarning
            # 这样 lambda 函数只接收非分组列的数据
            def aggregate_other_devices(group):
                return group[['device_id', 'pump_active_power', 'pump_frequency', 'running']].to_dict('records')

            df_others_grouped = df_others.groupby('ts_bucket', group_keys=False).apply(
                aggregate_other_devices,
                include_groups=False
            ).reset_index(name='other_devices')

            df_current = df_current.merge(df_others_grouped, on='ts_bucket', how='left')
        else:
            df_current['other_devices'] = None

        self.logger.info(
            "[数据加载] 数据透视完成",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '设备ID': device_id,
                '当前设备行数': len(df_current),
                '其他设备数量': len(df_others['device_id'].unique()) if not df_others.empty else 0,
                '时间跨度（小时）': f"{(df_current['ts_bucket'].max() - df_current['ts_bucket'].min()).total_seconds() / 3600:.2f}" if not df_current.empty else 0
            }}
        )

        return df_current

