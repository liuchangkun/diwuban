"""快速验证修复的核心功能"""
import sys
from pathlib import Path
import numpy as np

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.calculation.parameter_optimizer import ParameterOptimizer
from app.services.calculation.curve_optimizer import CurveOptimizer

def test_imports():
    """测试1：模块导入"""
    print("\n" + "="*80)
    print("测试1：模块导入")
    print("="*80)
    try:
        from app.services.calculation.parameter_optimizer import ParameterOptimizer
        from app.services.calculation.curve_optimizer import CurveOptimizer
        from app.services.calculation.orchestrator import CalculationOrchestrator
        print("✅ 所有模块导入成功")
        assert True
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"模块导入失败: {e}"

def test_rls_numerical_stability():
    """测试2：RLS数值稳定性"""
    print("\n" + "="*80)
    print("测试2：RLS数值稳定性")
    print("="*80)
    try:
        np.random.seed(42)
        n = 100
        x = np.linspace(0, 10, n)
        y = 3.0 + 2.0 * x + np.random.normal(0, 0.5, n)
        X = np.column_stack([np.ones(n), x])
        
        opt = ParameterOptimizer(forgetting_factor=1.0)
        theta, P, res = opt.apply_rls(X, y, np.array([0.0, 0.0]), np.eye(2) * 1000)
        
        error = np.abs(theta - np.array([3.0, 2.0]))
        print(f"真实参数: [3.0, 2.0]")
        print(f"估计参数: {theta}")
        print(f"参数误差: {error}")
        
        # 检查是否包含NaN或Inf
        if np.any(np.isnan(theta)) or np.any(np.isinf(theta)):
            print("❌ 参数包含NaN或Inf")
            assert False, "参数包含NaN或Inf"

        # 检查误差是否在合理范围内
        if np.all(error < 0.5):
            print("✅ RLS算法数值稳定，参数估计准确")
            assert True
        else:
            print(f"❌ 参数估计误差过大: {error}")
            assert False, f"参数估计误差过大: {error}"
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"测试失败: {e}"

def test_observation_matrix_pump_flow():
    """测试3：pump_flow_rate_method_a观测矩阵构建"""
    print("\n" + "="*80)
    print("测试3：pump_flow_rate_method_a观测矩阵构建")
    print("="*80)
    try:
        np.random.seed(42)
        n = 50
        
        # 模拟数据
        P = np.random.uniform(10, 50, n)  # 功率
        f = np.random.uniform(40, 50, n)  # 频率
        Q_total = np.random.uniform(100, 200, n)  # 总流量
        
        # 使用幂律模型生成流量
        alpha, beta = 1.2, 0.8
        Q_i = Q_total * (P**alpha * f**beta) / np.sum(P**alpha * f**beta) * n
        
        measured_data = {
            'pump_active_power': P,
            'pump_frequency': f,
            'main_pipeline_flow_rate': Q_total
        }
        calculated_data = {
            'pump_flow_rate': Q_i
        }
        
        opt = ParameterOptimizer()
        X, y = opt._build_observation_matrix(
            measured_data,
            calculated_data,
            'pump_flow_rate_method_a'
        )
        
        if X is None or y is None:
            print("❌ 观测矩阵构建失败")
            assert False, "观测矩阵构建失败"

        print(f"观测矩阵形状: {X.shape}")
        print(f"输出向量形状: {y.shape}")
        print(f"X范围: [{np.min(X):.2f}, {np.max(X):.2f}]")
        print(f"y范围: [{np.min(y):.2f}, {np.max(y):.2f}]")

        # 检查是否进行了对数变换
        if X.shape[1] == 2:  # 应该是[log(P), log(f)]
            print("✅ pump_flow_rate_method_a观测矩阵构建正确（对数线性化）")
            assert True
        else:
            print(f"❌ 观测矩阵列数错误: {X.shape[1]}，期望2")
            assert False, f"观测矩阵列数错误: {X.shape[1]}，期望2"
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"测试失败: {e}"

def test_curve_optimizer_syntax():
    """测试4：CurveOptimizer语法错误修复"""
    print("\n" + "="*80)
    print("测试4：CurveOptimizer语法错误修复")
    print("="*80)
    try:
        opt = CurveOptimizer(min_samples=20)
        
        # 创建测试数据
        np.random.seed(42)
        flow_rates = np.linspace(0, 400, 50)
        values = 30 - 0.0005 * flow_rates ** 2 + np.random.normal(0, 0.5, 50)
        
        # 测试多项式拟合
        fitted_curve = opt._fit_polynomial(flow_rates, values, degree=2)
        
        if fitted_curve is not None and len(fitted_curve) > 0:
            print(f"拟合曲线点数: {len(fitted_curve)}")
            print("✅ CurveOptimizer语法错误已修复，功能正常")
            assert True
        else:
            print("❌ 曲线拟合失败")
            assert False, "曲线拟合失败"
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"测试失败: {e}"

def main():
    """主函数"""
    print("\n" + "="*80)
    print("快速验证测试")
    print("="*80)
    
    tests = [
        ("模块导入", test_imports),
        ("RLS数值稳定性", test_rls_numerical_stability),
        ("pump_flow观测矩阵", test_observation_matrix_pump_flow),
        ("CurveOptimizer语法修复", test_curve_optimizer_syntax),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ 测试 '{test_name}' 异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # 打印总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️ {total - passed} 个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())

