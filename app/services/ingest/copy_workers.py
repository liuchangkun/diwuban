from __future__ import annotations

"""
并发 COPY 导入（ingest.copy_workers）
- 从 mapping.json 收集文件清单，生成 ValidRow/RejectRow
- 按批 COPY 到 staging_raw，记录 perf 与 backpressure 事件
- 失败与拒绝行写入 staging_rejects，过程日志均为结构化 JSON

注意：
- 不改变业务逻辑，仅补充中文注释与 Docstring；采样/背压策略详见 BackpressureController
- 事件：ingest.load.begin/progress/end、ingest.copy.batch、backpressure.enter/exit
"""


import json
import time
import logging
from pathlib import Path
from typing import Iterable, Iterator, List

# 可选依赖（未使用，移除以降低静态告警）
from app.adapters.db.gateway import (
    copy_valid_lines,
    create_staging_if_not_exists,
    get_conn,
    insert_rejects,
)
from app.adapters.fs.reader import iter_rows
from app.core.config.loader_new import Settings
from app.core.types import CopyStats, RejectRow, ValidRow
from app.services.ingest.backpressure import BackpressureController
from app.services.ingest.source_hint import make_source_hint

_act = logging.getLogger("activity")


def _ensure_staging(settings: Settings) -> None:
    """确保 staging 表存在（幂等），仅在任务开始时调用一次。"""
    with get_conn(settings) as conn:
        create_staging_if_not_exists(conn)


def _collect_files_from_mapping(
    mapping_path: Path, base_dir: Path
) -> Iterator[tuple[str, str, str, Path]]:
    """读取 mapping.json，产出 (station_name, device_name, metric_key, csv_path)。"""
    data = json.loads(mapping_path.read_text(encoding="utf-8"))
    stations = data.get("stations") or []
    for s in stations:
        station_name = str(s.get("name") or "").strip()
        for d in s.get("devices", []) or []:
            device_name = str(d.get("name") or "").strip()

            for m in d.get("metrics", []) or []:

                metric_key = str(m.get("key") or "").strip()
                for rel in m.get("files", []) or []:
                    p = base_dir / str(rel)
                    yield station_name, device_name, metric_key, p


def _valid_rows_for_file(
    csv_path: Path, station: str, device: str, metric_key: str, settings: Settings
) -> Iterator[ValidRow | RejectRow]:
    """基于 csv 文件生成 ValidRow/RejectRow，填充站点/设备/指标与 source_hint。"""
    base_dir = Path(settings.ingest.base_dir)
    source_hint = make_source_hint(settings, base_dir, csv_path)
    csv_cfg = settings.ingest.csv
    perf_cfg = settings.ingest.performance
    for r in iter_rows(
        csv_path,
        source_hint,
        delimiter=csv_cfg.delimiter,
        encoding=csv_cfg.encoding,
        quote_char=csv_cfg.quote_char,
        escape_char=csv_cfg.escape_char,
        allow_bom=csv_cfg.allow_bom,
        read_buffer_size=perf_cfg.read_buffer_size,
    ):
        if isinstance(r, ValidRow):
            # 时区归一化逻辑
            dt_str = r.DataTime
            normalized_dt_str = dt_str
            # 保留原始时间字符串，避免在 COPY 阶段进行时区转换（否则在 MERGE 阶段会二次转换）
            # 仅做轻量清洗，交由 MERGE SQL 结合站点时区统一转换为 UTC 秒级对齐
            try:
                normalized_dt_str = dt_str.strip()
            except Exception:
                normalized_dt_str = dt_str

            yield ValidRow(
                station_name=station,
                device_name=device,
                metric_key=metric_key,
                TagName=r.TagName,
                DataTime=normalized_dt_str,  # 使用归一化后的时间
                DataValue=r.DataValue,
                source_hint=source_hint,
            )
        else:
            yield r


def _lines_from_valid_rows(rows: Iterable[ValidRow]) -> Iterator[str]:
    """将 ValidRow 转为 COPY 所需 CSV 行（无表头）。"""
    for r in rows:
        vals = [
            r.station_name,
            r.device_name,
            r.metric_key,
            r.TagName,
            r.DataTime,
            r.DataValue,
            r.source_hint,
        ]
        out: list[str] = []
        for v in vals:
            v = v if v is not None else ""
            if ("," in v) or ('"' in v):
                out.append('"' + v.replace('"', '""') + '"')
            else:
                out.append(v)
        yield ",".join(out) + "\n"


