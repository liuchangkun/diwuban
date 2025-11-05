"""
测试设备运行阈值学习功能

职责：
- 测试 prepare_dim_stage2 流程
- 验证阈值学习是否成功
- 提供详细的执行日志

作者：AI
创建日期：2025-10-24
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.services.rules.running_thresholds import run_running_thresholds
from app.services.rules.validate_thresholds import validate_device_running_thresholds
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_log = logging.getLogger(__name__)


def test_threshold_learning():
    """测试阈值学习功能"""
    
    _log.info("=" * 80)
    _log.info("开始测试设备运行阈值学习功能")
    _log.info("=" * 80)
    
    settings = load_settings(Path("configs"))
    
    try:
        # 执行 run_running_thresholds
        _log.info("\n执行 run_running_thresholds()...")
        result = run_running_thresholds(
            settings=settings,
            start=None,  # 使用全局时间窗口
            end=None,
            station_id=None,  # 处理所有泵站
            device_id=None,  # 处理所有设备
            ensure_rows=True,  # 确保设备行存在
            method="robust",  # 使用稳健分位数方法
        )

        _log.info("\n" + "=" * 80)
        _log.info("run_running_thresholds 执行完成")
        _log.info("=" * 80)

        # 打印结果
        if result:
            _log.info("\n执行结果：")
            for key, value in result.items():
                _log.info(f"  {key}: {value}")

        # 执行验证
        _log.info("\n" + "=" * 80)
        _log.info("执行阈值验证...")
        _log.info("=" * 80)

        validation_result = validate_device_running_thresholds(settings)

        _log.info("\n验证结果：")
        _log.info(f"  是否通过: {validation_result['is_valid']}")
        _log.info(f"  总设备数: {validation_result['total_devices']}")
        _log.info(f"  已配置设备数: {validation_result['configured_devices']}")
        _log.info(f"  缺少配置设备数: {len(validation_result['missing_devices'])}")
        _log.info(f"  配置不完整设备数: {len(validation_result['incomplete_devices'])}")
        _log.info(f"  摘要: {validation_result['summary']}")

        if validation_result['warnings']:
            _log.info("\n警告信息：")
            for warning in validation_result['warnings']:
                _log.warning(f"  {warning}")

        return validation_result['is_valid']
    
    except Exception as e:
        _log.error(f"\n测试失败：{e}", exc_info=True)
        return False


if __name__ == "__main__":
    try:
        success = test_threshold_learning()
        sys.exit(0 if success else 1)
    except Exception as e:
        _log.error(f"测试失败：{e}", exc_info=True)
        sys.exit(1)

