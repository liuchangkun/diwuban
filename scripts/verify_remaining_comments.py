#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证剩余对象的注释是否正确添加"""

import psycopg2

def main():
    """主函数"""
    # 连接数据库
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        database="pump_station_optimization"
    )

    cursor = conn.cursor()

    print("=" * 80)
    print("验证剩余对象的注释")
    print("=" * 80)

    # 验证表注释
    tables = [
        'completion_audit', 'completion_failures', 'completion_steps',
        'device_metric_candidates', 'dim_mapping_items',
        'quality_code_dict', 'quality_diagnosis_log', 'quality_eval_by_device_metric',
        'mv_metric_60s_stats', 'mv_presence_1s', 'mv_device_running_1s',
        'metrics_presence_per_second_device_legacy',
        'staging_raw', 'staging_rejects', 'metric_quality_rules',
        'calculation_method_registry', 'calculation_validation_config',
        'metrics_presence_per_second_device', 'dim_device_capabilities',
        'device_running_thresholds', 'pump_characteristic_curves', 'metric_anomaly_strategy',
        'device_running_thresholds_shadow', 'metric_quality_rules_shadow', 'metric_rule_auto_baseline_shadow'
    ]

    print("\n检查表注释...")
    for table in tables:
        cursor.execute(f"SELECT obj_description('public.{table}'::regclass, 'pg_class');")
        comment = cursor.fetchone()[0]
        if comment:
            has_r = '\r' in comment
            status = "❌ 有\\r换行符" if has_r else "✅"
            print(f"{status} {table}: {len(comment)} 字符")
        else:
            print(f"❌ {table}: 无注释")

    # 检查质量码字典是否完整
    print("\n检查质量码字典...")
    cursor.execute("SELECT obj_description('public.quality_code_dict'::regclass, 'pg_class');")
    comment = cursor.fetchone()[0]
    if comment:
        quality_codes = ['101', '111', '112', '121', '131', '132', '201', '401', '501', '502', '701', '711', '721', '731', '751']
        missing_codes = [code for code in quality_codes if code not in comment]
        if missing_codes:
            print(f"❌ 质量码字典不完整，缺少: {missing_codes}")
        else:
            print(f"✅ 质量码字典完整（15个质量码）")

    # 检查规则参数字典是否完整
    print("\n检查规则参数字典...")
    cursor.execute("SELECT obj_description('public.metric_quality_rules'::regclass, 'pg_class');")
    comment = cursor.fetchone()[0]
    if comment:
        rule_params = ['value_min', 'value_max', 'spike_abs', 'roc_abs', 'roc_ratio', 
                       'flatline_secs', 'flatline_eps', 'flatline_delta', 
                       'saturation_min', 'saturation_max', 'noise_stddev_max']
        missing_params = [param for param in rule_params if param not in comment]
        if missing_params:
            print(f"❌ 规则参数字典不完整，缺少: {missing_params}")
        else:
            print(f"✅ 规则参数字典完整（9类参数）")

    # 验证视图注释
    views = [
        'cagg_presence_per_second', 'station_device_rated_params_view',
        'metrics_availability_v_weekly', 'metrics_missing_v', 'mv_presence_1s_any',
        'v_coverage_gaps_1s', 'v_startstop_windows',
        'v_effective_metric_metadata', 'v_effective_metric_rules', 'v_quality_code_metric'
    ]

    print("\n检查视图注释...")
    for view in views:
        cursor.execute(f"SELECT obj_description('public.{view}'::regclass, 'pg_class');")
        comment = cursor.fetchone()[0]
        if comment:
            has_r = '\r' in comment
            status = "❌ 有\\r换行符" if has_r else "✅"
            print(f"{status} {view}: {len(comment)} 字符")
        else:
            print(f"❌ {view}: 无注释")

    # 验证函数注释
    functions = [
        'sp_mark_quality_window(timestamptz, timestamptz, bigint, bigint)',
        'sp_mark_quality_window_vfast(timestamptz, timestamptz, bigint, bigint, int[])',
        'sp_reset_quality_window(timestamptz, timestamptz, bigint, bigint)',
        'sp_generate_quality_eval_by_device_metric(timestamptz, timestamptz, bigint, bigint)',
        'sp_refresh_mv_running_presence(timestamptz, timestamptz, bigint, bigint)',
        'sp_refresh_mv_metric_60s_stats(timestamptz, timestamptz, bigint, bigint)',
        'sp_refresh_metric_rule_auto_baseline(integer, bigint, bigint)',
        'database_health_check()',
        'check_data_consistency()',
        'check_performance_alerts()'
    ]

    print("\n检查函数注释...")
    for func in functions:
        cursor.execute(f"SELECT obj_description('public.{func}'::regprocedure, 'pg_proc');")
        comment = cursor.fetchone()[0]
        if comment:
            has_r = '\r' in comment
            status = "❌ 有\\r换行符" if has_r else "✅"
            print(f"{status} {func}: {len(comment)} 字符")
        else:
            print(f"❌ {func}: 无注释")

    cursor.close()
    conn.close()

    print("\n" + "=" * 80)
    print("验证完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()

