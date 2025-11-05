"""
测试特性曲线管理器 (CharacteristicCurveManager)

测试场景:
1. 正常流程测试 (3个场景)
2. 边界条件测试 (3个场景)
3. 异常情况测试 (2个场景)
4. 性能测试 (2个场景)

总计: 10个测试场景
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from app.services.calculation.characteristic_curve import CharacteristicCurveManager


class TestCharacteristicCurveManager:
    """特性曲线管理器测试类"""

    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return CharacteristicCurveManager(cache_ttl=3600)

    @pytest.fixture
    def sample_curve_data(self):
        """示例曲线数据"""
        # Q-H曲线：流量-扬程
        return [
            (0.0, 50.0),
            (50.0, 48.0),
            (100.0, 45.0),
            (150.0, 40.0),
            (200.0, 32.0),
            (250.0, 20.0)
        ]

    # =====================================================
    # 正常流程测试 (3个场景)
    # =====================================================

    def test_load_curves_from_database(self, manager):
        """场景1: 从数据库加载曲线"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1450.0, 50.0)  # speed, frequency
        mock_cursor.fetchall.return_value = [
            (0.0, 50.0),
            (100.0, 45.0),
            (200.0, 32.0)
        ]
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('app.services.calculation.characteristic_curve.get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_conn
            
            curves = manager.load_curves(
                device_id=1,
                curve_type='Q-H',
                use_cache=False
            )
        
        # 验证加载成功
        assert len(curves) == 3
        assert curves[0] == (0.0, 50.0)
        assert curves[1] == (100.0, 45.0)
        assert curves[2] == (200.0, 32.0)

    def test_interpolate_linear(self, manager, sample_curve_data):
        """场景2: 线性插值计算"""
        # 在已知点之间插值
        result = manager.interpolate(
            curve_type='Q-H',
            flow_rate=75.0,  # 在50和100之间
            curves_data=sample_curve_data,
            method='linear'
        )
        
        # 验证插值结果（应该在48和45之间）
        assert 45.0 <= result <= 48.0
        # 线性插值：75在50-100的中点，所以结果应该接近(48+45)/2=46.5
        assert abs(result - 46.5) < 0.1

    def test_validate_point_within_tolerance(self, manager, sample_curve_data):
        """场景3: 验证数据点在容忍范围内"""
        # 验证一个接近曲线的点
        is_valid, deviation = manager.validate_point(
            curve_type='Q-H',
            flow_rate=100.0,
            actual_value=44.0,  # 期望值45.0，偏差约2.2%
            curves_data=sample_curve_data,
            tolerance=0.1  # 10%容忍度
        )
        
        # 验证通过
        assert is_valid is True
        assert deviation < 0.1

    # =====================================================
    # 边界条件测试 (3个场景)
    # =====================================================

    def test_interpolate_boundary_extrapolation(self, manager, sample_curve_data):
        """场景4: 边界外插值（使用边界值）"""
        # 流量超出范围（小于最小值）
        result_low = manager.interpolate(
            curve_type='Q-H',
            flow_rate=-10.0,  # 小于0
            curves_data=sample_curve_data,
            method='linear'
        )
        
        # 应该返回最小流量对应的值
        assert result_low == 50.0
        
        # 流量超出范围（大于最大值）
        result_high = manager.interpolate(
            curve_type='Q-H',
            flow_rate=300.0,  # 大于250
            curves_data=sample_curve_data,
            method='linear'
        )
        
        # 应该返回最大流量对应的值
        assert result_high == 20.0

    def test_interpolate_single_point_curve(self, manager):
        """场景5: 单点曲线"""
        single_point_curve = [(100.0, 45.0)]
        
        # 单点曲线无法插值，应该返回该点的值
        result = manager.interpolate(
            curve_type='Q-H',
            flow_rate=100.0,
            curves_data=single_point_curve,
            method='linear'
        )
        
        assert result == 45.0

    def test_empty_curve_data(self, manager):
        """场景6: 空曲线数据"""
        empty_curve = []
        
        # 空曲线应该抛出异常
        with pytest.raises(ValueError) as exc_info:
            manager.interpolate(
                curve_type='Q-H',
                flow_rate=100.0,
                curves_data=empty_curve,
                method='linear'
            )
        
        assert "曲线数据为空" in str(exc_info.value)

    # =====================================================
    # 异常情况测试 (2个场景)
    # =====================================================

    def test_invalid_curve_type(self, manager):
        """场景7: 无效的曲线类型"""
        # Mock数据库连接
        with patch('app.services.calculation.characteristic_curve.get_connection'):
            with pytest.raises(ValueError) as exc_info:
                manager.load_curves(
                    device_id=1,
                    curve_type='INVALID_TYPE',
                    use_cache=False
                )
        
        assert "无效的曲线类型" in str(exc_info.value)

    def test_database_connection_error(self, manager):
        """场景8: 数据库连接错误"""
        # Mock数据库连接失败
        with patch('app.services.calculation.characteristic_curve.get_connection') as mock_conn:
            from app.core.exceptions import DatabaseError
            mock_conn.side_effect = DatabaseError("连接失败")
            
            with pytest.raises(DatabaseError):
                manager.load_curves(
                    device_id=1,
                    curve_type='Q-H',
                    use_cache=False
                )

    # =====================================================
    # 性能测试 (2个场景)
    # =====================================================

    def test_interpolation_performance(self, manager, sample_curve_data):
        """场景9: 插值性能测试"""
        import time
        
        # 大量插值计算
        flow_rates = np.linspace(0, 250, 1000)
        
        start_time = time.time()
        
        for flow_rate in flow_rates:
            manager.interpolate(
                curve_type='Q-H',
                flow_rate=float(flow_rate),
                curves_data=sample_curve_data,
                method='linear'
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 验证性能（1000次插值应该在1秒内完成）
        assert duration < 1.0

    def test_cache_effectiveness(self, manager):
        """场景10: 缓存效果测试"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1450.0, 50.0)
        mock_cursor.fetchall.return_value = [
            (0.0, 50.0),
            (100.0, 45.0),
            (200.0, 32.0)
        ]
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('app.services.calculation.characteristic_curve.get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_conn
            
            # 第一次加载（从数据库）
            curves1 = manager.load_curves(
                device_id=1,
                curve_type='Q-H',
                use_cache=True
            )
            
            # 第二次加载（从缓存）
            curves2 = manager.load_curves(
                device_id=1,
                curve_type='Q-H',
                use_cache=True
            )
        
        # 验证两次加载结果相同
        assert curves1 == curves2
        
        # 验证数据库只被调用一次
        assert mock_get_conn.call_count == 1
        
        # 验证缓存统计
        stats = manager.get_cache_stats()
        assert stats['cache_size'] == 1
        
        # 清空缓存
        manager.clear_cache()
        stats_after_clear = manager.get_cache_stats()
        assert stats_after_clear['cache_size'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

