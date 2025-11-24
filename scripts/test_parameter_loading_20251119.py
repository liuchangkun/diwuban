"""
测试参数加载
验证ParameterManager是否正确加载所有参数
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database
from app.core.config.loader import load_settings
from app.services.calculation.shared.parameter_manager import ParameterManager


def test_parameter_loading():
    """测试参数加载"""
    print("=" * 80)
    print("测试: 验证ParameterManager参数加载")
    print("=" * 80)
    
    param_manager = ParameterManager()
    
    # 测试1: 加载pump_flow_rate参数（不指定method_id）
    print("\n测试1: 加载pump_flow_rate参数（不指定method_id）")
    print("-" * 80)
    
    try:
        params = param_manager.get_parameters(
            metric_key='pump_flow_rate',
            method_id=None,  # 不指定method_id
            station_id=1,
            device_id=1
        )
        
        print(f"✅ 成功加载 {len(params)} 个参数:")
        for key, value in sorted(params.items()):
            print(f"  - {key} = {value}")
        
        # 检查validator需要的参数
        required_params = ['min_flow', 'max_flow', 'max_ratio']
        missing = [p for p in required_params if p not in params]
        
        if missing:
            print(f"\n❌ 缺少validator需要的参数: {missing}")
            return False
        else:
            print(f"\n✅ validator需要的参数都存在: {required_params}")
            return True
            
    except Exception as e:
        print(f"❌ 参数加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_parameter_loading_with_method_id():
    """测试参数加载（指定method_id）"""
    print("\n" + "=" * 80)
    print("测试2: 加载pump_flow_rate参数（指定method_id='data_filter'）")
    print("=" * 80)
    
    param_manager = ParameterManager()
    
    try:
        params = param_manager.get_parameters(
            metric_key='pump_flow_rate',
            method_id='data_filter',
            station_id=1,
            device_id=1
        )
        
        print(f"✅ 成功加载 {len(params)} 个参数:")
        for key, value in sorted(params.items()):
            print(f"  - {key} = {value}")
        
        # 检查validator需要的参数
        required_params = ['min_flow', 'max_flow', 'max_ratio']
        missing = [p for p in required_params if p not in params]
        
        if missing:
            print(f"\n❌ 缺少validator需要的参数: {missing}")
            return False
        else:
            print(f"\n✅ validator需要的参数都存在: {required_params}")
            return True
            
    except Exception as e:
        print(f"❌ 参数加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    # 初始化数据库
    config_dir = Path(__file__).parent.parent / 'config'
    settings = load_settings(config_dir)
    init_database(settings)
    
    print("\n🔍 开始测试参数加载\n")
    
    # 运行测试
    results = []
    results.append(("不指定method_id", test_parameter_loading()))
    results.append(("指定method_id='data_filter'", test_parameter_loading_with_method_id()))
    
    # 汇总结果
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！参数加载正常！")
        return 0
    else:
        print(f"\n⚠️ {total - passed}个测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(main())

