"""
pump_head 数据过滤模块
"""

import pandas as pd
import numpy as np
import logging


class DataFilter:
    """数据过滤器"""

    def __init__(self, params: dict = None):
        """
        初始化数据过滤器

        Args:
            params: 过滤参数配置
        """
        self.logger = logging.getLogger(__name__)

        # 从参数中读取范围配置（不允许硬编码默认值）
        params = params or {}
        self.max_pump_inlet_pressure = params.get('max_pump_inlet_pressure')  # MPa
        self.max_main_pipeline_outlet_pressure = params.get('max_main_pipeline_outlet_pressure')  # MPa
        self.max_n_running = params.get('max_n_running')  # 最大运行泵数量

        # 验证必需参数
        missing_params = []
        if self.max_pump_inlet_pressure is None:
            missing_params.append('max_pump_inlet_pressure')
        if self.max_main_pipeline_outlet_pressure is None:
            missing_params.append('max_main_pipeline_outlet_pressure')
        if self.max_n_running is None:
            missing_params.append('max_n_running')

        if missing_params:
            self.logger.error(
                f"[DataFilter] pump_head data_filter缺少必需参数",
                extra={'extra_data': {
                    '缺失参数': missing_params,
                    '当前参数': params,
                    '错误': '必须在calculation_parameters表中配置这些参数'
                }}
            )
            raise ValueError(
                f"pump_head data_filter缺少必需参数: {', '.join(missing_params)}. "
                f"必须在calculation_parameters表中配置: metric_key='pump_head', method_id='data_filter'"
            )

    def filter(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        过滤数据

        Args:
            data: 输入数据

        Returns:
            pd.DataFrame: 过滤后的数据
        """
        if data.empty:
            self.logger.info("[数据过滤] 输入数据为空，跳过过滤")
            return data

        initial_count = len(data)
        self.logger.info(
            "[数据过滤] 开始过滤",
            extra={'extra_data': {'initial_count': initial_count}}
        )

        # 过滤1：运行状态过滤（只保留运行中的设备）
        if 'running' in data.columns:
            data = data[data['running'] == 1].copy()
            after_running = len(data)
            self.logger.info(
                "[数据过滤] 运行状态过滤完成",
                extra={'extra_data': {
                    'removed': initial_count - after_running,
                    'remaining': after_running
                }}
            )
        else:
            after_running = len(data)

        # 过滤2：NaN/Inf过滤（只过滤计算依赖的字段）
        required_columns = [
            'pump_inlet_pressure',
            'main_pipeline_outlet_pressure',
            'n_running'  # 注意：SQL 返回的列名是小写
        ]

        # 检查必需列是否存在
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            self.logger.warning(
                "[数据过滤] 缺少必需列",
                extra={'extra_data': {'missing_columns': missing_columns}}
            )
            return pd.DataFrame()

        # 过滤NaN和Inf
        data = data.replace([np.inf, -np.inf], np.nan)
        data = data.dropna(subset=required_columns)
        after_nan = len(data)

        self.logger.info(
            "[数据过滤] NaN/Inf过滤完成",
            extra={'extra_data': {
                'removed': after_running - after_nan,
                'remaining': after_nan
            }}
        )

        # 过滤3：范围过滤（使用配置参数）
        # 注意：不过滤 pump_flow_rate，因为扬程计算不依赖流量
        data = data[
            (data['pump_inlet_pressure'] >= 0) & (data['pump_inlet_pressure'] <= self.max_pump_inlet_pressure) &
            (data['main_pipeline_outlet_pressure'] >= 0) & (data['main_pipeline_outlet_pressure'] <= self.max_main_pipeline_outlet_pressure) &
            (data['n_running'] >= 0) & (data['n_running'] <= self.max_n_running)
        ].copy()

        final_count = len(data)

        self.logger.info(
            "[数据过滤] 范围过滤完成",
            extra={'extra_data': {
                'removed': after_nan - final_count,
                'remaining': final_count
            }}
        )

        self.logger.info(
            "[数据过滤] 过滤完成",
            extra={'extra_data': {
                'initial_count': initial_count,
                '最终数量': final_count,
                'total_removed': initial_count - final_count,
                'removal_rate': f"{(initial_count - final_count) / initial_count * 100:.2f}%"
            }}
        )

        return data

