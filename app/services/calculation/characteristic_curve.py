"""
CharacteristicCurveManager - 水泵特性曲线管理器

负责加载、插值和验证水泵特性曲线数据。

支持的曲线类型：
- Q-H：流量-扬程曲线
- Q-P：流量-功率曲线
- Q-eta：流量-效率曲线

使用示例：
    from app.services.calculation.characteristic_curve import CharacteristicCurveManager
    
    manager = CharacteristicCurveManager()
    
    # 加载曲线
    curves = manager.load_curves(device_id=1, curve_type='Q-H')
    
    # 插值计算
    expected_head = manager.interpolate('Q-H', flow_rate=150, curves_data=curves)
    
    # 验证数据点
    is_valid, deviation = manager.validate_point(
        'Q-H', flow_rate=150, actual_value=29.5, 
        curves_data=curves, tolerance=0.1
    )
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.interpolate import interp1d

from app.adapters.db import get_connection

logger = logging.getLogger(__name__)


class CharacteristicCurveManager:
    """
    水泵特性曲线管理器
    
    负责加载、插值和验证水泵特性曲线数据。
    
    Attributes:
        _cache: 曲线数据缓存
        _cache_ttl: 缓存过期时间（秒）
        _cache_timestamps: 缓存时间戳
    """
    
    def __init__(self, cache_ttl: int = 3600):
        """
        初始化管理器
        
        Args:
            cache_ttl: 缓存过期时间（秒），默认3600秒（1小时）
        """
        self._cache: Dict[str, List[Tuple[float, float]]] = {}
        self._cache_ttl = cache_ttl
        self._cache_timestamps: Dict[str, float] = {}
        logger.info("[核心-初始化] CharacteristicCurveManager 初始化完成")
    
    def load_curves(
        self,
        device_id: int,
        curve_type: str,
        speed: Optional[float] = None,
        frequency: Optional[float] = None,
        use_cache: bool = True
    ) -> List[Tuple[float, float]]:
        """
        加载特性曲线数据
        
        Args:
            device_id: 设备ID
            curve_type: 曲线类型（'Q-H', 'Q-P', 'Q-eta'）
            speed: 转速（rpm），None表示额定转速
            frequency: 频率（Hz），None表示额定频率
            use_cache: 是否使用缓存
        
        Returns:
            曲线数据列表：[(flow_rate, value), ...]，按flow_rate排序
        
        Raises:
            ValueError: 如果曲线类型无效或没有数据
        """
        logger.info(
            "[流程-开始] [加载特性曲线]",
            extra={
                "extra_data": {
                    "device_id": device_id,
                    "curve_type": curve_type,
                    "speed": speed,
                    "frequency": frequency,
                    "use_cache": use_cache,
                }
            }
        )

        # 验证曲线类型
        if curve_type not in ['Q-H', 'Q-P', 'Q-eta']:
            logger.error(
                "[流程-错误] [无效的曲线类型]",
                extra={"extra_data": {"curve_type": curve_type}}
            )
            raise ValueError(f"无效的曲线类型: {curve_type}")

        # 构建缓存键
        cache_key = f"{device_id}_{curve_type}_{speed}_{frequency}"

        # 检查缓存
        if use_cache and cache_key in self._cache:
            # 检查缓存是否过期
            if time.time() - self._cache_timestamps.get(cache_key, 0) < self._cache_ttl:
                logger.info(
                    "[流程-完成] [从缓存加载曲线]",
                    extra={
                        "extra_data": {
                            "cache_key": cache_key,
                            "points": len(self._cache[cache_key]),
                        }
                    }
                )
                return self._cache[cache_key]

        # 从数据库加载
        logger.info("[流程-阶段] [从数据库加载曲线]")
        
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 构建查询
                    if speed is None and frequency is None:
                        # 查询任意转速/频率的曲线（取第一个可用的组合）
                        # 先获取第一个speed/frequency组合
                        cur.execute("""
                            SELECT speed, frequency
                            FROM pump_characteristic_curves
                            WHERE device_id = %s AND curve_type = %s
                            ORDER BY
                                CASE WHEN speed IS NULL THEN 0 ELSE 1 END,
                                COALESCE(speed, 0),
                                COALESCE(frequency, 0)
                            LIMIT 1
                        """, (device_id, curve_type))

                        first_group = cur.fetchone()
                        if first_group:
                            first_speed, first_freq = first_group

                            # 获取该组合的所有数据点
                            cur.execute("""
                                SELECT flow_rate, value
                                FROM pump_characteristic_curves
                                WHERE device_id = %s
                                  AND curve_type = %s
                                  AND (speed IS NOT DISTINCT FROM %s)
                                  AND (frequency IS NOT DISTINCT FROM %s)
                                ORDER BY flow_rate
                            """, (device_id, curve_type, first_speed, first_freq))

                            rows = cur.fetchall()
                        else:
                            rows = []
                    else:
                        # 查询指定转速/频率的曲线
                        query = """
                            SELECT flow_rate, value
                            FROM pump_characteristic_curves
                            WHERE device_id = %s
                              AND curve_type = %s
                              AND (speed IS NOT DISTINCT FROM %s)
                              AND (frequency IS NOT DISTINCT FROM %s)
                            ORDER BY flow_rate
                        """
                        cur.execute(query, (device_id, curve_type, speed, frequency))
                        rows = cur.fetchall()

                    if not rows:
                        logger.error(
                            "[流程-错误] [没有找到曲线数据]",
                            extra={
                                "extra_data": {
                                    "device_id": device_id,
                                    "curve_type": curve_type,
                                    "speed": speed,
                                    "frequency": frequency,
                                }
                            }
                        )
                        raise ValueError(
                            f"没有找到曲线数据: device_id={device_id}, "
                            f"type={curve_type}, speed={speed}, frequency={frequency}"
                        )

                    # 转换为列表
                    curves_data = [(float(row[0]), float(row[1])) for row in rows]

                    logger.info(
                        "[流程-阶段] [数据库查询完成]",
                        extra={"extra_data": {"points": len(curves_data)}}
                    )

                    # 保存到缓存
                    if use_cache:
                        self._cache[cache_key] = curves_data
                        self._cache_timestamps[cache_key] = time.time()
                        logger.info("[流程-阶段] [曲线已缓存]")

                    logger.info(
                        "[流程-完成] [加载曲线成功]",
                        extra={
                            "extra_data": {
                                "device_id": device_id,
                                "curve_type": curve_type,
                                "points": len(curves_data),
                                "cached": use_cache,
                            }
                        }
                    )

                    return curves_data

        except Exception as e:
            logger.error(
                "[流程-错误] [加载曲线失败]",
                extra={
                    "extra_data": {
                        "device_id": device_id,
                        "curve_type": curve_type,
                        "error": str(e),
                    }
                },
                exc_info=True
            )
            raise
    
    def interpolate(
        self,
        curve_type: str,
        flow_rate: float,
        curves_data: List[Tuple[float, float]],
        method: str = 'linear'
    ) -> float:
        """
        插值计算
        
        Args:
            curve_type: 曲线类型
            flow_rate: 流量（m³/h）
            curves_data: 曲线数据
            method: 插值方法（'linear', 'cubic'）
        
        Returns:
            插值结果
        
        Raises:
            ValueError: 如果流量超出曲线范围
        """
        if not curves_data:
            raise ValueError("曲线数据为空")
        
        # 提取流量和值
        flow_rates = np.array([point[0] for point in curves_data])
        values = np.array([point[1] for point in curves_data])
        
        # 检查范围
        min_flow = flow_rates.min()
        max_flow = flow_rates.max()
        
        if flow_rate < min_flow or flow_rate > max_flow:
            logger.warning(
                f"流量 {flow_rate} 超出曲线范围 [{min_flow}, {max_flow}]",
                extra={"flow_rate": flow_rate, "range": [min_flow, max_flow]}
            )
            # 使用边界值
            if flow_rate < min_flow:
                return float(values[0])
            else:
                return float(values[-1])
        
        # 插值
        if method == 'linear':
            f = interp1d(flow_rates, values, kind='linear')
        elif method == 'cubic':
            if len(flow_rates) < 4:
                logger.warning("数据点不足4个，使用线性插值")
                f = interp1d(flow_rates, values, kind='linear')
            else:
                f = interp1d(flow_rates, values, kind='cubic')
        else:
            raise ValueError(f"无效的插值方法: {method}")
        
        result = float(f(flow_rate))
        
        logger.debug(
            f"插值计算: {curve_type}, flow={flow_rate}, result={result:.2f}",
            extra={"curve_type": curve_type, "flow_rate": flow_rate, "result": result}
        )
        
        return result
    
    def get_expected_value(
        self,
        curve_type: str,
        flow_rate: float,
        curves_data: List[Tuple[float, float]]
    ) -> float:
        """
        获取期望值（插值计算的别名）
        
        Args:
            curve_type: 曲线类型
            flow_rate: 流量
            curves_data: 曲线数据
        
        Returns:
            期望值
        """
        return self.interpolate(curve_type, flow_rate, curves_data)
    
    def validate_point(
        self,
        curve_type: str,
        flow_rate: float,
        actual_value: float,
        curves_data: List[Tuple[float, float]],
        tolerance: float = 0.1
    ) -> Tuple[bool, float]:
        """
        验证单个数据点
        
        Args:
            curve_type: 曲线类型
            flow_rate: 流量
            actual_value: 实际值
            curves_data: 曲线数据
            tolerance: 容忍度（相对误差，默认0.1即10%）
        
        Returns:
            (是否有效, 偏差百分比)
        """
        try:
            # 获取期望值
            expected_value = self.interpolate(curve_type, flow_rate, curves_data)
            
            # 计算偏差
            if expected_value == 0:
                # 避免除以零
                deviation = abs(actual_value - expected_value)
                is_valid = deviation <= tolerance
            else:
                deviation = abs(actual_value - expected_value) / abs(expected_value)
                is_valid = deviation <= tolerance
            
            logger.debug(
                f"验证点: {curve_type}, flow={flow_rate}, "
                f"expected={expected_value:.2f}, actual={actual_value:.2f}, "
                f"deviation={deviation:.2%}, valid={is_valid}",
                extra={
                    "curve_type": curve_type,
                    "flow_rate": flow_rate,
                    "expected": expected_value,
                    "actual": actual_value,
                    "deviation": deviation,
                    "valid": is_valid
                }
            )
            
            return is_valid, deviation
        
        except Exception as e:
            logger.error(f"验证点失败: {e}", exc_info=True)
            return False, float('inf')
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.info("缓存已清空")
    
    def get_cache_stats(self) -> Dict:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计字典
        """
        return {
            'cache_size': len(self._cache),
            'cache_keys': list(self._cache.keys()),
            'cache_ttl': self._cache_ttl
        }