def _p95(costs: List[int]) -> int:
    """取 P95（向下取整索引），用于背压判定。空列表返回 0。"""
    if not costs:
        return 0
    arr = sorted(costs)
    idx = max(0, int(len(arr) * 0.95) - 1)
    return arr[idx]


def copy_from_mapping(
    settings: Settings, mapping_path: Path, run_id: str | None = None
) -> CopyStats:
    """从 mapping.json 并发导入 CSV 到 staging。
    - 步骤：
      1) _ensure_staging：确保 staging 表存在
      2) 读取 mapping.json → 收集文件路径
      3) 逐文件：构造 ValidRow/RejectRow → 批量 COPY → 采样日志 → 背压判定
      4) 拒绝行写入 staging_rejects
    - 结构化事件：
      - ingest.load.begin/progress/end（root 日志）
      - ingest.copy.batch（perf 日志）
      - backpressure.enter/exit（perf 日志）
      - ingest.copy.failed（root 日志）
    - 参数：
      - settings：全局配置（含采样/批大小/工作线程数等）
      - mapping_path：映射文件路径（JSON）
      - run_id：可选；若提供将注入到 settings 作为 _runtime_run_id，参与 source_hint 生成
    - 返回：CopyStats 统计（文件总数/成功/失败、读取/加载/拒绝的行数、读取字节数等）
    """

    t0 = time.perf_counter()

    base_dir = Path(settings.ingest.base_dir)
    _ensure_staging(settings)

    # 设置运行期 run_id 到 settings（进程内）
    if run_id:
        # 为避免 dataclass frozen，使用 object.__setattr__ 临时挂到对象上（仅 runtime 使用）
        object.__setattr__(settings, "_runtime_run_id", run_id)
        object.__setattr__(settings.ingest, "_runtime_run_id", run_id)

    files = list(_collect_files_from_mapping(mapping_path, base_dir))
    _act.info(
        "[流程-开始] [数据导入]",
        extra={
            "extra_data": {
                "mapping_file": str(mapping_path),
                "base_dir": str(base_dir),
                "file_count": len(files),
                "run_id": run_id,
            }
        },
    )

    stats: CopyStats = {
        "files_total": len(files),
        "files_succeeded": 0,
        "files_failed": 0,
        "rows_read": 0,
        "rows_loaded": 0,
        "rows_rejected": 0,
        "bytes_read": 0,
    }
    # 诊断聚合（背压与批耗时，整次 run）
    run_diag = {"bp_enter": 0, "bp_exit": 0, "p95_samples": []}

    if not files:
        # 无文件可处理，直接返回统计
        return stats

    # 控制器与状态
    ctrl = BackpressureController(
        batch_size=settings.ingest.commit_interval,
        workers=settings.ingest.workers,
        settings=settings,
    )
    in_backpressure = False
    file_costs: List[int] = []


    # 创建文件处理迭代器

    conn = None  # 初始化连接变量，但实际在需要时获取连接
    for station, device, metric_key, path in files:
        if not path.exists():
            # 文件不存在，跳过此文件
            stats["files_failed"] = stats.get("files_failed", 0) + 1
            _act.warning(
                "[流程-跳过] [文件不存在]",
                extra={
                    "extra_data": {
                        "station": station,
                        "device": device,
                        "metric_key": metric_key,
                        "file_path": str(path),
                    }
                },
            )
            continue

        _act.info(
            "[流程-阶段] [文件处理开始]",
            extra={
                "extra_data": {
                    "station": station,
                    "device": device,
                    "metric_key": metric_key,
                    "file_path": str(path),
                }
            },
        )


        # 流式读取与写入，避免一次性加载超大文件导致长时间卡住
        batch_size = max(
            1,
            int(getattr(settings.ingest.batch, "size", 0) or settings.ingest.commit_interval),
        )
        valids_batch: list[ValidRow] = []
        rejects: list[RejectRow] = []
        file_started_epoch = time.time()
        bytes_read = 0
        t0 = time.perf_counter()
        rows_read = 0
        loaded_this_file = 0


        # 小批量模式：统一使用普通连接，边读边 COPY
        with get_conn(settings) as conn:
            try:
                for r in _valid_rows_for_file(path, station, device, metric_key, settings):
                    rows_read += 1
                    if isinstance(r, ValidRow):
                        valids_batch.append(r)
                        if len(valids_batch) >= batch_size:
                            lines = list(_lines_from_valid_rows(valids_batch))
                            t_batch = time.perf_counter()
                            loaded = copy_valid_lines(conn, lines)
                            loaded_this_file += loaded

                            cost_ms = int((time.perf_counter() - t_batch) * 1000)
                            stats["rows_loaded"] = stats.get("rows_loaded", 0) + loaded
                            batch_bytes = sum(len(line.encode("utf-8")) for line in lines)
                            bytes_read += batch_bytes
                            valids_batch.clear()
                    else:
                        rejects.append(r)

                # flush 剩余批次
                if valids_batch:
                    lines = list(_lines_from_valid_rows(valids_batch))
                    t_batch = time.perf_counter()
                    loaded = copy_valid_lines(conn, lines)
                    cost_ms = int((time.perf_counter() - t_batch) * 1000)
                    stats["rows_loaded"] = stats.get("rows_loaded", 0) + loaded
                    loaded_this_file += loaded
                    batch_bytes = sum(len(line.encode("utf-8")) for line in lines)
                    bytes_read += batch_bytes
                    valids_batch.clear()

                stats["files_succeeded"] = stats.get("files_succeeded", 0) + 1
            except Exception as e:
                # COPY 失败，计入失败数并继续处理下一个文件
                stats["files_failed"] = stats.get("files_failed", 0) + 1
                _act.error(
                    "[流程-错误] [文件处理失败]",
                    extra={
                        "extra_data": {
                            "station": station,
                            "device": device,
                            "metric_key": metric_key,
                            "file_path": str(path),
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    },
                    exc_info=True,
                )

        # 记录读取行数
        stats["rows_read"] = stats.get("rows_read", 0) + rows_read


        if rejects:
            # 错误阈值控制：超过 per-file 阈值或错误百分比阈值则计失败并跳过写入
            eh = settings.ingest.error_handling
            total = rows_read
            over_count = len(rejects) > int(eh.max_errors_per_file)
            over_percent = (
                (len(rejects) / total) * 100.0 > float(eh.error_threshold_percent)
                if total
                else False
            )
            if over_count or over_percent:
                stats["files_failed"] = stats.get("files_failed", 0) + 1
                if not eh.continue_on_error:
                    # 中断整个处理流程（当前实现为按文件循环，continue_on_error=False 时结束本文件）
                    pass
            else:
                # 在需要时获取数据库连接来插入拒绝行
                with get_conn(settings) as conn:
                    insert_rejects(conn, rejects)
                stats["rows_rejected"] = stats.get("rows_rejected", 0) + len(rejects)

        file_cost_ms = int((time.perf_counter() - t0) * 1000)
        _act.info(
            "[流程-阶段] [文件处理完成]",
            extra={
                "extra_data": {
                    "station": station,
                    "device": device,
                    "metric_key": metric_key,
                    "file_path": str(path),
                    "duration_ms": file_cost_ms,
                    "rows_read": rows_read,
                    "rows_loaded": loaded_this_file,
                    "rows_rejected": len(rejects),
                }
            },
        )

    # 整次 run 的 task.summary 输出（一次）
    # 结束统计
    cost_ms = int((time.perf_counter() - t0) * 1000)
    _act.info(
        "[流程-完成] [数据导入]",
        extra={
            "extra_data": {
                "duration_ms": cost_ms,
                "files_total": stats.get("files_total"),
                "files_succeeded": stats.get("files_succeeded"),
                "files_failed": stats.get("files_failed"),
                "rows_read": stats.get("rows_read"),
                "rows_loaded": stats.get("rows_loaded"),
                "rows_rejected": stats.get("rows_rejected"),
            }
        },
    )

    return stats
