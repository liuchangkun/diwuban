#!/usr/bin/env python3
"""
测试 prepare_dim 流程

验证：
1. 元数据完整性验证是否正常工作
2. dim_metric_metadata 表是否不会被清空
3. 整个流程是否正常运行
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import logging
from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import Settings
from app.services.ingest.prepare_dim import prepare_dim

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """测试 prepare_dim 流程"""
    logger.info("=" * 80)
    logger.info("开始测试 prepare_dim 流程")
    logger.info("=" * 80)
    
    # 加载配置
    settings = Settings()
    
    try:
        # 步骤1：查询迁移前的元数据记录数
        logger.info("\n步骤1：查询元数据表当前状态...")
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM dim_metric_metadata")
                before_count = cur.fetchone()[0]
                logger.info(f"  ✓ 当前 dim_metric_metadata 表有 {before_count} 条记录")
        
        # 步骤2：执行 prepare_dim
        logger.info("\n步骤2：执行 prepare_dim 流程...")
        logger.info("-" * 80)

        # 使用默认映射文件
        mapping_path = project_root / "configs" / "data_mapping.v2.json"
        if not mapping_path.exists():
            logger.error(f"  ❌ 映射文件不存在：{mapping_path}")
            sys.exit(1)

        logger.info(f"  使用映射文件：{mapping_path}")
        logger.info(f"  执行阶段：阶段1（维度表重建）")
        prepare_dim(settings, mapping_path, stage=1)

        logger.info("-" * 80)
        logger.info("  ✓ prepare_dim 流程执行完成")
        
        # 步骤3：验证元数据表是否被清空
        logger.info("\n步骤3：验证元数据表是否被清空...")
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM dim_metric_metadata")
                after_count = cur.fetchone()[0]
                logger.info(f"  ✓ 执行后 dim_metric_metadata 表有 {after_count} 条记录")
                
                if after_count == before_count:
                    logger.info(f"  ✅ 验证通过：元数据表未被清空（{before_count} 条记录保持不变）")
                else:
                    logger.error(f"  ❌ 验证失败：元数据表记录数发生变化（{before_count} → {after_count}）")
                    sys.exit(1)
        
        # 步骤4：验证数据完整性
        logger.info("\n步骤4：验证数据完整性...")
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 验证三级数据分布
                cur.execute("""
                    WITH level_data AS (
                        SELECT 
                            CASE 
                                WHEN station_id IS NULL AND device_id IS NULL THEN '全局级'
                                WHEN station_id IS NOT NULL AND device_id IS NULL THEN '站点级'
                                WHEN device_id IS NOT NULL THEN '设备级'
                            END AS level
                        FROM public.dim_metric_metadata
                    )
                    SELECT level, COUNT(*) as count
                    FROM level_data
                    GROUP BY level
                    ORDER BY 
                        CASE level
                            WHEN '全局级' THEN 1
                            WHEN '站点级' THEN 2
                            WHEN '设备级' THEN 3
                        END
                """)
                
                results = cur.fetchall()
                logger.info("  数据分布：")
                for row in results:
                    logger.info(f"    {row[0]}: {row[1]} 条")
                
                # 验证总数
                total = sum(row[1] for row in results)
                if total == 560:
                    logger.info(f"  ✅ 数据完整性验证通过：总计 {total} 条记录")
                else:
                    logger.error(f"  ❌ 数据完整性验证失败：期望560条，实际{total}条")
                    sys.exit(1)
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ 所有测试通过！")
        logger.info("=" * 80)
        logger.info("验证结果：")
        logger.info("  ✓ 元数据完整性验证正常工作")
        logger.info("  ✓ dim_metric_metadata 表未被清空")
        logger.info("  ✓ prepare_dim 流程正常运行")
        logger.info("  ✓ 三级优先级架构数据完整")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"\n❌ 测试失败：{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

