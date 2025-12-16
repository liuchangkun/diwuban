"""
main_pipeline_inlet_pressure Pipeline 集成测试
"""

import pytest
import pandas as pd
from datetime import datetime

from app.services.calculation.metrics.main_pipeline_inlet_pressure.pipeline import MainPipelineInletPressurePipeline


class TestPipelineIntegration:
    """Pipeline集成测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self, initialize_db_pool):
        """测试前初始化"""
        self.pipeline = MainPipelineInletPressurePipeline()
    
    def test_pipeline_execute_success(self):
        """测试Pipeline成功执行"""
        # 测试参数
        station_id = 1
        device_id = 7  # 总管设备
        start_time = datetime(2025, 10, 22, 16, 0, 0)
        end_time = datetime(2025, 10, 22, 17, 0, 0)
        
        # 执行Pipeline
        result = self.pipeline.execute(
            station_id=station_id,
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            task_id="test_task_001"
        )
        
        # 验证结果
        assert result is not None
        assert isinstance(result, dict)
        assert 'written_count' in result
        assert result['written_count'] >= 0
    
    def test_pipeline_with_empty_data(self):
        """测试Pipeline处理空数据"""
        # 使用不存在的时间范围
        station_id = 1
        device_id = 7
        start_time = datetime(2020, 1, 1, 0, 0, 0)
        end_time = datetime(2020, 1, 1, 1, 0, 0)
        
        # 执行Pipeline
        result = self.pipeline.execute(
            station_id=station_id,
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            task_id="test_task_002"
        )
        
        # 验证结果
        assert result is not None
        assert result['written_count'] == 0
    
    def test_pipeline_cross_device_dependency(self):
        """测试跨设备依赖（device_id=7依赖device_id=8的pool_liquid_level）"""
        station_id = 1
        device_id = 7  # 总管设备
        start_time = datetime(2025, 10, 22, 16, 0, 0)
        end_time = datetime(2025, 10, 22, 17, 0, 0)
        
        # 执行Pipeline
        result = self.pipeline.execute(
            station_id=station_id,
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            task_id="test_task_003"
        )
        
        # 验证结果
        assert result is not None
        assert result['written_count'] >= 0
    
    def test_pipeline_error_handling(self):
        """测试Pipeline错误处理"""
        # 使用无效的device_id
        station_id = 1
        device_id = 999  # 无效设备
        start_time = datetime(2025, 10, 22, 16, 0, 0)
        end_time = datetime(2025, 10, 22, 17, 0, 0)
        
        # 执行Pipeline（应该优雅处理错误）
        result = self.pipeline.execute(
            station_id=station_id,
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            task_id="test_task_004"
        )
        
        # 验证结果
        assert result is not None
        assert result['written_count'] == 0
    
    def test_pipeline_performance(self):
        """测试Pipeline性能"""
        import time
        
        station_id = 1
        device_id = 7
        start_time = datetime(2025, 10, 22, 16, 0, 0)
        end_time = datetime(2025, 10, 23, 16, 0, 0)  # 24小时
        
        # 记录开始时间
        start = time.time()
        
        # 执行Pipeline
        result = self.pipeline.execute(
            station_id=station_id,
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            task_id="test_task_005"
        )
        
        # 记录结束时间
        elapsed = time.time() - start
        
        # 验证性能
        assert elapsed < 30.0  # 应在30秒内完成
        assert result['written_count'] >= 0

