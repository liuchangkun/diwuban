"""
测试参数优化器修复
"""
import numpy as np
from app.services.calculation.parameter_optimizer import ParameterOptimizer

def test_nan_inf_protection():
    """测试NaN/Inf保护"""
    print("\n" + "="*80)
    print("测试1：NaN/Inf保护")
    print("="*80)
    
    # 创建一个会导致NaN的场景
    optimizer = ParameterOptimizer(forgetting_factor=0.98)
    
    # 创建数据
    np.random.seed(42)
    n_samples = 100
    x = np.linspace(0, 10, n_samples)
    y = 3.0 + 2.0 * x + np.random.normal(0, 0.5, n_samples)
    X = np.column_stack([np.ones(n_samples), x])
    
    # 初始化参数
    theta = np.array([0.0, 0.0])
    P = np.eye(2) * 1000
    
    # 应用RLS
    theta_new, P_new, residuals = optimizer.apply_rls(X, y, theta, P)
    
    # 检查结果
    if np.any(np.isnan(theta_new)) or np.any(np.isinf(theta_new)):
        print("❌ 失败：参数包含NaN或Inf")
        print(f"   theta_new = {theta_new}")
        assert False, "参数包含NaN或Inf"
    else:
        print("✅ 成功：参数不包含NaN或Inf")
        print(f"   theta_new = {theta_new}")
        print(f"   真实参数 = [3.0, 2.0]")
        print(f"   误差 = {np.abs(theta_new - np.array([3.0, 2.0]))}")
        assert True

def test_constraint_application():
    """测试约束应用"""
    print("\n" + "="*80)
    print("测试2：约束应用")
    print("="*80)
    
    optimizer = ParameterOptimizer(forgetting_factor=0.98)
    
    # 测试正常值
    theta = np.array([3.0, 7.0])
    param_names = ['a', 'b']
    param_bounds = {'a': (0.0, 10.0), 'b': (0.0, 5.0)}
    
    theta_constrained = optimizer._apply_constraints(theta, param_names, param_bounds)
    
    print(f"原始参数: {theta}")
    print(f"约束范围: a ∈ [0, 10], b ∈ [0, 5]")
    print(f"约束后参数: {theta_constrained}")

    if theta_constrained[0] == 3.0 and theta_constrained[1] == 5.0:
        print("✅ 成功：约束正确应用")
        assert True
    else:
        print("❌ 失败：约束未正确应用")
        assert False, "约束未正确应用"

def test_nan_constraint_application():
    """测试NaN值的约束应用"""
    print("\n" + "="*80)
    print("测试3：NaN值的约束应用")
    print("="*80)
    
    optimizer = ParameterOptimizer(forgetting_factor=0.98)
    
    # 测试NaN值
    theta = np.array([3.0, np.nan])
    param_names = ['a', 'b']
    param_bounds = {'a': (0.0, 10.0), 'b': (0.0, 5.0)}
    
    theta_constrained = optimizer._apply_constraints(theta, param_names, param_bounds)
    
    print(f"原始参数: {theta}")
    print(f"约束范围: a ∈ [0, 10], b ∈ [0, 5]")
    print(f"约束后参数: {theta_constrained}")

    if theta_constrained[0] == 3.0 and theta_constrained[1] == 2.5:
        print("✅ 成功：NaN值被替换为中间值")
        assert True
    else:
        print("❌ 失败：NaN值未正确处理")
        assert False, "NaN值未正确处理"

def test_validation():
    """测试参数验证"""
    print("\n" + "="*80)
    print("测试4：参数验证")
    print("="*80)
    
    optimizer = ParameterOptimizer(forgetting_factor=0.98)
    
    # 测试正常值
    theta = np.array([3.0, 2.0])
    param_names = ['a', 'b']
    param_bounds = {'a': (0.0, 10.0), 'b': (0.0, 5.0)}
    
    result = optimizer._validate_parameters(theta, param_names, param_bounds)
    print(f"参数: {theta}")
    print(f"约束范围: a ∈ [0, 10], b ∈ [0, 5]")
    print(f"验证结果: {result}")
    
    if result:
        print("✅ 成功：正常值通过验证")
    else:
        print("❌ 失败：正常值未通过验证")
        assert False, "正常值未通过验证"

    # 测试超出范围的值
    theta = np.array([3.0, 7.0])
    result = optimizer._validate_parameters(theta, param_names, param_bounds)
    print(f"\n参数: {theta}")
    print(f"约束范围: a ∈ [0, 10], b ∈ [0, 5]")
    print(f"验证结果: {result}")

    if not result:
        print("✅ 成功：超出范围的值未通过验证")
    else:
        print("❌ 失败：超出范围的值通过了验证")
        assert False, "超出范围的值通过了验证"

    # 测试NaN值
    theta = np.array([3.0, np.nan])
    result = optimizer._validate_parameters(theta, param_names, param_bounds)
    print(f"\n参数: {theta}")
    print(f"验证结果: {result}")

    if not result:
        print("✅ 成功：NaN值未通过验证")
        assert True
    else:
        print("❌ 失败：NaN值通过了验证")
        assert False, "NaN值通过了验证"

if __name__ == "__main__":
    print("\n" + "="*80)
    print("参数优化器修复测试")
    print("="*80)
    
    results = []
    results.append(("NaN/Inf保护", test_nan_inf_protection()))
    results.append(("约束应用", test_constraint_application()))
    results.append(("NaN值的约束应用", test_nan_constraint_application()))
    results.append(("参数验证", test_validation()))
    
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, r in results if r)
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️ {total - passed} 个测试失败")

