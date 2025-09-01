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

import logging
import shutil
import time
from pathlib import Path

from app.adapters.db.gateway import get_conn
from app.core.config.loader import Settings
from app.utils.logging_decorators import (
    database_operation_logger,
    log_sql_execution,
    log_sql_statement,
)

logger = logging.getLogger(__name__)


def backup_logs_directory(logs_dir: Path, backup_count: int) -> None:
    """
    备份logs目录

    Args:
        logs_dir: logs目录路径
        backup_count: 保留的备份数量
    """
    if not logs_dir.exists():
        logger.info(
            "日志目录不存在，跳过备份",
            extra={"event": "cleanup.logs.backup.skip", "logs_dir": str(logs_dir)},
        )
        return

    timestamp = int(time.time())
    backup_name = f"logs_backup_{timestamp}"
    backup_dir = logs_dir.parent / backup_name

    try:
        logger.info(
            "开始备份日志目录",
            extra={
                "event": "cleanup.logs.backup.start",
                "source": str(logs_dir),
                "destination": str(backup_dir),
                "backup_count": backup_count,
            },
        )

        # 创建备份
        shutil.copytree(logs_dir, backup_dir)

        logger.info(
            "日志目录备份完成",
            extra={
                "event": "cleanup.logs.backup.completed",
                "backup_dir": str(backup_dir),
            },
        )

        # 清理旧的备份
        cleanup_old_backups(logs_dir.parent, "logs_backup_", backup_count)

    except Exception as e:
        logger.error(
            "日志目录备份失败",
            extra={
                "event": "cleanup.logs.backup.failed",
                "error": str(e),
                "logs_dir": str(logs_dir),
            },
        )
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
            logger.info(
                "删除旧备份目录",
                extra={"event": "cleanup.backup.remove", "backup_dir": str(backup_dir)},
            )
            shutil.rmtree(backup_dir)
        except Exception as e:
            logger.warning(
                "删除旧备份目录失败",
                extra={
                    "event": "cleanup.backup.remove.failed",
                    "backup_dir": str(backup_dir),
                    "error": str(e),
                },
            )


def clear_logs_directory(logs_dir: Path, backup_count: int) -> None:
    """
    清理logs目录

    Args:
        logs_dir: logs目录路径
        backup_count: 备份数量
    """
    logger.info(
        "开始清理日志目录",
        extra={
            "event": "cleanup.logs.start",
            "logs_dir": str(logs_dir),
            "backup_count": backup_count,
        },
    )

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
                logger.info(
                    "删除日志目录",
                    extra={
                        "event": "cleanup.logs.remove.start",
                        "logs_dir": str(logs_dir),
                        "file_count": file_count,
                    },
                )

                shutil.rmtree(logs_dir)

                logger.info(
                    "日志目录清理完成",
                    extra={
                        "event": "cleanup.logs.completed",
                        "logs_dir": str(logs_dir),
                        "files_removed": file_count,
                    },
                )
            else:
                logger.info(
                    "日志目录不存在，跳过清理",
                    extra={"event": "cleanup.logs.skip", "logs_dir": str(logs_dir)},
                )
            break
        except Exception as e:
            retry += 1
            logger.warning(
                "清理日志目录失败，稍后重试",
                extra={
                    "event": "cleanup.logs.failed",
                    "error": str(e),
                    "logs_dir": str(logs_dir),
                    "retry": retry,
                    "max_retries": max_retries,
                },
            )
            if retry >= max_retries:
                logger.error(
                    "清理日志目录多次失败，跳过该步骤",
                    extra={
                        "event": "cleanup.logs.giveup",
                        "logs_dir": str(logs_dir),
                    },
                )
                break


