"""
pump_hydraulic_power Pipeline模块

职责：协调6个阶段的执行流程
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional
import time

from .data_loader import DataLoader
from .data_filter import DataFilter
from .method_selector import MethodSelector
from .calculator import Calculator
from .validator import Validator
from app.services.calculation.shared.shared_services import SharedServices


class PumpHydraulicPowerPipeline:
    """pump_hydraulic_power计算流水线"""

    def __init__(self):
        """初始化Pipeline"""
        self.metric_key = 'pump_hydraulic_power'
        self.shared_services = SharedServices()

    def execute(
        self,
        station_id: int,
        device_id: int,
        start_time: datetime,
        end_time: datetime,
        task_id: str = ""
    ) -> Dict[str, Any]:
        """
        执行完整的计算流程

        Args:
            station_id: 泵站ID
            device_id: 设备ID
            start_time: 开始时间
            end_time: 结束时间
            task_id: 任务ID

        Returns:
            Dict: 执行结果
        """
        trace_id = task_id or f"pump_hydraulic_power_{device_id}_{int(time.time())}"

        print(f"\n{'='*80}")
        print(f"[{trace_id}] pump_hydraulic_power 计算开始")
        print(f"{'='*80}")
        print(f"  - station_id: {station_id}")
        print(f"  - device_id: {device_id}")
        print(f"  - start_time: {start_time}")
        print(f"  - end_time: {end_time}")

        try:
            # 阶段1: 加载参数
            print(f"\n[{trace_id}] [阶段1] 加载参数...")
            params = self.shared_services.parameter_manager.get_parameters(
                station_id=station_id,
                device_id=device_id,
                metric_key=self.metric_key
            )
            print(f"  - ✅ 参数加载成功")

            # 阶段2: 数据加载
            print(f"\n[{trace_id}] [阶段2] 数据加载...")
            data_loader = DataLoader(trace_id=trace_id)
            raw_data = data_loader.load(station_id, device_id, start_time, end_time)

            if raw_data.empty:
                print(f"  - ⚠️ 无数据，跳过计算")
                return {
                    'success': True,
                    'skipped': True,
                    'results_count': 0,
                    'message': '无数据'
                }

            # 阶段3: 数据过滤
            print(f"\n[{trace_id}] [阶段3] 数据过滤...")
            data_filter = DataFilter(trace_id=trace_id)
            filtered_data = data_filter.filter(raw_data)

            if filtered_data.empty:
                print(f"  - ⚠️ 过滤后无数据，跳过计算")
                return {
                    'success': True,
                    'skipped': True,
                    'results_count': 0,
                    'message': '过滤后无数据'
                }

            # 阶段4: 方法选择
            print(f"\n[{trace_id}] [阶段4] 方法选择...")
            method_selector = MethodSelector(params=params, trace_id=trace_id)
            method_id = method_selector.select(filtered_data, device_id)

            if not method_id:
                print(f"  - ⚠️ 无可用方法，跳过计算")
                return {
                    'success': True,
                    'skipped': True,
                    'results_count': 0,
                    'message': '无可用方法'
                }

            # 阶段5: 计算
            print(f"\n[{trace_id}] [阶段5] 计算...")
            calculator = Calculator(params=params, method_id=method_id, trace_id=trace_id)
            result_data = calculator.calculate(filtered_data, device_id)

            if result_data.empty:
                print(f"  - ⚠️ 计算结果为空")
                return {
                    'success': True,
                    'skipped': True,
                    'results_count': 0,
                    'message': '计算结果为空'
                }

            # 阶段6: 验证
            print(f"\n[{trace_id}] [阶段6] 验证...")
            validator = Validator(params=params, trace_id=trace_id)
            validated_data = validator.validate(result_data)

            # 阶段7: 数据写入
            print(f"\n[{trace_id}] [阶段7] 数据写入...")

            # 转换为WriteRecord列表
            from app.services.calculation.shared.data_writer import WriteRecord
            from datetime import datetime as dt

            records = []
            calculated_at = dt.now()

            for idx, row in validated_data.iterrows():
                if row.get('quality') == 'valid':
                    records.append(WriteRecord(
                        device_id=device_id,
                        metric_key=self.metric_key,
                        timestamp=row['ts_bucket'],
                        value=float(row['pump_hydraulic_power']),
                        quality_code=0,
                        method_id=method_id,
                        calculated_at=calculated_at
                    ))

            written_count = self.shared_services.data_writer.write(records, station_id=station_id)

            print(f"\n{'='*80}")
            print(f"[{trace_id}] pump_hydraulic_power 计算完成")
            print(f"  - ✅ 成功写入 {written_count} 条记录")
            print(f"{'='*80}\n")

            return {
                'success': True,
                'skipped': False,
                'results_count': written_count,
                'message': f'成功写入 {written_count} 条记录'
            }

        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"\n{'='*80}")
            print(f"[{trace_id}] ❌ pump_hydraulic_power 计算失败")
            print(f"  - 错误: {error_msg}")
            print(f"{'='*80}\n")

            return {
                'success': False,
                'skipped': False,
                'results_count': 0,
                'error_message': error_msg
            }

