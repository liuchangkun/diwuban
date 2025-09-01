from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import typer

from app.adapters.db import init_database
from app.core.config.loader_new import load_settings
from app.services.ingest.copy_workers import copy_from_mapping
from app.services.ingest.create_staging import create_staging
from app.services.ingest.merge_service import merge_window
from app.services.ingest.prepare_dim import prepare_dim

# 全局可选日志参数（方案B）
log_run_option = typer.Option(
    None, help="启用文件日志并创建新的运行目录（默认禁用）", show_default=False
)
log_dir_option = typer.Option(
    None, help="自定义日志目录（可配合 --log-run 复用同一目录）", show_default=False
)
log_format_option = typer.Option(
    None, help="覆盖日志格式：json|text（默认 YAML 配置）", show_default=False
)
log_routing_option = typer.Option(
    None, help="覆盖日志路由：by_run|by_module（默认 YAML 配置）", show_default=False
)
log_console_level_option = typer.Option(
    None,
    help="控制台日志级别（默认同全局）：DEBUG|INFO|WARNING|ERROR|CRITICAL",
    show_default=False,
)
quiet_option = typer.Option(
    False, "--quiet", help="安静模式（仅控制台 WARNING 及以上）", show_default=False
)
ingest_workers_option = typer.Option(
    None, help="覆盖导入并发数（INGEST_WORKERS）", show_default=False
)
ingest_commit_interval_option = typer.Option(
    None, help="覆盖提交批大小（INGEST_COMMIT_INTERVAL）", show_default=False
)


def initialize_app():
    """初始化应用程序，包括数据库连接池"""
    try:
        settings = load_settings(Path("configs"))
        init_database(settings)
        print("数据库连接池初始化成功")
    except Exception as e:
        print(f"数据库连接池初始化失败: {e}")


app = typer.Typer(
    help="CSV 高性能导入（方案A）：prepare-dim / create-staging / ingest:copy / merge:fact / run-all"
)


@app.command()
def version(
    log_run: bool | None = log_run_option,
    log_dir: str | None = log_dir_option,
    log_format: str | None = log_format_option,
    log_routing: str | None = log_routing_option,
    console_level: str | None = log_console_level_option,
    quiet: bool | None = quiet_option,
) -> None:
    """打印版本/存活检查。
    示例：python -m app.cli.main version --log-run --log-dir logs/runs/demo
    常见问题：无
    """
    initialize_app()
    if log_run:
        from pathlib import Path as _P

        from app.adapters.logging.init import compute_run_dir, init_logging

        # 初始化日志（可复用目录）
        run_dir = _P(log_dir) if log_dir else compute_run_dir()
        from app.adapters.logging.init import write_run_snapshot
        from app.core.config.loader_new import load_settings as _ls

        settings0 = _ls(Path("configs"))
        init_logging(
            settings0,
            run_dir,
            override_format=log_format,
            override_routing=log_routing,
            override_console_level=console_level,
            quiet=quiet,
        )
        write_run_snapshot(settings0, run_dir, args_summary={"command": "version"})
    typer.echo("ingest-cli ok")


# 预留：后续填充真实子命令


@app.command(
    name="prepare-dim",
    help="准备维表与映射：从 data_mapping.json 插入/更新 dim_* 与映射；示例：python -m app.cli.main prepare-dim config/data_mapping.json；常见错误：JSON 结构缺失 name/key/files、数据库连接失败",
)
def cmd_prepare_dim(
    mapping: str = typer.Argument(..., help="data_mapping.json 路径（相对仓库根）"),
    log_run: bool | None = log_run_option,
    log_dir: str | None = log_dir_option,
    log_format: str | None = log_format_option,
    log_routing: str | None = log_routing_option,
    console_level: str | None = log_console_level_option,
    quiet: bool | None = quiet_option,
) -> None:
    initialize_app()
    from app.core.config.loader_new import load_settings_with_sources as _lss

    settings, _sources = _lss(Path("configs"))
    if log_run:
        from pathlib import Path as _P

        from app.adapters.logging.init import compute_run_dir, init_logging

        run_dir = _P(log_dir) if log_dir else compute_run_dir()
        # 日志配置默认来自 logging.yaml；允许 CLI 临时覆盖 format/routing
        init_logging(
            settings,
            run_dir,
            override_format=log_format,
            override_routing=log_routing,
            override_console_level=console_level,
            quiet=quiet,
        )
    prepare_dim(settings, Path(mapping))


