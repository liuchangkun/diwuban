#!/usr/bin/env python3
"""
刷新物化视图脚本

功能：
1. 刷新 mv_device_running_1s 物化视图
2. 验证物化视图数据
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def refresh_mv_device_running_1s(conn):
    """刷新 mv_device_running_1s 物化视图"""
    print("\n" + "="*80)
    print("刷新 mv_device_running_1s 物化视图")
    print("="*80)
    
    with conn.cursor() as cur:
        # 检查物化视图是否存在
        print("\n1. 检查物化视图是否存在...")
        cur.execute("""
            SELECT matviewname FROM pg_matviews
            WHERE schemaname = 'public' AND matviewname = 'mv_device_running_1s'
        """)
        
        if cur.fetchone() is None:
            print("  ⚠️ 物化视图不存在，尝试创建...")
            
            # 创建物化视图（基于 fn_running_state_1s 函数）
            cur.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_device_running_1s AS
                SELECT
                    device_id,
                    ts_bucket,
                    CASE
                        WHEN pump_active_power >= 0.5 AND pump_frequency >= 3.0 THEN 1
                        ELSE 0
                    END AS running
                FROM (
                    SELECT
                        device_id,
                        ts_bucket,
                        MAX(CASE WHEN metric_key = 'pump_active_power' THEN value END) AS pump_active_power,
                        MAX(CASE WHEN metric_key = 'pump_frequency' THEN value END) AS pump_frequency
                    FROM fact_measurements fm
                    JOIN dim_metrics dm ON fm.metric_id = dm.id
                    WHERE metric_key IN ('pump_active_power', 'pump_frequency')
                    GROUP BY device_id, ts_bucket
                ) sub
                WITH DATA;
                
                CREATE INDEX IF NOT EXISTS idx_mv_device_running_1s_device_ts
                ON mv_device_running_1s (device_id, ts_bucket);
            """)
            print("  ✅ 物化视图创建成功")
        else:
            print("  ✅ 物化视图已存在")
        
        # 刷新物化视图
        print("\n2. 刷新物化视图...")
        cur.execute("REFRESH MATERIALIZED VIEW mv_device_running_1s")
        print("  ✅ 刷新成功")
        
        # 验证数据
        print("\n3. 验证物化视图数据...")
        cur.execute("""
            SELECT device_id, COUNT(*) as count, SUM(running) as running_count
            FROM mv_device_running_1s
            WHERE device_id IN (105, 106, 107)
            GROUP BY device_id
            ORDER BY device_id
        """)
        
        results = cur.fetchall()
        if results:
            print("\n  设备运行状态统计:")
            print("  " + "-"*60)
            print(f"  {'设备ID':<10} {'总记录数':<15} {'运行记录数':<15} {'运行率':<10}")
            print("  " + "-"*60)
            for device_id, count, running_count in results:
                running_rate = (running_count / count * 100) if count > 0 else 0
                print(f"  {device_id:<10} {count:<15} {running_count:<15} {running_rate:.1f}%")
            print("  " + "-"*60)
        else:
            print("  ⚠️ 物化视图中没有测试设备的数据")
        
        conn.commit()
        print("\n✅ 物化视图刷新完成")


def main():
    """主函数"""
    print("\n" + "="*80)
    print("刷新物化视图脚本")
    print("="*80)
    
    # 加载配置
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    with get_connection() as conn:
        refresh_mv_device_running_1s(conn)
    
    print("\n" + "="*80)
    print("✅ 物化视图刷新完成！")
    print("="*80)
    print("\n下一步：")
    print("  1. 初始化参数: python tests/fixtures/init_calculation_parameters.py")
    print("  2. 运行测试: pytest tests/unit/services/calculation/ -v")
    print()


if __name__ == "__main__":
    main()

