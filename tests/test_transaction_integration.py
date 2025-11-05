"""
事务管理器集成测试
"""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, cleanup_database, get_connection
from app.adapters.db.transaction import transaction, auto_commit, reset_connection_state


class TestTransactionIntegration:
    """测试事务管理器与连接池的集成"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """设置和清理测试环境"""
        # 先清理可能存在的真实连接池
        cleanup_database()

        # 使用Mock避免真实数据库连接
        with patch("app.adapters.db.pool.psycopg.connect") as mock_connect:
            mock_conn = Mock()
            mock_conn.closed = False
            mock_conn.autocommit = True
            mock_conn.info.transaction_status = 1  # IDLE
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            # 修复fetchone返回值
            mock_cursor.fetchone.return_value = (1,)  # 返回元组而不是Mock
            mock_connect.return_value = mock_conn

            # 初始化连接池
            settings = load_settings(Path("configs"))
            init_database(settings)

            yield mock_conn, mock_cursor

            # 清理
            cleanup_database()

    def test_connection_pool_with_transaction(self, setup_and_teardown):
        """测试连接池与事务管理器的集成"""
        mock_conn, mock_cursor = setup_and_teardown

        # 测试从连接池获取连接并使用事务
        with get_connection() as conn:
            with transaction(conn) as tx_conn:
                with tx_conn.cursor() as cur:
                    cur.execute("SELECT 1")  # 使用简单的SELECT而不是INSERT

        # 验证事务操作
        assert mock_cursor.execute.called
        mock_conn.commit.assert_called()

    def test_connection_pool_with_auto_commit(self, setup_and_teardown):
        """测试连接池与自动提交的集成"""
        mock_conn, mock_cursor = setup_and_teardown

        # 测试从连接池获取连接并使用自动提交
        with get_connection() as conn:
            with auto_commit(conn) as ac_conn:
                with ac_conn.cursor() as cur:
                    cur.execute("SELECT 1")  # 使用简单的SELECT而不是CREATE TABLE

        # 验证自动提交操作
        assert mock_cursor.execute.called
        # 自动提交模式下不应该调用commit
        mock_conn.commit.assert_not_called()

    def test_connection_state_reset_on_return(self, setup_and_teardown):
        """测试连接归还时状态重置"""
        mock_conn, mock_cursor = setup_and_teardown

        # 模拟连接处于事务状态
        mock_conn.info.transaction_status = 2  # INTRANS
        mock_conn.autocommit = False

        # Mock路径应该是pool模块中导入的reset_connection_state
        with patch("app.adapters.db.pool.reset_connection_state") as mock_reset:
            with get_connection() as conn:
                pass  # 简单获取和释放连接

        # 验证连接状态被重置
        mock_reset.assert_called()

    def test_transaction_error_handling(self, setup_and_teardown):
        """测试事务错误处理"""
        mock_conn, mock_cursor = setup_and_teardown

        # 模拟SQL执行错误
        mock_cursor.execute.side_effect = Exception("SQL error")

        with get_connection() as conn:
            with pytest.raises(Exception):
                with transaction(conn) as tx_conn:
                    with tx_conn.cursor() as cur:
                        cur.execute("INVALID SQL")

        # 验证回滚被调用
        mock_conn.rollback.assert_called()

    def test_multiple_transactions_isolation(self, setup_and_teardown):
        """测试多个事务的隔离性"""
        mock_conn, mock_cursor = setup_and_teardown

        # 第一个事务
        with get_connection() as conn1:
            with transaction(conn1) as tx_conn1:
                with tx_conn1.cursor() as cur1:
                    cur1.execute("INSERT INTO table1 VALUES (1)")

        # 第二个事务
        with get_connection() as conn2:
            with transaction(conn2) as tx_conn2:
                with tx_conn2.cursor() as cur2:
                    cur2.execute("INSERT INTO table2 VALUES (2)")

        # 验证两个事务都正确提交
        assert mock_conn.commit.call_count >= 2

    def test_nested_transactions_with_savepoints(self, setup_and_teardown):
        """测试嵌套事务（保存点）"""
        mock_conn, mock_cursor = setup_and_teardown

        with get_connection() as conn:
            with transaction(conn) as tx_conn:
                # 外层事务
                with tx_conn.cursor() as cur:
                    cur.execute("INSERT INTO outer_table VALUES (1)")

                # 内层事务（保存点）
                with transaction(tx_conn, savepoint="inner_sp") as inner_conn:
                    with inner_conn.cursor() as inner_cur:
                        inner_cur.execute("INSERT INTO inner_table VALUES (2)")

        # 验证保存点操作
        mock_cursor.execute.assert_any_call("SAVEPOINT inner_sp")
        mock_cursor.execute.assert_any_call("RELEASE SAVEPOINT inner_sp")

    def test_connection_health_check_integration(self, setup_and_teardown):
        """测试连接健康检查集成"""
        mock_conn, mock_cursor = setup_and_teardown

        # 模拟健康检查
        with patch("app.adapters.db.pool.PooledConnection.check_health") as mock_health:
            mock_health.return_value = True

            with get_connection() as conn:
                # 简单使用连接
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")

        # 验证健康检查被调用
        mock_health.assert_called()

    def test_connection_pool_stats_after_transactions(self, setup_and_teardown):
        """测试事务操作后连接池统计"""
        mock_conn, mock_cursor = setup_and_teardown

        from app.adapters.db import get_pool_stats

        # 执行一些事务操作
        for i in range(3):
            with get_connection() as conn:
                with transaction(conn) as tx_conn:
                    with tx_conn.cursor() as cur:
                        cur.execute(f"INSERT INTO test VALUES ({i})")

        # 获取统计信息
        stats = get_pool_stats()

        # 验证统计信息
        assert "total_requests" in stats
        assert stats["total_requests"] >= 3
