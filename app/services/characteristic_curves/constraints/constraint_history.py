"""
约束历史记录 (app.services.characteristic_curves.constraints.constraint_history)

记录约束参数的历史变化和版本追踪。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/03_核心模块/04_约束层.md
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class ConstraintHistoryEntry:
    """约束历史条目

    Attributes:
        entry_id: 条目ID
        constraint_type: 约束类型
        curve_type: 曲线类型
        parameters: 约束参数
        version: 版本号
        created_at: 创建时间
        created_by: 创建者
        reason: 变更原因
    """

    entry_id: str
    constraint_type: str
    curve_type: str
    parameters: Dict[str, Any]
    version: int
    created_at: datetime
    created_by: str = "system"
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "entry_id": self.entry_id,
            "constraint_type": self.constraint_type,
            "curve_type": self.curve_type,
            "parameters": self.parameters,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "reason": self.reason,
        }


class ConstraintHistory:
    """约束历史记录器

    记录约束参数的变更历史，支持版本追踪和回滚。

    Attributes:
        max_entries: 最大历史条目数
    """

    def __init__(self, max_entries: int = 1000) -> None:
        """初始化约束历史记录器

        Args:
            max_entries: 最大历史条目数
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.max_entries = max_entries
        self._history: Dict[str, List[ConstraintHistoryEntry]] = {}
        self._version_counter: Dict[str, int] = {}

    def _get_key(self, constraint_type: str, curve_type: str) -> str:
        """生成存储键"""
        return f"{constraint_type}:{curve_type}"

    def add_entry(
        self,
        constraint_type: str,
        curve_type: str,
        parameters: Dict[str, Any],
        created_by: str = "system",
        reason: str = "",
    ) -> ConstraintHistoryEntry:
        """添加历史条目

        Args:
            constraint_type: 约束类型
            curve_type: 曲线类型
            parameters: 约束参数
            created_by: 创建者
            reason: 变更原因

        Returns:
            ConstraintHistoryEntry: 新创建的历史条目
        """
        key = self._get_key(constraint_type, curve_type)

        # 更新版本号
        self._version_counter[key] = self._version_counter.get(key, 0) + 1
        version = self._version_counter[key]

        entry = ConstraintHistoryEntry(
            entry_id=str(uuid4()),
            constraint_type=constraint_type,
            curve_type=curve_type,
            parameters=parameters,
            version=version,
            created_at=datetime.now(),
            created_by=created_by,
            reason=reason,
        )

        if key not in self._history:
            self._history[key] = []

        self._history[key].append(entry)

        # 限制历史条目数量
        if len(self._history[key]) > self.max_entries:
            self._history[key] = self._history[key][-self.max_entries :]

        self._logger.debug(f"添加约束历史: {key} v{version}")
        return entry

    def get_history(
        self, constraint_type: str, curve_type: str, limit: int = 10
    ) -> List[ConstraintHistoryEntry]:
        """获取历史记录"""
        key = self._get_key(constraint_type, curve_type)
        entries = self._history.get(key, [])
        return entries[-limit:][::-1]  # 最新的在前

    def get_version(
        self, constraint_type: str, curve_type: str, version: int
    ) -> Optional[ConstraintHistoryEntry]:
        """获取指定版本"""
        key = self._get_key(constraint_type, curve_type)
        for entry in self._history.get(key, []):
            if entry.version == version:
                return entry
        return None

    def get_latest(
        self, constraint_type: str, curve_type: str
    ) -> Optional[ConstraintHistoryEntry]:
        """获取最新版本"""
        key = self._get_key(constraint_type, curve_type)
        entries = self._history.get(key, [])
        return entries[-1] if entries else None

    def get_current_version(self, constraint_type: str, curve_type: str) -> int:
        """获取当前版本号"""
        key = self._get_key(constraint_type, curve_type)
        return self._version_counter.get(key, 0)

    def clear_history(self, constraint_type: str, curve_type: str) -> int:
        """清除历史记录，返回删除的条目数"""
        key = self._get_key(constraint_type, curve_type)
        count = len(self._history.get(key, []))
        self._history.pop(key, None)
        self._version_counter.pop(key, None)
        return count

