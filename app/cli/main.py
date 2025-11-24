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
) -> bool:
    """读取 run-all 的 device_running 开关默认值。
    优先级：ENV > configs/merge.yaml(run_all) > 代码缺省(True)
    ENV: ORCHESTRATOR_WITH_DEVICE_RUNNING_DEFAULT
    merge.yaml keys (under run_all): device_running
    """
    dev_default = True

    # YAML（可选）
    try:
        import yaml  # 项目已使用 yaml 依赖

        # 1) 首选 merge.yaml 的 run_all 段
        merge_yml = config_dir / "merge.yaml"
        if merge_yml.exists():
            data = yaml.safe_load(merge_yml.read_text(encoding="utf-8")) or {}
            ra = (data or {}).get("run_all", {}) or {}
            dev_default = bool(ra.get("device_running", dev_default))
    except Exception:
        # 配置缺失或解析失败时，保持默认 True
        pass

    # ENV（最高优先级）
    dev_default = _parse_bool(
        os.getenv("ORCHESTRATOR_WITH_DEVICE_RUNNING_DEFAULT"), dev_default
    )

    return dev_default


# 计算动态默认值（模块加载时）
_DEV_RUN_DEFAULT = get_orchestrator_default_flags()

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
        "prepare-dim / create-staging / ingest:copy / merge:fact / run-all"
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


# ===== 特性曲线拟合命令 =====


@app.command(
    name="fit-curve",
    help=(
        "拟合泵特性曲线；"
        "示例：python -m app.cli.main fit-curve --pump-id=1 --curve-type=qh"
    ),
)
def cmd_fit_curve(
    pump_id: int = typer.Option(..., "--pump-id", help="泵设备ID"),
    curve_type: str = typer.Option("qh", "--curve-type", help="曲线类型: qh, qp, qeta"),
    output: str | None = typer.Option(None, "--output", "-o", help="输出文件路径（JSON）"),
) -> None:
    """拟合泵特性曲线。
    示例：python -m app.cli.main fit-curve --pump-id=1 --curve-type=qh
    """
    initialize_app()
    import json as _json

    from app.services.characteristic_curves.pipeline import CurveFittingPipeline

    pipeline = CurveFittingPipeline()
    result = pipeline.fit(device_id=pump_id, curve_type=curve_type)

    output_data = {
        "success": result.success,
        "curve_type": result.curve_type,
        "method_id": result.method_id,
        "r_squared": result.r_squared,
        "rmse": result.rmse,
        "quality_grade": result.quality_grade,
        "formula": result.formula,
    }

    if output:
        Path(output).write_text(_json.dumps(output_data, ensure_ascii=False, indent=2))
        typer.echo(f"✅ 结果已保存到: {output}")
    else:
        typer.echo(_json.dumps(output_data, ensure_ascii=False, indent=2))


