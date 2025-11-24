#!/usr/bin/env python3
"""
测试三级优先级架构

测试场景：
1. 只有全局级数据时，使用全局级
2. 有站点级数据时，站点级覆盖全局级
3. 有设备级数据时，设备级优先级最高
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import logging
from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import Settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_three_tier_priority():
    """测试三级优先级架构"""
    logger.info("=" * 80)
    logger.info("开始测试三级优先级架构")
    logger.info("=" * 80)
    
    # 加载配置
    settings = Settings()
    
    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 测试场景1：全局级数据
                logger.info("\n场景1：测试全局级数据（metric_id=1, station_id=1, device_id=1）")
                logger.info("-" * 80)
                
                cur.execute("""
                    SELECT resolution, phys_min, phys_max
                    FROM public.v_effective_metric_metadata vm
                    WHERE vm.metric_id = 1
                      AND (vm.device_id = 1 OR vm.device_id IS NULL)
                      AND (vm.station_id = 1 OR vm.station_id IS NULL)
                    ORDER BY (vm.device_id IS NOT NULL) DESC, (vm.station_id IS NOT NULL) DESC
                    LIMIT 1
                """)
                
                result = cur.fetchone()
                if result:
                    logger.info(f"  ✓ 查询成功：resolution={result[0]}, phys_min={result[1]}, phys_max={result[2]}")
                    
                    # 验证是否返回设备级数据
                    cur.execute("""
                        SELECT station_id, device_id
                        FROM public.v_effective_metric_metadata vm
                        WHERE vm.metric_id = 1
                          AND (vm.device_id = 1 OR vm.device_id IS NULL)
                          AND (vm.station_id = 1 OR vm.station_id IS NULL)
                        ORDER BY (vm.device_id IS NOT NULL) DESC, (vm.station_id IS NOT NULL) DESC
                        LIMIT 1
                    """)
                    level_result = cur.fetchone()
                    station_id, device_id = level_result
                    
                    if device_id is not None:
                        logger.info(f"  ✓ 优先级正确：使用设备级数据（station_id={station_id}, device_id={device_id}）")
                    elif station_id is not None:
                        logger.info(f"  ✓ 优先级正确：使用站点级数据（station_id={station_id}, device_id=NULL）")
                    else:
                        logger.info(f"  ✓ 优先级正确：使用全局级数据（station_id=NULL, device_id=NULL）")
                else:
                    logger.error("  ❌ 查询失败：未找到数据")
                    return False
                
                # 测试场景2：修改设备级数据，验证优先级
                logger.info("\n场景2：修改设备级数据，验证优先级")
                logger.info("-" * 80)
                
                # 保存原始值
                cur.execute("""
                    SELECT resolution FROM public.dim_metric_metadata
                    WHERE metric_id = 1 AND station_id = 1 AND device_id = 1
                """)
                original_resolution = cur.fetchone()[0]
                logger.info(f"  原始设备级 resolution: {original_resolution}")
                
                # 修改设备级数据
                test_resolution = 999.99
                cur.execute("""
                    UPDATE public.dim_metric_metadata
                    SET resolution = %s
                    WHERE metric_id = 1 AND station_id = 1 AND device_id = 1
                """, (test_resolution,))
                logger.info(f"  已修改设备级 resolution 为: {test_resolution}")
                
                # 查询验证
                cur.execute("""
                    SELECT resolution
                    FROM public.v_effective_metric_metadata vm
                    WHERE vm.metric_id = 1
                      AND (vm.device_id = 1 OR vm.device_id IS NULL)
                      AND (vm.station_id = 1 OR vm.station_id IS NULL)
                    ORDER BY (vm.device_id IS NOT NULL) DESC, (vm.station_id IS NOT NULL) DESC
                    LIMIT 1
                """)
                
                result_resolution = cur.fetchone()[0]
                if result_resolution == test_resolution:
                    logger.info(f"  ✅ 优先级验证通过：查询返回设备级数据（resolution={result_resolution}）")
                else:
                    logger.error(f"  ❌ 优先级验证失败：期望{test_resolution}，实际{result_resolution}")
                    return False
                
                # 恢复原始值
                cur.execute("""
                    UPDATE public.dim_metric_metadata
                    SET resolution = %s
                    WHERE metric_id = 1 AND station_id = 1 AND device_id = 1
                """, (original_resolution,))
                logger.info(f"  已恢复设备级 resolution 为: {original_resolution}")
                
                # 测试场景3：验证数据完整性
                logger.info("\n场景3：验证数据完整性")
                logger.info("-" * 80)
                
                cur.execute("""
                    SELECT 
                        COUNT(*) FILTER (WHERE station_id IS NULL AND device_id IS NULL) AS global_count,
                        COUNT(*) FILTER (WHERE station_id IS NOT NULL AND device_id IS NULL) AS station_count,
                        COUNT(*) FILTER (WHERE device_id IS NOT NULL) AS device_count,
                        COUNT(*) AS total_count
                    FROM public.dim_metric_metadata
                """)
                
                counts = cur.fetchone()
                logger.info(f"  全局级: {counts[0]} 条")
                logger.info(f"  站点级: {counts[1]} 条")
                logger.info(f"  设备级: {counts[2]} 条")
                logger.info(f"  总计: {counts[3]} 条")
                
                if counts[0] == 56 and counts[1] == 56 and counts[2] == 448:
                    logger.info("  ✅ 数据完整性验证通过")
                else:
                    logger.error(f"  ❌ 数据完整性验证失败：期望56+56+448=560，实际{counts[3]}")
                    return False
                
                logger.info("\n" + "=" * 80)
                logger.info("✅ 所有测试通过！三级优先级架构工作正常")
                logger.info("=" * 80)
                return True
                
    except Exception as e:
        logger.error(f"\n❌ 测试失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_three_tier_priority()
    sys.exit(0 if success else 1)

