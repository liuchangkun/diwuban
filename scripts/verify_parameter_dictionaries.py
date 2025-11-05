#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证参数字典的完整性"""

import psycopg2
import sys

def verify_table_comment(cursor, table_name, expected_keywords):
    """验证表注释是否包含预期的关键词"""
    cursor.execute(
        "SELECT obj_description(%s::regclass, 'pg_class');",
        (f'public.{table_name}',)
    )
    result = cursor.fetchone()
    comment = result[0] if result and result[0] else ""
    
    print(f"\n{'='*80}")
    print(f"表: {table_name}")
    print(f"{'='*80}")
    print(f"注释长度: {len(comment)} 字符")
    
    missing_keywords = []
    found_keywords = []
    
    for keyword in expected_keywords:
        if keyword in comment:
            found_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)
    
    print(f"\n✅ 找到的关键词 ({len(found_keywords)}/{len(expected_keywords)}):")
    for kw in found_keywords[:10]:  # 只显示前10个
        print(f"  ✓ {kw}")
    if len(found_keywords) > 10:
        print(f"  ... 还有 {len(found_keywords) - 10} 个关键词")
    
    if missing_keywords:
        print(f"\n❌ 缺失的关键词 ({len(missing_keywords)}):")
        for kw in missing_keywords:
            print(f"  ✗ {kw}")
        return False
    else:
        print(f"\n✅ 所有关键词都已找到！")
        return True

def main():
    """主函数"""
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        database="pump_station_optimization"
    )
    
    cursor = conn.cursor()
    
    print("="*80)
    print("验证参数字典完整性")
    print("="*80)
    
    all_passed = True
    
    # 验证 calculation_parameters（20个参数）
    calc_params_keywords = [
        # 流量计算参数（4个）
        "alpha（流量系数）",
        "beta（频率权重指数）",
        "f_thr（频率阈值）",
        "p_thr（功率阈值）",
        # 扬程计算参数（3个）
        "rho（流体密度）",
        "g（重力加速度）",
        "b_H（扬程偏移量）",
        # 转速计算参数（6个）
        "f_ref（参考频率）",
        "n_ref（参考转速）",
        "slip（电机转差率）",
        "pole_pairs（极对数）",
        "calibration_a（标定斜率）",
        "calibration_b（标定截距）",
        # 效率计算参数（3个）
        "eta_motor（电机效率）",
        "eta_vfd（变频器效率）",
        "eta_max（最大效率）",
        # 压力系数化参数（4个）
        "k_pin（进口压力系数）",
        "b_pin（进口压力偏移量）",
        "b0, b1, b2, b3（PIN_COEF_V1方法系数）",
        # 扬程系数化参数（6个）
        "a0, a1, a2, a3, a4, a5（HEAD_COEF_V1方法系数）",
    ]
    
    if not verify_table_comment(cursor, "calculation_parameters", calc_params_keywords):
        all_passed = False
    
    # 验证 device_rated_params（12个参数）
    device_params_keywords = [
        # 额定运行参数（6个）
        "rated_frequency（额定频率）",
        "poles_pair（极对数）",
        "rated_efficiency（额定效率）",
        "rated_flow（额定流量）",
        "rated_head（额定扬程）",
        "rated_power（额定功率）",
        # 效率参数（2个）
        "eta_motor（电机效率）",
        "eta_vfd（变频器效率）",
        # 管道参数（4个）
        "pipe_diameter（管道直径）",
        "pipe_length（管道长度）",
        "C_hazen（海曾-威廉系数）",
        "roughness_rel（相对粗糙度）",
    ]
    
    if not verify_table_comment(cursor, "device_rated_params", device_params_keywords):
        all_passed = False
    
    # 验证 global_default_rated_params（8个参数）
    global_params_keywords = [
        # 额定运行参数（6个）
        "rated_frequency（额定频率）",
        "poles_pair（极对数）",
        "rated_efficiency（额定效率）",
        "rated_flow（额定流量）",
        "rated_head（额定扬程）",
        "rated_power（额定功率）",
        # 效率参数（2个）
        "eta_motor（电机效率）",
        "eta_vfd（变频器效率）",
    ]
    
    if not verify_table_comment(cursor, "global_default_rated_params", global_params_keywords):
        all_passed = False
    
    # 验证 fact_measurements（7个质量码）
    quality_codes_keywords = [
        "101 - 物理边界违规",
        "111 - 尖峰检测",
        "121 - 平线检测",
        "401 - 状态矛盾",
        "701 - 功率因数异常",
        "702 - 三相不平衡",
        "751 - 计数器单调性违规",
    ]
    
    # 验证字段注释（先获取列号）
    cursor.execute(
        """
        SELECT a.attnum
        FROM pg_attribute a
        WHERE a.attrelid = 'public.fact_measurements'::regclass
          AND a.attname = 'quality_codes';
        """
    )
    result = cursor.fetchone()
    if not result:
        print(f"\n❌ 字段 fact_measurements.quality_codes 不存在！")
        all_passed = False
        quality_codes_comment = ""
    else:
        col_num = result[0]
        cursor.execute(
            "SELECT col_description('public.fact_measurements'::regclass, %s);",
            (col_num,)
        )
        result = cursor.fetchone()
        quality_codes_comment = result[0] if result and result[0] else ""
    
    print(f"\n{'='*80}")
    print(f"字段: fact_measurements.quality_codes")
    print(f"{'='*80}")
    print(f"注释长度: {len(quality_codes_comment)} 字符")
    
    missing_codes = []
    found_codes = []
    
    for code in quality_codes_keywords:
        if code in quality_codes_comment:
            found_codes.append(code)
        else:
            missing_codes.append(code)
    
    print(f"\n✅ 找到的质量码 ({len(found_codes)}/{len(quality_codes_keywords)}):")
    for code in found_codes:
        print(f"  ✓ {code}")
    
    if missing_codes:
        print(f"\n❌ 缺失的质量码 ({len(missing_codes)}):")
        for code in missing_codes:
            print(f"  ✗ {code}")
        all_passed = False
    else:
        print(f"\n✅ 所有质量码都已找到！")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*80)
    if all_passed:
        print("✅ 所有参数字典验证通过！")
        print("="*80)
        return 0
    else:
        print("❌ 部分参数字典验证失败！")
        print("="*80)
        return 1

if __name__ == "__main__":
    sys.exit(main())

