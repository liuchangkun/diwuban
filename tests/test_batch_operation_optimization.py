"""
批量操作优化测试
"""

import pytest
from unittest.mock import Mock, patch, call
import psycopg

from app.adapters.db.gateway import (
    insert_rejects,
    copy_valid_lines,
    _insert_rejects_batch,
    _copy_valid_lines_batch
)


class TestBatchOperationOptimization:
    """测试批量操作优化功能"""

    def test_insert_rejects_small_batch(self):
        """测试小批量拒绝记录插入（不分片）"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        
        # 模拟事务管理器
        with patch('app.adapters.db.gateway.transaction') as mock_transaction:
            mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_transaction.return_value.__exit__ = Mock(return_value=None)
            
            # 测试数据（小批量）
            rejects = [
                Mock(source_hint="test1", error_msg="error1"),
                Mock(source_hint="test2", error_msg="error2"),
                Mock(source_hint="test3", error_msg="error3")
            ]
            
            # 调用函数
            result = insert_rejects(mock_conn, rejects)
            
            # 验证结果
            assert result == 3
            mock_cursor.executemany.assert_called_once()
            
            # 验证SQL参数
            call_args = mock_cursor.executemany.call_args
            assert len(call_args[0][1]) == 3  # 3条记录

    @patch('app.adapters.db.gateway._insert_rejects_batch')
    def test_insert_rejects_large_batch(self, mock_batch_insert):
        """测试大批量拒绝记录插入（自动分片）"""
        # 模拟批次插入函数
        mock_batch_insert.return_value = 500
        
        # 创建Mock连接
        mock_conn = Mock()
        
        # 测试数据（大批量，超过500条）
        rejects = [Mock(source_hint=f"test{i}", error_msg=f"error{i}") for i in range(1200)]
        
        # 调用函数
        result = insert_rejects(mock_conn, rejects)
        
        # 验证结果
        assert result == 1500  # 3个批次 * 500
        
        # 验证分片调用
        assert mock_batch_insert.call_count == 3  # 应该分成3个批次
        
        # 验证每个批次的大小
        call_args_list = mock_batch_insert.call_args_list
        assert len(call_args_list[0][0][1]) == 500  # 第一批次
        assert len(call_args_list[1][0][1]) == 500  # 第二批次
        assert len(call_args_list[2][0][1]) == 200  # 第三批次

    def test_insert_rejects_batch_function(self):
        """测试单个批次插入函数"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        
        # 模拟事务管理器
        with patch('app.adapters.db.gateway.transaction') as mock_transaction:
            mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_transaction.return_value.__exit__ = Mock(return_value=None)
            
            # 测试数据
            reject_batch = [("test1", "error1"), ("test2", "error2")]
            sql = "INSERT INTO public.staging_rejects (source_hint, error_msg) VALUES (%s, %s)"
            
            # 调用函数
            result = _insert_rejects_batch(mock_conn, reject_batch, sql)
            
            # 验证结果
            assert result == 2
            mock_cursor.executemany.assert_called_once_with(sql, reject_batch)

    def test_copy_valid_lines_small_batch(self):
        """测试小批量COPY操作（不分片）"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_copy = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        mock_cursor.copy.return_value.__enter__ = Mock(return_value=mock_copy)
        mock_cursor.copy.return_value.__exit__ = Mock(return_value=None)
        
        # 测试数据（小批量）
        lines = ["line1\n", "line2\n", "line3\n"]
        
        # 调用函数
        result = copy_valid_lines(mock_conn, lines)
        
        # 验证结果
        assert result == 3
        
        # 验证COPY操作
        assert mock_copy.write.call_count == 3
        mock_conn.commit.assert_called_once()

    @patch('app.adapters.db.gateway._copy_valid_lines_batch')
    def test_copy_valid_lines_large_batch(self, mock_batch_copy):
        """测试大批量COPY操作（自动分片）"""
        # 模拟批次COPY函数
        mock_batch_copy.return_value = 2000
        
        # 创建Mock连接
        mock_conn = Mock()
        
        # 测试数据（大批量，超过2000行）
        lines = [f"line{i}\n" for i in range(5000)]
        
        # 调用函数
        result = copy_valid_lines(mock_conn, lines)
        
        # 验证结果
        assert result == 6000  # 3个批次 * 2000
        
        # 验证分片调用
        assert mock_batch_copy.call_count == 3  # 应该分成3个批次
        
        # 验证每个批次的大小
        call_args_list = mock_batch_copy.call_args_list
        assert len(call_args_list[0][0][1]) == 2000  # 第一批次
        assert len(call_args_list[1][0][1]) == 2000  # 第二批次
        assert len(call_args_list[2][0][1]) == 1000  # 第三批次

    def test_copy_valid_lines_batch_function(self):
        """测试单个批次COPY函数"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_copy = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        mock_cursor.copy.return_value.__enter__ = Mock(return_value=mock_copy)
        mock_cursor.copy.return_value.__exit__ = Mock(return_value=None)
        
        # 测试数据
        lines_batch = ["line1\n", "line2\n", "line3\n"]
        copy_sql = 'COPY public.staging_raw (station_name, device_name, metric_key, "TagName", "DataTime", "DataValue", source_hint) FROM STDIN WITH (FORMAT CSV)'
        
        # 调用函数
        result = _copy_valid_lines_batch(mock_conn, lines_batch, copy_sql)
        
        # 验证结果
        assert result == 3
        
        # 验证COPY操作
        mock_cursor.copy.assert_called_once_with(copy_sql)
        assert mock_copy.write.call_count == 3
        mock_conn.commit.assert_called_once()

    def test_insert_rejects_batch_exception_handling(self):
        """测试批次插入异常处理"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        
        # 模拟SQL执行异常
        mock_cursor.executemany.side_effect = Exception("SQL执行失败")
        
        # 模拟事务管理器
        with patch('app.adapters.db.gateway.transaction') as mock_transaction:
            mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_transaction.return_value.__exit__ = Mock(return_value=None)
            
            # 测试数据
            reject_batch = [("test1", "error1")]
            sql = "INSERT INTO public.staging_rejects (source_hint, error_msg) VALUES (%s, %s)"
            
            # 调用函数应该抛出异常
            with pytest.raises(Exception, match="SQL执行失败"):
                _insert_rejects_batch(mock_conn, reject_batch, sql)

    def test_copy_valid_lines_batch_exception_handling(self):
        """测试批次COPY异常处理"""
        # 创建Mock连接
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_copy = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        mock_cursor.copy.return_value.__enter__ = Mock(return_value=mock_copy)
        mock_cursor.copy.return_value.__exit__ = Mock(return_value=None)
        
        # 模拟COPY操作异常
        mock_copy.write.side_effect = Exception("COPY操作失败")
        
        # 测试数据
        lines_batch = ["line1\n"]
        copy_sql = 'COPY public.staging_raw (station_name, device_name, metric_key, "TagName", "DataTime", "DataValue", source_hint) FROM STDIN WITH (FORMAT CSV)'
        
        # 调用函数应该抛出异常
        with pytest.raises(Exception, match="COPY操作失败"):
            _copy_valid_lines_batch(mock_conn, lines_batch, copy_sql)

    # 注意：以下两个测试已删除，因为代码中已移除日志记录功能
    # - test_insert_rejects_logging
    # - test_copy_valid_lines_logging

    def test_batch_size_thresholds(self):
        """测试批次大小阈值"""
        # 创建Mock连接
        mock_conn = Mock()
        
        # 测试insert_rejects阈值（500）
        small_rejects = [Mock(source_hint=f"test{i}", error_msg=f"error{i}") for i in range(500)]
        large_rejects = [Mock(source_hint=f"test{i}", error_msg=f"error{i}") for i in range(501)]
        
        with patch('app.adapters.db.gateway._insert_rejects_batch') as mock_batch_insert:
            mock_batch_insert.return_value = len(small_rejects)
            
            # 小批量应该直接处理
            insert_rejects(mock_conn, small_rejects)
            assert mock_batch_insert.call_count == 1
            
            mock_batch_insert.reset_mock()
            mock_batch_insert.return_value = 500
            
            # 大批量应该分片处理
            insert_rejects(mock_conn, large_rejects)
            assert mock_batch_insert.call_count == 2  # 分成2个批次
        
        # 测试copy_valid_lines阈值（2000）
        small_lines = [f"line{i}\n" for i in range(2000)]
        large_lines = [f"line{i}\n" for i in range(2001)]
        
        with patch('app.adapters.db.gateway._copy_valid_lines_batch') as mock_batch_copy:
            mock_batch_copy.return_value = len(small_lines)
            
            # 小批量应该直接处理
            copy_valid_lines(mock_conn, small_lines)
            assert mock_batch_copy.call_count == 1
            
            mock_batch_copy.reset_mock()
            mock_batch_copy.return_value = 2000
            
            # 大批量应该分片处理
            copy_valid_lines(mock_conn, large_lines)
            assert mock_batch_copy.call_count == 2  # 分成2个批次
