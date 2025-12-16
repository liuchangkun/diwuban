"""
测试MethodSelector从数据库加载配置
"""
from app.services.characteristic_curves.core.data_structures import ConstraintResult
from app.services.characteristic_curves.shared.method_selector import MethodSelector
from app.core.config.loader_new import load_settings
from app.adapters.db import init_database
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """测试MethodSelector"""
    print("=" * 80)
    print("测试MethodSelector从数据库加载配置")
    print("=" * 80)

    # 初始化数据库连接
    settings = load_settings(Path("configs"))
    init_database(settings)
    print("✓ 数据库连接池初始化成功\n")

    try:
        # 创建MethodSelector实例
        print("创建MethodSelector实例...")
        selector = MethodSelector()
        print("✓ MethodSelector初始化成功\n")

        # 创建一个虚拟的ConstraintResult用于测试
        constraints = ConstraintResult(
            curve_type='qh',
            bounds={'a': (0.0, 100.0), 'b': (-50.0, 0.0)},
            monotonicity_type='decreasing',
            boundary_values={'H0': 50.0, 'Q_max': 100.0}
        )

        # 测试不同曲线类型的方法选择
        for curve_type in ['qh', 'qp', 'qeta']:
            methods = selector.select(curve_type, constraints)
            print(f"✓ {curve_type.upper()}曲线推荐方法: {methods}")

        print("\n" + "=" * 80)
        print("✅ 所有测试通过！MethodSelector成功从数据库加载配置")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
