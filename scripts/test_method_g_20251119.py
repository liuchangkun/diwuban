"""
测试method_g实现
验证待机状态检测功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader import load_settings


def test_method_g_parameters():
    """测试method_g参数是否存在"""
    print("=" * 80)
    print("测试1: 验证method_g参数")
    print("=" * 80)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT param_name, param_value, param_type
                FROM calculation_parameters
                WHERE metric_key = 'pump_flow_rate'
                  AND method_id = 'data_filter'
                  AND param_name IN ('standby_power_threshold', 'standby_freq_threshold')
                  AND device_id IS NULL
                ORDER BY param_name
            """)
            
            rows = cur.fetchall()
            
            if len(rows) == 2:
                print("✅ method_g参数已配置:")
                for row in rows:
                    print(f"  - {row[0]} = {row[1]} ({row[2]})")
                return True
            else:
                print(f"❌ method_g参数缺失，只找到{len(rows)}个参数")
                return False


def test_method_g_import():
    """测试method_g是否可以导入"""
    print("\n" + "=" * 80)
    print("测试2: 验证method_g导入")
    print("=" * 80)
    
    try:
        from app.services.calculation.metrics.pump_flow_rate.methods.method_g import calculate_method_g
        print("✅ method_g导入成功")
        print(f"  - 函数名: {calculate_method_g.__name__}")
        print(f"  - 模块: {calculate_method_g.__module__}")
        return True
    except Exception as e:
        print(f"❌ method_g导入失败: {e}")
        return False


def test_method_selector_config():
    """测试MethodSelector是否包含method_g配置"""
    print("\n" + "=" * 80)
    print("测试3: 验证MethodSelector配置")
    print("=" * 80)
    
    try:
        from app.services.calculation.metrics.pump_flow_rate.method_selector import MethodSelector
        
        # 检查METHODS列表
        method_ids = [m['id'] for m in MethodSelector.METHODS]
        
        if 'method_g' in method_ids:
            print("✅ MethodSelector包含method_g配置")
            
            # 找到method_g配置
            method_g_config = next(m for m in MethodSelector.METHODS if m['id'] == 'method_g')
            print(f"  - 名称: {method_g_config['name']}")
            print(f"  - 优先级: {method_g_config['priority']}")
            print(f"  - 依赖: {method_g_config['dependencies']}")
            print(f"  - 条件: {method_g_config['conditions']}")
            return True
        else:
            print(f"❌ MethodSelector不包含method_g，当前方法: {method_ids}")
            return False
    except Exception as e:
        print(f"❌ MethodSelector配置检查失败: {e}")
        return False


def test_calculator_mapping():
    """测试Calculator是否包含method_g映射"""
    print("\n" + "=" * 80)
    print("测试4: 验证Calculator映射")
    print("=" * 80)
    
    try:
        from app.services.calculation.metrics.pump_flow_rate.calculator import Calculator
        
        calc = Calculator()
        
        if 'method_g' in calc.methods:
            print("✅ Calculator包含method_g映射")
            print(f"  - 方法数量: {len(calc.methods)}")
            print(f"  - 所有方法: {list(calc.methods.keys())}")
            return True
        else:
            print(f"❌ Calculator不包含method_g，当前方法: {list(calc.methods.keys())}")
            return False
    except Exception as e:
        print(f"❌ Calculator映射检查失败: {e}")
        return False


def main():
    """主函数"""
    # 初始化数据库
    config_dir = Path(__file__).parent.parent / 'config'
    settings = load_settings(config_dir)
    init_database(settings)
    
    print("\n🔍 开始测试method_g实现\n")
    
    # 运行测试
    results = []
    results.append(("参数配置", test_method_g_parameters()))
    results.append(("模块导入", test_method_g_import()))
    results.append(("MethodSelector配置", test_method_selector_config()))
    results.append(("Calculator映射", test_calculator_mapping()))
    
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
        print("\n🎉 所有测试通过！method_g实现成功！")
        return 0
    else:
        print(f"\n⚠️ {total - passed}个测试失败，需要修复")
        return 1


if __name__ == '__main__':
    sys.exit(main())

