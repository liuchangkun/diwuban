"""
P2Pipeline修正模型集成测试

测试范围：
- 修正模型训练数据提取
- 理论扬程计算
- 合成曲线评估指标计算
- 5种泵组场景的修正模型集成
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List, Tuple

from app.services.characteristic_curves.pump_group.p2_pipeline import P2Pipeline
from app.services.characteristic_curves.pump_group.system_correction_model import (
    CorrectionModelConfig,
    SystemCorrectionModel,
)
from app.services.characteristic_curves.models import GroupProcessingStrategy


class TestP2PipelineCorrectionModel:
    """P2Pipeline修正模型集成测试"""

    @pytest.fixture
    def mock_db_connection(self):
        """模拟数据库连接"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        return mock_conn, mock_cursor

    @pytest.fixture
    def sample_training_data(self) -> List[Tuple[int, float, float]]:
        """生成样本训练数据"""
        # 生成100个数据点：(N, Q_total, H_actual)
        np.random.seed(42)
        data = []
        for _ in range(100):
            N = np.random.randint(1, 4)  # 1-3台泵
            Q_total = np.random.uniform(50, 300)  # 50-300 m³/h
            H_actual = 50 - 0.001 * Q_total**2 + np.random.normal(0, 1)  # 模拟实际扬程
            data.append((N, Q_total, max(0, H_actual)))
        return data

    @pytest.fixture
    def sample_pump_curves(self) -> Dict[int, Dict]:
        """生成样本单泵曲线"""
        def forward(Q):
            return 50 - 0.001 * Q**2

        def inverse(H):
            return np.sqrt((50 - H) / 0.001)

        return {
            1: {"forward": forward, "inverse": inverse},
            2: {"forward": forward, "inverse": inverse},
            3: {"forward": forward, "inverse": inverse},
        }

    @patch("app.adapters.db.get_connection")
    def test_extract_training_data_success(self, mock_get_connection, sample_training_data):
        """测试成功提取训练数据"""
        # 设置mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = sample_training_data
        mock_get_connection.return_value.__enter__.return_value = mock_conn

        pipeline = P2Pipeline()

        result = pipeline._extract_training_data(
            station_id=1,
            pump_ids=[1, 2, 3],
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
        )

        assert len(result) == 100
        assert all(isinstance(r, tuple) and len(r) == 3 for r in result)

    def test_extract_training_data_insufficient(self, mock_db_connection):
        """测试训练数据不足"""
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchall.return_value = [(1, 100.0, 45.0)] * 30  # 只有30个数据点

        pipeline = P2Pipeline()

        with patch("app.adapters.db.get_connection", return_value=mock_conn):
            with pytest.raises(Exception) as exc_info:
                pipeline._extract_training_data(
                    station_id=1,
                    pump_ids=[1, 2, 3],
                    start_time=datetime(2024, 1, 1),
                    end_time=datetime(2024, 1, 31),
                )
            assert "训练数据不足" in str(exc_info.value)

    def test_calculate_theoretical_head(self, sample_pump_curves):
        """测试理论扬程计算"""
        pipeline = P2Pipeline()

        # 测试3台泵，总流量300 m³/h
        H_theo = pipeline._calculate_theoretical_head(
            N=3, Q_total=300, pump_curves=sample_pump_curves
        )

        # 单泵流量 = 300/3 = 100 m³/h
        # 理论扬程 = 50 - 0.001 * 100^2 = 40 m
        assert abs(H_theo - 40.0) < 0.1

    def test_calculate_theoretical_head_zero_flow(self, sample_pump_curves):
        """测试零流量情况"""
        pipeline = P2Pipeline()

        H_theo = pipeline._calculate_theoretical_head(
            N=3, Q_total=0, pump_curves=sample_pump_curves
        )

        assert H_theo == 0.0

    def test_calculate_synthesis_metrics(self, sample_training_data, sample_pump_curves):
        """测试合成曲线评估指标计算"""
        pipeline = P2Pipeline()

        # 创建一个简单的正向函数
        def forward_func(Q):
            return 50 - 0.001 * Q**2

        metrics = pipeline._calculate_synthesis_metrics(
            training_data=sample_training_data,
            pump_curves=sample_pump_curves,
            forward_func=forward_func,
        )

        assert "r_squared" in metrics
        assert "rmse" in metrics
        assert "mae" in metrics
        assert 0 <= metrics["r_squared"] <= 1
        assert metrics["rmse"] >= 0
        assert metrics["mae"] >= 0

    @patch("app.adapters.db.get_connection")
    def test_synthesize_homogeneous_with_correction(
        self, mock_get_connection, sample_training_data, sample_pump_curves
    ):
        """测试同构泵组合成（带修正模型）"""
        # 模拟数据库连接
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = sample_training_data
        mock_get_connection.return_value = mock_conn

        pipeline = P2Pipeline(correction_config=CorrectionModelConfig(model_type="polynomial"))

        result = pipeline._synthesize_homogeneous(
            station_id=1,
            pump_ids=[1, 2, 3],
            pump_curves=sample_pump_curves,
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
        )

        assert result is not None
        assert "forward_func" in result
        assert "inverse_func" in result
        assert "r_squared" in result
        assert "rmse" in result
        assert callable(result["forward_func"])
        assert callable(result["inverse_func"])

    def test_synthesize_homogeneous_without_time_range(self, sample_pump_curves):
        """测试同构泵组合成（无时间范围，使用理论合成）"""
        pipeline = P2Pipeline()

        result = pipeline._synthesize_homogeneous(
            station_id=1,
            pump_ids=[1, 2, 3],
            pump_curves=sample_pump_curves,
            start_time=None,
            end_time=None,
        )

        assert result is not None
        assert "forward_func" in result
        assert "inverse_func" in result
        assert result["correction_model"] is None
        assert result["r_squared"] == 0.90

    @patch("app.adapters.db.get_connection")
    def test_synthesize_heterogeneous_with_correction(
        self, mock_get_connection, sample_training_data, sample_pump_curves
    ):
        """测试异构泵组合成（带修正模型）"""
        # 模拟数据库连接
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = sample_training_data
        mock_get_connection.return_value = mock_conn

        pipeline = P2Pipeline(correction_config=CorrectionModelConfig(model_type="polynomial"))

        result = pipeline._synthesize_heterogeneous(
            station_id=1,
            pump_ids=[1, 2, 3],
            pump_curves=sample_pump_curves,
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
        )

        assert result is not None
        assert "forward_func" in result
        assert "inverse_func" in result
        assert "r_squared" in result
        assert "rmse" in result

    @patch("app.adapters.db.get_connection")
    def test_synthesize_vfd_freq_with_correction(
        self, mock_get_connection, sample_training_data, sample_pump_curves
    ):
        """测试VFD频率异构合成（带修正模型）"""
        # 模拟数据库连接
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = sample_training_data
        mock_get_connection.return_value = mock_conn

        pipeline = P2Pipeline(correction_config=CorrectionModelConfig(model_type="polynomial"))

        result = pipeline._synthesize_vfd_freq(
            station_id=1,
            pump_ids=[1, 2, 3],
            pump_curves=sample_pump_curves,
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
        )

        assert result is not None
        assert "forward_func" in result
        assert "inverse_func" in result

    @patch("app.adapters.db.get_connection")
    def test_synthesize_mixed_with_correction(
        self, mock_get_connection, sample_training_data, sample_pump_curves
    ):
        """测试混合泵组合成（带修正模型）"""
        # 模拟数据库连接
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = sample_training_data
        mock_get_connection.return_value = mock_conn

        pipeline = P2Pipeline(correction_config=CorrectionModelConfig(model_type="polynomial"))

        result = pipeline._synthesize_mixed(
            station_id=1,
            pump_ids=[1, 2, 3],
            pump_curves=sample_pump_curves,
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
        )

        assert result is not None
        assert "forward_func" in result
        assert "inverse_func" in result

