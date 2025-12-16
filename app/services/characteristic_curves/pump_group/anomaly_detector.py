"""
泵组异常检测器 (app.services.characteristic_curves.pump_group.anomaly_detector)

检测泵组运行中的异常现象：逆流、倒灌、气蚀等。

核心功能：
- 逆流检测（负流量）
- 倒灌检测（出口压力低于入口）
- 气蚀检测（NPSHa < NPSHr）
- 最小流量限制检测
- 综合异常诊断

物理背景：
- 逆流：泵停止后未关闭止回阀，管网压力推动水流倒流
- 倒灌：出口压力低于入口压力，可能阀门故障或管路堵塞
- 气蚀：入口压力过低，液体汽化产生气泡，损坏叶轮
- 最小流量：流量过小导致泵内温升，损坏机械密封

版本: v1.0
创建日期: 2025-12-14
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class AnomalyType(str, Enum):
    """异常类型"""
    REVERSE_FLOW = "reverse_flow"  # 逆流
    BACKFLOW = "backflow"  # 倒灌
    CAVITATION = "cavitation"  # 气蚀
    MIN_FLOW_VIOLATION = "min_flow_violation"  # 最小流量违规
    PRESSURE_ANOMALY = "pressure_anomaly"  # 压力异常
    EFFICIENCY_ANOMALY = "efficiency_anomaly"  # 效率异常
    POWER_ANOMALY = "power_anomaly"  # 功率异常


class AnomalySeverity(str, Enum):
    """异常严重程度"""
    INFO = "info"  # 提示
    WARNING = "warning"  # 警告
    CRITICAL = "critical"  # 严重
    EMERGENCY = "emergency"  # 紧急


@dataclass
class AnomalyEvent:
    """单个异常事件"""
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    pump_id: Optional[int] = None  # 可能是整个泵组

    # 检测值
    detected_value: float = 0.0
    threshold_value: float = 0.0

    # 描述
    description: str = ""

    # 建议处理措施
    recommended_action: str = ""

    # 时间
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity.value,
            "pump_id": self.pump_id,
            "detected_value": self.detected_value,
            "threshold_value": self.threshold_value,
            "description": self.description,
            "recommended_action": self.recommended_action,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class AnomalyDetectionResult:
    """异常检测结果"""
    station_id: int
    pump_combination: List[int]

    # 检测到的异常
    anomalies: List[AnomalyEvent] = field(default_factory=list)

    # 总体状态
    has_critical: bool = False
    has_warning: bool = False

    # 统计
    anomaly_count: int = 0
    critical_count: int = 0

    # 检测时间
    detected_at: datetime = field(default_factory=datetime.now)

    def add_anomaly(self, event: AnomalyEvent) -> None:
        """添加异常事件"""
        self.anomalies.append(event)
        self.anomaly_count += 1

        if event.severity in [AnomalySeverity.CRITICAL, AnomalySeverity.EMERGENCY]:
            self.has_critical = True
            self.critical_count += 1
        elif event.severity == AnomalySeverity.WARNING:
            self.has_warning = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "station_id": self.station_id,
            "pump_combination": self.pump_combination,
            "anomalies": [a.to_dict() for a in self.anomalies],
            "has_critical": self.has_critical,
            "has_warning": self.has_warning,
            "anomaly_count": self.anomaly_count,
            "critical_count": self.critical_count,
            "detected_at": self.detected_at.isoformat(),
        }


class AnomalyDetector:
    """泵组异常检测器

    职责：
    1. 检测逆流现象（负流量）
    2. 检测倒灌现象（压力反向）
    3. 检测气蚀风险（NPSH不足）
    4. 检测最小流量违规
    5. 综合诊断并给出建议

    检测阈值（可配置）：
    - 逆流阈值：Q < -10 m³/h
    - 气蚀安全裕度：NPSHa > NPSHr × 1.3
    - 最小流量比例：Q > Q_rated × 0.1
    """

    def __init__(
        self,
        reverse_flow_threshold: float = -10.0,  # m³/h
        cavitation_margin: float = 1.3,  # NPSHa/NPSHr安全裕度
        min_flow_ratio: float = 0.10,  # 最小流量/额定流量
        min_efficiency: float = 0.30,  # 最低效率阈值
        max_power_ratio: float = 1.20,  # 最大功率/额定功率
    ):
        """初始化

        Args:
            reverse_flow_threshold: 逆流判定阈值 (m³/h)
            cavitation_margin: 气蚀安全裕度
            min_flow_ratio: 最小流量占额定流量比例
            min_efficiency: 效率异常阈值
            max_power_ratio: 过载功率比例
        """
        self._reverse_flow_threshold = reverse_flow_threshold
        self._cavitation_margin = cavitation_margin
        self._min_flow_ratio = min_flow_ratio
        self._min_efficiency = min_efficiency
        self._max_power_ratio = max_power_ratio
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

    def detect(
        self,
        station_id: int,
        pump_combination: List[int],
        operating_data: Dict[str, Any],
        pump_infos: Optional[Dict[int, Dict]] = None
    ) -> AnomalyDetectionResult:
        """执行异常检测

        Args:
            station_id: 泵站ID
            pump_combination: 泵组合
            operating_data: 运行数据 {
                'Q_total': float,
                'H_system': float,
                'P_total': float,
                'eta_total': float,
                'pump_flows': {pump_id: Q},
                'pump_powers': {pump_id: P},
                'inlet_pressure': float,  # 入口压力 (MPa)
                'outlet_pressure': float,  # 出口压力 (MPa)
                'npsha': float,  # 可用NPSH (m)
            }
            pump_infos: 泵参数 {pump_id: {
                'rated_flow': float,
                'rated_power': float,
                'npshr': float,  # 必需NPSH
                'min_flow': float,
            }}

        Returns:
            AnomalyDetectionResult: 检测结果
        """
        result = AnomalyDetectionResult(
            station_id=station_id,
            pump_combination=pump_combination,
        )

        pump_infos = pump_infos or {}

        # 1. 逆流检测
        self._detect_reverse_flow(operating_data, result)

        # 2. 倒灌检测
        self._detect_backflow(operating_data, result)

        # 3. 气蚀检测
        self._detect_cavitation(operating_data, pump_infos, result)

        # 4. 最小流量检测
        self._detect_min_flow_violation(
            operating_data, pump_infos, pump_combination, result
        )

        # 5. 效率异常检测
        self._detect_efficiency_anomaly(operating_data, result)

        # 6. 功率异常检测
        self._detect_power_anomaly(
            operating_data, pump_infos, pump_combination, result
        )

        self._logger.info(
            f"[异常检测] station={station_id}, pumps={pump_combination}, "
            f"异常数={result.anomaly_count}, 严重={result.critical_count}"
        )

        return result

    def _detect_reverse_flow(
        self,
        operating_data: Dict[str, Any],
        result: AnomalyDetectionResult
    ) -> None:
        """检测逆流"""
        Q_total = operating_data.get('Q_total', 0)

        if Q_total < self._reverse_flow_threshold:
            event = AnomalyEvent(
                anomaly_type=AnomalyType.REVERSE_FLOW,
                severity=AnomalySeverity.CRITICAL,
                detected_value=Q_total,
                threshold_value=self._reverse_flow_threshold,
                description=f"检测到逆流: Q={Q_total:.1f}m³/h < {self._reverse_flow_threshold}m³/h",
                recommended_action="立即检查止回阀是否正常关闭，确认泵是否停机"
            )
            result.add_anomaly(event)

        # 检查单泵逆流
        pump_flows = operating_data.get('pump_flows', {})
        for pump_id, Q in pump_flows.items():
            if Q < self._reverse_flow_threshold:
                event = AnomalyEvent(
                    anomaly_type=AnomalyType.REVERSE_FLOW,
                    severity=AnomalySeverity.CRITICAL,
                    pump_id=pump_id,
                    detected_value=Q,
                    threshold_value=self._reverse_flow_threshold,
                    description=f"泵{pump_id}逆流: Q={Q:.1f}m³/h",
                    recommended_action=f"检查泵{pump_id}的止回阀和运行状态"
                )
                result.add_anomaly(event)

    def _detect_backflow(
        self,
        operating_data: Dict[str, Any],
        result: AnomalyDetectionResult
    ) -> None:
        """检测倒灌（出口压力低于入口）"""
        inlet_p = operating_data.get('inlet_pressure')
        outlet_p = operating_data.get('outlet_pressure')

        if inlet_p is not None and outlet_p is not None:
            if outlet_p < inlet_p:
                delta_p = inlet_p - outlet_p
                event = AnomalyEvent(
                    anomaly_type=AnomalyType.BACKFLOW,
                    severity=AnomalySeverity.CRITICAL,
                    detected_value=outlet_p,
                    threshold_value=inlet_p,
                    description=f"倒灌风险: 出口压力{outlet_p:.3f}MPa < 入口压力{inlet_p:.3f}MPa",
                    recommended_action="检查出口阀门是否关闭、管路是否堵塞、泵是否运行"
                )
                result.add_anomaly(event)

    def _detect_cavitation(
        self,
        operating_data: Dict[str, Any],
        pump_infos: Dict[int, Dict],
        result: AnomalyDetectionResult
    ) -> None:
        """检测气蚀风险"""
        npsha = operating_data.get('npsha')

        if npsha is None:
            return

        # 检查各泵的NPSH
        for pump_id, info in pump_infos.items():
            npshr = info.get('npshr') or info.get('NPSHr')
            if npshr is None:
                continue

            required_npsha = npshr * self._cavitation_margin

            if npsha < required_npsha:
                if npsha < npshr:
                    # 已发生气蚀
                    severity = AnomalySeverity.EMERGENCY
                    desc = f"泵{pump_id}气蚀发生中: NPSHa={npsha:.1f}m < NPSHr={npshr:.1f}m"
                    action = "立即降低流量或增加入口压力，否则将损坏叶轮"
                else:
                    # 气蚀风险
                    severity = AnomalySeverity.WARNING
                    desc = f"泵{pump_id}气蚀风险: NPSHa={npsha:.1f}m < 安全值{required_npsha:.1f}m"
                    action = "建议降低流量或检查入口管路阻力"

                event = AnomalyEvent(
                    anomaly_type=AnomalyType.CAVITATION,
                    severity=severity,
                    pump_id=pump_id,
                    detected_value=npsha,
                    threshold_value=required_npsha,
                    description=desc,
                    recommended_action=action
                )
                result.add_anomaly(event)

    def _detect_min_flow_violation(
        self,
        operating_data: Dict[str, Any],
        pump_infos: Dict[int, Dict],
        pump_combination: List[int],
        result: AnomalyDetectionResult
    ) -> None:
        """检测最小流量违规"""
        pump_flows = operating_data.get('pump_flows', {})

        for pump_id in pump_combination:
            Q = pump_flows.get(pump_id, 0)
            info = pump_infos.get(pump_id, {})

            # 获取最小流量限制
            min_flow = info.get('min_flow')
            if min_flow is None:
                rated_flow = info.get('rated_flow', 500)
                min_flow = rated_flow * self._min_flow_ratio

            if 0 < Q < min_flow:
                event = AnomalyEvent(
                    anomaly_type=AnomalyType.MIN_FLOW_VIOLATION,
                    severity=AnomalySeverity.WARNING,
                    pump_id=pump_id,
                    detected_value=Q,
                    threshold_value=min_flow,
                    description=f"泵{pump_id}流量过低: Q={Q:.1f}m³/h < 最小流量{min_flow:.1f}m³/h",
                    recommended_action="增加流量或启用最小流量回流阀，避免泵内过热"
                )
                result.add_anomaly(event)

    def _detect_efficiency_anomaly(
        self,
        operating_data: Dict[str, Any],
        result: AnomalyDetectionResult
    ) -> None:
        """检测效率异常"""
        eta = operating_data.get('eta_total')

        if eta is not None and eta < self._min_efficiency and eta > 0:
            event = AnomalyEvent(
                anomaly_type=AnomalyType.EFFICIENCY_ANOMALY,
                severity=AnomalySeverity.WARNING,
                detected_value=eta,
                threshold_value=self._min_efficiency,
                description=f"泵组效率异常低: η={eta*100:.1f}% < {self._min_efficiency*100:.0f}%",
                recommended_action="检查是否偏离高效区运行，或存在机械故障"
            )
            result.add_anomaly(event)

    def _detect_power_anomaly(
        self,
        operating_data: Dict[str, Any],
        pump_infos: Dict[int, Dict],
        pump_combination: List[int],
        result: AnomalyDetectionResult
    ) -> None:
        """检测功率异常（过载）"""
        pump_powers = operating_data.get('pump_powers', {})

        for pump_id in pump_combination:
            P = pump_powers.get(pump_id, 0)
            info = pump_infos.get(pump_id, {})
            rated_power = info.get('rated_power', 55)

            max_power = rated_power * self._max_power_ratio

            if P > max_power:
                event = AnomalyEvent(
                    anomaly_type=AnomalyType.POWER_ANOMALY,
                    severity=AnomalySeverity.CRITICAL,
                    pump_id=pump_id,
                    detected_value=P,
                    threshold_value=max_power,
                    description=f"泵{pump_id}功率过载: P={P:.1f}kW > {max_power:.1f}kW ({self._max_power_ratio*100:.0f}%额定)",
                    recommended_action="降低流量或检查电机过载保护"
                )
                result.add_anomaly(event)

    def detect_from_operating_point(
        self,
        station_id: int,
        operating_point: Any,  # GroupOperatingPoint
        pump_infos: Optional[Dict[int, Dict]] = None
    ) -> AnomalyDetectionResult:
        """从运行工况点检测异常

        Args:
            station_id: 泵站ID
            operating_point: GroupOperatingPoint实例
            pump_infos: 泵信息

        Returns:
            AnomalyDetectionResult: 检测结果
        """
        operating_data = {
            'Q_total': operating_point.Q_total,
            'H_system': operating_point.H_system,
            'P_total': operating_point.P_total,
            'eta_total': operating_point.eta_total,
        }

        return self.detect(
            station_id=station_id,
            pump_combination=list(operating_point.running_pump_ids),
            operating_data=operating_data,
            pump_infos=pump_infos
        )
