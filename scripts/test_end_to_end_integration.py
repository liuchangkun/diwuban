"""
端到端集成测试 - 缺失指标计算系统
测试所有已实现的指标：pump_flow_rate, pump_inlet_pressure, pump_head, pump_outlet_pressure
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz
import time
from typing import Dict, List
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db.pool import initialize_pool, close_pool, get_connection
from app.services.calculation.shared.scheduler import Scheduler, Task

# 测试配置
TEST_CONFIG = {
    'metrics': ['pump_flow_rate', 'pump_inlet_pressure', 'pump_head'],
    'devices': [1, 2, 3, 4, 5, 6],
    'station_id': 1,
    # 使用完整的数据范围（从数据库查询得到）
    'start_time': datetime(2025, 10, 22, 8, 0, 0, tzinfo=pytz.UTC),
    'end_time': datetime(2025, 10, 23, 7, 20, 0, tzinfo=pytz.UTC),  # 约23.3小时
}


class IntegrationTestRunner:
    """集成测试运行器"""

    def __init__(self):
        self.results = {
            'summary': {},
            'details': {},
            'errors': [],
            'performance': {}
        }
        # 导入计算函数
        self.calculator_funcs = self._load_calculator_funcs()

    def _load_calculator_funcs(self):
        """加载所有计算函数"""
        from app.services.calculation.metrics.pump_flow_rate import calculate_pump_flow_rate
        from app.services.calculation.metrics.pump_inlet_pressure import calculate_pump_inlet_pressure
        from app.services.calculation.metrics.pump_head import calculate_pump_head

        return {
            'pump_flow_rate': calculate_pump_flow_rate,
            'pump_inlet_pressure': calculate_pump_inlet_pressure,
            'pump_head': calculate_pump_head
        }
        
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 100)
        print("🧪 缺失指标计算系统 - 端到端集成测试")
        print("=" * 100)
        print(f"\n测试配置:")
        print(f"  - 测试指标: {', '.join(TEST_CONFIG['metrics'])}")
        print(f"  - 测试设备: {TEST_CONFIG['devices']}")
        print(f"  - 时间范围: {TEST_CONFIG['start_time']} ~ {TEST_CONFIG['end_time']}")
        print(f"  - 时长: {(TEST_CONFIG['end_time'] - TEST_CONFIG['start_time']).total_seconds() / 60:.1f} 分钟")
        print("\n" + "=" * 100)
        
        # 1. 清理旧数据（可选）
        self._cleanup_old_test_data()
        
        # 2. 执行计算任务
        start_time = time.time()
        self._run_calculations()
        execution_time = time.time() - start_time
        
        # 3. 验证结果
        self._verify_results()
        
        # 4. 生成报告
        self._generate_report(execution_time)
        
    def _cleanup_old_test_data(self):
        """清理旧的测试数据"""
        print("\n📋 步骤1: 清理旧测试数据...")
        
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # 删除测试时间段内的计算数据
            cursor.execute("""
                DELETE FROM fact_measurements
                WHERE ts_bucket BETWEEN %s AND %s
                  AND device_id IN (1, 2, 3, 4, 5, 6)
                  AND metric_id IN (
                      SELECT id FROM dim_metric_config 
                      WHERE metric_key IN ('pump_flow_rate', 'pump_inlet_pressure', 'pump_head', 'pump_outlet_pressure')
                  )
                  AND source_hint = 'calculated'
            """, (TEST_CONFIG['start_time'], TEST_CONFIG['end_time']))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
        print(f"  ✅ 已删除 {deleted_count} 条旧测试数据")
        
    def _run_calculations(self):
        """执行计算任务"""
        print("\n📋 步骤2: 执行计算任务...")
        
        total_tasks = len(TEST_CONFIG['metrics']) * len(TEST_CONFIG['devices'])
        completed_tasks = 0
        
        for metric_key in TEST_CONFIG['metrics']:
            print(f"\n  📊 计算指标: {metric_key}")
            self.results['details'][metric_key] = {}
            
            for device_id in TEST_CONFIG['devices']:
                # 创建任务
                task = Task(
                    task_id=f"test_{metric_key}_device_{device_id}",
                    station_id=TEST_CONFIG['station_id'],
                    device_id=device_id,
                    metric_key=metric_key,
                    start_time=TEST_CONFIG['start_time'],
                    end_time=TEST_CONFIG['end_time']
                )

                # 执行任务
                try:
                    task_start = time.time()
                    calculator_func = self.calculator_funcs.get(metric_key)
                    if not calculator_func:
                        raise ValueError(f"未找到指标 {metric_key} 的计算函数")

                    result = calculator_func(task)
                    task_duration = time.time() - task_start
                    
                    # 记录结果
                    self.results['details'][metric_key][device_id] = {
                        'success': result.success,
                        'results_count': result.results_count,
                        'duration': task_duration,
                        'error': result.error_message
                    }
                    
                    status = "✅" if result.success else "❌"
                    print(f"    {status} 设备{device_id}: {result.results_count}条记录 ({task_duration:.2f}s)")
                    
                    if not result.success:
                        self.results['errors'].append({
                            'metric': metric_key,
                            'device': device_id,
                            'error': result.error_message
                        })
                        
                except Exception as e:
                    print(f"    ❌ 设备{device_id}: 执行失败 - {str(e)}")
                    self.results['errors'].append({
                        'metric': metric_key,
                        'device': device_id,
                        'error': str(e)
                    })
                    self.results['details'][metric_key][device_id] = {
                        'success': False,
                        'results_count': 0,
                        'duration': 0,
                        'error': str(e)
                    }
                
                completed_tasks += 1
                
        print(f"\n  ✅ 完成 {completed_tasks}/{total_tasks} 个任务")

    def _verify_results(self):
        """验证计算结果"""
        print("\n📋 步骤3: 验证计算结果...")

        with get_connection() as conn:
            cursor = conn.cursor()

            # 查询每个指标的统计信息（使用 inserted_at 而不是 ts_bucket，因为刚写入）
            cursor.execute("""
                SELECT
                    mc.metric_key,
                    fm.device_id,
                    COUNT(*) as record_count,
                    ROUND(MIN(fm.value)::numeric, 4) as min_value,
                    ROUND(MAX(fm.value)::numeric, 4) as max_value,
                    ROUND(AVG(fm.value)::numeric, 4) as avg_value,
                    ROUND(STDDEV(fm.value)::numeric, 4) as std_value
                FROM fact_measurements fm
                JOIN dim_metric_config mc ON mc.id = fm.metric_id
                WHERE fm.inserted_at > NOW() - INTERVAL '2 minutes'
                  AND fm.device_id IN (1, 2, 3, 4, 5, 6)
                  AND mc.metric_key IN ('pump_flow_rate', 'pump_inlet_pressure', 'pump_head', 'pump_outlet_pressure')
                GROUP BY mc.metric_key, fm.device_id
                ORDER BY mc.metric_key, fm.device_id
            """)

            db_results = cursor.fetchall()

        # 组织验证结果
        verification = {}
        for row in db_results:
            metric_key = row[0]
            device_id = row[1]

            if metric_key not in verification:
                verification[metric_key] = {}

            verification[metric_key][device_id] = {
                'record_count': row[2],
                'min_value': float(row[3]) if row[3] else None,
                'max_value': float(row[4]) if row[4] else None,
                'avg_value': float(row[5]) if row[5] else None,
                'std_value': float(row[6]) if row[6] else None
            }

        self.results['verification'] = verification

        # 打印验证结果
        for metric_key in ['pump_flow_rate', 'pump_inlet_pressure', 'pump_head', 'pump_outlet_pressure']:
            if metric_key in verification:
                print(f"\n  📊 {metric_key}:")
                for device_id in sorted(verification[metric_key].keys()):
                    stats = verification[metric_key][device_id]
                    print(f"    设备{device_id}: {stats['record_count']}条 | "
                          f"范围: [{stats['min_value']}, {stats['max_value']}] | "
                          f"均值: {stats['avg_value']} | 标准差: {stats['std_value']}")
            else:
                print(f"\n  ⚠️ {metric_key}: 无数据")

    def _generate_report(self, execution_time: float):
        """生成测试报告"""
        print("\n" + "=" * 100)
        print("📊 测试报告")
        print("=" * 100)

        # 统计总体情况
        total_tasks = 0
        successful_tasks = 0
        total_records = 0

        for metric_key, devices in self.results['details'].items():
            for device_id, result in devices.items():
                total_tasks += 1
                if result['success']:
                    successful_tasks += 1
                total_records += result['results_count']

        success_rate = (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0

        print(f"\n✅ 总体统计:")
        print(f"  - 总任务数: {total_tasks}")
        print(f"  - 成功任务: {successful_tasks}")
        print(f"  - 失败任务: {total_tasks - successful_tasks}")
        print(f"  - 成功率: {success_rate:.1f}%")
        print(f"  - 总记录数: {total_records}")
        print(f"  - 执行时间: {execution_time:.2f}秒")

        # 按指标统计
        print(f"\n📊 按指标统计:")
        for metric_key in TEST_CONFIG['metrics']:
            if metric_key in self.results['details']:
                devices = self.results['details'][metric_key]
                metric_success = sum(1 for d in devices.values() if d['success'])
                metric_records = sum(d['results_count'] for d in devices.values())
                metric_duration = sum(d['duration'] for d in devices.values())

                print(f"  {metric_key}:")
                print(f"    - 成功设备: {metric_success}/{len(devices)}")
                print(f"    - 总记录数: {metric_records}")
                print(f"    - 总耗时: {metric_duration:.2f}秒")

        # pump_outlet_pressure 统计（作为 pump_head 的副产品）
        if 'pump_outlet_pressure' in self.results.get('verification', {}):
            outlet_stats = self.results['verification']['pump_outlet_pressure']
            outlet_records = sum(d['record_count'] for d in outlet_stats.values())
            print(f"  pump_outlet_pressure (副产品):")
            print(f"    - 成功设备: {len(outlet_stats)}/{len(TEST_CONFIG['devices'])}")
            print(f"    - 总记录数: {outlet_records}")

        # 错误报告
        if self.results['errors']:
            print(f"\n❌ 错误列表 ({len(self.results['errors'])}个):")
            for i, error in enumerate(self.results['errors'][:10], 1):  # 只显示前10个
                print(f"  {i}. {error['metric']} - 设备{error['device']}: {error['error']}")
            if len(self.results['errors']) > 10:
                print(f"  ... 还有 {len(self.results['errors']) - 10} 个错误")

        # 数据合理性检查
        print(f"\n🔍 数据合理性检查:")
        self._check_data_reasonableness()

        # 保存详细报告到文件
        report_file = project_root / 'test_reports' / f'integration_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        report_file.parent.mkdir(exist_ok=True)

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n📄 详细报告已保存到: {report_file}")
        print("\n" + "=" * 100)

    def _check_data_reasonableness(self):
        """检查数据合理性"""
        verification = self.results.get('verification', {})

        # 定义合理范围
        reasonable_ranges = {
            'pump_flow_rate': (0, 1000),  # m³/h
            'pump_inlet_pressure': (0, 2),  # MPa
            'pump_head': (0, 200),  # m
            'pump_outlet_pressure': (0, 2)  # MPa
        }

        issues = []

        for metric_key, range_limits in reasonable_ranges.items():
            if metric_key in verification:
                for device_id, stats in verification[metric_key].items():
                    min_val = stats['min_value']
                    max_val = stats['max_value']

                    if min_val is not None and max_val is not None:
                        if min_val < range_limits[0] or max_val > range_limits[1]:
                            issues.append(
                                f"  ⚠️ {metric_key} 设备{device_id}: "
                                f"值超出合理范围 [{min_val}, {max_val}] vs [{range_limits[0]}, {range_limits[1]}]"
                            )

        if issues:
            for issue in issues:
                print(issue)
        else:
            print("  ✅ 所有数据都在合理范围内")


def main():
    """主函数"""
    # 初始化配置和数据库连接
    settings = load_settings(Path("configs"))
    initialize_pool(settings)

    try:
        # 运行测试
        runner = IntegrationTestRunner()
        runner.run_all_tests()

    finally:
        # 清理资源
        close_pool()


if __name__ == '__main__':
    main()


