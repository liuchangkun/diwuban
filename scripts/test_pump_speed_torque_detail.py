"""
测试pump_speed和pump_torque的详细执行过程
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib import Path
from datetime import datetime, timezone
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 初始化数据库
from app.adapters.db import init_database
from app.core.config.loader_new import load_settings

settings = load_settings(Path("configs"))
init_database(settings)

# 导入计算函数
from app.services.calculation.metrics.pump_speed import calculate_pump_speed
from app.services.calculation.metrics.pump_torque import calculate_pump_torque
from app.services.calculation.shared.scheduler import Task

def test_metric(metric_name, calculate_func):
    """测试单个指标"""
    print(f"\n{'='*100}")
    print(f"测试指标: {metric_name}")
    print(f"{'='*100}\n")
    
    # 创建任务
    task = Task(
        task_id=f"test_{metric_name}",
        station_id=1,
        device_id=6,
        metric_key=metric_name,
        start_time=datetime(2025, 10, 23, 4, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2025, 10, 23, 4, 1, 0, tzinfo=timezone.utc)
    )
    
    # 执行计算
    result = calculate_func(task)
    
    # 打印结果
    print(f"\n结果:")
    print(f"  success: {result.success}")
    print(f"  results_count: {result.results_count}")
    if result.error_message:
        print(f"  error_message: {result.error_message[:500]}")
    
    return result

def main():
    print("\n" + "=" * 100)
    print("pump_speed和pump_torque详细测试")
    print("=" * 100)
    
    # 测试pump_speed
    pump_speed_result = test_metric("pump_speed", calculate_pump_speed)
    
    # 测试pump_torque
    pump_torque_result = test_metric("pump_torque", calculate_pump_torque)
    
    # 总结
    print(f"\n{'='*100}")
    print("测试总结")
    print(f"{'='*100}")
    print(f"pump_speed: {'成功' if pump_speed_result.success else '失败'}, 写入{pump_speed_result.results_count}条")
    print(f"pump_torque: {'成功' if pump_torque_result.success else '失败'}, 写入{pump_torque_result.results_count}条")
    print(f"{'='*100}\n")

if __name__ == "__main__":
    main()

