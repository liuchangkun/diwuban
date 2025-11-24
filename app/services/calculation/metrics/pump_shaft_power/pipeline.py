"""
pump_shaft_power 流水线编排器

职责：
- 编排6个阶段的执行流程
- 管理阶段间的数据传递
- 记录完整的日志追踪（trace_id/span_id）
"""

from __future__ import annotations

from typing import Dict, Any
from datetime import datetime
import logging


class PumpShaftPowerPipeline:
    """
    pump_shaft_power 流水线编排器
    
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
            metric_key='pump_shaft_power'
        )

        # Load device_rated_params (eta_motor, eta_vfd)
        from app.adapters.db.pool import get_connection
        device_params = {}
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT device_id, param_key, value_numeric
                    FROM device_rated_params
                    WHERE station_id = %s
                      AND device_id IN (1,2,3,4,5,6)
                      AND param_key IN ('eta_motor', 'eta_vfd')
                      AND (effective_to IS NULL OR effective_to > NOW())
                    ORDER BY device_id, param_key
                """, (station_id,))

                for row in cur.fetchall():
                    dev_id, param_key, value = row
                    if dev_id not in device_params:
                        device_params[dev_id] = {}
                    device_params[dev_id][param_key] = float(value)

        # Add device_params to params
        params['device_params'] = device_params
        
        # Stage 1: DataLoader
        self.logger.info(
            f"[Pipeline-Stage1-开始] DataLoader",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                '指标键': 'pump_shaft_power',
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
                    '指标键': 'pump_shaft_power',
                    '原因': '设备类型不匹配或无原始数据'
                }}
            )
            return {
                'success': True,
                '设备ID': device_id,
                '指标键': 'pump_shaft_power',
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
        max_power = params.get('max_power')
        
        # 验证必需参数存在性
        if max_power is None:
            self.logger.error(
                f"[Pipeline] DataFilter缺少必需参数",
                extra={'extra_data': {
                    '任务ID': task_id,
                    '设备ID': device_id,
                    'missing_params': ['max_power']
                }}
            )
            raise ValueError(
                "DataFilter缺少必需参数: max_power。"
                "必须在calculation_parameters表中配置该参数。"
            )

        filter = DataFilter(max_power=max_power, trace_id=task_id)
        filtered_data = filter.filter_data(raw_data)
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

        # 检查过滤后数据
        if filtered_data.empty:
            self.logger.info(
                f"[Pipeline-跳过] 过滤后无数据",
                extra={'extra_data': {
                    '任务ID': task_id,
                    '设备ID': device_id,
                    '指标键': 'pump_shaft_power'
                }}
            )
            return {
                'success': True,
                '设备ID': device_id,
                '指标键': 'pump_shaft_power',
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
        method_id = selector.select_method(filtered_data)
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
        calculator = Calculator(params=params, trace_id=task_id)
        calculated_data = calculator.calculate(filtered_data, method_id)
        stage4_duration = time.time() - stage4_start
        self.logger.info(
            f"[Pipeline-Stage4-完成] Calculator",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                '计算行数': len(calculated_data),
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
        validator = Validator(params=params, trace_id=task_id)
        validated_data = validator.validate(calculated_data, method_id)
        stage5_duration = time.time() - stage5_start
        self.logger.info(
            f"[Pipeline-Stage5-完成] Validator",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                'valid_rows': len(validated_data),
                '耗时（毫秒）': round(stage5_duration * 1000, 2)
            }}
        )

        # 检查验证后数据
        if validated_data.empty:
            self.logger.warning(
                f"[Pipeline-警告] 验证后无有效数据",
                extra={'extra_data': {
                    '任务ID': task_id,
                    '设备ID': device_id,
                    '指标键': 'pump_shaft_power'
                }}
            )
            return {
                'success': True,
                '设备ID': device_id,
                '指标键': 'pump_shaft_power',
                'results_count': 0,
                'skipped': True,
                '原因': '验证后无有效数据'
            }

        # Stage 6: DataWriter
        self.logger.info(
            f"[Pipeline-Stage6-开始] DataWriter",
            extra={'extra_data': {
                '任务ID': task_id,
                '设备ID': device_id,
                'rows_to_write': len(validated_data)
            }}
        )
        stage6_start = time.time()

        # 准备写入记录
        from app.services.calculation.shared.data_writer import WriteRecord

        records = [
            WriteRecord(
                device_id=int(row['device_id']),
                metric_key='pump_shaft_power',
                timestamp=row['ts_bucket'],
                value=float(row['pump_shaft_power']),
                quality_code=int(row['quality_code']),
                method_id=row.get('method_id', 'method_a')
            )
            for _, row in validated_data.iterrows()
        ]

        # 写入数据
        written_count = shared_services.data_writer.write(
            records=records,
            station_id=station_id
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

        # 返回结果
        total_duration = time.time() - stage1_start
        return {
            'success': True,
            '设备ID': device_id,
            '指标键': 'pump_shaft_power',
            '方法ID': method_id,
            'results_count': len(validated_data),
            'written_count': written_count,
            '总耗时（毫秒）': round(total_duration * 1000, 2)
        }

