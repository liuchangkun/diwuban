"""
单泵场景端到端测试

测试S1（单泵-变频）和S2（单泵-软启）场景的曲线拟合。
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import yaml

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.services.characteristic_curves.pipeline.curve_fitting_pipeline import CurveFittingPipeline
from app.services.characteristic_curves.shared import ResultStorage, ResultOutput
from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings
import pandas as pd
import numpy as np


def load_plot_config():
    """加载绘图配置"""
    config_path = project_root / "configs" / "visualization.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def extract_curve_data(device_id: int, curve_type: str, start_time: datetime, end_time: datetime):
    """从数据库提取曲线数据

    Args:
        device_id: 设备ID
        curve_type: 曲线类型 (qh, qp, qeta)
        start_time: 开始时间
        end_time: 结束时间

    Returns:
        tuple: (x_values, y_values) numpy数组
    """

    if curve_type == "qh":
        # Q-H曲线：流量-扬程
        sql = """
            SELECT
                fm.ts_bucket,
                MAX(CASE WHEN mc.metric_key = 'pump_flow_rate' THEN fm.value END) AS Q,
                MAX(CASE WHEN mc.metric_key = 'pump_head' THEN fm.value END) AS H
            FROM fact_measurements fm
            JOIN dim_metric_config mc ON mc.id = fm.metric_id
            WHERE fm.device_id = %(device_id)s
              AND fm.ts_bucket >= %(start_time)s
              AND fm.ts_bucket < %(end_time)s
              AND mc.metric_key IN ('pump_flow_rate', 'pump_head')
            GROUP BY fm.ts_bucket
            HAVING MAX(CASE WHEN mc.metric_key = 'pump_flow_rate' THEN fm.value END) IS NOT NULL
               AND MAX(CASE WHEN mc.metric_key = 'pump_head' THEN fm.value END) IS NOT NULL
            ORDER BY fm.ts_bucket
        """

    elif curve_type == "qp":
        # Q-P曲线：流量-功率
        sql = """
            SELECT
                fm.ts_bucket,
                MAX(CASE WHEN mc.metric_key = 'pump_flow_rate' THEN fm.value END) AS Q,
                MAX(CASE WHEN mc.metric_key = 'pump_active_power' THEN fm.value END) AS P
            FROM fact_measurements fm
            JOIN dim_metric_config mc ON mc.id = fm.metric_id
            WHERE fm.device_id = %(device_id)s
              AND fm.ts_bucket >= %(start_time)s
              AND fm.ts_bucket < %(end_time)s
              AND mc.metric_key IN ('pump_flow_rate', 'pump_active_power')
            GROUP BY fm.ts_bucket
            HAVING MAX(CASE WHEN mc.metric_key = 'pump_flow_rate' THEN fm.value END) IS NOT NULL
               AND MAX(CASE WHEN mc.metric_key = 'pump_active_power' THEN fm.value END) IS NOT NULL
            ORDER BY fm.ts_bucket
        """

    elif curve_type == "qeta":
        # Q-Eta曲线：流量-效率
        # 效率 = (ρ * g * Q * H) / (1000 * P)
        # 其中 ρ=1000 kg/m³, g=9.81 m/s²
        sql = """
            SELECT
                fm.ts_bucket,
                MAX(CASE WHEN mc.metric_key = 'pump_flow_rate' THEN fm.value END) AS Q,
                MAX(CASE WHEN mc.metric_key = 'pump_head' THEN fm.value END) AS H,
                MAX(CASE WHEN mc.metric_key = 'pump_active_power' THEN fm.value END) AS P
            FROM fact_measurements fm
            JOIN dim_metric_config mc ON mc.id = fm.metric_id
            WHERE fm.device_id = %(device_id)s
              AND fm.ts_bucket >= %(start_time)s
              AND fm.ts_bucket < %(end_time)s
              AND mc.metric_key IN ('pump_flow_rate', 'pump_head', 'pump_active_power')
            GROUP BY fm.ts_bucket
            HAVING MAX(CASE WHEN mc.metric_key = 'pump_flow_rate' THEN fm.value END) IS NOT NULL
               AND MAX(CASE WHEN mc.metric_key = 'pump_head' THEN fm.value END) IS NOT NULL
               AND MAX(CASE WHEN mc.metric_key = 'pump_active_power' THEN fm.value END) IS NOT NULL
               AND MAX(CASE WHEN mc.metric_key = 'pump_active_power' THEN fm.value END) > 0
            ORDER BY fm.ts_bucket
        """
    else:
        raise ValueError(f"不支持的曲线类型: {curve_type}")

    with get_connection() as conn:
        df = pd.read_sql(
            sql,
            conn,
            params={
                'device_id': device_id,
                'start_time': start_time,
                'end_time': end_time
            }
        )

    if df.empty:
        raise ValueError(f"未找到数据: device_id={device_id}, curve_type={curve_type}")

    print(f"  提取数据: {len(df)} 条记录")

    if curve_type == "qh":
        x_values = df['q'].values
        y_values = df['h'].values
    elif curve_type == "qp":
        x_values = df['q'].values
        y_values = df['p'].values
    elif curve_type == "qeta":
        # 计算效率
        Q = df['q'].values
        H = df['h'].values
        P = df['p'].values
        # Eta = (ρ * g * Q * H) / (1000 * P)
        # Q单位: m³/h, H单位: m, P单位: kW
        # 转换: Q (m³/h) = Q/3600 (m³/s)
        # Eta = (1000 * 9.81 * (Q/3600) * H) / (P * 1000)
        # Eta = (9.81 * Q * H) / (3600 * P)
        Eta = (9.81 * Q * H) / (3600 * P)
        x_values = Q
        y_values = Eta

    # 过滤无效值
    valid_mask = (x_values > 0) & (y_values > 0) & np.isfinite(x_values) & np.isfinite(y_values)
    x_values = x_values[valid_mask]
    y_values = y_values[valid_mask]

    print(f"  有效数据: {len(x_values)} 条记录")

    return x_values, y_values


def test_s1_vfd_single():
    """S1: 单泵-变频场景（device_id=1）"""
    
    print("=" * 80)
    print("S1: 单泵-变频场景测试")
    print("=" * 80)
    print()
    
    # 初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 创建输出目录
    output_dir = project_root / "特性曲线开发" / "端到端验证结果"
    reports_dir = output_dir / "reports"
    plots_dir = output_dir / "plots"
    reports_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    # 初始化管道组件
    storage = ResultStorage()
    output = ResultOutput(output_dir=reports_dir)
    plot_config = load_plot_config()
    
    # 创建管道
    pipeline = CurveFittingPipeline(
        result_storage=storage,
        result_output=output,
        plot_config=plot_config,
        output_dir=str(plots_dir)
    )
    
    # 时间范围（30天）
    time_range = (
        datetime(2025, 10, 22, 8, 0, 0, tzinfo=timezone.utc),
        datetime(2025, 11, 21, 8, 0, 0, tzinfo=timezone.utc)
    )
    
    # 测试3种曲线类型
    curve_types = ["qh", "qp", "qeta"]
    results = {}
    
    for curve_type in curve_types:
        print(f"\n{'=' * 80}")
        print(f"测试 S1 - {curve_type.upper()} 曲线")
        print(f"{'=' * 80}\n")
        
        try:
            # 提取数据
            x_values, y_values = extract_curve_data(
                device_id=1,
                curve_type=curve_type,
                start_time=time_range[0],
                end_time=time_range[1]
            )

            # 执行拟合
            result = pipeline.fit(
                device_id=1,
                curve_type=curve_type,
                time_range=time_range,
                x_values=x_values,
                y_values=y_values
            )

            results[curve_type] = result

            print(f"✅ {curve_type.upper()} 曲线拟合成功")
            print(f"   - 成功: {result.success}")
            print(f"   - R²: {result.r_squared:.4f}")
            print(f"   - 方法: {result.method_id}")
            print(f"   - 质量等级: {result.quality_grade}")

        except Exception as e:
            print(f"❌ {curve_type.upper()} 曲线拟合失败: {e}")
            import traceback
            traceback.print_exc()
            results[curve_type] = None
    
    print(f"\n{'=' * 80}")
    print("S1场景测试完成")
    print(f"{'=' * 80}\n")
    
    # 汇总结果
    success_count = sum(1 for r in results.values() if r and r.success)
    print(f"成功: {success_count}/3")
    print(f"失败: {3 - success_count}/3")
    
    return results


def test_s2_ss_single():
    """S2: 单泵-软启场景（device_id=7）"""
    
    print("\n" + "=" * 80)
    print("S2: 单泵-软启场景测试")
    print("=" * 80)
    print()
    
    # 初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 创建输出目录
    output_dir = project_root / "特性曲线开发" / "端到端验证结果"
    reports_dir = output_dir / "reports"
    plots_dir = output_dir / "plots"
    
    # 初始化管道组件
    storage = ResultStorage()
    output = ResultOutput(output_dir=reports_dir)
    plot_config = load_plot_config()
    
    # 创建管道
    pipeline = CurveFittingPipeline(
        result_storage=storage,
        result_output=output,
        plot_config=plot_config,
        output_dir=str(plots_dir)
    )
    
    # 时间范围（30天）
    time_range = (
        datetime(2025, 10, 22, 8, 0, 0, tzinfo=timezone.utc),
        datetime(2025, 11, 21, 8, 0, 0, tzinfo=timezone.utc)
    )
    
    # 测试3种曲线类型
    curve_types = ["qh", "qp", "qeta"]
    results = {}
    
    for curve_type in curve_types:
        print(f"\n{'=' * 80}")
        print(f"测试 S2 - {curve_type.upper()} 曲线")
        print(f"{'=' * 80}\n")
        
        try:
            # 提取数据
            x_values, y_values = extract_curve_data(
                device_id=7,
                curve_type=curve_type,
                start_time=time_range[0],
                end_time=time_range[1]
            )

            # 执行拟合
            result = pipeline.fit(
                device_id=7,
                curve_type=curve_type,
                time_range=time_range,
                x_values=x_values,
                y_values=y_values
            )

            results[curve_type] = result

            print(f"✅ {curve_type.upper()} 曲线拟合成功")
            print(f"   - 成功: {result.success}")
            print(f"   - R²: {result.r_squared:.4f}")
            print(f"   - 方法: {result.method_id}")
            print(f"   - 质量等级: {result.quality_grade}")

        except Exception as e:
            print(f"❌ {curve_type.upper()} 曲线拟合失败: {e}")
            import traceback
            traceback.print_exc()
            results[curve_type] = None
    
    print(f"\n{'=' * 80}")
    print("S2场景测试完成")
    print(f"{'=' * 80}\n")
    
    # 汇总结果
    success_count = sum(1 for r in results.values() if r and r.success)
    print(f"成功: {success_count}/3")
    print(f"失败: {3 - success_count}/3")
    
    return results


if __name__ == "__main__":
    # 执行S1场景测试
    s1_results = test_s1_vfd_single()
    
    # 执行S2场景测试
    s2_results = test_s2_ss_single()
    
    print("\n" + "=" * 80)
    print("所有单泵场景测试完成")
    print("=" * 80)

