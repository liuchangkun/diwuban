"""
测试参数缺失时的错误处理

验证当物理常数参数缺失时，系统能够正确报错
"""

import sys
sys.path.insert(0, 'd:/Augment/diwuban')

import numpy as np
from app.services.calculation.methods.head_coef_v1 import calculate_head_coef_v1
from app.services.calculation.methods.pin_coef_v1 import calculate_pin_coef_v1
from app.services.calculation.methods.eff_simple_v1 import calculate_eff_simple_v1

def test_missing_parameters():
    """测试参数缺失时的错误处理"""
    print("=" * 80)
    print("测试参数缺失时的错误处理")
    print("=" * 80)
    
    # 准备测试数据
    data = {
        'pump_outlet_pressure': np.array([0.5]),
        'pool_liquid_level': np.array([5.0]),
        'pump_flow_rate': np.array([100.0]),
        'main_pipeline_flow_rate': np.array([300.0]),
        'pump_head': np.array([50.0]),
        'pump_active_power': np.array([100.0])
    }
    
    # 测试1：HEAD_COEF_V1 缺少 rho 参数
    print("\n[测试1] HEAD_COEF_V1 缺少 rho 参数")
    params_missing_rho = {
        'g': 9.80665,
        'a0': 50.0,
        'a1': -0.01,
        'a2': -0.0001,
        'a3': 0.0,
        'a4': 0.0,
        'a5': 0.0,
        'H_min': 0.0,
        'H_max': 100.0
    }
    try:
        result = calculate_head_coef_v1(data, params_missing_rho)
        print("  ❌ 应该抛出 ValueError，但没有抛出")
        return False
    except ValueError as e:
        if "缺少必需的参数" in str(e) and "rho" in str(e):
            print(f"  ✅ 正确抛出 ValueError: {e}")
        else:
            print(f"  ❌ 错误信息不正确: {e}")
            return False
    
    # 测试2：PIN_COEF_V1 缺少 g 参数
    print("\n[测试2] PIN_COEF_V1 缺少 g 参数")
    params_missing_g = {
        'rho': 1000.0,
        'b0': 101325.0,
        'b1': 1.0,
        'b2': 0.0,
        'b3': 0.0,
        'P_in_min': -0.1,
        'P_in_max': 1.0
    }
    try:
        result = calculate_pin_coef_v1(data, params_missing_g)
        print("  ❌ 应该抛出 ValueError，但没有抛出")
        return False
    except ValueError as e:
        if "缺少必需的参数" in str(e) and "g" in str(e):
            print(f"  ✅ 正确抛出 ValueError: {e}")
        else:
            print(f"  ❌ 错误信息不正确: {e}")
            return False
    
    # 测试3：EFF_SIMPLE_V1 缺少物理常数参数
    print("\n[测试3] EFF_SIMPLE_V1 缺少物理常数参数")
    params_missing_physical = {
        'eta_motor': 0.92,
        'eta_max': 0.85
    }
    try:
        result = calculate_eff_simple_v1(data, params_missing_physical)
        print("  ❌ 应该抛出 ValueError，但没有抛出")
        return False
    except ValueError as e:
        if "缺少必需的物理常数参数" in str(e):
            print(f"  ✅ 正确抛出 ValueError: {e}")
        else:
            print(f"  ❌ 错误信息不正确: {e}")
            return False
    
    # 测试4：HEAD_COEF_V1 缺少系数参数
    print("\n[测试4] HEAD_COEF_V1 缺少系数参数 a0")
    params_missing_coef = {
        'rho': 1000.0,
        'g': 9.80665,
        'a1': -0.01,
        'a2': -0.0001,
        'a3': 0.0,
        'a4': 0.0,
        'a5': 0.0,
        'H_min': 0.0,
        'H_max': 100.0
    }
    try:
        result = calculate_head_coef_v1(data, params_missing_coef)
        print("  ❌ 应该抛出 ValueError，但没有抛出")
        return False
    except ValueError as e:
        if "缺少必需的参数" in str(e) and "a0" in str(e):
            print(f"  ✅ 正确抛出 ValueError: {e}")
        else:
            print(f"  ❌ 错误信息不正确: {e}")
            return False
    
    print("\n" + "=" * 80)
    print("✅ 所有参数缺失错误处理测试通过！")
    print("=" * 80)
    return True

if __name__ == '__main__':
    try:
        success = test_missing_parameters()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

