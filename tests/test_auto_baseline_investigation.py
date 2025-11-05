#!/usr/bin/env python
"""
自动基线计算深度调查测试
目的：对比方案A和方案B，找出为什么基线计算失败或产生异常结果

测试场景：
1. 方案A（存储过程）- 使用 robust_pcnt+meta+mv 方法
2. 方案B（Python STL）- 使用 stl_residual 方法
3. 对比两种方案的结果差异
4. 分析失败原因（数据不足、元数据缺失、算法问题等）
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from app.core.config.loader import load_settings
from app.adapters.db import get_connection, init_database
from app.services.rules.auto_baseline import run_auto_baseline
from app.services.rules.auto_baseline_b import run_auto_baseline_b


def print_section(title):
    """打印分隔线"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def check_prerequisites(conn):
    """检查前置条件"""
    print_section("前置条件检查")
    
    with conn.cursor() as cur:
        # 1. 检查 dim_metric_metadata 表
        cur.execute("SELECT COUNT(*) FROM public.dim_metric_metadata")
        metadata_count = cur.fetchone()[0]
        print(f"✓ dim_metric_metadata 表行数: {metadata_count}")
        if metadata_count == 0:
            print("  ⚠️  警告：元数据表为空，可能影响基线计算精度")
        
        # 2. 检查 v_effective_metric_metadata 视图
        cur.execute("SELECT COUNT(*) FROM public.v_effective_metric_metadata")
        view_count = cur.fetchone()[0]
        print(f"✓ v_effective_metric_metadata 视图行数: {view_count}")
        
        # 3. 检查 fact_measurements 表
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE quality_status = 0) as good_quality,
                MIN(ts_bucket) as earliest,
                MAX(ts_bucket) as latest
            FROM public.fact_measurements
        """)
        row = cur.fetchone()
        print(f"✓ fact_measurements 表:")
        print(f"  - 总行数: {row[0]}")
        print(f"  - 质量=0行数: {row[1]}")
        print(f"  - 时间范围: {row[2]} ~ {row[3]}")
        
        # 4. 检查 mv_device_running_1s 表
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE phase = 1) as phase_1,
                COUNT(*) FILTER (WHERE running = 1) as running_1,
                MIN(ts_bucket) as earliest,
                MAX(ts_bucket) as latest
            FROM public.mv_device_running_1s
        """)
        row = cur.fetchone()
        print(f"✓ mv_device_running_1s 表:")
        print(f"  - 总行数: {row[0]}")
        print(f"  - phase=1行数: {row[1]}")
        print(f"  - running=1行数: {row[2]}")
        print(f"  - 时间范围: {row[3]} ~ {row[4]}")
        
        # 5. 检查存储过程
        cur.execute("""
            SELECT COUNT(*) 
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE n.nspname = 'public' 
              AND p.proname = 'sp_refresh_metric_rule_auto_baseline'
        """)
        proc_count = cur.fetchone()[0]
        print(f"✓ 存储过程 sp_refresh_metric_rule_auto_baseline: {'存在' if proc_count > 0 else '不存在'}")
        
        return {
            'metadata_count': metadata_count,
            'view_count': view_count,
            'measurements_count': row[0] if row else 0,
            'phase_1_count': row[1] if row else 0,
            'has_procedure': proc_count > 0
        }


