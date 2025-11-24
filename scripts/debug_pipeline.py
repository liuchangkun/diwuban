"""调试完整流水线"""

import sys
from pathlib import Path
from datetime import datetime
import pytz
import logging

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置日志级别为 INFO
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.core.config.loader_new import load_settings
from app.adapters.db.pool import initialize_pool, close_pool
from app.services.calculation.shared.scheduler import Task
from app.services.calculation.metrics.pump_head import calculate_pump_head

# 初始化数据库
settings = load_settings(Path("configs"))
initialize_pool(settings)

try:
    # 测试参数
    TZ_UTC = pytz.UTC
    start_time = datetime(2025, 10, 22, 18, 43, 0, tzinfo=TZ_UTC)
    end_time = datetime(2025, 10, 22, 18, 50, 0, tzinfo=TZ_UTC)
    
    # 创建任务
    task = Task(
        task_id="debug_pump_head",
        station_id=1,
        device_id=5,
        metric_key="pump_head",
        start_time=start_time,
        end_time=end_time
    )
    
    print(f"\n开始测试 pump_head 计算流水线")
    print(f"  - 设备ID: {task.device_id}")
    print(f"  - 时间范围: {task.start_time} ~ {task.end_time}")
    
    # 执行计算
    result = calculate_pump_head(task)
    
    print(f"\n计算结果:")
    print(f"  - 成功: {result.success}")
    print(f"  - 写入记录数: {result.results_count}")
    print(f"  - 错误信息: {result.error_message}")
    
finally:
    close_pool()

