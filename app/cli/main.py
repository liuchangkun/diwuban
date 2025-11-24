from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Tuple

import typer

from app.adapters.db import init_database
from app.core.config.loader_new import load_settings
from app.core.logging.setup import init_logging


def _parse_bool(val: str | None, default: bool = False) -> bool:
    if val is None:
        return default
    s = str(val).strip().lower()
    return s in ("1", "true", "yes", "y", "on")


def get_orchestrator_default_flags(
    config_dir: Path = Path("configs"),
) -> Tuple[bool, bool]:
    """读取 run-all 的两个开关默认值。
    优先级：ENV > configs/merge.yaml(run_all) > 代码缺省(False)
    ENV: ORCHESTRATOR_WITH_DEVICE_RUNNING_DEFAULT / ORCHESTRATOR_WITH_PRESENCE_DEFAULT
    merge.yaml keys (under run_all): device_running / presence
    """
    dev_default = True
    pres_default = True

    # YAML（可选）
    try:
        import yaml  # 项目已使用 yaml 依赖

        # 1) 首选 merge.yaml 的 run_all 段
        merge_yml = config_dir / "merge.yaml"
        if merge_yml.exists():
            data = yaml.safe_load(merge_yml.read_text(encoding="utf-8")) or {}
            ra = (data or {}).get("run_all", {}) or {}
            dev_default = bool(ra.get("device_running", dev_default))
            pres_default = bool(ra.get("presence", pres_default))
    except Exception:
        # 配置缺失或解析失败时，保持默认 False
        pass

    # ENV（最高优先级）
    dev_default = _parse_bool(
        os.getenv("ORCHESTRATOR_WITH_DEVICE_RUNNING_DEFAULT"), dev_default
    )
    pres_default = _parse_bool(
        os.getenv("ORCHESTRATOR_WITH_PRESENCE_DEFAULT"), pres_default
    )

    return dev_default, pres_default


# 计算动态默认值（模块加载时）
_DEV_RUN_DEFAULT, _PRES_DEFAULT = get_orchestrator_default_flags()

from app.services.ingest.prepare_dim import prepare_dim

ingest_workers_option = typer.Option(
    None, help="覆盖导入并发数（INGEST_WORKERS）", show_default=False
)
ingest_commit_interval_option = typer.Option(
    None, help="覆盖提交批大小（INGEST_COMMIT_INTERVAL）", show_default=False
)


def initialize_app():
    """初始化应用程序，包括日志与数据库连接池"""
    try:
        settings = load_settings(Path("configs"))
        try:
            init_logging("configs", settings.system.timezone.default)
        except Exception:
            pass
        init_database(settings)
        print("数据库连接池初始化成功")
    except Exception as e:
        print(f"数据库连接池初始化失败: {e}")


app = typer.Typer(
    help=(
        "CSV 高性能导入（方案A）："
        "prepare-dim / create-staging / ingest:copy / merge:fact / run-all / presence:compute"
    ),
)


@app.command()
def version() -> None:
    """打印版本/存活检查。
    示例：python -m app.cli.main version
    常见问题：无
    """
    initialize_app()
    typer.echo("ingest-cli ok")


# 预留：后续填充真实子命令


@app.command(
    name="prepare-dim",
    help=(
        "准备维表与映射（两阶段执行）：从 data_mapping.json 插入/更新 dim_* 与映射；"
        "阶段1（merge-fact前）：重建维度表；阶段2（merge-fact后）：生成规则表；"
        "示例：python -m app.cli.main prepare-dim config/data_mapping.json --stage 1；"
        "常见错误：JSON 结构缺失 name/key/files、数据库连接失败"
    ),
)
def cmd_prepare_dim(
    mapping: str = typer.Argument("configs/data_mapping.v2.json", help="data_mapping.json 路径（相对仓库根）"),
    stage: int | None = typer.Option(
        None,
        "--stage",
        help="执行阶段：1=阶段1（重建维度表），2=阶段2（生成规则表），不指定=完整流程"
    ),
) -> None:
    initialize_app()
    from app.core.config.loader_new import load_settings_with_sources as _lss
    import json as _json

    settings, _sources = _lss(Path("configs"))

    # 检查文件是否存在
    mapping_path = Path(mapping)
    if not mapping_path.exists():
        typer.echo(f"❌ 错误：文件不存在：{mapping}", err=True)
        typer.echo(f"💡 提示：默认路径是 configs/data_mapping.v2.json", err=True)
        raise typer.Exit(code=1)

    result = prepare_dim(settings, mapping_path, stage=stage)

    # 输出执行摘要
    typer.echo(_json.dumps(result, ensure_ascii=False, indent=2))


