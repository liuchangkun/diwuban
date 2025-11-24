#!/usr/bin/env python3
"""
端到端测试数据生成器

功能：
1. 创建测试设备（dim_devices、device_rated_params）
2. 生成符合真实特征的泵运行数据（30天）
3. 插入数据到fact_measurements表
4. 生成运行状态数据（确保通过数据过滤）
5. 扩展真实数据到30天
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import random
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection


class E2EDataGenerator:
    """端到端测试数据生成器"""
    
    # Metric ID映射（基于dim_metric_config表）
    METRIC_IDS = {
        'pump_frequency': 1,
        'pump_active_power': 8,
        'pump_flow_rate': 14,
        'pump_cumulative_flow': 15,
        'pump_head': 17,
        'main_pipeline_flow_rate': 62,  # 需要确认
        'pump_inlet_pressure': 13,
        'pump_outlet_pressure': 12,
    }
    
    def __init__(self, db_connection=None):
        """初始化生成器
        
        Args:
            db_connection: 数据库连接（可选，如不提供则自动创建）
        """
        self.conn = db_connection
        self._own_connection = db_connection is None
        
    def __enter__(self):
        if self._own_connection:
            self.conn = get_connection().__enter__()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._own_connection and self.conn:
            self.conn.__exit__(exc_type, exc_val, exc_tb)
    
    def create_test_devices(self, device_configs: List[Dict]) -> None:
        """创建测试设备
        
        Args:
            device_configs: 设备配置列表，每个配置包含：
                - device_id: 设备ID
                - name: 设备名称
                - pump_type: 泵类型（variable_frequency或soft_start）
                - rated_power: 额定功率（kW）
                - rated_flow: 额定流量（m³/h）
                - rated_head: 额定扬程（m）
                - rated_frequency: 额定频率（Hz）
        """
        with self.conn.cursor() as cur:
            for config in device_configs:
                # 插入设备到dim_devices
                cur.execute("""
                    INSERT INTO dim_devices (id, station_id, name, type, pump_type, is_active, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        type = EXCLUDED.type,
                        pump_type = EXCLUDED.pump_type,
                        is_active = EXCLUDED.is_active
                """, (
                    config['device_id'],
                    1,  # station_id固定为1
                    config['name'],
                    'pump',
                    config['pump_type'],
                    True
                ))
                
                # 删除旧的额定参数（如果存在）
                cur.execute("""
                    DELETE FROM device_rated_params
                    WHERE device_id = %s
                      AND param_key IN ('rated_power', 'rated_flow', 'rated_head', 'rated_frequency')
                """, (config['device_id'],))

                # 插入额定参数到device_rated_params
                rated_params = [
                    ('rated_power', config['rated_power'], 'kW'),
                    ('rated_flow', config['rated_flow'], 'm3/h'),
                    ('rated_head', config['rated_head'], 'm'),
                    ('rated_frequency', config['rated_frequency'], 'Hz'),
                ]

                for param_key, value, unit in rated_params:
                    cur.execute("""
                        INSERT INTO device_rated_params (device_id, param_key, value_numeric, unit, source, created_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                    """, (config['device_id'], param_key, value, unit, 'e2e_test_data'))
                
                # 插入运行阈值到device_running_thresholds（确保运行状态判断正常）
                # 变频泵：启用电流、功率、频率判断
                # 软启泵：启用电流、功率判断，禁用频率判断
                enable_f = config['pump_type'] == 'variable_frequency'
                
                cur.execute("""
                    INSERT INTO device_running_thresholds (
                        device_id, enable_i, enable_p, enable_f,
                        i_on, i_off, p_on, p_off, f_on, f_off,
                        grace_hold_secs, min_run_secs, min_stop_secs, smoothing_secs,
                        updated_by
                    ) VALUES (
                        %s, TRUE, TRUE, %s,
                        10, 5, %s, %s, %s, %s,
                        30, 10, 10, 5,
                        'e2e_data_generator'
                    )
                    ON CONFLICT (device_id) DO UPDATE SET
                        enable_i = EXCLUDED.enable_i,
                        enable_p = EXCLUDED.enable_p,
                        enable_f = EXCLUDED.enable_f,
                        i_on = EXCLUDED.i_on,
                        i_off = EXCLUDED.i_off,
                        p_on = EXCLUDED.p_on,
                        p_off = EXCLUDED.p_off,
                        f_on = EXCLUDED.f_on,
                        f_off = EXCLUDED.f_off,
                        updated_by = EXCLUDED.updated_by
                """, (
                    config['device_id'],
                    enable_f,
                    config['rated_power'] * 0.15,  # p_on: 15%额定功率
                    config['rated_power'] * 0.10,  # p_off: 10%额定功率
                    40.0 if enable_f else None,    # f_on: 40Hz（变频泵）
                    35.0 if enable_f else None,    # f_off: 35Hz（变频泵）
                ))
            
            self.conn.commit()
            print(f"✅ 成功创建 {len(device_configs)} 台测试设备")

    def generate_pump_data(
        self,
        device_id: int,
        start_time: datetime,
        end_time: datetime,
        rated_params: Dict,
        control_type: str,
        noise_level: float = 0.02,
        running_ratio: float = 0.8
    ) -> pd.DataFrame:
        """生成单台泵的运行数据

        Args:
            device_id: 设备ID
            start_time: 开始时间
            end_time: 结束时间
            rated_params: 额定参数字典（rated_power, rated_flow, rated_head, rated_frequency）
            control_type: 控制类型（'variable_frequency'或'soft_start'）
            noise_level: 噪声水平（默认2%）
            running_ratio: 运行时间占比（默认80%）

        Returns:
            DataFrame包含：ts_bucket, device_id, metric_id, value, running
        """
        print(f"\n生成设备 {device_id} 的运行数据...")
        print(f"  时间范围: {start_time} ~ {end_time}")
        print(f"  控制类型: {control_type}")

        # 生成时间序列（1秒间隔）
        total_seconds = int((end_time - start_time).total_seconds())
        timestamps = [start_time + timedelta(seconds=i) for i in range(total_seconds)]

        # 生成运行状态（80%运行，20%停机，避免频繁切换）
        running_states = self._generate_running_states(total_seconds, running_ratio)

        # 提取额定参数
        rated_power = rated_params['rated_power']
        rated_flow = rated_params['rated_flow']
        rated_head = rated_params['rated_head']
        rated_frequency = rated_params['rated_frequency']

        # 计算特性曲线参数
        H0 = rated_head * 1.2  # 零流量扬程
        K_h = (H0 - rated_head) / (rated_flow ** 2)  # 扬程系数
        P0 = rated_power * 0.2  # 空载功率
        K_p1 = (rated_power - P0) / rated_flow  # 功率一次系数
        K_p2 = 0.0001  # 功率二次系数

        # 生成数据
        data_records = []

        for i, (ts, running) in enumerate(zip(timestamps, running_states)):
            if running:
                # 运行状态：生成正常运行数据
                # 流量：在0.5~1.0倍额定流量之间变化（正弦波+噪声）
                base_flow_ratio = 0.75 + 0.25 * np.sin(2 * np.pi * i / 3600)  # 1小时周期
                flow = rated_flow * base_flow_ratio * (1 + np.random.normal(0, noise_level))
                flow = max(rated_flow * 0.2, min(rated_flow * 1.0, flow))  # 限制范围

                # 扬程：基于流量计算（H = H0 - K*Q²）
                head = H0 - K_h * (flow ** 2)
                head = head * (1 + np.random.normal(0, noise_level * 0.5))

                # 功率：基于流量计算（P = P0 + K1*Q + K2*Q²）
                power = P0 + K_p1 * flow + K_p2 * (flow ** 2)
                power = power * (1 + np.random.normal(0, noise_level * 1.5))
                power = max(rated_power * 0.15, min(rated_power * 1.1, power))  # 确保超过p_on阈值

                # 频率
                if control_type == 'variable_frequency':
                    # 变频泵：频率随流量变化（35~50Hz）
                    freq_ratio = flow / rated_flow
                    frequency = 35 + 15 * freq_ratio
                    frequency = frequency * (1 + np.random.normal(0, noise_level * 0.5))
                    frequency = max(35, min(50, frequency))  # 确保超过f_on阈值
                else:
                    # 软启泵：频率固定50Hz
                    frequency = rated_frequency

                # 累计流量（递增）
                cumulative_flow = (i / 3600.0) * flow  # 简化计算

            else:
                # 停机状态：所有值接近0
                flow = np.random.uniform(0, rated_flow * 0.05)
                head = np.random.uniform(0, rated_head * 0.05)
                power = np.random.uniform(0, rated_power * 0.08)  # 确保低于p_off阈值
                frequency = 0 if control_type == 'variable_frequency' else rated_frequency
                cumulative_flow = (i / 3600.0) * 0.01  # 几乎不变

            # 添加记录（每个指标一条记录）
            metrics_data = [
                (self.METRIC_IDS['pump_flow_rate'], flow),
                (self.METRIC_IDS['pump_head'], head),
                (self.METRIC_IDS['pump_active_power'], power),
                (self.METRIC_IDS['pump_frequency'], frequency),
                (self.METRIC_IDS['pump_cumulative_flow'], cumulative_flow),
            ]

            for metric_id, value in metrics_data:
                data_records.append({
                    'station_id': 1,
                    'device_id': device_id,
                    'metric_id': metric_id,
                    'ts_raw': ts,
                    'ts_bucket': ts,
                    'value': value,
                    'running': 1 if running else 0
                })

        df = pd.DataFrame(data_records)
        print(f"  ✅ 生成 {len(df)} 条记录（{total_seconds}秒 × 5指标）")
        print(f"  运行时间: {sum(running_states)}/{total_seconds}秒 ({sum(running_states)/total_seconds*100:.1f}%)")

        return df

    def _generate_running_states(self, total_seconds: int, running_ratio: float) -> List[int]:
        """生成运行状态序列（避免频繁切换）

        Args:
            total_seconds: 总秒数
            running_ratio: 运行时间占比

        Returns:
            运行状态列表（1=运行，0=停机）
        """
        # 生成运行段和停机段（每段至少持续10分钟）
        min_segment_seconds = 600  # 10分钟
        states = []
        current_time = 0
        current_state = 1  # 从运行状态开始

        while current_time < total_seconds:
            # 随机生成段长度（10分钟~2小时）
            segment_length = random.randint(min_segment_seconds, 7200)
            segment_length = min(segment_length, total_seconds - current_time)

            # 添加当前段
            states.extend([current_state] * segment_length)
            current_time += segment_length

            # 切换状态
            current_state = 1 - current_state

        # 调整运行时间占比
        actual_running = sum(states)
        target_running = int(total_seconds * running_ratio)

        if actual_running < target_running:
            # 需要增加运行时间：将部分停机段改为运行
            diff = target_running - actual_running
            for i in range(len(states)):
                if states[i] == 0 and diff > 0:
                    states[i] = 1
                    diff -= 1
        elif actual_running > target_running:
            # 需要减少运行时间：将部分运行段改为停机
            diff = actual_running - target_running
            for i in range(len(states)):
                if states[i] == 1 and diff > 0:
                    states[i] = 0
                    diff -= 1

        return states

    def insert_to_database(self, data: pd.DataFrame, batch_size: int = 10000) -> None:
        """批量插入数据到fact_measurements表

        Args:
            data: 数据DataFrame
            batch_size: 批次大小（默认10000）
        """
        print(f"\n插入数据到数据库...")
        print(f"  总记录数: {len(data)}")
        print(f"  批次大小: {batch_size}")

        total_batches = (len(data) + batch_size - 1) // batch_size

        with self.conn.cursor() as cur:
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min((batch_idx + 1) * batch_size, len(data))
                batch = data.iloc[start_idx:end_idx]

                # 准备批量插入数据
                values = []
                for _, row in batch.iterrows():
                    values.append((
                        int(row['station_id']),
                        int(row['device_id']),
                        int(row['metric_id']),
                        row['ts_raw'],
                        row['ts_bucket'],
                        float(row['value'])
                    ))

                # 批量插入（使用MD5哈希生成id）
                cur.executemany("""
                    INSERT INTO fact_measurements
                    (id, station_id, device_id, metric_id, ts_raw, ts_bucket, value, source_hint)
                    SELECT
                        abs(('x' || substr(md5(%s::text || '-' || %s::text || '-' || %s::text || '-' || %s::text), 1, 16))::bit(64)::bigint),
                        %s, %s, %s, %s, %s, %s, 'e2e_test_data'
                    ON CONFLICT (station_id, device_id, metric_id, ts_bucket) DO NOTHING
                """, [(
                    row[0], row[1], row[2], row[4],  # station_id, device_id, metric_id, ts_bucket for MD5
                    row[0], row[1], row[2], row[3], row[4], row[5]  # actual values
                ) for row in values])

                self.conn.commit()
                print(f"  进度: [{batch_idx + 1}/{total_batches}] 已插入 {end_idx}/{len(data)} 条记录")

        print(f"  ✅ 数据插入完成")

    def extend_real_data(
        self,
        device_id: int,
        real_end_time: datetime,
        target_end_time: datetime,
        rated_params: Dict,
        control_type: str,
        batch_size: int = 10000
    ) -> None:
        """扩展真实数据（基于最后一天的模式生成后续数据）

        Args:
            device_id: 设备ID
            real_end_time: 真实数据的结束时间
            target_end_time: 目标结束时间
            rated_params: 额定参数字典
            control_type: 控制类型
            batch_size: 批次大小
        """
        print(f"\n扩展设备 {device_id} 的真实数据...")
        print(f"  真实数据结束时间: {real_end_time}")
        print(f"  目标结束时间: {target_end_time}")

        # 生成扩展数据
        extended_data = self.generate_pump_data(
            device_id=device_id,
            start_time=real_end_time,
            end_time=target_end_time,
            rated_params=rated_params,
            control_type=control_type,
            noise_level=0.02,
            running_ratio=0.8
        )

        # 插入到数据库
        self.insert_to_database(extended_data, batch_size=batch_size)

        print(f"  ✅ 数据扩展完成")

    def refresh_running_state_view(self, device_ids: List[int]) -> None:
        """刷新运行状态物化视图

        Args:
            device_ids: 设备ID列表
        """
        print(f"\n刷新运行状态物化视图...")

        with self.conn.cursor() as cur:
            for device_id in device_ids:
                # 调用存储过程刷新mv_device_running_1s
                # 注意：这里需要根据实际的存储过程名称调整
                try:
                    cur.execute("""
                        SELECT public.fn_running_state_1s(
                            (SELECT station_id FROM dim_devices WHERE id = %s),
                            %s,
                            (SELECT MIN(ts_bucket) FROM fact_measurements WHERE device_id = %s),
                            (SELECT MAX(ts_bucket) FROM fact_measurements WHERE device_id = %s)
                        )
                    """, (device_id, device_id, device_id, device_id))

                    print(f"  ✅ 设备 {device_id} 运行状态已刷新")
                except Exception as e:
                    print(f"  ⚠️ 设备 {device_id} 运行状态刷新失败: {e}")

            self.conn.commit()

        print(f"  ✅ 运行状态刷新完成")


# 便捷函数
def create_e2e_test_data():
    """创建端到端测试数据的便捷函数"""
    with E2EDataGenerator() as generator:
        # 定义设备配置
        device_configs = [
            # 设备7-9: 同构软启泵组
            {'device_id': 7, 'name': '测试泵7#（软启）', 'pump_type': 'soft_start',
             'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50},
            {'device_id': 8, 'name': '测试泵8#（软启）', 'pump_type': 'soft_start',
             'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50},
            {'device_id': 9, 'name': '测试泵9#（软启）', 'pump_type': 'soft_start',
             'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50},

            # 设备10-12: 异构变频泵组
            {'device_id': 10, 'name': '测试泵10#（变频-75kW）', 'pump_type': 'variable_frequency',
             'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50},
            {'device_id': 11, 'name': '测试泵11#（变频-90kW）', 'pump_type': 'variable_frequency',
             'rated_power': 90, 'rated_flow': 480, 'rated_head': 25, 'rated_frequency': 50},
            {'device_id': 12, 'name': '测试泵12#（变频-110kW）', 'pump_type': 'variable_frequency',
             'rated_power': 110, 'rated_flow': 550, 'rated_head': 25, 'rated_frequency': 50},

            # 设备13-15: 异构软启泵组
            {'device_id': 13, 'name': '测试泵13#（软启-75kW）', 'pump_type': 'soft_start',
             'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50},
            {'device_id': 14, 'name': '测试泵14#（软启-90kW）', 'pump_type': 'soft_start',
             'rated_power': 90, 'rated_flow': 480, 'rated_head': 25, 'rated_frequency': 50},
            {'device_id': 15, 'name': '测试泵15#（软启-110kW）', 'pump_type': 'soft_start',
             'rated_power': 110, 'rated_flow': 550, 'rated_head': 25, 'rated_frequency': 50},

            # 设备16-18: 混合泵组
            {'device_id': 16, 'name': '测试泵16#（变频-75kW）', 'pump_type': 'variable_frequency',
             'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50},
            {'device_id': 17, 'name': '测试泵17#（变频-90kW）', 'pump_type': 'variable_frequency',
             'rated_power': 90, 'rated_flow': 480, 'rated_head': 25, 'rated_frequency': 50},
            {'device_id': 18, 'name': '测试泵18#（软启-75kW）', 'pump_type': 'soft_start',
             'rated_power': 75, 'rated_flow': 400, 'rated_head': 25, 'rated_frequency': 50},
        ]

        # 创建设备
        generator.create_test_devices(device_configs)

        # 生成30天数据
        start_time = datetime(2025, 10, 22, 8, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 21, 8, 0, 0, tzinfo=timezone.utc)

        for config in device_configs:
            # 生成数据
            data = generator.generate_pump_data(
                device_id=config['device_id'],
                start_time=start_time,
                end_time=end_time,
                rated_params={
                    'rated_power': config['rated_power'],
                    'rated_flow': config['rated_flow'],
                    'rated_head': config['rated_head'],
                    'rated_frequency': config['rated_frequency'],
                },
                control_type=config['pump_type'],
                noise_level=0.02,
                running_ratio=0.8
            )

            # 插入数据库
            generator.insert_to_database(data)

        # 刷新运行状态
        device_ids = [c['device_id'] for c in device_configs]
        generator.refresh_running_state_view(device_ids)

        print("\n" + "="*80)
        print("✅ 端到端测试数据创建完成！")
        print("="*80)


if __name__ == '__main__':
    create_e2e_test_data()

