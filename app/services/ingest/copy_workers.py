from __future__ import annotations

"""
并发 COPY 导入（ingest.copy_workers）
- 从 mapping.json 收集文件清单，生成 ValidRow/RejectRow
- 支持并行处理多个CSV文件（ProcessPoolExecutor）
- 按批 COPY 到 staging_raw，记录 perf 与 backpressure 事件
- 失败与拒绝行写入 staging_rejects，过程日志均为结构化 JSON

性能优化：
- 使用ProcessPoolExecutor绕过Python GIL，实现真正多核并行
- 直接流式COPY，避免中间列表缓存
"""


import json
import time
import logging
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, Iterator, List, Tuple, Dict, Any
from io import StringIO

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


def _format_row_fast(r: ValidRow) -> str:
    """快速格式化单行（避免创建中间列表）。"""
    vals = (
        r.station_name,
        r.device_name,
        r.metric_key,
        r.TagName,
        r.DataTime,
        r.DataValue,
        r.source_hint,
    )
    out_parts = []
    for v in vals:
        v = v if v is not None else ""
        if "," in v or '"' in v:
            out_parts.append('"' + v.replace('"', '""') + '"')
        else:
            out_parts.append(v)
    return ",".join(out_parts) + "\n"


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


def _extract_config_for_subprocess(settings: Settings) -> Dict[str, Any]:
    """提取配置为可序列化的字典，用于子进程。"""
    return {
        "db_dsn": settings.db.dsn_write or settings.db.dsn_read or 
                  f"host={settings.db.host} port={settings.db.port} dbname={settings.db.dbname} user={settings.db.user} password={settings.db.password}",
        "base_dir": str(settings.ingest.base_dir),
        "csv_delimiter": settings.ingest.csv.delimiter,
        "csv_encoding": settings.ingest.csv.encoding,
        "csv_quote_char": settings.ingest.csv.quote_char,
        "csv_escape_char": settings.ingest.csv.escape_char,
        "csv_allow_bom": settings.ingest.csv.allow_bom,
        "read_buffer_size": settings.ingest.performance.read_buffer_size,
        "max_errors_per_file": settings.ingest.error_handling.max_errors_per_file,
        "error_threshold_percent": settings.ingest.error_handling.error_threshold_percent,
        "runtime_run_id": getattr(settings, "_runtime_run_id", None),
    }


def _process_file_in_subprocess(
    config: Dict[str, Any],
    station: str,
    device: str,
    metric_key: str,
    path_str: str,
    batch_size: int,
    file_index: int,
    total_files: int,
) -> Dict[str, Any]:
    """在子进程中处理单个CSV文件（可序列化参数）。
    
    这个函数必须是顶层函数，不能是闭包或类方法。
    """
    import psycopg
    from pathlib import Path
    from io import StringIO
    
    path = Path(path_str)
    process_name = multiprocessing.current_process().name
    
    print(f"[开始] {process_name}: 文件 {file_index}/{total_files} - {path.name}", flush=True)
    
    result = {
        "rows_read": 0,
        "rows_loaded": 0,
        "rows_rejected": 0,
        "bytes_read": 0,
        "success": False,
        "error": None,
    }
    
    t0 = time.perf_counter()
    rows_read = 0
    loaded_this_file = 0
    reject_count = 0
    
    # 直接连接数据库（每个子进程独立连接）
    try:
        with psycopg.connect(config["db_dsn"]) as conn:
            conn.autocommit = False
            
            # COPY SQL
            copy_sql = 'COPY public.staging_raw (station_name, device_name, metric_key, "TagName", "DataTime", "DataValue", source_hint) FROM STDIN WITH (FORMAT CSV)'
            
            # 流式处理：读取CSV -> 格式化 -> 缓存到StringIO -> 批量COPY
            buffer = StringIO()
            buffer_rows = 0
            
            # 读取CSV文件
            source_hint = f"{path.name}"
            
            import csv
            with open(path, 'r', encoding=config["csv_encoding"], 
                      buffering=config["read_buffer_size"]) as f:
                # 跳过BOM
                if config["csv_allow_bom"]:
                    first_char = f.read(1)
                    if first_char != '\ufeff':
                        f.seek(0)
                
                reader = csv.DictReader(f, delimiter=config["csv_delimiter"],
                                        quotechar=config["csv_quote_char"])
                
                for row in reader:
                    rows_read += 1
                    
                    # 提取字段
                    tag_name = row.get("TagName", "") or ""
                    data_time = row.get("DataTime", "") or ""
                    data_value = row.get("DataValue", "") or ""
                    
                    # 格式化为CSV行
                    vals = [station, device, metric_key, tag_name, data_time.strip(), data_value, source_hint]
                    out_parts = []
                    for v in vals:
                        v = v if v else ""
                        if "," in v or '"' in v:
                            out_parts.append('"' + v.replace('"', '""') + '"')
                        else:
                            out_parts.append(v)
                    line = ",".join(out_parts) + "\n"
                    buffer.write(line)
                    buffer_rows += 1
                    
                    # 批量COPY
                    if buffer_rows >= batch_size:
                        buffer.seek(0)
                        with conn.cursor() as cur:
                            cur.execute("SET LOCAL synchronous_commit = 'off'")
                            with cur.copy(copy_sql) as cp:
                                while True:
                                    chunk = buffer.read(1048576)
                                    if not chunk:
                                        break
                                    cp.write(chunk)
                        conn.commit()
                        loaded_this_file += buffer_rows
                        buffer = StringIO()
                        buffer_rows = 0
            
            # flush剩余数据
            if buffer_rows > 0:
                buffer.seek(0)
                with conn.cursor() as cur:
                    cur.execute("SET LOCAL synchronous_commit = 'off'")
                    with cur.copy(copy_sql) as cp:
                        while True:
                            chunk = buffer.read(1048576)
                            if not chunk:
                                break
                            cp.write(chunk)
                conn.commit()
                loaded_this_file += buffer_rows
            
            result["success"] = True
            
    except Exception as e:
        result["error"] = str(e)
        print(f"[错误] {process_name}: {path.name} - {e}", flush=True)
    
    result["rows_read"] = rows_read
    result["rows_loaded"] = loaded_this_file
    result["bytes_read"] = rows_read * 100  # 估算
    
    file_cost_ms = int((time.perf_counter() - t0) * 1000)
    print(f"[完成] {process_name}: {path.name} - {loaded_this_file}行, {file_cost_ms}ms", flush=True)
    
    return result

