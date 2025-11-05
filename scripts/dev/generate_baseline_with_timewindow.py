#!/usr/bin/env python
"""
使用时间窗口生成自动基线数据
目的：为历史数据生成基线，避免 lookback_days 参数导致的时间窗口不匹配问题
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.core.config.loader import load_settings
from app.adapters.db import get_connection, init_database
from app.services.rules.auto_baseline import run_auto_baseline


def main():
    """主函数"""
    print("=" * 80)
    print("  使用时间窗口生成自动基线数据")
    print("=" * 80)
    
    # 加载配置
    settings = load_settings(Path("configs"))
    
    # 初始化数据库连接池
    init_database(settings)
    
    # 获取实际数据的时间范围
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT MIN(ts_bucket), MAX(ts_bucket)
                FROM public.fact_measurements
            """)
            row = cur.fetchone()
            data_start = row[0].isoformat() if row and row[0] else None
            data_end = row[1].isoformat() if row and row[1] else None
    
    print(f"\n实际数据时间范围: {data_start} ~ {data_end}")
    
    # 运行方案A（使用时间窗口版本）
    print(f"\n运行自动基线计算（方案A - robust方法）...")
    print(f"  时间窗口: {data_start} ~ {data_end}")
    print(f"  方法: win:robust_pcnt+mv")
    print(f"  版本: v070")
    
    try:
        result = run_auto_baseline(
            settings,
            start=data_start,
            end=data_end,
            station_id=None,
            device_id=None
        )
        print(f"\n✓ 自动基线计算成功")
        print(f"  结果: {result}")
    except Exception as e:
        print(f"\n✗ 自动基线计算失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 验证结果
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total_rows,
                    COUNT(DISTINCT station_id) as station_count,
                    COUNT(DISTINCT device_id) as device_count,
                    COUNT(DISTINCT metric_id) as metric_count,
                    AVG(p05) as avg_p05,
                    AVG(p95) as avg_p95,
                    AVG(median) as avg_median,
                    AVG(mad) as avg_mad,
                    AVG(spike_abs) as avg_spike_abs,
                    AVG(flatline_eps) as avg_flatline_eps
                FROM public.metric_rule_auto_baseline
            """)
            row = cur.fetchone()
            
            print(f"\n✓ 基线数据统计:")
            print(f"  - 总行数: {row[0]}")
            print(f"  - 站点数: {row[1]}")
            print(f"  - 设备数: {row[2]}")
            print(f"  - 指标数: {row[3]}")
            print(f"  - 平均p05: {row[4]:.6f}" if row[4] else "  - 平均p05: NULL")
            print(f"  - 平均p95: {row[5]:.6f}" if row[5] else "  - 平均p95: NULL")
            print(f"  - 平均median: {row[6]:.6f}" if row[6] else "  - 平均median: NULL")
            print(f"  - 平均MAD: {row[7]:.6f}" if row[7] else "  - 平均MAD: NULL")
            print(f"  - 平均spike_abs: {row[8]:.6f}" if row[8] else "  - 平均spike_abs: NULL")
            print(f"  - 平均flatline_eps: {row[9]:.6f}" if row[9] else "  - 平均flatline_eps: NULL")
    
    print("\n" + "=" * 80)
    print("  自动基线生成完成")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

