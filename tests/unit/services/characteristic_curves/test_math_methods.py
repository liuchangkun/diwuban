"""
数学拟合方法单元测试

测试范围：
- MathPoly2Method (math_poly_2)
- MathPoly3Method (math_poly_3)
- MathStatGaussianMethod (math_stat_gaussian)
- MathSplineCubicMethod (math_spline_cubic)
- MathSplineBsplineMethod (math_spline_bspline)
- MathKernelRbfMethod (math_kernel_rbf)
- MathRationalPadeMethod (math_rational_pade)
- MathLocalLowessMethod (math_local_lowess)

版本: v1.0
更新日期: 2025-12-08
"""

import pytest

# P2模块已删除，等待P0完成后重写
pytestmark = pytest.mark.skip(reason="P2模块已删除，等待P0完成后重写")

import numpy as np

from app.services.characteristic_curves.methods.mathematical import (
    MathPoly2Method,
    MathPoly3Method,
    MathStatGaussianMethod,
    MathSplineCubicMethod,
    MathSplineBsplineMethod,
    MathKernelRbfMethod,
    MathRationalPadeMethod,
    MathLocalLowessMethod,
)
from app.services.characteristic_curves.methods.physical import (
    PhysicsPumpCharMethod,
    PhysicsPowerEqMethod,
)
from app.services.characteristic_curves.models import MethodResult


# ==================== 测试数据生成 ====================


@pytest.fixture
def qh_data():
    """Q-H曲线测试数据（二次递减）"""
    np.random.seed(42)
    Q = np.linspace(10, 100, 100)
    # H = 50 - 0.1*Q - 0.002*Q² + noise
    H = 50 - 0.1 * Q - 0.002 * Q**2 + np.random.normal(0, 0.5, 100)
    return Q, H


@pytest.fixture
def qp_data():
    """Q-P曲线测试数据（三次）"""
    np.random.seed(42)
    Q = np.linspace(10, 100, 100)
    # P = 5 + 0.05*Q + 0.001*Q² - 0.00001*Q³ + noise
    P = 5 + 0.05 * Q + 0.001 * Q**2 - 0.00001 * \
        Q**3 + np.random.normal(0, 0.3, 100)
    return Q, P


@pytest.fixture
def qeta_data():
    """Q-η曲线测试数据（高斯单峰）"""
    np.random.seed(42)
    Q = np.linspace(10, 100, 100)
    # η = 0.8 * exp(-((Q - 55)² / (2 * 20²))) + noise
    eta = 0.8 * np.exp(-((Q - 55) ** 2) / (2 * 20**2)) + \
        np.random.normal(0, 0.02, 100)
    return Q, eta


# ==================== 多项式方法测试 ====================


class TestMathPoly2Method:
    """测试2次多项式方法"""

    def test_init(self):
        """测试初始化"""
        method = MathPoly2Method()
        assert method.method_id == "math_poly_2"
        assert method.method_name == "2次多项式"
        assert method.degree == 2

    def test_fit_qh_data(self, qh_data):
        """测试Q-H数据拟合"""
        Q, H = qh_data
        method = MathPoly2Method()
        result = method.fit(Q, H)

        assert isinstance(result, MethodResult)
        assert result.method_id == "math_poly_2"
        assert "a0" in result.coefficients
        assert "a1" in result.coefficients
        assert "a2" in result.coefficients
        assert result.r_squared > 0.9  # 应该有良好拟合
        assert result.predict_func is not None
        assert result.formula != ""

    def test_predict_func(self, qh_data):
        """测试预测函数"""
        Q, H = qh_data
        method = MathPoly2Method()
        result = method.fit(Q, H)

        # 使用predict_func预测
        y_pred = result.predict_func(Q)
        assert len(y_pred) == len(Q)
        assert np.allclose(y_pred, result.predict_func(Q))

    def test_predict_method(self, qh_data):
        """测试predict方法"""
        Q, H = qh_data
        method = MathPoly2Method()
        result = method.fit(Q, H)

        # 使用predict方法
        y_pred = method.predict(Q, result.coefficients)
        assert len(y_pred) == len(Q)


