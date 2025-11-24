"""
测试 pump_efficiency 计算

测试范围：2025-10-22 16:00 ~ 2025-10-23 15:00
测试设备：1-6（泵设备）
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from datetime import datetime
from pathlib import Path
import pytz
import logging
import pandas as pd
from app.services.calculation.metrics.pump_efficiency import calculate_pump_efficiency
from app.services.calculation.shared.scheduler import Task
from app.adapters.db.pool import get_connection
from app.core.config.loader import load_settings
from app.adapters.db import init_database

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 初始化数据库
settings = load_settings(Path('configs'))
init_database(settings)


def test_pump_efficiency():
    """测试 pump_efficiency 计算"""
    
    # 测试参数
    station_id = 1
    device_ids = [1, 2, 3, 4, 5, 6]  # 6台泵
    start_time = datetime(2025, 10, 22, 16, 0, 0, tzinfo=pytz.UTC)
    end_time = datetime(2025, 10, 23, 15, 0, 0, tzinfo=pytz.UTC)
    
    logger.info("=" * 80)
    logger.info("开始测试 pump_efficiency 计算")
    logger.info(f"测试范围: {start_time} ~ {end_time}")
    logger.info(f"测试设备: {device_ids}")
    logger.info("=" * 80)
    
    results = []
    
    for device_id in device_ids:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"测试设备 {device_id}")
        logger.info(f"{'=' * 80}")
        
        # 创建任务
        task = Task(
            task_id=f"test_pump_efficiency_device_{device_id}",
            station_id=station_id,
            device_id=device_id,
            metric_key='pump_efficiency',
            start_time=start_time,
            end_time=end_time
        )
        
        # 执行计算
        result = calculate_pump_efficiency(task)
        
        results.append({
            'device_id': device_id,
            'success': result.success,
            'results_count': result.results_count,
            'error_message': result.error_message
        })
        
        logger.info(f"设备 {device_id} 计算完成:")
        logger.info(f"  - 成功: {result.success}")
        logger.info(f"  - 写入记录数: {result.results_count}")
        if result.error_message:
            logger.error(f"  - 错误信息: {result.error_message}")
    
    # 汇总结果
    logger.info("\n" + "=" * 80)
    logger.info("测试汇总")
    logger.info("=" * 80)
    
    df_results = pd.DataFrame(results)
    logger.info(f"\n{df_results.to_string(index=False)}")
    
    total_success = df_results['success'].sum()
    total_records = df_results['results_count'].sum()
    
    logger.info(f"\n总计:")
    logger.info(f"  - 成功设备数: {total_success}/{len(device_ids)}")
    logger.info(f"  - 总写入记录数: {total_records}")
    
    # 数据质量分析
    logger.info("\n" + "=" * 80)
    logger.info("数据质量分析")
    logger.info("=" * 80)
    
    analyze_data_quality(device_ids, start_time, end_time)
    
    return df_results


def analyze_data_quality(device_ids, start_time, end_time):
    """分析数据质量"""
    
    sql = """
    SELECT
        fm.device_id,
        COUNT(*) as total_count,
        MIN(fm.value) as min_value,
        MAX(fm.value) as max_value,
        AVG(fm.value) as avg_value,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fm.value) as median_value,
        STDDEV(fm.value) as stddev_value,
        COUNT(CASE WHEN fm.value < 0.3 THEN 1 END) as below_min_count,
        COUNT(CASE WHEN fm.value > 0.95 THEN 1 END) as above_max_count
    FROM fact_measurements fm
    JOIN dim_metric_config mc ON mc.id = fm.metric_id
    WHERE mc.metric_key = 'pump_efficiency'
      AND fm.device_id = ANY(%(device_ids)s)
      AND fm.ts_raw >= %(start_time)s
      AND fm.ts_raw < %(end_time)s
    GROUP BY fm.device_id
    ORDER BY fm.device_id
    """
    
    with get_connection() as conn:
        df = pd.read_sql(
            sql,
            conn,
            params={
                'device_ids': device_ids,
                'start_time': start_time,
                'end_time': end_time
            }
        )
    
    if df.empty:
        logger.warning("没有找到 pump_efficiency 数据")
        return
    
    logger.info(f"\n{df.to_string(index=False)}")
    
    # 总体统计
    logger.info(f"\n总体统计:")
    logger.info(f"  - 总记录数: {df['total_count'].sum()}")
    logger.info(f"  - 平均效率: {df['avg_value'].mean():.4f}")
    logger.info(f"  - 效率范围: {df['min_value'].min():.4f} ~ {df['max_value'].max():.4f}")
    logger.info(f"  - 低于阈值(0.3)记录数: {df['below_min_count'].sum()}")
    logger.info(f"  - 高于阈值(0.95)记录数: {df['above_max_count'].sum()}")


if __name__ == '__main__':
    test_pump_efficiency()

