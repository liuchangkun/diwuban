#!/usr/bin/env python3
"""
最终验证修复效果（新进程，避免缓存）
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
    """删除旧数据"""
    print("\n🗑️  删除旧数据...")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM dim_metric_config WHERE metric_key = 'pump_inlet_pressure'")
            metric_id = cur.fetchone()[0]
            
            cur.execute("""
                DELETE FROM fact_measurements
                WHERE metric_id = %s
                  AND device_id IN (1,2,3,4,5,6)
                  AND ts_raw >= '2025-10-22 16:00:00+08:00'
                  AND ts_raw < '2025-10-23 15:00:00+08:00'
            """, (metric_id,))
            
            conn.commit()
            print(f"✅ 旧数据已删除")


def run_calculation():
    """运行计算"""
    print("\n🔧 运行计算...")
    
    shared_services = SharedServices()
    
    tz = pytz.timezone('Asia/Shanghai')
    start_time = datetime(2025, 10, 22, 16, 0, 0, tzinfo=tz)
    end_time = datetime(2025, 10, 23, 15, 0, 0, tzinfo=tz)
    
    result = shared_services.scheduler.schedule_single_metric(
        metric_key='pump_inlet_pressure',
        device_ids=[1, 2, 3, 4, 5, 6],
        start_time=start_time,
        end_time=end_time,
        time_chunk_hours=24
    )
    
    print(f"✅ 计算完成: {result['success_count']}/{result['total_tasks']} 任务成功")
    return result


def query_stats():
    """查询统计"""
    print("\n📊 数据质量统计:")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM dim_metric_config WHERE metric_key = 'pump_inlet_pressure'")
            metric_id = cur.fetchone()[0]
            
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN value IS NULL OR value = 'NaN'::numeric OR value < 0 THEN 1 END) as invalid
                FROM fact_measurements
                WHERE metric_id = %s
                  AND device_id IN (1,2,3,4,5,6)
                  AND ts_raw >= '2025-10-22 16:00:00+08:00'
                  AND ts_raw < '2025-10-23 15:00:00+08:00'
            """, (metric_id,))
            
            total, invalid = cur.fetchone()
            ratio = (invalid / total * 100) if total > 0 else 0
            
            print(f"  - 总记录数: {total:,}条")
            print(f"  - 无效值: {invalid:,}个 ({ratio:.2f}%)")
            
            cur.execute("""
                SELECT 
                    device_id,
                    COUNT(*) as total,
                    COUNT(CASE WHEN value IS NULL OR value = 'NaN'::numeric OR value < 0 THEN 1 END) as invalid
                FROM fact_measurements
                WHERE metric_id = %s
                  AND device_id IN (1,2,3,4,5,6)
                  AND ts_raw >= '2025-10-22 16:00:00+08:00'
                  AND ts_raw < '2025-10-23 15:00:00+08:00'
                GROUP BY device_id
                ORDER BY device_id
            """, (metric_id,))
            
            print(f"\n  按设备统计:")
            for device_id, total, invalid in cur.fetchall():
                ratio = (invalid / total * 100) if total > 0 else 0
                status = "✅" if invalid == 0 else "⚠️" if ratio < 1 else "❌"
                print(f"    {status} 设备{device_id}: {total:,}条, 无效{invalid}个 ({ratio:.2f}%)")
            
            return {'total': total, 'invalid': invalid, 'ratio': ratio}


def main():
    print("=" * 100)
    print("🎯 pump_inlet_pressure 修复最终验证")
    print("=" * 100)
    
    # 初始化
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    
    # 1. 删除旧数据
    delete_old_data()
    
    # 2. 运行计算
    calc_result = run_calculation()
    
    # 3. 查询统计
    stats = query_stats()
    
    # 4. 结论
    print("\n" + "=" * 100)
    print("📈 修复效果:")
    print("=" * 100)
    print(f"\n修复前: 6,921个无效值 (4.2%)")
    print(f"修复后: {stats['invalid']:,}个无效值 ({stats['ratio']:.2f}%)")
    
    if stats['ratio'] < 0.5:
        print(f"\n✅ 修复成功！无效值比例从 4.2% 降至 {stats['ratio']:.2f}%")
        return 0
    elif stats['ratio'] < 2.0:
        print(f"\n⚠️  部分改善，无效值比例从 4.2% 降至 {stats['ratio']:.2f}%")
        return 1
    else:
        print(f"\n❌ 修复失败，无效值比例仍为 {stats['ratio']:.2f}%")
        return 2


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(3)

