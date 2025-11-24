"""
出水检测器（app.services.calculation.metrics.pump_flow_rate.pump_k_coefficient.detector）

本模块实现基于 k 系数和出口压力的泵出水判断。

核心原理：
    f_min = sqrt(P_outlet × 102 / k)
    is_outputting = 1 if f >= f_min else 0

使用方式：
    from app.services.calculation.metrics.pump_flow_rate.pump_k_coefficient import WaterOutputDetector

    detector = WaterOutputDetector(station_id=1, params={...})
    enhanced_df = detector.detect(df)  # 添加 f_min 和 is_outputting 列
"""

from __future__ import annotations

import logging
import math
from typing import Dict, Any, Optional, List, Tuple

import pandas as pd

from app.services.calculation.shared.parameter_manager import ParameterManager
from .constants import (
    PRESSURE_TO_HEAD, PARAM_NAME_K_COEFFICIENT, METRIC_KEY,
    PARAM_NAME_K_DEFAULT, PARAM_NAME_F_MIN_FALLBACK,
    PARAM_NAME_F_MIN_LOWER_BOUND, PARAM_NAME_F_MIN_UPPER_BOUND,
)

_log = logging.getLogger(__name__)


class WaterOutputDetector:
    """
    出水检测器

    使用学习到的 k 系数和实时出口压力计算最小有效频率 f_min，
    判断每台泵是否在出水。
    所有配置参数从数据库 calculation_parameters 表读取。
    """

    def __init__(
        self,
        station_id: int,
        params: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ):
        """
        初始化检测器

        Args:
            station_id: 泵站ID，用于参数查询
            params: 预加载的参数字典（可选）
            trace_id: 追踪ID，用于日志关联
        """
        self.station_id = station_id
        self.params = params or {}
        self.trace_id = trace_id or "water_output_detector"
        self.logger = _log

        # k 值缓存：{device_id: (k_value, source)}
        self._k_cache: Dict[int, Tuple[float, str]] = {}

        # 加载全局参数
        self._param_manager = ParameterManager()
        self._global_params = self._param_manager.get_parameters(
            metric_key=METRIC_KEY, station_id=station_id
        )

    def detect(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        检测每行数据的出水状态

        Args:
            data: 输入 DataFrame，必须包含以下列：
                - device_id: 设备ID
                - pump_frequency: 泵频率
                - main_pipeline_outlet_pressure: 出口压力（可选）

        Returns:
            pd.DataFrame: 添加了以下列的 DataFrame：
                - f_min: 最小有效频率
                - is_outputting: 出水状态（1=出水, 0=不出水）
        """
        if data.empty:
            data['f_min'] = pd.Series(dtype=float)
            data['is_outputting'] = pd.Series(dtype=int)
            return data

        # 获取回退 f_min 参数
        f_min_fallback = self._get_param(PARAM_NAME_F_MIN_FALLBACK)

        # 检查必需列
        if 'device_id' not in data.columns:
            self.logger.error("[出水检测] 缺少 device_id 列")
            data['f_min'] = f_min_fallback
            data['is_outputting'] = 1
            return data

        # 获取出口压力列
        pressure_col = None
        for col in ['main_pipeline_outlet_pressure', 'outlet_pressure', 'p_outlet']:
            if col in data.columns:
                pressure_col = col
                break

        if pressure_col is None:
            self.logger.warning(
                "[出水检测] 未找到出口压力列，使用回退 f_min",
                extra={'extra_data': {'available_columns': list(data.columns)}}
            )
            data['f_min'] = f_min_fallback
            # 假设所有运行中的泵都出水
            freq_col = 'pump_frequency' if 'pump_frequency' in data.columns else None
            if freq_col:
                data['is_outputting'] = (data[freq_col] >= f_min_fallback).astype(int)
            else:
                data['is_outputting'] = 1
            return data

        # 获取频率列
        freq_col = 'pump_frequency' if 'pump_frequency' in data.columns else None
        if freq_col is None:
            self.logger.error("[出水检测] 缺少 pump_frequency 列")
            data['f_min'] = f_min_fallback
            data['is_outputting'] = 1
            return data

        # 计算每行的 f_min 和 is_outputting
        f_min_list = []
        is_outputting_list = []

        for idx, row in data.iterrows():
            device_id = int(row['device_id'])
            pressure = row[pressure_col]
            frequency = row[freq_col]

            # 计算 f_min
            f_min = self._calculate_f_min(device_id, pressure)
            f_min_list.append(f_min)

            # 判断出水状态
            is_out = 1 if frequency >= f_min else 0
            is_outputting_list.append(is_out)

        data['f_min'] = f_min_list
        data['is_outputting'] = is_outputting_list

        # 记录统计信息
        outputting_count = sum(is_outputting_list)
        total_count = len(is_outputting_list)
        self.logger.debug(
            "[出水检测] 检测完成",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'total_rows': total_count,
                'outputting_rows': outputting_count,
                'non_outputting_rows': total_count - outputting_count,
            }}
        )

        return data

    def _get_param(self, name: str) -> float:
        """获取参数值"""
        if name not in self._global_params:
            raise ValueError(f"参数 {name} 未在数据库中配置")
        return float(self._global_params[name])

    def detect_for_other_devices(
        self,
        other_devices: List[Dict[str, Any]],
        outlet_pressure: float
    ) -> List[Dict[str, Any]]:
        """
        为 other_devices 列表计算出水状态

        Args:
            other_devices: 其他设备列表，每个字典包含 device_id, frequency 等
            outlet_pressure: 当前出口压力

        Returns:
            List[Dict]: 添加了 f_min 和 is_outputting 的设备列表
        """
        f_min_fallback = self._get_param(PARAM_NAME_F_MIN_FALLBACK)

        result = []
        for device in other_devices:
            device_id = device.get('device_id')
            frequency = device.get('frequency', 0) or device.get('pump_frequency', 0)

            if device_id is None:
                device['f_min'] = f_min_fallback
                device['is_outputting'] = 1 if frequency >= f_min_fallback else 0
            else:
                f_min = self._calculate_f_min(int(device_id), outlet_pressure)
                device['f_min'] = f_min
                device['is_outputting'] = 1 if frequency >= f_min else 0

            result.append(device)

        return result

    def _calculate_f_min(self, device_id: int, outlet_pressure: float) -> float:
        """
        计算最小有效频率

        公式：f_min = sqrt(P_outlet × 102 / k)

        Args:
            device_id: 设备ID
            outlet_pressure: 出口压力（MPa）

        Returns:
            float: 最小有效频率（Hz）
        """
        # 获取参数
        f_min_fallback = self._get_param(PARAM_NAME_F_MIN_FALLBACK)
        f_min_lower = self._get_param(PARAM_NAME_F_MIN_LOWER_BOUND)
        f_min_upper = self._get_param(PARAM_NAME_F_MIN_UPPER_BOUND)

        # 处理无效压力
        if outlet_pressure is None or math.isnan(outlet_pressure) or outlet_pressure <= 0:
            return f_min_fallback

        # 获取 k 值
        k, source = self._get_k_coefficient(device_id)

        # 计算 f_min = sqrt(P_outlet × 102 / k)
        try:
            f_min_squared = outlet_pressure * PRESSURE_TO_HEAD / k
            if f_min_squared < 0:
                return f_min_fallback
            f_min = math.sqrt(f_min_squared)
        except (ValueError, ZeroDivisionError):
            return f_min_fallback

        # 限制在合理范围
        f_min = max(f_min_lower, min(f_min_upper, f_min))

        return f_min

    def _get_k_coefficient(self, device_id: int) -> Tuple[float, str]:
        """
        获取设备的 k 系数

        优先级：设备级 > 预加载参数 > 默认值

        Args:
            device_id: 设备ID

        Returns:
            Tuple[float, str]: (k_value, source)
        """
        # 检查缓存
        if device_id in self._k_cache:
            return self._k_cache[device_id]

        # 尝试从预加载参数获取
        param_key = f"pump_k_coefficient_{device_id}"
        if param_key in self.params:
            k = float(self.params[param_key])
            self._k_cache[device_id] = (k, "preloaded")
            return k, "preloaded"

        # 尝试通用参数名
        if PARAM_NAME_K_COEFFICIENT in self.params:
            k = float(self.params[PARAM_NAME_K_COEFFICIENT])
            self._k_cache[device_id] = (k, "preloaded_global")
            return k, "preloaded_global"

        # 从数据库加载
        k, source = self._load_k_from_db(device_id)
        self._k_cache[device_id] = (k, source)
        return k, source

    def _load_k_from_db(self, device_id: int) -> Tuple[float, str]:
        """
        从数据库加载 k 系数

        三级回退：设备级 → 泵站平均 → 全局默认

        Args:
            device_id: 设备ID

        Returns:
            Tuple[float, str]: (k_value, source)
        """
        from app.adapters.db.pool import get_connection

        sql = """
            WITH param_hierarchy AS (
                SELECT
                    param_value,
                    CASE
                        WHEN device_id IS NOT NULL THEN 1
                        WHEN station_id IS NOT NULL THEN 2
                        ELSE 3
                    END AS priority
                FROM calculation_parameters
                WHERE metric_key = %s
                  AND param_name = %s
                  AND (
                      device_id = %s OR
                      (station_id = %s AND device_id IS NULL) OR
                      (station_id IS NULL AND device_id IS NULL)
                  )
            )
            SELECT param_value
            FROM param_hierarchy
            ORDER BY priority
            LIMIT 1
        """

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, [
                        METRIC_KEY, PARAM_NAME_K_COEFFICIENT,
                        device_id, self.station_id
                    ])
                    row = cur.fetchone()

                    if row and row[0]:
                        return float(row[0]), "database"

        except Exception as e:
            self.logger.warning(
                "[出水检测] 从数据库加载 k 值失败",
                extra={'extra_data': {'device_id': device_id, 'error': str(e)}}
            )

        # 返回数据库配置的默认值
        k_default = self._get_param(PARAM_NAME_K_DEFAULT)
        return k_default, "default"

    def clear_cache(self):
        """清除 k 值缓存"""
        self._k_cache.clear()