@app.command(
    name="validate-curve",
    help=(
        "验证已拟合的曲线；"
        "示例：python -m app.cli.main validate-curve --result-id=123 --r-squared-threshold=0.95"
    ),
)
def cmd_validate_curve(
    result_id: int = typer.Option(..., "--result-id", help="拟合结果ID（数据库主键）"),
    r_squared_threshold: float = typer.Option(0.90, "--r-squared-threshold", help="R²阈值（默认0.90）"),
    rmse_threshold: float = typer.Option(0.10, "--rmse-threshold", help="RMSE阈值（默认0.10）"),
    min_data_points: int = typer.Option(10, "--min-data-points", help="最小数据点数（默认10）"),
    strict: bool = typer.Option(False, "--strict", help="严格模式：所有检查必须通过"),
) -> None:
    """验证已拟合的曲线。

    示例：
        # 使用默认阈值
        python -m app.cli.main validate-curve --result-id=123

        # 自定义阈值
        python -m app.cli.main validate-curve --result-id=123 --r-squared-threshold=0.95 --rmse-threshold=0.05

        # 严格模式
        python -m app.cli.main validate-curve --result-id=123 --strict
    """
    initialize_app()
    import json as _json
    from app.adapters.db.pool import get_connection

    # 从数据库加载拟合结果
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # 查询拟合结果和指标
                query = """
                    SELECT r.id, r.device_id, r.curve_type, r.version, r.method_name,
                           m.r_squared, m.rmse, m.mae, m.mape,
                           r.data_point_count, r.status
                    FROM curve_fit_results r
                    LEFT JOIN curve_fit_metrics m ON r.id = m.result_id
                    WHERE r.id = %s
                """
                cursor.execute(query, (result_id,))
                row = cursor.fetchone()

                if not row:
                    typer.echo(f"❌ 未找到结果: result_id={result_id}", err=True)
                    raise typer.Exit(code=1)

                # 解析结果
                r_squared = row[5] or 0.0
                rmse = row[6] or 0.0
                mae = row[7] or 0.0
                mape = row[8] or 0.0
                data_points = row[9] or 0
                status = row[10]

                # 质量检查
                checks = {}

                # 检查1: R² 阈值检查
                r_squared_passed = r_squared >= r_squared_threshold
                checks["r_squared_check"] = {
                    "passed": r_squared_passed,
                    "threshold": r_squared_threshold,
                    "actual": round(r_squared, 4),
                    "importance": "critical" if strict else "high"
                }

                # 检查2: RMSE 检查
                rmse_passed = rmse < rmse_threshold if rmse > 0 else True
                checks["rmse_check"] = {
                    "passed": rmse_passed,
                    "threshold": rmse_threshold,
                    "actual": round(rmse, 4),
                    "importance": "critical" if strict else "high"
                }

                # 检查3: 数据点数量检查
                data_points_passed = data_points >= min_data_points
                checks["data_points_check"] = {
                    "passed": data_points_passed,
                    "threshold": min_data_points,
                    "actual": data_points,
                    "importance": "medium"
                }

                # 检查4: 状态检查
                status_passed = status == 'active'
                checks["status_check"] = {
                    "passed": status_passed,
                    "expected": "active",
                    "actual": status,
                    "importance": "high"
                }

                # 总体验证结果
                if strict:
                    # 严格模式：所有检查必须通过
                    validation_passed = all(check["passed"] for check in checks.values())
                else:
                    # 宽松模式：关键检查通过即可
                    critical_checks = ["r_squared_check", "rmse_check", "status_check"]
                    validation_passed = all(checks[key]["passed"] for key in critical_checks)

                overall_status = "valid" if validation_passed else "invalid"

                # 生成建议
                suggestions = []
                if not r_squared_passed:
                    suggestions.append(f"R²低于阈值，建议重新拟合或调整拟合方法")
                if not rmse_passed:
                    suggestions.append(f"RMSE过高，建议检查数据质量或增加数据点")
                if not data_points_passed:
                    suggestions.append(f"数据点不足，建议扩大数据采集范围")
                if not status_passed:
                    suggestions.append(f"结果状态为{status}，可能已被废弃")

                validation_result = {
                    "result_id": result_id,
                    "device_id": row[1],
                    "curve_type": row[2],
                    "version": row[3],
                    "method_name": row[4],
                    "validation_mode": "strict" if strict else "normal",
                    "validation_passed": validation_passed,
                    "checks": checks,
                    "overall_status": overall_status,
                    "suggestions": suggestions,
                }

                typer.echo(_json.dumps(validation_result, ensure_ascii=False, indent=2))

    except Exception as e:
        typer.echo(f"❌ 验证失败: {e}", err=True)
        raise typer.Exit(code=1)


