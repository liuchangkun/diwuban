"""
pump_head 流水线编排模块
"""

import logging
from datetime import datetime
from typing import Dict
import pytz

from app.services.calculation.shared.shared_services import SharedServices
from app.services.calculation.shared.data_writer import WriteRecord
from app.services.calculation.metrics.pump_head.data_loader import DataLoader
from app.services.calculation.metrics.pump_head.data_filter import DataFilter
from app.services.calculation.metrics.pump_head.method_selector import MethodSelector
from app.services.calculation.metrics.pump_head.calculator import Calculator
from app.services.calculation.metrics.pump_head.validator import Validator


class PumpHeadPipeline:
    """pump_head 计算流水线"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_loader = DataLoader()
        # DataFilter 和 Validator 将在 execute() 中使用 params 初始化
        self.method_selector = MethodSelector()
        self.calculator = Calculator()

    def execute(
        self,
        station_id: int,
        device_id: int,
        start_time: datetime,
        end_time: datetime,
        task_id: str
    ) -> Dict:
        """
        执行计算流水线

        Args:
            station_id: 泵站ID
            device_id: 设备ID
            start_time: 开始时间
            end_time: 结束时间
            task_id: 任务ID

        Returns:
            Dict: 执行结果
        """
        self.logger.info(
            "=" * 80,
            extra={'extra_data': {
                '任务ID': task_id,
                '泵站ID': station_id,
                '设备ID': device_id,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }}
        )

        # 获取共享服务
        shared_services = SharedServices()

        # 加载参数
        params = shared_services.parameter_manager.get_parameters(
            station_id=station_id,
            device_id=device_id,
            metric_key='pump_head'
        )

        self.logger.info(
            "[流水线] 参数加载完成",
            extra={'extra_data': {'参数': params}}
        )

        # 阶段1：数据加载
        data = self.data_loader.load(station_id, device_id, start_time, end_time)

        if data.empty:
            self.logger.info("[流水线] 数据为空，跳过计算")
            return {'written_count': 0, '任务ID': task_id}

        # 阶段2：数据过滤（使用 params 初始化）
        data_filter = DataFilter(params=params)
        filtered_data = data_filter.filter(data)

        if filtered_data.empty:
            self.logger.info("[流水线] 过滤后数据为空，跳过计算")
            return {'written_count': 0, '任务ID': task_id}

        # 阶段3：方法选择
        try:
            selected_method = self.method_selector.select_method(filtered_data, params)
        except ValueError as e:
            self.logger.error(f"[流水线] 方法选择失败: {e}")
            return {'written_count': 0, '任务ID': task_id}

        # 阶段4：计算执行
        pump_outlet_pressure_result, pump_head_result = self.calculator.calculate(
            filtered_data,
            selected_method,
            params
        )

        # 阶段5：结果验证（使用 params 初始化）
        validator = Validator(params=params)
        validated_outlet_pressure, validated_head, valid_outlet_count, valid_head_count = validator.validate(
            pump_outlet_pressure_result,
            pump_head_result
        )

        # 阶段6：数据写入
        written_count = 0

        if valid_outlet_count > 0 and valid_head_count > 0:
            TZ_SH = pytz.timezone('Asia/Shanghai')
            calculated_at = datetime.now(TZ_SH)

            # 写入 pump_outlet_pressure
            records_outlet = []
            for _, row in validated_outlet_pressure.iterrows():
                records_outlet.append(WriteRecord(
                    device_id=device_id,
                    metric_key='pump_outlet_pressure',
                    timestamp=row['ts_bucket'],
                    value=float(row['pump_outlet_pressure']),
                    quality_code=int(row.get('quality_code', 0)),
                    method_id=selected_method,
                    calculated_at=calculated_at
                ))

            written_count_outlet = shared_services.data_writer.write(records_outlet, station_id=station_id)

            # 写入 pump_head
            records_head = []
            for _, row in validated_head.iterrows():
                records_head.append(WriteRecord(
                    device_id=device_id,
                    metric_key='pump_head',
                    timestamp=row['ts_bucket'],
                    value=float(row['pump_head']),
                    quality_code=int(row.get('quality_code', 0)),
                    method_id=selected_method,
                    calculated_at=calculated_at
                ))

            written_count_head = shared_services.data_writer.write(records_head, station_id=station_id)

            written_count = written_count_outlet + written_count_head

            self.logger.info(
                "[流水线] 数据写入完成",
                extra={'extra_data': {
                    'pump_outlet_pressure_written': written_count_outlet,
                    'pump_head_written': written_count_head,
                    'total_written': written_count
                }}
            )

        self.logger.info("=" * 80)

        return {'written_count': written_count, '任务ID': task_id}