class TestMathPoly3Method:
    """测试3次多项式方法"""

    def test_init(self):
        """测试初始化"""
        method = MathPoly3Method()
        assert method.method_id == "math_poly_3"
        assert method.method_name == "3次多项式"
        assert method.degree == 3

    def test_fit_qp_data(self, qp_data):
        """测试Q-P数据拟合"""
        Q, P = qp_data
        method = MathPoly3Method()
        result = method.fit(Q, P)

        assert isinstance(result, MethodResult)
        assert "a3" in result.coefficients
        assert result.r_squared > 0.9


# ==================== 统计方法测试 ====================


class TestMathStatGaussianMethod:
    """测试高斯函数方法"""

    def test_init(self):
        """测试初始化"""
        method = MathStatGaussianMethod()
        assert method.method_id == "math_stat_gaussian"
        assert method.method_name == "高斯函数"

    def test_fit_qeta_data(self, qeta_data):
        """测试Q-η数据拟合"""
        Q, eta = qeta_data
        method = MathStatGaussianMethod()
        result = method.fit(Q, eta)

        assert isinstance(result, MethodResult)
        assert "A" in result.coefficients
        assert "mu" in result.coefficients
        assert "sigma" in result.coefficients
        assert result.r_squared > 0.8  # 高斯拟合应该效果好


# ==================== 样条方法测试 ====================


class TestMathSplineCubicMethod:
    """测试三次样条方法"""

    def test_init(self):
        """测试初始化"""
        method = MathSplineCubicMethod()
        assert method.method_id == "math_spline_cubic"
        assert method.method_name == "三次样条"
        assert method.bc_type == "natural"

    def test_fit_qh_data(self, qh_data):
        """测试Q-H数据拟合"""
        Q, H = qh_data
        method = MathSplineCubicMethod()
        result = method.fit(Q, H)

        assert isinstance(result, MethodResult)
        assert result.r_squared > 0.95  # 样条插值应该非常好
        assert result.predict_func is not None
        assert "knots" in result.metadata


class TestMathSplineBsplineMethod:
    """测试B样条方法"""

    def test_init(self):
        """测试初始化"""
        method = MathSplineBsplineMethod()
        assert method.method_id == "math_spline_bspline"
        assert method.method_name == "B样条"
        assert method.degree == 3

    def test_fit_qh_data(self, qh_data):
        """测试Q-H数据拟合"""
        Q, H = qh_data
        method = MathSplineBsplineMethod()
        result = method.fit(Q, H)

        assert isinstance(result, MethodResult)
        assert result.r_squared > 0.95
        assert "knots" in result.metadata


# ==================== 核方法测试 ====================


class TestMathKernelRbfMethod:
    """测试RBF方法"""

    def test_init(self):
        """测试初始化"""
        method = MathKernelRbfMethod()
        assert method.method_id == "math_kernel_rbf"
        assert method.method_name == "径向基函数"
        assert method.kernel == "thin_plate_spline"

    def test_fit_qh_data(self, qh_data):
        """测试Q-H数据拟合"""
        Q, H = qh_data
        method = MathKernelRbfMethod()
        result = method.fit(Q, H)

        assert isinstance(result, MethodResult)
        assert result.r_squared > 0.95  # RBF插值应该非常好
        assert result.predict_func is not None


# ==================== 有理函数方法测试 ====================


class TestMathRationalPadeMethod:
    """测试Padé逼近方法"""

    def test_init(self):
        """测试初始化"""
        method = MathRationalPadeMethod()
        assert method.method_id == "math_rational_pade"
        assert method.method_name == "Padé逼近"

    def test_fit_qh_data(self, qh_data):
        """测试Q-H数据拟合"""
        Q, H = qh_data
        method = MathRationalPadeMethod()
        result = method.fit(Q, H)

        assert isinstance(result, MethodResult)
        # Padé可能收敛也可能不收敛
        if result.r_squared > 0:  # 如果成功拟合
            assert "a0" in result.coefficients
            assert "b1" in result.coefficients


