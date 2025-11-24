"""
时间窗口划分器 (app.services.characteristic_curves.shared.time_window_splitter)

本模块提供时间窗口的自动划分功能：
- 按75%/25%比例划分拟合窗口和测试窗口
- 确保拟合和测试数据不重叠
- 验证数据量是否足够

配置参数：
- fit_ratio: 拟合数据占比（默认0.75）
- min_fit_days: 最小拟合天数（默认30）
- min_test_days: 最小测试天数（默认7）
- min_test_points: 最小测试点数（默认100）

使用方式：
    from app.services.characteristic_curves.shared import TimeWindowSplitter
    
    splitter = TimeWindowSplitter(fit_ratio=0.75)
    result = splitter.split(device_id=1, curve_type='qh')
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from app.adapters.db import get_connection
from app.services.characteristic_curves.shared.historical_data_evaluator import (
    CURVE_METRICS,
    TimeWindow,
    TimeWindowSplitResult,
)


class TimeWindowSplitter:
    """时间窗口自动划分器
    
    按75%/25%比例划分拟合窗口和测试窗口，确保数据不重叠。
    """

    def __init__(
        self,
        fit_ratio: float = 0.75,
        min_fit_days: int = 30,
        min_test_days: int = 7,
        min_test_points: int = 100
    ):
        """初始化时间窗口划分器
        
        Args:
            fit_ratio: 拟合数据占比，默认0.75
            min_fit_days: 最小拟合天数，默认30
            min_test_days: 最小测试天数，默认7
            min_test_points: 最小测试点数，默认100
        """
        self._fit_ratio = fit_ratio
        self._test_ratio = 1.0 - fit_ratio
        self._min_fit_days = min_fit_days
        self._min_test_days = min_test_days
        self._min_test_points = min_test_points
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        self._logger.info(
            "[时间划分] 初始化",
            extra={"extra_data": {
                "组件": "TimeWindowSplitter",
                "拟合比例": fit_ratio,
                "最小拟合天数": min_fit_days,
                "最小测试天数": min_test_days
            }}
        )

    def split(
        self,
        device_id: int,
        curve_type: str
    ) -> TimeWindowSplitResult:
        """自动划分拟合和测试时间窗口
        
        处理流程：
        1. 查询 fact_measurements 表获取数据时间范围
        2. 计算总天数，按 75%/25% 比例划分
        3. 验证测试数据量是否足够
        4. 返回划分结果
        
        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            
        Returns:
            TimeWindowSplitResult: 划分结果
        """
        warnings = []
        
        # 获取数据时间范围
        time_range = self._get_data_time_range(device_id, curve_type)
        
        if time_range is None:
            self._logger.warning(f"[时间划分] 无法获取设备{device_id}的数据时间范围")
            now = datetime.now()
            return TimeWindowSplitResult(
                fit_window=TimeWindow(start=now, end=now, point_count=0),
                test_window=TimeWindow(start=now, end=now, point_count=0),
                total_days=0,
                fit_days=0,
                test_days=0,
                can_evaluate=False,
                warnings=["无法获取数据时间范围"]
            )
        
        start_time = time_range['start']
        end_time = time_range['end']
        total_points = time_range['point_count']
        
        # 计算总天数
        total_days = (end_time - start_time).days
        
        if total_days < self._min_fit_days + self._min_test_days:
            warnings.append(
                f"数据天数不足: {total_days}天 < 最小要求{self._min_fit_days + self._min_test_days}天"
            )
        
        # 按比例计算划分点
        fit_days = max(int(total_days * self._fit_ratio), self._min_fit_days)
        test_days = total_days - fit_days
        
        if test_days < self._min_test_days:
            test_days = self._min_test_days
            fit_days = total_days - test_days
            warnings.append(f"测试天数调整为最小值: {test_days}天")
        
        # 计算时间窗口边界
        split_point = start_time + timedelta(days=fit_days)
        
        fit_window = TimeWindow(
            start=start_time,
            end=split_point,
            point_count=int(total_points * self._fit_ratio)
        )
        
        test_window = TimeWindow(
            start=split_point,
            end=end_time,
            point_count=int(total_points * self._test_ratio)
        )
        
        # 验证测试数据量
        can_evaluate = test_window.point_count >= self._min_test_points
        if not can_evaluate:
            warnings.append(
                f"测试点数不足: {test_window.point_count} < {self._min_test_points}"
            )
        
        result = TimeWindowSplitResult(
            fit_window=fit_window,
            test_window=test_window,
            total_days=total_days,
            fit_days=fit_days,
            test_days=test_days,
            can_evaluate=can_evaluate,
            warnings=warnings
        )

        self._logger.info(
            "[时间划分] 划分完成",
            extra={"extra_data": {
                "设备ID": device_id,
                "曲线类型": curve_type,
                "总天数": total_days,
                "拟合天数": fit_days,
                "测试天数": test_days,
                "可评估": can_evaluate
            }}
        )

        return result

    def _get_data_time_range(
        self,
        device_id: int,
        curve_type: str
    ) -> Optional[Dict[str, Any]]:
        """获取设备数据的时间范围

        Args:
            device_id: 设备ID
            curve_type: 曲线类型

        Returns:
            Dict: {'start': datetime, 'end': datetime, 'point_count': int}
        """
        if curve_type not in CURVE_METRICS:
            self._logger.warning(f"[时间划分] 不支持的曲线类型: {curve_type}")
            return None

        x_col = CURVE_METRICS[curve_type]['x']
        y_col = CURVE_METRICS[curve_type]['y']

        sql = f"""
            SELECT
                MIN(ts) as start_time,
                MAX(ts) as end_time,
                COUNT(*) as point_count
            FROM fact_measurements
            WHERE device_id = %s
              AND {x_col} IS NOT NULL
              AND {y_col} IS NOT NULL
              AND {x_col} > 0
              AND {y_col} > 0
        """

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (device_id,))
                    row = cur.fetchone()

                    if row is None or row[0] is None:
                        return None

                    return {
                        'start': row[0],
                        'end': row[1],
                        'point_count': row[2]
                    }
        except Exception as e:
            self._logger.error(
                f"[时间划分] 查询数据时间范围失败: {e}",
                exc_info=True
            )
            return None

    def split_with_custom_range(
        self,
        start_time: datetime,
        end_time: datetime,
        total_points: int = 0
    ) -> TimeWindowSplitResult:
        """使用自定义时间范围进行划分

        Args:
            start_time: 起始时间
            end_time: 结束时间
            total_points: 总数据点数（可选）

        Returns:
            TimeWindowSplitResult: 划分结果
        """
        warnings = []
        total_days = (end_time - start_time).days

        if total_days < self._min_fit_days + self._min_test_days:
            warnings.append(
                f"数据天数不足: {total_days}天 < 最小要求{self._min_fit_days + self._min_test_days}天"
            )

        fit_days = max(int(total_days * self._fit_ratio), self._min_fit_days)
        test_days = total_days - fit_days

        if test_days < self._min_test_days:
            test_days = self._min_test_days
            fit_days = total_days - test_days
            warnings.append(f"测试天数调整为最小值: {test_days}天")

        split_point = start_time + timedelta(days=fit_days)

        fit_window = TimeWindow(
            start=start_time,
            end=split_point,
            point_count=int(total_points * self._fit_ratio)
        )

        test_window = TimeWindow(
            start=split_point,
            end=end_time,
            point_count=int(total_points * self._test_ratio)
        )

        can_evaluate = test_window.point_count >= self._min_test_points or total_points == 0
        if not can_evaluate:
            warnings.append(
                f"测试点数不足: {test_window.point_count} < {self._min_test_points}"
            )

        return TimeWindowSplitResult(
            fit_window=fit_window,
            test_window=test_window,
            total_days=total_days,
            fit_days=fit_days,
            test_days=test_days,
            can_evaluate=can_evaluate,
            warnings=warnings
        )

    @property
    def fit_ratio(self) -> float:
        """获取拟合数据占比"""
        return self._fit_ratio

    @property
    def test_ratio(self) -> float:
        """获取测试数据占比"""
        return self._test_ratio

    @property
    def min_fit_days(self) -> int:
        """获取最小拟合天数"""
        return self._min_fit_days

    @property
    def min_test_days(self) -> int:
        """获取最小测试天数"""
        return self._min_test_days

    @property
    def min_test_points(self) -> int:
        """获取最小测试点数"""
        return self._min_test_points

