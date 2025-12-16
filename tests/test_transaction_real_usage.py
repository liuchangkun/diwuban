"""
事务管理器实际使用测试
"""

import pytest
from unittest.mock import Mock, patch

from app.adapters.db.transaction import transaction, auto_commit, reset_connection_state
from app.adapters.db.gateway import insert_rejects, run_merge_window
from app.core.types import RejectRow


class TestTransactionRealUsage:
    """测试事务管理器在实际数据库操作中的使用"""

    def test_insert_rejects_with_transaction(self):
        """测试insert_rejects函数使用事务管理器"""
        # 创建Mock连接和游标
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # 测试数据（使用RejectRow对象）
        rejects = [
            RejectRow(source_hint="test1", error_msg="error1"),
            RejectRow(source_hint="test2", error_msg="error2")
        ]

        # 调用函数
        result = insert_rejects(mock_conn, rejects)
        
        # 验证事务操作
        assert result == 2  # 应该返回插入的行数
        mock_cursor.executemany.assert_called_once()
        mock_conn.commit.assert_called_once()  # 事务应该被提交

    def test_insert_rejects_with_exception(self):
        """测试insert_rejects函数异常处理"""
        # 创建Mock连接和游标
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # 模拟SQL执行错误
        mock_cursor.executemany.side_effect = Exception("SQL error")

        # 测试数据（使用RejectRow对象）
        rejects = [RejectRow(source_hint="test", error_msg="error")]

        # 调用函数应该抛出异常
        with pytest.raises(Exception):
            insert_rejects(mock_conn, rejects)
        
        # 验证回滚被调用
        mock_conn.rollback.assert_called_once()

    def test_run_merge_window_with_transaction(self):
        """测试run_merge_window函数使用事务管理器"""
        # 创建Mock连接和游标
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.rowcount = 10  # 模拟影响的行数
        mock_cursor.fetchone.return_value = (10, 100, 5, 95, 0.05, 1000)  # Mock返回值

        # 调用函数（使用新的签名）
        result = run_merge_window(
            mock_conn,
            start_utc="2025-01-01 00:00:00",
            end_utc="2025-01-01 01:00:00",
            default_station_tz="Asia/Shanghai"
        )

        # 验证事务操作
        assert isinstance(result, dict)  # 应该返回字典
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()  # 事务应该被提交

    def test_connection_state_reset_functionality(self):
        """测试连接状态重置功能"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False
        mock_conn.info.transaction_status = 2  # INTRANS (事务中)
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # 调用连接状态重置
        reset_connection_state(mock_conn)
        
        # 验证状态重置操作
        mock_conn.rollback.assert_called_once()
        assert mock_conn.autocommit == True

    def test_transaction_context_manager_integration(self):
        """测试事务上下文管理器集成"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = True
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # 使用事务上下文管理器
        with transaction(mock_conn) as tx_conn:
            assert tx_conn == mock_conn
            assert mock_conn.autocommit == False  # 应该禁用自动提交
            
            # 模拟数据库操作
            with tx_conn.cursor() as cur:
                cur.execute("INSERT INTO test VALUES (1)")
        
        # 验证事务提交和自动提交恢复
        mock_conn.commit.assert_called_once()
        assert mock_conn.autocommit == True

    def test_auto_commit_context_manager_integration(self):
        """测试自动提交上下文管理器集成"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # 使用自动提交上下文管理器
        with auto_commit(mock_conn) as ac_conn:
            assert ac_conn == mock_conn
            assert mock_conn.autocommit == True  # 应该启用自动提交
            
            # 模拟数据库操作
            with ac_conn.cursor() as cur:
                cur.execute("CREATE TABLE test (id INT)")
        
        # 验证自动提交状态恢复
        assert mock_conn.autocommit == False

    def test_nested_transaction_with_savepoint(self):
        """测试嵌套事务（保存点）"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # 使用嵌套事务
        with transaction(mock_conn) as outer_conn:
            # 外层事务操作
            with outer_conn.cursor() as cur:
                cur.execute("INSERT INTO outer_table VALUES (1)")
            
            # 内层事务（保存点）
            with transaction(outer_conn, savepoint="inner_sp") as inner_conn:
                with inner_conn.cursor() as cur:
                    cur.execute("INSERT INTO inner_table VALUES (2)")
        
        # 验证保存点操作
        mock_cursor.execute.assert_any_call("SAVEPOINT inner_sp")
        mock_cursor.execute.assert_any_call("RELEASE SAVEPOINT inner_sp")
        mock_conn.commit.assert_called_once()

    def test_transaction_error_with_savepoint_rollback(self):
        """测试保存点错误回滚"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.autocommit = False
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # 使用嵌套事务并模拟内层错误
        with transaction(mock_conn) as outer_conn:
            # 外层事务操作
            with outer_conn.cursor() as cur:
                cur.execute("INSERT INTO outer_table VALUES (1)")
            
            # 内层事务出错
            try:
                with transaction(outer_conn, savepoint="inner_sp") as inner_conn:
                    with inner_conn.cursor() as cur:
                        cur.execute("INSERT INTO inner_table VALUES (2)")
                        raise Exception("Inner transaction error")
            except Exception:
                pass  # 忽略内层错误，外层事务应该继续
        
        # 验证保存点回滚和外层事务提交
        mock_cursor.execute.assert_any_call("SAVEPOINT inner_sp")
        mock_cursor.execute.assert_any_call("ROLLBACK TO SAVEPOINT inner_sp")
        mock_conn.commit.assert_called_once()  # 外层事务仍然提交

    def test_connection_pool_integration_with_transaction_manager(self):
        """测试连接池与事务管理器的完整集成"""
        # 这个测试验证整个流程：从连接池获取连接 -> 使用事务

        with patch('app.adapters.db.pool.psycopg.connect') as mock_connect, \
             patch('app.adapters.db._pool_initialized', True), \
             patch('app.adapters.db.pool.get_pool') as mock_get_pool:

            # 设置Mock连接
            mock_conn = Mock()
            mock_conn.closed = False
            mock_conn.autocommit = True
            mock_conn.info.transaction_status = 1  # IDLE
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_cursor.fetchone.return_value = (1,)
            mock_connect.return_value = mock_conn

            # Mock连接池
            mock_pool = Mock()
            mock_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_pool.get_connection.return_value.__exit__ = Mock(return_value=None)
            mock_get_pool.return_value = mock_pool

            # 模拟从连接池获取连接并使用事务
            from app.adapters.db import get_connection

            with get_connection() as conn:
                # 使用事务管理器
                with transaction(conn) as tx_conn:
                    with tx_conn.cursor() as cur:
                        cur.execute("INSERT INTO test VALUES (%s)", ("test_data",))

            # 验证事务操作
            mock_cursor.execute.assert_called()
            mock_conn.commit.assert_called()

            # 验证连接池的get_connection被调用
            mock_pool.get_connection.assert_called()
