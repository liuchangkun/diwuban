"""
pump_torque 测试脚本

测试 pump_torque 指标的完整计算流程
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
import logging
import pytz

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# UTC 时区
UTC = pytz.UTC


def test_pump_torque_single_device():
    """测试单个设备的 pump_torque 计算"""
    from app.services.calculation.metrics.pump_torque import PumpTorquePipeline
    from app.core.config.loader_new import load_settings
    from app.adapters.db.pool import initialize_pool

    # 初始化数据库连接池
    settings = load_settings(Path("configs"))
    initialize_pool(settings)

    logger.info("=" * 80)
    logger.info("测试 pump_torque 计算 - 单设备")
    logger.info("=" * 80)

    # 测试参数（使用UTC时间）
    station_id = 1
    device_id = 1
    start_time = UTC.localize(datetime(2025, 10, 22, 18, 39, 0))  # UTC时间
    end_time = UTC.localize(datetime(2025, 10, 22, 19, 39, 0))  # 1小时数据
    task_id = f"test_pump_torque_{device_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    logger.info(f"测试参数:")
    logger.info(f"  station_id: {station_id}")
    logger.info(f"  device_id: {device_id}")
    logger.info(f"  start_time: {start_time}")
    logger.info(f"  end_time: {end_time}")
    logger.info(f"  task_id: {task_id}")

    # 执行计算
    pipeline = PumpTorquePipeline()
    result = pipeline.execute(
        station_id=station_id,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
        task_id=task_id
    )

    logger.info(f"计算结果:")
    logger.info(f"  success: {result.get('success')}")
    logger.info(f"  device_id: {result.get('device_id')}")
    logger.info(f"  metric_key: {result.get('metric_key')}")
    logger.info(f"  results_count: {result.get('results_count')}")
    logger.info(f"  method_id: {result.get('method_id')}")
    logger.info(f"  skipped: {result.get('skipped', False)}")

    return result


def test_pump_torque_all_devices():
    """测试所有设备的 pump_torque 计算"""
    from app.services.calculation.metrics.pump_torque import PumpTorquePipeline
    from app.core.config.loader_new import load_settings
    from app.adapters.db.pool import initialize_pool

    # 初始化数据库连接池
    settings = load_settings(Path("configs"))
    initialize_pool(settings)

    logger.info("=" * 80)
    logger.info("测试 pump_torque 计算 - 所有设备")
    logger.info("=" * 80)

    # 测试参数（使用UTC时间）
    station_id = 1
    device_ids = [1, 2, 3, 4, 5, 6]
    start_time = UTC.localize(datetime(2025, 10, 22, 18, 39, 0))  # UTC时间
    end_time = UTC.localize(datetime(2025, 10, 22, 19, 39, 0))  # 1小时数据

    results = []
    for device_id in device_ids:
        task_id = f"test_pump_torque_{device_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        logger.info(f"\n测试设备 {device_id}...")

        pipeline = PumpTorquePipeline()
        result = pipeline.execute(
            station_id=station_id,
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            task_id=task_id
        )

        results.append(result)

        logger.info(f"  设备 {device_id} 结果: {result.get('results_count')} 条记录")

    # 汇总结果
    total_records = sum(r.get('results_count', 0) for r in results)
    logger.info(f"\n总计: {total_records} 条记录")

    return results


def verify_data_in_database():
    """验证数据库中的 pump_torque 数据"""
    from app.core.config.loader_new import load_settings
    from app.adapters.db.pool import get_connection, initialize_pool

    # 初始化数据库连接池
    settings = load_settings(Path("configs"))
    initialize_pool(settings)

    logger.info("=" * 80)
    logger.info("验证数据库中的 pump_torque 数据")
    logger.info("=" * 80)

    sql = """
        SELECT 
            device_id,
            COUNT(*) as record_count,
            MIN(ts_bucket) as earliest,
            MAX(ts_bucket) as latest,
            AVG(value) as avg_torque,
            MIN(value) as min_torque,
            MAX(value) as max_torque
        FROM fact_measurements
        WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_torque')
        GROUP BY device_id
        ORDER BY device_id
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

            if not rows:
                logger.info("数据库中没有 pump_torque 数据")
                return

            logger.info(f"找到 {len(rows)} 个设备的数据:")
            for row in rows:
                logger.info(f"  设备 {row[0]}: {row[1]} 条记录, 平均扭矩={row[4]:.2f} N·m, 范围=[{row[5]:.2f}, {row[6]:.2f}]")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='测试 pump_torque 计算')
    parser.add_argument('--mode', choices=['single', 'all', 'verify'], default='single',
                        help='测试模式: single=单设备, all=所有设备, verify=验证数据库')
    args = parser.parse_args()

    if args.mode == 'single':
        test_pump_torque_single_device()
    elif args.mode == 'all':
        test_pump_torque_all_devices()
    elif args.mode == 'verify':
        verify_data_in_database()

