from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, TypedDict


class Adjustment(TypedDict, total=False):
    action: Literal["none", "shrink_batch", "shrink_workers", "recover"]
    from_batch: int | None
    to_batch: int | None
    new_workers: int | None


@dataclass
class Thresholds:
    p95_ms: int = 2000
    fail_rate: float = 0.01


@dataclass
class BackpressureController:
    batch_size: int
    workers: int
    thresholds: Thresholds = Thresholds()
    min_workers: int = 1
    min_batch: int = 1000

    def decide(self, p95_ms: int, fail_rate: float) -> Adjustment:
        # 触发进入背压
        if p95_ms > self.thresholds.p95_ms or fail_rate > self.thresholds.fail_rate:
            # 优先缩批次 50%
            if self.batch_size > self.min_batch:
                new_batch = max(self.min_batch, self.batch_size // 2)
                adj: Adjustment = {
                    "action": "shrink_batch",
                    "from_batch": self.batch_size,
                    "to_batch": new_batch,
                }
                self.batch_size = new_batch
                return adj
            # 其次降并发（-1）
            if self.workers > self.min_workers:
                self.workers -= 1
                return {
                    "action": "shrink_workers",
                    "new_workers": self.workers,
                }
            return {"action": "none"}
        # 恢复路径（简单回升策略，可后续改为渐进）
        return {"action": "recover"}
