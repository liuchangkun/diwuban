#!/usr/bin/env python3
"""
元数据表三级优先级架构迁移脚本

执行步骤：
1. 备份现有数据
2. 删除 dim_metric_metadata_override 表
3. 修改 dim_metric_metadata 表结构
4. 生成三级元数据（全局 + 站点 + 设备）
5. 验证数据完整性

使用方法：
    python scripts/python/migrate_metadata_to_three_tier.py
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
    """执行迁移"""
    logger.info("=" * 80)
    logger.info("开始执行元数据表三级优先级架构迁移")
    logger.info("=" * 80)
    
    # 加载配置
    settings = Settings()
    
    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 步骤1：前置检查
                logger.info("\n步骤1：前置检查...")
                
                cur.execute("SELECT COUNT(*) FROM dim_metric_metadata")
                metadata_count = cur.fetchone()[0]
                logger.info(f"  ✓ dim_metric_metadata 表有 {metadata_count} 条记录")
                
                if metadata_count != 56:
                    raise RuntimeError(f"❌ dim_metric_metadata 表数据量不正确：期望56条，实际{metadata_count}条")
                
                cur.execute("SELECT COUNT(*) FROM dim_stations")
                station_count = cur.fetchone()[0]
                logger.info(f"  ✓ dim_stations 表有 {station_count} 条记录")
                
                cur.execute("SELECT COUNT(*) FROM dim_devices")
                device_count = cur.fetchone()[0]
                logger.info(f"  ✓ dim_devices 表有 {device_count} 条记录")
                
                cur.execute("SELECT COUNT(*) FROM dim_metric_config")
                metric_count = cur.fetchone()[0]
                logger.info(f"  ✓ dim_metric_config 表有 {metric_count} 条记录")
                
                # 步骤2：创建临时备份表
                logger.info("\n步骤2：创建临时备份表...")
                
                cur.execute("DROP TABLE IF EXISTS tmp_metadata_backup CASCADE")
                cur.execute("""
                    CREATE TEMP TABLE tmp_metadata_backup AS
                    SELECT 
                        metric_id, unit, resolution, phys_min, phys_max,
                        saturation_min, saturation_max, remark, updated_at, updated_by
                    FROM public.dim_metric_metadata
                """)
                
                cur.execute("SELECT COUNT(*) FROM tmp_metadata_backup")
                backup_count = cur.fetchone()[0]
                logger.info(f"  ✓ 备份成功：{backup_count} 条记录")
                
                if backup_count != 56:
                    raise RuntimeError(f"❌ 备份失败：期望56条，实际{backup_count}条")
                
                # 步骤3：删除 dim_metric_metadata_override 表
                logger.info("\n步骤3：删除 dim_metric_metadata_override 表...")
                
                cur.execute("DROP VIEW IF EXISTS public.v_effective_metric_metadata CASCADE")
                logger.info("  ✓ 视图已删除")
                
                cur.execute("DROP TABLE IF EXISTS public.dim_metric_metadata_override CASCADE")
                logger.info("  ✓ dim_metric_metadata_override 表已删除")
                
                # 步骤4：修改 dim_metric_metadata 表结构
                logger.info("\n步骤4：修改 dim_metric_metadata 表结构...")
                
                # 4.1 添加字段
                cur.execute("""
                    ALTER TABLE public.dim_metric_metadata
                        ADD COLUMN IF NOT EXISTS station_id bigint NULL,
                        ADD COLUMN IF NOT EXISTS device_id bigint NULL
                """)
                logger.info("  ✓ 已添加 station_id 和 device_id 字段")
                
                # 4.2 移除外键约束（永久配置表不应受维度表重建影响）
                cur.execute("""
                    ALTER TABLE public.dim_metric_metadata
                        DROP CONSTRAINT IF EXISTS fk_metadata_station CASCADE
                """)
                cur.execute("""
                    ALTER TABLE public.dim_metric_metadata
                        DROP CONSTRAINT IF EXISTS fk_metadata_device CASCADE
                """)
                logger.info("  ✓ 已移除外键约束（永久配置表不受维度表重建影响）")
                
                # 4.3 删除旧主键
                cur.execute("""
                    ALTER TABLE public.dim_metric_metadata
                        DROP CONSTRAINT IF EXISTS dim_metric_metadata_pkey CASCADE
                """)
                logger.info("  ✓ 已删除旧主键")

                # 步骤5：迁移现有数据为全局级（必须在创建主键之前）
                logger.info("\n步骤5：迁移现有数据为全局级...")

                cur.execute("""
                    UPDATE public.dim_metric_metadata
                    SET station_id = NULL, device_id = NULL
                """)

                cur.execute("""
                    SELECT COUNT(*) FROM public.dim_metric_metadata
                    WHERE station_id IS NULL AND device_id IS NULL
                """)
                global_count = cur.fetchone()[0]
                logger.info(f"  ✓ 全局级数据迁移成功：{global_count} 条")

                if global_count != 56:
                    raise RuntimeError(f"❌ 全局级数据迁移失败：期望56条，实际{global_count}条")

                # 步骤6：生成站点级数据
                logger.info("\n步骤6：生成站点级数据...")

                cur.execute("""
                    INSERT INTO public.dim_metric_metadata (
                        station_id, device_id, metric_id,
                        unit, resolution, phys_min, phys_max,
                        saturation_min, saturation_max, remark,
                        updated_at, updated_by
                    )
                    SELECT
                        1 AS station_id,
                        NULL AS device_id,
                        metric_id, unit, resolution, phys_min, phys_max,
                        saturation_min, saturation_max, remark,
                        now() AS updated_at,
                        'migration_script' AS updated_by
                    FROM tmp_metadata_backup
                """)

                cur.execute("""
                    SELECT COUNT(*) FROM public.dim_metric_metadata
                    WHERE station_id = 1 AND device_id IS NULL
                """)
                station_level_count = cur.fetchone()[0]
                logger.info(f"  ✓ 站点级数据生成成功：{station_level_count} 条")

                if station_level_count != 56:
                    raise RuntimeError(f"❌ 站点级数据生成失败：期望56条，实际{station_level_count}条")

                # 步骤7：生成设备级数据
                logger.info("\n步骤7：生成设备级数据...")

                cur.execute("""
                    INSERT INTO public.dim_metric_metadata (
                        station_id, device_id, metric_id,
                        unit, resolution, phys_min, phys_max,
                        saturation_min, saturation_max, remark,
                        updated_at, updated_by
                    )
                    SELECT
                        d.station_id,
                        d.id AS device_id,
                        t.metric_id, t.unit, t.resolution, t.phys_min, t.phys_max,
                        t.saturation_min, t.saturation_max, t.remark,
                        now() AS updated_at,
                        'migration_script' AS updated_by
                    FROM tmp_metadata_backup t
                    CROSS JOIN public.dim_devices d
                """)

                cur.execute("""
                    SELECT COUNT(*) FROM public.dim_metric_metadata
                    WHERE device_id IS NOT NULL
                """)
                device_level_count = cur.fetchone()[0]
                expected_device_level = device_count * 56
                logger.info(f"  ✓ 设备级数据生成成功：{device_level_count} 条（{device_count} 个设备 × 56 指标）")

                if device_level_count != expected_device_level:
                    raise RuntimeError(f"❌ 设备级数据生成失败：期望{expected_device_level}条，实际{device_level_count}条")

                # 步骤8：创建唯一约束（在数据生成完成后）
                # 注意：由于全局级数据的 station_id 和 device_id 都是 NULL，
                # PostgreSQL 不允许在包含 NULL 的列上创建主键，
                # 因此使用唯一索引（COALESCE 处理 NULL）来保证数据完整性
                logger.info("\n步骤8：创建唯一约束...")

                # 创建唯一索引（使用 COALESCE 处理 NULL）
                cur.execute("""
                    DROP INDEX IF EXISTS uk_metadata_scope CASCADE
                """)
                cur.execute("""
                    CREATE UNIQUE INDEX uk_metadata_scope
                        ON public.dim_metric_metadata (
                            COALESCE(station_id, -1),
                            COALESCE(device_id, -1),
                            metric_id
                        )
                """)
                logger.info("  ✓ 已创建唯一索引（使用 COALESCE 处理 NULL 值）")

                # 步骤9：验证数据完整性
                logger.info("\n步骤9：验证数据完整性...")

                cur.execute("SELECT COUNT(*) FROM public.dim_metric_metadata")
                total_count = cur.fetchone()[0]
                expected_total = 56 + 56 + expected_device_level

                logger.info("  " + "=" * 60)
                logger.info(f"  总记录数：{total_count} / {expected_total} (期望)")
                logger.info(f"  全局级：{global_count} / 56 (期望)")
                logger.info(f"  站点级：{station_level_count} / 56 (期望)")
                logger.info(f"  设备级：{device_level_count} / {expected_device_level} (期望)")
                logger.info("  " + "=" * 60)

                if total_count != expected_total:
                    raise RuntimeError(f"❌ 总记录数不正确")

                logger.info("  ✓ 数据完整性验证通过")

                # 步骤10：创建索引
                logger.info("\n步骤10：创建索引...")

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_metadata_metric_id
                        ON public.dim_metric_metadata(metric_id)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_metadata_station_metric
                        ON public.dim_metric_metadata(station_id, metric_id)
                        WHERE station_id IS NOT NULL
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_metadata_device_metric
                        ON public.dim_metric_metadata(device_id, metric_id)
                        WHERE device_id IS NOT NULL
                """)
                logger.info("  ✓ 索引创建成功")

                # 步骤11：添加表注释
                logger.info("\n步骤11：添加表注释...")

                cur.execute("""
                    COMMENT ON TABLE public.dim_metric_metadata IS
                    '指标元数据表（三级优先级架构）：
- 全局级：station_id=NULL, device_id=NULL（默认值）
- 站点级：station_id=<id>, device_id=NULL（覆盖全局）
- 设备级：station_id=<id>, device_id=<id>（最高优先级）

查询时按优先级排序：设备级 > 站点级 > 全局级'
                """)

                cur.execute("""
                    COMMENT ON COLUMN public.dim_metric_metadata.station_id IS
                    '站点ID（NULL表示全局级）'
                """)

                cur.execute("""
                    COMMENT ON COLUMN public.dim_metric_metadata.device_id IS
                    '设备ID（NULL表示站点级或全局级）'
                """)
                logger.info("  ✓ 表注释已添加")

                # 提交事务
                conn.commit()

                logger.info("\n" + "=" * 80)
                logger.info("✅ 迁移完成！")
                logger.info("=" * 80)
                logger.info(f"表结构已改造为三级优先级架构")
                logger.info(f"数据已生成：56全局 + 56站点 + {expected_device_level}设备 = {expected_total}条")
                logger.info(f"下一步：执行视图修改脚本")
                logger.info("  python scripts/python/alter_v_effective_metric_metadata.py")
                logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\n❌ 迁移失败：{str(e)}")
        logger.error("事务已回滚，数据库状态未改变")
        sys.exit(1)


if __name__ == "__main__":
    main()

