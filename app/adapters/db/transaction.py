"""
数据库事务管理模块（app.adapters.db.transaction）

本模块提供统一的事务管理功能：
- 事务上下文管理器
- 连接状态重置机制
- 统一的事务策略
- 自动错误处理和回滚

使用方式：
1. 使用 transaction() 上下文管理器进行事务操作
2. 使用 auto_commit() 进行自动提交操作
3. 使用 reset_connection_state() 重置连接状态

设计原则：
- 明确的事务边界
- 自动的错误处理
- 连接状态一致性
- 向后兼容性
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

import psycopg
from psycopg import Connection


import logging

_act = logging.getLogger(__name__)


class TransactionError(Exception):
    """事务操作异常"""

    pass


def reset_connection_state(conn: Connection) -> None:
    """
    重置连接状态，确保连接处于干净状态

    此函数会：
    1. 回滚任何未提交的事务
    2. 重置连接到自动提交模式
    3. 清除任何错误状态
    4. 重置关键的连接参数

    参数：
        conn: 数据库连接
    """
    try:
        _act.debug("[核心-事务] [重置连接状态]")

        # 检查连接是否处于事务中
        if conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
            conn.rollback()
            _act.debug("[核心-事务] [回滚未提交事务]")

        # 确保连接处于自动提交模式
        if not conn.autocommit:
            conn.autocommit = True

        # 重置关键的连接参数到默认值
        _reset_connection_parameters(conn)

    except Exception:
        pass


def _reset_connection_parameters(conn: Connection) -> None:
    """
    重置连接参数到默认值

    重置可能被用户代码修改的关键参数：
    - search_path: 重置到默认搜索路径
    - timezone: 重置到UTC
    - statement_timeout: 保持应用设置的值
    - 其他会话级参数

    参数：
        conn: 数据库连接
    """
    try:
        with conn.cursor() as cur:
            # 重置搜索路径到默认值（public schema）
            cur.execute("SET search_path TO public")

            # 重置时区到UTC（如果应用有特定需求可以调整）
            cur.execute("SET timezone TO 'UTC'")

            # 重置其他可能被修改的参数
            cur.execute("SET client_encoding TO 'UTF8'")

            # 清除任何临时设置的变量
            cur.execute("RESET ALL")

    except Exception:
        pass


@contextmanager
def transaction(
    conn: Connection, savepoint: Optional[str] = None
) -> Iterator[Connection]:
    """
    事务上下文管理器

    提供明确的事务边界管理：
    - 自动开始事务
    - 成功时自动提交
    - 异常时自动回滚
    - 支持嵌套事务（savepoint）

    参数：
        conn: 数据库连接
        savepoint: 保存点名称，用于嵌套事务

    用法：
        with transaction(conn) as tx_conn:
            # 数据库操作
            cur.execute("INSERT ...")
            # 自动提交
    """
    if conn.closed:
        raise TransactionError("连接已关闭，无法开始事务")

    # 保存原始自动提交状态
    original_autocommit = conn.autocommit

    try:
        # 禁用自动提交以开始事务
        if conn.autocommit:
            conn.autocommit = False

        # 如果指定了保存点，创建保存点
        if savepoint:
            with conn.cursor() as cur:
                cur.execute(f"SAVEPOINT {savepoint}")

        yield conn

        # 成功完成，提交事务
        if savepoint:
            with conn.cursor() as cur:
                cur.execute(f"RELEASE SAVEPOINT {savepoint}")
        else:
            # 调试日志：记录提交前的连接状态
            _act.debug(
                "[核心-事务] [准备提交]",
                extra={
                    "extra_data": {
                        '事务状态（修改前）': str(conn.info.transaction_status),
                        '自动提交（修改前）': conn.autocommit,
                    }
                },
            )

            conn.commit()

            # 调试日志：记录提交后的连接状态
            _act.debug(
                "[核心-事务] [事务已提交]",
                extra={
                    "extra_data": {
                        '事务状态（修改后）': str(conn.info.transaction_status),
                        '自动提交（修改后）': conn.autocommit,
                    }
                },
            )

    except Exception as e:
        # 发生异常，回滚事务
        try:
            if savepoint:
                with conn.cursor() as cur:
                    cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            else:
                conn.rollback()
        except Exception:
            pass

        # 重新抛出原始异常
        raise TransactionError(f"事务执行失败: {e}") from e

    finally:
        # 恢复原始自动提交状态
        try:
            # 调试日志：记录恢复前的状态
            _act.debug(
                "[核心-事务] [恢复autocommit前]",
                extra={
                    "extra_data": {
                        '事务状态': str(conn.info.transaction_status),
                        '自动提交（当前）': conn.autocommit,
                        '自动提交（原始）': original_autocommit,
                    }
                },
            )

            conn.autocommit = original_autocommit

            # 调试日志：记录恢复后的状态
            _act.debug(
                "[核心-事务] [恢复autocommit后]",
                extra={
                    "extra_data": {
                        '事务状态': str(conn.info.transaction_status),
                        '自动提交': conn.autocommit,
                    }
                },
            )
        except Exception as e:
            _act.error(
                "[核心-事务] [恢复autocommit失败]",
                extra={"extra_data": {"error": str(e)}},
            )


@contextmanager
def auto_commit(conn: Connection) -> Iterator[Connection]:
    """
    自动提交上下文管理器

    用于需要立即提交的单个操作：
    - 每个操作自动提交
    - 适用于DDL操作和独立的DML操作
    - 不支持回滚

    参数：
        conn: 数据库连接

    用法：
        with auto_commit(conn) as ac_conn:
            # 每个操作自动提交
            cur.execute("CREATE TABLE ...")
    """
    if conn.closed:
        raise TransactionError("连接已关闭，无法进行自动提交操作")

    # 保存原始自动提交状态
    original_autocommit = conn.autocommit

    try:
        # 启用自动提交
        if not conn.autocommit:
            conn.autocommit = True

        yield conn

    finally:
        # 恢复原始自动提交状态
        try:
            conn.autocommit = original_autocommit
        except Exception as e:
            pass


def execute_with_retry(
    conn: Connection, sql: str, params: Optional[tuple] = None, max_retries: int = 3
) -> int:
    """
    带重试的SQL执行

    参数：
        conn: 数据库连接
        sql: SQL语句
        params: 参数
        max_retries: 最大重试次数

    返回：
        影响的行数
    """
    for attempt in range(max_retries):
        try:
            with conn.cursor() as cur:
                if params:
                    cur.execute(sql, params)
                else:
                    cur.execute(sql)
                return cur.rowcount or 0

        except (psycopg.OperationalError, psycopg.InterfaceError) as e:
            if attempt < max_retries - 1:
                # 重置连接状态
                reset_connection_state(conn)
                continue
            else:
                raise TransactionError(f"SQL执行失败，已达最大重试次数: {e}") from e
        except Exception as e:
            # 非连接相关错误，不重试
            raise TransactionError(f"SQL执行失败: {e}") from e


def validate_connection_state(conn: Connection) -> dict:
    """
    验证连接状态，返回详细的状态信息

    检查连接的各种状态参数，用于诊断连接状态问题。

    参数：
        conn: 数据库连接

    返回：
        包含连接状态信息的字典
    """
    try:
        state_info = {
            "connection_closed": conn.closed,
            '自动提交': conn.autocommit,
            '事务状态': (
                conn.info.transaction_status.name
                if hasattr(conn.info.transaction_status, "name")
                else str(conn.info.transaction_status)
            ),
            "backend_pid": getattr(conn.info, "backend_pid", None),
            "parameters": {},
            "healthy": True,
            "issues": [],
        }

        # 检查连接是否关闭
        if conn.closed:
            state_info["healthy"] = False
            state_info["issues"].append("连接已关闭")
            return state_info

        # 获取关键的连接参数
        try:
            with conn.cursor() as cur:
                # 获取当前的关键参数
                cur.execute("SHOW search_path")
                state_info["parameters"]["search_path"] = cur.fetchone()[0]

                cur.execute("SHOW timezone")
                state_info["parameters"]["timezone"] = cur.fetchone()[0]

                cur.execute("SHOW client_encoding")
                state_info["parameters"]["client_encoding"] = cur.fetchone()[0]

                cur.execute("SHOW statement_timeout")
                state_info["parameters"]["statement_timeout"] = cur.fetchone()[0]

        except Exception as e:
            state_info["issues"].append(f"无法获取连接参数: {e}")
            state_info["healthy"] = False

        # 检查事务状态是否一致
        if (
            not conn.autocommit
            and conn.info.transaction_status == psycopg.pq.TransactionStatus.IDLE
        ):
            state_info["issues"].append(
                "连接处于手动提交模式但事务状态为IDLE，状态不一致"
            )
            state_info["healthy"] = False

        return state_info

    except Exception as e:
        return {
            "healthy": False,
            "error": f"连接状态验证失败: {e}",
            "connection_closed": True,
            "issues": [f"状态验证异常: {e}"],
        }


def diagnose_connection_issues(conn: Connection) -> str:
    """
    诊断连接问题，返回人类可读的诊断报告

    参数：
        conn: 数据库连接

    返回：
        诊断报告字符串
    """
    state = validate_connection_state(conn)

    if state["healthy"]:
        return "连接状态正常"

    issues = state.get("issues", [])
    if not issues:
        return "连接状态异常，但无法确定具体问题"

    report = "连接状态问题诊断:\n"
    for i, issue in enumerate(issues, 1):
        report += f"{i}. {issue}\n"

    # 提供修复建议
    report += "\n建议的修复措施:\n"
    if "连接已关闭" in str(issues):
        report += "- 重新创建连接\n"
    if "状态不一致" in str(issues):
        report += "- 调用 reset_connection_state() 重置连接状态\n"
    if "无法获取连接参数" in str(issues):
        report += "- 检查连接是否仍然有效，考虑重新创建连接\n"

    return report
