"""
泵组验证器 (app.services.characteristic_curves.pump_group.pump_group_validator)

本模块提供泵组配置和数据验证功能：
- 泵组配置验证（泵数量、类型、参数）
- 数据完整性检查（曲线注册、频率数据）
- 物理一致性验证（曲线参数、功率范围）

版本: v1.0
更新日期: 2025-12-09
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
import logging

from app.services.characteristic_curves.models import GroupProcessingStrategy


@dataclass
class ValidationResult:
    """验证结果"""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, message: str) -> None:
        """添加错误"""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """添加警告"""
        self.warnings.append(message)

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """合并另一个验证结果"""
        return ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
            details={**self.details, **other.details},
        )


class PumpGroupValidator:
    """
    泵组验证器

    职责：
    1. 泵组配置验证（泵数量、类型、参数）
    2. 数据完整性检查（曲线注册、频率数据）
    3. 物理一致性验证（曲线参数、功率范围）
    """

    # 验证阈值常量
    MIN_PUMPS = 1
    MAX_PUMPS = 10
    MIN_RATED_POWER = 1.0  # kW
    MAX_RATED_POWER = 1000.0  # kW
    POWER_DIFF_THRESHOLD = 0.10  # 功率差异阈值（10%）
    FREQ_DIFF_THRESHOLD = 2.0  # 频率差异阈值（Hz）

    def __init__(self):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def validate_group_config(
        self, pump_infos: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        验证泵组配置

        Args:
            pump_infos: 泵信息列表
                格式: [{'pump_id': int, 'rated_power': float, 'control_type': str}, ...]

        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult(is_valid=True)

        # 1. 检查泵数量
        n_pumps = len(pump_infos)
        if n_pumps < self.MIN_PUMPS:
            result.add_error(f"泵数量不足：{n_pumps} < {self.MIN_PUMPS}")
        if n_pumps > self.MAX_PUMPS:
            result.add_error(f"泵数量超限：{n_pumps} > {self.MAX_PUMPS}")

        # 2. 检查泵ID唯一性
        pump_ids = [p.get("pump_id") for p in pump_infos]
        if len(pump_ids) != len(set(pump_ids)):
            result.add_error("存在重复的泵ID")

        # 3. 检查必需字段
        required_fields = ["pump_id", "rated_power", "control_type"]
        for i, info in enumerate(pump_infos):
            missing = [f for f in required_fields if f not in info]
            if missing:
                result.add_error(f"泵[{i}]缺少必需字段: {missing}")

        # 4. 检查控制类型
        valid_control_types = {"VFD", "SS"}
        for info in pump_infos:
            ct = info.get("control_type")
            if ct and ct not in valid_control_types:
                result.add_error(f"无效的控制类型: {ct}，应为 VFD 或 SS")

        # 5. 检查额定功率范围
        for info in pump_infos:
            power = info.get("rated_power", 0)
            if power < self.MIN_RATED_POWER:
                result.add_error(
                    f"泵{info.get('pump_id')}额定功率过低: {power}kW"
                )
            if power > self.MAX_RATED_POWER:
                result.add_error(
                    f"泵{info.get('pump_id')}额定功率过高: {power}kW"
                )

        result.details["n_pumps"] = n_pumps
        result.details["pump_ids"] = pump_ids

        self._logger.info(
            f"[配置验证] n_pumps={n_pumps}, is_valid={result.is_valid}, "
            f"errors={len(result.errors)}, warnings={len(result.warnings)}"
        )
        return result

    def validate_data_completeness(
        self,
        pump_ids: List[int],
        curve_registry: Any,
        freq_provider: Optional[Any] = None,
    ) -> ValidationResult:
        """
        验证数据完整性

        Args:
            pump_ids: 泵ID列表
            curve_registry: 曲线注册表实例
            freq_provider: 频率数据提供器实例（可选）

        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult(is_valid=True)

        # 1. 检查曲线注册
        missing_curves = []
        for pump_id in pump_ids:
            if not curve_registry.has_curve(pump_id, "qh"):
                missing_curves.append(pump_id)

        if missing_curves:
            result.add_error(f"以下泵缺少Q-H曲线注册: {missing_curves}")

        result.details["missing_curves"] = missing_curves
        result.details["registered_count"] = len(pump_ids) - len(missing_curves)

        self._logger.info(
            f"[数据完整性] pumps={pump_ids}, "
            f"missing_curves={missing_curves}, is_valid={result.is_valid}"
        )
        return result

    def validate_physics_consistency(
        self,
        pump_infos: List[Dict[str, Any]],
        group_type: GroupProcessingStrategy,
    ) -> ValidationResult:
        """
        验证物理一致性

        Args:
            pump_infos: 泵信息列表
            group_type: 泵组类型

        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult(is_valid=True)

        if len(pump_infos) < 2:
            return result

        # 1. 计算功率差异
        powers = [p.get("rated_power", 0) for p in pump_infos]
        max_power = max(powers)
        min_power = min(powers)
        power_diff = (max_power - min_power) / max_power if max_power > 0 else 0

        result.details["power_diff"] = power_diff
        result.details["max_power"] = max_power
        result.details["min_power"] = min_power

        # 2. 根据泵组类型验证功率差异
        is_homogeneous = group_type in (
            GroupProcessingStrategy.HOMOGENEOUS_GROUP,
            GroupProcessingStrategy.VFD_HETEROGENEOUS_FREQ,
        )

        if is_homogeneous and power_diff >= self.POWER_DIFF_THRESHOLD:
            result.add_warning(
                f"同构泵组功率差异 {power_diff:.1%} >= {self.POWER_DIFF_THRESHOLD:.0%}，"
                "建议检查泵组分类"
            )

        # 3. 检查混合泵组的控制类型
        control_types = set(p.get("control_type") for p in pump_infos)
        is_mixed = group_type in (
            GroupProcessingStrategy.MIXED_GROUP,
            GroupProcessingStrategy.MIXED_HETEROGENEOUS,
        )

        if is_mixed and len(control_types) < 2:
            result.add_error(
                f"混合泵组应包含VFD和SS两种控制类型，当前只有: {control_types}"
            )

        if not is_mixed and len(control_types) > 1:
            result.add_warning(
                f"非混合泵组包含多种控制类型: {control_types}，建议检查泵组分类"
            )

        result.details["control_types"] = list(control_types)

        self._logger.info(
            f"[物理一致性] group_type={group_type.value}, "
            f"power_diff={power_diff:.2%}, control_types={control_types}, "
            f"is_valid={result.is_valid}"
        )
        return result

    def validate_curve_parameters(
        self,
        pump_ids: List[int],
        curve_registry: Any,
    ) -> ValidationResult:
        """
        验证曲线参数一致性

        Args:
            pump_ids: 泵ID列表
            curve_registry: 曲线注册表实例

        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult(is_valid=True)

        h0_values = []
        k_values = []

        for pump_id in pump_ids:
            entry = curve_registry.get_entry(pump_id, "qh")
            if entry:
                if entry.h0 is not None:
                    h0_values.append(entry.h0)
                if entry.k is not None:
                    k_values.append(entry.k)

        # 检查H0一致性
        if len(h0_values) >= 2:
            h0_max = max(h0_values)
            h0_min = min(h0_values)
            h0_diff = (h0_max - h0_min) / h0_max if h0_max > 0 else 0

            if h0_diff > 0.20:  # 20%差异
                result.add_warning(
                    f"曲线H0差异较大: {h0_diff:.1%}，可能影响并联合成精度"
                )
            result.details["h0_diff"] = h0_diff
            result.details["h0_values"] = h0_values

        # 检查K值一致性
        if len(k_values) >= 2:
            k_max = max(k_values)
            k_min = min(k_values)
            k_diff = (k_max - k_min) / k_max if k_max > 0 else 0

            if k_diff > 0.30:  # 30%差异
                result.add_warning(
                    f"曲线K值差异较大: {k_diff:.1%}，可能影响并联合成精度"
                )
            result.details["k_diff"] = k_diff
            result.details["k_values"] = k_values

        self._logger.info(
            f"[曲线参数] pumps={pump_ids}, h0_count={len(h0_values)}, "
            f"k_count={len(k_values)}, is_valid={result.is_valid}"
        )
        return result

    def validate_all(
        self,
        pump_infos: List[Dict[str, Any]],
        group_type: GroupProcessingStrategy,
        curve_registry: Any,
        freq_provider: Optional[Any] = None,
    ) -> ValidationResult:
        """
        执行全部验证

        Args:
            pump_infos: 泵信息列表
            group_type: 泵组类型
            curve_registry: 曲线注册表实例
            freq_provider: 频率数据提供器实例（可选）

        Returns:
            ValidationResult: 合并的验证结果
        """
        pump_ids = [p.get("pump_id") for p in pump_infos]

        # 1. 配置验证
        config_result = self.validate_group_config(pump_infos)

        # 2. 数据完整性验证
        data_result = self.validate_data_completeness(
            pump_ids, curve_registry, freq_provider
        )

        # 3. 物理一致性验证
        physics_result = self.validate_physics_consistency(pump_infos, group_type)

        # 4. 曲线参数验证
        curve_result = self.validate_curve_parameters(pump_ids, curve_registry)

        # 合并结果
        final_result = config_result.merge(data_result).merge(physics_result).merge(
            curve_result
        )

        self._logger.info(
            f"[综合验证] group_type={group_type.value}, "
            f"is_valid={final_result.is_valid}, "
            f"errors={len(final_result.errors)}, "
            f"warnings={len(final_result.warnings)}"
        )
        return final_result

