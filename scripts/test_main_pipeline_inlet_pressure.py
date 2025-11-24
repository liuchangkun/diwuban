"""
测试 main_pipeline_inlet_pressure 计算

使用调度器计算 main_pipeline_inlet_pressure 指标
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
    device_ids = [7]  # 总管设备
    start_time = datetime(2025, 10, 22, 16, 0, 0)
    end_time = datetime(2025, 10, 23, 17, 0, 0)
    
    # 要计算的指标列表
    metrics = ["main_pipeline_inlet_pressure"]
    
    logger.info(f"开始计算指标: {metrics}")
    logger.info(f"设备范围: {device_ids}")
    logger.info(f"时间范围: {start_time} ~ {end_time}")
    
    # 3. 执行计算
    try:
        results = shared_services.scheduler.schedule_all_metrics(
            device_ids=device_ids,
            start_time=start_time,
            end_time=end_time,
            time_chunk_hours=24,  # 24小时分片
            metrics=metrics
        )
        
        # 4. 输出结果
        print("\n" + "=" * 80)
        print("计算结果统计")
        print("=" * 80)

        for metric_key, metric_result in results.items():
            print(f"\n指标: {metric_key}")
            print("-" * 80)
            print(f"成功任务数: {metric_result.get('success_count', 0)}")
            print(f"失败任务数: {metric_result.get('failed_count', 0)}")
            print(f"总记录数: {metric_result.get('total_results', 0):,}")
            print(f"执行时长: {metric_result.get('duration', 0):.2f}秒")

        print("\n" + "=" * 80)
        print("总体统计")
        print("=" * 80)

        total_success = sum(r.get('success_count', 0) for r in results.values())
        total_failed = sum(r.get('failed_count', 0) for r in results.values())
        total_records = sum(r.get('total_results', 0) for r in results.values())
        total_duration = sum(r.get('duration', 0) for r in results.values())

        print(f"总成功任务数: {total_success}")
        print(f"总失败任务数: {total_failed}")
        print(f"总记录数: {total_records:,}")
        print(f"总执行时长: {total_duration:.2f}秒")

        print("=" * 80)
        
    except Exception as e:
        logger.error(f"计算失败: {str(e)}", exc_info=True)
        raise
    
    finally:
        # 清理
        cleanup_database()
        logger.info("数据库连接池已关闭")


if __name__ == "__main__":
    main()

