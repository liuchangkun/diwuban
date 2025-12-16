"""
时间窗口验证器 (app.services.characteristic_curves.shared.time_window_validator)

验证时间窗口的有效性。

版本: v1.0
参考: 设计文档 3.6.8节
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple


logger = logging.getLogger(__name__)


class TimeWindowValidator:
    """时间窗口验证器
    
    验证时间窗口的有效性。
    
    验证规则:
    - 窗口时长需满足最小要求
    - 时间顺序正确
    - 拟合窗口与测试窗口不重叠
    - 不能使用未来数据
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化验证器
        
        Args:
            config: 配置参数,可选
        """
        self._config = config or {}
        self._min_duration_days = self._config.get('min_duration_days', 7.0)
        
        logger.info(
            "[时间窗口验证器] 初始化",
            extra={"extra_data": {
                "min_duration_days": self._min_duration_days,
            }}
        )
    
    def validate(
        self,
        fit_window: Tuple[datetime, datetime],
        test_window: Optional[Tuple[datetime, datetime]] = None,
        config: Optional[Dict] = None
    ) -> Tuple[bool, List[str]]:
        """验证时间窗口
        
        Args:
            fit_window: 拟合窗口 (start_time, end_time)
            test_window: 测试窗口 (start_time, end_time),可选
            config: 额外配置(可选)
        
        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors = []
        
        # 验证拟合窗口
        fit_start, fit_end = fit_window
        
        # 规则1: 时间顺序
        if fit_start >= fit_end:
            errors.append(f"拟合窗口时间顺序错误: {fit_start} >= {fit_end}")
        
        # 规则2: 窗口时长
        fit_duration_days = (fit_end - fit_start).total_seconds() / 86400
        if fit_duration_days < self._min_duration_days:
            errors.append(
                f"拟合窗口时长不足: {fit_duration_days:.1f}天 < "
                f"{self._min_duration_days}天"
            )
        
        # 规则3: 未来时间
        now = datetime.now()
        if fit_end > now:
            errors.append(f"不能使用未来数据: {fit_end} > {now}")
        
        # 验证测试窗口(如果提供)
        if test_window is not None:
            test_start, test_end = test_window
            
            # 时间顺序
            if test_start >= test_end:
                errors.append(f"测试窗口时间顺序错误: {test_start} >= {test_end}")
            
            # 窗口不重叠
            if not (fit_end <= test_start or test_end <= fit_start):
                errors.append(
                    f"拟合窗口与测试窗口重叠: "
                    f"fit=[{fit_start}, {fit_end}], "
                    f"test=[{test_start}, {test_end}]"
                )
            
            # 未来时间
            if test_end > now:
                errors.append(f"测试窗口不能使用未来数据: {test_end} > {now}")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info("[时间窗口验证] 通过")
        else:
            logger.warning(f"[时间窗口验证] 失败: {errors}")
        
        return is_valid, errors
