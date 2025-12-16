from __future__ import annotations

"""
系统清理服务（system.cleanup）

负责程序启动时的清理工作，包括数据库清理和日志目录清理。
根据配置文件的设置自动执行清理操作，确保干净的运行环境。

设计要点：
- 支持数据库完全清理（TRUNCATE所有表）
- 支持日志目录清理（保留指定数量的备份）
- 支持确认提示（可配置）
- 完整的日志记录和错误处理
"""

import shutil
import time
import logging
from pathlib import Path

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import Settings

_act = logging.getLogger("activity")


def backup_logs_directory(logs_dir: Path, backup_count: int) -> None:
    """
    备份logs目录

    Args:
        logs_dir: logs目录路径
        backup_count: 保留的备份数量
    """
    if not logs_dir.exists():
        return

    timestamp = int(time.time())
    backup_name = f"logs_backup_{timestamp}"
    backup_dir = logs_dir.parent / backup_name

    try:
        # 创建备份
        shutil.copytree(logs_dir, backup_dir)

        # 清理旧的备份
        cleanup_old_backups(logs_dir.parent, "logs_backup_", backup_count)

    except Exception:
        raise


def cleanup_old_backups(parent_dir: Path, prefix: str, keep_count: int) -> None:
    """
    清理旧的备份目录

    Args:
        parent_dir: 父目录
        prefix: 备份目录前缀
        keep_count: 保留的备份数量
    """
    if not parent_dir.exists():
        return

    backup_dirs = [
        d for d in parent_dir.iterdir() if d.is_dir() and d.name.startswith(prefix)
    ]
    backup_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    dirs_to_remove = backup_dirs[keep_count:]

    for backup_dir in dirs_to_remove:
        try:
            shutil.rmtree(backup_dir)
        except Exception:
            pass


def clear_logs_directory(logs_dir: Path, backup_count: int) -> None:
    """
    清理logs目录

    Args:
        logs_dir: logs目录路径
        backup_count: 备份数量
    """

    t0 = time.perf_counter()
    try:
        _act.info(
            "[流程-开始] [日志目录清理]",
            extra={
                "extra_data": {
                    "logs_dir": str(logs_dir),
                    "backup_count": backup_count,
                }
            }
        )
    except Exception:
        pass

    # 先备份
    if logs_dir.exists() and backup_count > 0:
        backup_logs_directory(logs_dir, backup_count)

    # 清理logs目录（尽最大努力策略：失败仅告警；包含重试）
    retry = 0
    max_retries = 3
    while True:
        try:
            if logs_dir.exists():
                file_count = len(list(logs_dir.rglob("*")))

                shutil.rmtree(logs_dir)

            else:
                break
        except Exception as e:
            retry += 1
            # 清理失败，稍后重试
            if retry >= max_retries:
                break

    dur_ms = int((time.perf_counter() - t0) * 1000)
    try:
        _act.info(
            "[流程-完成] [日志目录清理完成]",
            extra={
                "extra_data": {
                    "logs_dir": str(logs_dir),
                    "duration_ms": dur_ms,
                }
            }
        )
    except Exception:
        pass


