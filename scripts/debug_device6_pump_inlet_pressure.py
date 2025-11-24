"""
调试设备6的 pump_inlet_pressure 数据异常问题

问题：设备6只有40,555条 pump_inlet_pressure 记录，而设备5有83,568条
"""

import sys
from pathlib import Path
from datetime import datetime
import pytz

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db.pool import initialize_pool, close_pool
from app.services.calculation.metrics.pump_inlet_pressure import calculate_pump_inlet_pressure
from app.services.calculation.shared.scheduler import Task


def debug_device6():
    """调试设备6的 pump_inlet_pressure 计算"""
    
    # 初始化配置和数据库连接
    settings = load_settings(Path("configs"))
    initialize_pool(settings)
    
    try:
        # 测试参数
        TZ_UTC = pytz.UTC
        start_time = datetime(2025, 10, 22, 8, 0, 0, tzinfo=TZ_UTC)
        end_time = datetime(2025, 10, 23, 7, 20, 0, tzinfo=TZ_UTC)
        
        print("=" * 100)
        print("🔍 调试设备6的 pump_inlet_pressure 数据异常问题")
        print("=" * 100)
        print(f"时间范围: {start_time} ~ {end_time}")
        print(f"时长: {(end_time - start_time).total_seconds() / 3600:.1f} 小时")
        print("=" * 100)
        
        # 测试设备5和设备6
        for device_id in [5, 6]:
            print(f"\n{'='*100}")
            print(f"📊 测试设备 {device_id}")
            print(f"{'='*100}")
            
            # 创建任务
            task = Task(
                task_id=f"debug_device_{device_id}",
                station_id=1,
                device_id=device_id,
                metric_key="pump_inlet_pressure",
                start_time=start_time,
                end_time=end_time
            )
            
            # 执行计算
            result = calculate_pump_inlet_pressure(task)
            
            # 打印结果
            print(f"\n✅ 计算结果:")
            print(f"  - 成功: {result.success}")
            print(f"  - 写入记录数: {getattr(result, 'records_written', 'N/A')}")
            print(f"  - 错误信息: {getattr(result, 'error_message', 'N/A')}")
            print(f"  - 元数据: {getattr(result, 'metadata', {})}")

            metadata = getattr(result, 'metadata', {})
            if metadata:
                print(f"\n📊 详细统计:")
                for key, value in metadata.items():
                    print(f"  - {key}: {value}")
        
        print(f"\n{'='*100}")
        print("🎯 调试完成")
        print(f"{'='*100}")
        
    finally:
        # 清理资源
        close_pool()


if __name__ == "__main__":
    debug_device6()

