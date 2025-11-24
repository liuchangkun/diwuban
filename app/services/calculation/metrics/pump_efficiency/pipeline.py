"""
pump_efficiency 流水线编排模块
"""

import logging
from datetime import datetime
from typing import Dict
import pytz

from app.services.calculation.shared.shared_services import SharedServices
from app.services.calculation.shared.data_writer import WriteRecord
from app.services.calculation.metrics.pump_efficiency.data_loader import DataLoader
from app.services.calculation.metrics.pump_efficiency.data_filter import DataFilter
from app.services.calculation.metrics.pump_efficiency.method_selector import MethodSelector
from app.services.calculation.metrics.pump_efficiency.calculator import Calculator
from app.services.calculation.metrics.pump_efficiency.validator import Validator


class PumpEfficiencyPipeline:
    """pump_efficiency 计算流水线"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_loader = DataLoader()
        self.data_filter = DataFilter()
        self.method_selector = MethodSelector()

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
                '指标键': 'pump_efficiency',
                '开始时间': start_time.isoformat(),
                '结束时间': end_time.isoformat()
            }}
        )

        # 获取共享服务
        shared_services = SharedServices()

        # 阶段1：数据加载
        data = self.data_loader.load(station_id, device_id, start_time, end_time)

        if data.empty:
            self.logger.info("[流水线] 数据为空，跳过计算", extra={'extra_data': {'设备ID': device_id, '指标键': 'pump_efficiency'}})
            return {'written_count': 0, 'task_id': task_id}

        # 阶段2：数据过滤
        filtered_data = self.data_filter.filter(data)

        if filtered_data.empty:
            self.logger.info("[流水线] 过滤后数据为空，跳过计算", extra={'extra_data': {'设备ID': device_id, '指标键': 'pump_efficiency'}})
            return {'written_count': 0, 'task_id': task_id}

        # 阶段3：方法选择
        selected_method = self.method_selector.select(filtered_data)

        if selected_method is None:
            self.logger.error("[流水线] 方法选择失败", extra={'extra_data': {'设备ID': device_id, '指标键': 'pump_efficiency'}})
            return {'written_count': 0, 'task_id': task_id}

        # 阶段4：计算执行
        calculator = Calculator(shared_services)
        result = calculator.calculate(filtered_data, selected_method, device_id)

        if result is None or result.empty:
            self.logger.error("[流水线] 计算失败", extra={'extra_data': {'设备ID': device_id, '指标键': 'pump_efficiency', '方法ID': selected_method}})
            return {'written_count': 0, 'task_id': task_id}

        # 阶段5：结果验证
        validator = Validator(shared_services)
        valid_result, is_valid = validator.validate(result, device_id)

        # 阶段6：数据写入
        write_records = []
        if is_valid.sum() > 0:
            # 获取当前时间（上海时区）
            TZ_SH = pytz.timezone('Asia/Shanghai')
            calculated_at = datetime.now(TZ_SH)

            for idx, row in valid_result.iterrows():
                if is_valid.loc[idx]:
                    write_records.append(WriteRecord(
                        device_id=device_id,
                        metric_key='pump_efficiency',
                        timestamp=row['ts_bucket'],
                        value=float(row['pump_efficiency']),
                        quality_code=int(row.get('quality_code', 0)),
                        method_id=selected_method,
                        calculated_at=calculated_at
                    ))

        if not write_records:
            self.logger.warning("[流水线] 没有有效数据可写入", extra={'extra_data': {'设备ID': device_id, '指标键': 'pump_efficiency', '方法ID': selected_method}})
            return {'written_count': 0, 'task_id': task_id}

        # 使用 SharedServices 的 data_writer 写入数据
        written_count = shared_services.data_writer.write(write_records, station_id=station_id)

        self.logger.info(
            "[流水线] 执行完成",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                '指标键': 'pump_efficiency',
                '方法ID': selected_method,
                '总数量': len(result),
                '有效数量': is_valid.sum(),
                '写入数量': written_count
            }}
        )

        return {
            'written_count': written_count,
            'task_id': task_id,
            'method': selected_method,
            'total_count': len(result),
            'valid_count': int(is_valid.sum())
        }

