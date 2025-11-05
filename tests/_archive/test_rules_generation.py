#!/usr/bin/env python
"""
测试规则生成函数
直接调用修改后的规则生成函数，验证是否能生成规则数据
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.config.loader import load_settings
from app.services.rules.auto_baseline_b import run_auto_baseline_b
from app.services.rules.running_thresholds_b import run_running_thresholds_b
from app.services.rules.metric_quality_rules_b import compute_metric_quality_rules_shadow

def main():
    print("=" * 80)
    print("测试规则生成函数")
    print("=" * 80)

    settings = load_settings(Path("configs"))
    
    # 测试1: auto_baseline_b
    print("\n[测试1] 运行 auto_baseline_b...")
    try:
        result = run_auto_baseline_b(
            settings,
            start=None,  # 自动检测时间窗口
            end=None,
            station_id=None,
            device_id=None,
            method="stl_residual",
            version="vB_shadow"
        )
        print(f"✓ auto_baseline_b 完成: {result}")
    except Exception as e:
        print(f"✗ auto_baseline_b 失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试2: running_thresholds_b
    print("\n[测试2] 运行 running_thresholds_b...")
    try:
        result = run_running_thresholds_b(
            settings,
            start=None,  # 自动检测时间窗口
            end=None,
            station_id=None,
            device_id=None,
            ensure_rows=True,
            method="robust"
        )
        print(f"✓ running_thresholds_b 完成: {result}")
    except Exception as e:
        print(f"✗ running_thresholds_b 失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试3: metric_quality_rules_b
    print("\n[测试3] 运行 compute_metric_quality_rules_shadow...")
    try:
        result = compute_metric_quality_rules_shadow(
            settings,
            station_id=None,
            device_id=None,
            method="from_shadow_baseline",
            version="vB_shadow"
        )
        print(f"✓ compute_metric_quality_rules_shadow 完成: {result}")
    except Exception as e:
        print(f"✗ compute_metric_quality_rules_shadow 失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    main()