@app.command(
    name="compare-versions",
    help=(
        "比较不同版本的曲线；"
        "示例：python -m app.cli.main compare-versions --device-id=1 --curve-type=qh --v1=20250101_100000 --v2=20250102_100000"
    ),
)
def cmd_compare_versions(
    device_id: int = typer.Option(..., "--device-id", help="设备ID"),
    curve_type: str = typer.Option(..., "--curve-type", help="曲线类型（qh/qp/qeta）"),
    v1: str = typer.Option(..., "--v1", help="版本1的版本号"),
    v2: str = typer.Option(..., "--v2", help="版本2的版本号"),
    output: str | None = typer.Option(None, "--output", "-o", help="输出文件路径（JSON）"),
) -> None:
    """比较不同版本的曲线。
    示例：python -m app.cli.main compare-versions --device-id=1 --curve-type=qh --v1=20250101_100000 --v2=20250102_100000
    """
    initialize_app()
    import json as _json
    from app.services.characteristic_curves.shared import ResultStorage

    try:
        storage = ResultStorage()

        # 加载两个版本
        result_v1 = storage.load(device_id=device_id, curve_type=curve_type, version=v1)
        result_v2 = storage.load(device_id=device_id, curve_type=curve_type, version=v2)

        if not result_v1:
            typer.echo(f"❌ 未找到版本1: device_id={device_id}, curve_type={curve_type}, version={v1}", err=True)
            raise typer.Exit(code=1)

        if not result_v2:
            typer.echo(f"❌ 未找到版本2: device_id={device_id}, curve_type={curve_type}, version={v2}", err=True)
            raise typer.Exit(code=1)

        # 比较指标
        r_squared_diff = result_v2.r_squared - result_v1.r_squared
        rmse_diff = result_v2.rmse - result_v1.rmse
        mae_diff = result_v2.mae - result_v1.mae

        # 比较系数
        coefficient_changes = []
        all_keys = set(result_v1.coefficients.keys()) | set(result_v2.coefficients.keys())
        for key in sorted(all_keys):
            c1 = result_v1.coefficients.get(key, 0.0)
            c2 = result_v2.coefficients.get(key, 0.0)
            if c1 != 0 or c2 != 0:  # 只记录非零系数
                coefficient_changes.append({
                    "coefficient": key,
                    "v1": round(c1, 6),
                    "v2": round(c2, 6),
                    "diff": round(c2 - c1, 6),
                    "relative_change": round((c2 - c1) / c1 * 100, 2) if c1 != 0 else None
                })

        # 判断质量变化
        if r_squared_diff > 0.01:
            quality_change = "improved"
        elif r_squared_diff < -0.01:
            quality_change = "degraded"
        else:
            quality_change = "similar"

        # 推荐版本（基于R²）
        if r_squared_diff > 0:
            recommendation = v2
            recommendation_reason = f"R²提升 {r_squared_diff:.4f}"
        elif r_squared_diff < 0:
            recommendation = v1
            recommendation_reason = f"R²下降 {abs(r_squared_diff):.4f}"
        else:
            # R²相同，比较RMSE
            if rmse_diff < 0:
                recommendation = v2
                recommendation_reason = f"RMSE降低 {abs(rmse_diff):.4f}"
            else:
                recommendation = v1
                recommendation_reason = "指标相似，保持原版本"

        comparison_result = {
            "device_id": device_id,
            "curve_type": curve_type,
            "version_1": {
                "version": v1,
                "method_name": result_v1.method_name,
                "r_squared": round(result_v1.r_squared, 4),
                "rmse": round(result_v1.rmse, 4),
                "mae": round(result_v1.mae, 4),
                "data_points": result_v1.data_points,
            },
            "version_2": {
                "version": v2,
                "method_name": result_v2.method_name,
                "r_squared": round(result_v2.r_squared, 4),
                "rmse": round(result_v2.rmse, 4),
                "mae": round(result_v2.mae, 4),
                "data_points": result_v2.data_points,
            },
            "comparison": {
                "r_squared_diff": round(r_squared_diff, 4),
                "rmse_diff": round(rmse_diff, 4),
                "mae_diff": round(mae_diff, 4),
                "coefficient_changes": coefficient_changes,
                "fit_quality_change": quality_change,
            },
            "recommendation": recommendation,
            "recommendation_reason": recommendation_reason,
        }

        if output:
            Path(output).write_text(_json.dumps(comparison_result, ensure_ascii=False, indent=2))
            typer.echo(f"✅ 比较结果已保存到: {output}")
        else:
            typer.echo(_json.dumps(comparison_result, ensure_ascii=False, indent=2))

    except Exception as e:
        typer.echo(f"❌ 比较失败: {e}", err=True)
        raise typer.Exit(code=1)