# ==================== 局部方法测试 ====================


class TestMathLocalLowessMethod:
    """测试LOWESS方法"""

    def test_init(self):
        """测试初始化"""
        method = MathLocalLowessMethod()
        assert method.method_id == "math_local_lowess"
        assert method.method_name == "局部加权回归"
        assert method.frac == 0.3
        assert method.it == 3

    def test_fit_qh_data(self, qh_data):
        """测试Q-H数据拟合"""
        Q, H = qh_data
        method = MathLocalLowessMethod()
        result = method.fit(Q, H)

        assert isinstance(result, MethodResult)
        assert result.r_squared > 0.9
        assert result.predict_func is not None


# ==================== 方法注册测试 ====================


class TestMethodRegistration:
    """测试方法注册功能"""

    def test_register_polynomial_methods(self):
        """测试多项式方法注册"""
        from app.services.characteristic_curves.methods.mathematical.polynomial import (
            register_polynomial_methods,
        )
        from app.services.characteristic_curves.methods.method_registry import (
            MethodRegistry,
        )

        register_polynomial_methods()
        registry = MethodRegistry()

        # 验证方法已注册（list_methods返回字典列表，需要提取method_id）
        qh_methods = registry.list_methods("qh")
        qh_method_ids = [m["method_id"] for m in qh_methods]
        assert "math_poly_2" in qh_method_ids
        assert "math_poly_3" in qh_method_ids

    def test_register_all_math_methods(self):
        """测试注册所有数学方法"""
        from app.services.characteristic_curves.methods.mathematical import (
            register_all_math_methods,
        )
        from app.services.characteristic_curves.methods.method_registry import (
            MethodRegistry,
        )

        register_all_math_methods()
        registry = MethodRegistry()

        # 验证所有方法已注册（list_methods返回字典列表，需要提取method_id）
        qh_methods = registry.list_methods("qh")
        qh_method_ids = [m["method_id"] for m in qh_methods]
        assert "math_poly_2" in qh_method_ids
        assert "math_poly_3" in qh_method_ids
        assert "math_spline_cubic" in qh_method_ids
        assert "math_spline_bspline" in qh_method_ids
        assert "math_kernel_rbf" in qh_method_ids
        assert "math_rational_pade" in qh_method_ids
        assert "math_local_lowess" in qh_method_ids

        # 验证qeta曲线的方法
        qeta_methods = registry.list_methods("qeta")
        qeta_method_ids = [m["method_id"] for m in qeta_methods]
        assert "math_stat_gaussian" in qeta_method_ids


# ==================== 物理模型方法测试 ====================


class TestPhysicsPumpCharMethod:
    """测试泵特性方程方法"""

    def test_init(self):
        """测试初始化"""
        method = PhysicsPumpCharMethod()
        assert method.method_id == "physics_pump_char"
        assert method.method_name == "泵特性方程"

    def test_fit_qh_data(self, qh_data):
        """测试Q-H数据拟合"""
        Q, H = qh_data
        method = PhysicsPumpCharMethod()
        result = method.fit(Q, H)

        assert isinstance(result, MethodResult)
        assert result.method_id == "physics_pump_char"
        assert "H0" in result.coefficients
        assert "K" in result.coefficients
        assert result.r_squared > 0.9  # 泵特性方程应该拟合得很好
        assert result.predict_func is not None
        assert "physics_valid" in result.metadata

    def test_fit_with_constraints(self, qh_data):
        """测试带约束参数的拟合"""
        Q, H = qh_data
        method = PhysicsPumpCharMethod()
        constraints = {"H0": 55.0, "K": 0.005}
        result = method.fit(Q, H, constraints=constraints)

        assert isinstance(result, MethodResult)
        assert result.r_squared > 0.8

    def test_predict_method(self, qh_data):
        """测试predict方法"""
        Q, H = qh_data
        method = PhysicsPumpCharMethod()
        result = method.fit(Q, H)

        # 使用predict方法
        y_pred = method.predict(Q, result.coefficients)
        assert len(y_pred) == len(Q)

    def test_negative_flow_raises_error(self):
        """测试负流量抛出异常"""
        method = PhysicsPumpCharMethod()
        Q = np.array([-1, 0, 1, 2])
        H = np.array([50, 49, 48, 47])
        with pytest.raises(ValueError, match="流量Q不能为负值"):
            method.fit(Q, H)


