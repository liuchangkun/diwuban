"""
告警管理器 (app.services.characteristic_curves.shared.alert_manager)

管理曲线拟合和分析过程中的告警。

版本: v1.0
更新日期: 2025-12-08
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4


class AlertLevel(str, Enum):
    """告警级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """告警

    Attributes:
        alert_id: 告警ID
        level: 告警级别
        source: 来源模块
        message: 告警消息
        created_at: 创建时间
        acknowledged: 是否已确认
        details: 详细信息
    """

    alert_id: str
    level: AlertLevel
    source: str
    message: str
    created_at: datetime
    acknowledged: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "alert_id": self.alert_id,
            "level": self.level.value,
            "source": self.source,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "acknowledged": self.acknowledged,
            "details": self.details,
        }


class AlertManager:
    """告警管理器

    集中管理系统告警，支持告警过滤和回调。

    Attributes:
        max_alerts: 最大告警数量
    """

    def __init__(self, max_alerts: int = 1000) -> None:
        """初始化告警管理器

        Args:
            max_alerts: 最大告警数量
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.max_alerts = max_alerts
        self._alerts: List[Alert] = []
        self._callbacks: List[Callable[[Alert], None]] = []

    def add_alert(
        self,
        level: str,
        source: str,
        message: str,
        **details: Any,
    ) -> Alert:
        """添加告警

        Args:
            level: 告警级别 ('info', 'warning', 'error', 'critical')
            source: 来源模块
            message: 告警消息
            **details: 额外详细信息

        Returns:
            Alert: 新创建的告警
        """
        alert = Alert(
            alert_id=str(uuid4()),
            level=AlertLevel(level),
            source=source,
            message=message,
            created_at=datetime.now(),
            details=details,
        )

        self._alerts.append(alert)

        # 限制告警数量
        if len(self._alerts) > self.max_alerts:
            self._alerts = self._alerts[-self.max_alerts :]

        # 触发回调
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                self._logger.error(f"告警回调执行失败: {e}")

        self._logger.log(
            self._get_log_level(alert.level),
            f"[{alert.source}] {alert.message}",
        )

        return alert

    def _get_log_level(self, level: AlertLevel) -> int:
        """获取对应的日志级别"""
        mapping = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL,
        }
        return mapping.get(level, logging.INFO)

    def get_alerts(
        self, level: Optional[str] = None, source: Optional[str] = None, limit: int = 50
    ) -> List[Alert]:
        """获取告警列表"""
        alerts = self._alerts
        if level:
            alerts = [a for a in alerts if a.level.value == level]
        if source:
            alerts = [a for a in alerts if a.source == source]
        return alerts[-limit:][::-1]

    def acknowledge(self, alert_id: str) -> bool:
        """确认告警"""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def get_unacknowledged(self) -> List[Alert]:
        """获取未确认的告警"""
        return [a for a in self._alerts if not a.acknowledged]

    def register_callback(self, callback: Callable[[Alert], None]) -> None:
        """注册告警回调"""
        self._callbacks.append(callback)

    def clear(self) -> int:
        """清除所有告警，返回清除数量"""
        count = len(self._alerts)
        self._alerts.clear()
        return count

