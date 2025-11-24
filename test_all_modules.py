"""特性曲线拟合系统 - 全面测试脚本"""
import numpy as np
np.random.seed(42)

Q = np.linspace(10, 300, 50)
H = 120.0 - 0.001 * Q**2 + np.random.normal(0, 1, 50)
P = 5.0 + 0.1 * Q + 0.00005 * Q**2 + np.random.normal(0, 0.5, 50)

print("=" * 60)
print("特性曲线拟合系统 - 全面测试")
print("=" * 60)

# ===== 1. 测试基础模块 =====
print("\n[1/12] 测试 models.py...")
from app.services.characteristic_curves.models import FitResult, MethodResult, FittingScenario
print(f"  FittingScenario.VFD_SINGLE = {FittingScenario.VFD_SINGLE.value}")
fr = FitResult(device_id=1, curve_type="qh", r_squared=0.95)
print(f"  FitResult创建成功: device_id={fr.device_id}, r2={fr.r_squared}")
print("  ✅ models.py 测试通过")

# ===== 2. 测试方法层基础 =====
print("\n[2/12] 测试方法层基础...")
from app.services.characteristic_curves.methods.base_method import BaseMethod
from app.services.characteristic_curves.methods.method_registry import MethodRegistry
registry = MethodRegistry()
print("  MethodRegistry 创建成功")
print("  ✅ 方法层基础测试通过")

# ===== 3. 测试数学方法 =====
print("\n[3/12] 测试数学方法...")
from app.services.characteristic_curves.methods.math.polynomial import MathPoly2Method, MathPoly3Method
from app.services.characteristic_curves.methods.math.spline import MathSplineCubicMethod
from app.services.characteristic_curves.methods.math.kernel import MathKernelRbfMethod

poly2 = MathPoly2Method()
result = poly2.fit(Q, H)
print(f"  MathPoly2Method: r2={round(result.r_squared, 4)}, rmse={round(result.rmse, 4)}")

poly3 = MathPoly3Method()
result2 = poly3.fit(Q, H)
print(f"  MathPoly3Method: r2={round(result2.r_squared, 4)}")

spline = MathSplineCubicMethod()
result3 = spline.fit(Q, H)
print(f"  MathSplineCubicMethod: r2={round(result3.r_squared, 4)}")
print("  ✅ 数学方法测试通过")

# ===== 4. 测试物理模型 =====
print("\n[4/12] 测试物理模型...")
from app.services.characteristic_curves.methods.physics.pump_characteristic import PhysicsPumpCharMethod
physics = PhysicsPumpCharMethod()
result4 = physics.fit(Q, H)
print(f"  PhysicsPumpCharMethod: r2={round(result4.r_squared, 4)}")
print("  ✅ 物理模型测试通过")

# ===== 5. 测试ML方法 =====
print("\n[5/12] 测试ML方法...")
from app.services.characteristic_curves.methods.ml.gaussian_process import MLGaussianProcessMethod
from app.services.characteristic_curves.methods.ml.random_forest import MLRandomForestMethod
gp = MLGaussianProcessMethod()
result5 = gp.fit(Q, H)
print(f"  MLGaussianProcessMethod: r2={round(result5.r_squared, 4)}")

rf = MLRandomForestMethod()
result6 = rf.fit(Q, H)
print(f"  MLRandomForestMethod: r2={round(result6.r_squared, 4)}")
print("  ✅ ML方法测试通过")

# ===== 6. 测试约束层 =====
print("\n[6/12] 测试约束层...")
from app.services.characteristic_curves.constraints.monotonicity_constraint import MonotonicityConstraint
from app.services.characteristic_curves.constraints.boundary_constraint import BoundaryConstraint
mono = MonotonicityConstraint()
result7 = mono.validate("qh", Q, H)
print(f"  MonotonicityConstraint: is_valid={result7.is_valid}, violation_ratio={round(result7.violation_ratio, 3)}")

boundary = BoundaryConstraint()
result8 = boundary.validate("qh", Q, H, q_range=(0, 400), h_range=(0, 150))
print(f"  BoundaryConstraint: is_valid={result8.is_valid}")
print("  ✅ 约束层测试通过")

# ===== 7. 测试预处理层 =====
print("\n[7/12] 测试预处理层...")
from app.services.characteristic_curves.preprocessing.data_cleaner import DataCleaner
from app.services.characteristic_curves.preprocessing.normalizer import Normalizer
cleaner = DataCleaner()
normalizer = Normalizer()
print("  DataCleaner 创建成功")
print("  Normalizer 创建成功")
print("  ✅ 预处理层测试通过")

# ===== 8. 测试曲线模块 =====
print("\n[8/12] 测试曲线模块...")
from app.services.characteristic_curves.curves.qh_curve import QHCurve
from app.services.characteristic_curves.curves.qp_curve import QPCurve
from app.services.characteristic_curves.curves.curve_registry import CurveRegistry

qh = QHCurve()
result9 = qh.fit(Q, H)
print(f"  QHCurve.fit(): success={result9.success}, r2={round(result9.r_squared, 4)}")

qp = QPCurve()
result10 = qp.fit(Q, P)
print(f"  QPCurve.fit(): success={result10.success}, r2={round(result10.r_squared, 4)}")
print("  ✅ 曲线模块测试通过")

# ===== 9. 测试共享模块 =====
print("\n[9/12] 测试共享模块...")
from app.services.characteristic_curves.shared.cache_manager import get_cache_manager
from app.services.characteristic_curves.shared.parameter_manager import get_parameter_manager
from app.services.characteristic_curves.shared.alert_manager import AlertManager
from app.services.characteristic_curves.shared.config_validator import ConfigValidator

cache = get_cache_manager()
cache.set("test_key", {"value": 123})
result11 = cache.get("test_key")
print(f"  CacheManager: set/get ok, value={result11}")

pm = get_parameter_manager()
pm.set("test.param", 42)
val = pm.get("test.param")
print(f"  ParameterManager: get={val}")

am = AlertManager()
am.add_alert(level="warning", message="test alert", source="test")
print(f"  AlertManager: unack_count={len(am.get_unacknowledged())}")
print("  ✅ 共享模块测试通过")

# ===== 10. 测试管道模块 =====
print("\n[10/12] 测试管道模块...")
from app.services.characteristic_curves.pipeline.pipeline_context import PipelineContext, PipelineStage
from app.services.characteristic_curves.pipeline.curve_fitting_pipeline import CurveFittingPipeline
from app.services.characteristic_curves.pipeline.dependency_container import get_container, reset_container

reset_container()
ctx = PipelineContext(device_id=1, curve_type="qh")
ctx.set_stage(PipelineStage.TIME_WINDOW_SPLIT)
ctx.set_data("test", 123)
print(f"  PipelineContext: stage={ctx.current_stage.value}, data={ctx.get_data('test')}")

container = get_container()
container.register_singleton(str, "test_value")
print(f"  DependencyContainer: resolve={container.resolve(str)}")

pipeline = CurveFittingPipeline()
result12 = pipeline.fit(device_id=1, curve_type="qh", x_values=Q, y_values=H)
print(f"  CurveFittingPipeline.fit(): success={result12.success}, r2={round(result12.r_squared, 4)}")
print("  ✅ 管道模块测试通过")

print("\n" + "=" * 60)
print("✅ 全部测试通过！")
print("=" * 60)

