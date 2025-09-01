from __future__ import annotations

from dataclasses import dataclass

from app.core.config.loader import Settings


@dataclass
class Thresholds:
    p95_ms: int = 2000  # P95 阈值（ms）
    fail_rate: float = 0.01  # 失败率阈值（0~1）
    min_batch: int = 1000  # 最小批大小
    min_workers: int = 1  # 最小并发数


class BackpressureController:
    def __init__(
        self,
        batch_size: int,
        workers: int,
        thresholds: Thresholds | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.batch_size = int(batch_size)
        self.workers = int(workers)
        if thresholds is None and settings is not None:
            t = settings.ingest.backpressure.thresholds
            thresholds = Thresholds(
                p95_ms=t.p95_ms,
                fail_rate=t.fail_rate,
                min_batch=t.min_batch,
                min_workers=t.min_workers,
            )
        self.th = thresholds or Thresholds()

    def decide(self, p95_ms: int, fail_rate: float) -> dict:
        """根据 p95 与失败率决定是否收缩批大小/并发，或恢复。
        返回：{"action": "shrink_batch"|"shrink_workers"|"recover"|"none", ...}
        """
        # 进入拥塞：收缩批大小，其次收缩并发
        if p95_ms > self.th.p95_ms or fail_rate > self.th.fail_rate:
            to_batch = max(self.th.min_batch, self.batch_size // 2)
            if to_batch < self.batch_size:
                self.batch_size = to_batch
                return {"action": "shrink_batch", "to_batch": to_batch}
            if self.workers > self.th.min_workers:
                to_workers = max(self.th.min_workers, self.workers - 1)
                if to_workers < self.workers:
                    self.workers = to_workers
                    return {"action": "shrink_workers", "to_workers": to_workers}
        else:
            # 恢复信号（由调用方决定如何回升）
            return {"action": "recover"}
        return {"action": "none"}
