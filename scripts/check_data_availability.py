#!/usr/bin/env python3
"""
数据可用性检查脚本：检查数据库中是否有足够的数据用于验证

用途：
1. 检查 fact_measurements 表的数据量和时间范围
2. 检查质量标注数据的存在性
3. 检查性能日志数据的存在性
4. 推荐合适的测试时间窗口

使用方法：
    python scripts/check_data_availability.py
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, get_connection


def check_data_availability():
    """检查数据可用性"""
    print("\n" + "="*80)
    print("数据可用性检查")
    print("="*80)
    
    # 初始化
    settings = load_settings(Path('configs'))
    init_database(settings)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. 检查 fact_measurements 表
            print("\n1. fact_measurements 表检查")
            print("-"*80)
            
            cur.execute("""
                SELECT 
                    MIN(ts_bucket) as min_ts,
                    MAX(ts_bucket) as max_ts,
                    COUNT(*) as total_rows,
                    COUNT(DISTINCT station_id) as stations,
                    COUNT(DISTINCT device_id) as devices
                FROM public.fact_measurements
                WHERE ts_bucket >= NOW() - INTERVAL '7 days'
            """)
            result = cur.fetchone()
            
            if result[0] is None:
                print("❌ 最近7天无数据！")
                return False
            
            print(f"最早时间: {result[0]}")
            print(f"最晚时间: {result[1]}")
            print(f"总行数: {result[2]:,}")
            print(f"站点数: {result[3]}")
            print(f"设备数: {result[4]}")
            
            # 2. 检查质量标注数据
            print("\n2. 质量标注数据检查")
            print("-"*80)
            
            cur.execute("""
                SELECT 
                    COUNT(*) as annotated_rows,
                    COUNT(DISTINCT quality_status) as quality_codes
                FROM public.fact_measurements
                WHERE ts_bucket >= NOW() - INTERVAL '7 days'
                  AND quality_status IS NOT NULL
                  AND quality_status != 0
            """)
            result = cur.fetchone()
            
            annotated_rows = result[0]
            quality_codes = result[1]
            
            print(f"已标注行数: {annotated_rows:,}")
            print(f"质量码种类: {quality_codes}")
            
            if annotated_rows == 0:
                print("⚠️ 无质量标注数据，需要先运行 mark-window 命令")
            else:
                print("✅ 存在质量标注数据")
            
            # 3. 检查性能日志
            print("\n3. 性能日志检查")
            print("-"*80)
            
            cur.execute("""
                SELECT 
                    COUNT(*) as log_count,
                    MAX(created_at) as last_run,
                    MAX(window_start) as last_window_start,
                    MAX(window_end) as last_window_end
                FROM public.quality_profile_log
                WHERE created_at >= NOW() - INTERVAL '7 days'
            """)
            result = cur.fetchone()
            
            log_count = result[0]
            last_run = result[1]
            last_window_start = result[2]
            last_window_end = result[3]
            
            print(f"性能日志记录数: {log_count:,}")
            print(f"最后执行时间: {last_run}")
            
            if log_count == 0:
                print("⚠️ 无性能日志数据，需要先运行 mark-window 命令")
            else:
                print("✅ 存在性能日志数据")
                print(f"最后窗口: {last_window_start} ~ {last_window_end}")
            
            # 4. 推荐测试窗口
            print("\n4. 推荐测试窗口")
            print("-"*80)
            
            if annotated_rows > 0 and log_count > 0:
                # 使用最后一次执行的窗口
                print(f"✅ 推荐使用最后一次执行的窗口：")
                print(f"   开始时间: {last_window_start}")
                print(f"   结束时间: {last_window_end}")
                print()
                print("验证命令示例：")
                print(f'python scripts/test_performance_validation.py --start "{last_window_start}" --end "{last_window_end}"')
                print(f'python scripts/test_functional_validation.py --start "{last_window_start}" --end "{last_window_end}"')
                print(f'python scripts/test_diagnosis_log_validation.py --start "{last_window_start}" --end "{last_window_end}"')
            else:
                # 推荐一个2小时窗口
                now = datetime.now()
                # 向下取整到小时
                start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=2)
                end = start + timedelta(hours=2)
                
                print(f"⚠️ 建议先运行 mark-window 命令生成测试数据：")
                print(f'python -m app.cli.main mark-window --start "{start}" --end "{end}"')
                print()
                print("然后再运行验证脚本")
            
            print("="*80)
            return True


if __name__ == "__main__":
    try:
        success = check_data_availability()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

