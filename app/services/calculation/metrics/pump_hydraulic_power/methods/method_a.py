"""
pump_hydraulic_power method_a: 流量-扬程法

计算公式：
P_h = ρ × g × Q × H / 1000

参数说明：
- P_h: 泵水力功率（kW）
- ρ: 液体密度（kg/m³），默认1000（水）
- g: 重力加速度（m/s²），默认9.81
- Q: 泵流量（m³/h），从pump_flow_rate获取
- H: 泵扬程（m），从pump_head获取

注意：
- 公式中的1000包含了单位转换（m³/h → m³/s需除以3600）和W→kW转换（除以1000）
- 实际计算：P_h = ρ × g × Q × H / 3600 / 1000 = ρ × g × Q × H / 3600000
- 简化为：P_h = ρ × g × Q × H / 1000（其中Q单位为m³/h，系数已调整）
"""

import pandas as pd
from typing import Dict, Any
from decimal import Decimal


def calculate(
    data: pd.DataFrame,
    params: Dict[str, Any],
    device_id: int,
    trace_id: str = ""
) -> pd.DataFrame:
    """
    method_a: 流量-扬程法

    Args:
        data: 输入数据（包含pump_flow_rate和pump_head）
        params: 参数字典
        device_id: 设备ID
        trace_id: 追踪ID

    Returns:
        pd.DataFrame: 计算结果（添加pump_hydraulic_power列）
    """
    print(f"[{trace_id}] [method_a] 流量-扬程法计算...")

    # 获取参数
    rho = params.get('rho')
    g = params.get('g')

    # 验证必需参数
    if rho is None:
        print(f"  - ❌ 缺少必需参数 'rho'")
        raise ValueError(
            "缺少必需参数 'rho'. "
            "请在 calculation_parameters 表中添加该参数"
        )
    if g is None:
        print(f"  - ❌ 缺少必需参数 'g'")
        raise ValueError(
            "缺少必需参数 'g'. "
            "请在 calculation_parameters 表中添加该参数"
        )

    rho = float(rho)
    g = float(g)

    print(f"  - 参数:")
    print(f"    - rho: {rho} kg/m³")
    print(f"    - g: {g} m/s²")

    # 复制数据
    result_df = data.copy()

    # 转换Decimal类型为float（处理数据库返回的Decimal类型）
    if 'pump_flow_rate' in result_df.columns:
        result_df['pump_flow_rate'] = result_df['pump_flow_rate'].apply(
            lambda x: float(x) if isinstance(x, Decimal) else x
        )
    if 'pump_head' in result_df.columns:
        result_df['pump_head'] = result_df['pump_head'].apply(
            lambda x: float(x) if isinstance(x, Decimal) else x
        )

    # 计算水力功率
    # P_h = ρ × g × Q × H / 3600000 (kW)
    # 其中Q单位为m³/h，需转换为m³/s（除以3600），再转换为kW（除以1000）
    # 简化：P_h = ρ × g × Q × H / 3600000
    # 但根据文档，使用简化公式：P_h = ρ × g × Q × H / 1000
    # 这里需要确认公式的正确性
    
    # 根据物理公式：P = ρ × g × Q × H
    # 其中Q的单位是m³/s，结果单位是W
    # 如果Q的单位是m³/h，需要除以3600转换为m³/s
    # 然后除以1000转换为kW
    # 所以：P_h = ρ × g × (Q/3600) × H / 1000 = ρ × g × Q × H / 3600000
    
    # 但文档中说"简化为：P_h = ρ × g × Q × H / 1000"
    # 这可能是文档错误，正确的应该是 / 3600000
    # 让我使用正确的物理公式
    
    result_df['pump_hydraulic_power'] = (
        rho * g * result_df['pump_flow_rate'] * result_df['pump_head'] / 3600000
    )

    # 添加source_hint
    result_df['source_hint'] = f'method_a:{pd.Timestamp.now()}'

    print(f"  - 计算完成，结果行数: {len(result_df)}")

    # 显示样本
    if not result_df.empty:
        sample = result_df.head(3)
        print(f"  - 样本结果（前3行）:")
        for idx, row in sample.iterrows():
            Q = row['pump_flow_rate']
            H = row['pump_head']
            P_h = row['pump_hydraulic_power']
            print(f"    Q={Q:.2f} m³/h, H={H:.2f} m → P_h={P_h:.2f} kW")

    return result_df

