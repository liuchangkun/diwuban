"""
Validator - 计算结果验证器

验证计算结果是否符合物理规律和合理范围。

验证规则:
1. 范围检查：值是否在合理范围内
2. 物理规律检查：是否符合基本物理定律
3. 一致性检查：相关指标之间是否一致

使用示例:
    from app.services.calculation.validator import PhysicsValidator

    validator = PhysicsValidator()
    is_valid, errors = validator.validate(
        metric_key='pump_flow_rate',
        values=np.array([100.0, 120.0, 110.0]),
        context={'device_id': 1}
    )
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

import numpy as np

from app.adapters.db import get_connection
from app.services.calculation.characteristic_curve import CharacteristicCurveManager

from app.services.calculation.domain import CalculationContext

logger = logging.getLogger(__name__)


class PhysicsValidator:
    """
    物理规律验证器

    验证计算结果是否符合物理规律和合理范围。

    Attributes:
        _validation_config: 验证配置（从数据库加载）
    """

    def __init__(self):
        """初始化验证器"""
        logger.info("[流程-开始] [物理验证器初始化]")

        self._validation_config: Dict[str, List[Dict]] = {}
        self._config_cache_time: float = 0  # 配置缓存时间戳
        self._cache_ttl: int = 300  # 缓存有效期（秒）
        self._curve_manager = CharacteristicCurveManager()  # 特性曲线管理器
        self._load_config_from_db()
        logger.info("[核心-初始化] PhysicsValidator 初始化完成")

    def _load_config_from_db(
        self,
        station_id: int = None,
        device_id: int = None,
        force_reload: bool = False
    ) -> None:
        """
        从数据库加载验证配置

        支持层级配置：全局 → 站点 → 设备
        优先级：设备级 > 站点级 > 全局级

        Args:
            station_id: 站点ID（可选）
            device_id: 设备ID（可选）
            force_reload: 强制重新加载（忽略缓存）
        """
        import time

        # 检查缓存是否有效
        current_time = time.time()
        if not force_reload and (current_time - self._config_cache_time) < self._cache_ttl:
            logger.debug("使用缓存的验证配置")
            return

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 查询验证配置（支持层级）
                    # 优先级：设备级 > 站点级 > 全局级
                    query = """
                        SELECT
                            metric_key,
                            validator_type,
                            params,
                            priority,
                            CASE
                                WHEN device_id IS NOT NULL THEN 3
                                WHEN station_id IS NOT NULL THEN 2
                                ELSE 1
                            END as config_level
                        FROM calculation_validation_config
                        WHERE is_enabled = TRUE
                            AND (
                                (station_id IS NULL AND device_id IS NULL)  -- 全局配置
                                OR (station_id = %s AND device_id IS NULL)  -- 站点配置
                                OR (station_id = %s AND device_id = %s)     -- 设备配置
                            )
                        ORDER BY metric_key, config_level DESC, priority ASC
                    """
                    cur.execute(query, (station_id, station_id, device_id))
                    rows = cur.fetchall()

                    # 清空现有配置
                    self._validation_config.clear()

                    # 按指标分组，保留最高优先级的配置
                    seen_validators = {}  # {(metric_key, validator_type): config_level}

                    for row in rows:
                        metric_key, validator_type, params, priority, config_level = row

                        # 检查是否已有更高优先级的配置
                        key = (metric_key, validator_type)
                        if key in seen_validators and seen_validators[key] > config_level:
                            continue  # 跳过低优先级配置

                        seen_validators[key] = config_level

                        if metric_key not in self._validation_config:
                            self._validation_config[metric_key] = []

                        # 解析JSONB参数
                        params_dict = params if isinstance(params, dict) else {}

                        self._validation_config[metric_key].append({
                            'validator_type': validator_type,
                            'params': params_dict,
                            'priority': priority,
                            'config_level': config_level
                        })

                    # 更新缓存时间
                    self._config_cache_time = current_time

                    logger.info(
                        f"PhysicsValidator 加载完成：{len(self._validation_config)} 个指标的验证配置",
                        extra={
                            "metric_count": len(self._validation_config),
                            "station_id": station_id,
                            "device_id": device_id
                        }
                    )
        except Exception as e:
            logger.warning(f"PhysicsValidator 加载配置失败（使用默认配置）: {e}")
            # 使用默认配置
            self._use_default_config()

    def _use_default_config(self) -> None:
        """使用默认验证配置"""
        self._validation_config = {
            'pump_flow_rate': [
                {'validator_type': 'range', 'params': {'min': 0, 'max': 10000}},
                {'validator_type': 'non_negative', 'params': {}}
            ],
            'pump_head': [
                {'validator_type': 'range', 'params': {'min': 0, 'max': 500}},
                {'validator_type': 'non_negative', 'params': {}}
            ],
            'pump_outlet_pressure': [
                {'validator_type': 'range', 'params': {'min': 0, 'max': 10}},
                {'validator_type': 'non_negative', 'params': {}}
            ]
        }

    def validate_range(
        self,
        values: np.ndarray,
        min_val: float,
        max_val: float
    ) -> Tuple[np.ndarray, List[str]]:
        """
        范围验证

        Args:
            values: 待验证的值数组
            min_val: 最小值
            max_val: 最大值

        Returns:
            (有效性掩码, 错误信息列表)
        """
        mask = (values >= min_val) & (values <= max_val)
        errors = []

        if not mask.all():
            invalid_count = (~mask).sum()
            errors.append(f"范围验证失败：{invalid_count} 个值超出范围 [{min_val}, {max_val}]")

        return mask, errors

    def validate_non_negative(
        self,
        values: np.ndarray
    ) -> Tuple[np.ndarray, List[str]]:
        """
        非负验证

        Args:
            values: 待验证的值数组

        Returns:
            (有效性掩码, 错误信息列表)
        """
        mask = values >= 0
        errors = []

        if not mask.all():
            invalid_count = (~mask).sum()
            errors.append(f"非负验证失败：{invalid_count} 个值为负数")

        return mask, errors

    def validate_not_nan(
        self,
        values: np.ndarray
    ) -> Tuple[np.ndarray, List[str]]:
        """
        NaN验证

        Args:
            values: 待验证的值数组

        Returns:
            (有效性掩码, 错误信息列表)
        """
        mask = ~np.isnan(values)
        errors = []

        if not mask.all():
            invalid_count = (~mask).sum()
            errors.append(f"NaN验证失败：{invalid_count} 个值为NaN")

        return mask, errors

    def validate_not_inf(
        self,
        values: np.ndarray
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Inf验证

        Args:
            values: 待验证的值数组

        Returns:
            (有效性掩码, 错误信息列表)
        """
        mask = ~np.isinf(values)
        errors = []

        if not mask.all():
            invalid_count = (~mask).sum()
            errors.append(f"Inf验证失败：{invalid_count} 个值为Inf")

        return mask, errors

    def validate_efficiency(
        self,
        efficiency: np.ndarray,
        strict_mode: bool = False
    ) -> Tuple[np.ndarray, List[str], List[str]]:
        """
        效率验证

        验证效率值在0-100%范围内，并检查是否符合水泵特性。

        Args:
            efficiency: 效率值数组（百分比，0-100）
            strict_mode: 严格模式（警告也视为错误）

        Returns:
            (有效性掩码, 错误信息列表, 警告信息列表)
        """
        mask = np.ones(len(efficiency), dtype=bool)
        errors = []
        warnings = []

        # 1. 基本范围验证（0-100%）
        valid_range = (efficiency >= 0) & (efficiency <= 100)
        if not valid_range.all():
            invalid_count = (~valid_range).sum()
            errors.append(f"效率超出范围[0, 100]%：{invalid_count} 个值")
            mask &= valid_range

        # 2. 合理性验证（通常在30-95%）
        reasonable_range = (efficiency >= 30) & (efficiency <= 95)
        if not reasonable_range.all():
            low_count = ((efficiency < 30) & (efficiency >= 0)).sum()
            high_count = ((efficiency > 95) & (efficiency <= 100)).sum()

            if low_count > 0:
                warnings.append(f"效率偏低：{low_count} 个值 < 30%")
            if high_count > 0:
                warnings.append(f"效率偏高：{high_count} 个值 > 95%")

            if strict_mode:
                mask &= reasonable_range

        # 3. 异常值检测（<10%或>98%）
        extreme_low = (efficiency < 10) & (efficiency >= 0)
        extreme_high = (efficiency > 98) & (efficiency <= 100)

        if extreme_low.any():
            extreme_low_count = extreme_low.sum()
            warnings.append(f"效率异常低：{extreme_low_count} 个值 < 10%（可能设备故障）")

        if extreme_high.any():
            extreme_high_count = extreme_high.sum()
            warnings.append(f"效率异常高：{extreme_high_count} 个值 > 98%（不符合实际）")

        return mask, errors, warnings

    def validate_power_flow_head_consistency(
        self,
        flow_rate: np.ndarray,  # m³/h
        head: np.ndarray,  # m
        power: np.ndarray,  # kW
        efficiency: np.ndarray = None,  # %
        power_type: str = 'hydraulic',  # 'hydraulic', 'shaft', 'electric'
        tolerance: float = 0.15  # 15% tolerance
    ) -> Tuple[np.ndarray, List[str], List[str]]:
        """
        功率与流量扬程匹配验证

        验证水力功率公式：P_h = ρ × g × Q × H / 3600

        Args:
            flow_rate: 流量（m³/h）
            head: 扬程（m）
            power: 功率（kW）
            efficiency: 效率（%，可选）
            power_type: 功率类型（'hydraulic', 'shaft', 'electric'）
            tolerance: 允许误差（默认15%）

        Returns:
            (有效性掩码, 错误信息列表, 警告信息列表)
        """
        mask = np.ones(len(flow_rate), dtype=bool)
        errors = []
        warnings = []

        # 物理常数（验证器中使用标准值，不从数据库读取）
        # 注意：计算方法中的物理常数必须从数据库读取，验证器中使用标准值进行验证
        rho = 1000.0  # 水密度 kg/m³（标准值，20°C）
        g = 9.80665  # 重力加速度 m/s²（标准值）

        # 计算理论水力功率（kW）
        P_hydraulic = (rho * g * flow_rate * head) / 3600000.0

        # 根据功率类型调整
        if power_type == 'hydraulic':
            P_expected = P_hydraulic
        elif power_type == 'shaft':
            if efficiency is None:
                warnings.append("轴功率验证需要效率值，跳过验证")
                return mask, errors, warnings
            P_expected = P_hydraulic / (efficiency / 100.0)
        elif power_type == 'electric':
            if efficiency is None:
                warnings.append("电功率验证需要效率值，跳过验证")
                return mask, errors, warnings
            # 假设电机效率为95%
            motor_efficiency = 0.95
            P_expected = P_hydraulic / (efficiency / 100.0) / motor_efficiency
        else:
            errors.append(f"未知的功率类型: {power_type}")
            return mask, errors, warnings

        # 计算相对误差
        valid_points = (P_expected > 0) & ~np.isnan(P_expected) & ~np.isnan(power)
        if not valid_points.any():
            warnings.append("没有有效数据点进行功率一致性验证")
            return mask, errors, warnings

        # 使用np.divide避免除零警告
        with np.errstate(divide='ignore', invalid='ignore'):
            relative_error = np.abs(power - P_expected) / P_expected
        # 将无效值设为0
        relative_error = np.nan_to_num(relative_error, nan=0.0, posinf=0.0, neginf=0.0)

        # 验证误差在容忍范围内
        within_tolerance = relative_error <= tolerance

        if not within_tolerance[valid_points].all():
            exceed_count = (~within_tolerance[valid_points]).sum()
            max_error = relative_error[valid_points].max()
            errors.append(
                f"功率不一致：{exceed_count} 个值超出容忍范围±{tolerance*100:.0f}%，"
                f"最大误差{max_error*100:.1f}%"
            )
            mask[valid_points] &= within_tolerance[valid_points]

        # 警告：误差在10-15%之间
        warning_threshold = tolerance * 0.67  # 10%
        moderate_error = (relative_error > warning_threshold) & (relative_error <= tolerance)
        if moderate_error[valid_points].any():
            moderate_count = moderate_error[valid_points].sum()
            warnings.append(
                f"功率偏差较大：{moderate_count} 个值误差在"
                f"{warning_threshold*100:.0f}-{tolerance*100:.0f}%之间"
            )

        return mask, errors, warnings

    def validate_pressure(
        self,
        pressure: np.ndarray,  # MPa
        pressure_type: str = 'outlet',  # 'outlet', 'inlet', 'differential'
        rated_pressure: float = None,  # MPa
        tolerance: float = 0.2  # 20% tolerance
    ) -> Tuple[np.ndarray, List[str], List[str]]:
        """
        压力合理性验证

        Args:
            pressure: 压力值（MPa）
            pressure_type: 压力类型
            rated_pressure: 额定压力（MPa，可选）
            tolerance: 允许超出额定值的比例

        Returns:
            (有效性掩码, 错误信息列表, 警告信息列表)
        """
        mask = np.ones(len(pressure), dtype=bool)
        errors = []
        warnings = []

        # 1. 基本验证：压力为正数（进口压力可以为负表压）
        if pressure_type == 'inlet':
            # 进口压力可以为负（真空）
            valid_range = pressure >= -0.1  # 允许-0.1 MPa（真空）
        else:
            # 出口压力和压差必须为正
            valid_range = pressure >= 0

        if not valid_range.all():
            invalid_count = (~valid_range).sum()
            errors.append(f"压力值异常：{invalid_count} 个值超出合理范围")
            mask &= valid_range

        # 2. 额定压力验证
        if rated_pressure is not None:
            max_allowed = rated_pressure * (1 + tolerance)
            exceed_rated = pressure > max_allowed

            if exceed_rated.any():
                exceed_count = exceed_rated.sum()
                max_pressure = pressure[exceed_rated].max()
                errors.append(
                    f"压力超出额定值：{exceed_count} 个值 > {max_allowed:.2f} MPa，"
                    f"最大值{max_pressure:.2f} MPa"
                )
                mask &= ~exceed_rated

            # 警告：接近额定值（90-100%）
            near_rated = (pressure > rated_pressure * 0.9) & (pressure <= max_allowed)
            if near_rated.any():
                near_count = near_rated.sum()
                warnings.append(f"压力接近额定值：{near_count} 个值 > {rated_pressure*0.9:.2f} MPa")

        # 3. 异常高压检测（>2.0 MPa通常异常）
        if pressure_type == 'outlet':
            extreme_high = pressure > 2.0
            if extreme_high.any():
                extreme_count = extreme_high.sum()
                warnings.append(f"压力异常高：{extreme_count} 个值 > 2.0 MPa")

        return mask, errors, warnings

    def validate_speed(
        self,
        speed: np.ndarray,  # rpm
        rated_speed: float = None,  # rpm
        frequency: np.ndarray = None,  # Hz
        rated_frequency: float = 50.0,  # Hz
        tolerance: float = 0.2  # 20% tolerance
    ) -> Tuple[np.ndarray, List[str], List[str]]:
        """
        转速合理性验证

        Args:
            speed: 转速（rpm）
            rated_speed: 额定转速（rpm，可选）
            frequency: 频率（Hz，可选）
            rated_frequency: 额定频率（Hz）
            tolerance: 允许超出额定值的比例

        Returns:
            (有效性掩码, 错误信息列表, 警告信息列表)
        """
        mask = np.ones(len(speed), dtype=bool)
        errors = []
        warnings = []

        # 1. 基本验证：转速为正数
        valid_positive = speed > 0
        if not valid_positive.all():
            invalid_count = (~valid_positive).sum()
            errors.append(f"转速必须为正数：{invalid_count} 个值 ≤ 0")
            mask &= valid_positive

        # 2. 额定转速验证
        if rated_speed is not None:
            min_allowed = rated_speed * (1 - tolerance)
            max_allowed = rated_speed * (1 + tolerance)

            within_range = (speed >= min_allowed) & (speed <= max_allowed)
            if not within_range.all():
                exceed_count = (~within_range).sum()
                errors.append(
                    f"转速超出额定范围：{exceed_count} 个值不在"
                    f"[{min_allowed:.0f}, {max_allowed:.0f}] rpm"
                )
                mask &= within_range

            # 警告：转速过低（<60%额定）
            too_low = (speed < rated_speed * 0.6) & (speed > 0)
            if too_low.any():
                low_count = too_low.sum()
                warnings.append(f"转速过低：{low_count} 个值 < {rated_speed*0.6:.0f} rpm")

        # 3. 频率-转速一致性验证
        if frequency is not None and rated_speed is not None:
            expected_speed = (frequency / rated_frequency) * rated_speed
            speed_error = np.abs(speed - expected_speed) / expected_speed

            valid_points = ~np.isnan(speed_error)
            inconsistent = (speed_error > 0.05) & valid_points  # 5% tolerance

            if inconsistent.any():
                inconsistent_count = inconsistent.sum()
                warnings.append(
                    f"转速与频率不一致：{inconsistent_count} 个值误差 > 5%"
                )

        return mask, errors, warnings

    def validate_torque(
        self,
        torque: np.ndarray,  # N·m
        power: np.ndarray = None,  # kW
        speed: np.ndarray = None,  # rpm
        rated_torque: float = None,  # N·m
        tolerance: float = 0.15  # 15% tolerance
    ) -> Tuple[np.ndarray, List[str], List[str]]:
        """
        扭矩合理性验证

        验证扭矩与功率和转速的关系：T = P / ω = P × 9549 / n

        Args:
            torque: 扭矩（N·m）
            power: 功率（kW，可选）
            speed: 转速（rpm，可选）
            rated_torque: 额定扭矩（N·m，可选）
            tolerance: 允许误差

        Returns:
            (有效性掩码, 错误信息列表, 警告信息列表)
        """
        mask = np.ones(len(torque), dtype=bool)
        errors = []
        warnings = []

        # 1. 基本验证：扭矩为正数
        valid_positive = torque > 0
        if not valid_positive.all():
            invalid_count = (~valid_positive).sum()
            errors.append(f"扭矩必须为正数：{invalid_count} 个值 ≤ 0")
            mask &= valid_positive

        # 2. 功率-转速-扭矩一致性验证
        if power is not None and speed is not None:
            # T = P × 9549 / n （P单位kW，n单位rpm，T单位N·m）
            expected_torque = power * 9549.0 / speed

            valid_points = (speed > 0) & ~np.isnan(expected_torque) & ~np.isnan(torque)
            if valid_points.any():
                relative_error = np.abs(torque - expected_torque) / expected_torque

                inconsistent = (relative_error > tolerance) & valid_points
                if inconsistent.any():
                    inconsistent_count = inconsistent.sum()
                    max_error = relative_error[valid_points].max()
                    errors.append(
                        f"扭矩不一致：{inconsistent_count} 个值与功率/转速不匹配，"
                        f"最大误差{max_error*100:.1f}%"
                    )
                    mask[valid_points] &= ~inconsistent[valid_points]

                # 警告：误差在10-15%之间
                warning_threshold = tolerance * 0.67
                moderate_error = (relative_error > warning_threshold) & (relative_error <= tolerance) & valid_points
                if moderate_error.any():
                    moderate_count = moderate_error.sum()
                    warnings.append(
                        f"扭矩偏差较大：{moderate_count} 个值误差在"
                        f"{warning_threshold*100:.0f}-{tolerance*100:.0f}%之间"
                    )

        # 3. 额定扭矩验证
        if rated_torque is not None:
            max_allowed = rated_torque * (1 + tolerance)
            exceed_rated = torque > max_allowed

            if exceed_rated.any():
                exceed_count = exceed_rated.sum()
                max_torque = torque[exceed_rated].max()
                errors.append(
                    f"扭矩超出额定值：{exceed_count} 个值 > {max_allowed:.1f} N·m，"
                    f"最大值{max_torque:.1f} N·m"
                )
                mask &= ~exceed_rated

        return mask, errors, warnings

    def validate(
        self,
        metric_key: str,
        values: np.ndarray,
        context: Dict = None,
        strict_mode: bool = False
    ) -> Tuple[bool, np.ndarray, List[str], List[str]]:
        """
        综合验证

        Args:
            metric_key: 指标键
            values: 待验证的值数组
            context: 上下文字典（可选，包含相关数据用于物理规律验证）
            strict_mode: 严格模式（警告也视为错误）

        Returns:
            (是否全部通过, 有效性掩码, 错误信息列表, 警告信息列表)

        Context可包含的字段：
            - flow_rate: 流量（用于功率验证）
            - head: 扬程（用于功率验证）
            - power: 功率（用于扭矩验证）
            - speed: 转速（用于扭矩验证）
            - efficiency: 效率（用于功率验证）
            - frequency: 频率（用于转速验证）
            - rated_*: 额定值

        Example:
            >>> is_valid, mask, errors, warnings = validator.validate(
            ...     'pump_flow_rate',
            ...     np.array([100.0, -10.0, 120.0])
            ... )
            >>> print(is_valid)
            False
            >>> print(mask)
            [True False True]
            >>> print(errors)
            ['非负验证失败：1 个值为负数']
        """
        if context is None:
            context = {}

        logger.info(
            "[流程-开始] [结果验证]",
            extra={
                "extra_data": {
                    "指标": metric_key,
                    "数据点数": len(values),
                    "严格模式": strict_mode
                }
            }
        )

        # 初始化掩码（全部有效）
        mask = np.ones(len(values), dtype=bool)
        all_errors = []
        all_warnings = []

        # 基本验证（NaN和Inf）
        nan_mask, nan_errors = self.validate_not_nan(values)
        mask &= nan_mask
        all_errors.extend(nan_errors)

        inf_mask, inf_errors = self.validate_not_inf(values)
        mask &= inf_mask
        all_errors.extend(inf_errors)

        # 物理规律验证（根据指标类型）
        if 'efficiency' in metric_key:
            eff_mask, eff_errors, eff_warnings = self.validate_efficiency(
                values, strict_mode=strict_mode
            )
            mask &= eff_mask
            all_errors.extend(eff_errors)
            all_warnings.extend(eff_warnings)

            logger.debug(
                "[验证-规则] [效率验证]",
                extra={
                    "extra_data": {
                        "指标": metric_key,
                        "有效数据": int(eff_mask.sum()),
                        "错误数": len(eff_errors),
                        "警告数": len(eff_warnings)
                    }
                }
            )

        elif 'pressure' in metric_key:
            pressure_type = 'outlet' if 'outlet' in metric_key else 'inlet'
            rated_pressure = context.get('rated_pressure')
            press_mask, press_errors, press_warnings = self.validate_pressure(
                values, pressure_type=pressure_type, rated_pressure=rated_pressure
            )
            mask &= press_mask
            all_errors.extend(press_errors)
            all_warnings.extend(press_warnings)

        elif 'speed' in metric_key:
            rated_speed = context.get('rated_speed')
            frequency = context.get('frequency')
            speed_mask, speed_errors, speed_warnings = self.validate_speed(
                values, rated_speed=rated_speed, frequency=frequency
            )
            mask &= speed_mask
            all_errors.extend(speed_errors)
            all_warnings.extend(speed_warnings)

        elif 'torque' in metric_key:
            power = context.get('power')
            speed = context.get('speed')
            rated_torque = context.get('rated_torque')
            torque_mask, torque_errors, torque_warnings = self.validate_torque(
                values, power=power, speed=speed, rated_torque=rated_torque
            )
            mask &= torque_mask
            all_errors.extend(torque_errors)
            all_warnings.extend(torque_warnings)

        elif 'power' in metric_key:
            flow_rate = context.get('flow_rate')
            head = context.get('head')
            efficiency = context.get('efficiency')

            if flow_rate is not None and head is not None:
                power_type = 'hydraulic' if 'hydraulic' in metric_key else 'shaft'
                power_mask, power_errors, power_warnings = self.validate_power_flow_head_consistency(
                    flow_rate, head, values, efficiency=efficiency, power_type=power_type
                )
                mask &= power_mask
                all_errors.extend(power_errors)
                all_warnings.extend(power_warnings)

        # 获取验证配置（基本范围验证）
        if metric_key in self._validation_config:
            validators = self._validation_config[metric_key]

            logger.debug(
                "[验证-规则] [范围检查]",
                extra={
                    "extra_data": {
                        "指标": metric_key,
                        "规则数": len(validators),
                        "当前有效数据": int(mask.sum())
                    }
                }
            )

            # 执行配置的验证
            for validator_config in validators:
                validator_type = validator_config['validator_type']
                params = validator_config['params']

                if validator_type == 'range':
                    min_val = params.get('min', -np.inf)
                    max_val = params.get('max', np.inf)
                    range_mask, range_errors = self.validate_range(values, min_val, max_val)
                    mask &= range_mask
                    all_errors.extend(range_errors)

                elif validator_type == 'non_negative':
                    nn_mask, nn_errors = self.validate_non_negative(values)
                    mask &= nn_mask
                    all_errors.extend(nn_errors)

        # 特性曲线验证（如果启用且有必要的上下文）
        use_characteristic_curve = context.get('use_characteristic_curve', True)
        if use_characteristic_curve and 'device_id' in context and 'flow_rate' in context:
            curve_valid, curve_mask, curve_errors, curve_warnings = self.validate_against_characteristic_curve(
                metric_key=metric_key,
                values=values,
                context=context,
                tolerance=context.get('curve_tolerance', 0.1)
            )
            # 特性曲线验证作为额外检查，不强制要求通过
            # 只记录警告，不影响mask
            all_warnings.extend(curve_warnings)
            if curve_errors:
                all_warnings.extend([f"[特性曲线] {e}" for e in curve_errors])

        # 严格模式：警告也视为错误
        if strict_mode and all_warnings:
            all_errors.extend([f"[警告→错误] {w}" for w in all_warnings])
            all_warnings = []

        is_valid = mask.all() and (not strict_mode or not all_warnings)

        if is_valid:
            logger.info(
                "[流程-完成] [验证通过]",
                extra={
                    "extra_data": {
                        "指标": metric_key,
                        "数据点数": len(values),
                        "有效率": "100%"
                    }
                }
            )
        else:
            invalid_count = (~mask).sum()
            valid_rate = (len(values) - invalid_count) / len(values) if len(values) > 0 else 0
            logger.error(
                "[流程-完成] [验证失败]",
                extra={
                    "extra_data": {
                        "指标": metric_key,
                        "无效数据": f"{invalid_count}/{len(values)}",
                        "有效率": f"{valid_rate:.1%}",
                        "错误": all_errors,
                        "警告": all_warnings
                    }
                }
            )


        return is_valid, mask, all_errors, all_warnings

    def refresh(
        self,
        station_id: int = None,
        device_id: int = None
    ) -> None:
        """
        刷新验证配置

        Args:
            station_id: 站点ID（可选）
            device_id: 设备ID（可选）
        """
        logger.info("PhysicsValidator 刷新")
        self._validation_config.clear()
        self._config_cache_time = 0
        self._load_config_from_db(station_id=station_id, device_id=device_id, force_reload=True)

    def get_config_for_metric(self, metric_key: str) -> List[Dict]:
        """
        获取指定指标的验证配置

        Args:
            metric_key: 指标键

        Returns:
            验证配置列表
        """
        return self._validation_config.get(metric_key, [])

    def validate_against_characteristic_curve(
        self,
        metric_key: str,
        values: np.ndarray,
        context: Dict,
        tolerance: float = 0.1
    ) -> Tuple[bool, np.ndarray, List[str], List[str]]:

        """
        基于特性曲线验证计算结果

        Args:
            metric_key: 指标名称
            values: 计算值数组
            context: 上下文字典，必须包含：
                - device_id: 设备ID
                - flow_rate: 流量数组（与values长度相同）
                可选：
                - speed: 转速
                - frequency: 频率
            tolerance: 容忍度（相对误差，默认0.1即10%）

        Returns:
            (是否全部有效, 有效性掩码, 错误列表, 警告列表)
        """
        errors = []
        warnings = []

        # 检查必需的上下文参数
        if 'device_id' not in context:
            errors.append("缺少device_id参数")
            return False, np.zeros(len(values), dtype=bool), errors, warnings

        if 'flow_rate' not in context:
            errors.append("缺少flow_rate参数")
            return False, np.zeros(len(values), dtype=bool), errors, warnings

        device_id = context['device_id']
        flow_rates = context['flow_rate']
        speed = context.get('speed')
        frequency = context.get('frequency')

        # 确定曲线类型
        curve_type_map = {
            'pump_head': 'Q-H',
            'pump_shaft_power': 'Q-P',
            'pump_efficiency': 'Q-eta',
            'main_pipeline_outlet_head': 'Q-H',  # 站级扬程也可以用Q-H验证
        }

        curve_type = curve_type_map.get(metric_key)

        if curve_type is None:
            # 不支持的指标类型，跳过特性曲线验证
            logger.debug(f"指标 {metric_key} 不支持特性曲线验证")
            return True, np.ones(len(values), dtype=bool), errors, warnings

        try:
            # 加载特性曲线
            curves_data = self._curve_manager.load_curves(
                device_id=device_id,
                curve_type=curve_type,
                speed=speed,
                frequency=frequency
            )

            logger.info(
                f"开始特性曲线验证: {metric_key} ({curve_type})",
                extra={
                    "metric": metric_key,
                    "curve_type": curve_type,
                    "device_id": device_id,
                    "points": len(values)
                }
            )

            # 验证每个数据点
            mask = np.ones(len(values), dtype=bool)
            deviations = []

            for i, (flow_rate, actual_value) in enumerate(zip(flow_rates, values)):
                # 跳过NaN值
                if np.isnan(flow_rate) or np.isnan(actual_value):
                    mask[i] = False
                    continue

                # 验证点
                is_valid, deviation = self._curve_manager.validate_point(
                    curve_type=curve_type,
                    flow_rate=flow_rate,
                    actual_value=actual_value,
                    curves_data=curves_data,
                    tolerance=tolerance
                )

                mask[i] = is_valid
                deviations.append(deviation)

                if not is_valid:
                    errors.append(
                        f"数据点 {i}: 流量={flow_rate:.1f}, "
                        f"实际值={actual_value:.2f}, 偏差={deviation:.1%} > {tolerance:.1%}"
                    )

            # 统计结果
            valid_count = mask.sum()
            total_count = len(values)
            valid_rate = valid_count / total_count if total_count > 0 else 0

            if deviations:
                avg_deviation = np.mean(deviations)
                max_deviation = np.max(deviations)

                logger.info(
                    f"特性曲线验证完成: {valid_count}/{total_count} 有效 ({valid_rate:.1%}), "
                    f"平均偏差={avg_deviation:.1%}, 最大偏差={max_deviation:.1%}",
                    extra={
                        "valid_count": valid_count,
                        "total_count": total_count,
                        "valid_rate": valid_rate,
                        "avg_deviation": avg_deviation,
                        "max_deviation": max_deviation
                    }
                )

                # 添加警告
                if valid_rate < 0.9:
                    warnings.append(
                        f"有效率较低: {valid_rate:.1%} < 90%"
                    )

                if max_deviation > tolerance * 2:
                    warnings.append(
                        f"最大偏差过大: {max_deviation:.1%} > {tolerance*2:.1%}"
                    )

            is_all_valid = valid_count == total_count

            return is_all_valid, mask, errors, warnings

        except ValueError as e:
            # 没有找到曲线数据，跳过验证
            logger.warning(f"特性曲线验证跳过: {e}")
            warnings.append(f"特性曲线验证跳过: {str(e)}")
            return True, np.ones(len(values), dtype=bool), errors, warnings

        except Exception as e:
            # 其他错误
            logger.error(f"特性曲线验证失败: {e}", exc_info=True)
            errors.append(f"特性曲线验证失败: {str(e)}")
            return False, np.zeros(len(values), dtype=bool), errors, warnings



    # ------------------------- 统一签名适配层（保持向后兼容） -------------------------
    def validate_ctx(
        self,
        metric_key: str,
        values: np.ndarray,
        ctx: CalculationContext,
    ) -> Tuple[bool, np.ndarray, List[str], List[str]]:
        """
        基于统一领域上下文的综合验证适配层。

        Args:
            metric_key: 指标键
            values: 待验证的值数组
            ctx: 统一 CalculationContext
        Returns:
            (是否全部通过, 有效性掩码, 错误信息列表, 警告信息列表)
        """
        legacy_context: Dict = {
            "station_id": ctx.station_id,
            "device_id": ctx.device_id,
            "strict_mode": ctx.strict_mode,
        }
        # 合并质量过滤与额外上下文（不覆盖核心键）
        for src in (ctx.quality_filters or {}, ctx.extra or {}):
            for k, v in src.items():
                if k not in legacy_context:
                    legacy_context[k] = v

        return self.validate(
            metric_key=metric_key,
            values=values,
            context=legacy_context,
            strict_mode=ctx.strict_mode,
        )
