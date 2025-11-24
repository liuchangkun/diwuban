"""
Pipeline - 流水线编排器

职责：
- 编排整个计算流程
- 协调各个组件（DataLoader, DataFilter, MethodSelector, Calculator, Validator）
- 调用DataWriter写入结果
- 处理异常和日志
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime
import logging
import uuid

from .data_loader import DataLoader
from .data_filter import DataFilter
from .method_selector import MethodSelector
from .calculator import Calculator
from .validator import Validator


class MainPipelineInletPressurePipeline:
    """
    main_pipeline_inlet_pressure 计算流水线
    
    职责：
    - 编排完整的计算流程
    - 集成共享模块（ParameterManager, DataWriter）
    """
    
    def __init__(self):
        """初始化Pipeline"""
        self.logger = logging.getLogger(__name__)
        self.metric_key = 'main_pipeline_inlet_pressure'
        self.metric_id = 61
    
    def execute(
        self,
        station_id: int,
        device_id: int,
        start_time: datetime,
        end_time: datetime,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行计算流水线
        
        Args:
            station_id: 泵站ID
            device_id: 设备ID（应为7，总管设备）
            start_time: 开始时间
            end_time: 结束时间
            task_id: 任务ID
        
        Returns:
            执行结果字典
        """
        trace_id = task_id or str(uuid.uuid4())
        
        self.logger.info(
            f"[Pipeline] 开始执行: metric={self.metric_key}, device={device_id}",
            extra={'extra_data': {
                '追踪ID': trace_id,
                '泵站ID': station_id,
                '设备ID': device_id,
                'start_time': str(start_time),
                'end_time': str(end_time)
            }}
        )
        
        try:
            # 1. 加载参数
            from app.services.calculation.shared.shared_services import SharedServices
            shared_services = SharedServices()
            params = shared_services.parameter_manager.get_parameters(
                metric_key=self.metric_key,
                station_id=station_id,
                device_id=device_id
            )
            
            # 2. 加载数据
            data_loader = DataLoader(trace_id=trace_id)
            data = data_loader.load_data(
                station_id=station_id,
                device_id=device_id,
                start_time=start_time,
                end_time=end_time
            )
            
            if data.empty:
                self.logger.warning(
                    "[Pipeline] 无数据，跳过计算",
                    extra={'extra_data': {'追踪ID': trace_id}}
                )
                return {'written_count': 0}
            
            # 3. 过滤数据
            data_filter = DataFilter(params=params, trace_id=trace_id)
            filtered_data = data_filter.filter_data(data)
            
            if filtered_data.empty:
                self.logger.warning(
                    "[Pipeline] 过滤后无数据，跳过计算",
                    extra={'extra_data': {'追踪ID': trace_id}}
                )
                return {'written_count': 0}
            
            # 4. 选择方法
            method_selector = MethodSelector(params=params, trace_id=trace_id)
            method_result = method_selector.select_method(filtered_data)
            
            if method_result is None:
                self.logger.warning(
                    "[Pipeline] 无可用方法，跳过计算",
                    extra={'extra_data': {'追踪ID': trace_id}}
                )
                return {'written_count': 0}
            
            method_id, priority = method_result
            
            # 5. 执行计算
            calculator = Calculator(params=params, trace_id=trace_id)
            calculated_data = calculator.calculate(filtered_data, method_id)
            
            # 6. 验证结果
            validator = Validator(params=params, trace_id=trace_id)
            validated_data = validator.validate(calculated_data)

            # 7. 写入数据库
            from app.services.calculation.shared.data_writer import WriteRecord
            from datetime import datetime

            # 准备写入记录
            records = []
            for idx, row in validated_data.iterrows():
                if row['quality_code'] == 0:  # 只写入有效数据
                    record = WriteRecord(
                        device_id=device_id,
                        metric_key=self.metric_key,
                        timestamp=row['ts_bucket'],
                        value=float(row['main_pipeline_inlet_pressure']),
                        quality_code=row['quality_code'],
                        method_id=row['method'],
                        calculated_at=datetime.now()
                    )
                    records.append(record)

            # 写入数据库
            written_count = shared_services.data_writer.write(records, station_id=station_id)

            self.logger.info(
                f"[Pipeline] 执行完成: 写入{written_count}条记录",
                extra={'extra_data': {'追踪ID': trace_id}}
            )
            
            return {'written_count': written_count}
            
        except Exception as e:
            self.logger.error(
                f"[Pipeline] 执行失败: {str(e)}",
                extra={'extra_data': {'追踪ID': trace_id}},
                exc_info=True
            )
            return {'written_count': 0, 'error': str(e)}

