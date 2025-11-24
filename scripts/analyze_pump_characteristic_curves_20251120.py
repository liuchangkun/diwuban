#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析可以拟合的泵特性曲线
"""
from app.core.config.loader import load_settings
from app.adapters.db import get_connection, init_database
from pathlib import Path
import pandas as pd

def main():
    settings = load_settings(Path('configs'))
    init_database(settings)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. 查询设备信息
            cur.execute('''
                SELECT id, device_name, device_type, rated_power, rated_flow, rated_head
                FROM dim_device
                WHERE station_id = 1
                ORDER BY id
            ''')
            
            print('=' * 120)
            print('设备信息')
            print('=' * 120)
            print(f'ID   设备名称              设备类型              额定功率      额定流量      额定扬程')
            print('-' * 120)
            
            devices = {}
            for row in cur.fetchall():
                device_id = row[0]
                device_name = row[1] or ''
                device_type = row[2] or ''
                rated_power = row[3]
                rated_flow = row[4]
                rated_head = row[5]
                
                devices[device_id] = {
                    'name': device_name,
                    'type': device_type,
                    'rated_power': rated_power,
                    'rated_flow': rated_flow,
                    'rated_head': rated_head
                }
                
                power_str = f'{rated_power:.1f} kW' if rated_power else 'N/A'
                flow_str = f'{rated_flow:.1f} m³/h' if rated_flow else 'N/A'
                head_str = f'{rated_head:.1f} m' if rated_head else 'N/A'
                
                print(f'{device_id:4d} {device_name:20s} {device_type:20s} {power_str:>12s} {flow_str:>12s} {head_str:>12s}')
            
            # 2. 查询每个设备的数据量和工况范围
            print('\n' + '=' * 120)
            print('设备数据量和工况范围（2025-10-22 16:00 ~ 2025-10-23 15:20）')
            print('=' * 120)
            
            for device_id in devices.keys():
                cur.execute('''
                    SELECT 
                        COUNT(*) as total_count,
                        MIN(flow.value) as min_flow,
                        MAX(flow.value) as max_flow,
                        AVG(flow.value) as avg_flow,
                        MIN(head.value) as min_head,
                        MAX(head.value) as max_head,
                        AVG(head.value) as avg_head,
                        MIN(power.value) as min_power,
                        MAX(power.value) as max_power,
                        AVG(power.value) as avg_power,
                        MIN(freq.value) as min_freq,
                        MAX(freq.value) as max_freq,
                        AVG(freq.value) as avg_freq
                    FROM fact_measurements flow
                    LEFT JOIN fact_measurements head ON 
                        flow.device_id = head.device_id AND 
                        flow.ts_bucket = head.ts_bucket AND
                        head.metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_head')
                    LEFT JOIN fact_measurements power ON 
                        flow.device_id = power.device_id AND 
                        flow.ts_bucket = power.ts_bucket AND
                        power.metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_active_power')
                    LEFT JOIN fact_measurements freq ON 
                        flow.device_id = freq.device_id AND 
                        flow.ts_bucket = freq.ts_bucket AND
                        freq.metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_frequency')
                    WHERE flow.device_id = %s
                      AND flow.metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_flow_rate')
                      AND flow.ts_bucket BETWEEN '2025-10-22 16:00:00' AND '2025-10-23 15:20:00'
                      AND flow.value > 0
                ''', (device_id,))
                
                result = cur.fetchone()
                if result and result[0] > 0:
                    total_count = result[0]
                    min_flow, max_flow, avg_flow = result[1], result[2], result[3]
                    min_head, max_head, avg_head = result[4], result[5], result[6]
                    min_power, max_power, avg_power = result[7], result[8], result[9]
                    min_freq, max_freq, avg_freq = result[10], result[11], result[12]
                    
                    print(f'\n设备{device_id} - {devices[device_id]["name"]}:')
                    print(f'  数据点数: {total_count:,}')
                    print(f'  流量范围: {min_flow:.1f} ~ {max_flow:.1f} m³/h (平均: {avg_flow:.1f})')
                    print(f'  扬程范围: {min_head:.1f} ~ {max_head:.1f} m (平均: {avg_head:.1f})')
                    print(f'  功率范围: {min_power:.1f} ~ {max_power:.1f} kW (平均: {avg_power:.1f})')
                    print(f'  频率范围: {min_freq:.1f} ~ {max_freq:.1f} Hz (平均: {avg_freq:.1f})')
                    
                    # 判断泵类型
                    freq_variation = max_freq - min_freq
                    if freq_variation > 10:
                        pump_type = '变频泵'
                    elif freq_variation > 2:
                        pump_type = '软起变频泵'
                    else:
                        pump_type = '工频泵/软启泵'
                    
                    print(f'  推断类型: {pump_type} (频率变化: {freq_variation:.1f} Hz)')
            
            # 3. 分析可以拟合的特性曲线
            print('\n' + '=' * 120)
            print('可以拟合的特性曲线分析')
            print('=' * 120)
            
            print('\n基于现有数据，可以拟合以下特性曲线：')
            
            print('\n1. Q-H曲线（流量-扬程曲线）')
            print('   依赖数据: pump_flow_rate, pump_head')
            print('   拟合方法: 多项式拟合（2次或3次）')
            print('   公式: H = a₀ + a₁Q + a₂Q²')
            print('   应用: 预测不同流量下的扬程')
            
            print('\n2. Q-P曲线（流量-功率曲线）')
            print('   依赖数据: pump_flow_rate, pump_active_power')
            print('   拟合方法: 多项式拟合（2次或3次）')
            print('   公式: P = b₀ + b₁Q + b₂Q² + b₃Q³')
            print('   应用: 预测不同流量下的功率消耗')
            
            print('\n3. Q-η曲线（流量-效率曲线）')
            print('   依赖数据: pump_flow_rate, pump_efficiency')
            print('   拟合方法: 多项式拟合（2次或3次）')
            print('   公式: η = c₀ + c₁Q + c₂Q² + c₃Q³')
            print('   应用: 找到最佳效率点（BEP）')
            
            print('\n4. 相似定律曲线（变频泵）')
            print('   依赖数据: pump_flow_rate, pump_head, pump_frequency')
            print('   拟合方法: 相似定律变换')
            print('   公式: Q₁/Q₂ = n₁/n₂, H₁/H₂ = (n₁/n₂)², P₁/P₂ = (n₁/n₂)³')
            print('   应用: 预测不同转速下的性能')

if __name__ == '__main__':
    main()

