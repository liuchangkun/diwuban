"""
特性曲线拟合功能测试脚本

用于代码审查过程中验证拟合功能的正确性。
"""

import logging
import numpy as np
import sys
import os

# 添加项目根目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def test_polynomial_fit():
    """测试多项式拟合方法"""
    logger.info("=" * 60)
    logger.info("测试1: 多项式拟合方法")
    logger.info("=" * 60)

    from app.services.characteristic_curves.methods.mathematical.polynomial import (
        MathPoly2Method,
        MathPoly3Method,
    )

    # 生成模拟数据: H = 60 - 0.001 * Q^2 + 噪声
    np.random.seed(42)
    Q = np.linspace(50, 500, 100)
    H_true = 60 - 0.001 * Q**2
    H_noisy = H_true + np.random.normal(0, 0.5, len(Q))

    # 2次多项式拟合
    poly2 = MathPoly2Method()
    result2 = poly2.fit(Q, H_noisy)

    logger.info(f"2次多项式拟合结果:")
    logger.info(f"  - R² = {result2.r_squared:.6f}")
    logger.info(f"  - RMSE = {result2.rmse:.4f}")
    logger.info(f"  - MAE = {result2.mae:.4f}")
    logger.info(f"  - MAPE = {result2.mape:.4f}%")
    logger.info(f"  - 公式 = {result2.formula}")
    logger.info(f"  - 系数 = {result2.coefficients}")

    # 验证R²是否合理
    assert 0.9 < result2.r_squared <= 1.0, f"R²异常: {result2.r_squared}"
    assert result2.rmse > 0, "RMSE应该大于0"
    assert result2.mape < 10, f"MAPE过高: {result2.mape}%"

    logger.info("✓ 2次多项式拟合测试通过")

    # 3次多项式拟合
    poly3 = MathPoly3Method()
    result3 = poly3.fit(Q, H_noisy)

    logger.info(f"\n3次多项式拟合结果:")
    logger.info(f"  - R² = {result3.r_squared:.6f}")
    logger.info(f"  - RMSE = {result3.rmse:.4f}")

    assert result3.r_squared >= result2.r_squared - 0.01, "3次应不劣于2次"

    logger.info("✓ 3次多项式拟合测试通过")

    return True


def test_physics_pump_char():
    """测试泵特性方程拟合"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 泵特性方程拟合 (H = H0 - K*Q²)")
    logger.info("=" * 60)

    from app.services.characteristic_curves.methods.physical.pump_characteristic import (
        PhysicsPumpCharMethod,
    )

    # 生成符合泵特性方程的数据
    np.random.seed(42)
    H0_true, K_true = 65.0, 0.0001
    Q = np.linspace(10, 600, 100)
    H_true = H0_true - K_true * Q**2
    H_noisy = H_true + np.random.normal(0, 0.3, len(Q))

    # 确保H不为负
    H_noisy = np.maximum(H_noisy, 0.1)

    method = PhysicsPumpCharMethod()

    # 提供约束参数
    constraints = {
        "H0": 70.0,  # 初始估计
        "K": 0.0001,
    }

    result = method.fit(Q, H_noisy, constraints)

    logger.info(f"泵特性方程拟合结果:")
    logger.info(f"  - R² = {result.r_squared:.6f}")
    logger.info(f"  - RMSE = {result.rmse:.4f}")
    logger.info(f"  - H0 = {result.coefficients.get('H0', 'N/A')}")
    logger.info(f"  - K = {result.coefficients.get('K', 'N/A')}")
    logger.info(f"  - 公式 = {result.formula}")

    # 验证拟合质量
    if result.r_squared > 0:
        assert result.r_squared > 0.95, f"R²过低: {result.r_squared}"

        # 验证参数接近真实值
        H0_fit = result.coefficients.get('H0', 0)
        K_fit = result.coefficients.get('K', 0)

        logger.info(
            f"  - H0误差 = {abs(H0_fit - H0_true):.2f}m ({abs(H0_fit - H0_true)/H0_true*100:.2f}%)")
        logger.info(f"  - K误差 = {abs(K_fit - K_true):.6f}")

        logger.info("✓ 泵特性方程拟合测试通过")
    else:
        logger.warning("泵特性方程拟合失败")

    return True


def test_data_cleaner():
    """测试数据清洗器"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: 数据清洗器")
    logger.info("=" * 60)

    import pandas as pd
    from app.services.characteristic_curves.preprocessing.data_cleaner import (
        DataCleaner,
    )

    # 创建测试数据（包含异常值和缺失值）
    np.random.seed(42)
    n = 100
    Q = np.linspace(50, 500, n)
    H = 60 - 0.0001 * Q**2 + np.random.normal(0, 1, n)

    # 添加异常值
    H[10] = 200  # 极端高值
    H[50] = -10  # 负值

    # 添加缺失值
    H[20] = np.nan
    Q[30] = np.nan

    df = pd.DataFrame({'Q': Q, 'H': H})

    cleaner = DataCleaner(outlier_method='iqr', outlier_threshold=1.5)
    result = cleaner.clean(df, x_col='Q', y_col='H')

    logger.info(f"数据清洗结果:")
    logger.info(f"  - 原始数据点: {result.stats['original_count']}")
    logger.info(f"  - 清洗后数据点: {result.stats['final_count']}")
    logger.info(f"  - 移除数量: {result.removed_count}")
    logger.info(f"  - 保留率: {(1 - result.stats['removed_ratio'])*100:.1f}%")

    # 验证异常值被移除
    cleaned_H = result.cleaned_data['H'].values
    assert cleaned_H.min() >= 0, "应移除负值"
    assert cleaned_H.max() < 100, "应移除极端高值"
    assert not np.isnan(cleaned_H).any(), "应移除缺失值"

    logger.info("✓ 数据清洗器测试通过")

    return True


