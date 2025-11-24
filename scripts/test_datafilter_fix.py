"""
测试 DataFilter 修改后的效果

验证：
1. pump_inlet_pressure 的 DataFilter 是否正确过滤掉 pump_flow_rate <= 0 的数据
2. pump_head 的 DataFilter 是否正确过滤掉 pump_flow_rate <= 0 的数据
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
from app.services.calculation.metrics.pump_head import calculate_pump_head
from app.services.calculation.shared.scheduler import Task


def test_datafilter_fix():
    """测试 DataFilter 修改后的效果"""
    
    # 初始化配置和数据库连接
    settings = load_settings(Path("configs"))
    initialize_pool(settings)
    
    try:
        # 测试参数：使用设备6在17:00-20:00的数据（有大量流量=0的数据）
        TZ_UTC = pytz.UTC
        start_time = datetime(2025, 10, 22, 17, 0, 0, tzinfo=TZ_UTC)
        end_time = datetime(2025, 10, 22, 20, 0, 0, tzinfo=TZ_UTC)
        
        print("=" * 100)
        print("🧪 测试 DataFilter 修改后的效果")
        print("=" * 100)
        print(f"测试时间范围: {start_time} ~ {end_time}")
        print(f"测试设备: 设备6")
        print(f"测试重点: 验证流量=0的数据是否被正确过滤")
        print("=" * 100)
        
        # 测试 pump_inlet_pressure
        print(f"\n{'='*100}")
        print("📊 测试1: pump_inlet_pressure")
        print(f"{'='*100}")
        
        task1 = Task(
            task_id="test_pump_inlet_pressure_device6",
            station_id=1,
            device_id=6,
            metric_key="pump_inlet_pressure",
            start_time=start_time,
            end_time=end_time
        )
        
        result1 = calculate_pump_inlet_pressure(task1)
        
        print(f"\n✅ 计算结果:")
        print(f"  - 成功: {result1.success}")
        print(f"  - 错误信息: {getattr(result1, 'error_message', 'N/A')}")
        
        # 测试 pump_head
        print(f"\n{'='*100}")
        print("📊 测试2: pump_head")
        print(f"{'='*100}")
        
        task2 = Task(
            task_id="test_pump_head_device6",
            station_id=1,
            device_id=6,
            metric_key="pump_head",
            start_time=start_time,
            end_time=end_time
        )
        
        result2 = calculate_pump_head(task2)
        
        print(f"\n✅ 计算结果:")
        print(f"  - 成功: {result2.success}")
        print(f"  - 错误信息: {getattr(result2, 'error_message', 'N/A')}")
        
        print(f"\n{'='*100}")
        print("🎯 测试完成")
        print(f"{'='*100}")
        
        print("\n📝 说明:")
        print("  - 修改前：pump_flow_rate >= 0 会保留流量=0的数据")
        print("  - 修改后：pump_flow_rate > 0 会过滤掉流量=0的数据")
        print("  - 预期效果：数据量会减少，但数据质量会提高")
        
    finally:
        # 清理资源
        close_pool()


if __name__ == "__main__":
    test_datafilter_fix()