@app.command(
    name="create-staging",
    help="创建/幂等 staging_raw 与 staging_rejects（UNLOGGED）；示例：python -m app.cli.main create-staging；常见错误：数据库连接失败",
)
def cmd_create_staging(
    log_run: bool | None = log_run_option,
    log_dir: str | None = log_dir_option,
    log_format: str | None = log_format_option,
    log_routing: str | None = log_routing_option,
    console_level: str | None = log_console_level_option,
    quiet: bool | None = quiet_option,
) -> None:
    initialize_app()
    settings = load_settings(Path("configs"))
    if log_run:
        from pathlib import Path as _P

        from app.adapters.logging.init import compute_run_dir, init_logging

        run_dir = _P(log_dir) if log_dir else compute_run_dir()
        init_logging(
            settings,
            run_dir,
            override_format=log_format,
            override_routing=log_routing,
            override_console_level=console_level,
            quiet=quiet,
        )
    create_staging(settings)


@app.command(
    name="ingest-copy",
    help="并发 COPY 导入 CSV 到 staging_raw；示例：python -m app.cli.main ingest-copy config/data_mapping.json；常见错误：路径带 data/ 前缀、文件不存在、CSV 列头缺失",
)
def cmd_ingest_copy(
    mapping: str = typer.Argument(..., help="data_mapping.json 路径"),
    log_run: bool | None = log_run_option,
    log_dir: str | None = log_dir_option,
    log_format: str | None = log_format_option,
    log_routing: str | None = log_routing_option,
    console_level: str | None = log_console_level_option,
    quiet: bool | None = quiet_option,
) -> None:
    initialize_app()
    settings = load_settings(Path("configs"))
    if log_run:
        from pathlib import Path as _P

        from app.adapters.logging.init import compute_run_dir, init_logging

        run_dir = _P(log_dir) if log_dir else compute_run_dir()
        init_logging(
            settings,
            run_dir,
            override_format=log_format,
            override_routing=log_routing,
            override_console_level=console_level,
            quiet=quiet,
        )
    stats = copy_from_mapping(settings, Path(mapping))
    typer.echo(f"copy done: {stats}")


@app.command(
    name="merge-fact",
    help="集合式合并：tz→UTC→秒级对齐→去重→UPSERT；示例：python -m app.cli.main merge-fact --window-start ...Z --window-end ...Z；常见错误：时间格式不正确",
)
def cmd_merge_fact(
    window_start: str = typer.Option(..., help="UTC 起始（YYYY-MM-DDTHH:MM:SSZ）"),
    window_end: str = typer.Option(..., help="UTC 结束（YYYY-MM-DDTHH:MM:SSZ）"),
    log_run: bool | None = log_run_option,
    log_dir: str | None = log_dir_option,
    log_format: str | None = log_format_option,
    log_routing: str | None = log_routing_option,
    console_level: str | None = log_console_level_option,
    quiet: bool | None = quiet_option,
) -> None:
    initialize_app()
    settings = load_settings(Path("configs"))
    if log_run:
        from pathlib import Path as _P

        from app.adapters.logging.init import compute_run_dir, init_logging

        run_dir = _P(log_dir) if log_dir else compute_run_dir()
        init_logging(
            settings,
            run_dir,
            override_format=log_format,
            override_routing=log_routing,
            override_console_level=console_level,
            quiet=quiet,
        )
    ws = datetime.fromisoformat(window_start.replace("Z", "+00:00"))
    we = datetime.fromisoformat(window_end.replace("Z", "+00:00"))
    merge_window(settings, ws, we)