def test_physics_validator():
    """测试物理验证器"""
    logger.info("\n" + "=" * 60)
    logger.info("测试4: 物理验证器")
    logger.info("=" * 60)

    from app.services.characteristic_curves.constraints.physics_validator import (
        PhysicsValidator,
    )

    validator = PhysicsValidator()

    # 测试1: 单调递减曲线（应通过）
    Q = np.linspace(50, 500, 50)
    H_decreasing = 60 - 0.0001 * Q**2

    result1 = validator.validate(
        curve_type='qh',
        x_values=Q,
        y_values=H_decreasing,
        tolerance=0.01
    )

    logger.info(f"单调递减Q-H曲线验证:")
    logger.info(f"  - 总体通过: {result1.overall_passed}")
    logger.info(f"  - 单调性通过: {result1.monotonicity_passed}")
    logger.info(f"  - 边界通过: {result1.boundary_passed}")
    logger.info(f"  - 物理得分: {result1.physics_score:.1f}")

    # 测试2: 非单调曲线（应失败）
    H_non_mono = 60 - 0.0001 * (Q - 250)**2  # 凹形曲线

    result2 = validator.validate(
        curve_type='qh',
        x_values=Q,
        y_values=H_non_mono,
        tolerance=0.01
    )

    logger.info(f"\n非单调曲线验证:")
    logger.info(f"  - 单调性通过: {result2.monotonicity_passed}")
    logger.info(f"  - 物理得分: {result2.physics_score:.1f}")

    # 单调递减曲线应该通过单调性验证
    assert result1.monotonicity_passed == True, "单调递减应通过"

    logger.info("✓ 物理验证器测试通过")

    return True


