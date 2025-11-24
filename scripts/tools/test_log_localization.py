"""
测试日志中文化效果

运行一个简单的计算任务，检查日志输出是否已中文化
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, cleanup_database
from app.services.calculation.metrics.pump_speed.pipeline import PumpSpeedPipeline
from app.core.logging.setup import init_logging, set_context, clear_context
import time


def main():
    """主函数"""
    print("=" * 80)
    print("日志中文化效果测试")
    print("=" * 80)
    
    # 初始化配置
    config_dir = Path("configs")
    settings = load_settings(config_dir)
    
    # 初始化日志系统
    init_logging(config_dir, "Asia/Shanghai")
    
    # 初始化数据库
    init_database(settings)
    
    try:
        # 设置上下文
        task_id = f"test-log-{int(time.time())}"
        set_context(
            request_id=task_id,
            trace_id=f"trace-{task_id}",
            user_id="test-user",
            tenant="test"
        )
        
        # 运行一个简单的计算任务
        print("\n开始运行 pump_speed 计算任务...")
        print(f"任务ID: {task_id}")
        
        pipeline = PumpSpeedPipeline()
        
        # 计算最近1小时的数据
        end_time = datetime(2024, 11, 20, 12, 0)
        start_time = end_time - timedelta(hours=1)
        
        result = pipeline.execute(
            station_id=1,
            device_id=1,
            start_time=start_time,
            end_time=end_time,
            task_id=task_id
        )
        
        print(f"\n✅ 计算完成！")
        print(f"   结果: {result}")
        
        # 清除上下文
        clear_context()
        
    finally:
        # 清理数据库连接
        cleanup_database()
    
    print("\n" + "=" * 80)
    print("测试完成！请检查 logs/app.log 文件查看中文化效果")
    print("=" * 80)


if __name__ == '__main__':
    main()