@database_operation_logger()
def clear_database(settings: Settings) -> None:
    """
    清理数据库

    Args:
        settings: 应用配置
    """
    logger.info(
        "开始清理数据库",
        extra={"event": "cleanup.database.start", "database": settings.db.name},
    )

    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 获取所有表名
                query_tables_sql = """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """

                log_sql_statement(query_tables_sql, logger=logger)
                start_time = time.time()
                cur.execute(query_tables_sql)
                tables = [row[0] for row in cur.fetchall()]

                execution_time = (time.time() - start_time) * 1000
                log_sql_execution(
                    sql_type="SELECT",
                    sql_summary="查询数据库中的所有表",
                    execution_time_ms=execution_time,
                    table_name="information_schema.tables",
                    logger=logger,
                )

                if not tables:
                    logger.info(
                        "数据库中没有表，跳过清理",
                        extra={
                            "event": "cleanup.database.skip",
                            "database": settings.db.name,
                        },
                    )
                    return

                logger.info(
                    "开始清空数据库表",
                    extra={
                        "event": "cleanup.database.truncate.start",
                        "database": settings.db.name,
                        "table_count": len(tables),
                        "tables": tables,
                    },
                )

                # 禁用外键约束检查
                disable_fk_sql = "SET session_replication_role = replica;"
                log_sql_statement(disable_fk_sql, logger=logger)
                cur.execute(disable_fk_sql)
                log_sql_execution(
                    sql_type="SET",
                    sql_summary="禁用外键约束检查",
                    execution_time_ms=0,
                    logger=logger,
                )

                # 清空所有表
                for table in tables:
                    try:
                        truncate_sql = (
                            f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE;'
                        )
                        log_sql_statement(truncate_sql, {"table_name": table}, logger)

                        table_start_time = time.time()
                        cur.execute(truncate_sql)
                        table_execution_time = (time.time() - table_start_time) * 1000

                        log_sql_execution(
                            sql_type="TRUNCATE",
                            sql_summary=f"清空表 {table}",
                            execution_time_ms=table_execution_time,
                            table_name=table,
                            logger=logger,
                        )

                        logger.debug(
                            "清空表完成",
                            extra={
                                "event": "cleanup.database.table.truncated",
                                "table": table,
                            },
                        )
                    except Exception as e:
                        log_sql_execution(
                            sql_type="TRUNCATE",
                            sql_summary=f"清空表 {table}",
                            execution_time_ms=0,
                            table_name=table,
                            error=str(e),
                            logger=logger,
                        )
                        logger.warning(
                            "清空表失败",
                            extra={
                                "event": "cleanup.database.table.failed",
                                "table": table,
                                "error": str(e),
                            },
                        )

                # 恢复外键约束检查
                enable_fk_sql = "SET session_replication_role = DEFAULT;"
                log_sql_statement(enable_fk_sql, logger=logger)
                cur.execute(enable_fk_sql)
                log_sql_execution(
                    sql_type="SET",
                    sql_summary="恢复外键约束检查",
                    execution_time_ms=0,
                    logger=logger,
                )

                conn.commit()

                logger.info(
                    "数据库清理完成",
                    extra={
                        "event": "cleanup.database.completed",
                        "database": settings.db.name,
                        "tables_cleared": len(tables),
                    },
                )

    except Exception as e:
        logger.error(
            "数据库清理失败",
            extra={
                "event": "cleanup.database.failed",
                "error": str(e),
                "database": settings.db.name,
            },
        )
        raise


def perform_startup_cleanup(settings: Settings) -> None:
    """
    执行启动清理

    Args:
        settings: 应用配置
    """
    cleanup_config = settings.logging.startup_cleanup

    logger.info(
        "开始执行启动清理",
        extra={
            "event": "cleanup.startup.begin",
            "clear_logs": cleanup_config.clear_logs,
            "clear_database": cleanup_config.clear_database,
            "confirm_clear": cleanup_config.confirm_clear,
        },
    )

    # 确认提示
    if cleanup_config.confirm_clear:
        response = input("确认清理数据库和日志？(y/N): ").strip().lower()
        if response not in ("y", "yes"):
            logger.info(
                "用户取消清理操作", extra={"event": "cleanup.startup.cancelled"}
            )
            return

    start_time = time.time()

    try:
        # 清理日志目录
        if cleanup_config.clear_logs:
            # 使用系统配置中的日志目录
            from app.core.config.loader_new import load_settings

            system_settings = load_settings(Path("configs"))
            logs_dir = Path(system_settings.system.directories.logs)
            clear_logs_directory(logs_dir, cleanup_config.logs_backup_count)

        # 清理数据库（若启用）
        if cleanup_config.clear_database:
            try:
                clear_database(settings)
            except Exception as e:
                logger.error(
                    "启动清理: 数据库清理失败，已跳过",
                    extra={
                        "event": "cleanup.database.skip_after_error",
                        "error": str(e),
                    },
                )
                # 避免事务中止刷屏，直接跳过后续清理

        end_time = time.time()
        duration = end_time - start_time

        logger.info(
            "启动清理完成",
            extra={
                "event": "cleanup.startup.completed",
                "duration_seconds": round(duration, 2),
                "clear_logs": cleanup_config.clear_logs,
                "clear_database": cleanup_config.clear_database,
            },
        )

    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time

        logger.error(
            "启动清理失败",
            extra={
                "event": "cleanup.startup.failed",
                "error": str(e),
                "duration_seconds": round(duration, 2),
            },
        )
        raise


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
        except Exception as e:
            logger.warning(
                "获取日志目录信息失败",
                extra={"event": "cleanup.status.logs.failed", "error": str(e)},
            )

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

                log_sql_statement(count_tables_sql, logger=logger)
                start_time = time.time()
                cur.execute(count_tables_sql)
                status["database"]["table_count"] = cur.fetchone()[0]

                execution_time = (time.time() - start_time) * 1000
                log_sql_execution(
                    sql_type="SELECT",
                    sql_summary="获取数据库表数量",
                    execution_time_ms=execution_time,
                    table_name="information_schema.tables",
                    logger=logger,
                )

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
                        log_sql_statement(count_sql, {"table": table}, logger)

                        table_start_time = time.time()
                        cur.execute(count_sql)
                        rows = cur.fetchone()[0]
                        total_rows += rows

                        table_execution_time = (time.time() - table_start_time) * 1000
                        log_sql_execution(
                            sql_type="SELECT",
                            sql_summary=f"统计表 {table} 行数",
                            execution_time_ms=table_execution_time,
                            table_name=table,
                            logger=logger,
                        )
                    except Exception:
                        pass  # 表不存在时跳过

                status["database"]["total_rows"] = total_rows

    except Exception as e:
        logger.warning(
            "获取数据库信息失败",
            extra={"event": "cleanup.status.database.failed", "error": str(e)},
        )

    return status
