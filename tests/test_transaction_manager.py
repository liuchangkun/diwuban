"""
测试事务管理器功能
"""

import pytest
import psycopg
from unittest.mock import Mock, patch, MagicMock

from app.adapters.db.transaction import (
    transaction,
    auto_commit,
    reset_connection_state,
    execute_with_retry,
    TransactionError,
)


class TestTransactionManager:
    """测试事务管理器"""

    def test_reset_connection_state_idle_connection(self):
        """测试重置空闲连接状态"""
        mock_conn = Mock()
        mock_conn.info.transaction_status = psycopg.pq.TransactionStatus.IDLE
        mock_conn.autocommit = False

        reset_connection_state(mock_conn)

        # 应该设置为自动提交模式
        assert mock_conn.autocommit == True
        # 空闲连接不应该调用rollback
        mock_conn.rollback.assert_not_called()

    def test_reset_connection_state_in_transaction(self):
        """测试重置事务中的连接状态"""
        mock_conn = Mock()
        mock_conn.info.transaction_status = psycopg.pq.TransactionStatus.INTRANS
        mock_conn.autocommit = False

        reset_connection_state(mock_conn)

        # 应该回滚事务并设置为自动提交模式
        mock_conn.rollback.assert_called_once()
        assert mock_conn.autocommit == True

    def test_reset_connection_state_with_exception(self):
        """测试重置连接状态时发生异常"""
        mock_conn = Mock()
        mock_conn.info.transaction_status = psycopg.pq.TransactionStatus.INTRANS
        mock_conn.rollback.side_effect = Exception("rollback failed")

        # 不应该抛出异常
        reset_connection_state(mock_conn)

    def test_transaction_success(self):
        """测试事务成功提交"""
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = True

        with transaction(mock_conn) as conn:
            assert conn == mock_conn
            # 应该禁用自动提交
            assert mock_conn.autocommit == False

        # 应该提交事务并恢复自动提交
        mock_conn.commit.assert_called_once()
        assert mock_conn.autocommit == True

    def test_transaction_with_exception(self):
        """测试事务异常回滚"""
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = True

        with pytest.raises(TransactionError):
            with transaction(mock_conn) as conn:
                assert mock_conn.autocommit == False
                raise ValueError("test error")

        # 应该回滚事务并恢复自动提交
        mock_conn.rollback.assert_called_once()
        assert mock_conn.autocommit == True

    def test_transaction_with_savepoint(self):
        """测试带保存点的事务"""
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)

        with transaction(mock_conn, savepoint="test_sp") as conn:
            assert conn == mock_conn

        # 应该创建和释放保存点
        mock_cursor.execute.assert_any_call("SAVEPOINT test_sp")
        mock_cursor.execute.assert_any_call("RELEASE SAVEPOINT test_sp")

    def test_transaction_savepoint_rollback(self):
        """测试保存点回滚"""
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)

        with pytest.raises(TransactionError):
            with transaction(mock_conn, savepoint="test_sp"):
                raise ValueError("test error")

        # 应该回滚到保存点
        mock_cursor.execute.assert_any_call("ROLLBACK TO SAVEPOINT test_sp")

    def test_transaction_closed_connection(self):
        """测试关闭的连接"""
        mock_conn = Mock()
        mock_conn.closed = True

        with pytest.raises(TransactionError, match="连接已关闭"):
            with transaction(mock_conn):
                pass

    def test_auto_commit_success(self):
        """测试自动提交成功"""
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False

        with auto_commit(mock_conn) as conn:
            assert conn == mock_conn
            # 应该启用自动提交
            assert mock_conn.autocommit == True

        # 应该恢复原始状态
        assert mock_conn.autocommit == False

    def test_auto_commit_closed_connection(self):
        """测试自动提交关闭的连接"""
        mock_conn = Mock()
        mock_conn.closed = True

        with pytest.raises(TransactionError, match="连接已关闭"):
            with auto_commit(mock_conn):
                pass

    def test_execute_with_retry_success(self):
        """测试重试执行成功"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.rowcount = 5
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)

        result = execute_with_retry(mock_conn, "SELECT 1", ("param",))

        assert result == 5
        mock_cursor.execute.assert_called_once_with("SELECT 1", ("param",))

    def test_execute_with_retry_operational_error(self):
        """测试重试执行遇到操作错误"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = [
            psycopg.OperationalError("connection lost"),
            None,  # 第二次成功
        ]
        mock_cursor.rowcount = 3
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)

        with patch("app.adapters.db.transaction.reset_connection_state") as mock_reset:
            result = execute_with_retry(mock_conn, "SELECT 1", max_retries=2)

        assert result == 3
        assert mock_cursor.execute.call_count == 2
        mock_reset.assert_called_once_with(mock_conn)

    def test_execute_with_retry_max_retries_exceeded(self):
        """测试重试次数超限"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = psycopg.OperationalError("persistent error")
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)

        with pytest.raises(TransactionError, match="已达最大重试次数"):
            execute_with_retry(mock_conn, "SELECT 1", max_retries=2)

    def test_execute_with_retry_non_retryable_error(self):
        """测试不可重试的错误"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = ValueError("syntax error")
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)

        with pytest.raises(TransactionError, match="SQL执行失败"):
            execute_with_retry(mock_conn, "SELECT 1")

        # 不应该重试
        assert mock_cursor.execute.call_count == 1