@app.command(
    name="batch-fit",
    help=(
        "批量拟合多个设备的特性曲线；"
        "示例：python -m app.cli.main batch-fit --device-ids=1,2,3 --curve-type=qh"
    ),
)
def cmd_batch_fit(
    device_ids: str = typer.Option(..., "--device-ids", help="设备ID列表（逗号分隔），如：1,2,3"),
    curve_type: str = typer.Option("qh", "--curve-type", help="曲线类型: qh, qp, qeta"),
    output: str | None = typer.Option(None, "--output", "-o", help="输出文件路径（JSON）"),
    continue_on_error: bool = typer.Option(True, "--continue-on-error", help="遇到错误时继续处理"),
) -> None:
    """批量拟合多个设备的特性曲线。

    示例：
        # 拟合3个设备的QH曲线
        python -m app.cli.main batch-fit --device-ids=1,2,3 --curve-type=qh

        # 拟合并保存结果
        python -m app.cli.main batch-fit --device-ids=1,2,3 --curve-type=qh --output=results.json

        # 遇到错误时停止
        python -m app.cli.main batch-fit --device-ids=1,2,3 --curve-type=qh --continue-on-error=false
    """
    initialize_app()
    import json as _json
    from app.services.characteristic_curves.pipeline import CurveFittingPipeline

    # 解析设备ID列表
    try:
        device_id_list = [int(x.strip()) for x in device_ids.split(",")]
    except ValueError:
        typer.echo("❌ 设备ID格式错误，请使用逗号分隔的整数，如：1,2,3", err=True)
        raise typer.Exit(code=1)

    if not device_id_list:
        typer.echo("❌ 设备ID列表为空", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"📊 开始批量拟合：{len(device_id_list)}个设备，曲线类型={curve_type}")

    pipeline = CurveFittingPipeline()
    results = []
    success_count = 0
    failed_count = 0

    for idx, device_id in enumerate(device_id_list, 1):
        typer.echo(f"\n[{idx}/{len(device_id_list)}] 拟合设备 {device_id}...")

        try:
            result = pipeline.fit(device_id=device_id, curve_type=curve_type)

            result_data = {
                "device_id": device_id,
                "success": result.success,
                "curve_type": result.curve_type,
                "method_id": result.method_id,
                "r_squared": result.r_squared,
                "rmse": result.rmse,
                "quality_grade": result.quality_grade,
                "formula": result.formula,
            }

            results.append(result_data)

            if result.success:
                success_count += 1
                typer.echo(
                    f"  ✅ 成功: method={result.method_id}, r²={result.r_squared:.4f}, "
                    f"rmse={result.rmse:.4f}, grade={result.quality_grade}"
                )
            else:
                failed_count += 1
                error_info = result.metadata.get("error", "未知错误") if result.metadata else "拟合失败"
                typer.echo(f"  ⚠️ 失败: {error_info}")

        except Exception as e:
            failed_count += 1
            error_msg = str(e)
            typer.echo(f"  ❌ 异常: {error_msg}")

            results.append(
                {
                    "device_id": device_id,
                    "success": False,
                    "error": error_msg,
                }
            )

            if not continue_on_error:
                typer.echo("\n❌ 遇到错误，停止批量处理", err=True)
                raise typer.Exit(code=1)

    # 输出汇总
    typer.echo(f"\n{'='*60}")
    typer.echo(f"📊 批量拟合完成")
    typer.echo(f"  总数: {len(device_id_list)}")
    typer.echo(f"  成功: {success_count}")
    typer.echo(f"  失败: {failed_count}")
    typer.echo(f"  成功率: {success_count/len(device_id_list)*100:.1f}%")

    # 保存结果
    output_data = {
        "summary": {
            "total": len(device_id_list),
            "success": success_count,
            "failed": failed_count,
            "success_rate": success_count / len(device_id_list),
        },
        "results": results,
    }

    if output:
        Path(output).write_text(_json.dumps(output_data, ensure_ascii=False, indent=2))
        typer.echo(f"\n✅ 结果已保存到: {output}")
    else:
        typer.echo(f"\n{_json.dumps(output_data, ensure_ascii=False, indent=2)}")


