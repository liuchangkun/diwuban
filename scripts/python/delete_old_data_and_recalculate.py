#!/usr/bin/env python3
"""
删除旧数据并重新计算
"""
import sys
from pathlib import Path
from datetime import datetime
import pytz

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings
from app.services.calculation.shared.shared_services import SharedServices


def delete_old_data():
    """删除旧的 pump_inlet_pressure 数据"""
    print("\n" + "=" * 100)
    print("🗑️  删除旧数据")
    print("=" * 100)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 获取 metric_id
            cur.execute("SELECT id FROM dim_metric_config WHERE metric_key = 'pump_inlet_pressure'")
            metric_id = cur.fetchone()[0]
            
            # 查询要删除的数据量
            cur.execute("""
                SELECT COUNT(*) 
                FROM fact_measurements
                WHERE metric_id = %s
                  AND device_id IN (1,2,3,4,5,6)
                  AND ts_raw >= '2025-10-22 16:00:00+08:00'
                  AND ts_raw < '2025-10-23 15:00:00+08:00'
            """, (metric_id,))
            
            count = cur.fetchone()[0]
            print(f"\n将删除 {count:,} 条旧数据")
            
            # 删除数据
            cur.execute("""
                DELETE FROM fact_measurements
                WHERE metric_id = %s
                  AND device_id IN (1,2,3,4,5,6)
                  AND ts_raw >= '2025-10-22 16:00:00+08:00'
                  AND ts_raw < '2025-10-23 15:00:00+08:00'
            """, (metric_id,))
            
            conn.commit()
            
            print(f"✅ 已删除 {count:,} 条旧数据")


def run_calculation():
    """运行 pump_inlet_pressure 计算任务"""
    print("\n" + "=" * 100)
    print("🔧 运行 pump_inlet_pressure 计算任务")
    print("=" * 100)
    
    # 初始化 SharedServices
    shared_services = SharedServices()
    
    # 设置时间范围
    tz = pytz.timezone('Asia/Shanghai')
    start_time = datetime(2025, 10, 22, 16, 0, 0, tzinfo=tz)
    end_time = datetime(2025, 10, 23, 15, 0, 0, tzinfo=tz)
    
    print(f"\n时间范围: {start_time} ~ {end_time}")
    print(f"设备: 1-6")
    print(f"指标: pump_inlet_pressure")
    
    # 执行计算
    print("\n开始计算...")
    result = shared_services.scheduler.schedule_single_metric(
        metric_key='pump_inlet_pressure',
        device_ids=[1, 2, 3, 4, 5, 6],
        start_time=start_time,
        end_time=end_time,
        time_chunk_hours=24
    )
    
    print(f"\n✅ 计算完成")
    print(f"   - 总任务数: {result['total_tasks']}")
    print(f"   - 成功任务: {result['success_count']}")
    print(f"   - 失败任务: {result['failure_count']}")
    print(f"   - 总数据点: {result['total_points']:,}")
    
    return result


def query_new_data_stats():
    """查询新数据统计"""
    print("\n" + "=" * 100)
    print("📊 新数据统计")
    print("=" * 100)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 获取 metric_id
            cur.execute("SELECT id FROM dim_metric_config WHERE metric_key = 'pump_inlet_pressure'")
            metric_id = cur.fetchone()[0]
            
            # 查询总体统计
            cur.execute("""
                SELECT 
                    COUNT(*) as total_count,
                    COUNT(CASE WHEN value IS NULL OR value = 'NaN'::numeric OR value < 0 THEN 1 END) as invalid_count
                FROM fact_measurements
                WHERE metric_id = %s
                  AND device_id IN (1,2,3,4,5,6)
                  AND ts_raw >= '2025-10-22 16:00:00+08:00'
                  AND ts_raw < '2025-10-23 15:00:00+08:00'
            """, (metric_id,))
            
            row = cur.fetchone()
            total_count, invalid_count = row
            invalid_ratio = (invalid_count / total_count * 100) if total_count > 0 else 0
            
            print(f"\n总记录数: {total_count:,}条")
            print(f"无效值数量: {invalid_count:,}个")
            print(f"无效值比例: {invalid_ratio:.2f}%")
            
            # 查询按设备统计
            cur.execute("""
                SELECT 
                    device_id,
                    COUNT(*) as total_count,
                    COUNT(CASE WHEN value IS NULL OR value = 'NaN'::numeric OR value < 0 THEN 1 END) as invalid_count,
                    MIN(value) as min_value,
                    MAX(value) as max_value,
                    AVG(value) as avg_value
                FROM fact_measurements
                WHERE metric_id = %s
                  AND device_id IN (1,2,3,4,5,6)
                  AND ts_raw >= '2025-10-22 16:00:00+08:00'
                  AND ts_raw < '2025-10-23 15:00:00+08:00'
                GROUP BY device_id
                ORDER BY device_id
            """, (metric_id,))
            
            rows = cur.fetchall()
            print(f"\n{'设备ID':<8} {'总记录数':<12} {'无效值':<10} {'无效率':<10} {'最小值':<12} {'最大值':<12} {'平均值':<12}")
            print("-" * 90)
            
            for row in rows:
                device_id, total, invalid, min_val, max_val, avg_val = row
                ratio = (invalid / total * 100) if total > 0 else 0
                status = "✅" if invalid == 0 else "⚠️" if ratio < 1 else "❌"
                print(f"{status} {device_id:<6} {total:<12,} {invalid:<10} {ratio:<10.2f}% {min_val:<12.6f} {max_val:<12.6f} {avg_val:<12.6f}")
            
            # 结论
            print(f"\n结论:")
            if invalid_ratio < 0.5:
                print(f"   ✅ 修复成功！无效值比例已降至 {invalid_ratio:.2f}%")
            elif invalid_ratio < 2.0:
                print(f"   ⚠️  部分改善，无效值比例为 {invalid_ratio:.2f}%")
            else:
                print(f"   ❌ 修复效果不佳，无效值比例仍为 {invalid_ratio:.2f}%")


if __name__ == "__main__":
    try:
        # 初始化
        config_dir = project_root / "configs"
        settings = load_settings(config_dir)
        init_database(settings)
        
        # 1. 删除旧数据
        delete_old_data()
        
        # 2. 运行计算任务
        calc_result = run_calculation()
        
        # 3. 查询新数据统计
        query_new_data_stats()
        
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

