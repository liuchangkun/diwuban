"""
泵 k 系数学习命令行脚本

使用方法：
    # 学习所有泵站的 k 系数（使用全部历史数据）
    python scripts/run_pump_k_learning.py

    # 指定时间范围
    python scripts/run_pump_k_learning.py --start 2025-10-22 --end 2025-10-23

    # 指定泵站
    python scripts/run_pump_k_learning.py --station-id 1

    # 指定设备
    python scripts/run_pump_k_learning.py --station-id 1 --device-id 1
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.adapters.db import init_database
from app.core.config.loader_new import load_settings


def main():
    parser = argparse.ArgumentParser(description='泵 k 系数学习工具')
    parser.add_argument('--start', type=str, default=None,
                        help='开始时间 (ISO格式, 例如: 2025-10-22)')
    parser.add_argument('--end', type=str, default=None,
                        help='结束时间 (ISO格式, 例如: 2025-10-23)')
    parser.add_argument('--station-id', type=int, default=None,
                        help='泵站ID (不指定则处理所有泵站)')
    parser.add_argument('--device-id', type=int, default=None,
                        help='设备ID (不指定则处理泵站所有设备)')
    args = parser.parse_args()

    print("=" * 60)
    print("泵 k 系数学习工具")
    print("=" * 60)

    # 加载配置并初始化数据库
    print("\n[1/3] 初始化数据库连接...")
    settings = load_settings(Path("configs"))
    init_database(settings)
    print("✅ 数据库连接成功")

    # 导入学习函数
    print("\n[2/3] 加载学习模块...")
    from app.services.rules.pump_k_learning import run_pump_k_learning
    print("✅ 模块加载成功")

    # 执行学习
    print("\n[3/3] 开始执行 k 系数学习...")
    print(f"    时间范围: {args.start or '自动'} ~ {args.end or '自动'}")
    print(f"    泵站ID: {args.station_id or '全部'}")
    print(f"    设备ID: {args.device_id or '全部'}")
    print("-" * 60)

    start_time = datetime.now()

    result = run_pump_k_learning(
        settings=settings,
        start=args.start,
        end=args.end,
        station_id=args.station_id,
        device_id=args.device_id
    )

    elapsed = (datetime.now() - start_time).total_seconds()

    print("-" * 60)
    print("\n✅ 学习完成！")
    print(f"    时间窗口: {result['window']['start']} ~ {result['window']['end']}")
    print(f"    学习设备数: {result['learned_devices']}")
    print(f"    保存成功数: {result['saved_devices']}")
    print(f"    耗时: {elapsed:.2f} 秒")

    # 输出详细结果
    if result['results']:
        print("\n学习结果详情:")
        print("-" * 60)
        print(f"{'设备ID':>8} | {'k 值':>10} | {'样本数':>8} | {'置信度':>8} | {'来源':>15}")
        print("-" * 60)
        for r in result['results']:
            print(f"{r['device_id']:>8} | {r['k_value']:>10.6f} | {r['sample_count']:>8} | {r['confidence']:>8} | {r['source']:>15}")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()

