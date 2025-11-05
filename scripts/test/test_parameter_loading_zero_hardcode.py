"""
测试参数加载机制 - 零硬编码验证

验证所有计算方法能够从数据库正确加载物理常数和参数
"""

import sys
sys.path.insert(0, 'd:/Augment/diwuban')

from pathlib import Path
from app.services.calculation.orchestrator import CalculationOrchestrator
from app.adapters.db import init_database
from app.core.config.loader import load_settings

def test_parameter_loading():
    """测试参数加载机制"""
    print("=" * 80)
    print("测试参数加载机制 - 零硬编码验证")
    print("=" * 80)

    # 初始化数据库连接池
    settings = load_settings(Path("configs"))
    init_database(settings)
    print("✅ 数据库连接池初始化成功\n")

    orchestrator = CalculationOrchestrator()

    # 使用设备ID=1进行测试
    test_device_id = 1

    # 测试1：pump_head_method_main 应该有 rho, g, P_atm
    print("\n[测试1] pump_head_method_main 参数加载")
    params = orchestrator.load_parameters(device_id=test_device_id, method_id='pump_head_method_main')
    print(f"  加载的参数: {list(params.keys())}")
    assert 'rho' in params, "缺少 rho 参数"
    assert 'g' in params, "缺少 g 参数"
    assert 'P_atm' in params, "缺少 P_atm 参数"
    print(f"  ✅ rho = {params['rho']}")
    print(f"  ✅ g = {params['g']}")
    print(f"  ✅ P_atm = {params['P_atm']}")
    
    # 测试2：HEAD_COEF_V1 应该有 rho, g, a0-a5, H_min, H_max
    print("\n[测试2] HEAD_COEF_V1 参数加载")
    params = orchestrator.load_parameters(device_id=test_device_id, method_id='HEAD_COEF_V1')
    print(f"  加载的参数: {list(params.keys())}")
    assert 'rho' in params, "缺少 rho 参数"
    assert 'g' in params, "缺少 g 参数"
    assert 'a0' in params, "缺少 a0 参数"
    assert 'a1' in params, "缺少 a1 参数"
    assert 'a2' in params, "缺少 a2 参数"
    assert 'a3' in params, "缺少 a3 参数"
    assert 'a4' in params, "缺少 a4 参数"
    assert 'a5' in params, "缺少 a5 参数"
    assert 'H_min' in params, "缺少 H_min 参数"
    assert 'H_max' in params, "缺少 H_max 参数"
    assert len(params) >= 10, f"参数数量不足，预期>=10，实际{len(params)}"
    print(f"  ✅ 物理常数: rho={params['rho']}, g={params['g']}")
    print(f"  ✅ 系数参数: a0={params['a0']}, a1={params['a1']}, a2={params['a2']}")
    print(f"  ✅ 边界参数: H_min={params['H_min']}, H_max={params['H_max']}")
    
    # 测试3：PIN_COEF_V1 应该有 rho, g, b0-b3, P_in_min, P_in_max
    print("\n[测试3] PIN_COEF_V1 参数加载")
    params = orchestrator.load_parameters(device_id=test_device_id, method_id='PIN_COEF_V1')
    print(f"  加载的参数: {list(params.keys())}")
    assert 'rho' in params, "缺少 rho 参数"
    assert 'g' in params, "缺少 g 参数"
    assert 'b0' in params, "缺少 b0 参数"
    assert 'b1' in params, "缺少 b1 参数"
    assert 'b2' in params, "缺少 b2 参数"
    assert 'b3' in params, "缺少 b3 参数"
    assert 'P_in_min' in params, "缺少 P_in_min 参数"
    assert 'P_in_max' in params, "缺少 P_in_max 参数"
    assert len(params) >= 8, f"参数数量不足，预期>=8，实际{len(params)}"
    print(f"  ✅ 物理常数: rho={params['rho']}, g={params['g']}")
    print(f"  ✅ 系数参数: b0={params['b0']}, b1={params['b1']}, b2={params['b2']}, b3={params['b3']}")
    print(f"  ✅ 边界参数: P_in_min={params['P_in_min']}, P_in_max={params['P_in_max']}")
    
    # 测试4：EFF_SIMPLE_V1 应该有 rho, g, eta_motor, eta_max
    print("\n[测试4] EFF_SIMPLE_V1 参数加载")
    params = orchestrator.load_parameters(device_id=test_device_id, method_id='EFF_SIMPLE_V1')
    print(f"  加载的参数: {list(params.keys())}")
    assert 'rho' in params, "缺少 rho 参数"
    assert 'g' in params, "缺少 g 参数"
    assert 'eta_motor' in params, "缺少 eta_motor 参数"
    assert 'eta_max' in params, "缺少 eta_max 参数"
    print(f"  ✅ 物理常数: rho={params['rho']}, g={params['g']}")
    print(f"  ✅ 可优化参数: eta_motor={params['eta_motor']}, eta_max={params['eta_max']}")
    
    # 测试5：pump_torque_method_a 应该有 rho, g
    print("\n[测试5] pump_torque_method_a 参数加载")
    params = orchestrator.load_parameters(device_id=test_device_id, method_id='pump_torque_method_a')
    print(f"  加载的参数: {list(params.keys())}")
    assert 'rho' in params, "缺少 rho 参数"
    assert 'g' in params, "缺少 g 参数"
    print(f"  ✅ 物理常数: rho={params['rho']}, g={params['g']}")
    
    print("\n" + "=" * 80)
    print("✅ 所有参数加载测试通过！")
    print("=" * 80)

if __name__ == '__main__':
    try:
        test_parameter_loading()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

