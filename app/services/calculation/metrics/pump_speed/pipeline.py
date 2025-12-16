"""
pump_speed 流水线编排器

职责：
- 编排6个阶段的执行流程
- 管理阶段间的数据传递
- 记录完整的日志追踪（trace_id/span_id）
"""

from __future__ import annotations

from typing import Dict, Any
from datetime import datetime
import logging


class PumpSpeedPipeline:
    """
    pump_speed 流水线编排器

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
            metric_key='pump_speed'
        )

        # Stage 1: DataLoader
        self.logger.info(
            f"[Pipeline-Stage1-开始] DataLoader",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                '指标键': 'pump_speed',
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
                    '指标键': 'pump_speed',
                    '原因': '设备类型不匹配或无原始数据'
                }}
            )
            return {
                'success': True,
                '设备ID': device_id,
                '指标键': 'pump_speed',
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

        # 从params获取过滤参数（不允许硬编码默认值）
        filter_params = {
            'min_freq': params.get('min_freq'),
            'max_freq': params.get('max_freq')
        }

        # 验证必需参数
        missing_params = []
        if filter_params['min_freq'] is None:
            missing_params.append('min_freq')
        if filter_params['max_freq'] is None:
            missing_params.append('max_freq')

        if missing_params:
            self.logger.error(
                f"[Pipeline] pump_speed缺少过滤参数",
                extra={'extra_data': {
                    '任务ID': task_id,
                    '缺失参数': missing_params,
                    '错误': '必须在calculation_parameters表中配置这些参数'
                }}
            )
            raise ValueError(
                f"pump_speed缺少过滤参数: {', '.join(missing_params)}. "
                f"必须在calculation_parameters表中配置: metric_key='pump_speed', method_id='data_filter'"
            )

        filter_obj = DataFilter(params=filter_params, trace_id=task_id)
        filtered_data = filter_obj.filter_data(raw_data)

        stage2_duration = time.time() - stage2_start
        self.logger.info(
            f"[Pipeline-Stage2-完成] DataFilter",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                '过滤后行数': len(filtered_data),
                '耗时（毫秒）': round(stage2_duration * 1000, 2)
            }}
        )

        # 检查过滤后是否有数据
        if filtered_data.empty:
            self.logger.info(
                f"[Pipeline-跳过] 过滤后无数据",
                extra={'extra_data': {
                    '任务ID': task_id,
                    '设备ID': device_id,
                    '指标键': 'pump_speed'
                }}
            )
            return {
                'success': True,
                '设备ID': device_id,
                '指标键': 'pump_speed',
                'results_count': 0,
                'skipped': True,
                '原因': '过滤后无数据'
            }

        # Stage 3: MethodSelector
        self.logger.info(
            f"[Pipeline-Stage3-开始] MethodSelector",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id
            }}
        )
        stage3_start = time.time()

        selector = MethodSelector(params=params, trace_id=task_id)
        try:
            method_id = selector.select_method(filtered_data)
        except ValueError as e:
            self.logger.error(
                f"[Pipeline-Stage3-失败] MethodSelector: {str(e)}",
                extra={'extra_data': {
                    '任务ID': task_id,
                    '设备ID': device_id,
                    'error': str(e)
                }}
            )
            return {
                'success': False,
                '设备ID': device_id,
                '指标键': 'pump_speed',
                'results_count': 0,
                'error': str(e)
            }

        stage3_duration = time.time() - stage3_start
        self.logger.info(
            f"[Pipeline-Stage3-完成] MethodSelector",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                '选择的方法': method_id,
                '耗时（毫秒）': round(stage3_duration * 1000, 2)
            }}
        )

        # Stage 4: Calculator
        self.logger.info(
            f"[Pipeline-Stage4-开始] Calculator",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                '方法ID': method_id
            }}
        )
        stage4_start = time.time()

        calculator = Calculator(param_manager=shared_services.parameter_manager, trace_id=task_id)
        calc_results = calculator.calculate(filtered_data, method_id, params)

        stage4_duration = time.time() - stage4_start
        self.logger.info(
            f"[Pipeline-Stage4-完成] Calculator",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                '结果行数': len(calc_results),
                '耗时（毫秒）': round(stage4_duration * 1000, 2)
            }}
        )

        # Stage 5: Validator
        self.logger.info(
            f"[Pipeline-Stage5-开始] Validator",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id
            }}
        )
        stage5_start = time.time()

        # 获取验证参数（不允许硬编码默认值）
        validation_params = {
            'min_speed': params.get('min_speed'),
            'max_speed': params.get('max_speed')
        }

        # 验证必需参数
        missing_params = []
        if validation_params['min_speed'] is None:
            missing_params.append('min_speed')
        if validation_params['max_speed'] is None:
            missing_params.append('max_speed')

        if missing_params:
            self.logger.error(
                f"[Pipeline] pump_speed缺少验证参数",
                extra={'extra_data': {
                    '任务ID': task_id,
                    '缺失参数': missing_params,
                    '错误': '必须在calculation_parameters表中配置这些参数'
                }}
            )
            raise ValueError(
                f"pump_speed缺少验证参数: {', '.join(missing_params)}. "
                f"必须在calculation_parameters表中配置: metric_key='pump_speed', method_id='validator'"
            )

        validator = Validator(params=validation_params)
        validation_result = validator.validate(calc_results, filtered_data)

        stage5_duration = time.time() - stage5_start
        self.logger.info(
            f"[Pipeline-Stage5-完成] Validator",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                'valid_count': validation_result['valid_count'],
                'invalid_count': validation_result['invalid_count'],
                '质量代码': validation_result['quality_code'],
                '耗时（毫秒）': round(stage5_duration * 1000, 2)
            }}
        )

        # Stage 6: DataWriter
        self.logger.info(
            f"[Pipeline-Stage6-开始] DataWriter",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id
            }}
        )
        stage6_start = time.time()

        # 准备写入数据
        valid_results = validation_result['valid_results']
        valid_results = valid_results.dropna(subset=['pump_speed'])

        if len(valid_results) > 0:
            from app.services.calculation.shared.data_writer import WriteRecord

            records = []
            for idx, row in valid_results.iterrows():
                record = WriteRecord(
                    device_id=device_id,
                    metric_key='pump_speed',
                    timestamp=row['ts_bucket'],
                    value=float(row['pump_speed']),
                    quality_code=validation_result['quality_code'],
                    method_id=method_id,
                    calculated_at=datetime.now()
                )
                records.append(record)

            # 写入数据库
            written_count = shared_services.data_writer.write(records, station_id=station_id)

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
        else:
            written_count = 0
            self.logger.info(
                f"[Pipeline-Stage6-跳过] DataWriter（无有效数据）",
                extra={'extra_data': {
                    '任务ID': task_id,
                    '设备ID': device_id
                }}
            )

        # 返回结果
        return {
            'success': True,
            '设备ID': device_id,
            '指标键': 'pump_speed',
            'results_count': written_count,
            '方法ID': method_id,
            '质量代码': validation_result['quality_code']
        }