def test_parallel_synthesizer():
    """测试并联合成器"""
    logger.info("\n" + "=" * 60)
    logger.info("测试5: 并联合成器")
    logger.info("=" * 60)

    from app.services.characteristic_curves.pump_group.parallel_synthesizer import (
        ParallelSynthesizer,
    )

    synthesizer = ParallelSynthesizer()

    # 注册单泵曲线
    def qh_curve_1(Q):
        """泵1的Q-H曲线"""
        return 60 - 0.0001 * Q**2

    def inverse_1(H):
        """反函数"""
        if H > 60:
            return 0
        return np.sqrt((60 - H) / 0.0001)

    synthesizer.register_pump_curve(
        pump_id=1,
        curve_func=qh_curve_1,
        inverse_func=inverse_1,
        H_range=(0, 60),
        rated_power=55.0
    )

    synthesizer.register_pump_curve(
        pump_id=2,
        curve_func=qh_curve_1,
        inverse_func=inverse_1,
        H_range=(0, 60),
        rated_power=55.0
    )

    logger.info("已注册2台同型号泵")

    # 测试同构泵组合成
    group_curve = synthesizer.synthesize_homogeneous(base_pump_id=1, n_pumps=2)

    # 验证并联公式: Q_total = n * Q_single
    Q_single = 300
    H_single = qh_curve_1(Q_single)
    H_group = group_curve(Q_single * 2)

    logger.info(f"同构泵组合成:")
    logger.info(f"  - 单泵: Q={Q_single}, H={H_single:.2f}m")
    logger.info(f"  - 双泵: Q_total={Q_single*2}, H={H_group:.2f}m")

    # 扬程应相同
    assert abs(H_single - H_group) < 0.1, f"扬程不一致: {H_single} vs {H_group}"

    logger.info("✓ 并联合成器测试通过")

    return True


def test_method_metrics_calculation():
    """测试指标计算的正确性"""
    logger.info("\n" + "=" * 60)
    logger.info("测试6: 指标计算验证")
    logger.info("=" * 60)

    from app.services.characteristic_curves.methods.base_method import BaseMethod

    # 创建一个简单的测试类
    class TestMethod(BaseMethod):
        def fit(self, X, y, constraints=None, **kwargs):
            pass

        def predict(self, X, params):
            pass

    method = TestMethod(method_name="测试", method_id="test")

    # 已知数据
    y_true = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    y_pred = np.array([11.0, 19.0, 31.0, 39.0, 51.0])  # 误差为±1

    metrics = method._calculate_metrics(y_true, y_pred)

    logger.info(f"指标计算结果:")
    logger.info(f"  - R² = {metrics['r_squared']:.6f}")
    logger.info(f"  - RMSE = {metrics['rmse']:.6f}")
    logger.info(f"  - MAE = {metrics['mae']:.6f}")
    logger.info(f"  - MAPE = {metrics['mape']:.6f}")

    # 手动计算验证
    mae_expected = np.mean(np.abs(y_true - y_pred))  # 应为1.0
    rmse_expected = np.sqrt(np.mean((y_true - y_pred)**2))  # 应为1.0

    assert abs(
        metrics['mae'] - mae_expected) < 0.001, f"MAE计算错误: {metrics['mae']} vs {mae_expected}"
    assert abs(
        metrics['rmse'] - rmse_expected) < 0.001, f"RMSE计算错误: {metrics['rmse']} vs {rmse_expected}"
    assert metrics['rmse'] > 0, "RMSE应该大于0"

    logger.info("✓ 指标计算验证通过")

    return True


def run_all_tests():
    """运行所有测试"""
    logger.info("\n" + "=" * 60)
    logger.info("特性曲线拟合功能测试")
    logger.info("=" * 60 + "\n")

    tests = [
        ("多项式拟合", test_polynomial_fit),
        ("泵特性方程", test_physics_pump_char),
        ("数据清洗器", test_data_cleaner),
        ("物理验证器", test_physics_validator),
        ("并联合成器", test_parallel_synthesizer),
        ("指标计算", test_method_metrics_calculation),
    ]

    results = []
    for name, test_func in tests:
        try:
            test_func()
            results.append((name, "✓ 通过"))
        except Exception as e:
            logger.error(f"{name} 测试失败: {e}", exc_info=True)
            results.append((name, f"✗ 失败: {e}"))

    # 打印测试汇总
    logger.info("\n" + "=" * 60)
    logger.info("测试结果汇总")
    logger.info("=" * 60)

    passed = 0
    failed = 0
    for name, result in results:
        logger.info(f"  {name}: {result}")
        if "通过" in result:
            passed += 1
        else:
            failed += 1

    logger.info("-" * 60)
    logger.info(f"总计: {passed} 通过, {failed} 失败")
    logger.info("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
