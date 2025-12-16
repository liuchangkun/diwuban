#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""直接通过Python添加数据库注释（使用参数化查询避免引号问题）"""

import psycopg2
import sys

def add_table_comment(cursor, table_name, comment):
    """添加表注释"""
    try:
        # 使用参数化查询避免引号问题
        cursor.execute(
            f"COMMENT ON TABLE {table_name} IS %s;",
            (comment,)
        )
        print(f"✅ 表注释已添加: {table_name}")
        return True
    except Exception as e:
        print(f"❌ 表注释添加失败 {table_name}: {e}")
        return False

def add_column_comment(cursor, table_name, column_name, comment):
    """添加字段注释"""
    try:
        cursor.execute(
            f"COMMENT ON COLUMN {table_name}.{column_name} IS %s;",
            (comment,)
        )
        return True
    except Exception as e:
        # 忽略字段不存在的错误
        if "does not exist" not in str(e):
            print(f"⚠️  字段注释添加失败 {table_name}.{column_name}: {e}")
        return False

def main():
    """主函数"""
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        database="pump_station_optimization"
    )
    
    cursor = conn.cursor()
    
    print("=" * 80)
    print("开始添加数据库注释（使用Python参数化查询）")
    print("=" * 80)
    
    success_count = 0
    fail_count = 0
    
    # =========================================================================
    # 表1: device_rated_params
    # =========================================================================
    
    comment = """
设备额定参数表

用途：
  存储每个设备的额定参数（如额定功率、额定流量、额定扬程等），用于计算流程中的参数加载。
  在5层参数优先级系统中处于第3层（global → global_default_rated → device_rated → station → device）。

参数粒度：
  - 设备级参数：每个设备可以有不同的额定参数
  - 支持时间有效性：通过 effective_from 和 effective_to 字段控制参数的有效期

📚 参数字典（按类型分类）：

【额定运行参数】
  • rated_frequency（额定频率）
    - 物理含义：设备的额定运行频率，用于计算泵的实际转速
    - 计算公式：n = (f / f_ref) × n_ref × (1 - slip)
      其中：n = 转速 (rpm)
           f = 实际频率 (Hz)
           f_ref = 额定频率 (Hz)
           n_ref = 额定转速 (rpm)
           slip = 电机转差率 (无量纲)
    - 单位：Hz
    - 典型值：50（中国）、60（美国）
    - 示例值：50.0
    - 用途：作为转速计算的参考频率，反映电网频率标准

  • poles_pair（极对数）
    - 物理含义：电机的极对数，决定电机的同步转速
    - 计算公式：n_sync = (60 × f) / p
      其中：n_sync = 同步转速 (rpm)
           f = 频率 (Hz)
           p = 极对数 (无量纲)
    - 单位：无量纲
    - 典型值：2（对应1500rpm@50Hz）、3（对应1000rpm@50Hz）
    - 示例值：2
    - 用途：计算电机的同步转速，用于转速计算

  • rated_efficiency（额定效率）
    - 物理含义：设备在额定工况下的效率
    - 计算公式：eta = P_out / P_in = (rho × g × Q × H) / (P_e × 1000)
      其中：eta = 效率 (无量纲)
           P_out = 输出功率 (W)
           P_in = 输入功率 (W)
           rho = 流体密度 (kg/m³)
           g = 重力加速度 (m/s²)
           Q = 流量 (m³/s)
           H = 扬程 (m)
           P_e = 电功率 (kW)
    - 单位：无量纲
    - 典型范围：0.60 ~ 0.85
    - 示例值：0.75
    - 用途：作为效率计算的参考值，用于性能评估

  • rated_flow（额定流量）
    - 物理含义：设备在额定工况下的流量
    - 单位：m³/h
    - 典型范围：100 ~ 1000（根据泵型号）
    - 示例值：400.0
    - 用途：作为流量计算的参考值，用于性能曲线拟合

  • rated_head（额定扬程）
    - 物理含义：设备在额定工况下的扬程
    - 单位：m
    - 典型范围：20 ~ 100（根据泵型号）
    - 示例值：50.0
    - 用途：作为扬程计算的参考值，用于性能曲线拟合

  • rated_power（额定功率）
    - 物理含义：设备的额定电功率
    - 单位：kW
    - 典型范围：50 ~ 500（根据泵型号）
    - 示例值：110.0
    - 用途：作为功率计算的参考值，用于能耗分析

【效率参数】
  • eta_motor（电机效率）
    - 物理含义：电机的效率，反映电能转换为机械能的效率
    - 计算公式：eta_pump = eta_measured / (eta_motor × eta_vfd)
      其中：eta_pump = 泵效率 (无量纲)
           eta_measured = 测量效率 (无量纲)
           eta_motor = 电机效率 (无量纲)
           eta_vfd = 变频器效率 (无量纲)
    - 单位：无量纲
    - 典型范围：0.85 ~ 0.95
    - 示例值：0.92
    - 用途：用于效率计算，将电功率转换为轴功率

  • eta_vfd（变频器效率）
    - 物理含义：变频器的效率，反映电能通过变频器的损耗
    - 单位：无量纲
    - 典型范围：0.95 ~ 0.98
    - 示例值：0.97
    - 用途：用于效率计算，考虑变频器的能量损耗

【管道参数】
  • pipe_diameter（管道直径）
    - 物理含义：与设备连接的管道内径
    - 单位：m
    - 典型范围：0.2 ~ 1.0
    - 示例值：0.5
    - 用途：用于流速计算和水力损失计算

  • pipe_length（管道长度）
    - 物理含义：管道的总长度
    - 单位：m
    - 典型范围：10 ~ 1000
    - 示例值：100.0
    - 用途：用于沿程损失计算

  • C_hazen（海曾-威廉系数）
    - 物理含义：管道粗糙度系数，用于海曾-威廉公式计算沿程损失
    - 计算公式：h_f = 10.67 × L × Q^1.852 / (C^1.852 × D^4.87)
      其中：h_f = 沿程损失 (m)
           L = 管道长度 (m)
           Q = 流量 (m³/s)
           C = 海曾-威廉系数 (无量纲)
           D = 管道直径 (m)
    - 单位：无量纲
    - 典型范围：100 ~ 140（新管道140，旧管道100）
    - 示例值：120
    - 用途：用于沿程损失计算

  • roughness_rel（相对粗糙度）
    - 物理含义：管道内壁的相对粗糙度，用于达西-魏斯巴赫公式计算沿程损失
    - 计算公式：epsilon_rel = epsilon / D
      其中：epsilon_rel = 相对粗糙度 (无量纲)
           epsilon = 绝对粗糙度 (m)
           D = 管道直径 (m)
    - 单位：无量纲
    - 典型范围：0.0001 ~ 0.01
    - 示例值：0.001
    - 用途：用于达西-魏斯巴赫公式计算摩擦系数

数据来源：
  - 设备铭牌：rated_frequency, poles_pair, rated_efficiency, rated_flow, rated_head, rated_power
  - 技术文档：eta_motor, eta_vfd
  - 现场测量：pipe_diameter, pipe_length, C_hazen, roughness_rel
  - SQL脚本导入：批量导入设备参数

更新机制：
  - 设备参数变更时手动更新
  - 支持时间有效性（effective_from, effective_to）
  - 新参数自动生效（effective_to IS NULL）
  - 旧参数自动失效（effective_to <= NOW()）

使用示例：
  -- 查询设备的所有有效额定参数
  SELECT param_key, value_numeric, unit
  FROM device_rated_params
  WHERE device_id = 1
    AND (effective_to IS NULL OR effective_to > NOW())
  ORDER BY param_key;
"""
    
    if add_table_comment(cursor, "device_rated_params", comment):
        success_count += 1
    else:
        fail_count += 1
    
    # 提交事务
    conn.commit()
    
    print("\n" + "=" * 80)
    print(f"注释添加完成！成功: {success_count}, 失败: {fail_count}")
    print("=" * 80)
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

