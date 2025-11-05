import unittest
import numpy as np

from app.services.calculation.domain import CalculationContext, MethodDescriptor
from app.services.calculation.calculators import get_calculator_unified
from app.services.calculation.validator import PhysicsValidator


class TestUnifiedSignatures(unittest.TestCase):
    def test_calculator_wrapper_and_validator_ctx(self):
        # 构造上下文与方法描述
        ctx = CalculationContext(
            station_id=1,
            device_id=1,
            start_ts=None,
            end_ts=None,
        )
        method = MethodDescriptor(
            method_id="pump_flow_rate_method_a",
            method_code="A",
            metric_key="pump_flow_rate",
            priority=1,
            dependencies=[
                "main_pipeline_flow_rate",
                "pump_active_power",
                "pump_frequency",
            ],
        )

        # 构造最小数据
        n = 5
        data = {
            "main_pipeline_flow_rate": np.ones(n) * 100.0,
            "pump_active_power": np.ones(n) * 10.0,
            "pump_frequency": np.ones(n) * 50.0,
        }

        # 计算
        calc = get_calculator_unified(method.method_id)
        values, meta = calc(ctx, method, data)
        self.assertEqual(values.shape[0], n)
        self.assertIn("method_id", meta)

        # 验证
        validator = PhysicsValidator()
        is_valid, mask, errors, warnings = validator.validate_ctx(
            metric_key="pump_flow_rate", values=values, ctx=ctx
        )
        # 在无DB配置的环境下，默认配置可能导致部分数据未通过校验，这里仅校验接口可用与掩码长度
        self.assertEqual(mask.shape[0], n)
        self.assertEqual(mask.shape[0], n)
        self.assertIsInstance(errors, list)
        self.assertIsInstance(warnings, list)


if __name__ == "__main__":
    unittest.main()

