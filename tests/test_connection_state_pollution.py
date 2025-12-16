"""
连接状态污染修复测试
"""

import time
import pytest
from unittest.mock import Mock, patch, MagicMock
import psycopg

from app.adapters.db.transaction import (
    validate_connection_state,
    diagnose_connection_issues,
    reset_connection_state,
    auto_commit,
)
from app.adapters.db.pool import PooledConnection


class TestConnectionStatePollution:
    """测试连接状态污染修复功能"""

    def test_validate_connection_state_healthy(self):
        """测试健康连接的状态验证"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = True
        mock_conn.info.transaction_status = psycopg.pq.TransactionStatus.IDLE
        mock_conn.info.backend_pid = 12345

        # Mock游标和查询结果
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)

        # 设置查询结果
        mock_cursor.fetchone.side_effect = [
            ("public",),  # search_path
            ("UTC",),  # timezone
            ("UTF8",),  # client_encoding
            ("0",),  # statement_timeout
        ]

        # 验证连接状态
        state = validate_connection_state(mock_conn)

        # 验证结果
        assert state["healthy"] is True
        assert state["connection_closed"] is False
        assert state["autocommit"] is True
        assert len(state["issues"]) == 0
        assert "search_path" in state["parameters"]
        assert state["parameters"]["search_path"] == "public"

    def test_validate_connection_state_closed(self):
        """测试关闭连接的状态验证"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_conn.closed = True

        # 验证连接状态
        state = validate_connection_state(mock_conn)

        # 验证结果
        assert state["healthy"] is False
        assert state["connection_closed"] is True
        assert "连接已关闭" in state["issues"]

    def test_validate_connection_state_inconsistent(self):
        """测试状态不一致的连接验证"""
        # 创建Mock连接，模拟状态不一致
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False  # 手动提交模式
        mock_conn.info.transaction_status = (
            psycopg.pq.TransactionStatus.IDLE
        )  # 但事务状态为IDLE

        # Mock游标
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.fetchone.side_effect = [("public",), ("UTC",), ("UTF8",), ("0",)]

        # 验证连接状态
        state = validate_connection_state(mock_conn)

        # 验证结果
        assert state["healthy"] is False
        assert any("状态不一致" in issue for issue in state["issues"])

    def test_diagnose_connection_issues_healthy(self):
        """测试健康连接的诊断"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = True
        mock_conn.info.transaction_status = psycopg.pq.TransactionStatus.IDLE

        # Mock游标
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.fetchone.side_effect = [("public",), ("UTC",), ("UTF8",), ("0",)]

        # 诊断连接
        report = diagnose_connection_issues(mock_conn)

        # 验证结果
        assert report == "连接状态正常"

    def test_diagnose_connection_issues_with_problems(self):
        """测试有问题连接的诊断"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_conn.closed = True

        # 诊断连接
        report = diagnose_connection_issues(mock_conn)

        # 验证结果
        assert "连接状态问题诊断" in report
        assert "连接已关闭" in report
        assert "建议的修复措施" in report
        assert "重新创建连接" in report

    def test_health_check_with_auto_commit(self):
        """测试健康检查使用自动提交模式"""
        # 创建Mock连接池连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False  # 初始为手动提交模式

        # Mock游标
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.fetchone.return_value = (1,)

        # 创建PooledConnection
        mock_pool = Mock()
        pooled_conn = PooledConnection(mock_conn, mock_pool)

        # 执行健康检查
        result = pooled_conn.check_health()

        # 验证结果
        assert result is True
        assert pooled_conn.is_healthy is True

        # 验证自动提交状态被正确恢复
        # 健康检查应该使用auto_commit上下文管理器，不影响原始状态
        assert mock_conn.autocommit == False  # 原始状态应该被恢复

    def test_connection_parameter_reset(self):
        """测试连接参数重置功能"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False
        mock_conn.info.transaction_status = psycopg.pq.TransactionStatus.INTRANS

        # Mock游标
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)

        # 重置连接状态
        reset_connection_state(mock_conn)

        # 验证事务回滚
        mock_conn.rollback.assert_called_once()

        # 验证自动提交启用
        assert mock_conn.autocommit == True

        # 验证参数重置SQL被执行
        expected_calls = [
            "SET search_path TO public",
            "SET timezone TO 'UTC'",
            "SET client_encoding TO 'UTF8'",
            "RESET ALL",
        ]

        for expected_sql in expected_calls:
            mock_cursor.execute.assert_any_call(expected_sql)

    def test_pooled_connection_validation(self):
        """测试池化连接验证功能"""
        # 创建Mock连接池
        mock_pool = Mock()

        # 创建Mock连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = True
        mock_conn.info.transaction_status = psycopg.pq.TransactionStatus.IDLE

        # Mock游标
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.fetchone.side_effect = [
            (1,),  # 健康检查
            ("public",),
            ("UTC",),
            ("UTF8",),
            ("0",),  # 状态验证
        ]

        # 创建PooledConnection
        pooled_conn = PooledConnection(mock_conn, mock_pool)

        # 验证连接
        from app.adapters.db.pool import ConnectionPool

        pool = ConnectionPool.__new__(ConnectionPool)  # 创建实例但不调用__init__

        result = pool._validate_pooled_connection(pooled_conn)

        # 验证结果
        assert result is True

    def test_pooled_connection_validation_fails(self):
        """测试池化连接验证失败的情况"""
        # 创建Mock连接池
        mock_pool = Mock()

        # 创建Mock连接，模拟状态污染
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False  # 不在自动提交模式，状态被污染

        # Mock游标
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.fetchone.return_value = (1,)

        # 创建PooledConnection
        pooled_conn = PooledConnection(mock_conn, mock_pool)
        # 设置为长时间未使用，触发详细验证
        pooled_conn.last_used = time.time() - 60  # 60秒前使用

        # 验证连接
        from app.adapters.db.pool import ConnectionPool

        pool = ConnectionPool.__new__(ConnectionPool)  # 创建实例但不调用__init__

        # Mock validate_connection_state 和 auto_commit
        with patch(
            "app.adapters.db.transaction.validate_connection_state"
        ) as mock_validate:
            mock_validate.return_value = {"healthy": True}

            with patch("app.adapters.db.transaction.auto_commit") as mock_auto_commit:
                mock_auto_commit.return_value.__enter__ = Mock(return_value=mock_conn)
                mock_auto_commit.return_value.__exit__ = Mock(return_value=None)

                result = pool._validate_pooled_connection(pooled_conn)

        # 验证结果 - 由于autocommit=False，应该失败
        assert result is False

    def test_connection_state_pollution_prevention(self):
        """测试连接状态污染预防机制"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = True

        # Mock游标
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)

        # 模拟用户代码污染连接状态
        with auto_commit(mock_conn) as conn:
            # 在自动提交模式下执行操作
            assert conn.autocommit == True

            # 模拟执行一些可能改变状态的操作
            with conn.cursor() as cur:
                cur.execute("SET search_path TO custom_schema")

        # 验证自动提交状态被恢复
        assert mock_conn.autocommit == True

    def test_connection_state_reset_with_exception(self):
        """测试连接状态重置时的异常处理"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False
        mock_conn.info.transaction_status = psycopg.pq.TransactionStatus.INTRANS

        # Mock游标，模拟参数重置失败
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.execute.side_effect = Exception("Parameter reset failed")

        # 重置连接状态不应该抛出异常
        try:
            reset_connection_state(mock_conn)
        except Exception:
            pytest.fail("reset_connection_state should not raise exceptions")

        # 验证基本的事务回滚和自动提交设置仍然执行
        mock_conn.rollback.assert_called_once()
        assert mock_conn.autocommit == True
