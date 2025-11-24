"""
pump_flow_rate 流水线编排器

职责：
- 编排6个阶段的执行流程
- 管理阶段间的数据传递
- 记录完整的日志追踪（trace_id/span_id）
"""

from __future__ import annotations

from typing import Dict, Any
from datetime import datetime
import logging


class PumpFlowRatePipeline:
    """
    pump_flow_rate 流水线编排器

    职责：
    - 编排6个阶段的执行流程
    - 管理阶段间的数据传递
    - 记录完整的日志追踪
    """

    def __init__(self):
        """初始化流水线"""
        self.logger = logging.getLogger(__name__)

    def execute(
        self,
        station_id: int,
        device_id: int,
        start_time: datetime,
        end_time: datetime,
        task_id: str
    ) -> Dict[str, Any]:
        """
        执行完整的计算流水线

        Args:
            station_id: 泵站ID
            device_id: 设备ID
            start_time: 开始时间
            end_time: 结束时间
            task_id: 任务ID

        Returns:
            计算结果
        """
        from app.services.calculation.shared.shared_services import SharedServices
        from .data_loader import DataLoader
        from .data_filter import DataFilter
        from .method_selector import MethodSelector
        from .calculator import Calculator
        from .validator import Validator

        # Get shared services
        shared_services = SharedServices()

        import time

        # 时间范围字符串
        time_range_str = f"{start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_time.strftime('%Y-%m-%d %H:%M:%S')}"

        # Load parameters
        params = shared_services.parameter_manager.get_parameters(
            station_id=station_id,
            device_id=device_id,
            metric_key='pump_flow_rate'
        )

        # Stage 1: DataLoader
        self.logger.info(
            f"[Pipeline-Stage1-开始] DataLoader",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                '指标键': 'pump_flow_rate',
                'time_range': time_range_str
            }}
        )
        stage1_start = time.time()
        loader = DataLoader(trace_id=task_id)
        raw_data = loader.load_data(
            station_id=station_id,
            device_id=device_id,
            start_time=start_time,
            end_time=end_time
        )
        stage1_duration = time.time() - stage1_start
        self.logger.info(
            f"[Pipeline-Stage1-完成] DataLoader",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                '加载行数': len(raw_data),
                '耗时（毫秒）': round(stage1_duration * 1000, 2)
            }}
        )

        # 检查空数据：如果DataLoader返回空数据，跳过计算
        if raw_data.empty:
            self.logger.info(
                f"[Pipeline-跳过] 无数据可计算（设备类型不匹配或无原始数据）",
                extra={'extra_data': {
                    '任务ID': task_id,
                    '设备ID': device_id,
                    '指标键': 'pump_flow_rate',
                    '原因': '设备类型不匹配或无原始数据'
                }}
            )
            return {
                'success': True,
                '设备ID': device_id,
                '指标键': 'pump_flow_rate',
                'results_count': 0,
                'skipped': True,
                '原因': '设备类型不匹配或无原始数据'
            }

        # Stage 2: DataFilter
        self.logger.info(
            f"[Pipeline-Stage2-开始] DataFilter",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                'input_rows': len(raw_data)
            }}
        )
        stage2_start = time.time()

        # 从params获取参数（禁止使用默认值）
        max_flow = params.get('max_flow')
        max_power = params.get('max_power')
        max_freq = params.get('max_freq')

        # 验证参数存在性
        if max_flow is None or max_power is None or max_freq is None:
            missing = []
            if max_flow is None:
                missing.append('max_flow')
            if max_power is None:
                missing.append('max_power')
            if max_freq is None:
                missing.append('max_freq')

            self.logger.error(
                f"[Pipeline] DataFilter缺少必需参数",
                extra={'extra_data': {
                    '任务ID': task_id,
                    '设备ID': device_id,
                    '缺失参数': missing,
                    '错误': '必须在calculation_parameters表中配置这些参数'
                }}
            )
            raise ValueError(
                f"DataFilter缺少必需参数: {', '.join(missing)}. "
                f"必须在calculation_parameters表中配置: metric_key='pump_flow_rate', method_id='data_filter'"
            )

        filter = DataFilter(
            max_flow=max_flow,
            max_power=max_power,
            max_freq=max_freq,
            station_id=station_id,  # 传递 station_id 用于出水检测
            trace_id=task_id
        )
        filtered_data = filter.filter_data(raw_data)
        stage2_duration = time.time() - stage2_start
        filter_ratio = (1 - len(filtered_data) / len(raw_data)) * 100 if len(raw_data) > 0 else 0
        self.logger.info(
            f"[Pipeline-Stage2-完成] DataFilter",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                'input_rows': len(raw_data),
                'output_rows': len(filtered_data),
                '过滤比例': f"{filter_ratio:.2f}%",
                '耗时（毫秒）': round(stage2_duration * 1000, 2)
            }}
        )

        # Stage 3: MethodSelector
        self.logger.info(
            f"[Pipeline-Stage3-开始] MethodSelector",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                '数据行数': len(filtered_data)
            }}
        )
        stage3_start = time.time()
        selector = MethodSelector(params=params, trace_id=task_id)
        selected_method = selector.select_method(filtered_data)
        stage3_duration = time.time() - stage3_start
        self.logger.info(
            f"[Pipeline-Stage3-完成] MethodSelector",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                '选择的方法': selected_method,
                '耗时（毫秒）': round(stage3_duration * 1000, 2)
            }}
        )

        # Stage 4: Calculator
        self.logger.info(
            f"[Pipeline-Stage4-开始] Calculator",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                '方法ID': selected_method,
                'parameters': params
            }}
        )
        stage4_start = time.time()
        calculator = Calculator(trace_id=task_id)
        calc_result = calculator.calculate(
            data=filtered_data,
            method_id=selected_method,
            params=params
        )
        stage4_duration = time.time() - stage4_start
        self.logger.info(
            f"[Pipeline-Stage4-完成] Calculator",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                '方法ID': selected_method,
                '计算行数': len(calc_result),
                '耗时（毫秒）': round(stage4_duration * 1000, 2)
            }}
        )

        # Stage 5: Validator
        self.logger.info(
            f"[Pipeline-Stage5-开始] Validator",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                'input_rows': len(calc_result)
            }}
        )
        stage5_start = time.time()
        validator = Validator(params=params)
        validation_result = validator.validate(calc_result, filtered_data)
        validated_result = validation_result['valid_results']
        valid_count = validation_result['valid_count']
        invalid_count = validation_result['invalid_count']
        stage5_duration = time.time() - stage5_start
        validation_pass_rate = (valid_count / len(calc_result)) * 100 if len(calc_result) > 0 else 0
        self.logger.info(
            f"[Pipeline-Stage5-完成] Validator",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                'valid_count': valid_count,
                'invalid_count': invalid_count,
                'validation_pass_rate': f"{validation_pass_rate:.2f}%",
                '耗时（毫秒）': round(stage5_duration * 1000, 2)
            }}
        )

        # Stage 6: DataWriter
        # 只写入有效数据
        self.logger.info(
            f"[Pipeline-Stage6-开始] DataWriter",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                'valid_count': valid_count
            }}
        )
        stage6_start = time.time()
        written_count = 0
        if valid_count > 0:
            # Convert DataFrame to List[WriteRecord]
            from app.services.calculation.shared.data_writer import WriteRecord
            from datetime import datetime
            import pytz

            # 获取当前时间（上海时区）
            TZ_SH = pytz.timezone('Asia/Shanghai')
            calculated_at = datetime.now(TZ_SH)

            records = []
            for _, row in validated_result.iterrows():
                records.append(WriteRecord(
                    device_id=device_id,
                    metric_key='pump_flow_rate',
                    timestamp=row['ts_bucket'],
                    value=float(row['pump_flow_rate']),
                    quality_code=int(row.get('quality_code', 0)),
                    method_id=selected_method,  # 使用选择的计算方法ID
                    calculated_at=calculated_at  # 计算时间
                ))

            written_count = shared_services.data_writer.write(records, station_id=station_id)
        else:
            self.logger.warning(
                "[流水线] 跳过数据写入: 没有有效数据",
                extra={'extra_data': {
                    '任务ID': task_id,
                    '设备ID': device_id,
                    'total_count': len(validated_result),
                    'valid_count': valid_count
                }}
            )

        stage6_duration = time.time() - stage6_start
        self.logger.info(
            f"[Pipeline-Stage6-完成] DataWriter",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                'written_count': written_count,
                '耗时（毫秒）': round(stage6_duration * 1000, 2)
            }}
        )

        return {
            'written_count': written_count,
            '任务ID': task_id
        }
        # 阶段1: DataLoader
        # 阶段2: DataFilter
        # 阶段3: MethodSelector
        # 阶段4: Calculator
        # 阶段5: Validator
        # 阶段6: DataWriter
        pass