@app.command(
    name="create-staging",
    help=(
        "创建/幂等 staging_raw 与 staging_rejects（UNLOGGED）；"
        "示例：python -m app.cli.main create-staging；常见错误：数据库连接失败"
    ),
)
def cmd_create_staging() -> None:
    initialize_app()
    from app.services.ingest.create_staging import create_staging

    settings = load_settings(Path("configs"))
    create_staging(settings)


@app.command(
    name="ingest-copy",
    help=(
        "并发 COPY 导入 CSV 到 staging_raw；"
        "示例：python -m app.cli.main ingest-copy config/data_mapping.json；"
        "常见错误：路径带 data/ 前缀、文件不存在、CSV 列头缺失"
    ),
)
def cmd_ingest_copy(
    mapping: str = typer.Argument(..., help="data_mapping.json 路径"),
) -> None:
    initialize_app()
    from app.services.ingest.copy_workers import copy_from_mapping

    settings = load_settings(Path("configs"))
    stats = copy_from_mapping(settings, Path(mapping))
    typer.echo(f"copy done: {stats}")


@app.command(
    name="merge-fact",
    help=(
        "集合式合并：tz→UTC→秒级对齐→去重→UPSERT；"
        "示例：python -m app.cli.main merge-fact --window-start 'YYYY-MM-DD HH:MM:SS+08' --window-end 'YYYY-MM-DD HH:MM:SS+08'；"
        "常见错误：时间格式不正确；说明：输入支持 ISO8601（可带时区），未带时区按系统默认时区解析，内部统一转换为 UTC；对外展示统一为 +08 格式"
    ),
)
def cmd_merge_fact(
    window_start: str = typer.Option(..., help="起始时间（ISO8601）。不带时区按系统默认时区解析；对外展示统一为 +08 格式"),
    window_end: str = typer.Option(..., help="结束时间（ISO8601）。不带时区按系统默认时区解析；对外展示统一为 +08 格式"),
) -> None:
    initialize_app()
    settings = load_settings(Path("configs"))
    from app.services.ingest.merge_cli import run_merge_fact_command

    res = run_merge_fact_command(settings, window_start, window_end)
    import json as _json

    typer.echo(_json.dumps(res, ensure_ascii=False))


@app.command(
    name="data-report",
    help=(
        "生成数据质量报表：覆盖/越界/拒绝统计；"
        "示例：python -m app.cli.main data-report --window-start 'YYYY-MM-DD HH:MM:SS+08' --window-end 'YYYY-MM-DD HH:MM:SS+08'；"
        "说明：输入支持 ISO8601（可带时区），未带时区按系统默认时区解析；对外展示统一为 +08 格式"
    ),
)
def cmd_data_report(
    window_start: str = typer.Option(..., help="起始时间（ISO8601）。不带时区按系统默认时区解析；对外展示统一为 +08 格式"),
    window_end: str = typer.Option(..., help="结束时间（ISO8601）。不带时区按系统默认时区解析；对外展示统一为 +08 格式"),
    expected_interval: int = typer.Option(
        1, "--expected-interval", help="期望采样间隔（秒），用于覆盖率与缺口检测"
    ),
    top_k: int = typer.Option(100, "--top-k", help="各榜单 TopN 数量"),
    group_by: str = typer.Option(
        "metric",
        "--group-by",
        help="直方图分组维度：metric|device|station|source|batch",
    ),
) -> None:
    initialize_app()
    settings = load_settings(Path("configs"))
    from app.services.reporting.data_report_cli import run_data_report_command

    res = run_data_report_command(
        settings,
        window_start,
        window_end,
        expected_interval,
        top_k,
        group_by,
        run_dir=None,
    )
    import json as _json

    typer.echo(_json.dumps(res, ensure_ascii=False))


