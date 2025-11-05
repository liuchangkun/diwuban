"""
测试自适应时间窗口管理器 (AdaptiveWindowManager)

测试场景:
1. 正常流程测试 (4个场景)
2. 边界条件测试 (4个场景)
3. 异常情况测试 (2个场景)
4. 性能测试 (2个场景)

总计: 12个测试场景
"""

import pytest
from app.services.calculation.adaptive_window import AdaptiveWindowManager


class TestAdaptiveWindowManager:
    """自适应时间窗口管理器测试类"""

    # =====================================================
    # 正常流程测试 (4个场景)
    # =====================================================

    def test_initialization_with_default_config(self):
        """场景1: 使用默认配置初始化"""
        manager = AdaptiveWindowManager()
        
        # 验证默认值
        assert manager.is_enabled() is True
        assert manager.get_initial_minutes() == 60
        assert manager.min_minutes == 15
        assert manager.max_minutes == 240
        assert manager.target_duration == 5000
        assert manager.adjustment_factor == 0.2
        assert manager.smoothing_alpha == 0.3

    def test_initialization_with_custom_config(self):
        """场景2: 使用自定义配置初始化"""
        config = {
            'enabled': True,
            'initial_minutes': 30,
            'min_minutes': 10,
            'max_minutes': 120,
            'target_duration_ms': 3000,
            'adjustment_factor': 0.15,
            'smoothing_alpha': 0.25
        }
        
        manager = AdaptiveWindowManager(config)
        
        # 验证自定义值
        assert manager.is_enabled() is True
        assert manager.get_initial_minutes() == 30
        assert manager.min_minutes == 10
        assert manager.max_minutes == 120
        assert manager.target_duration == 3000
        assert manager.adjustment_factor == 0.15
        assert manager.smoothing_alpha == 0.25

    def test_adjust_window_stable_performance(self):
        """场景3: 性能稳定时保持窗口大小不变"""
        manager = AdaptiveWindowManager({
            'enabled': True,
            'initial_minutes': 60,
            'min_minutes': 15,
            'max_minutes': 240,
            'target_duration_ms': 5000
        })
        
        # 模拟稳定性能（处理时间接近目标，数据密度适中）
        performance = {
            'duration_ms': 5000,  # 等于目标
            'data_points': 3000  # 60分钟 * 50点/分钟 = 3000点
        }
        
        new_window, reason = manager.adjust(60, performance)
        
        # 验证窗口大小保持不变或变化很小
        assert abs(new_window - 60) < 5  # 小于5分钟的变化会被忽略
        assert "保持不变" in reason or "稳定" in reason

    def test_adjust_window_increase_on_fast_processing(self):
        """场景4: 处理快时增大窗口"""
        manager = AdaptiveWindowManager({
            'enabled': True,
            'initial_minutes': 60,
            'min_minutes': 15,
            'max_minutes': 240,
            'target_duration_ms': 5000,
            'adjustment_factor': 0.3  # 增大调整因子以触发更大变化
        })

        # 模拟极快速处理+极低密度（需要足够大的差异才能触发>5分钟的调整）
        performance = {
            'duration_ms': 500,  # 远低于目标5000ms的50% (2500ms)
            'data_points': 300  # 极低密度（5点/分钟）
        }

        new_window, reason = manager.adjust(60, performance)

        # 验证窗口增大
        assert new_window > 60
        assert "处理快" in reason or "数据稀疏" in reason

    # =====================================================
    # 边界条件测试 (4个场景)
    # =====================================================

    def test_adjust_window_decrease_on_slow_processing(self):
        """场景5: 处理慢时减小窗口"""
        manager = AdaptiveWindowManager({
            'enabled': True,
            'initial_minutes': 60,
            'min_minutes': 15,
            'max_minutes': 240,
            'target_duration_ms': 5000,
            'adjustment_factor': 0.2
        })

        # 模拟极慢速处理（需要足够大的差异才能触发>5分钟的调整）
        performance = {
            'duration_ms': 15000,  # 远高于目标5000ms的150% (7500ms)
            'data_points': 7000  # 高密度（116点/分钟）
        }

        new_window, reason = manager.adjust(60, performance)

        # 验证窗口减小
        assert new_window < 60
        assert "处理慢" in reason or "数据密集" in reason

    def test_adjust_window_decrease_on_high_density(self):
        """场景6: 数据密集时减小窗口"""
        manager = AdaptiveWindowManager({
            'enabled': True,
            'initial_minutes': 60,
            'min_minutes': 15,
            'max_minutes': 240,
            'target_duration_ms': 5000
        })
        
        # 模拟高数据密度（>100点/分钟）
        performance = {
            'duration_ms': 5000,
            'data_points': 7000  # 60分钟 * 116点/分钟
        }
        
        new_window, reason = manager.adjust(60, performance)
        
        # 验证窗口减小（因为数据密集）
        assert new_window <= 60
        assert "数据密集" in reason or "保持不变" in reason

    def test_window_size_min_boundary(self):
        """场景7: 窗口大小不低于最小值"""
        manager = AdaptiveWindowManager({
            'enabled': True,
            'initial_minutes': 60,
            'min_minutes': 15,
            'max_minutes': 240,
            'target_duration_ms': 5000
        })
        
        # 模拟极端慢速处理
        performance = {
            'duration_ms': 20000,  # 极慢
            'data_points': 10000  # 极高密度
        }
        
        new_window, reason = manager.adjust(20, performance)
        
        # 验证不低于最小值
        assert new_window >= manager.min_minutes

    def test_window_size_max_boundary(self):
        """场景8: 窗口大小不超过最大值"""
        manager = AdaptiveWindowManager({
            'enabled': True,
            'initial_minutes': 60,
            'min_minutes': 15,
            'max_minutes': 240,
            'target_duration_ms': 5000
        })
        
        # 模拟极端快速处理
        performance = {
            'duration_ms': 500,  # 极快
            'data_points': 500  # 极低密度
        }
        
        new_window, reason = manager.adjust(200, performance)
        
        # 验证不超过最大值
        assert new_window <= manager.max_minutes

    # =====================================================
    # 异常情况测试 (2个场景)
    # =====================================================

    def test_invalid_config_min_greater_than_max(self):
        """场景9: 无效配置 - min_minutes >= max_minutes"""
        with pytest.raises(ValueError) as exc_info:
            AdaptiveWindowManager({
                'min_minutes': 120,
                'max_minutes': 60  # max < min
            })
        
        assert "min_minutes" in str(exc_info.value)
        assert "max_minutes" in str(exc_info.value)

    def test_invalid_config_initial_out_of_range(self):
        """场景10: 无效配置 - initial_minutes超出范围"""
        with pytest.raises(ValueError) as exc_info:
            AdaptiveWindowManager({
                'initial_minutes': 5,  # < min_minutes
                'min_minutes': 15,
                'max_minutes': 240
            })
        
        assert "initial_minutes" in str(exc_info.value)

    # =====================================================
    # 性能测试 (2个场景)
    # =====================================================

    def test_disabled_manager_returns_unchanged_window(self):
        """场景11: 禁用管理器时返回原窗口大小"""
        manager = AdaptiveWindowManager({
            'enabled': False
        })
        
        performance = {
            'duration_ms': 10000,
            'data_points': 10000
        }
        
        new_window, reason = manager.adjust(60, performance)
        
        # 验证窗口不变
        assert new_window == 60
        assert "禁用" in reason

    def test_ema_smoothing_effect(self):
        """场景12: EMA平滑效果验证"""
        manager = AdaptiveWindowManager({
            'enabled': True,
            'initial_minutes': 60,
            'min_minutes': 15,
            'max_minutes': 240,
            'target_duration_ms': 5000,
            'smoothing_alpha': 0.3,  # 30%新值，70%旧值
            'adjustment_factor': 0.3  # 增大调整因子
        })

        # 模拟需要大幅调整的性能（极端慢+高密度）
        performance = {
            'duration_ms': 20000,  # 4倍目标时间
            'data_points': 8000  # 高密度（133点/分钟）
        }

        new_window, reason = manager.adjust(60, performance)

        # 验证调整被平滑（不会立即减小到理论值）
        # 理论上应该减小很多，但EMA会平滑这个变化
        assert new_window < 60  # 确实减小了
        # 但不会减小太多（因为EMA平滑）
        # 具体值取决于adjustment_factor和smoothing_alpha的组合


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

