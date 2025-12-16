"""
单元测试：app/services/ingest/create_staging.py

测试create_staging函数的各种场景：
- 正常流程
- 错误处理
- 日志记录
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
import time

from app.services.ingest.create_staging import create_staging
from app.core.config.loader_new import Settings


class TestCreateStagingNormalFlow:
    """正常流程测试"""

    @patch('app.services.ingest.create_staging.get_conn')
    @patch('app.services.ingest.create_staging.create_staging_if_not_exists')
    def test_create_staging_success(self, mock_create_staging_fn, mock_get_conn):
        """场景1: 成功创建staging表"""
        # Mock数据库连接
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        # Mock Settings
        settings = Mock(spec=Settings)
        
        # 执行
        create_staging(settings)
        
        # 验证
        mock_get_conn.assert_called_once_with(settings)
        mock_create_staging_fn.assert_called_once_with(mock_conn)

    @patch('app.services.ingest.create_staging.get_conn')
    @patch('app.services.ingest.create_staging.create_staging_if_not_exists')
    @patch('app.services.ingest.create_staging._act')
    def test_create_staging_logs_start(self, mock_logger, mock_create_staging_fn, mock_get_conn):
        """场景2: 记录开始日志"""
        # Mock数据库连接
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        # Mock Settings
        settings = Mock(spec=Settings)
        
        # 执行
        create_staging(settings)
        
        # 验证开始日志
        assert any(
            call_args[0][0] == "[流程-开始] [创建staging表]"
            for call_args in mock_logger.info.call_args_list
        )

    @patch('app.services.ingest.create_staging.get_conn')
    @patch('app.services.ingest.create_staging.create_staging_if_not_exists')
    @patch('app.services.ingest.create_staging._act')
    def test_create_staging_logs_completion(self, mock_logger, mock_create_staging_fn, mock_get_conn):
        """场景3: 记录完成日志"""
        # Mock数据库连接
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        # Mock Settings
        settings = Mock(spec=Settings)
        
        # 执行
        create_staging(settings)
        
        # 验证完成日志
        completion_calls = [
            call_args for call_args in mock_logger.info.call_args_list
            if call_args[0][0] == "[流程-完成] [创建staging表]"
        ]
        assert len(completion_calls) == 1
        
        # 验证extra_data包含duration_ms和tables
        extra_data = completion_calls[0][1]['extra']['extra_data']
        assert 'duration_ms' in extra_data
        assert extra_data['tables'] == ["staging_raw", "staging_rejects"]

    @patch('app.services.ingest.create_staging.get_conn')
    @patch('app.services.ingest.create_staging.create_staging_if_not_exists')
    @patch('app.services.ingest.create_staging.time')
    def test_create_staging_measures_duration(self, mock_time, mock_create_staging_fn, mock_get_conn):
        """场景4: 测量执行时间"""
        # Mock数据库连接
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        # Mock时间（模拟100ms执行时间）
        mock_time.perf_counter.side_effect = [0.0, 0.1]
        
        # Mock Settings
        settings = Mock(spec=Settings)
        
        # 执行
        create_staging(settings)
        
        # 验证perf_counter被调用两次
        assert mock_time.perf_counter.call_count == 2


class TestCreateStagingErrorHandling:
    """错误处理测试"""

    @patch('app.services.ingest.create_staging.get_conn')
    @patch('app.services.ingest.create_staging.create_staging_if_not_exists')
    def test_create_staging_database_error(self, mock_create_staging_fn, mock_get_conn):
        """场景5: 数据库连接错误"""
        # Mock数据库连接失败
        mock_get_conn.side_effect = Exception("Database connection failed")
        
        # Mock Settings
        settings = Mock(spec=Settings)
        
        # 验证抛出异常
        with pytest.raises(Exception) as exc_info:
            create_staging(settings)
        
        assert "Database connection failed" in str(exc_info.value)

    @patch('app.services.ingest.create_staging.get_conn')
    @patch('app.services.ingest.create_staging.create_staging_if_not_exists')
    @patch('app.services.ingest.create_staging._act')
    def test_create_staging_logs_error(self, mock_logger, mock_create_staging_fn, mock_get_conn):
        """场景6: 记录错误日志"""
        # Mock数据库操作失败
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_create_staging_fn.side_effect = Exception("Table creation failed")
        
        # Mock Settings
        settings = Mock(spec=Settings)
        
        # 执行并捕获异常
        with pytest.raises(Exception):
            create_staging(settings)
        
        # 验证错误日志
        error_calls = [
            call_args for call_args in mock_logger.error.call_args_list
            if call_args[0][0] == "[流程-错误] [创建staging表失败]"
        ]
        assert len(error_calls) == 1
        
        # 验证extra_data包含error和error_type
        extra_data = error_calls[0][1]['extra']['extra_data']
        assert 'error' in extra_data
        assert 'error_type' in extra_data
        assert extra_data['error_type'] == 'Exception'

    @patch('app.services.ingest.create_staging.get_conn')
    @patch('app.services.ingest.create_staging.create_staging_if_not_exists')
    def test_create_staging_reraises_exception(self, mock_create_staging_fn, mock_get_conn):
        """场景7: 重新抛出异常"""
        # Mock数据库操作失败
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        original_error = ValueError("Invalid table name")
        mock_create_staging_fn.side_effect = original_error
        
        # Mock Settings
        settings = Mock(spec=Settings)
        
        # 验证异常被重新抛出
        with pytest.raises(ValueError) as exc_info:
            create_staging(settings)
        
        assert exc_info.value is original_error


class TestCreateStagingIdempotency:
    """幂等性测试"""

    @patch('app.services.ingest.create_staging.get_conn')
    @patch('app.services.ingest.create_staging.create_staging_if_not_exists')
    def test_create_staging_idempotent(self, mock_create_staging_fn, mock_get_conn):
        """场景8: 多次调用幂等"""
        # Mock数据库连接
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        # Mock Settings
        settings = Mock(spec=Settings)
        
        # 执行多次
        create_staging(settings)
        create_staging(settings)
        create_staging(settings)
        
        # 验证每次都调用create_staging_if_not_exists
        assert mock_create_staging_fn.call_count == 3

    @patch('app.services.ingest.create_staging.get_conn')
    @patch('app.services.ingest.create_staging.create_staging_if_not_exists')
    def test_create_staging_uses_context_manager(self, mock_create_staging_fn, mock_get_conn):
        """场景9: 使用上下文管理器"""
        # Mock数据库连接
        mock_conn = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_conn
        mock_context.__exit__.return_value = None
        mock_get_conn.return_value = mock_context
        
        # Mock Settings
        settings = Mock(spec=Settings)
        
        # 执行
        create_staging(settings)
        
        # 验证上下文管理器被正确使用
        mock_context.__enter__.assert_called_once()
        mock_context.__exit__.assert_called_once()


class TestCreateStagingIntegration:
    """集成测试（Mock最小化）"""

    @patch('app.services.ingest.create_staging.get_conn')
    @patch('app.services.ingest.create_staging.create_staging_if_not_exists')
    @patch('app.services.ingest.create_staging._act')
    def test_create_staging_full_flow(self, mock_logger, mock_create_staging_fn, mock_get_conn):
        """场景10: 完整流程测试"""
        # Mock数据库连接
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        # Mock Settings
        settings = Mock(spec=Settings)
        
        # 执行
        create_staging(settings)
        
        # 验证完整流程
        # 1. 记录开始日志
        start_calls = [c for c in mock_logger.info.call_args_list if c[0][0] == "[流程-开始] [创建staging表]"]
        assert len(start_calls) == 1
        
        # 2. 获取数据库连接
        mock_get_conn.assert_called_once_with(settings)
        
        # 3. 创建staging表
        mock_create_staging_fn.assert_called_once_with(mock_conn)
        
        # 4. 记录完成日志
        completion_calls = [c for c in mock_logger.info.call_args_list if c[0][0] == "[流程-完成] [创建staging表]"]
        assert len(completion_calls) == 1

