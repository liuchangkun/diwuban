#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 DataFilter 配置

用途: 验证迁移脚本 109 执行后，DataFilter 配置是否正确插入
创建日期: 2025-11-14
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db.pool import get_connection, initialize_pool, close_pool


def verify_config() -> bool:
    """验证 DataFilter 配置"""
    print("=" * 80)
    print("验证 DataFilter 配置")
    print("=" * 80)
    print()

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 步骤1: 验证 data_filter 方法记录
                print("📋 步骤1: 验证 data_filter 方法记录")
                cur.execute("""
                    SELECT method_id, method_name, metric_key, is_enabled
                    FROM calculation_method_registry
                    WHERE method_id = 'data_filter'
                        AND metric_key = 'pump_flow_rate'
                """)
                method_row = cur.fetchone()
                
                if method_row:
                    print(f"  ✅ data_filter 方法记录存在")
                    print(f"     - method_id: {method_row[0]}")
                    print(f"     - method_name: {method_row[1]}")
                    print(f"     - metric_key: {method_row[2]}")
                    print(f"     - is_enabled: {method_row[3]}")
                else:
                    print("  ❌ data_filter 方法记录不存在")
                    return False
                
                print()
                
                # 步骤2: 验证配置参数
                print("📋 步骤2: 验证配置参数")
                cur.execute("""
                    SELECT 
                        param_name,
                        param_value,
                        param_type,
                        is_optimizable,
                        confidence_score,
                        station_id,
                        device_id
                    FROM calculation_parameters
                    WHERE metric_key = 'pump_flow_rate'
                        AND method_id = 'data_filter'
                    ORDER BY param_name
                """)
                param_rows = cur.fetchall()
                
                if not param_rows:
                    print("  ❌ 未找到任何配置参数")
                    return False
                
                # 预期参数
                expected_params = {
                    'max_flow': 500.0,
                    'max_power': 200.0,
                    'max_freq': 50.0
                }
                
                # 验证每个参数
                all_passed = True
                found_params = {}
                
                for row in param_rows:
                    param_name = row[0]
                    param_value = float(row[1])
                    param_type = row[2]
                    is_optimizable = row[3]
                    confidence_score = float(row[4]) if row[4] else None
                    station_id = row[5]
                    device_id = row[6]
                    
                    found_params[param_name] = param_value
                    
                    print(f"  参数: {param_name}")
                    print(f"    - 值: {param_value}")
                    print(f"    - 类型: {param_type}")
                    print(f"    - 可优化: {is_optimizable}")
                    print(f"    - 置信度: {confidence_score}")
                    print(f"    - station_id: {station_id}")
                    print(f"    - device_id: {device_id}")
                    
                    # 验证
                    if param_name in expected_params:
                        if param_value == expected_params[param_name]:
                            print(f"    ✅ 值正确")
                        else:
                            print(f"    ❌ 值错误: 预期 {expected_params[param_name]}, 实际 {param_value}")
                            all_passed = False
                        
                        if station_id is None and device_id is None:
                            print(f"    ✅ 全局参数")
                        else:
                            print(f"    ❌ 不是全局参数")
                            all_passed = False
                    else:
                        print(f"    ⚠️ 未预期的参数")
                    
                    print()
                
                # 检查是否所有预期参数都存在
                for param_name, expected_value in expected_params.items():
                    if param_name not in found_params:
                        print(f"  ❌ 缺少参数: {param_name}")
                        all_passed = False
                
                print("=" * 80)
                if all_passed and len(found_params) == len(expected_params):
                    print("✅ 所有配置参数验证通过！")
                    print()
                    print("📋 验证结果:")
                    print("  - data_filter 方法记录: 存在 ✅")
                    print("  - max_flow 参数: 500.0 ✅")
                    print("  - max_power 参数: 200.0 ✅")
                    print("  - max_freq 参数: 50.0 ✅")
                    print("  - 全局参数: 是 ✅")
                else:
                    print("❌ 部分配置参数验证失败！")
                print("=" * 80)
                print()
                
                return all_passed

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ 验证失败！")
        print("=" * 80)
        print(f"错误信息: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    # 加载配置
    settings = load_settings(project_root / "configs")
    
    # 初始化连接池
    try:
        initialize_pool(settings)
    except Exception as e:
        print(f"❌ 初始化连接池失败: {e}")
        return 1
    
    try:
        # 验证配置
        success = verify_config()
        return 0 if success else 1
    finally:
        # 关闭连接池
        try:
            close_pool()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())

