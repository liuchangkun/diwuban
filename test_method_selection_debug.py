"""
测试方法选择逻辑 - 验证 pool_liquid_level 是否能被正确识别为可用依赖
"""
import sys
import logging
import numpy as np
from pathlib import Path
from app.services.calculation.orchestrator import CalculationOrchestrator
from app.services.calculation.domain import CalculationContext
from app.core.config.loader import load_settings
from app.adapters.db import init_database

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,  # 使用 DEBUG 级别查看详细日志
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_method_selection():
    """测试方法选择是否正确识别 pool_liquid_level 依赖"""
    
    # 初始化数据库连接
    settings = load_settings(Path("configs"))
    init_database(settings)

    # 初始化组件
    orchestrator = CalculationOrchestrator()
    
    # 测试参数
    station_id = 1
    device_id = 1  # pump 类型设备
    start_time = "2025-05-31 18:00:00+00"
    end_time = "2025-05-31 20:00:00+00"
    metric_keys = ["pump_inlet_pressure"]
    
    logger.info("=" * 80)
    logger.info("测试方法选择逻辑")
    logger.info(f"station_id={station_id}, device_id={device_id}")
    logger.info(f"metric_keys={metric_keys}")
    logger.info("=" * 80)
    
    # 步骤1：加载数据
    logger.info("\n步骤1：加载数据")
    data, timestamps = orchestrator.load_data(
        station_id=station_id,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
        metric_keys=metric_keys,
        filter_running=False,
        filter_quality=True
    )
    
    logger.info(f"data 字典键: {list(data.keys())}")
    logger.info(f"pool_liquid_level 在 data 中: {'pool_liquid_level' in data}")
    
    # 步骤2：构造 available_metrics
    logger.info("\n步骤2：构造 available_metrics")
    available_metrics = list(data.keys())
    logger.info(f"available_metrics: {available_metrics}")
    logger.info(f"pool_liquid_level 在 available_metrics 中: {'pool_liquid_level' in available_metrics}")
    
    # 步骤3：获取设备类型
    logger.info("\n步骤3：获取设备类型")
    device_type = orchestrator._get_device_type(station_id, device_id)
    logger.info(f"device_type: {device_type}")
    
    # 步骤4：构造上下文
    logger.info("\n步骤4：构造上下文")
    running_count = orchestrator._get_running_device_count(
        station_id=station_id, start_time=start_time, end_time=end_time
    )
    ctx = CalculationContext(
        station_id=station_id,
        device_id=device_id,
        start_ts=start_time,
        end_ts=end_time,
        bucket_size_sec=None,
        extra={"device_type": device_type, "running_count": running_count}
    )
    logger.info(f"ctx.extra: {ctx.extra}")
    
    # 步骤5：调用方法选择器
    logger.info("\n步骤5：调用方法选择器")
    logger.info("=" * 80)
    method_desc = orchestrator.method_selector.select_method_ctx(
        ctx=ctx,
        metric_key="pump_inlet_pressure",
        available_metrics=available_metrics,
        data=data
    )
    logger.info("=" * 80)
    
    # 步骤6：检查结果
    logger.info("\n步骤6：检查结果")
    if method_desc is not None:
        logger.info(f"✅ 方法选择成功！")
        logger.info(f"   method_id: {method_desc.method_id}")
        logger.info(f"   method_code: {method_desc.method_code}")
        logger.info(f"   priority: {method_desc.priority}")
        logger.info(f"   dependencies: {method_desc.dependencies}")
    else:
        logger.error(f"❌ 方法选择失败！")
        logger.error(f"   没有找到合适的方法")
        
        # 手动检查方法注册表
        logger.info("\n手动检查方法注册表：")
        if "pump_inlet_pressure" in orchestrator.method_selector._method_registry:
            methods = orchestrator.method_selector._method_registry["pump_inlet_pressure"]
            logger.info(f"pump_inlet_pressure 有 {len(methods)} 个注册方法：")
            for i, method in enumerate(methods):
                logger.info(f"\n方法 {i+1}:")
                logger.info(f"  method_id: {method.get('method_id')}")
                logger.info(f"  method_code: {method.get('method_code')}")
                logger.info(f"  priority: {method.get('priority')}")
                logger.info(f"  dependencies: {method.get('dependencies')}")
                logger.info(f"  allowed_device_types: {method.get('allowed_device_types')}")
                
                # 检查依赖是否满足
                deps = method.get('dependencies', [])
                logger.info(f"  依赖检查:")
                for dep in deps:
                    in_available = dep in available_metrics
                    in_data = dep in data if data else False
                    logger.info(f"    - {dep}: in_available={in_available}, in_data={in_data}")
        else:
            logger.error("pump_inlet_pressure 没有注册方法！")
    
    logger.info("=" * 80)
    logger.info("测试完成")
    logger.info("=" * 80)

if __name__ == "__main__":
    test_method_selection()