@app.command(
    name="check-mapping",
    help=(
        "只读一致性检查与路径建议；支持 --out 导出 JSON；"
        "常见错误：路径在 data/ 外或含 data/ 前缀"
    ),
)
def cmd_check_mapping(
    mapping: str = typer.Argument(..., help="data_mapping.json 路径（只读检查）"),
    out: str | None = typer.Option(
        None, help="将检查报告写入到该路径（JSON），默认打印到控制台"
    ),
    show_all: bool = typer.Option(
        False,
        "--show-all",
        help="默认只展示聚类的缺陷项（missing_files>0 或 with_data_prefix>0）；开启后展示全部",
    ),
) -> None:
    """只读一致性检查：
    - 检查是否含 data/ 前缀
    - 按严格规则（base_dir+相对路径）检查文件是否存在
    - 校验 schema 必填项：stations/devices/metrics/files/key/name
    - 仅输出建议，不修改文件
    示例：python -m app.cli.main check-mapping config/data_mapping.json --out mapping_report.json
    常见错误：路径带 data/ 前缀；文件不存在；结构缺失 key/files/name
    """
    import json as _json

    settings = load_settings(Path("configs"))
    from app.services.ingest.check_mapping_cli import run_check_mapping_command

    res = run_check_mapping_command(
        settings, Path(mapping), Path(out) if out else None, show_all
    )
    typer.echo(_json.dumps(res, ensure_ascii=False, indent=2))


