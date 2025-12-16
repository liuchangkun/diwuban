"""
泵组合有效性判定器 (app.services.characteristic_curves.pump_group.combination_validator)

验证泵组合是否满足运行条件和物理约束。

核心功能：
- 泵组合成员有效性验证
- 功率匹配性检查（避免大小泵差异过大）
- 控制类型兼容性检查（VFD/SS混合约束）
- 运行台数合理性检查
- 管网承载能力验证

版本: v1.0
创建日期: 2025-12-14
参考文档: 08_泵组直接拟合.md 第17.2节
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class CombinationValidationResult:
    """泵组合验证结果"""
    is_valid: bool = True
    pump_combination: List[int] = field(default_factory=list)
    station_id: Optional[int] = None

    # 各项检查结果
    membership_valid: bool = True  # 成员有效性
    power_match_valid: bool = True  # 功率匹配
    control_type_valid: bool = True  # 控制类型兼容
    count_valid: bool = True  # 台数合理性
    capacity_valid: bool = True  # 管网承载能力

    # 详细信息
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "pump_combination": self.pump_combination,
            "station_id": self.station_id,
            "membership_valid": self.membership_valid,
            "power_match_valid": self.power_match_valid,
            "control_type_valid": self.control_type_valid,
            "count_valid": self.count_valid,
            "capacity_valid": self.capacity_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "details": self.details,
        }


class CombinationValidator:
    """泵组合有效性判定器

    职责：
    1. 验证泵是否属于指定泵站
    2. 检查泵功率匹配性（避免大泵带小泵）
    3. 验证控制类型兼容性
    4. 检查运行台数是否合理
    5. 评估管网承载能力

    判定规则（来自文档17.2节）：
    1. 运行泵必须是泵站成员
    2. 至少1台VFD泵（纯SS泵组不支持变流量控制）
    3. 泵功率匹配（max/min功率比不超过阈值）
    4. 运行台数合理（不超过管网承载能力）
    """

    def __init__(
        self,
        power_ratio_threshold: float = 2.0,
        min_vfd_count: int = 1,
        max_running_pumps: int = 10
    ):
        """初始化

        Args:
            power_ratio_threshold: 最大/最小功率比阈值
            min_vfd_count: 最少VFD泵数量
            max_running_pumps: 最大运行台数
        """
        self._power_ratio_threshold = power_ratio_threshold
        self._min_vfd_count = min_vfd_count
        self._max_running_pumps = max_running_pumps
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

    def validate(
        self,
        pump_combination: List[int],
        station_id: int,
        pump_infos: Dict[int, Dict[str, Any]],
        station_pump_ids: Optional[List[int]] = None,
        max_station_flow: Optional[float] = None
    ) -> CombinationValidationResult:
        """验证泵组合有效性

        Args:
            pump_combination: 泵组合（泵ID列表）
            station_id: 泵站ID
            pump_infos: 泵信息字典 {pump_id: {'control_type': 'VFD'/'SS', 'rated_power': float, ...}}
            station_pump_ids: 泵站所有泵ID（可选）
            max_station_flow: 管网最大承载流量（可选）

        Returns:
            CombinationValidationResult: 验证结果
        """
        result = CombinationValidationResult(
            pump_combination=pump_combination,
            station_id=station_id,
        )

        if not pump_combination:
            result.is_valid = False
            result.errors.append("泵组合为空")
            return result

        # 1. 成员有效性验证
        self._check_membership(
            pump_combination, station_pump_ids, pump_infos, result)

        # 2. 功率匹配性检查
        self._check_power_match(pump_combination, pump_infos, result)

        # 3. 控制类型兼容性检查
        self._check_control_type(pump_combination, pump_infos, result)

        # 4. 运行台数合理性检查
        self._check_pump_count(pump_combination, result)

        # 5. 管网承载能力验证
        self._check_capacity(pump_combination, pump_infos,
                             max_station_flow, result)

        # 汇总结果
        result.is_valid = (
            result.membership_valid and
            result.power_match_valid and
            result.control_type_valid and
            result.count_valid and
            result.capacity_valid
        )

        self._logger.info(
            f"[组合验证] station={station_id}, pumps={pump_combination}, "
            f"valid={result.is_valid}, errors={len(result.errors)}"
        )

        return result

    def _check_membership(
        self,
        pump_combination: List[int],
        station_pump_ids: Optional[List[int]],
        pump_infos: Dict[int, Dict[str, Any]],
        result: CombinationValidationResult
    ) -> None:
        """检查泵是否属于泵站"""
        # 如果没有提供泵站泵列表，使用pump_infos的键
        valid_pumps = set(station_pump_ids) if station_pump_ids else set(
            pump_infos.keys())

        invalid_pumps = [
            pid for pid in pump_combination if pid not in valid_pumps]

        if invalid_pumps:
            result.membership_valid = False
            result.errors.append(f"以下泵不属于泵站: {invalid_pumps}")

        # 检查是否有重复
        if len(pump_combination) != len(set(pump_combination)):
            result.membership_valid = False
            result.errors.append("泵组合存在重复ID")

        result.details["invalid_pumps"] = invalid_pumps
        result.details["valid_pump_count"] = len(
            pump_combination) - len(invalid_pumps)

    def _check_power_match(
        self,
        pump_combination: List[int],
        pump_infos: Dict[int, Dict[str, Any]],
        result: CombinationValidationResult
    ) -> None:
        """检查泵功率匹配性"""
        powers = []
        for pump_id in pump_combination:
            info = pump_infos.get(pump_id, {})
            power = info.get('rated_power') or info.get('power') or 55.0
            powers.append(power)

        if not powers:
            return

        min_power = min(powers)
        max_power = max(powers)

        if min_power > 0:
            power_ratio = max_power / min_power
            result.details["power_ratio"] = power_ratio
            result.details["min_power"] = min_power
            result.details["max_power"] = max_power

            if power_ratio > self._power_ratio_threshold:
                result.power_match_valid = False
                result.warnings.append(
                    f"功率差异过大: 最大{max_power}kW / 最小{min_power}kW = {power_ratio:.1f} "
                    f"(阈值{self._power_ratio_threshold})"
                )

    def _check_control_type(
        self,
        pump_combination: List[int],
        pump_infos: Dict[int, Dict[str, Any]],
        result: CombinationValidationResult
    ) -> None:
        """检查控制类型兼容性"""
        vfd_pumps = []
        ss_pumps = []
        unknown_pumps = []

        for pump_id in pump_combination:
            info = pump_infos.get(pump_id, {})
            control_type = info.get('control_type', '').upper()

            if control_type == 'VFD':
                vfd_pumps.append(pump_id)
            elif control_type == 'SS':
                ss_pumps.append(pump_id)
            else:
                unknown_pumps.append(pump_id)

        result.details["vfd_pumps"] = vfd_pumps
        result.details["ss_pumps"] = ss_pumps
        result.details["unknown_type_pumps"] = unknown_pumps

        # 检查VFD泵数量
        if len(vfd_pumps) < self._min_vfd_count:
            result.control_type_valid = False
            result.errors.append(
                f"VFD泵数量不足: {len(vfd_pumps)} < {self._min_vfd_count}（纯SS泵组不支持变流量控制）"
            )

        # 警告：存在未知控制类型
        if unknown_pumps:
            result.warnings.append(f"以下泵控制类型未知: {unknown_pumps}")

    def _check_pump_count(
        self,
        pump_combination: List[int],
        result: CombinationValidationResult
    ) -> None:
        """检查运行台数合理性"""
        n_pumps = len(pump_combination)
        result.details["pump_count"] = n_pumps

        if n_pumps > self._max_running_pumps:
            result.count_valid = False
            result.errors.append(
                f"运行台数过多: {n_pumps} > {self._max_running_pumps}"
            )

        if n_pumps == 0:
            result.count_valid = False
            result.errors.append("运行台数为0")

    def _check_capacity(
        self,
        pump_combination: List[int],
        pump_infos: Dict[int, Dict[str, Any]],
        max_station_flow: Optional[float],
        result: CombinationValidationResult
    ) -> None:
        """检查管网承载能力"""
        if max_station_flow is None:
            return

        # 估算泵组最大流量
        total_rated_flow = 0.0
        for pump_id in pump_combination:
            info = pump_infos.get(pump_id, {})
            rated_flow = info.get('rated_flow') or info.get('flow') or 500.0
            total_rated_flow += rated_flow

        result.details["total_rated_flow"] = total_rated_flow
        result.details["max_station_flow"] = max_station_flow

        if total_rated_flow > max_station_flow * 1.2:  # 允许20%裕度
            result.capacity_valid = False
            result.warnings.append(
                f"泵组额定流量{total_rated_flow:.0f}m³/h超出管网承载能力{max_station_flow:.0f}m³/h"
            )

    def validate_for_curve_type(
        self,
        pump_combination: List[int],
        curve_type: str,
        pump_infos: Dict[int, Dict[str, Any]]
    ) -> CombinationValidationResult:
        """针对特定曲线类型的验证

        Args:
            pump_combination: 泵组合
            curve_type: 曲线类型 (qh/qp/qeta)
            pump_infos: 泵信息

        Returns:
            CombinationValidationResult: 验证结果
        """
        result = CombinationValidationResult(pump_combination=pump_combination)

        # 基础验证
        if not pump_combination:
            result.is_valid = False
            result.errors.append("泵组合为空")
            return result

        # Q-η曲线需要效率数据
        if curve_type == 'qeta':
            pumps_without_eta = []
            for pump_id in pump_combination:
                info = pump_infos.get(pump_id, {})
                if not info.get('has_efficiency_curve', True):
                    pumps_without_eta.append(pump_id)

            if pumps_without_eta:
                result.warnings.append(
                    f"以下泵缺少效率曲线数据: {pumps_without_eta}"
                )

        result.is_valid = len(result.errors) == 0
        return result

    def check_curve_compatibility(
        self,
        pump_combination: List[int],
        pump_infos: Dict[int, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """检查泵曲线兼容性

        评估并联运行时泵曲线的匹配程度。

        Args:
            pump_combination: 泵组合
            pump_infos: 泵信息（包含额定扬程、流量等）

        Returns:
            Dict: {
                'is_compatible': bool,
                'compatibility_score': float (0-100),
                'head_deviation': float (扬程偏差%),
                'flow_deviation': float (流量偏差%),
                'warnings': List[str]
            }
        """
        result = {
            'is_compatible': True,
            'compatibility_score': 100.0,
            'head_deviation': 0.0,
            'flow_deviation': 0.0,
            'warnings': []
        }

        if len(pump_combination) < 2:
            return result

        # 收集各泵额定参数
        heads = []
        flows = []
        for pump_id in pump_combination:
            info = pump_infos.get(pump_id, {})
            if 'rated_head' in info:
                heads.append(info['rated_head'])
            if 'rated_flow' in info:
                flows.append(info['rated_flow'])

        # 计算扬程偏差
        if len(heads) >= 2:
            avg_head = sum(heads) / len(heads)
            max_head_dev = max(abs(h - avg_head) /
                               avg_head * 100 for h in heads)
            result['head_deviation'] = max_head_dev

            if max_head_dev > 20:
                result['is_compatible'] = False
                result['compatibility_score'] -= 40
                result['warnings'].append(
                    f"扬程偏差过大({max_head_dev:.1f}%)，可能导致抢流"
                )
            elif max_head_dev > 10:
                result['compatibility_score'] -= 20
                result['warnings'].append(
                    f"扬程偏差较大({max_head_dev:.1f}%)，建议监控运行状态"
                )

        # 计算流量偏差
        if len(flows) >= 2:
            avg_flow = sum(flows) / len(flows)
            max_flow_dev = max(abs(f - avg_flow) /
                               avg_flow * 100 for f in flows)
            result['flow_deviation'] = max_flow_dev

            if max_flow_dev > 30:
                result['compatibility_score'] -= 20
                result['warnings'].append(
                    f"流量偏差较大({max_flow_dev:.1f}%)，可能影响效率"
                )

        result['compatibility_score'] = max(0, result['compatibility_score'])
        return result
