"""
分析现有数据的质量（不重新计算）

功能：
1. 分析fact_measurements表中已有的7个指标数据
2. 执行4维度质量分析
3. 生成详细的质量分析报告
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List, Any
from collections import defaultdict

# 初始化数据库
from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings

settings = load_settings(Path("configs"))
init_database(settings)

def analyze_data_quality() -> Dict[str, Any]:
    """
    执行数据质量分析（4个维度）
    
    Returns:
        质量分析结果字典
    """
    print("\n" + "=" * 100)
    print("[数据质量分析 - 基于现有数据]")
    print("=" * 100)
    
    metrics = [
        "pump_flow_rate",
        "pump_inlet_pressure",
        "main_pipeline_inlet_pressure",
        "pump_head",
        "pump_efficiency",
        "pump_speed",
        "pump_torque",
    ]
    
    analysis_results = {}
    
    with get_connection() as conn:
        with conn.cursor() as cursor:
            for metric_key in metrics:
                print(f"\n[分析指标: {metric_key}]")
                print("-" * 100)
                
                # 维度1: 数据完整性分析
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT fm.device_id) as device_count,
                        COUNT(*) as record_count,
                        MIN(fm.ts_bucket) as earliest_time,
                        MAX(fm.ts_bucket) as latest_time,
                        COUNT(DISTINCT fm.ts_bucket) as unique_timestamps,
                        COUNT(DISTINCT DATE(fm.ts_bucket)) as unique_days
                    FROM fact_measurements fm
                    JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
                    WHERE dmc.metric_key = %s
                """, (metric_key,))
                
                completeness = cursor.fetchone()
                
                # 维度2: 数据合理性分析（按设备）
                cursor.execute("""
                    SELECT 
                        fm.device_id,
                        COUNT(*) as count,
                        ROUND(MIN(fm.value)::numeric, 6) as min_value,
                        ROUND(MAX(fm.value)::numeric, 6) as max_value,
                        ROUND(AVG(fm.value)::numeric, 6) as avg_value,
                        ROUND(STDDEV(fm.value)::numeric, 6) as stddev_value,
                        COUNT(CASE WHEN fm.value < 0 THEN 1 END) as negative_count,
                        COUNT(CASE WHEN fm.value = 0 THEN 1 END) as zero_count,
                        ROUND((COUNT(CASE WHEN fm.value = 0 THEN 1 END)::numeric / COUNT(*)::numeric * 100), 2) as zero_pct
                    FROM fact_measurements fm
                    JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
                    WHERE dmc.metric_key = %s
                    GROUP BY fm.device_id
                    ORDER BY fm.device_id
                """, (metric_key,))
                
                reasonableness = cursor.fetchall()
                
                # 维度3: 计算逻辑验证（查询使用的方法）
                cursor.execute("""
                    SELECT 
                        fm.device_id,
                        fm.source_hint,
                        COUNT(*) as count,
                        ROUND((COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY fm.device_id) * 100), 2) as pct
                    FROM fact_measurements fm
                    JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
                    WHERE dmc.metric_key = %s
                    GROUP BY fm.device_id, fm.source_hint
                    ORDER BY fm.device_id, count DESC
                """, (metric_key,))
                
                methods_used = cursor.fetchall()
                
                # 维度4: 参数配置验证
                cursor.execute("""
                    SELECT 
                        param_name,
                        param_value,
                        station_id,
                        device_id,
                        param_type,
                        updated_at,
                        updated_by
                    FROM calculation_parameters
                    WHERE metric_key = %s
                    ORDER BY 
                        CASE WHEN station_id IS NULL AND device_id IS NULL THEN 1
                             WHEN station_id IS NOT NULL AND device_id IS NULL THEN 2
                             ELSE 3 END,
                        param_name
                """, (metric_key,))
                
                parameters = cursor.fetchall()
                
                analysis_results[metric_key] = {
                    'completeness': completeness,
                    'reasonableness': reasonableness,
                    'methods_used': methods_used,
                    'parameters': parameters
                }
                
                # 打印详细结果
                if completeness:
                    print(f"  [完整性]")
                    print(f"    - 记录数: {completeness[1]:,}条")
                    print(f"    - 设备数: {completeness[0]}个")
                    print(f"    - 时间戳数: {completeness[4]:,}个")
                    print(f"    - 天数: {completeness[5]}天")
                    print(f"    - 时间范围: {completeness[2]} ~ {completeness[3]}")
                
                print(f"  [合理性]")
                for row in reasonableness:
                    device_id, count, min_val, max_val, avg_val, stddev_val, neg_count, zero_count, zero_pct = row
                    print(f"    - 设备{device_id}: {count:,}条, 范围[{min_val}, {max_val}], 均值{avg_val}, 标准差{stddev_val}, 零值{zero_pct}%")
                
                print(f"  [计算方法]")
                for row in methods_used:
                    device_id, method, count, pct = row
                    print(f"    - 设备{device_id}: {method} ({pct}%, {count:,}条)")
                
                print(f"  [参数配置]")
                if parameters:
                    for row in parameters:
                        param_name, param_value, station_id, device_id, param_type, updated_at, updated_by = row
                        scope = f"全局" if station_id is None and device_id is None else f"站点{station_id}" if device_id is None else f"设备{device_id}"
                        print(f"    - {param_name}={param_value} ({scope}, {param_type})")
                else:
                    print(f"    - 无参数配置")
    
    return analysis_results


def main():
    """主函数"""
    print("\n" + "=" * 100)
    print("[数据质量分析工具]")
    print("=" * 100)
    
    # 执行质量分析
    analysis_results = analyze_data_quality()
    
    print("\n" + "=" * 100)
    print("[OK] 分析完成！")
    print("=" * 100)


if __name__ == '__main__':
    main()

