"""
刷新运行状态物化视图
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from tests.fixtures.e2e_data_generator import E2EDataGenerator
from app.adapters.db import init_database
from app.core.config.loader_new import load_settings


def main():
    """刷新运行状态物化视图"""
    
    print("=" * 80)
    print("刷新运行状态物化视图")
    print("=" * 80)
    print()
    
    # 初始化数据库连接池
    settings = load_settings(Path("configs"))
    init_database(settings)
    print("✅ 数据库连接池已初始化\n")
    
    with E2EDataGenerator() as generator:
        # 刷新device_id=1-3的运行状态
        generator.refresh_running_state_view([1, 2, 3])
    
    print()
    print("=" * 80)
    print("✅ 运行状态视图刷新完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()

