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
    - 按优先级顺序检查（100 → 50）
    """

    # 方法配置（按优先级从高到低）
    METHODS = [
        {
            'id': 'equiv_coef',
            'name': '等效损失系数法',
            'priority': 100,
            'dependencies': ['pool_liquid_level', 'pump_flow_rate'],
            'conditions': {'has_device_params': ['L_offset', 'pipe_diameter']}
        },
        {
            'id': 'static_pressure',
            'name': '静压法',
            'priority': 50,
            'dependencies': ['pool_liquid_level'],
            'conditions': {'has_device_params': ['L_offset']}
        }
    ]

    def __init__(self, device_params: Dict[str, Any], trace_id: Optional[str] = None):
        """
        初始化方法选择器

        Args:
            device_params: 设备参数字典
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id
        self.device_params = device_params

    def select_method(self, data: pd.DataFrame) -> str:
        """
        选择计算方法（按优先级顺序）

        Args:
            data: 过滤后的数据

        Returns:
            方法ID（equiv_coef 或 static_pressure）

        Raises:
            ValueError: 如果没有合适的方法
        """
        self.logger.info(
            "[方法选择] 开始选择计算方法",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '数据行数': len(data),
                '可用列': list(data.columns),
                'device_params': list(self.device_params.keys())
            }}
        )

        # 按优先级检查每个方法
        failed_methods = []  # 记录失败的方法和原因

        for method in self.METHODS:
            method_id = method['id']
            method_name = method['name']
            priority = method['priority']

            # 检查依赖（返回详细信息）
            dependencies_met, missing_deps = self._check_dependencies_detailed(data, method['dependencies'])

            # 检查条件（返回详细信息）
            conditions_met, missing_conditions = self._check_conditions_detailed(method['conditions'])

            # 记录检查结果
            if not dependencies_met or not conditions_met:
                failed_methods.append({
                    'method_name': method_name,
                    '方法ID': method_id,
                    'priority': priority,
                    'missing_deps': missing_deps,
                    'missing_conditions': missing_conditions
                })

                self.logger.warning(
                    f"[方法选择] 方法不可用: {method_name}",
                    extra={'extra_data': {
                        '追踪ID': self.trace_id,
                        '方法ID': method_id,
                        'priority': priority,
                        'dependencies_met': dependencies_met,
                        'conditions_met': conditions_met,
                        'missing_data_columns': missing_deps,
                        'missing_device_params': missing_conditions
                    }}
                )
            else:
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

        # 没有合适的方法 - 提供详细的失败原因
        error_msg = "没有找到合适的计算方法，所有方法的依赖或条件都不满足"

        # 构建详细的错误信息
        failure_details = []
        for failed in failed_methods:
            details = f"方法[{failed['method_name']}]"
            if failed['missing_deps']:
                details += f" 缺少数据列: {', '.join(failed['missing_deps'])}"
            if failed['missing_conditions']:
                details += f" 缺少设备参数: {', '.join(failed['missing_conditions'])}"
            failure_details.append(details)

        self.logger.error(
            f"[方法选择] 失败: {error_msg}",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '数据行数': len(data),
                '可用列': list(data.columns),
                'device_params': list(self.device_params.keys()),
                'failure_details': failure_details
            }}
        )
        raise ValueError(error_msg)

    def _check_dependencies(self, data: pd.DataFrame, dependencies: List[str]) -> bool:
        """
        检查数据依赖是否满足（简化版，向后兼容）

        Args:
            data: 数据
            dependencies: 依赖的列名列表

        Returns:
            是否满足依赖
        """
        met, _ = self._check_dependencies_detailed(data, dependencies)
        return met

    def _check_dependencies_detailed(self, data: pd.DataFrame, dependencies: List[str]) -> tuple[bool, List[str]]:
        """
        检查数据依赖是否满足（详细版）

        Args:
            data: 数据
            dependencies: 依赖的列名列表

        Returns:
            (是否满足依赖, 缺失的列名列表)
        """
        if not dependencies:
            return True, []

        missing = []
        for dep in dependencies:
            # 检查列是否存在
            if dep not in data.columns:
                missing.append(f"{dep}(列不存在)")
            # 检查列是否有有效值（非NaN）
            elif data[dep].isna().all():
                missing.append(f"{dep}(全部为NaN)")

        return len(missing) == 0, missing

    def _check_conditions(self, conditions: Dict[str, Any]) -> bool:
        """
        检查运行条件是否满足（简化版，向后兼容）

        Args:
            conditions: 条件字典

        Returns:
            是否满足条件
        """
        met, _ = self._check_conditions_detailed(conditions)
        return met

    def _check_conditions_detailed(self, conditions: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        检查运行条件是否满足（详细版）

        Args:
            conditions: 条件字典

        Returns:
            (是否满足条件, 缺失的参数列表)
        """
        if not conditions:
            return True, []

        missing = []

        # 检查设备参数是否存在
        if 'has_device_params' in conditions:
            required_params = conditions['has_device_params']
            for param in required_params:
                if param not in self.device_params:
                    missing.append(f"{param}(参数不存在)")
                # 检查参数值是否有效（非None）
                elif self.device_params[param] is None:
                    missing.append(f"{param}(值为None)")

        return len(missing) == 0, missing