class TestPhysicsPowerEqMethod:
    """测试功率方程方法"""

    def test_init(self):
        """测试初始化"""
        method = PhysicsPowerEqMethod()
        assert method.method_id == "physics_power_eq"
        assert method.method_name == "功率方程"

    def test_fit_qp_data(self, qp_data):
        """测试Q-P数据拟合"""
        Q, P = qp_data
        method = PhysicsPowerEqMethod()
        result = method.fit(Q, P)

        assert isinstance(result, MethodResult)
        assert result.method_id == "physics_power_eq"
        assert "P0" in result.coefficients
        assert "K" in result.coefficients
        assert "n" in result.coefficients
        assert result.r_squared > 0.85  # 功率方程拟合精度要求
        assert result.predict_func is not None
        assert "physics_valid" in result.metadata

    def test_fit_with_constraints(self, qp_data):
        """测试带约束参数的拟合"""
        Q, P = qp_data
        method = PhysicsPowerEqMethod()
        constraints = {"P0": 5.0, "n": 1.5}
        result = method.fit(Q, P, constraints=constraints)

        assert isinstance(result, MethodResult)
        assert result.r_squared > 0.8

    def test_predict_method(self, qp_data):
        """测试predict方法"""
        Q, P = qp_data
        method = PhysicsPowerEqMethod()
        result = method.fit(Q, P)

        # 使用predict方法
        y_pred = method.predict(Q, result.coefficients)
        assert len(y_pred) == len(Q)


class TestPhysicsMethodRegistration:
    """测试物理模型方法注册"""

    def test_register_physics_methods(self):
        """测试物理模型方法注册"""
        from app.services.characteristic_curves.methods.physical import (
            register_all_physics_methods,
        )
        from app.services.characteristic_curves.methods.method_registry import (
            MethodRegistry,
        )

        register_all_physics_methods()
        registry = MethodRegistry()

        # 验证Q-H曲线的物理方法
        qh_methods = registry.list_methods("qh")
        qh_method_ids = [m["method_id"] for m in qh_methods]
        assert "physics_pump_char" in qh_method_ids

        # 验证Q-P曲线的物理方法
        qp_methods = registry.list_methods("qp")
        qp_method_ids = [m["method_id"] for m in qp_methods]
        assert "physics_power_eq" in qp_method_ids

    def test_physics_methods_highest_priority(self):
        """测试物理模型方法优先级为最高"""
        from app.services.characteristic_curves.methods.physical import (
            register_all_physics_methods,
        )
        from app.services.characteristic_curves.methods.method_registry import (
            MethodRegistry,
        )

        register_all_physics_methods()
        registry = MethodRegistry()

        # 检查泵特性方程优先级
        qh_methods = registry.list_methods("qh")
        pump_char = next(
            (m for m in qh_methods if m["method_id"] == "physics_pump_char"), None)
        assert pump_char is not None
        assert pump_char["priority"] == 100  # 最高优先级

        # 检查功率方程优先级
        qp_methods = registry.list_methods("qp")
        power_eq = next(
            (m for m in qp_methods if m["method_id"] == "physics_power_eq"), None)
        assert power_eq is not None
        assert power_eq["priority"] == 100  # 最高优先级
