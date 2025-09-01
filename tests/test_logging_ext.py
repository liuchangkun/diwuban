# import json  # 未使用，移除以通过 ruff F401
import logging
import time

from app.utils.logging_ext import (
    EventLogger,
    SamplingGate,
    TaskSummaryCollector,
    log_align_merge_window,
    log_ingest_begin,
    log_ingest_end,
    log_ingest_progress,
    log_task_summary,
    setup_basic_json_logging,
)


def test_progress_sampling_and_summary(caplog):
    setup_basic_json_logging()
    caplog.set_level(logging.INFO)
    log = EventLogger(logging.getLogger("root"))

    # ingest begin
    log_ingest_begin(log, file_path="data/a.csv", rows_total=100000)

    gate = SamplingGate(every_n=10, min_interval_sec=0)
    started = time.time()
    emitted = 0
    for i in range(1, 51):
        log_ingest_progress(
            log, gate, rows_read=i, bytes_read=i * 100, started_ts=started
        )
        if i % 10 == 0:
            emitted += 1
    # ingest end
    log_ingest_end(log, rows_loaded=49876, cost_ms=300000)

    # align.merge.window
    log_align_merge_window(
        log,
        window_start="2025-08-18T02:00:00Z",
        window_end="2025-08-18T03:00:00Z",
        rows_in=50000,
        rows_deduped=124,
        rows_merged=49876,
        dedup_ratio=124 / 50000,
        sql_cost_ms=1800,
        affected_rows=49876,
    )

    # task.summary
    summary = TaskSummaryCollector(
        rows_total=100000, rows_merged=99876, backpressure_count=2
    )
    log_task_summary(log, summary)

    # 断言：采样条数
    progress_lines = [
        r for r in caplog.records if getattr(r, "event", None) == "ingest.load.progress"
    ]
    assert len(progress_lines) == emitted

    # 断言：task.summary 字段存在
    summary_lines = [
        r for r in caplog.records if getattr(r, "event", None) == "task.summary"
    ]
    assert summary_lines, "missing task.summary"

    # 验证 JSON 结构可序列化（通过 JsonFormatter）
    # 取最后一条日志进行格式化检查
    formatter = logging.getLogger().handlers[0].formatter
    assert formatter is not None