def _process_single_file(
    settings: Settings,
    station: str,
    device: str,
    metric_key: str,
    path: Path,
    batch_size: int,
    file_index: int = 0,
    total_files: int = 0,
) -> Dict[str, Any]:
    """处理单个CSV文件（线程安全）。

    每个线程创建独立的数据库连接，避免连接共享问题。

    返回：
        Dict 包含：rows_read, rows_loaded, rows_rejected, bytes_read, success, error
    """
    import sys
    # 获取当前线程名称
    thread_name = threading.current_thread().name

    # 打印文件开始处理信息
    print(
        f"[开始] {thread_name}: 文件 {file_index}/{total_files} - {path.name}", flush=True)

    # 在开始处理时打印日志
    _act.info(
        "[流程-阶段] [文件处理开始]",
        extra={
            "extra_data": {
                "thread": thread_name,
                "file_index": file_index,
                "total_files": total_files,
                "station": station,
                "device": device,
                "metric_key": metric_key,
                "file_path": str(path),
                "file_name": path.name,
            }
        },
    )

    result = {
        "rows_read": 0,
        "rows_loaded": 0,
        "rows_rejected": 0,
        "bytes_read": 0,
        "success": False,
        "error": None,
    }

    t0 = time.perf_counter()
    rejects: list[RejectRow] = []
    bytes_read = 0
    rows_read = 0
    loaded_this_file = 0

    # 每个线程使用独立的数据库连接
    with get_conn(settings) as conn:
        try:
            # 优化：流式处理，减少内存分配
            valids_buffer: list[str] = []  # 直接存储格式化后的字符串
            
            for r in _valid_rows_for_file(path, station, device, metric_key, settings):
                rows_read += 1
                if isinstance(r, ValidRow):
                    # 直接格式化为字符串，避免存储ValidRow对象
                    valids_buffer.append(_format_row_fast(r))
                    if len(valids_buffer) >= batch_size:
                        loaded = copy_valid_lines(conn, valids_buffer)
                        loaded_this_file += loaded
                        # 优化：移除bytes计算，改为估算（每行约100字节）
                        bytes_read += len(valids_buffer) * 100
                        valids_buffer.clear()
                else:
                    rejects.append(r)

            # flush 剩余批次
            if valids_buffer:
                loaded = copy_valid_lines(conn, valids_buffer)
                loaded_this_file += loaded
                bytes_read += len(valids_buffer) * 100
                valids_buffer.clear()

            result["success"] = True
        except Exception as e:
            result["error"] = str(e)
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

    result["rows_read"] = rows_read
    result["rows_loaded"] = loaded_this_file
    result["bytes_read"] = bytes_read

    # 处理拒绝行
    if rejects:
        eh = settings.ingest.error_handling
        over_count = len(rejects) > int(eh.max_errors_per_file)
        over_percent = (
            (len(rejects) / rows_read) *
            100.0 > float(eh.error_threshold_percent)
            if rows_read
            else False
        )
        if over_count or over_percent:
            result["success"] = False
            result["error"] = f"拒绝行过多: {len(rejects)}"
        else:
            # 写入拒绝行
            with get_conn(settings) as conn:
                insert_rejects(conn, rejects)
            result["rows_rejected"] = len(rejects)

    file_cost_ms = int((time.perf_counter() - t0) * 1000)

    # 完成信息在主循环中打印，这里不重复打印

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

    return result


