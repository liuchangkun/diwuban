"""
运行所有已实现指标的计算

使用Scheduler调度器计算以下指标：
1. pump_flow_rate（泵流量）
2. pump_inlet_pressure（泵入口压力）
3. pump_head（泵扬程）
4. pump_efficiency（泵效率）
5. pump_speed（泵转速）

时间范围：2025-10-22 16:00:00 到 2025-10-23 17:00:00
设备范围：设备1-6（泵设备）
"""

import sys
from pathlib import Path
from datetime import datetime
import logging

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, cleanup_database
from app.services.calculation.shared.shared_services import SharedServices
from app.core.logging.setup import init_logging


def main():
    """主函数"""
    # 1. 初始化配置
    print("=" * 80)
    print("开始运行所有已实现指标的计算")
    print("=" * 80)

    # 加载配置
    settings = load_settings(Path("configs"))

    # 初始化日志
    init_logging(Path("configs"))
    logger = logging.getLogger(__name__)

    # 初始化数据库连接池
    init_database(settings)
    logger.info("数据库连接池已初始化")
    
    # 初始化SharedServices
    shared_services = SharedServices()
    logger.info("SharedServices已初始化")
    
    # 2. 定义计算参数
    device_ids = [1, 2, 3, 4, 5, 6]  # 泵设备
    start_time = datetime(2025, 10, 22, 16, 0, 0)
    end_time = datetime(2025, 10, 23, 17, 0, 0)
    
    # 要计算的指标列表
    metrics = [
        "pump_flow_rate",
        "pump_inlet_pressure",
        "pump_head",
        "pump_efficiency",
        "pump_speed"
    ]
    
    logger.info(
        "计算参数",
        extra={
            "extra_data": {
                "设备ID列表": device_ids,
                "时间范围": f"{start_time} ~ {end_time}",
                "指标列表": metrics,
                "指标数量": len(metrics)
            }
        }
    )
    
    # 3. 执行计算
    try:
        print(f"\n开始计算 {len(metrics)} 个指标...")
        print(f"设备范围: {device_ids}")
        print(f"时间范围: {start_time} ~ {end_time}")
        print("-" * 80)
        
        results = shared_services.scheduler.schedule_all_metrics(
            device_ids=device_ids,
            start_time=start_time,
            end_time=end_time,
            time_chunk_hours=24,  # 24小时分片
            metrics=metrics
        )
        
        # 4. 输出结果统计
        print("\n" + "=" * 80)
        print("计算完成！结果统计：")
        print("=" * 80)
        
        for metric_key, metric_result in results.items():
            print(f"\n指标: {metric_key}")
            print(f"  - 成功任务数: {metric_result.get('success_count', 0)}")
            print(f"  - 失败任务数: {metric_result.get('failure_count', 0)}")
            print(f"  - 总记录数: {metric_result.get('total_points', 0)}")
            print(f"  - 执行时长: {metric_result.get('duration_seconds', 0):.2f}秒")
            
            # 如果有失败任务，输出错误信息
            if metric_result.get('failure_count', 0) > 0:
                print(f"  ⚠️ 失败任务详情:")
                for task_result in metric_result.get('results', []):
                    if not task_result.success:
                        print(f"    - 设备{task_result.device_id}: {task_result.error_message}")
        
        # 5. 总体统计
        total_success = sum(r.get('success_count', 0) for r in results.values())
        total_failure = sum(r.get('failure_count', 0) for r in results.values())
        total_points = sum(r.get('total_points', 0) for r in results.values())
        total_duration = sum(r.get('duration_seconds', 0) for r in results.values())
        
        print("\n" + "=" * 80)
        print("总体统计：")
        print("=" * 80)
        print(f"总成功任务数: {total_success}")
        print(f"总失败任务数: {total_failure}")
        print(f"总记录数: {total_points}")
        print(f"总执行时长: {total_duration:.2f}秒")
        print(f"成功率: {total_success / (total_success + total_failure) * 100:.2f}%" if (total_success + total_failure) > 0 else "N/A")
        
        logger.info(
            "所有指标计算完成",
            extra={
                "extra_data": {
                    "总成功任务数": total_success,
                    "总失败任务数": total_failure,
                    "总记录数": total_points,
                    "总执行时长秒": total_duration
                }
            }
        )
        
    except Exception as e:
        logger.error(f"计算过程中发生错误: {e}", exc_info=True)
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 6. 清理资源
        shared_services.scheduler.shutdown()
        cleanup_database()
        logger.info("资源已清理")
        print("\n" + "=" * 80)
        print("程序结束")
        print("=" * 80)


if __name__ == "__main__":
    main()