@app.command(
    name="data-report",
    help="生成数据质量报表：覆盖/越界/拒绝统计；示例：python -m app.cli.main data-report --window-start ...Z --window-end ...Z",
)
def cmd_data_report(
    window_start: str = typer.Option(..., help="UTC 起始（YYYY-MM-DDTHH:MM:SSZ）"),
    window_end: str = typer.Option(..., help="UTC 结束（YYYY-MM-DDTHH:MM:SSZ）"),
    expected_interval: int = typer.Option(
        1, "--expected-interval", help="期望采样间隔（秒），用于覆盖率与缺口检测"
    ),
    top_k: int = typer.Option(100, "--top-k", help="各榜单 TopN 数量"),
    group_by: str = typer.Option(
        "metric",
        "--group-by",
        help="直方图分组维度：metric|device|station|source|batch",
    ),
    log_run: bool | None = log_run_option,
    log_dir: str | None = log_dir_option,
    log_format: str | None = log_format_option,
    log_routing: str | None = log_routing_option,
    console_level: str | None = log_console_level_option,
    quiet: bool | None = quiet_option,
) -> None:
    initialize_app()
    settings = load_settings(Path("configs"))
    run_dir = None
    if log_run:
        from pathlib import Path as _P

        from app.adapters.logging.init import compute_run_dir, init_logging

        run_dir = _P(log_dir) if log_dir else compute_run_dir()
        init_logging(
            settings,
            run_dir,
            override_format=log_format,
            override_routing=log_routing,
            override_console_level=console_level,
            quiet=quiet,
        )
    ws = datetime.fromisoformat(window_start.replace("Z", "+00:00"))
    we = datetime.fromisoformat(window_end.replace("Z", "+00:00"))
    from app.services.reporting.data_quality import generate_report

    _ = generate_report(
        settings,
        ws,
        we,
        run_dir=run_dir,
        expected_interval_seconds=expected_interval,
        top_k=top_k,
        group_by=group_by,
    )
    typer.echo("report generated")