@app.command(
    name="evaluate-fit",
    help=(
        "评估已拟合曲线的预测准确性；"
        "示例：python -m app.cli.main evaluate-fit --result-id=123"
    ),
)
def cmd_evaluate_fit(
    result_id: int = typer.Option(..., "--result-id", help="拟合结果ID（数据库主键）"),
    test_days: int = typer.Option(7, "--test-days", help="测试窗口天数（默认7天）"),
    output: str | None = typer.Option(None, "--output", "-o", help="输出文件路径（JSON）"),
) -> None:
    """评估已拟合曲线的预测准确性。

    使用独立的测试数据评估曲线的预测能力。
    合格标准：90%的测试点偏差小于5%。

    示例：
        # 评估拟合结果
        python -m app.cli.main evaluate-fit --result-id=123

        # 自定义测试窗口
        python -m app.cli.main evaluate-fit --result-id=123 --test-days=14

        # 保存评估结果
        python -m app.cli.main evaluate-fit --result-id=123 --output=evaluation.json
    """
    initialize_app()
    import json as _json
    from datetime import datetime, timedelta
    from app.adapters.db.pool import get_connection
    from app.services.characteristic_curves.shared.historical_data_evaluator import (
        HistoricalDataEvaluator,
        TimeWindow,
    )

    typer.echo(f"📊 开始评估拟合结果: result_id={result_id}")

    # 从数据库加载拟合结果
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # 查询拟合结果
                query = """
                    SELECT r.id, r.device_id, r.curve_type, r.method_name,
                           m.r_squared, m.rmse
                    FROM curve_fit_results r
                    LEFT JOIN curve_fit_metrics m ON r.id = m.result_id
                    WHERE r.id = %s
                """
                cursor.execute(query, (result_id,))
                row = cursor.fetchone()

                if not row:
                    typer.echo(f"❌ 未找到结果: result_id={result_id}", err=True)
                    raise typer.Exit(code=1)

                device_id = row[1]
                curve_type = row[2]
                method_name = row[3]
                r_squared = row[4]
                rmse = row[5]

                # 查询系数参数（从curve_fit_params表）
                param_query = """
                    SELECT param_key, param_value
                    FROM curve_fit_params
                    WHERE result_id = %s AND param_category = 'coefficients'
                    ORDER BY param_key
                """
                cursor.execute(param_query, (result_id,))
                param_rows = cursor.fetchall()
                coefficients = [row[1] for row in param_rows] if param_rows else []

                typer.echo(f"  设备ID: {device_id}")
                typer.echo(f"  曲线类型: {curve_type}")
                typer.echo(f"  拟合方法: {method_name}")
                typer.echo(f"  R²: {r_squared:.4f}")
                typer.echo(f"  RMSE: {rmse:.4f}")

    except Exception as e:
        typer.echo(f"❌ 加载拟合结果失败: {e}", err=True)
        raise typer.Exit(code=1)

    # 创建预测函数（简化版，仅支持多项式）
    def predict_func(x: float) -> float:
        """多项式预测函数"""
        if not coefficients:
            return 0.0
        y = 0.0
        for i, coef in enumerate(coefficients):
            y += coef * (x**i)
        return y

    # 定义测试窗口（最近N天）
    end_time = datetime.now()
    start_time = end_time - timedelta(days=test_days)
    test_window = TimeWindow(start=start_time, end=end_time)

    typer.echo(f"\n📅 测试窗口: {start_time.strftime('%Y-%m-%d')} ~ {end_time.strftime('%Y-%m-%d')}")

    # 评估预测准确性
    try:
        evaluator = HistoricalDataEvaluator()
        evaluation = evaluator.evaluate_prediction_accuracy(
            device_id=device_id,
            curve_type=curve_type,
            predict_func=predict_func,
            test_window=test_window,
        )

        # 输出评估结果
        typer.echo(f"\n{'='*60}")
        typer.echo("📊 评估结果")
        typer.echo(f"  测试点数: {evaluation['test_point_count']}")
        typer.echo(f"  5%偏差内: {evaluation['pass_rate']['within_5_percent']*100:.1f}%")
        typer.echo(f"  10%偏差内: {evaluation['pass_rate']['within_10_percent']*100:.1f}%")
        typer.echo(f"  平均偏差: {evaluation['deviation_stats']['mean_deviation']:.2f}%")
        typer.echo(f"  最大偏差: {evaluation['deviation_stats']['max_deviation']:.2f}%")

        # 判断是否合格
        is_qualified = evaluation["pass_rate"]["within_5_percent"] >= 0.90
        if is_qualified:
            typer.echo(f"\n✅ 评估合格（90%点位偏差<5%）")
        else:
            typer.echo(f"\n⚠️ 评估不合格（90%点位偏差<5%）")

        # 保存结果
        output_data = {
            "result_id": result_id,
            "device_id": device_id,
            "curve_type": curve_type,
            "method_name": method_name,
            "fit_quality": {"r_squared": r_squared, "rmse": rmse},
            "evaluation": evaluation,
            "is_qualified": is_qualified,
        }

        if output:
            Path(output).write_text(_json.dumps(output_data, ensure_ascii=False, indent=2))
            typer.echo(f"\n✅ 评估结果已保存到: {output}")
        else:
            typer.echo(f"\n{_json.dumps(output_data, ensure_ascii=False, indent=2)}")

    except Exception as e:
        typer.echo(f"❌ 评估失败: {e}", err=True)
        raise typer.Exit(code=1)