def clear_database(settings: Settings) -> None:
    """
    清理数据库

    - 默认清理 public schema
    - 如 configs/merge.yaml.run_all.reset_db_schemas 声明其他 schema，则一并清理
    - 永远跳过系统/internal schema：pg_catalog、information_schema、_timescaledb_*

    Args:
        settings: 应用配置
    """

    t0 = time.perf_counter()
    try:
        _act.info(
            "[流程-开始] [数据库清理]",
            extra={"extra_data": {}}
        )
    except Exception:
        pass

    # 读取配置中声明的 schema 列表（可选）
    schemas_to_clear = ["public"]
    try:
        import yaml  # type: ignore
        from pathlib import Path as _Path
        cfg_path = _Path(getattr(getattr(settings.system, "directories", None), "configs", "configs")) / "merge.yaml"
        if cfg_path.exists():
            data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            ra = (data or {}).get("run_all", {}) or {}
            sch = ra.get("reset_db_schemas")
            if isinstance(sch, list) and all(isinstance(x, str) for x in sch):
                schemas_to_clear = sch or schemas_to_clear
    except Exception:
        pass

    # 黑名单 schema（绝不清理）
    forbidden_prefixes = ("_timescaledb_",)
    forbidden_exact = {"pg_catalog", "information_schema"}

    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 规范化 schema 列表
                schemas = []
                for s in schemas_to_clear:
                    s1 = (s or "").strip()
                    if not s1 or s1 in forbidden_exact or any(s1.startswith(p) for p in forbidden_prefixes):
                        continue
                    schemas.append(s1)
                if not schemas:
                    return

                # 每个 schema 分别收集可清空的表
                preserve_by_schema = {
                    "public": {
                        # 保留表白名单：不清空关键配置表（public）（2025-11-11更新）
                        # 规则表（1个）
                        "device_running_thresholds",
                        # 维度表（3个）
                        "dim_metric_config",
                        "dim_stations",
                        "dim_devices",
                        # 手动配置表（7个）
                        "dim_device_capabilities",
                        "pump_characteristic_curves",  # 泵特性曲线表
                        "calculation_validation_config",
                        "metric_capability_policy",
                        "metric_anomaly_strategy",  # 新增：异常判定策略表（2025-11-11）
                        "device_metric_candidates",
                        "optimization_history",  # 新增：优化历史表（2025-11-11）
                        # 配置表（5个）
                        "device_rated_params",
                        "calculation_method_registry",
                        "metric_calculation_order",
                        "calculation_parameters",
                        "global_default_rated_params",  # 新增：全局默认额定参数（2025-11-11）
                        # 元数据表（2个）
                        "dim_metric_metadata",  # 新增：指标元数据表（2025-11-11）
                        "dim_device_param_metadata",  # 新增：设备参数元数据表（2025-11-11）
                    }
                }

                disable_fk_sql = "SET session_replication_role = replica;"
                enable_fk_sql = "SET session_replication_role = DEFAULT;"

                cur.execute(disable_fk_sql)

                for schema in schemas:
                    query_tables_sql = (
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name"
                    )
                    cur.execute(query_tables_sql, (schema,))
                    tables = [row[0] for row in cur.fetchall()]
                    preserves = preserve_by_schema.get(schema, set())
                    tables = [t for t in tables if t not in preserves]

                    for table in tables:
                        try:
                            truncate_sql = f'TRUNCATE TABLE "{schema}"."{table}" RESTART IDENTITY CASCADE;'
                            cur.execute(truncate_sql)
                        except Exception:
                            # 忽略单表清理失败，继续
                            pass

                cur.execute(enable_fk_sql)
                conn.commit()
                try:
                    _act.info(
                        "[流程-完成] [数据库清理完成]",
                        extra={
                            "extra_data": {
                                "schemas_cleared": schemas,
                                "duration_ms": int((time.perf_counter() - t0) * 1000),
                            }
                        }
                    )
                except Exception:
                    pass

    except Exception:
        # 避免清理失败影响主流程
        pass




def get_system_status(settings: Settings) -> dict:
    """
    获取系统状态信息

    Args:
        settings: 应用配置

    Returns:
        系统状态字典
    """
    # 使用系统配置中的日志目录
    from app.core.config.loader_new import load_settings

    system_settings = load_settings(Path("configs"))
    logs_path = Path(system_settings.system.directories.logs)

    status = {
        "logs_directory": {
            "path": str(logs_path),
            "exists": logs_path.exists(),
            "size_mb": 0,
            "file_count": 0,
        },
        "database": {
            "name": settings.db.name,
            "host": settings.db.host,
            "table_count": 0,
            "total_rows": 0,
        },
    }

    # 检查logs目录
    logs_dir = logs_path
    if logs_dir.exists():
        try:
            files = list(logs_dir.rglob("*"))
            status["logs_directory"]["file_count"] = len(
                [f for f in files if f.is_file()]
            )
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            status["logs_directory"]["size_mb"] = round(total_size / (1024 * 1024), 2)
        except Exception:
            pass

    # 检查数据库
    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 获取表数量
                count_tables_sql = """
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                """

                start_time = time.time()
                cur.execute(count_tables_sql)
                status["database"]["table_count"] = cur.fetchone()[0]

                execution_time = (time.time() - start_time) * 1000

                # 获取总行数（仅统计主要表）
                main_tables = [
                    "fact_measurements",
                    "staging_raw",
                    "dim_stations",
                    "dim_devices",
                    "dim_metric_config",
                ]
                total_rows = 0
                for table in main_tables:
                    try:
                        count_sql = f'SELECT COUNT(*) FROM "{table}"'
                        table_start_time = time.time()
                        cur.execute(count_sql)
                        rows = cur.fetchone()[0]
                        total_rows += rows
                        table_execution_time = (time.time() - table_start_time) * 1000
                    except Exception:
                        pass

                status["database"]["total_rows"] = total_rows

    except Exception:
        pass

    return status