@app.command(
    name="check-mapping",
    help="只读一致性检查与路径建议；支持 --out 导出 JSON；常见错误：路径在 data/ 外或含 data/ 前缀",
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
    log_run: bool | None = log_run_option,
    log_dir: str | None = log_dir_option,
    log_format: str | None = log_format_option,
    log_routing: str | None = log_routing_option,
    console_level: str | None = log_console_level_option,
    quiet: bool | None = quiet_option,
) -> None:
    """只读一致性检查：
    - 检查是否含 data/ 前缀
    - 按严格规则（base_dir+相对路径）检查文件是否存在
    - 校验 schema 必填项：stations/devices/metrics/files/key/name
    - 仅输出建议，不修改文件
    示例：python -m app.cli.main check-mapping config/data_mapping.json --out mapping_report.json --log-run
    常见错误：路径带 data/ 前缀；文件不存在；结构缺失 key/files/name
    """
    import json as _json

    settings = load_settings(Path("config"))
    if log_run:
        from pathlib import Path as _P

        from app.adapters.logging.init import compute_run_dir, init_logging

        run_dir = _P(log_dir) if log_dir else compute_run_dir()
        init_logging(
            settings,
            run_dir,
            override_format=log_format,
            override_routing=log_routing,
            override_console_level=console_level,
            quiet=quiet,
        )
    from app.services.ingest.check_mapping import check_mapping_paths

    report = check_mapping_paths(settings, Path(mapping))

    if not show_all:

        def _flt(arr):
            return [
                x
                for x in (arr or [])
                if (x.get("missing_files", 0) > 0 or x.get("with_data_prefix", 0) > 0)
            ]

        if isinstance(report, dict):
            if "group_by_station" in report:
                report["group_by_station"] = _flt(report.get("group_by_station"))
            if "group_by_device" in report:
                report["group_by_device"] = _flt(report.get("group_by_device"))
            if "group_by_metric" in report:
                report["group_by_metric"] = _flt(report.get("group_by_metric"))

    if out:
        Path(out).write_text(
            _json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        typer.echo(f"检查报告已写入：{out}")
    else:
        typer.echo(_json.dumps(report, ensure_ascii=False, indent=2))


@app.command(
    name="db-ping",
    help="免密连接测试；--verbose 输出 host/db/user(脱敏)/时区/版本；常见错误：.pgpass 无效、用户/库不匹配",
)
def db_ping(
    verbose: bool = typer.Option(
        False, "--verbose", help="打印脱敏连接信息与数据库/时区信息"
    ),
    log_run: bool | None = log_run_option,
    log_dir: str | None = log_dir_option,
    log_format: str | None = log_format_option,
    log_routing: str | None = log_routing_option,
    console_level: str | None = log_console_level_option,
    quiet: bool | None = quiet_option,
) -> None:
    """免密连接测试。
    示例：python -m app.cli.main db-ping --verbose --log-run --log-dir logs/runs/demo
    常见错误：.pgpass 未生效/权限不正确；host/db/user 与实际不符
    """
    from app.adapters.db.gateway import get_conn

    settings = load_settings(Path("config"))
    if log_run:
        from pathlib import Path as _P

        from app.adapters.logging.init import compute_run_dir, init_logging

        run_dir = _P(log_dir) if log_dir else compute_run_dir()
        init_logging(
            settings,
            run_dir,
            override_format=log_format,
            override_routing=log_routing,
            override_console_level=console_level,
            quiet=quiet,
        )
    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                row = cur.fetchone()
                val = row[0] if row else 1
                if verbose:
                    cur.execute(
                        "SELECT current_database(), current_user, current_setting('TimeZone'), version()"
                    )
                    dbrow = cur.fetchone() or (None, None, None, None)
                    dbname, dbuser, tz, ver = dbrow

                    def _mask(u: str | None) -> str:
                        if not u:
                            return ""
                        return (u[0] + "***" + u[-1]) if len(u) > 2 else (u + "*")

                    host = settings.db.host
                    typer.echo(
                        f"host={host} db={dbname} user={_mask(str(dbuser))} tz={tz} ver={str(ver).split(' ')[0]}"
                    )
        typer.echo(f"db:ping ok ({val})")
    except Exception as e:
        typer.echo(f"db:ping failed: {e}", err=True)


@app.command(
    name="run-all",
    help="一键执行完整流程：prepare-dim → create-staging → ingest-copy → merge-fact；可选自动窗口 --use-staging-time-range",
)
def cmd_run_all(
    mapping: str = typer.Argument(
        "configs/data_mapping.v2.json", help="data_mapping.json 路径"
    ),
    use_staging_time_range: bool = typer.Option(
        False, "--use-staging-time-range", help="自动探测 staging 时间范围作为合并窗口"
    ),
    window_start: str | None = typer.Option(
        None, help="UTC 起始（YYYY-MM-DDTHH:MM:SSZ）"
    ),
    window_end: str | None = typer.Option(
        None, help="UTC 结束（YYYY-MM-DDTHH:MM:SSZ）"
    ),
    summary_json: str | None = typer.Option(
        None,
        "--summary-json",
        help="将执行摘要写入 JSON 文件（rows_loaded/rows_merged/window 等）",
    ),
    log_run: bool | None = log_run_option,
    log_dir: str | None = log_dir_option,
    log_format: str | None = log_format_option,
    log_routing: str | None = log_routing_option,
    console_level: str | None = log_console_level_option,
    quiet: bool | None = quiet_option,
) -> None:
    """完整流程执行：
    - 默认使用 mapping 文件路径
    - 若指定 --use-staging-time-range，将从 staging_raw 中计算窗口（min(ts_raw)~max(ts_raw)）
    - 否则使用 --window-start/--window-end
    - 若指定 --summary-json，写入执行摘要（便于 CI/采集）
    """
    initialize_app()
    settings = load_settings(Path("configs"))

    if log_run:
        from pathlib import Path as _P

        from app.adapters.logging.init import compute_run_dir, init_logging

        run_dir = _P(log_dir) if log_dir else compute_run_dir()
        init_logging(
            settings,
            run_dir,
            override_format=log_format,
            override_routing=log_routing,
            override_console_level=console_level,
            quiet=quiet,
        )

    # 1) prepare-dim
    prepare_dim(settings, Path(mapping))
    # 2) create-staging
    create_staging(settings)
    # 3) ingest-copy（采集统计）
    copy_stats = copy_from_mapping(settings, Path(mapping))

    # 4) merge-fact（确定窗口与统计）
    ws: str
    we: str
    if use_staging_time_range:
        from app.adapters.db.gateway import get_conn

        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      MIN(to_timestamp(rtrim(replace(split_part(sr."DataTime", '.', 1), 'T', ' '), 'Z'), 'YYYY-MM-DD HH24:MI:SS')) AS ws,
                      MAX(to_timestamp(rtrim(replace(split_part(sr."DataTime", '.', 1), 'T', ' '), 'Z'), 'YYYY-MM-DD HH24:MI:SS')) AS we
                    FROM public.staging_raw sr
                    """
                )
                row = cur.fetchone()
                if not row or not row[0] or not row[1]:
                    typer.echo("staging_raw 无数据，跳过 merge-fact", err=True)
                    raise typer.Exit(code=1)
                ws = row[0].strftime("%Y-%m-%dT%H:%M:%SZ")
                we = row[1].strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        if not window_start or not window_end:
            typer.echo("未指定窗口且未启用 --use-staging-time-range", err=True)
            raise typer.Exit(code=2)
        ws, we = window_start, window_end

    merge_stats = merge_window(
        settings,
        datetime.fromisoformat(ws.replace("Z", "+00:00")),
        datetime.fromisoformat(we.replace("Z", "+00:00")),
    )

    # 5) 可选写入摘要 JSON（包含窗口与拷贝/合并统计）
    if summary_json:
        try:
            import json as _json
            from pathlib import Path as _P

            _p = _P(summary_json)
            _p.parent.mkdir(parents=True, exist_ok=True)
            summary = {
                "mapping_file": str(mapping),
                "window": {"start": ws, "end": we},
                "copy_stats": {
                    "files_total": int(copy_stats.get("files_total", 0)),
                    "files_succeeded": int(copy_stats.get("files_succeeded", 0)),
                    "files_failed": int(copy_stats.get("files_failed", 0)),
                    "rows_read": int(copy_stats.get("rows_read", 0)),
                    "rows_loaded": int(copy_stats.get("rows_loaded", 0)),
                    "rows_rejected": int(copy_stats.get("rows_rejected", 0)),
                },
                "merge_stats": {
                    k: int(v) if isinstance(v, (int, float)) else v
                    for k, v in (merge_stats or {}).items()
                },
            }
            _p.write_text(
                _json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            typer.echo(f"summary json written: {summary_json}")
        except Exception as e:
            typer.echo(f"failed to write summary json: {e}", err=True)

    typer.echo("run-all 完成")


@app.command(
    name="admin-clear-db",
    help="危险：清空 public 架构所有表数据（TRUNCATE + RESTART IDENTITY + CASCADE）；仅限 DEV",
)
def admin_clear_db(
    log_run: bool | None = log_run_option,
    log_dir: str | None = log_dir_option,
    log_format: str | None = log_format_option,
    log_routing: str | None = log_routing_option,
    console_level: str | None = log_console_level_option,
    quiet: bool | None = quiet_option,
) -> None:
    """危险：清空 public 架构所有表数据（TRUNCATE + RESTART IDENTITY + CASCADE）。
    示例：python -m app.cli.main admin-clear-db --log-run --log-dir logs/runs/demo
    排障：确保连接到 DEV 数据库；该命令不可恢复
    """
    from app.services.admin.clear_db import truncate_public_schema

    settings = load_settings(Path("config"))
    if log_run:
        from pathlib import Path as _P

        from app.adapters.logging.init import compute_run_dir, init_logging

        run_dir = _P(log_dir) if log_dir else compute_run_dir()
        init_logging(
            settings,
            run_dir,
            override_format=log_format,
            override_routing=log_routing,
            override_console_level=console_level,
            quiet=quiet,
        )
    truncate_public_schema(settings)
    typer.echo("已清空 public 架构所有表数据")


def _main() -> None:
    try:
        app()
    except KeyboardInterrupt:
        typer.echo("已中断", err=True)
        sys.exit(130)


if __name__ == "__main__":
    _main()
