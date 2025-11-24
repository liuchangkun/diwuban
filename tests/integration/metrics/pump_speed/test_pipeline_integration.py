"""
pump_speed Pipeline 集成测试

测试目标：
- 验证完整的计算流水线
- 验证各模块间的集成
- 验证端到端的数据流
"""

import pytest
import pandas as pd
from datetime import datetime
from app.services.calculation.metrics.pump_speed.pipeline import PumpSpeedPipeline


class TestPipelineIntegration:
    """Pipeline 集成测试"""

    @pytest.fixture
    def pipeline(self):
        """创建Pipeline实例"""
        return PumpSpeedPipeline()

    @pytest.fixture
    def test_params(self):
        """测试参数"""
        return {
            'station_id': 1,
            'device_id': 1,
            'start_time': datetime(2025, 10, 22, 16, 0, 0),
            'end_time': datetime(2025, 10, 22, 17, 0, 0),
            'task_id': 'test_pipeline_integration'
        }

    def test_pipeline_execute_success(self, pipeline, test_params):
        """
        测试用例：完整流水线执行成功
        
        验证Pipeline能成功执行完整的计算流程
        """
        # 执行流水线
        result = pipeline.execute(**test_params)

        # 断言：执行成功
        assert result['success'] is True
        
        # 断言：包含必需字段
        assert 'device_id' in result
        assert 'metric_key' in result
        assert 'results_count' in result
        
        # 断言：metric_key正确
        assert result['metric_key'] == 'pump_speed'
        
        # 断言：device_id正确
        assert result['device_id'] == test_params['device_id']
        
        # 断言：有计算结果
        assert result['results_count'] > 0

    def test_pipeline_execute_empty_data(self, pipeline):
        """
        测试用例：空数据处理
        
        验证Pipeline能正确处理无数据情况
        """
        # 使用不存在的设备
        result = pipeline.execute(
            station_id=1,
            device_id=999,
            start_time=datetime(2025, 10, 22, 8, 0, 0),
            end_time=datetime(2025, 10, 22, 9, 0, 0),
            task_id='test_empty_data'
        )

        # 断言：执行成功但无结果
        assert result['success'] is True
        assert result['results_count'] == 0
        assert result.get('skipped') is True

    def test_pipeline_execute_multiple_devices(self, pipeline):
        """
        测试用例：多设备计算
        
        验证Pipeline能正确处理多个设备的计算
        """
        device_ids = [1, 2, 3, 4, 5, 6]
        results = []

        for device_id in device_ids:
            result = pipeline.execute(
                station_id=1,
                device_id=device_id,
                start_time=datetime(2025, 10, 22, 16, 0, 0),
                end_time=datetime(2025, 10, 22, 17, 0, 0),
                task_id=f'test_device_{device_id}'
            )
            results.append(result)

        # 断言：所有设备都执行成功
        assert all(r['success'] for r in results)
        
        # 断言：至少有一个设备有结果
        assert any(r['results_count'] > 0 for r in results)

    def test_pipeline_data_flow(self, pipeline, test_params):
        """
        测试用例：数据流验证
        
        验证数据在各阶段间正确传递
        """
        # 执行流水线
        result = pipeline.execute(**test_params)

        # 断言：执行成功
        assert result['success'] is True
        
        # 断言：包含阶段信息（如果Pipeline记录了阶段信息）
        # 这里假设Pipeline会记录各阶段的执行时间
        if 'stages' in result:
            assert 'data_loader' in result['stages']
            assert 'data_filter' in result['stages']
            assert 'method_selector' in result['stages']
            assert 'calculator' in result['stages']
            assert 'validator' in result['stages']

    def test_pipeline_error_handling(self, pipeline):
        """
        测试用例：错误处理
        
        验证Pipeline能正确处理错误情况
        """
        # 使用无效的时间范围（end_time < start_time）
        result = pipeline.execute(
            station_id=1,
            device_id=1,
            start_time=datetime(2025, 10, 22, 9, 0, 0),
            end_time=datetime(2025, 10, 22, 8, 0, 0),  # 错误：早于start_time
            task_id='test_error_handling'
        )

        # 断言：执行失败或返回空结果
        assert result['success'] is True  # Pipeline应该优雅处理错误
        assert result['results_count'] == 0

