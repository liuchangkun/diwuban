#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析可用指标和可计算的新指标
"""
from app.core.config.loader import load_settings
from app.adapters.db import get_connection, init_database
from pathlib import Path

def main():
    settings = load_settings(Path('configs'))
    init_database(settings)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. 获取所有已定义的指标
            cur.execute('''
                SELECT id, metric_key, unit_display, unit
                FROM dim_metric_config
                ORDER BY id
            ''')
            
            print('=' * 100)
            print('所有已定义的指标')
            print('=' * 100)
            all_metrics = cur.fetchall()
            for row in all_metrics:
                unit = row[2] or row[3] or ''
                print(f'{row[0]:3d}. {row[1]:45s} {unit}')
            
            # 2. 检查fact_measurements中有哪些指标有数据
            cur.execute('''
                SELECT 
                    dmc.metric_key,
                    dmc.unit_display,
                    COUNT(DISTINCT fm.device_id) as device_count,
                    COUNT(*) as record_count
                FROM fact_measurements fm
                JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
                WHERE fm.ts_bucket BETWEEN '2025-10-22 16:00:00' AND '2025-10-23 15:20:00'
                GROUP BY dmc.metric_key, dmc.unit_display
                ORDER BY dmc.metric_key
            ''')
            
            print('\n' + '=' * 100)
            print('fact_measurements中有数据的指标（2025-10-22 16:00 ~ 2025-10-23 15:20）')
            print('=' * 100)
            print(f'{"指标名称":50s} {"单位":15s} {"设备数":>8s} {"记录数":>12s}')
            print('-' * 100)
            
            available_metrics = {}
            for row in cur.fetchall():
                metric_key = row[0]
                unit = row[1] or ''
                device_count = row[2]
                record_count = row[3]
                available_metrics[metric_key] = {
                    'unit': unit,
                    'device_count': device_count,
                    'record_count': record_count
                }
                print(f'{metric_key:50s} {unit:15s} {device_count:8d} {record_count:12,d}')
            
            # 3. 分类指标
            print('\n' + '=' * 100)
            print('指标分类')
            print('=' * 100)
            
            # 原始传感器数据
            sensor_metrics = [k for k in available_metrics.keys() if not any(x in k for x in ['pump_flow_rate', 'pump_inlet_pressure', 'pump_head', 'pump_efficiency'])]
            
            # 已计算的指标
            calculated_metrics = [k for k in available_metrics.keys() if any(x in k for x in ['pump_flow_rate', 'pump_inlet_pressure', 'pump_head', 'pump_efficiency'])]
            
            print(f'\n原始传感器数据（{len(sensor_metrics)}个）:')
            for m in sorted(sensor_metrics):
                print(f'  - {m:45s} {available_metrics[m]["unit"]}')
            
            print(f'\n已计算的指标（{len(calculated_metrics)}个）:')
            for m in sorted(calculated_metrics):
                print(f'  - {m:45s} {available_metrics[m]["unit"]}')
            
            # 4. 分析可以计算的新指标
            print('\n' + '=' * 100)
            print('可以计算的新指标分析')
            print('=' * 100)
            
            # 检查是否有必要的数据
            has_power = 'pump_active_power' in available_metrics
            has_voltage = any('pump_voltage' in k for k in available_metrics.keys())
            has_current = any('pump_current' in k for k in available_metrics.keys())
            has_frequency = 'pump_frequency' in available_metrics
            has_flow = 'pump_flow_rate' in available_metrics
            has_head = 'pump_head' in available_metrics
            has_efficiency = 'pump_efficiency' in available_metrics
            has_inlet_pressure = 'pump_inlet_pressure' in available_metrics
            has_outlet_pressure = 'main_pipeline_outlet_pressure' in available_metrics
            has_power_factor = 'pump_power_factor' in available_metrics
            
            print('\n可用数据检查:')
            print(f'  ✓ 有功功率: {has_power}')
            print(f'  ✓ 电压: {has_voltage}')
            print(f'  ✓ 电流: {has_current}')
            print(f'  ✓ 频率: {has_frequency}')
            print(f'  ✓ 流量: {has_flow}')
            print(f'  ✓ 扬程: {has_head}')
            print(f'  ✓ 效率: {has_efficiency}')
            print(f'  ✓ 进口压力: {has_inlet_pressure}')
            print(f'  ✓ 出口压力: {has_outlet_pressure}')
            print(f'  ✓ 功率因数: {has_power_factor}')
            
            print('\n可以计算的新指标:')
            
            # 1. 视在功率
            if has_voltage and has_current:
                print('  1. pump_apparent_power（泵视在功率）')
                print('     公式: S = √3 × U × I')
                print('     依赖: pump_voltage_a/b/c, pump_current_a/b/c')
            
            # 2. 无功功率
            if has_power and has_power_factor:
                print('  2. pump_reactive_power（泵无功功率）')
                print('     公式: Q = P × tan(arccos(PF))')
                print('     依赖: pump_active_power, pump_power_factor')
            
            # 3. 比能耗
            if has_power and has_flow and has_head:
                print('  3. pump_specific_energy（泵比能耗）')
                print('     公式: e = P / (Q × H)')
                print('     依赖: pump_active_power, pump_flow_rate, pump_head')
            
            # 4. 轴功率
            if has_power:
                print('  4. pump_shaft_power（泵轴功率）')
                print('     公式: P_shaft = P_active / eta_motor')
                print('     依赖: pump_active_power, eta_motor（参数）')
            
            # 5. 水力功率
            if has_flow and has_head:
                print('  5. pump_hydraulic_power（泵水力功率）')
                print('     公式: P_h = ρ × g × Q × H / 3600')
                print('     依赖: pump_flow_rate, pump_head')
            
            # 6. 能耗统计
            if has_power:
                print('  6. pump_energy_consumption（泵能耗）')
                print('     公式: E = ∫ P dt（累计）')
                print('     依赖: pump_active_power')
            
            # 7. 运行时长
            print('  7. pump_running_hours（泵运行时长）')
            print('     公式: T = ∫ running dt（累计）')
            print('     依赖: running')

if __name__ == '__main__':
    main()