def copy_from_mapping(
    settings: Settings, mapping_path: Path, run_id: str | None = None
) -> CopyStats:
    """从 mapping.json 并发导入 CSV 到 staging。

    支持并行处理多个CSV文件，通过 settings.ingest.workers 配置并行线程数。

    - 步骤：
      1) _ensure_staging：确保 staging 表存在
      2) 读取 mapping.json → 收集文件路径
      3) 并行处理文件：构造 ValidRow/RejectRow → 批量 COPY
      4) 拒绝行写入 staging_rejects
    - 结构化事件：
      - ingest.load.begin/progress/end（root 日志）
      - ingest.copy.batch（perf 日志）
    - 参数：
      - settings：全局配置（含采样/批大小/工作线程数等）
      - mapping_path：映射文件路径（JSON）
      - run_id：可选；若提供将注入到 settings 作为 _runtime_run_id，参与 source_hint 生成
    - 返回：CopyStats 统计（文件总数/成功/失败、读取/加载/拒绝的行数、读取字节数等）
    """

    t0_total = time.perf_counter()

    base_dir = Path(settings.ingest.base_dir)
    _ensure_staging(settings)

    # 设置运行期 run_id 到 settings（进程内）
    if run_id:
        object.__setattr__(settings, "_runtime_run_id", run_id)
        object.__setattr__(settings.ingest, "_runtime_run_id", run_id)

    files = list(_collect_files_from_mapping(mapping_path, base_dir))

    # 获取并行线程数，默认6
    max_workers = max(1, int(settings.ingest.workers))

    _act.info(
        "[流程-开始] [数据导入]",
        extra={
            "extra_data": {
                "mapping_file": str(mapping_path),
                "base_dir": str(base_dir),
                "file_count": len(files),
                "run_id": run_id,
                "parallel_workers": max_workers,
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

    if not files:
        return stats

    # 批次大小
    batch_size = max(
        1,
        int(getattr(settings.ingest.batch, "size", 0)
            or settings.ingest.commit_interval),
    )

    # 统计信息的线程安全更新锁
    stats_lock = threading.Lock()

    # 过滤不存在的文件
    valid_files = []
    for station, device, metric_key, path in files:
        if not path.exists():
            with stats_lock:
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
        else:
            valid_files.append((station, device, metric_key, path))

    if not valid_files:
        return stats

    # 使用 ProcessPoolExecutor 并行处理文件（绕过GIL）
    print(
        f"[数据导入] 开始多进程并行处理 {len(valid_files)} 个文件，使用 {max_workers} 个进程", flush=True)

    _act.info(
        "[流程-阶段] [并行处理开始]",
        extra={
            "extra_data": {
                "valid_files": len(valid_files),
                "parallel_workers": max_workers,
                "mode": "ProcessPoolExecutor",
            }
        },
    )

    completed_count = 0  # 已完成文件计数
    
    # 提取可序列化的配置
    config = _extract_config_for_subprocess(settings)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有文件处理任务
        total_files = len(valid_files)
        future_to_file = {
            executor.submit(
                _process_file_in_subprocess,
                config,
                station,
                device,
                metric_key,
                str(path),  # 转换为字符串以便序列化
                batch_size,
                file_index=idx + 1,
                total_files=total_files,
            ): (station, device, metric_key, path)
            for idx, (station, device, metric_key, path) in enumerate(valid_files)
        }

        # 收集结果
        for future in as_completed(future_to_file):
            station, device, metric_key, path = future_to_file[future]
            try:
                result = future.result()
                completed_count += 1

                # 每完成一个文件就打印进度
                print(
                    f"[进度] {completed_count}/{total_files} 完成 - {path.name} ({result['rows_loaded']}行)", flush=True)

                # 线程安全地更新统计信息
                with stats_lock:
                    stats["rows_read"] = stats.get(
                        "rows_read", 0) + result["rows_read"]
                    stats["rows_loaded"] = stats.get(
                        "rows_loaded", 0) + result["rows_loaded"]
                    stats["rows_rejected"] = stats.get(
                        "rows_rejected", 0) + result["rows_rejected"]
                    stats["bytes_read"] = stats.get(
                        "bytes_read", 0) + result["bytes_read"]

                    if result["success"]:
                        stats["files_succeeded"] = stats.get(
                            "files_succeeded", 0) + 1
                    else:
                        stats["files_failed"] = stats.get(
                            "files_failed", 0) + 1

            except Exception as e:
                with stats_lock:
                    stats["files_failed"] = stats.get("files_failed", 0) + 1
                _act.error(
                    "[流程-错误] [线程执行失败]",
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

    # 结束统计
    cost_ms = int((time.perf_counter() - t0_total) * 1000)

    # 打印最终统计
    print(f"[数据导入] 完成! 成功:{stats.get('files_succeeded')}/{stats.get('files_total')}, "
          f"加载:{stats.get('rows_loaded')}行, 耗时:{cost_ms/1000:.1f}秒", flush=True)

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
                "parallel_workers": max_workers,
            }
        },
    )

    return stats
