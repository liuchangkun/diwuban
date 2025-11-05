"""
测试 load_data 方法是否正确加载站级数据（pool_liquid_level）
"""
import sys
import logging
import numpy as np
from pathlib import Path
from app.services.calculation.orchestrator import CalculationOrchestrator
from app.core.config.loader import load_settings
from app.adapters.db import init_database

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_load_data():
    """测试 load_data 是否正确加载 pool_liquid_level"""

    # 初始化数据库连接
    settings = load_settings(Path("configs"))
    init_database(settings)

    # 初始化组件（使用默认初始化）
    orchestrator = CalculationOrchestrator()
    
    # 测试参数
    station_id = 1
    device_id = 1  # pump 类型设备
    start_time = "2025-05-31 18:00:00+00"
    end_time = "2025-05-31 20:00:00+00"
    metric_keys = ["pump_inlet_pressure"]  # 需要计算的指标
    
    logger.info("=" * 80)
    logger.info("测试 load_data 方法")
    logger.info(f"station_id={station_id}, device_id={device_id}")
    logger.info(f"metric_keys={metric_keys}")
    logger.info("=" * 80)
    
    # 调用 load_data
    data, timestamps = orchestrator.load_data(
        station_id=station_id,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
        metric_keys=metric_keys,
        filter_running=False,  # 不过滤运行状态
        filter_quality=True
    )
    
    logger.info("=" * 80)
    logger.info("load_data 结果：")
    logger.info(f"timestamps 数量: {len(timestamps)}")
    logger.info(f"data 字典键: {list(data.keys())}")
    logger.info("=" * 80)
    
    # 检查 pool_liquid_level 是否在 data 中
    if "pool_liquid_level" in data:
        pool_data = data["pool_liquid_level"]
        non_nan_count = (~np.isnan(pool_data)).sum()
        logger.info(f"✅ pool_liquid_level 已加载！")
        logger.info(f"   数据点数: {len(pool_data)}")
        logger.info(f"   非NaN数据点: {non_nan_count}")
        logger.info(f"   前5个值: {pool_data[:5]}")
    else:
        logger.error(f"❌ pool_liquid_level 未加载！")
        logger.error(f"   data 字典中的键: {list(data.keys())}")
    
    # 检查 _is_station_metric 的判断
    is_station = orchestrator._is_station_metric("pool_liquid_level")
    logger.info(f"_is_station_metric('pool_liquid_level') = {is_station}")
    
    # 检查 _collect_metric_requirements 的结果
    device_metrics, station_metrics = orchestrator._collect_metric_requirements(metric_keys)
    logger.info(f"device_metrics: {device_metrics}")
    logger.info(f"station_metrics: {station_metrics}")
    
    logger.info("=" * 80)
    logger.info("测试完成")
    logger.info("=" * 80)

if __name__ == "__main__":
    test_load_data()

