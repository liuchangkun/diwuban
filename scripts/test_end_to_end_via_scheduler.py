"""
通过调度器运行的端到端集成测试

这是真正的端到端测试：
1. 使用 Scheduler.schedule_all_metrics() 调度所有指标
2. 按照 METRIC_ORDER 顺序执行（pump_flow_rate → pump_inlet_pressure → pump_head）
3. 指标间串行，设备间并行
4. 验证整个流水线的正确性
"""

import sys
from pathlib import Path
from datetime import datetime
import pytz
import json

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.core.logging.setup import init_logging
from app.adapters.db import init_database, cleanup_database
from app.services.calculation.shared.scheduler import Scheduler


def test_end_to_end_via_scheduler():
    """通过调度器运行端到端集成测试"""

    # 初始化配置、日志和数据库连接
    settings = load_settings(Path("configs"))
    init_logging(Path("configs"), settings.system.timezone.default)
    init_database(settings)
    
    try:
        # 测试配置
        TZ_UTC = pytz.UTC
        start_time = datetime(2025, 10, 22, 8, 0, 0, tzinfo=TZ_UTC)
        end_time = datetime(2025, 10, 23, 7, 20, 0, tzinfo=TZ_UTC)
        device_ids = [1, 2, 3, 4, 5, 6]
        metrics = ['pump_flow_rate', 'pump_inlet_pressure', 'pump_head', 'pump_efficiency']
        
        print("=" * 100)
        print("🧪 通过调度器运行端到端集成测试")
        print("=" * 100)
        print(f"测试时间范围: {start_time} ~ {end_time} (23.3小时)")
        print(f"测试设备: {device_ids}")
        print(f"测试指标: {metrics}")
        print(f"执行策略: 指标间串行，设备间并行")
        print("=" * 100)
        
        # 清除参数缓存（重要！确保加载最新的参数配置）
        from app.services.calculation.shared.parameter_manager import ParameterManager
        param_manager = ParameterManager()
        param_manager.cache.clear()
        print(f"✅ 已清除参数缓存")

        # 清除测试时段的计算指标数据
        print(f"\n🗑️  清除测试时段的计算指标数据...")
        from app.adapters.db import get_connection
        with get_connection() as conn:
            cursor = conn.cursor()

            # 获取要删除的指标ID
            cursor.execute("""
                SELECT id FROM dim_metric_config
                WHERE metric_key IN ('pump_flow_rate', 'pump_inlet_pressure', 'pump_head', 'pump_outlet_pressure', 'pump_efficiency')
            """)
            metric_ids = [row[0] for row in cursor.fetchall()]

            # 删除数据
            delete_sql = """
                DELETE FROM fact_measurements
                WHERE metric_id = ANY(%s)
                    AND ts_bucket >= %s
                    AND ts_bucket < %s
            """
            cursor.execute(delete_sql, (metric_ids, start_time, end_time))
            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()

            print(f"✅ 已删除 {deleted_count:,} 条旧数据")

        # 创建调度器实例
        scheduler = Scheduler(max_workers=10, enable_adaptive_chunk=True)

        # 通过调度器执行所有指标计算
        print(f"\n{'='*100}")
        print("📊 开始调度执行")
        print(f"{'='*100}")
        
        results = scheduler.schedule_all_metrics(
            device_ids=device_ids,
            start_time=start_time,
            end_time=end_time,
            time_chunk_hours=None,  # 使用自适应分片
            metrics=metrics
        )
        
        # 打印结果摘要
        print(f"\n{'='*100}")
        print("📊 执行结果摘要")
        print(f"{'='*100}")
        
        total_success = 0
        total_failure = 0
        total_points = 0
        total_duration = 0.0
        
        for metric_key, metric_result in results.items():
            success_count = metric_result.get('success_count', 0)
            failure_count = metric_result.get('failure_count', 0)
            points = metric_result.get('total_points', 0)
            duration = metric_result.get('duration_seconds', 0.0)
            
            total_success += success_count
            total_failure += failure_count
            total_points += points
            total_duration += duration
            
            print(f"\n指标: {metric_key}")
            print(f"  - 成功任务: {success_count}/{success_count + failure_count}")
            print(f"  - 写入记录: {points:,}条")
            print(f"  - 执行时间: {duration:.2f}秒")
            
            if failure_count > 0:
                print(f"  ⚠️ 失败任务: {failure_count}")
                # 打印失败任务的详细信息
                for task_result in metric_result.get('results', []):
                    if not task_result.success:
                        print(f"    - 设备{task_result.device_id}: {task_result.error_message}")
        
        print(f"\n{'='*100}")
        print("📊 总体统计")
        print(f"{'='*100}")
        print(f"总任务数: {total_success + total_failure}")
        print(f"成功任务: {total_success}")
        print(f"失败任务: {total_failure}")
        print(f"成功率: {total_success / (total_success + total_failure) * 100:.1f}%")
        print(f"总记录数: {total_points:,}条")
        print(f"总执行时间: {total_duration:.2f}秒")
        print(f"平均吞吐量: {total_points / total_duration:.0f}条/秒" if total_duration > 0 else "N/A")
        
        # 保存详细结果到JSON文件
        output_dir = Path("test_reports")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"scheduler_test_{timestamp}.json"
        
        # 转换结果为可序列化的格式
        serializable_results = {}
        for metric_key, metric_result in results.items():
            serializable_results[metric_key] = {
                'success_count': metric_result.get('success_count', 0),
                'failure_count': metric_result.get('failure_count', 0),
                'total_points': metric_result.get('total_points', 0),
                'duration_seconds': metric_result.get('duration_seconds', 0.0),
                'tasks': [
                    {
                        'device_id': r.device_id,
                        'success': r.success,
                        'error_message': r.error_message,
                        'points_calculated': getattr(r, 'points_calculated', 0),
                    }
                    for r in metric_result.get('results', [])
                ]
            }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n详细结果已保存到: {output_file}")
        
        print(f"\n{'='*100}")
        print("🎯 测试完成")
        print(f"{'='*100}")
        
    finally:
        # 清理资源
        cleanup_database()


if __name__ == "__main__":
    test_end_to_end_via_scheduler()

