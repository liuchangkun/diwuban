"""
测试 DataFilter 修改后的效果（带数据清理）

验证：
1. 清理旧数据
2. 重新计算
3. 验证过滤效果
"""

import sys
from pathlib import Path
from datetime import datetime
import pytz

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db.pool import initialize_pool, close_pool, get_connection
from app.services.calculation.metrics.pump_inlet_pressure import calculate_pump_inlet_pressure
from app.services.calculation.metrics.pump_head import calculate_pump_head
from app.services.calculation.shared.scheduler import Task


def test_datafilter_fix_with_cleanup():
    """测试 DataFilter 修改后的效果（带数据清理）"""
    
    # 初始化配置和数据库连接
    settings = load_settings(Path("configs"))
    initialize_pool(settings)
    
    try:
        # 测试参数：使用设备6在17:00-20:00的数据（有大量流量=0的数据）
        TZ_UTC = pytz.UTC
        start_time = datetime(2025, 10, 22, 17, 0, 0, tzinfo=TZ_UTC)
        end_time = datetime(2025, 10, 22, 20, 0, 0, tzinfo=TZ_UTC)
        device_id = 6
        
        print("=" * 100)
        print("🧪 测试 DataFilter 修改后的效果（带数据清理）")
        print("=" * 100)
        print(f"测试时间范围: {start_time} ~ {end_time}")
        print(f"测试设备: 设备{device_id}")
        print("=" * 100)
        
        # 步骤1：清理旧数据
        print(f"\n{'='*100}")
        print("📋 步骤1: 清理旧数据")
        print(f"{'='*100}")
        
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM fact_measurements
                    WHERE device_id = %s
                      AND ts_bucket BETWEEN %s AND %s
                      AND metric_id IN (
                          SELECT id FROM dim_metric_config 
                          WHERE metric_key IN ('pump_inlet_pressure', 'pump_head', 'pump_outlet_pressure')
                      )
                """, (device_id, start_time, end_time))
                deleted_count = cursor.rowcount
                conn.commit()
        
        print(f"✅ 已删除 {deleted_count} 条旧数据")
        
        # 步骤2：重新计算 pump_inlet_pressure
        print(f"\n{'='*100}")
        print("📋 步骤2: 重新计算 pump_inlet_pressure")
        print(f"{'='*100}")
        
        task1 = Task(
            task_id="test_pump_inlet_pressure_device6",
            station_id=1,
            device_id=device_id,
            metric_key="pump_inlet_pressure",
            start_time=start_time,
            end_time=end_time
        )
        
        result1 = calculate_pump_inlet_pressure(task1)
        print(f"✅ 计算成功: {result1.success}")
        
        # 步骤3：重新计算 pump_head
        print(f"\n{'='*100}")
        print("📋 步骤3: 重新计算 pump_head")
        print(f"{'='*100}")
        
        task2 = Task(
            task_id="test_pump_head_device6",
            station_id=1,
            device_id=device_id,
            metric_key="pump_head",
            start_time=start_time,
            end_time=end_time
        )
        
        result2 = calculate_pump_head(task2)
        print(f"✅ 计算成功: {result2.success}")
        
        # 步骤4：查询验证结果
        print(f"\n{'='*100}")
        print("📋 步骤4: 验证结果")
        print(f"{'='*100}")
        
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        mc.metric_key,
                        COUNT(*) as record_count
                    FROM fact_measurements fm
                    JOIN dim_metric_config mc ON mc.id = fm.metric_id
                    WHERE fm.device_id = %s
                      AND fm.ts_bucket BETWEEN %s AND %s
                      AND mc.metric_key IN ('pump_inlet_pressure', 'pump_head', 'pump_outlet_pressure')
                    GROUP BY mc.metric_key
                    ORDER BY mc.metric_key
                """, (device_id, start_time, end_time))
                
                results = cursor.fetchall()
                
                print("\n📊 写入数据统计:")
                for row in results:
                    print(f"  - {row[0]}: {row[1]}条")
        
        print(f"\n{'='*100}")
        print("🎯 测试完成")
        print(f"{'='*100}")
        
        print("\n📝 预期结果:")
        print("  - pump_inlet_pressure: 应该只有流量>0的数据（约900条，而不是3600条）")
        print("  - pump_head: 应该只有流量>0的数据")
        print("  - pump_outlet_pressure: 与pump_head数量相同")
        
    finally:
        # 清理资源
        close_pool()


if __name__ == "__main__":
    test_datafilter_fix_with_cleanup()

