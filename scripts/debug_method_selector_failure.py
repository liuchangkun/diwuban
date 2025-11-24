"""
调试 MethodSelector 失败的原因

专门查看为什么某些时间片的方法选择会失败
"""

import sys
from pathlib import Path
from datetime import datetime
import pytz

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, cleanup_database
from app.services.calculation.metrics.pump_inlet_pressure.pipeline import PumpInletPressurePipeline


def debug_method_selector():
    """调试方法选择器"""
    
    # 初始化配置和数据库连接
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    try:
        # 测试一个失败的时间片（根据调度器的自适应分片，大约是24小时一片）
        TZ_UTC = pytz.UTC
        
        # 第一个时间片：2025-10-22 08:00 ~ 2025-10-23 07:20（应该成功）
        # 第二个时间片：可能不存在（因为总时长只有23.3小时）
        
        # 让我们测试设备1的第一个时间片
        device_id = 1
        start_time = datetime(2025, 10, 22, 8, 0, 0, tzinfo=TZ_UTC)
        end_time = datetime(2025, 10, 23, 7, 20, 0, tzinfo=TZ_UTC)
        
        print("=" * 100)
        print(f"调试 pump_inlet_pressure 方法选择失败")
        print("=" * 100)
        print(f"设备ID: {device_id}")
        print(f"时间范围: {start_time} ~ {end_time}")
        print("=" * 100)
        
        # 创建 Pipeline 实例
        pipeline = PumpInletPressurePipeline()
        
        # 执行计算
        try:
            result = pipeline.execute(
                station_id=1,
                device_id=device_id,
                start_time=start_time,
                end_time=end_time,
                task_id="debug_task"
            )
            
            print(f"\n✅ 计算成功！")
            print(f"写入记录数: {result.get('points_calculated', 0)}")
            
        except Exception as e:
            print(f"\n❌ 计算失败！")
            print(f"错误信息: {str(e)}")
            print(f"错误类型: {type(e).__name__}")
            
            # 打印详细的堆栈跟踪
            import traceback
            traceback.print_exc()
        
    finally:
        # 清理资源
        cleanup_database()


if __name__ == "__main__":
    debug_method_selector()

