"""
事务管理器核心功能验证测试
"""

import pytest
from unittest.mock import Mock, patch
import psycopg

from app.adapters.db.transaction import (
    transaction,
    auto_commit,
    reset_connection_state,
    execute_with_retry,
)


class TestTransactionCoreFunctionality:
    """测试事务管理器的核心功能是否正确工作"""

    def test_transaction_manager_basic_flow(self):
        """测试事务管理器基本流程"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = True  # 初始状态为自动提交

        # 使用事务管理器
        with transaction(mock_conn) as tx_conn:
            # 验证连接对象正确返回
            assert tx_conn == mock_conn
            # 验证自动提交被禁用
            assert mock_conn.autocommit == False

        # 验证事务提交和自动提交恢复
        mock_conn.commit.assert_called_once()
        assert mock_conn.autocommit == True

    def test_transaction_manager_exception_handling(self):
        """测试事务管理器异常处理"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = True

        # 在事务中抛出异常，应该抛出TransactionError
        from app.adapters.db.transaction import TransactionError

        with pytest.raises(TransactionError):
            with transaction(mock_conn) as tx_conn:
                assert mock_conn.autocommit == False
                raise ValueError("Test exception")

        # 验证回滚和自动提交恢复
        mock_conn.rollback.assert_called_once()
        assert mock_conn.autocommit == True

    def test_auto_commit_manager_basic_flow(self):
        """测试自动提交管理器基本流程"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False  # 初始状态为手动提交

        # 使用自动提交管理器
        with auto_commit(mock_conn) as ac_conn:
            # 验证连接对象正确返回
            assert ac_conn == mock_conn
            # 验证自动提交被启用
            assert mock_conn.autocommit == True

        # 验证自动提交状态恢复
        assert mock_conn.autocommit == False

    def test_connection_state_reset_in_transaction(self):
        """测试事务状态下的连接重置"""
        # 创建Mock连接，模拟处于事务状态
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False
        mock_conn.info.transaction_status = 2  # INTRANS

        # 重置连接状态
        reset_connection_state(mock_conn)

        # 验证回滚和自动提交设置
        mock_conn.rollback.assert_called_once()
        assert mock_conn.autocommit == True

    def test_connection_state_reset_idle_connection(self):
        """测试空闲状态下的连接重置"""
        # 创建Mock连接，模拟空闲状态
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False
        mock_conn.info.transaction_status = 1  # IDLE

        # 重置连接状态
        reset_connection_state(mock_conn)

        # 验证设置自动提交（当前实现总是调用rollback以确保状态一致）
        # 这是安全的做法，即使在IDLE状态下也确保连接完全重置
        mock_conn.rollback.assert_called_once()
        assert mock_conn.autocommit == True

    def test_execute_with_retry_success(self):
        """测试重试执行成功"""
        # 创建Mock连接和游标
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.rowcount = 5
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)

        # 执行SQL
        result = execute_with_retry(mock_conn, "SELECT 1", ("param",))

        # 验证结果
        assert result == 5
        mock_cursor.execute.assert_called_once_with("SELECT 1", ("param",))

    def test_execute_with_retry_operational_error(self):
        """测试重试执行遇到操作错误"""
        # 创建Mock连接和游标
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

        # 执行SQL，应该重试成功
        with patch("app.adapters.db.transaction.reset_connection_state") as mock_reset:
            result = execute_with_retry(mock_conn, "SELECT 1", max_retries=2)

        # 验证重试和连接重置
        assert result == 3
        assert mock_cursor.execute.call_count == 2
        mock_reset.assert_called_once_with(mock_conn)

    def test_savepoint_transaction_success(self):
        """测试保存点事务成功"""
        # 创建Mock连接和游标
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)

        # 使用保存点事务
        with transaction(mock_conn, savepoint="test_sp") as tx_conn:
            assert tx_conn == mock_conn

        # 验证保存点操作
        mock_cursor.execute.assert_any_call("SAVEPOINT test_sp")
        mock_cursor.execute.assert_any_call("RELEASE SAVEPOINT test_sp")

    def test_savepoint_transaction_rollback(self):
        """测试保存点事务回滚"""
        # 创建Mock连接和游标
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)

        # 在保存点事务中抛出异常
        with pytest.raises(Exception):
            with transaction(mock_conn, savepoint="test_sp"):
                raise Exception("Test error")

        # 验证保存点回滚
        mock_cursor.execute.assert_any_call("SAVEPOINT test_sp")
        mock_cursor.execute.assert_any_call("ROLLBACK TO SAVEPOINT test_sp")

    def test_nested_transactions_complete_flow(self):
        """测试嵌套事务完整流程"""
        # 创建Mock连接和游标
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = True
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)

        # 执行嵌套事务
        with transaction(mock_conn) as outer_conn:
            # 外层事务应该禁用自动提交
            assert mock_conn.autocommit == False

            # 内层保存点事务
            with transaction(outer_conn, savepoint="inner") as inner_conn:
                assert inner_conn == outer_conn

        # 验证完整的事务流程
        mock_cursor.execute.assert_any_call("SAVEPOINT inner")
        mock_cursor.execute.assert_any_call("RELEASE SAVEPOINT inner")
        mock_conn.commit.assert_called_once()
        assert mock_conn.autocommit == True

    def test_transaction_manager_thread_safety_simulation(self):
        """模拟测试事务管理器的线程安全性"""
        # 创建多个Mock连接模拟不同线程
        connections = []
        for i in range(3):
            mock_conn = Mock()
            mock_conn.closed = False
            mock_conn.autocommit = True
            mock_conn.id = i  # 用于区分连接
            connections.append(mock_conn)

        # 模拟并发事务
        results = []
        for conn in connections:
            with transaction(conn) as tx_conn:
                # 每个连接应该独立管理自己的事务状态
                assert tx_conn.autocommit == False
                results.append(tx_conn.id)

        # 验证所有连接都正确处理了事务
        assert results == [0, 1, 2]
        for conn in connections:
            conn.commit.assert_called_once()
            assert conn.autocommit == True

    def test_transaction_manager_error_recovery(self):
        """测试事务管理器错误恢复"""
        from app.adapters.db.transaction import TransactionError

        # 创建Mock连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = True

        # 模拟连续的事务操作，其中一个失败
        # 第一个事务成功
        with transaction(mock_conn) as tx_conn:
            assert tx_conn.autocommit == False

        # 验证第一个事务提交
        mock_conn.commit.assert_called_once()
        assert mock_conn.autocommit == True

        # 重置Mock以测试第二个事务
        mock_conn.reset_mock()
        mock_conn.autocommit = True

        # 第二个事务失败
        with pytest.raises(TransactionError):
            with transaction(mock_conn) as tx_conn:
                assert tx_conn.autocommit == False
                raise ValueError("Second transaction error")

        # 验证第二个事务回滚
        mock_conn.rollback.assert_called_once()
        assert mock_conn.autocommit == True

        # 重置Mock以测试第三个事务
        mock_conn.reset_mock()
        mock_conn.autocommit = True

        # 第三个事务应该正常工作
        with transaction(mock_conn) as tx_conn:
            assert tx_conn.autocommit == False

        # 验证第三个事务提交
        mock_conn.commit.assert_called_once()
        assert mock_conn.autocommit == True

    def test_transaction_manager_with_closed_connection(self):
        """测试关闭连接的处理"""
        # 创建Mock连接，模拟已关闭状态
        mock_conn = Mock()
        mock_conn.closed = True

        # 尝试使用已关闭的连接应该抛出异常
        with pytest.raises(Exception, match="连接已关闭"):
            with transaction(mock_conn):
                pass
