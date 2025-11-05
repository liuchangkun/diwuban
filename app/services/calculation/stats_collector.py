"""
集中式统计器：缺失指标计算的唯一记账与过程统计

本模块提供轻量的内存聚合实现，面向 orchestrator 的统一事件接口：
- on_group_start / on_group_end
- on_metric_start / on_metric_end
- on_write
- flush

设计目标：
- 统一口径（循环/非循环路径一致），避免重复累加
- 幂等（同一唯一键仅记一次成功完成）
- 可扩展（后续可接入 monitoring schema 或持久化管道）

作者：AI
最后修改：2025-10-07
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

_act = logging.getLogger(__name__)


@dataclass(frozen=True)
class _MetricKey:
    """唯一记账键（运行维度 + 业务维度）"""
    run_id: str
    station_id: int
    device_id: int
    metric_key: str
    bucket: Tuple[str, str]  # (start_iso, end_iso) 或 (窗口标识, 粒度)


@dataclass
class _MetricStats:
    total_points: int = 0
    valid_points: int = 0
    written_points: int = 0
    calc_duration_ms: int = 0
    validate_duration_ms: int = 0
    write_duration_ms: int = 0
    method_id: Optional[str] = None
    path_type: Optional[str] = None  # "cyclic" | "acyclic"
    finished: bool = False  # 幂等标记：完成后不再重复累计


class StatsCollector:
    """
    统计采集与聚合器（内存实现）

    用法（示意）：
      sc = StatsCollector()
      sc.on_metric_start(...)
      sc.on_write(...)
      sc.on_metric_end(...)
      sc.flush()
    """

    def __init__(self) -> None:
        self._stats: Dict[_MetricKey, _MetricStats] = {}
        self._groups: Dict[str, Dict] = {}

    # ------------------------- 组级事件 -------------------------
    def on_group_start(self, group_id: str, run_id: str, station_id: int, device_id: int) -> None:
        """记录循环组开始事件（不做重计数，仅留痕）。"""
        self._groups[group_id] = {
            "run_id": run_id,
            "station_id": station_id,
            "device_id": device_id,
        }
        _act.info("[计算-开始] 循环组开始", extra={"extra_data": {"group_id": group_id}})

    def on_group_end(self, group_id: str, succeeded: bool, iterations: int, converged: bool) -> None:
        """记录循环组结束事件（迭代次数与收敛标记）。"""
        _act.info(
            "[计算-完成] 循环组完成",
            extra={
                "extra_data": {
                    "group_id": group_id,
                    "succeeded": succeeded,
                    "iterations": iterations,
                    "converged": converged,
                }
            },
        )
        # 保留组元信息，供后续 flush 输出或监控使用

    # ------------------------- 指标级事件 -------------------------
    def on_metric_start(
        self,
        run_id: str,
        station_id: int,
        device_id: int,
        metric_key: str,
        bucket: Tuple[str, str],
        path_type: str,
        method_id: Optional[str] = None,
        total_points: int = 0,
    ) -> None:
        """
        指标开始事件：创建统计项。如果此前已完成（finished=True），保持幂等不重复。
        """
        k = _MetricKey(run_id, station_id, device_id, metric_key, bucket)
        s = self._stats.get(k)
        if s is None:
            s = _MetricStats()
            self._stats[k] = s
        if s.finished:
            _act.debug(f"指标统计忽略: metric_key={metric_key}, event=metric_start_ignored")
            return
        s.path_type = path_type
        s.method_id = method_id or s.method_id
        s.total_points += int(total_points)

    def on_write(
        self,
        run_id: str,
        station_id: int,
        device_id: int,
        metric_key: str,
        bucket: Tuple[str, str],
        written_points: int,
        write_duration_ms: int,
    ) -> None:
        """写入事件：仅在一次成功落地中累计，完成后不重复。"""
        k = _MetricKey(run_id, station_id, device_id, metric_key, bucket)
        s = self._stats.setdefault(k, _MetricStats())
        if s.finished:
            _act.debug(f"指标统计忽略: metric_key={metric_key}, event=write_ignored")
            return
        s.written_points += int(written_points)
        s.write_duration_ms += int(write_duration_ms)

    def on_metric_end(
        self,
        run_id: str,
        station_id: int,
        device_id: int,
        metric_key: str,
        bucket: Tuple[str, str],
        valid_points: int,
        calc_duration_ms: int,
        validate_duration_ms: int,
        method_id: Optional[str] = None,
    ) -> None:
        """
        指标结束事件：完成唯一记账并设置幂等标记 finished=True。
        """
        k = _MetricKey(run_id, station_id, device_id, metric_key, bucket)
        s = self._stats.setdefault(k, _MetricStats())
        if s.finished:
            _act.debug(f"指标统计忽略: metric_key={metric_key}, event=metric_end_ignored")
            return
        s.valid_points += int(valid_points)
        s.calc_duration_ms += int(calc_duration_ms)
        s.validate_duration_ms += int(validate_duration_ms)
        if method_id:
            s.method_id = method_id
        s.finished = True

    # ------------------------- 汇总/输出 -------------------------
    def flush(self) -> Dict[str, Dict]:
        """
        返回汇总后的统计结果（内存结构），供调用方落地或监控使用。

        Returns:
            一个 dict，其中 key 为序列化后的唯一键字符串，value 为统计内容字典。
        """
        result: Dict[str, Dict] = {}
        for k, s in self._stats.items():
            key_s = f"{k.run_id}|{k.station_id}|{k.device_id}|{k.metric_key}|{k.bucket[0]}|{k.bucket[1]}"
            result[key_s] = {
                "total_points": s.total_points,
                "valid_points": s.valid_points,
                "written_points": s.written_points,
                "calc_duration_ms": s.calc_duration_ms,
                "validate_duration_ms": s.validate_duration_ms,
                "write_duration_ms": s.write_duration_ms,
                "method_id": s.method_id,
                "path_type": s.path_type,
                "finished": s.finished,
            }
        _act.debug(f"统计汇总完成: 指标数={len(result)}")
        return result


__all__ = ["StatsCollector"]

