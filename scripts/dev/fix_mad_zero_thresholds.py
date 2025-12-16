#!/usr/bin/env python
"""
修复MAD=0指标的最小阈值问题

问题：
1. 7个指标的MAD=0，导致flatline_eps=0，平台期检测失效
2. metric_id=10（功率因数）的resolution为NULL

解决方案：
1. 为功率因数配置resolution=0.01（无量纲，精度0.01）
2. 更新所有MAD=0的基线数据，设置flatline_eps=resolution
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db import get_connection, init_database


def main():
    """主函数"""
    print("=" * 80)
    print("  修复MAD=0指标的最小阈值问题")
    print("=" * 80)
    
    # 加载配置
    settings = load_settings(Path("configs"))
    
    # 初始化数据库连接池
    init_database(settings)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 步骤1：检查MAD=0的指标
            print("\n步骤1：检查MAD=0的指标")
            print("-" * 80)
            cur.execute("""
                SELECT 
                    b.station_id,
                    b.device_id,
                    b.metric_id,
                    c.metric_key,
                    m.unit,
                    m.resolution,
                    b.median,
                    b.mad,
                    b.flatline_eps
                FROM metric_rule_auto_baseline b
                JOIN dim_metric_config c ON b.metric_id = c.id
                LEFT JOIN dim_metric_metadata m ON b.metric_id = m.metric_id
                WHERE b.mad = 0
                ORDER BY b.station_id, b.device_id, b.metric_id
            """)
            
            mad_zero_rows = cur.fetchall()
            print(f"  发现 {len(mad_zero_rows)} 个MAD=0的基线数据：")
            for row in mad_zero_rows:
                print(f"    站点{row[0]} 设备{row[1]} 指标{row[2]} ({row[3]}): "
                      f"unit={row[4]}, resolution={row[5]}, median={row[6]}, "
                      f"mad={row[7]}, flatline_eps={row[8]}")
            
            # 步骤2：修复功率因数的resolution
            print("\n步骤2：修复功率因数的resolution")
            print("-" * 80)
            cur.execute("""
                UPDATE dim_metric_metadata
                SET resolution = 0.01,
                    remark = COALESCE(remark, '') || 
                             CASE 
                                 WHEN COALESCE(remark, '') = '' THEN ''
                                 ELSE ' | '
                             END ||
                             '修复: 添加resolution=0.01（无量纲）'
                FROM dim_metric_config c
                WHERE dim_metric_metadata.metric_id = c.id
                  AND c.metric_key = 'pump_power_factor'
                  AND dim_metric_metadata.resolution IS NULL
            """)
            
            updated_count = cur.rowcount
            print(f"  ✓ 更新了 {updated_count} 个指标的resolution")
            
            # 步骤3：更新MAD=0的基线数据的flatline_eps
            print("\n步骤3：更新MAD=0的基线数据的flatline_eps")
            print("-" * 80)

            # 使用resolution作为最小阈值
            cur.execute("""
                UPDATE metric_rule_auto_baseline b
                SET flatline_eps = COALESCE(m.resolution, 0.01)
                FROM dim_metric_metadata m
                WHERE b.metric_id = m.metric_id
                  AND b.mad = 0
                  AND b.flatline_eps = 0
            """)

            updated_count = cur.rowcount
            print(f"  ✓ 更新了 {updated_count} 行基线数据的flatline_eps")
            print(f"  策略: flatline_eps = resolution（如果resolution为NULL则使用0.01）")
            
            # 步骤4：验证修复结果
            print("\n步骤4：验证修复结果")
            print("-" * 80)
            
            # 检查功率因数的resolution
            cur.execute("""
                SELECT 
                    metric_id,
                    resolution,
                    LEFT(remark, 100) as remark_preview
                FROM dim_metric_metadata
                WHERE metric_id = 10
            """)
            row = cur.fetchone()
            print(f"\n  功率因数元数据:")
            print(f"    metric_id: {row[0]}")
            print(f"    resolution: {row[1]}")
            print(f"    remark: {row[2]}")
            
            # 检查MAD=0的基线数据
            cur.execute("""
                SELECT
                    b.station_id,
                    b.device_id,
                    b.metric_id,
                    c.metric_key,
                    m.resolution,
                    b.median,
                    b.mad,
                    b.flatline_eps
                FROM metric_rule_auto_baseline b
                JOIN dim_metric_config c ON b.metric_id = c.id
                LEFT JOIN dim_metric_metadata m ON b.metric_id = m.metric_id
                WHERE b.mad = 0
                ORDER BY b.station_id, b.device_id, b.metric_id
            """)

            print(f"\n  MAD=0的基线数据（修复后）:")
            for row in cur.fetchall():
                print(f"\n    站点{row[0]} 设备{row[1]} 指标{row[2]} ({row[3]}):")
                print(f"      resolution: {row[4]}")
                print(f"      median: {row[5]}")
                print(f"      mad: {row[6]}")
                print(f"      flatline_eps: {row[7]} {'✅' if row[7] > 0 else '❌'}")
            
            # 步骤5：统计修复结果
            print("\n步骤5：统计修复结果")
            print("-" * 80)
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE mad = 0) as mad_zero_count,
                    COUNT(*) FILTER (WHERE mad = 0 AND flatline_eps > 0) as fixed_count
                FROM metric_rule_auto_baseline
            """)
            row = cur.fetchone()
            print(f"  总基线数据: {row[0]}")
            print(f"  MAD=0的数据: {row[1]}")
            print(f"  已修复的数据（flatline_eps>0）: {row[2]}")
            
            # 提交事务
            conn.commit()
    
    print("\n" + "=" * 80)
    print("  修复完成")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