@app.command(
    name="export-curves",
    help=(
        "导出曲线拟合结果；"
        "示例：python -m app.cli.main export-curves --device-id=1 --format=csv --output=curves.csv"
    ),
)
def cmd_export_curves(
    device_id: int | None = typer.Option(None, "--device-id", help="设备ID（可选，不指定则导出所有）"),
    curve_type: str | None = typer.Option(None, "--curve-type", help="曲线类型（可选）: qh, qp, qeta"),
    format: str = typer.Option("csv", "--format", "-f", help="导出格式: csv, json, excel"),
    output: str = typer.Option(..., "--output", "-o", help="输出文件路径"),
    limit: int = typer.Option(1000, "--limit", help="最大导出行数（默认1000）"),
) -> None:
    """导出曲线拟合结果到文件。

    支持CSV、JSON、Excel格式。

    示例：
        # 导出所有曲线到CSV
        python -m app.cli.main export-curves --output=all_curves.csv

        # 导出指定设备的QH曲线
        python -m app.cli.main export-curves --device-id=1 --curve-type=qh --output=device1_qh.csv

        # 导出为JSON格式
        python -m app.cli.main export-curves --device-id=1 --format=json --output=curves.json

        # 导出为Excel格式
        python -m app.cli.main export-curves --format=excel --output=curves.xlsx --limit=5000
    """
    initialize_app()
    import json as _json
    from app.adapters.db.pool import get_connection
    from app.services.characteristic_curves.shared.data_exporter import DataExporter

    typer.echo(f"📊 开始导出曲线数据")
    typer.echo(f"  设备ID: {device_id or '全部'}")
    typer.echo(f"  曲线类型: {curve_type or '全部'}")
    typer.echo(f"  导出格式: {format}")
    typer.echo(f"  输出文件: {output}")

    # 从数据库查询曲线数据
    try:
        with get_connection() as conn:
            # 构建查询
            query = """
                SELECT
                    r.id,
                    r.device_id,
                    r.curve_type,
                    r.version,
                    r.method_name,
                    r.data_point_count,
                    r.status,
                    r.created_at,
                    m.r_squared,
                    m.rmse,
                    m.mae,
                    m.mape
                FROM curve_fit_results r
                LEFT JOIN curve_fit_metrics m ON r.id = m.result_id
                WHERE 1=1
            """
            params = []

            if device_id is not None:
                query += " AND r.device_id = %s"
                params.append(device_id)

            if curve_type is not None:
                query += " AND r.curve_type = %s"
                params.append(curve_type)

            query += " ORDER BY r.created_at DESC LIMIT %s"
            params.append(limit)

            import pandas as pd

            # 使用cursor执行查询，避免pandas警告
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                df = pd.DataFrame(rows, columns=columns)

            if df.empty:
                typer.echo("⚠️ 未找到符合条件的曲线数据", err=True)
                raise typer.Exit(code=1)

            typer.echo(f"\n✅ 查询到 {len(df)} 条记录")

    except Exception as e:
        typer.echo(f"❌ 查询数据失败: {e}", err=True)
        raise typer.Exit(code=1)

    # 导出数据
    try:
        exporter = DataExporter()
        result = exporter.export(data=df, format=format, file_path=output)

        if result.success:
            typer.echo(f"\n✅ 导出成功")
            typer.echo(f"  文件路径: {result.file_path}")
            typer.echo(f"  导出行数: {result.rows}")
            typer.echo(f"  导出格式: {result.format}")
        else:
            typer.echo(f"❌ 导出失败: {result.message}", err=True)
            raise typer.Exit(code=1)

    except Exception as e:
        typer.echo(f"❌ 导出失败: {e}", err=True)
        raise typer.Exit(code=1)


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
