"""
测试自适应批处理管理器 (AdaptiveBatchManager)

测试场景:
1. 正常流程测试 (4个场景)
2. 边界条件测试 (4个场景)
3. 异常情况测试 (2个场景)
4. 性能测试 (2个场景)

总计: 12个测试场景
"""

import pytest
from app.services.calculation.adaptive_batch import AdaptiveBatchManager


class TestAdaptiveBatchManager:
    """自适应批处理管理器测试类"""

    # =====================================================
    # 正常流程测试 (4个场景)
    # =====================================================

    def test_initialization_with_default_config(self):
        """场景1: 使用默认配置初始化"""
        manager = AdaptiveBatchManager()
        
        # 验证默认值
        assert manager.is_enabled() is True
        assert manager.get_initial_size() == 10000
        assert manager.min_size == 1000
        assert manager.max_size == 50000
        assert manager.memory_limit == 1000
        assert manager.target_throughput == 10000

    def test_initialization_with_custom_config(self):
        """场景2: 使用自定义配置初始化"""
        config = {
            'enabled': True,
            'initial_size': 5000,
            'min_size': 500,
            'max_size': 20000,
            'memory_limit_mb': 500,
            'target_throughput': 5000
        }
        
        manager = AdaptiveBatchManager(config)
        
        # 验证自定义值
        assert manager.is_enabled() is True
        assert manager.get_initial_size() == 5000
        assert manager.min_size == 500
        assert manager.max_size == 20000
        assert manager.memory_limit == 500
        assert manager.target_throughput == 5000

    def test_adjust_batch_size_stable_performance(self):
        """场景3: 性能稳定时保持批量大小不变"""
        manager = AdaptiveBatchManager({
            'enabled': True,
            'initial_size': 10000,
            'min_size': 1000,
            'max_size': 50000,
            'memory_limit_mb': 1000,
            'target_throughput': 10000
        })
        
        # 模拟稳定性能
        performance = {
            'memory_mb': 500,  # 50% 内存使用
            'throughput': 10000,  # 达到目标吞吐量
            'duration_ms': 5000
        }
        
        new_batch, reason = manager.adjust(10000, performance)
        
        # 验证批量大小保持不变
        assert new_batch == 10000
        assert "稳定" in reason or "保持不变" in reason

    def test_adjust_batch_size_increase_on_good_performance(self):
        """场景4: 性能良好时增大批量"""
        manager = AdaptiveBatchManager({
            'enabled': True,
            'initial_size': 10000,
            'min_size': 1000,
            'max_size': 50000,
            'memory_limit_mb': 1000,
            'target_throughput': 10000
        })
        
        # 模拟高吞吐量和低内存
        performance = {
            'memory_mb': 400,  # 40% 内存使用
            'throughput': 20000,  # 高吞吐量 (2x目标)
            'duration_ms': 2000
        }
        
        new_batch, reason = manager.adjust(10000, performance)
        
        # 验证批量增大
        assert new_batch > 10000
        assert "吞吐量高" in reason or "内存充足" in reason

    # =====================================================
    # 边界条件测试 (4个场景)
    # =====================================================

    def test_adjust_batch_size_decrease_on_memory_pressure(self):
        """场景5: 内存压力高时减小批量"""
        manager = AdaptiveBatchManager({
            'enabled': True,
            'initial_size': 10000,
            'min_size': 1000,
            'max_size': 50000,
            'memory_limit_mb': 1000,
            'target_throughput': 10000
        })
        
        # 模拟高内存使用
        performance = {
            'memory_mb': 900,  # 90% 内存使用
            'throughput': 10000,
            'duration_ms': 5000
        }
        
        new_batch, reason = manager.adjust(10000, performance)
        
        # 验证批量减小
        assert new_batch < 10000
        assert "内存压力" in reason

    def test_adjust_batch_size_decrease_on_low_throughput(self):
        """场景6: 吞吐量低时减小批量"""
        manager = AdaptiveBatchManager({
            'enabled': True,
            'initial_size': 10000,
            'min_size': 1000,
            'max_size': 50000,
            'memory_limit_mb': 1000,
            'target_throughput': 10000
        })
        
        # 模拟低吞吐量
        performance = {
            'memory_mb': 500,
            'throughput': 3000,  # 30% 目标吞吐量
            'duration_ms': 10000
        }
        
        new_batch, reason = manager.adjust(10000, performance)
        
        # 验证批量减小
        assert new_batch < 10000
        assert "吞吐量低" in reason

    def test_batch_size_min_boundary(self):
        """场景7: 批量大小不低于最小值"""
        manager = AdaptiveBatchManager({
            'enabled': True,
            'initial_size': 10000,
            'min_size': 1000,
            'max_size': 50000,
            'memory_limit_mb': 1000,
            'target_throughput': 10000
        })
        
        # 模拟极端低性能
        performance = {
            'memory_mb': 950,  # 极高内存
            'throughput': 100,  # 极低吞吐量
            'duration_ms': 20000
        }
        
        new_batch, reason = manager.adjust(1500, performance)
        
        # 验证不低于最小值
        assert new_batch >= manager.min_size

    def test_batch_size_max_boundary(self):
        """场景8: 批量大小不超过最大值"""
        manager = AdaptiveBatchManager({
            'enabled': True,
            'initial_size': 10000,
            'min_size': 1000,
            'max_size': 50000,
            'memory_limit_mb': 1000,
            'target_throughput': 10000
        })
        
        # 模拟极端高性能
        performance = {
            'memory_mb': 200,  # 极低内存
            'throughput': 50000,  # 极高吞吐量
            'duration_ms': 1000
        }
        
        new_batch, reason = manager.adjust(40000, performance)
        
        # 验证不超过最大值
        assert new_batch <= manager.max_size

    # =====================================================
    # 异常情况测试 (2个场景)
    # =====================================================

    def test_invalid_config_min_greater_than_max(self):
        """场景9: 无效配置 - min_size >= max_size"""
        with pytest.raises(ValueError) as exc_info:
            AdaptiveBatchManager({
                'min_size': 10000,
                'max_size': 5000  # max < min
            })
        
        assert "min_size" in str(exc_info.value)
        assert "max_size" in str(exc_info.value)

    def test_invalid_config_initial_out_of_range(self):
        """场景10: 无效配置 - initial_size超出范围"""
        with pytest.raises(ValueError) as exc_info:
            AdaptiveBatchManager({
                'initial_size': 100,  # < min_size
                'min_size': 1000,
                'max_size': 50000
            })
        
        assert "initial_size" in str(exc_info.value)

    # =====================================================
    # 性能测试 (2个场景)
    # =====================================================

    def test_disabled_manager_returns_unchanged_batch(self):
        """场景11: 禁用管理器时返回原批量大小"""
        manager = AdaptiveBatchManager({
            'enabled': False
        })
        
        performance = {
            'memory_mb': 900,
            'throughput': 3000,
            'duration_ms': 10000
        }
        
        new_batch, reason = manager.adjust(10000, performance)
        
        # 验证批量不变
        assert new_batch == 10000
        assert "禁用" in reason

    def test_small_adjustment_threshold(self):
        """场景12: 小幅调整（<10%）时保持不变"""
        manager = AdaptiveBatchManager({
            'enabled': True,
            'initial_size': 10000,
            'min_size': 1000,
            'max_size': 50000,
            'memory_limit_mb': 1000,
            'target_throughput': 10000
        })
        
        # 模拟略微偏离目标的性能（但不足以触发大幅调整）
        performance = {
            'memory_mb': 550,  # 略高于50%
            'throughput': 9500,  # 略低于目标
            'duration_ms': 5500
        }
        
        new_batch, reason = manager.adjust(10000, performance)
        
        # 验证批量保持不变（因为调整幅度<10%）
        assert new_batch == 10000
        assert "保持不变" in reason or "稳定" in reason


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

