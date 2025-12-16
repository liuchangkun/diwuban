#!/usr/bin/env python3
"""
修改 v_effective_metric_metadata 视图脚本

将视图从两表合并简化为单表直接映射

使用方法：
    python scripts/python/alter_v_effective_metric_metadata.py
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
    """执行视图修改"""
    logger.info("=" * 80)
    logger.info("开始修改 v_effective_metric_metadata 视图")
    logger.info("=" * 80)
    
    # 加载配置
    settings = Settings()
    
    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 步骤1：删除旧视图
                logger.info("\n步骤1：删除旧视图...")
                
                cur.execute("DROP VIEW IF EXISTS public.v_effective_metric_metadata CASCADE")
                logger.info("  ✓ 旧视图已删除")
                
                # 步骤2：创建新视图
                logger.info("\n步骤2：创建新视图...")
                
                cur.execute("""
                    CREATE OR REPLACE VIEW public.v_effective_metric_metadata AS
                    SELECT 
                        station_id,
                        device_id,
                        metric_id,
                        unit,
                        resolution,
                        phys_min,
                        phys_max,
                        saturation_min,
                        saturation_max
                    FROM public.dim_metric_metadata
                """)
                logger.info("  ✓ 新视图已创建")
                
                # 步骤3：添加视图注释
                logger.info("\n步骤3：添加视图注释...")
                
                cur.execute("""
                    COMMENT ON VIEW public.v_effective_metric_metadata IS 
'有效指标元数据视图（三级优先级架构）：
- 直接映射 dim_metric_metadata 表
- 支持三级优先级查询：设备级 > 站点级 > 全局级
- 查询时使用 LEFT JOIN LATERAL + ORDER BY 实现优先级

典型查询模式：
  LEFT JOIN LATERAL (
    SELECT resolution, phys_min, phys_max
    FROM v_effective_metric_metadata vm
    WHERE vm.metric_id = f.metric_id
      AND (vm.device_id = f.device_id OR vm.device_id IS NULL)
      AND (vm.station_id = f.station_id OR vm.station_id IS NULL)
    ORDER BY (vm.device_id IS NOT NULL) DESC, (vm.station_id IS NOT NULL) DESC
    LIMIT 1
  ) meta ON TRUE

注意事项：
- 视图返回所有记录（56全局 + 56站点 + N设备×56）
- 查询时必须使用 ORDER BY 和 LIMIT 1 确保优先级正确
- 字段顺序与原视图保持一致，确保向后兼容'
                """)
                logger.info("  ✓ 视图注释已添加")
                
                # 步骤4：验证视图
                logger.info("\n步骤4：验证视图...")
                
                cur.execute("SELECT COUNT(*) FROM public.v_effective_metric_metadata")
                view_count = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM public.dim_devices")
                device_count = cur.fetchone()[0]
                
                expected_count = 56 + 56 + (device_count * 56)
                
                logger.info(f"  视图记录数：{view_count} / {expected_count} (期望)")
                
                if view_count != expected_count:
                    raise RuntimeError(f"❌ 视图记录数不正确：期望{expected_count}条，实际{view_count}条")
                
                logger.info("  ✓ 视图验证通过")
                
                # 提交事务
                conn.commit()
                
                logger.info("\n" + "=" * 80)
                logger.info("✅ 视图修改完成！")
                logger.info("=" * 80)
                logger.info("视图已简化为直接映射 dim_metric_metadata 表")
                logger.info("查询性能已优化（无JOIN操作）")
                logger.info("向后兼容性已保持（字段顺序和名称不变）")
                logger.info("=" * 80)
                
    except Exception as e:
        logger.error(f"\n❌ 视图修改失败：{str(e)}")
        logger.error("事务已回滚")
        sys.exit(1)


if __name__ == "__main__":
    main()