@app.command(
    name="presence:compute",
    help=(
        "统计每秒(UTC)×站×设备的已有/需要计算指标名并写入 public.metrics_presence_per_second_device；"
        "默认全量，若表已有数据则增量+滚动7天"
    ),
)
def presence_compute(
    station_name: str | None = typer.Option(
        None,
        "--station-name",
        help="限定站点名称；默认全部站（当提供 --station-id 时忽略）",
    ),
    station_id: int | None = typer.Option(
        None, "--station-id", help="优先使用：按站点ID过滤；可与 --device-id 联用"
    ),
    device_id: int | None = typer.Option(
        None,
        "--device-id",
        help="可选：按设备ID过滤；若未提供 station_id 将自动根据设备ID推断其站点",
    ),
    start: str | None = typer.Option(
        None, "--start", help="起始时间（ISO8601）。不带时区按系统默认时区解析；对外展示统一为 +08 格式"
    ),
    end: str | None = typer.Option(
        None, "--end", help="结束时间（ISO8601）。不带时区按系统默认时区解析；对外展示统一为 +08 格式"
    ),
    batch_days: int = typer.Option(1, "--batch-days", help="按天分片大小"),
    rolling_days: int = typer.Option(7, "--rolling-days", help="增量时回退刷新近N天"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅显示计划，不执行写入"),
) -> None:
    initialize_app()
    settings = load_settings(Path("configs"))
    from app.services.reporting.presence_cli import run_presence_compute_command

    res = run_presence_compute_command(
        settings,
        station_name,
        station_id,
        device_id,
        start,
        end,
        batch_days,
        rolling_days,
        dry_run,
    )
    import json as _json

    typer.echo(_json.dumps(res, ensure_ascii=False))


@app.command(
    name="missing-metrics:compute",
    help=(
        "批量计算缺失指标：按设备×时间窗进行全量/增量计算；"
        "示例：python -m app.cli.main missing-metrics:compute --start '2025-01-01 00:00:00+08' --end '2025-02-28 23:59:59+08' "
        "[--station-id] [--device-id] [--window-hours 1] [--concurrency 3] "
        "[--dry-run/--no-dry-run] [--filter-running/--no-filter-running] [--filter-quality/--no-filter-quality]"
    ),
)
def cmd_missing_metrics_compute(
    start: str | None = typer.Option(None, "--start", help="起始时间（ISO8601，默认取fact表最早时间）"),
    end: str | None = typer.Option(None, "--end", help="结束时间（ISO8601，默认取fact表最晚时间）"),
    station_id: int | None = typer.Option(None, "--station-id", help="可选：限定站点ID"),
    device_id: int | None = typer.Option(None, "--device-id", help="可选：限定设备ID"),
    window_hours: int = typer.Option(1, "--window-hours", help="时间分片粒度（小时）"),
    concurrency: int = typer.Option(3, "--concurrency", help="并发度（线程数），建议≤连接池max"),
    dry_run: bool = typer.Option(False, "--dry-run/--no-dry-run", help="仅试运行，不写库"),
    filter_running: bool = typer.Option(True, "--filter-running/--no-filter-running", help="按运行态过滤"),
    filter_quality: bool = typer.Option(True, "--filter-quality/--no-filter-quality", help="仅使用质量=0的原始数据作为输入"),
    limit_devices: int | None = typer.Option(None, "--limit-devices", help="限设备数量（排障/演练用）"),
    limit_windows_per_device: int | None = typer.Option(None, "--limit-windows-per-device", help="每设备限窗口数（排障/演练用）"),
    use_presence_table: bool = typer.Option(True, "--use-presence-table/--no-use-presence-table", help="使用metrics_presence_per_second_device表动态查询指标"),
) -> None:
    """批量计算缺失指标（可全量）。

    注意：默认直接写入 fact_measurements（quality_status=1）。如需合规，请先将写入路径改为存储过程。
    """
    initialize_app()
    settings = load_settings(Path("configs"))

    from app.services.calculation.missing_metrics_batch import build_plan, run_missing_metrics_compute

    plan = build_plan(
        start=start, end=end, station_id=station_id, device_id=device_id,
        window_hours=window_hours, concurrency=concurrency, dry_run=dry_run,
        filter_running=filter_running, filter_quality=filter_quality,
        limit_devices=limit_devices, limit_windows_per_device=limit_windows_per_device,
        use_presence_table=use_presence_table,
    )

    res = run_missing_metrics_compute(plan)
    import json as _json
    typer.echo(_json.dumps(res, ensure_ascii=False))


@app.command(
    name="db-ping",
    help=(
        "免密连接测试；--verbose 输出 host/db/user(脱敏)/时区/版本；"
        "常见错误：.pgpass  无效、用户/库不匹配！"
    ),
)
def db_ping(
    verbose: bool = typer.Option(
        False, "--verbose", help="打印脱敏连接信息与数据库/时区信息"
    ),
) -> None:
    """免密连接测试。
    示例：python -m app.cli.main db-ping --verbose
    常见错误：.pgpass 未生效/权限不正确；host/db/user 与实际不符
    """
    settings = load_settings(Path("configs"))
    from app.services.admin.db_ping import run_db_ping

    res = run_db_ping(settings, verbose=verbose)
    import json as _json

    typer.echo(_json.dumps(res, ensure_ascii=False))


@app.command(
    name="run-all",
    help=(
        "一键执行完整流程：prepare-dim → create-staging → ingest-copy → merge-fact；"
        "可选自动窗口 --use-staging-time-range"
    ),
)
def cmd_run_all(
    mapping: str = typer.Argument(
        "configs/data_mapping.v2.json", help="data_mapping.json 路径"
    ),
    use_staging_time_range: bool = typer.Option(
        True,
        "--use-staging-time-range/--no-use-staging-time-range",
        help="自动探测 staging 时间范围作为合并窗口（默认开启，可用 --no-use-staging-time-range 关闭）",
    ),
    window_start: str | None = typer.Option(
        None, help="起始时间（ISO8601）。不带时区按系统默认时区解析并内部转换为 UTC；对外展示统一为 +08 格式"
    ),
    window_end: str | None = typer.Option(
        None, help="结束时间（ISO8601）。不带时区按系统默认时区解析并内部转换为 UTC；对外展示统一为 +08 格式"
    ),
    summary_json: str | None = typer.Option(
        None,
        "--summary-json",
        help="将执行摘要写入 JSON 文件（rows_loaded/rows_merged/window 等）",
    ),
    with_device_running: bool = typer.Option(
        _DEV_RUN_DEFAULT, "--with-device-running", help="合并后追加设备运行状态落地"
    ),
    with_presence: bool = typer.Option(
        _PRES_DEFAULT, "--with-presence", help="合并后按窗口执行 presence:compute"
    ),
    device_id: int | None = typer.Option(
        None, "--device-id", help="可选：限定设备ID，仅处理该设备"
    ),
) -> None:
    """完整流程执行：
    - 默认使用 mapping 文件路径
    - 若指定 --use-staging-time-range，将从 staging_raw 中计算窗口（min(ts_raw)~max(ts_raw)）
    - 否则使用 --window-start/--window-end
    - 若指定 --summary-json，写入执行摘要（便于 CI/采集）
    """
    # 在初始化日志/连接池之前，根据 configs/merge.yaml(run_all) 可选清空日志与数据库
    try:
        settings = load_settings(Path("configs"))
        import yaml  # type: ignore
        from pathlib import Path as _Path
        cfg_dir = getattr(getattr(settings.system, "directories", None), "configs", "configs")
        cfg_path = _Path(cfg_dir) / "merge.yaml"
        reset_logs = False
        reset_db = False
        if cfg_path.exists():
            data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            ra = (data or {}).get("run_all", {}) or {}
            reset_logs = bool(ra.get("reset_logs", False))
            reset_db = bool(ra.get("reset_db", False))
        if reset_logs or reset_db:
            from app.services.system.cleanup import clear_logs_directory, clear_database
            if reset_logs:
                try:
                    logs_dir = Path(getattr(getattr(settings.system, "directories", None), "logs", "logs"))
                    clear_logs_directory(logs_dir, backup_count=0)
                except Exception:
                    pass
            if reset_db:
                try:
                    clear_database(settings)
                except Exception:
                    pass
    except Exception:
        pass

    initialize_app()
    # 默认：提升日志到最丰富（DEBUG），包括根与常用命名空间
    try:
        import logging as _logging

        _logging.root.setLevel(_logging.DEBUG)
        for _h in list(_logging.root.handlers):
            try:
                _h.setLevel(_logging.DEBUG)
            except Exception:
                pass
        for _n in ("activity", "anomaly", "sql", "stderr"):
            try:
                _logging.getLogger(_n).setLevel(_logging.DEBUG)
            except Exception:
                pass
    except Exception:
        pass
    settings = load_settings(Path("configs"))

    # 进度打点（开始）
    import logging as _logging

    _act = _logging.getLogger("activity")
    try:
        _act.info(
            "[进度] run-all 开始",
            extra={
                "extra_data": {
                    "event": "run_all.start",
                    "mapping": mapping,
                    "use_staging_time_range": bool(use_staging_time_range),
                    "window_start": window_start,
                    "window_end": window_end,
                }
            },
        )
    except Exception:
        pass

    # 委托 orchestrator 执行（将 import 放入 try 以捕获导入错误）
    try:
        from app.services.run_all.orchestrator import run_all as _run_all

        summary = _run_all(
            settings=settings,
            mapping=mapping,
            use_staging_time_range=use_staging_time_range,
            window_start=window_start,
            window_end=window_end,
            summary_json=summary_json,
            with_device_running=with_device_running,
            with_presence=with_presence,
            with_device_phase=False,
            device_id=device_id,
        )
    except Exception:
        _logging.getLogger("error").exception(
            "run-all 失败", extra={"extra_data": {"event": "run_all.error"}}
        )
        raise

    # 进度打点（完成）
    try:
        _act.info(
            "[进度] run-all 完成",
            extra={
                "extra_data": {
                    "event": "run_all.done",
                    "window": (
                        summary.get("window") if isinstance(summary, dict) else None
                    ),
                    "copy": (
                        summary.get("copy_stats") if isinstance(summary, dict) else None
                    ),
                    "merge": (
                        summary.get("merge_stats")
                        if isinstance(summary, dict)
                        else None
                    ),
                }
            },
        )
    except Exception:
        pass

    import json as _json

    typer.echo(
        _json.dumps(
            {"ok": True, "message": "run-all 完成", "summary": summary},
            ensure_ascii=False,
        )
    )


# baseline:auto:compute command removed (2025-11-07)
# Reason: Quality checking feature deleted, baseline tables no longer used
# Archive location: _archive/baseline_feature_20251107/





@app.command(
    name="rules:diff:report",
    hidden=True,
    help=(
        "生成 A（正式）与 B（影子）的差异报告；可选导出CSV详情。\n"
        "示例：python -m app.cli.main rules:diff:report --out-dir reports --top-k 20"
    ),
)
def cmd_rules_diff_report(
    method: str = typer.Option(
        "stl_residual",
        "--method",
        help="影子算法方法：通常为 stl_residual",
        show_default=True,
    ),
    version: str = typer.Option(
        "vB_shadow",
        "--version",
        help="影子版本标识",
        show_default=True,
    ),
    out_dir: str | None = typer.Option(
        None, "--out-dir", help="可选：将CSV详情写入该目录"
    ),
    top_k: int = typer.Option(20, "--top-k", help="TopK 差异清单数量"),
) -> None:
    initialize_app()
    settings = load_settings(Path("configs"))
    from app.services.reporting.rules_diff_report import run_rules_diff_report

    res = run_rules_diff_report(
        settings,
        method=method,
        version=version,
        out_dir=out_dir,
        top_k=top_k,
    )

    import json as _json

    typer.echo(_json.dumps(res, ensure_ascii=False, indent=2))


@app.command(
    name="admin-clear-db",
    help="危险：清空 public 架构所有表数据（TRUNCATE + RESTART IDENTITY + CASCADE）；仅限 DEV",
)
def admin_clear_db() -> None:
    """危险：清空 public 架构所有表数据（TRUNCATE + RESTART IDENTITY + CASCADE）。
    示例：python -m app.cli.main admin-clear-db
    排障：确保连接到 DEV 数据库；该命令不可恢复
    """
    from app.services.system.cleanup import clear_database

    settings = load_settings(Path("config"))
    clear_database(settings)
    typer.echo("已清空 public 架构所有表数据")


def _main() -> None:
    try:
        app()
    except KeyboardInterrupt:
        typer.echo("已中断", err=True)
        sys.exit(130)


if __name__ == "__main__":
    _main()
