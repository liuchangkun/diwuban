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
            - pool_liquid_level: 水池液位（m）
            - pump_flow_rate: 水泵流量（m³/h）
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

        # 检查设备类型：pump_inlet_pressure 只计算 type='pump' 的设备
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
                        "[数据加载] 跳过非泵设备（pump_inlet_pressure只计算type='pump'的设备）",
                        extra={'extra_data': {
                            '追踪ID': self.trace_id,
                            '设备ID': device_id,
                            '设备名称': device_name,
                            '设备类型': device_type,
                            '原因': 'pump_inlet_pressure只计算type=pump的设备'
                        }}
                    )
                    return pd.DataFrame()

        # 单个SQL查询获取所有数据
        # 注意：pool_liquid_level 来自水池液位传感器（通常是 device_id=8），pump_flow_rate 来自当前泵设备
        sql = """
            WITH metric_ids AS (
                SELECT id, metric_key
                FROM dim_metric_config
                WHERE metric_key IN (
                    'pool_liquid_level',
                    'pump_flow_rate'
                )
            )
            SELECT
                fm.ts_bucket,
                fm.device_id,
                mc.metric_key,
                fm.value,
                COALESCE(dr.running, 1) AS running  -- 处理 NULL：清水池等设备没有运行状态，默认为1
            FROM fact_measurements fm
            JOIN metric_ids mc ON mc.id = fm.metric_id
            LEFT JOIN mv_device_running_1s dr
                ON dr.station_id = fm.station_id
               AND dr.device_id = fm.device_id
               AND dr.ts_bucket = fm.ts_bucket
            WHERE fm.station_id = %(station_id)s
              AND fm.ts_bucket >= %(start_time)s
              AND fm.ts_bucket < %(end_time)s
              AND (
                  (mc.metric_key = 'pump_flow_rate' AND fm.device_id = %(device_id)s)
                  OR (mc.metric_key = 'pool_liquid_level')
              )
            ORDER BY fm.ts_bucket, fm.device_id, mc.metric_key
        """

        start = time.time()

        # 执行SQL查询
        from app.adapters.db.pool import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {
                    '泵站ID': station_id,
                    '设备ID': device_id,
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
            params={'泵站ID': station_id, '设备ID': device_id, 'start_time': start_time, 'end_time': end_time},
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
        # 注意：pool_liquid_level 和 pump_flow_rate 来自不同设备，需要分别处理

        # 1. 提取 pool_liquid_level（来自水池液位传感器，通常是设备8）
        df_pool = df_raw[df_raw['metric_key'] == 'pool_liquid_level'][['ts_bucket', 'value', 'device_id']].copy()
        df_pool.rename(columns={'value': 'pool_liquid_level'}, inplace=True)
        df_pool = df_pool.drop_duplicates(subset=['ts_bucket'])  # 每个时间戳只保留一个值

        # 记录 pool_liquid_level 数据来源
        pool_device_ids = df_pool['device_id'].unique().tolist() if not df_pool.empty else []
        df_pool = df_pool.drop(columns=['device_id'])  # 删除设备ID列，避免合并冲突

        # 2. 提取 pump_flow_rate（来自当前泵设备）
        df_pump = df_raw[
            (df_raw['metric_key'] == 'pump_flow_rate') &
            (df_raw['device_id'] == device_id)
        ][['ts_bucket', 'value', 'running']].copy()
        df_pump.rename(columns={'value': 'pump_flow_rate'}, inplace=True)
        df_pump = df_pump.drop_duplicates(subset=['ts_bucket'])  # 每个时间戳只保留一个值

        # 3. 按时间戳合并（使用 left join 保留所有 pump_flow_rate 数据）
        df_final = df_pump.merge(df_pool, on='ts_bucket', how='left')
        df_final['device_id'] = device_id  # 添加设备ID列

        # 统计数据质量
        pool_missing_count = df_final['pool_liquid_level'].isna().sum()
        pool_coverage = (len(df_final) - pool_missing_count) / len(df_final) * 100 if len(df_final) > 0 else 0

        # 添加详细的数据样本日志
        sample_data = {}
        if not df_final.empty:
            # 获取前3行和后3行作为样本
            sample_indices = list(df_final.index[:3]) + list(df_final.index[-3:])
            sample_data = {
                'sample_rows': [
                    {
                        'ts_bucket': str(df_final.loc[idx, 'ts_bucket']),
                        'pump_flow_rate': float(df_final.loc[idx, 'pump_flow_rate']),
                        'pool_liquid_level': float(df_final.loc[idx, 'pool_liquid_level']) if not pd.isna(df_final.loc[idx, 'pool_liquid_level']) else None,
                        'running': int(df_final.loc[idx, 'running'])
                    }
                    for idx in sample_indices[:6]  # 最多6行
                ]
            }

        # 直接打印到控制台（用于调试）
        print(f"\n{'='*100}")
        print(f"[数据加载] 数据透视完成 - 设备{device_id}")
        print(f"{'='*100}")
        print(f"  pump_flow_rate_rows: {len(df_pump)}")
        print(f"  pool_liquid_level_rows: {len(df_pool)}")
        print(f"  pool_device_ids: {pool_device_ids}")
        print(f"  final_rows: {len(df_final)}")
        print(f"  pool_missing_count: {pool_missing_count}")
        print(f"  pool_coverage_pct: {pool_coverage:.2f}%")
        if sample_data:
            print(f"\n  样本数据（前3行+后3行）:")
            for i, row in enumerate(sample_data['sample_rows'], 1):
                print(f"    {i}. {row}")
        print(f"{'='*100}\n")

        self.logger.info(
            "[数据加载] 数据透视完成",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '设备ID': device_id,
                'pump_flow_rate_rows': len(df_pump),
                'pool_liquid_level_rows': len(df_pool),
                'pool_device_ids': pool_device_ids,
                '最终行数': len(df_final),
                'pool_missing_count': pool_missing_count,
                'pool_coverage_pct': f"{pool_coverage:.2f}",
                '时间跨度（小时）': f"{(df_final['ts_bucket'].max() - df_final['ts_bucket'].min()).total_seconds() / 3600:.2f}" if not df_final.empty else 0,
                **sample_data
            }}
        )

        # 如果 pool_liquid_level 缺失率过高，记录警告
        if pool_coverage < 50:
            self.logger.warning(
                "[数据加载] pool_liquid_level 数据缺失严重",
                extra={'extra_data': {
                    '追踪ID': self.trace_id,
                    '设备ID': device_id,
                    'pool_coverage_pct': f"{pool_coverage:.2f}",
                    'pool_device_ids': pool_device_ids,
                    'suggestion': '检查设备8（水池液位传感器）的数据是否正常'
                }}
            )

        return df_final

