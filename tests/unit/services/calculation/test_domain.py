"""
测试 calculation/domain.py - 领域模型

测试场景:
1. CalculationContext 数据类测试 (5个)
2. MethodDescriptor 数据类测试 (5个)

总计: 10个测试场景
"""

import pytest
from datetime import datetime, timezone
from app.services.calculation.domain import CalculationContext, MethodDescriptor


class TestCalculationContext:
    """CalculationContext 数据类测试"""

    def test_context_creation_with_required_fields(self):
        """场景1: 使用必需字段创建上下文"""
        start_ts = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_ts = datetime(2025, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        ctx = CalculationContext(
            station_id=1,
            device_id=10,
            start_ts=start_ts,
            end_ts=end_ts
        )
        
        # 验证必需字段
        assert ctx.station_id == 1
        assert ctx.device_id == 10
        assert ctx.start_ts == start_ts
        assert ctx.end_ts == end_ts
        
        # 验证默认值
        assert ctx.bucket_size_sec == 1
        assert ctx.run_id == ""
        assert ctx.batch_no is None
        assert ctx.strict_mode is False
        assert ctx.quality_filters == {}
        assert ctx.extra == {}

    def test_context_creation_with_all_fields(self):
        """场景2: 使用所有字段创建上下文"""
        start_ts = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_ts = datetime(2025, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        ctx = CalculationContext(
            station_id=1,
            device_id=10,
            start_ts=start_ts,
            end_ts=end_ts,
            bucket_size_sec=60,
            run_id="run_123",
            batch_no=5,
            strict_mode=True,
            quality_filters={"quality_status": ["good", "fair"]},
            extra={"custom_field": "value"}
        )
        
        # 验证所有字段
        assert ctx.station_id == 1
        assert ctx.device_id == 10
        assert ctx.start_ts == start_ts
        assert ctx.end_ts == end_ts
        assert ctx.bucket_size_sec == 60
        assert ctx.run_id == "run_123"
        assert ctx.batch_no == 5
        assert ctx.strict_mode is True
        assert ctx.quality_filters == {"quality_status": ["good", "fair"]}
        assert ctx.extra == {"custom_field": "value"}

    def test_context_is_frozen(self):
        """场景3: 验证上下文是不可变的（frozen）"""
        start_ts = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_ts = datetime(2025, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        ctx = CalculationContext(
            station_id=1,
            device_id=10,
            start_ts=start_ts,
            end_ts=end_ts
        )
        
        # 尝试修改字段应该抛出异常
        with pytest.raises(Exception):  # dataclass frozen会抛出FrozenInstanceError或AttributeError
            ctx.station_id = 2

    def test_context_quality_filters_default(self):
        """场景4: 验证quality_filters默认为空字典"""
        start_ts = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_ts = datetime(2025, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        ctx = CalculationContext(
            station_id=1,
            device_id=10,
            start_ts=start_ts,
            end_ts=end_ts
        )
        
        # 验证默认值是空字典
        assert ctx.quality_filters == {}
        assert isinstance(ctx.quality_filters, dict)

    def test_context_extra_field(self):
        """场景5: 验证extra字段可以存储任意扩展信息"""
        start_ts = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_ts = datetime(2025, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        extra_data = {
            "custom_param1": 123,
            "custom_param2": "value",
            "nested": {"key": "value"}
        }
        
        ctx = CalculationContext(
            station_id=1,
            device_id=10,
            start_ts=start_ts,
            end_ts=end_ts,
            extra=extra_data
        )
        
        # 验证extra字段
        assert ctx.extra == extra_data
        assert ctx.extra["custom_param1"] == 123
        assert ctx.extra["custom_param2"] == "value"
        assert ctx.extra["nested"]["key"] == "value"


class TestMethodDescriptor:
    """MethodDescriptor 数据类测试"""

    def test_descriptor_creation_with_required_fields(self):
        """场景6: 使用必需字段创建方法描述符"""
        desc = MethodDescriptor(
            method_id="method_001",
            method_code="A",
            metric_key="pump_flow_rate",
            priority=1
        )
        
        # 验证必需字段
        assert desc.method_id == "method_001"
        assert desc.method_code == "A"
        assert desc.metric_key == "pump_flow_rate"
        assert desc.priority == 1
        
        # 验证默认值
        assert desc.dependencies == []
        assert desc.conditions == {}
        assert desc.params == {}
        assert desc.validator_hint is None

    def test_descriptor_creation_with_all_fields(self):
        """场景7: 使用所有字段创建方法描述符"""
        desc = MethodDescriptor(
            method_id="method_001",
            method_code="A",
            metric_key="pump_flow_rate",
            priority=1,
            dependencies=["main_pipeline_flow_rate", "pump_active_power"],
            conditions={"running_count": {"min": 1}},
            params={"coefficient": 1.2, "offset": 0.5},
            validator_hint="physics_laws"
        )
        
        # 验证所有字段
        assert desc.method_id == "method_001"
        assert desc.method_code == "A"
        assert desc.metric_key == "pump_flow_rate"
        assert desc.priority == 1
        assert desc.dependencies == ["main_pipeline_flow_rate", "pump_active_power"]
        assert desc.conditions == {"running_count": {"min": 1}}
        assert desc.params == {"coefficient": 1.2, "offset": 0.5}
        assert desc.validator_hint == "physics_laws"

    def test_descriptor_is_frozen(self):
        """场景8: 验证方法描述符是不可变的（frozen）"""
        desc = MethodDescriptor(
            method_id="method_001",
            method_code="A",
            metric_key="pump_flow_rate",
            priority=1
        )
        
        # 尝试修改字段应该抛出异常
        with pytest.raises(Exception):  # dataclass frozen会抛出FrozenInstanceError或AttributeError
            desc.method_id = "method_002"

    def test_descriptor_dependencies_list(self):
        """场景9: 验证dependencies是列表类型"""
        desc = MethodDescriptor(
            method_id="method_001",
            method_code="A",
            metric_key="pump_flow_rate",
            priority=1,
            dependencies=["dep1", "dep2", "dep3"]
        )
        
        # 验证dependencies是列表
        assert isinstance(desc.dependencies, list)
        assert len(desc.dependencies) == 3
        assert "dep1" in desc.dependencies
        assert "dep2" in desc.dependencies
        assert "dep3" in desc.dependencies

    def test_descriptor_params_and_conditions_dicts(self):
        """场景10: 验证params和conditions是字典类型"""
        desc = MethodDescriptor(
            method_id="method_001",
            method_code="A",
            metric_key="pump_flow_rate",
            priority=1,
            conditions={"running_count": {"min": 1, "max": 10}},
            params={"param1": 1.0, "param2": "value"}
        )
        
        # 验证conditions是字典
        assert isinstance(desc.conditions, dict)
        assert desc.conditions["running_count"]["min"] == 1
        assert desc.conditions["running_count"]["max"] == 10
        
        # 验证params是字典
        assert isinstance(desc.params, dict)
        assert desc.params["param1"] == 1.0
        assert desc.params["param2"] == "value"

