"""
完整的端到端测试 - 实际执行 pump_inlet_pressure 计算
"""
import sys
import logging
import numpy as np
from pathlib import Path
from app.services.calculation.orchestrator import CalculationOrchestrator
from app.core.config.loader import load_settings
from app.adapters.db import init_database, get_connection

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_full_calculation():
    """完整的端到端测试"""
    
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
    metrics = ["pump_inlet_pressure"]
    
    logger.info("=" * 80)
    logger.info("完整的端到端测试")
    logger.info(f"station_id={station_id}, device_id={device_id}")
    logger.info(f"metrics={metrics}")
    logger.info("=" * 80)
    
    # 步骤1：检查计算前的数据库状态
    logger.info("\n步骤1：检查计算前的数据库状态")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) 
                FROM fact_measurements fm
                JOIN dim_metric_config mc ON mc.id = fm.metric_id
                WHERE fm.station_id = %s
                  AND fm.device_id = %s
                  AND mc.metric_key = 'pump_inlet_pressure'
                  AND fm.ts_bucket >= %s::timestamptz
                  AND fm.ts_bucket < %s::timestamptz
            """, (station_id, device_id, start_time, end_time))
            count_before = cur.fetchone()[0]
            logger.info(f"计算前 pump_inlet_pressure 数据点数: {count_before}")
    
    # 步骤2：执行计算（不写入数据库）
    logger.info("\n步骤2：执行计算（不写入数据库）")
    result = orchestrator.calculate_missing_metrics(
        station_id=station_id,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
        metrics=metrics,
        write_to_db=False  # 先不写入，只测试计算
    )
    
    logger.info(f"计算结果:")
    logger.info(f"  success: {result['success']}")
    logger.info(f"  metrics_calculated: {result['metrics_calculated']}")
    logger.info(f"  metrics_failed: {result['metrics_failed']}")
    logger.info(f"  total_points: {result['total_points']}")
    logger.info(f"  valid_points: {result['valid_points']}")
    logger.info(f"  errors: {result['errors']}")
    
    # 步骤3：如果计算成功，再次执行并写入数据库
    if result['success'] and 'pump_inlet_pressure' in result['metrics_calculated']:
        logger.info("\n步骤3：执行计算并写入数据库")
        result2 = orchestrator.calculate_missing_metrics(
            station_id=station_id,
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            metrics=metrics,
            write_to_db=True  # 写入数据库
        )
        
        logger.info(f"写入结果:")
        logger.info(f"  success: {result2['success']}")
        logger.info(f"  written_points: {result2['written_points']}")
        
        # 步骤4：检查计算后的数据库状态
        logger.info("\n步骤4：检查计算后的数据库状态")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM fact_measurements fm
                    JOIN dim_metric_config mc ON mc.id = fm.metric_id
                    WHERE fm.station_id = %s
                      AND fm.device_id = %s
                      AND mc.metric_key = 'pump_inlet_pressure'
                      AND fm.ts_bucket >= %s::timestamptz
                      AND fm.ts_bucket < %s::timestamptz
                """, (station_id, device_id, start_time, end_time))
                count_after = cur.fetchone()[0]
                logger.info(f"计算后 pump_inlet_pressure 数据点数: {count_after}")
                logger.info(f"新增数据点数: {count_after - count_before}")
                
                # 查看前5个数据点
                cur.execute("""
                    SELECT fm.ts_bucket, fm.value, fm.quality_status
                    FROM fact_measurements fm
                    JOIN dim_metric_config mc ON mc.id = fm.metric_id
                    WHERE fm.station_id = %s
                      AND fm.device_id = %s
                      AND mc.metric_key = 'pump_inlet_pressure'
                      AND fm.ts_bucket >= %s::timestamptz
                      AND fm.ts_bucket < %s::timestamptz
                    ORDER BY fm.ts_bucket
                    LIMIT 5
                """, (station_id, device_id, start_time, end_time))
                rows = cur.fetchall()
                if rows:
                    logger.info(f"前5个数据点:")
                    for row in rows:
                        logger.info(f"  {row[0]}: value={row[1]}, quality_status={row[2]}")
                else:
                    logger.warning("没有找到数据点！")
    else:
        logger.error("\n❌ 计算失败！")
        logger.error(f"失败的指标: {result['metrics_failed']}")
        logger.error(f"错误信息: {result['errors']}")
    
    logger.info("=" * 80)
    logger.info("测试完成")
    logger.info("=" * 80)

if __name__ == "__main__":
    test_full_calculation()

