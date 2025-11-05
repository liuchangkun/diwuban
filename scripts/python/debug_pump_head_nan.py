#!/usr/bin/env python3
"""
调试pump_head计算结果为NaN的问题

检查HEAD_COEF_V1方法所需的输入数据是否有效
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings


def check_input_data():
    """检查HEAD_COEF_V1方法的输入数据"""
    print("="*80)
    print("检查HEAD_COEF_V1方法的输入数据")
    print("="*80)
    
    # 查询设备129的关键指标数据
    query = """
    SELECT 
        dmc.metric_key,
        COUNT(*) as row_count,
        MIN(fm.value) as min_value,
        MAX(fm.value) as max_value,
        AVG(fm.value) as avg_value,
        COUNT(CASE WHEN fm.value IS NULL OR fm.value = 0 THEN 1 END) as zero_or_null_count
    FROM fact_measurements fm
    JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
    WHERE fm.device_id = 129
      AND fm.ts_bucket >= '2025-06-01 02:00:00+08'
      AND fm.ts_bucket < '2025-06-01 04:00:00+08'
      AND dmc.metric_key IN ('pump_inlet_pressure', 'pump_outlet_pressure', 'pool_liquid_level', 'pump_flow_rate')
    GROUP BY dmc.metric_key
    ORDER BY dmc.metric_key
    """
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
    
    print("\n设备129的关键指标数据统计:")
    print(f"{'指标':<35} {'数据量':<10} {'最小值':<15} {'最大值':<15} {'平均值':<15} {'零/空值':<10}")
    print("-" * 100)
    for row in results:
        metric_key, count, min_val, max_val, avg_val, zero_count = row
        print(
            f"{metric_key:<35} {count:<10} "
            f"{float(min_val) if min_val is not None else 'NULL':<15} "
            f"{float(max_val) if max_val is not None else 'NULL':<15} "
            f"{float(avg_val) if avg_val is not None else 'NULL':<15} "
            f"{zero_count:<10}"
        )


def check_head_coef_v1_params():
    """检查HEAD_COEF_V1方法的参数配置"""
    print("\n" + "="*80)
    print("检查HEAD_COEF_V1方法的参数配置")
    print("="*80)
    
    query = """
    SELECT param_name, param_value, is_optimizable, confidence_score
    FROM calculation_parameters
    WHERE method_id = 'HEAD_COEF_V1'
    ORDER BY param_name
    """
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
    
    if not results:
        print("\n❌ HEAD_COEF_V1方法没有配置参数！")
        return
    
    print(f"\n{'参数名':<15} {'参数值':<15} {'可优化':<10} {'置信度':<10}")
    print("-" * 50)
    for row in results:
        param_name, param_value, is_optimizable, confidence = row
        print(f"{param_name:<15} {float(param_value):<15.6f} {is_optimizable!s:<10} {float(confidence):<10.2f}")


def check_head_calculation_logic():
    """检查pump_head的计算逻辑"""
    print("\n" + "="*80)
    print("检查pump_head的计算逻辑")
    print("="*80)
    
    print("\nHEAD_COEF_V1方法的计算公式:")
    print("  H = a0 + a1 * head_out - a2 * level - a3 * (Q_i ** 2) - a4 * (Q_st ** 2) - a5 * Q_i")
    print("  其中: head_out = (P_out * 1e6) / (rho * g)")
    print("\n所需输入数据:")
    print("  - pump_outlet_pressure (P_out): 泵出口压力 [MPa]")
    print("  - pool_liquid_level (level): 水池液位 [m]")
    print("  - pump_flow_rate (Q_i): 泵流量 [m³/s]")
    print("  - main_pipeline_flow_rate (Q_st): 总管流量 [m³/s]")
    
    print("\n⚠️ 注意:")
    print("  - HEAD_COEF_V1方法不需要pump_inlet_pressure")
    print("  - 如果pump_outlet_pressure或pool_liquid_level缺失，计算结果将为NaN")


def check_actual_calculation():
    """检查实际计算过程"""
    print("\n" + "="*80)
    print("模拟HEAD_COEF_V1计算过程")
    print("="*80)
    
    # 查询一个时间点的数据
    query = """
    SELECT 
        dmc.metric_key,
        fm.value
    FROM fact_measurements fm
    JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
    WHERE fm.device_id = 129
      AND fm.ts_bucket = '2025-06-01 02:00:00+08'
      AND dmc.metric_key IN ('pump_outlet_pressure', 'pool_liquid_level', 'pump_flow_rate', 'main_pipeline_flow_rate')
    ORDER BY dmc.metric_key
    """
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
    
    data = {row[0]: float(row[1]) if row[1] is not None else None for row in results}
    
    print("\n时间点 2025-06-01 02:00:00+08 的数据:")
    for key, value in data.items():
        print(f"  {key}: {value}")
    
    # 查询参数
    query_params = """
    SELECT param_name, param_value
    FROM calculation_parameters
    WHERE method_id = 'HEAD_COEF_V1'
    """
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query_params)
            param_results = cur.fetchall()
    
    params = {row[0]: float(row[1]) for row in param_results}
    
    print("\nHEAD_COEF_V1参数:")
    for key, value in params.items():
        print(f"  {key}: {value}")
    
    # 模拟计算
    P_out = data.get('pump_outlet_pressure')
    level = data.get('pool_liquid_level')
    Q_i = data.get('pump_flow_rate')
    Q_st = data.get('main_pipeline_flow_rate')
    
    print("\n计算过程:")
    print(f"  P_out = {P_out} MPa")
    print(f"  level = {level} m")
    print(f"  Q_i = {Q_i} m³/s")
    print(f"  Q_st = {Q_st} m³/s")
    
    if P_out is None:
        print("\n❌ pump_outlet_pressure为空，无法计算！")
        return
    
    if level is None:
        print("\n❌ pool_liquid_level为空，无法计算！")
        return
    
    rho = params.get('rho', 1000.0)
    g = params.get('g', 9.81)
    a0 = params.get('a0', 0.0)
    a1 = params.get('a1', 1.0)
    a2 = params.get('a2', 1.0)
    a3 = params.get('a3', 0.0)
    a4 = params.get('a4', 0.0)
    a5 = params.get('a5', 0.0)
    
    head_out = (P_out * 1e6) / (rho * g)
    print(f"\n  head_out = (P_out * 1e6) / (rho * g) = ({P_out} * 1e6) / ({rho} * {g}) = {head_out:.2f} m")
    
    H = a0 + a1 * head_out - a2 * level
    if Q_i is not None:
        H -= a3 * (Q_i ** 2) + a5 * Q_i
    if Q_st is not None:
        H -= a4 * (Q_st ** 2)
    
    print(f"  H = a0 + a1*head_out - a2*level - a3*Q_i² - a4*Q_st² - a5*Q_i")
    print(f"    = {a0} + {a1}*{head_out:.2f} - {a2}*{level} - {a3}*{Q_i}² - {a4}*{Q_st}² - {a5}*{Q_i}")
    print(f"    = {H:.2f} m")
    
    print(f"\n✅ 计算结果: H = {H:.2f} m")


def main():
    """主函数"""
    # 初始化数据库
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    
    # 执行检查
    check_input_data()
    check_head_coef_v1_params()
    check_head_calculation_logic()
    check_actual_calculation()
    
    print("\n" + "="*80)
    print("调试完成")
    print("="*80)


if __name__ == "__main__":
    main()

