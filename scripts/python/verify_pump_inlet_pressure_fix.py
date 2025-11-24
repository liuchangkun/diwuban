#!/usr/bin/env python3
"""
验证 pump_inlet_pressure 修复效果
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


def query_before_fix_stats():
    """查询修复前的数据统计（从之前的分析结果）"""
    print("\n" + "=" * 100)
    print("📊 修复前数据统计（参考值）")
    print("=" * 100)
    
    stats = {
        'total_records': 164888,
        'invalid_count': 6921,
        'invalid_ratio': 4.2,
        'pool_coverage': 0.0,
        'device_stats': {
            1: {'total': 25626, 'invalid': 350, 'ratio': 1.4},
            2: {'total': 42240, 'invalid': 2091, 'ratio': 5.0},
            3: {'total': 5547, 'invalid': 0, 'ratio': 0.0},
            4: {'total': 47659, 'invalid': 837, 'ratio': 1.8},
            5: {'total': 133, 'invalid': 0, 'ratio': 0.0},
            6: {'total': 43683, 'invalid': 3643, 'ratio': 8.3},
        }
    }
    
    print(f"\n总记录数: {stats['total_records']:,}条")
    print(f"无效值数量: {stats['invalid_count']:,}个")
    print(f"无效值比例: {stats['invalid_ratio']}%")
    print(f"pool_liquid_level 覆盖率: {stats['pool_coverage']}%")
    
    print(f"\n{'设备ID':<8} {'总记录数':<12} {'无效值':<10} {'无效率':<10}")
    print("-" * 50)
    for device_id, stat in stats['device_stats'].items():
        print(f"{device_id:<8} {stat['total']:<12,} {stat['invalid']:<10} {stat['ratio']:<10}%")
    
    return stats


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

    # 处理 success_rate 可能是字符串的情况
    success_rate = result.get('success_rate', 0)
    if isinstance(success_rate, str):
        success_rate = float(success_rate.rstrip('%')) / 100 if '%' in success_rate else float(success_rate)
    print(f"   - 成功率: {success_rate * 100:.1f}%")

    avg_duration = result.get('avg_duration_per_task_seconds', 0)
    if isinstance(avg_duration, str):
        avg_duration = float(avg_duration)
    print(f"   - 平均耗时: {avg_duration:.2f}秒/任务")
    
    return result


def query_after_fix_stats():
    """查询修复后的数据统计"""
    print("\n" + "=" * 100)
    print("📊 修复后数据统计")
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
            
            device_stats = {}
            for row in rows:
                device_id, total, invalid, min_val, max_val, avg_val = row
                ratio = (invalid / total * 100) if total > 0 else 0
                device_stats[device_id] = {
                    'total': total,
                    'invalid': invalid,
                    'ratio': ratio
                }
                status = "✅" if invalid == 0 else "⚠️" if ratio < 1 else "❌"
                print(f"{status} {device_id:<6} {total:<12,} {invalid:<10} {ratio:<10.2f}% {min_val:<12.6f} {max_val:<12.6f} {avg_val:<12.6f}")
            
            return {
                'total_records': total_count,
                'invalid_count': invalid_count,
                'invalid_ratio': invalid_ratio,
                'device_stats': device_stats
            }


def generate_comparison_report(before_stats, after_stats):
    """生成对比报告"""
    print("\n" + "=" * 100)
    print("📈 修复效果对比报告")
    print("=" * 100)
    
    # 总体对比
    print("\n1️⃣ 总体效果：")
    print(f"   修复前: {before_stats['invalid_count']:,}个无效值 ({before_stats['invalid_ratio']}%)")
    print(f"   修复后: {after_stats['invalid_count']:,}个无效值 ({after_stats['invalid_ratio']:.2f}%)")
    
    improvement = before_stats['invalid_count'] - after_stats['invalid_count']
    improvement_ratio = (improvement / before_stats['invalid_count'] * 100) if before_stats['invalid_count'] > 0 else 0
    
    if improvement > 0:
        print(f"   ✅ 改善: 减少 {improvement:,}个无效值 ({improvement_ratio:.1f}%)")
    elif improvement < 0:
        print(f"   ❌ 恶化: 增加 {abs(improvement):,}个无效值")
    else:
        print(f"   ⚠️  无变化")
    
    # 按设备对比
    print("\n2️⃣ 按设备对比：")
    print(f"{'设备ID':<8} {'修复前无效值':<15} {'修复后无效值':<15} {'改善情况':<20}")
    print("-" * 70)
    
    for device_id in sorted(before_stats['device_stats'].keys()):
        before = before_stats['device_stats'][device_id]
        after = after_stats['device_stats'].get(device_id, {'invalid': 0})
        
        before_invalid = before['invalid']
        after_invalid = after['invalid']
        improvement = before_invalid - after_invalid
        
        if improvement > 0:
            status = f"✅ 减少 {improvement}"
        elif improvement < 0:
            status = f"❌ 增加 {abs(improvement)}"
        else:
            status = "⚠️  无变化"
        
        print(f"{device_id:<8} {before_invalid:<15} {after_invalid:<15} {status:<20}")
    
    # 结论
    print("\n3️⃣ 结论：")
    if after_stats['invalid_ratio'] < 0.5:
        print("   ✅ 修复成功！无效值比例已降至 0.5% 以下")
    elif after_stats['invalid_ratio'] < 2.0:
        print("   ⚠️  部分改善，但仍有少量无效值")
    else:
        print("   ❌ 修复效果不佳，需要进一步排查")


if __name__ == "__main__":
    try:
        # 初始化
        config_dir = project_root / "configs"
        settings = load_settings(config_dir)
        init_database(settings)
        
        # 1. 显示修复前统计
        before_stats = query_before_fix_stats()
        
        # 2. 运行计算任务
        calc_result = run_calculation()
        
        # 3. 查询修复后统计
        after_stats = query_after_fix_stats()
        
        # 4. 生成对比报告
        generate_comparison_report(before_stats, after_stats)
        
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

