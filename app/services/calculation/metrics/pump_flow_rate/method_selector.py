"""
方法选择器（MethodSelector）

职责：
- 根据数据可用性和条件，选择最合适的计算方法
- 按优先级顺序检查方法可用性
- 返回方法ID
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import pandas as pd
import logging


class MethodSelector:
    """
    方法选择器

    职责：
    - 根据数据可用性和条件选择最合适的计算方法
    - 按优先级顺序检查（100 → 90 → 80 → ...）
    """

    # 方法配置（按优先级从高到低）
    METHODS = [
        {
            'id': 'method_a',
            'name': '功率×频率分摊',
            'priority': 100,
            'dependencies': ['main_pipeline_flow_rate', 'pump_active_power', 'pump_frequency', 'other_devices'],
            'conditions': {'min_running_pumps': 2}
        },
        {
            'id': 'method_b',
            'name': '累计流量导数',
            'priority': 90,
            'dependencies': ['pump_cumulative_flow'],
            'conditions': {
                'cumulative_flow_valid': True,
                'enabled': False  # 临时禁用：数据源可能是主管道累计流量，而非单泵累计流量
            }
        },
        {
            'id': 'method_c',
            'name': '单泵直接取总管流量',
            'priority': 80,
            'dependencies': ['main_pipeline_flow_rate'],
            'conditions': {'exact_running_pumps': 1}
        },
        {
            'id': 'method_d',
            'name': '功率分摊',
            'priority': 70,
            'dependencies': ['main_pipeline_flow_rate', 'pump_active_power', 'other_devices'],
            'conditions': {'min_running_pumps': 2}
        },
        {
            'id': 'method_e',
            'name': '频率分摊',
            'priority': 60,
            'dependencies': ['main_pipeline_flow_rate', 'pump_frequency', 'other_devices'],
            'conditions': {'min_running_pumps': 2}
        },
        {
            'id': 'method_f',
            'name': '数据驱动回归',
            'priority': 50,
            'dependencies': [],
            'conditions': {'enabled': False}  # 暂时禁用
        },
        {
            'id': 'method_g',
            'name': '待机状态检测',
            'priority': 10,  # 最低优先级（仅在其他方法都不适用时使用）
            'dependencies': ['pump_active_power', 'pump_frequency'],
            'conditions': {
                'standby_mode': True  # 检测待机状态（power≈0 且 frequency≈0）
            }
        }
    ]

    def __init__(self, params: Optional[Dict[str, Any]] = None, trace_id: Optional[str] = None):
        """
        初始化方法选择器

        Args:
            params: 参数字典（包含standby_power_threshold, standby_freq_threshold等）
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id
        self.params = params or {}

    def select_method(self, data: pd.DataFrame) -> str:
        """
        选择计算方法（按优先级顺序）

        Args:
            data: 过滤后的数据

        Returns:
            方法ID（method_a 到 method_f）

        Raises:
            ValueError: 如果没有合适的方法
        """
        self.logger.info(
            "[方法选择] 开始选择计算方法",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '数据行数': len(data),
                '可用列': list(data.columns)
            }}
        )

        # 按优先级检查每个方法
        for method in self.METHODS:
            method_id = method['id']
            method_name = method['name']
            priority = method['priority']

            # 检查依赖
            dependencies_met = self._check_dependencies(data, method['dependencies'])

            # 检查条件
            conditions_met = self._check_conditions(data, method['conditions'])

            self.logger.debug(
                f"[方法选择] 检查方法: {method_name}",
                extra={'extra_data': {
                    '追踪ID': self.trace_id,
                    '方法ID': method_id,
                    'priority': priority,
                    'dependencies_met': dependencies_met,
                    'conditions_met': conditions_met
                }}
            )

            # 如果依赖和条件都满足，选择此方法
            if dependencies_met and conditions_met:
                self.logger.info(
                    f"[方法选择] 选择完成: {method_name}",
                    extra={'extra_data': {
                        '追踪ID': self.trace_id,
                        '选择的方法': method_id,
                        'method_name': method_name,
                        'priority': priority
                    }}
                )
                return method_id

        # 没有合适的方法
        error_msg = "没有找到合适的计算方法，所有方法的依赖或条件都不满足"
        self.logger.error(
            f"[方法选择] 失败: {error_msg}",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '数据行数': len(data),
                '可用列': list(data.columns)
            }}
        )
        raise ValueError(error_msg)


    def _check_dependencies(self, data: pd.DataFrame, dependencies: List[str]) -> bool:
        """
        检查数据依赖是否满足

        Args:
            data: 数据
            dependencies: 依赖的列名列表

        Returns:
            是否满足依赖
        """
        if not dependencies:
            return True

        for dep in dependencies:
            if dep == 'other_devices':
                # 检查是否有其他设备数据
                if 'other_devices' not in data.columns:
                    return False
                if data['other_devices'].isna().all():
                    return False
            else:
                # 检查列是否存在
                if dep not in data.columns:
                    return False
                # 检查列是否有有效值（非NaN）
                if data[dep].isna().all():
                    return False

        return True

    def _check_conditions(self, data: pd.DataFrame, conditions: Dict[str, Any]) -> bool:
        """
        检查运行条件是否满足

        Args:
            data: 数据
            conditions: 条件字典

        Returns:
            是否满足条件
        """
        if not conditions:
            return True

        # 检查是否禁用
        if 'enabled' in conditions and not conditions['enabled']:
            return False

        # 检查最小运行泵数
        if 'min_running_pumps' in conditions:
            running_pumps = self._count_running_pumps(data)
            min_required = conditions['min_running_pumps']
            if running_pumps < min_required:
                return False

        # 检查精确运行泵数
        if 'exact_running_pumps' in conditions:
            running_pumps = self._count_running_pumps(data)
            exact_required = conditions['exact_running_pumps']
            if running_pumps != exact_required:
                return False

        # 检查累计流量有效性
        if 'cumulative_flow_valid' in conditions:
            if not self._is_cumulative_flow_valid(data):
                return False

        # 检查待机状态（power≈0 且 frequency≈0）
        if 'standby_mode' in conditions and conditions['standby_mode']:
            if not self._is_standby_mode(data):
                return False

        return True

    def _count_running_pumps(self, data: pd.DataFrame) -> int:
        """
        统计运行中的泵数量

        逻辑：
        1. 当前设备算1台（数据已过滤 running=1）
        2. 统计 other_devices 中 running=1 的设备数

        注意：不使用硬编码阈值（f_thr, p_thr）

        Args:
            data: 数据（已过滤 running=1）

        Returns:
            运行泵数量
        """
        # 当前设备算1台（数据已在 DataFilter 阶段过滤 running=1）
        count = 1

        # 统计其他设备
        if 'other_devices' in data.columns and not data['other_devices'].isna().all():
            # 取第一行的 other_devices（假设同一时间窗口内设备数量不变）
            other_devices = data['other_devices'].iloc[0]
            if other_devices:
                # 统计 running=1 的设备
                running_device_ids = set()
                for record in other_devices:
                    device_id = record.get('device_id')
                    running = record.get('running', 0)

                    # 使用 running 字段判断（不使用硬编码阈值）
                    if running == 1:
                        running_device_ids.add(device_id)

                count += len(running_device_ids)

        return count

    def _is_cumulative_flow_valid(self, data: pd.DataFrame) -> bool:
        """
        检查累计流量是否有效

        Args:
            data: 数据

        Returns:
            累计流量是否有效
        """
        if 'pump_cumulative_flow' not in data.columns:
            return False

        cumulative_flow = data['pump_cumulative_flow']

        # 检查是否有有效值
        if cumulative_flow.isna().all():
            return False

        # 检查是否单调递增（累计流量应该递增）
        # 允许小幅波动（可能是传感器误差）
        valid_values = cumulative_flow.dropna()
        if len(valid_values) < 2:
            return False

        # 计算差分，检查是否大部分是正值
        diff = valid_values.diff().dropna()
        if len(diff) == 0:
            return False

        positive_ratio = (diff >= 0).sum() / len(diff)

        # 如果至少80%的差分是正值，认为累计流量有效
        return positive_ratio >= 0.8

    def _is_standby_mode(self, data: pd.DataFrame) -> bool:
        """
        检查是否处于待机状态（running=1 但 power≈0 且 frequency≈0）

        Args:
            data: 数据

        Returns:
            是否处于待机状态
        """
        # 检查必需列是否存在
        if 'pump_active_power' not in data.columns or 'pump_frequency' not in data.columns:
            return False

        # 从params获取阈值（禁止使用默认值）
        standby_power_threshold = self.params.get('standby_power_threshold')
        standby_freq_threshold = self.params.get('standby_freq_threshold')

        if standby_power_threshold is None or standby_freq_threshold is None:
            self.logger.error(
                "[方法选择] 待机状态检测缺少必需参数",
                extra={'extra_data': {
                    '追踪ID': self.trace_id,
                    'standby_power_threshold': standby_power_threshold,
                    'standby_freq_threshold': standby_freq_threshold,
                    '错误': '必须在calculation_parameters表中配置这些参数'
                }}
            )
            raise ValueError(
                f"待机状态检测缺少必需参数: standby_power_threshold={standby_power_threshold}, "
                f"standby_freq_threshold={standby_freq_threshold}. "
                f"必须在calculation_parameters表中配置: metric_key='pump_flow_rate', method_id='data_filter'"
            )

        # 检查是否所有数据点都满足待机条件
        power = data['pump_active_power']
        freq = data['pump_frequency']

        # 计算满足待机条件的数据点比例
        standby_mask = (power < standby_power_threshold) & (freq < standby_freq_threshold)
        standby_ratio = standby_mask.sum() / len(data) if len(data) > 0 else 0

        # 如果至少90%的数据点满足待机条件，认为处于待机状态
        is_standby = standby_ratio >= 0.9

        if is_standby:
            self.logger.info(
                "[方法选择] 检测到待机状态",
                extra={'extra_data': {
                    '追踪ID': self.trace_id,
                    'standby_ratio': f"{standby_ratio:.2%}",
                    'avg_power': f"{power.mean():.2f} kW",
                    'avg_freq': f"{freq.mean():.2f} Hz",
                    'standby_power_threshold': standby_power_threshold,
                    'standby_freq_threshold': standby_freq_threshold
                }}
            )

        return is_standby