def test_method_a(settings, conn, data_start, data_end):
    """测试方案A：存储过程方法"""
    print_section("方案A：存储过程（robust_pcnt+meta+mv）")

    # 清空旧数据
    with conn.cursor() as cur:
        cur.execute("DELETE FROM public.metric_rule_auto_baseline")
        conn.commit()
        print("✓ 已清空 metric_rule_auto_baseline 表")

    # 运行方案A（使用时间窗口版本）
    print(f"\n运行方案A（时间窗口: {data_start} ~ {data_end}）...")
    try:
        result = run_auto_baseline(
            settings,
            start=data_start,
            end=data_end,
            station_id=None,
            device_id=None
        )
        print(f"✓ 方案A执行成功")
        print(f"  结果: {result}")
    except Exception as e:
        print(f"✗ 方案A执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 检查结果
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
        
        print(f"\n✓ 方案A结果统计:")
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
        
        # 显示前5行详细数据
        cur.execute("""
            SELECT 
                station_id, device_id, metric_id,
                p05, p95, median, mad,
                spike_abs, roc_abs, roc_ratio,
                flatline_eps, flatline_delta,
                method, version
            FROM public.metric_rule_auto_baseline
            ORDER BY station_id, device_id, metric_id
            LIMIT 5
        """)
        rows = cur.fetchall()
        
        if rows:
            print(f"\n✓ 前5行详细数据:")
            for i, row in enumerate(rows, 1):
                print(f"\n  [{i}] 站点{row[0]} 设备{row[1]} 指标{row[2]}")
                print(f"      p05={row[3]:.6f}, p95={row[4]:.6f}, median={row[5]:.6f}, mad={row[6]:.6f}")
                spike_abs_str = f"{row[7]:.6f}" if row[7] is not None else "NULL"
                roc_abs_str = f"{row[8]:.6f}" if row[8] is not None else "NULL"
                roc_ratio_str = f"{row[9]:.6f}" if row[9] is not None else "NULL"
                print(f"      spike_abs={spike_abs_str}, roc_abs={roc_abs_str}, roc_ratio={roc_ratio_str}")
                print(f"      flatline_eps={row[10]:.6f}, flatline_delta={row[11]:.6f}")
                print(f"      method={row[12]}, version={row[13]}")
        
        return {
            'total_rows': row[0],
            'avg_median': row[6],
            'avg_mad': row[7],
            'avg_flatline_eps': row[9]
        }


def test_method_b(settings, conn):
    """测试方案B：Python STL方法"""
    print_section("方案B：Python STL（stl_residual）")
    
    # 清空旧数据
    with conn.cursor() as cur:
        cur.execute("DELETE FROM public.metric_rule_auto_baseline_shadow")
        conn.commit()
        print("✓ 已清空 metric_rule_auto_baseline_shadow 表")
    
    # 运行方案B
    print("\n运行方案B...")
    try:
        result = run_auto_baseline_b(
            settings,
            lookback_days=30,
            station_id=None,
            device_id=None,
            method="stl_residual",
            version="vB_shadow"
        )
        print(f"✓ 方案B执行成功")
        print(f"  结果: {result}")
    except Exception as e:
        print(f"✗ 方案B执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 检查结果
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
            FROM public.metric_rule_auto_baseline_shadow
        """)
        row = cur.fetchone()
        
        print(f"\n✓ 方案B结果统计:")
        print(f"  - 总行数: {row[0]}")
        print(f"  - 站点数: {row[1]}")
        print(f"  - 设备数: {row[2]}")
        print(f"  - 指标数: {row[3]}")
        print(f"  - 平均p05: {row[4]:.6e}" if row[4] else "  - 平均p05: NULL")
        print(f"  - 平均p95: {row[5]:.6e}" if row[5] else "  - 平均p95: NULL")
        print(f"  - 平均median: {row[6]:.6e}" if row[6] else "  - 平均median: NULL")
        print(f"  - 平均MAD: {row[7]:.6e}" if row[7] else "  - 平均MAD: NULL")
        print(f"  - 平均spike_abs: {row[8]:.6e}" if row[8] else "  - 平均spike_abs: NULL")
        print(f"  - 平均flatline_eps: {row[9]:.6e}" if row[9] else "  - 平均flatline_eps: NULL")
        
        # 显示前5行详细数据
        cur.execute("""
            SELECT 
                station_id, device_id, metric_id,
                p05, p95, median, mad,
                spike_abs, roc_abs, roc_ratio,
                flatline_eps, flatline_delta,
                method, version, remark
            FROM public.metric_rule_auto_baseline_shadow
            ORDER BY station_id, device_id, metric_id
            LIMIT 5
        """)
        rows = cur.fetchall()
        
        if rows:
            print(f"\n✓ 前5行详细数据:")
            for i, row in enumerate(rows, 1):
                print(f"\n  [{i}] 站点{row[0]} 设备{row[1]} 指标{row[2]}")
                print(f"      p05={row[3]:.6e}, p95={row[4]:.6e}, median={row[5]:.6e}, mad={row[6]:.6e}")
                spike_abs_str = f"{row[7]:.6e}" if row[7] is not None else "NULL"
                roc_abs_str = f"{row[8]:.6e}" if row[8] is not None else "NULL"
                roc_ratio_str = f"{row[9]:.6f}" if row[9] is not None else "NULL"
                print(f"      spike_abs={spike_abs_str}, roc_abs={roc_abs_str}, roc_ratio={roc_ratio_str}")
                print(f"      flatline_eps={row[10]:.6e}, flatline_delta={row[11]:.6e}")
                print(f"      method={row[12]}, version={row[13]}, remark={row[14]}")
        
        return {
            'total_rows': row[0],
            'avg_median': row[6],
            'avg_mad': row[7],
            'avg_flatline_eps': row[9]
        }


def main():
    """主函数"""
    print_section("自动基线计算深度调查")
    print(f"测试时间: {datetime.now()}")

    # 加载配置
    settings = load_settings(Path("configs"))

    # 初始化数据库连接池
    init_database(settings)

    # 连接数据库
    with get_connection() as conn:
        # 1. 检查前置条件
        prereq = check_prerequisites(conn)

        # 获取实际数据的时间范围
        with conn.cursor() as cur:
            cur.execute("""
                SELECT MIN(ts_bucket), MAX(ts_bucket)
                FROM public.fact_measurements
            """)
            row = cur.fetchone()
            data_start = row[0].isoformat() if row and row[0] else None
            data_end = row[1].isoformat() if row and row[1] else None

        print(f"\n实际数据时间范围: {data_start} ~ {data_end}")

        # 2. 测试方案A（使用实际数据时间范围）
        result_a = test_method_a(settings, conn, data_start, data_end)

        # 3. 测试方案B
        result_b = test_method_b(settings, conn)
        
        # 4. 对比分析
        print_section("对比分析")
        
        if result_a and result_b:
            print(f"✓ 方案A生成 {result_a['total_rows']} 行数据")
            print(f"✓ 方案B生成 {result_b['total_rows']} 行数据")
            
            if result_a['avg_median'] and result_b['avg_median']:
                ratio = abs(result_a['avg_median'] / result_b['avg_median']) if result_b['avg_median'] != 0 else float('inf')
                print(f"\n数值对比:")
                print(f"  - 方案A平均median: {result_a['avg_median']:.6f}")
                print(f"  - 方案B平均median: {result_b['avg_median']:.6e}")
                print(f"  - 比值: {ratio:.2e}")
                
                if ratio > 1e10:
                    print(f"\n⚠️  警告：方案B的结果比方案A小 {ratio:.2e} 倍！")
                    print(f"  可能原因：")
                    print(f"    1. STL分解后残差接近0（数据太规律）")
                    print(f"    2. STL参数设置不当（period、seasonal等）")
                    print(f"    3. 数据量不足（需要至少2个周期）")
        
        elif result_a and not result_b:
            print(f"✓ 方案A成功生成 {result_a['total_rows']} 行数据")
            print(f"✗ 方案B执行失败")
        
        elif not result_a and result_b:
            print(f"✗ 方案A执行失败")
            print(f"✓ 方案B成功生成 {result_b['total_rows']} 行数据")
        
        else:
            print(f"✗ 两种方案都执行失败")
        
        # 5. 诊断建议
        print_section("诊断建议")
        
        if prereq['metadata_count'] == 0:
            print("⚠️  元数据表为空")
            print("   建议：执行 python scripts/dev/apply_metadata_migrations.py")
        
        if prereq['phase_1_count'] == 0:
            print("⚠️  没有稳态数据（phase=1）")
            print("   建议：检查 mv_device_running_1s 表的数据质量")
        
        if result_b and result_b['avg_median'] and abs(result_b['avg_median']) < 1e-10:
            print("⚠️  方案B结果异常（值太小）")
            print("   可能原因：STL分解后残差接近0")
            print("   建议：")
            print("     1. 检查原始数据是否有足够的变化")
            print("     2. 调整STL参数（period、seasonal）")
            print("     3. 考虑使用方案A（robust方法）")
    
    print_section("测试完成")


if __name__ == "__main__":
    main()

