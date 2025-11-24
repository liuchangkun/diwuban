#!/usr/bin/env python3
"""
修复元数据表外键约束

问题：ON DELETE CASCADE 导致清空 dim_devices/dim_stations 时元数据被删除
解决：移除外键约束，因为 dim_metric_metadata 是永久配置表
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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """修复外键约束"""
    logger.info("=" * 80)
    logger.info("开始修复元数据表外键约束")
    logger.info("=" * 80)
    
    # 加载配置
    settings = Settings()
    
    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 步骤1：删除外键约束
                logger.info("\n步骤1：删除外键约束...")
                
                cur.execute("""
                    ALTER TABLE public.dim_metric_metadata
                        DROP CONSTRAINT IF EXISTS fk_metadata_station CASCADE
                """)
                logger.info("  ✓ 已删除 fk_metadata_station 约束")
                
                cur.execute("""
                    ALTER TABLE public.dim_metric_metadata
                        DROP CONSTRAINT IF EXISTS fk_metadata_device CASCADE
                """)
                logger.info("  ✓ 已删除 fk_metadata_device 约束")
                
                # 步骤2：添加表注释
                logger.info("\n步骤2：更新表注释...")
                
                cur.execute("""
                    COMMENT ON TABLE public.dim_metric_metadata IS 
'指标元数据表（三级优先级架构，永久配置表）：
- 全局级：station_id=NULL, device_id=NULL（默认值）
- 站点级：station_id=<id>, device_id=NULL（覆盖全局）
- 设备级：station_id=<id>, device_id=<id>（最高优先级）

查询时按优先级排序：设备级 > 站点级 > 全局级

重要特性：
- 永久配置表：不会被 prepare_dim 流程清空或备份
- 无外键约束：不受 dim_devices/dim_stations 重建影响
- 数据完整性：通过应用层验证和唯一索引保证'
                """)
                
                cur.execute("""
                    COMMENT ON COLUMN public.dim_metric_metadata.station_id IS 
'站点ID（NULL表示全局级）- 无外键约束，数据完整性由应用层保证'
                """)
                
                cur.execute("""
                    COMMENT ON COLUMN public.dim_metric_metadata.device_id IS 
'设备ID（NULL表示站点级或全局级）- 无外键约束，数据完整性由应用层保证'
                """)
                logger.info("  ✓ 表注释已更新")
                
                # 提交事务
                conn.commit()
                
                logger.info("\n" + "=" * 80)
                logger.info("✅ 外键约束修复完成！")
                logger.info("=" * 80)
                logger.info("修改内容：")
                logger.info("  - 已移除 fk_metadata_station 外键约束")
                logger.info("  - 已移除 fk_metadata_device 外键约束")
                logger.info("  - 元数据表现在不受维度表重建影响")
                logger.info("")
                logger.info("下一步：重新执行迁移脚本生成完整数据")
                logger.info("  python scripts/python/migrate_metadata_to_three_tier.py")
                logger.info("=" * 80)
                
    except Exception as e:
        logger.error(f"\n❌ 修复失败：{str(e)}")
        logger.error("事务已回滚")
        sys.exit(1)


if __name__ == "__main__":
    main()

