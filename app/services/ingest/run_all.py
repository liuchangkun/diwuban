from __future__ import annotations

"""
端到端导入与合并（ingest.run_all）
流程：prepare_dim → create_staging → copy_from_mapping → merge_window → 汇总与快照
- 统一初始化 compute_run_dir + init_logging；写 env.json 与 task.begin 事件
- 输出：logs/runs 下 app/sql/perf/error；env.json 合并 run_id 与 config_snapshot
"""


import json
import logging
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from app.adapters.db.gateway import count_tz_fallback, get_conn
from app.adapters.logging.init import compute_run_dir, init_logging
from app.core.config.loader import Settings
from app.services.ingest.copy_workers import copy_from_mapping
from app.services.ingest.create_staging import create_staging
from app.services.ingest.merge_service import merge_window
from app.services.ingest.prepare_dim import prepare_dim
from app.utils.logging_ext import (
    EventLogger,
    SqlStat,
    TaskSummaryCollector,
    log_task_summary,
)
from app.utils.logging_decorators import (
    business_logger,
    log_key_metrics,
    log_file_processing_metrics,
    log_data_processing_metrics,
    log_merge_statistics,
    create_internal_step_logger,
    log_business_milestone,
)

logger = logging.getLogger(__name__)


@business_logger("run_all_pipeline", enable_progress=True)
def run_all(
    settings: Settings,
    mapping: Path,
    window_start_utc: datetime,
    window_end_utc: datetime,
    run_dir: Path | None = None,
    use_staging_time_range: bool = False,
) -> None:
    """端到端执行一次导入与合并任务。
    步骤：
    0) 前置清理：根据配置参数决定是否清空数据库，然后清空logs目录
    1) 初始化日志目录与全局日志（compute_run_dir + init_logging）并写入 env.json 快照
    2) prepare_dim → create_staging：准备维表、创建 staging 表
    3) copy_from_mapping：并发 COPY 导入，期间输出 ingest.load.* / ingest.copy.batch 等事件
    4) merge_window：集合式合并到 fact，并输出 align.merge.window 事件
    5) 汇总 task.summary，合并 copy/merge 耗时与统计
    参数：settings/mapping/window_start_utc/window_end_utc/run_dir
    返回：None（结果体现在 logs/runs 与 env.json）
    """
    # ========== 步骤0：前置清理 ==========
    from app.services.system.cleanup import perform_startup_cleanup

    # 检查配置中的启动清理设置
    cleanup_config = settings.logging.startup_cleanup

    if cleanup_config.clear_database or cleanup_config.clear_logs:
        logger.info(
            "执行run-all前置清理",
            extra={
                "event": "run_all.pre_cleanup.start",
                "clear_database": cleanup_config.clear_database,
                "clear_logs": cleanup_config.clear_logs,
                "confirm_clear": cleanup_config.confirm_clear,
            },
        )

        try:
            # 调用系统清理服务
            perform_startup_cleanup(settings)

            logger.info(
                "run-all前置清理完成",
                extra={
                    "event": "run_all.pre_cleanup.completed",
                    "clear_database": cleanup_config.clear_database,
                    "clear_logs": cleanup_config.clear_logs,
                },
            )
        except Exception as e:
            logger.error(
                "run-all前置清理失败",
                extra={"event": "run_all.pre_cleanup.failed", "error": str(e)},
            )
            # 清理失败不中止流程，仅记录错误
            pass
    else:
        logger.info(
            "跳过run-all前置清理",
            extra={
                "event": "run_all.pre_cleanup.skip",
                "reason": "配置中clear_database和clear_logs均为false",
            },
        )

    # ========== 步骤1：开始原有流程 ==========
    # 创建内部步骤日志记录器
    step_logger = create_internal_step_logger("run_all_pipeline", logger, settings)

    step_logger.step(
        "初始化运行环境和日志系统", run_dir=str(run_dir) if run_dir else "auto"
    )
    run_dir = run_dir or compute_run_dir()
    init_logging(settings, run_dir)

    step_logger.step("生成运行标识符")
    # 写入配置快照：若 CLI 已写入 env.json（含 args_summary/config_snapshot），此处仅补充 run_id 与 run_dir，避免覆盖
    run_id = datetime.now(tz=datetime.utcnow().astimezone().tzinfo).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    step_logger.step("写入配置快照", run_id=run_id)
    env_path = run_dir / "env.json"
    merged: dict[str, object] = {}
    try:
        if env_path.exists():
            merged = json.loads(env_path.read_text(encoding="utf-8")) or {}
    except Exception:
        merged = {}
    # 若无 config_snapshot，则使用当前 settings 生成
    if "config_snapshot" not in merged:
        merged["config_snapshot"] = asdict(settings)
    merged["run_id"] = run_id
    merged["run_dir"] = str(run_dir)
    env_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    step_logger.checkpoint(
        "env_setup_complete",
        {
            "run_id": run_id,
            "run_dir": str(run_dir),
            "mapping_file": str(mapping),
            "window_duration": str(window_end_utc - window_start_utc),
        },
    )

    logger.info(
        "开始运行",
        extra={
            "event": "task.begin",
            "extra": {
                "run_dir": str(run_dir),
                "mapping_file": str(mapping),
                "window_start": window_start_utc.isoformat(),
                "window_end": window_end_utc.isoformat(),
                "config_summary": {
                    "workers": settings.ingest.workers,
                    "commit_interval": settings.ingest.commit_interval,
                    "batch_size": settings.ingest.batch.size,
                },
            },
        },
    )

    # 记录开始时间用于性能监控
    pipeline_start_time = time.perf_counter()

    log_business_milestone(
        "管道执行开始",
        {
            "mapping_file": str(mapping),
            "time_window": f"{window_start_utc.isoformat()} - {window_end_utc.isoformat()}",
            "workers": settings.ingest.workers,
            "commit_interval": settings.ingest.commit_interval,
        },
        logger,
    )

    # 执行各阶段任务，并记录关键指标
    step_logger.step("开始准备维表阶段")
    stage_start = time.perf_counter()
    prepare_dim(settings, mapping)
    prepare_time = time.perf_counter() - stage_start
    step_logger.step("维表准备完成", result=f"耗时 {prepare_time:.2f} 秒")
    log_key_metrics(
        "准备维表",
        {"duration_seconds": round(prepare_time, 2), "mapping_file": str(mapping)},
        logger,
    )

    step_logger.step("开始创建临时表阶段")
    stage_start = time.perf_counter()
    create_staging(settings)
    staging_time = time.perf_counter() - stage_start
    step_logger.step("临时表创建完成", result=f"耗时 {staging_time:.2f} 秒")
    log_key_metrics("创建临时表", {"duration_seconds": round(staging_time, 2)}, logger)

    # # 【注意】为了测试验证，暂时注释掉自动清空逻辑
    # # 开始导入前，清空 staging 表，确保幂等性
    # try:
    #     with get_conn(settings) as conn:
    #         with conn.cursor() as cur:
    #             cur.execute("TRUNCATE public.staging_raw, public.staging_rejects;")
    #         conn.commit()
    #         logger.info("已清空 staging_raw 和 staging_rejects 表")
    # except Exception as e:
    #     logger.error(f"Failed to truncate staging tables: {e}")
    #     # 可选：如果清空失败则抛出异常中止运行
    #     raise

    step_logger.step("开始文件导入阶段")
    t0 = time.perf_counter()
    copy_stats = copy_from_mapping(settings, mapping, run_id=run_id)
    copy_ms = int((time.perf_counter() - t0) * 1000)
    step_logger.step(
        "文件导入完成",
        result=f"耗时 {copy_ms/1000:.2f} 秒",
        files_processed=copy_stats.get("files_total", 0),
        rows_loaded=copy_stats.get("rows_loaded", 0),
    )

    # 记录文件处理指标
    if copy_stats:
        step_logger.validation(
            "文件导入结果验证",
            copy_stats.get("files_succeeded", 0) > 0,
            f"成功: {copy_stats.get('files_succeeded', 0)}, 失败: {copy_stats.get('files_failed', 0)}",
        )

        log_file_processing_metrics(
            file_count=copy_stats.get("files_total", 0),
            total_size_mb=round(copy_stats.get("bytes_read", 0) / (1024 * 1024), 2),
            processing_time_seconds=copy_ms / 1000,
            success_count=copy_stats.get("files_succeeded", 0),
            error_count=copy_stats.get("files_failed", 0),
            logger=logger,
        )

        log_data_processing_metrics(
            rows_processed=copy_stats.get("rows_read", 0),
            rows_valid=copy_stats.get("rows_loaded", 0),
            rows_invalid=copy_stats.get("rows_rejected", 0),
            processing_time_seconds=copy_ms / 1000,
            data_time_range={
                "start": window_start_utc.isoformat(),
                "end": window_end_utc.isoformat(),
            },
            logger=logger,
        )

    # ========== 步骤3.5：动态时间窗口检测（可选）==========
    # 如果启用了从 staging_raw 获取时间范围，则在此处更新时间窗口
    if use_staging_time_range:
        step_logger.step("检测staging_raw实际时间范围")
        try:
            from app.adapters.db.gateway import get_staging_time_range

            with get_conn(settings) as conn:
                min_time, max_time, count = get_staging_time_range(
                    conn, settings.merge.tz.default_station_tz
                )

            if count > 0 and min_time and max_time:
                # 更新时间窗口
                original_window_start = window_start_utc
                original_window_end = window_end_utc
                window_start_utc = min_time
                window_end_utc = max_time

                step_logger.step(
                    "时间窗口已更新",
                    original_start=original_window_start.isoformat(),
                    original_end=original_window_end.isoformat(),
                    new_start=window_start_utc.isoformat(),
                    new_end=window_end_utc.isoformat(),
                    data_count=count,
                )

                logger.info(
                    "基于staging_raw数据更新时间窗口",
                    extra={
                        "event": "run_all.time_window_updated",
                        "original_window": {
                            "start": original_window_start.isoformat(),
                            "end": original_window_end.isoformat(),
                        },
                        "new_window": {
                            "start": window_start_utc.isoformat(),
                            "end": window_end_utc.isoformat(),
                        },
                        "data_count": count,
                        "time_range_source": "staging_raw",
                    },
                )
            else:
                step_logger.step(
                    "staging_raw无数据，保持原时间窗口",
                    start=window_start_utc.isoformat(),
                    end=window_end_utc.isoformat(),
                )
                logger.warning(
                    "staging_raw表中没有数据，保持原始时间窗口",
                    extra={
                        "event": "run_all.time_window_unchanged",
                        "reason": "staging_raw表为空或无可解析数据",
                        "data_count": count,
                    },
                )
        except Exception as e:
            step_logger.step(
                "时间窗口检测失败，保持原窗口",
                error=str(e),
                start=window_start_utc.isoformat(),
                end=window_end_utc.isoformat(),
            )
            logger.error(
                "从staging_raw获取时间范围失败，保持原始时间窗口",
                extra={
                    "event": "run_all.time_window_detection_failed",
                    "error": str(e),
                    "original_window": {
                        "start": window_start_utc.isoformat(),
                        "end": window_end_utc.isoformat(),
                    },
                },
            )

    step_logger.step("开始数据合并阶段")
    t1 = time.perf_counter()
    merge_stats = merge_window(settings, window_start_utc, window_end_utc)
    merge_ms = int((time.perf_counter() - t1) * 1000)
    step_logger.step(
        "数据合并完成",
        result=f"耗时 {merge_ms/1000:.2f} 秒",
        merged_rows=(
            merge_stats.get("rows_merged", 0) if isinstance(merge_stats, dict) else 0
        ),
    )

    # 记录合并统计指标
    if merge_stats and isinstance(merge_stats, dict):
        input_rows = merge_stats.get("rows_input", 0)
        output_rows = merge_stats.get("rows_merged", 0)
        deduped_rows = merge_stats.get("rows_deduped", 0)

        step_logger.validation(
            "数据合并结果验证",
            output_rows > 0,
            f"输入: {input_rows}, 输出: {output_rows}, 去重: {deduped_rows}",
        )

        log_merge_statistics(
            input_rows=input_rows,
            output_rows=output_rows,
            duplicates_removed=deduped_rows,
            merge_time_seconds=merge_ms / 1000,
            data_time_range={
                "start": window_start_utc.isoformat(),
                "end": window_end_utc.isoformat(),
            },
            logger=logger,
        )

    # 统计 tz 兜底数量（窗口内）
    tz_fallback_count = 0
    try:
        with get_conn(settings) as conn:
            # 确保使用UTC时区并格式化为标准ISO格式
            start_utc_str = (
                window_start_utc.astimezone(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            )
            end_utc_str = (
                window_end_utc.astimezone(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            )
            tz_fallback_count = count_tz_fallback(
                conn,
                start_utc=start_utc_str,
                end_utc=end_utc_str,
                default_station_tz=settings.merge.tz.default_station_tz,
            )
    except Exception:
        tz_fallback_count = 0

    # 统计 perf 日志中的背压事件（enter/exit 次数）
    perf_path = run_dir / "perf.ndjson"
    backpressure_enter = 0
    backpressure_exit = 0
    perf_batches_cost: list[int] = []
    perf_fail_rates: list[float] = []
    if perf_path.exists():
        try:
            for line in perf_path.read_text(encoding="utf-8").splitlines():
                if '"event": "backpressure.enter"' in line:
                    backpressure_enter += 1
                    try:
                        obj = json.loads(line)
                        fr = obj.get("fail_rate") or obj.get("extra", {}).get(
                            "fail_rate"
                        )
                        if fr is not None:
                            perf_fail_rates.append(float(fr))
                    except Exception:
                        pass
                elif '"event": "backpressure.exit"' in line:
                    backpressure_exit += 1
                elif '"event": "ingest.copy.batch"' in line:
                    try:
                        obj = json.loads(line)
                        cost = obj.get("batch_cost_ms") or obj.get("extra", {}).get(
                            "batch_cost_ms"
                        )
                        if cost is not None:
                            perf_batches_cost.append(int(cost))

                    except Exception:
                        pass
        except Exception:
            pass

    # 统计 SQL 慢语句 Top（按 sql_cost_ms 排序，截取前 N，可配置 logging.sql.top_n_slow）
    slow_sql_top: list[SqlStat] = []
    sql_path = run_dir / "sql.ndjson"
    top_n = max(1, int(getattr(settings.logging.sql, "top_n_slow", 5)))
    if sql_path.exists():
        try:
            rows: list[tuple[str, float, int]] = []
            for line in sql_path.read_text(encoding="utf-8").splitlines():
                # 简易解析：寻找键字段
                if '"event":"db.exec.succeeded"' in line and '"sql_cost_ms":' in line:
                    # 尝试宽松解析
                    try:
                        obj = json.loads(line)
                        sql_cost = float(
                            obj.get("sql_cost_ms")
                            or obj.get("extra", {}).get("sql_cost_ms")
                            or 0
                        )
                        affected = int(
                            obj.get("affected_rows")
                            or obj.get("extra", {}).get("affected_rows")
                            or 0
                        )
                        # 这里不包含完整 SQL，取 target_table + window 简短摘要
                        sql_summary = f"merge fact_measurements {obj.get('window_start') or obj.get('extra', {}).get('window_start')}→{obj.get('window_end') or obj.get('extra', {}).get('window_end')}"
                        rows.append((sql_summary, sql_cost, affected))
                    except Exception:
                        continue
            rows.sort(key=lambda x: x[1], reverse=True)
            for s, c, a in rows[:top_n]:
                slow_sql_top.append(SqlStat(sql=s, cost_ms=c, affected_rows=a))
        except Exception:
            pass

    # 诊断聚合：P50/P90/P95/P99 + 失败率 + 样本计数
    def _p_tile(vals: List[int], q: float) -> int:
        if not vals:
            return 0
        s: List[int] = sorted(vals)
        idx = int(q * (len(s) - 1))
        return s[idx]

    diagnostics: Dict[str, Any] = {
        "p50_batch_ms": _p_tile(perf_batches_cost, 0.50),
        "p90_batch_ms": _p_tile(perf_batches_cost, 0.90),
        "p95_batch_ms": _p_tile(perf_batches_cost, 0.95),
        "p99_batch_ms": _p_tile(perf_batches_cost, 0.99),
        "max_batch_ms": (max(perf_batches_cost) if perf_batches_cost else 0),
        "min_batch_ms": (min(perf_batches_cost) if perf_batches_cost else 0),
        "avg_fail_rate": (
            (sum(perf_fail_rates) / len(perf_fail_rates)) if perf_fail_rates else 0.0
        ),
        "p95_fail_rate": (
            (
                _p_tile([int(fr * 1_000_000) for fr in perf_fail_rates], 0.95)
                / 1_000_000.0
            )
            if perf_fail_rates
            else 0.0
        ),
        "max_fail_rate": (max(perf_fail_rates) if perf_fail_rates else 0.0),
        "samples_count": len(perf_batches_cost),
        "backpressure_enter": backpressure_enter,
        "backpressure_exit": backpressure_exit,
    }

    # 统一 task.summary 输出
    summary_collector = TaskSummaryCollector(
        rows_total=int(copy_stats.get("rows_read", 0)),
        rows_merged=(
            int(merge_stats.get("rows_merged", 0))
            if isinstance(merge_stats, dict)
            else 0
        ),
        backpressure_count=int(backpressure_enter),
        diagnostics=diagnostics,
    )
    # 以 copy 与 merge 总耗时估算 rows_per_sec 由 collector 计算（基于 duration_ms）
    # 这里我们将“任务开始”为 copy 阶段起点
    # 重置任务开始时间为 copy 阶段开始，便于计算行速率
    object.__setattr__(summary_collector, "started_ts", t0)
    # 说明：
    # - CopyStats 字段：files_total/files_succeeded/files_failed/rows_read/rows_loaded/rows_rejected/bytes_read
    # - MergeStats 字段：affected_rows/rows_input/rows_deduped/rows_merged/dedup_ratio/sql_cost_ms/rows_per_sec（可选）
    # - diagnostics：汇总 p50/p90/p95/p99 等批耗时与失败率、背压进入与退出计数

    summary_dict = summary_collector.as_dict()
    # 将合并统计也放入 summary.merge 字段，便于统一读取
    summary_dict.update(
        {
            "timing_ms": {"copy_total_ms": copy_ms, "merge_total_ms": merge_ms},
            "diagnostics": diagnostics,
            "tz_fallback_count": tz_fallback_count,
            "slow_sql_top": [
                {"sql": s.sql, "cost_ms": s.cost_ms, "affected_rows": s.affected_rows}
                for s in slow_sql_top
            ],
            "merge": merge_stats,
            "copy": copy_stats,
        }
    )

    (run_dir / "summary.json").write_text(
        json.dumps(summary_dict, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log_task_summary(EventLogger(logging.getLogger("root")), summary_collector)

    # 记录整体管道执行指标
    total_pipeline_time = time.perf_counter() - pipeline_start_time
    log_key_metrics(
        "管道执行完成",
        {
            "total_duration_seconds": round(total_pipeline_time, 2),
            "copy_duration_ms": copy_ms,
            "merge_duration_ms": merge_ms,
            "prepare_duration_seconds": round(prepare_time, 2),
            "staging_duration_seconds": round(staging_time, 2),
            "total_files_processed": (
                copy_stats.get("files_total", 0) if copy_stats else 0
            ),
            "total_rows_processed": copy_stats.get("rows_read", 0) if copy_stats else 0,
            "final_rows_merged": (
                merge_stats.get("rows_merged", 0)
                if isinstance(merge_stats, dict)
                else 0
            ),
            "backpressure_events": backpressure_enter,
            "tz_fallback_count": tz_fallback_count,
        },
        logger,
    )
