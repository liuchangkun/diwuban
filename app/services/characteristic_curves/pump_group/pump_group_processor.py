"""泵组处理器 (app.services.characteristic_curves.pump_group.pump_group_processor)

泵组曲线处理的核心编排器，负责识别泵组类型并调用相应的处理策略。

核心功能：
- 识别泵组类型（同构/异构/混合）
- 检查单泵曲线是否已注册
- 根据策略选择处理方法
- 调用ParallelSynthesizer合成曲线
- 调用SystemCorrectionModel学习修正系数

版本: v1.0
创建日期: 2025-12-14
参考文档: 07_泵组处理层.md 第2节
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from app.adapters.db import get_connection
from app.services.characteristic_curves.core.data_structures import (
    GroupProcessingStrategy,
    GroupFitResult,
)
from app.services.characteristic_curves.shared.exceptions import (
    CurveFittingError,
    InsufficientDataError,
    MissingCurveError,
    P0FittingRetryExhaustedError,
    CurveInconsistencyError,
)
from .frequency_data_provider import FrequencyDataProvider
from .parallel_synthesizer import ParallelSynthesizer
from .system_correction_model import SystemCorrectionModel


logger = logging.getLogger(__name__)


class PumpGroupProcessor:
    """泵组处理器

    职责：
    1. 识别泵组类型（同构/异构/混合）
    2. 根据策略选择处理方法
    3. 调用 ParallelSynthesizer 合成曲线
    4. 调用 SystemCorrectionModel 学习修正系数
    """

    def __init__(
        self,
        parallel_synthesizer: Optional[ParallelSynthesizer] = None,
        correction_model: Optional[SystemCorrectionModel] = None,
        power_diff_threshold: float = 0.1,
        freq_diff_threshold: float = 0.02
    ):
        """初始化泵组处理器

        Args:
            parallel_synthesizer: 并联合成器实例
            correction_model: 系统修正模型实例
            power_diff_threshold: 功率差异阈值（默认10%）
            freq_diff_threshold: 频率差异阈值（默认2%）
        """
        self._synthesizer = parallel_synthesizer or ParallelSynthesizer()
        self._correction = correction_model or SystemCorrectionModel()
        self._freq_provider = FrequencyDataProvider()
        self._power_diff_threshold = power_diff_threshold
        self._freq_diff_threshold = freq_diff_threshold
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

        self._logger.info("[泵组处理器] 初始化完成")

    def identify_group_type(
        self,
        pump_infos: List[Dict[str, Any]]
    ) -> GroupProcessingStrategy:
        """识别泵组类型

        Args:
            pump_infos: 泵信息列表，每个包含 {'pump_id', 'rated_power', 'control_type'}

        Returns:
            GroupProcessingStrategy: 泵组类型

        Raises:
            ValueError: 纯SS泵组不支持

        决策树:
        1. 检查控制类型 → 纯SS时抛异常（不支持）
        2. 混合(VFD+SS)时进入混合分支
        3. 混合分支内检查功率差异 → 差异≥10%返回MIXED_HETEROGENEOUS
        4. 纯VFD时，先检查频率差异 → 差异≥2%返回VFD_HETEROGENEOUS_FREQ
        5. 纯VFD功率差异≥10%返回HETEROGENEOUS_GROUP
        6. 纯VFD功率差异<10%返回HOMOGENEOUS_GROUP
        """
        # 步骤1: 检查是否有混合控制类型
        control_types = set(p.get('control_type', 'VFD') for p in pump_infos)
        is_mixed = len(control_types) > 1

        # 纯SS泵组不支持
        if control_types == {'SS'}:
            raise ValueError(
                f"不支持纯软启泵组：软启泵必须与变频泵混合使用。"
                f"泵组成员: {[p['pump_id'] for p in pump_infos]}"
            )

        # 步骤2: 计算功率差异
        powers = [p.get('rated_power', 0) for p in pump_infos]
        if not powers or max(powers) == 0:
            power_diff = 0.0
        else:
            power_diff = (max(powers) - min(powers)) / max(powers)

        is_heterogeneous = power_diff >= self._power_diff_threshold

        # 步骤3: 决策
        if is_mixed:
            # VFD + SS 混合
            if is_heterogeneous:
                self._logger.info(
                    f"[泵组识别] 混合控制类型 + 功率差异{power_diff:.1%}≥10%，"
                    f"判定为 MIXED_HETEROGENEOUS"
                )
                return GroupProcessingStrategy.MIXED_HETEROGENEOUS
            else:
                self._logger.info(
                    "[泵组识别] 混合控制类型 + 功率相近，判定为 MIXED_GROUP"
                )
                return GroupProcessingStrategy.MIXED_GROUP
        else:
            # 纯VFD泵组
            pump_ids = [p['pump_id'] for p in pump_infos]

            # 尝试获取频率差异
            try:
                freq_diff = self._freq_provider.get_frequency_diff_ratio(
                    pump_ids)
                if freq_diff >= self._freq_diff_threshold:
                    self._logger.info(
                        f"[泵组识别] 全VFD泵组频率差异 {freq_diff:.1%} ≥ 2%，"
                        f"判定为 VFD_HETEROGENEOUS_FREQ"
                    )
                    return GroupProcessingStrategy.VFD_HETEROGENEOUS_FREQ
            except Exception as e:
                self._logger.debug(f"[泵组识别] 无法获取频率差异: {e}")

            if is_heterogeneous:
                self._logger.info(
                    f"[泵组识别] 功率差异 {power_diff:.1%} ≥ {self._power_diff_threshold:.0%}，"
                    f"判定为 HETEROGENEOUS_GROUP"
                )
                return GroupProcessingStrategy.HETEROGENEOUS_GROUP
            else:
                self._logger.info(
                    f"[泵组识别] 功率差异 {power_diff:.1%} < {self._power_diff_threshold:.0%}，"
                    f"判定为 HOMOGENEOUS_GROUP"
                )
                return GroupProcessingStrategy.HOMOGENEOUS_GROUP

    def process(
        self,
        station_id: int,
        pump_infos: List[Dict[str, Any]],
        curve_type: str = 'qh',
        auto_trigger_p0: bool = False,
        max_p0_retries: int = 3
    ) -> GroupFitResult:
        """处理泵组曲线

        Args:
            station_id: 泵站ID
            pump_infos: 泵信息列表
            curve_type: 曲线类型
            auto_trigger_p0: 单泵曲线缺失时是否自动触发P0拟合
            max_p0_retries: P0拟合最大重试次数

        Returns:
            GroupFitResult: 泵组拟合结果

        Raises:
            MissingCurveError: 单泵曲线未注册且auto_trigger_p0=False
            P0FittingRetryExhaustedError: P0拟合重试次数耗尽
            InsufficientDataError: 数据不足
        """
        pump_ids = [p['pump_id'] for p in pump_infos]

        # 前置检查：验证所有单泵曲线是否已完成P0拟合
        missing_curves = self._check_single_pump_curves(pump_ids, curve_type)
        if missing_curves:
            if auto_trigger_p0:
                self._trigger_p0_fitting(
                    missing_curves, curve_type, max_p0_retries)
            else:
                raise MissingCurveError(
                    f"以下泵的{curve_type}曲线未完成P0拟合: {missing_curves}。"
                    f"请先完成单泵拟合，或设置auto_trigger_p0=True自动触发。",
                    missing_pump_ids=missing_curves
                )

        # 1. 识别泵组类型
        group_type = self.identify_group_type(pump_infos)

        self._logger.info(
            f"[泵组处理] station={station_id}, pumps={pump_ids}, type={group_type.value}"
        )

        # 2. 根据策略处理
        if group_type == GroupProcessingStrategy.HOMOGENEOUS_GROUP:
            return self._process_homogeneous_group(station_id, pump_infos, curve_type)
        elif group_type == GroupProcessingStrategy.HETEROGENEOUS_GROUP:
            return self._process_heterogeneous_group(station_id, pump_infos, curve_type)
        elif group_type == GroupProcessingStrategy.VFD_HETEROGENEOUS_FREQ:
            return self._process_vfd_heterogeneous_freq(station_id, pump_infos, curve_type)
        elif group_type == GroupProcessingStrategy.MIXED_HETEROGENEOUS:
            return self._process_mixed_heterogeneous_group(station_id, pump_infos, curve_type)
        else:  # MIXED_GROUP
            return self._process_mixed_group(station_id, pump_infos, curve_type)

    def _check_single_pump_curves(
        self,
        pump_ids: List[int],
        curve_type: str
    ) -> List[int]:
        """检查单泵曲线是否已注册

        检查顺序：
        1. 先检查内存缓存
        2. 内存未找到时再检查数据库，并加载到内存

        Args:
            pump_ids: 泵ID列表
            curve_type: 曲线类型

        Returns:
            List[int]: 未注册的泵ID列表
        """
        missing = []

        for pump_id in pump_ids:
            # 1. 先检查内存缓存
            if pump_id in self._synthesizer._pump_curves:
                continue

            # 2. 内存未找到，检查数据库
            try:
                with get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "SELECT id, method_name FROM curve_fit_results "
                            "WHERE device_id = %s AND curve_type = %s AND status = 'active' "
                            "ORDER BY created_at DESC LIMIT 1",
                            (pump_id, curve_type)
                        )
                        db_result = cursor.fetchone()

                if db_result:
                    # 数据库有记录，尝试加载到内存
                    self._logger.info(
                        f"[前置检查] 泵 {pump_id} 的 {curve_type} 曲线在数据库中找到，尝试加载"
                    )
                    if self._load_curve_from_db(pump_id, curve_type):
                        continue

                # 内存和数据库都未找到
                missing.append(pump_id)
                self._logger.warning(
                    f"[前置检查] 泵 {pump_id} 的 {curve_type} 曲线未注册"
                )
            except Exception as e:
                self._logger.warning(
                    f"[前置检查] 检查泵 {pump_id} 曲线时出错: {e}"
                )
                missing.append(pump_id)

        if missing:
            self._logger.error(
                f"[前置检查] 失败: {len(missing)}/{len(pump_ids)} 泵曲线未注册"
            )
        else:
            self._logger.info(
                f"[前置检查] 通过: 所有 {len(pump_ids)} 泵曲线已注册"
            )

        return missing

    def _load_curve_from_db(self, pump_id: int, curve_type: str) -> bool:
        """从数据库加载曲线到内存

        Args:
            pump_id: 泵ID
            curve_type: 曲线类型

        Returns:
            bool: 加载是否成功
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    # 查询拟合结果
                    cursor.execute(
                        "SELECT id, method_name FROM curve_fit_results "
                        "WHERE device_id = %s AND curve_type = %s AND status = 'active' "
                        "ORDER BY created_at DESC LIMIT 1",
                        (pump_id, curve_type)
                    )
                    result_row = cursor.fetchone()

                    if not result_row:
                        return False

                    result_id = result_row[0]

                    # 查询拟合系数
                    cursor.execute(
                        "SELECT param_key, param_value FROM curve_fit_params "
                        "WHERE result_id = %s AND param_category = 'fit' "
                        "ORDER BY param_key",
                        (result_id,)
                    )
                    params = {row[0]: row[1] for row in cursor.fetchall()}

                    # 查询额定功率
                    cursor.execute(
                        "SELECT value_numeric FROM device_rated_params "
                        "WHERE device_id = %s AND param_key = 'rated_power'",
                        (pump_id,)
                    )
                    power_row = cursor.fetchone()
                    rated_power = float(power_row[0]) if power_row else 55.0

            if not params:
                self._logger.warning(
                    f"[曲线加载] 泵 {pump_id} 的 {curve_type} 曲线无拟合系数"
                )
                return False

            # 构建曲线函数（假设是多项式）
            # 将系数转换为数组格式 [a0, a1, a2, ...]
            coeffs = []
            i = 0
            while f"a{i}" in params:
                coeffs.append(params[f"a{i}"])
                i += 1

            if not coeffs:
                # 尝试其他系数格式 (H0, K)
                if 'H0' in params and 'K' in params:
                    H0 = params['H0']
                    K = params['K']

                    def curve_func(Q):
                        return H0 - K * np.power(Q, 2)

                    def inverse_func(H):
                        if H > H0:
                            return 0
                        return np.sqrt((H0 - H) / K) if K > 0 else 0

                    H_max = H0
                else:
                    self._logger.warning(
                        f"[曲线加载] 泵 {pump_id} 的 {curve_type} 曲线系数格式未知"
                    )
                    return False
            else:
                # 多项式曲线
                coeffs_array = np.array(coeffs)

                def curve_func(Q):
                    return np.polyval(coeffs_array, Q)

                # 计算最大扬程（Q=0时）
                H_max = curve_func(0)

                def inverse_func(H):
                    # 简化的反函数实现
                    if H > H_max:
                        return 0
                    # 二分法求解
                    Q_low, Q_high = 0, 1000
                    for _ in range(50):
                        Q_mid = (Q_low + Q_high) / 2
                        H_mid = curve_func(Q_mid)
                        if H_mid > H:
                            Q_low = Q_mid
                        else:
                            Q_high = Q_mid
                    return Q_mid

            # 注册到合成器
            self._synthesizer.register_pump_curve(
                pump_id=pump_id,
                curve_func=curve_func,
                inverse_func=inverse_func,
                H_range=(0, H_max),
                rated_power=rated_power
            )

            self._logger.info(
                f"[曲线加载] 成功从数据库加载泵 {pump_id} 的 {curve_type} 曲线"
            )
            return True

        except Exception as e:
            self._logger.error(
                f"[曲线加载] 加载泵 {pump_id} 曲线失败: {e}"
            )
            return False

    def _trigger_p0_fitting(
        self,
        pump_ids: List[int],
        curve_type: str,
        max_retries: int = 3
    ) -> Dict[int, bool]:
        """自动触发P0单泵拟合

        Args:
            pump_ids: 需要拟合的泵ID列表
            curve_type: 曲线类型
            max_retries: 每台泵的最大重试次数

        Returns:
            Dict[int, bool]: {pump_id: success} 拟合结果

        Raises:
            P0FittingRetryExhaustedError: 当某台泵重试次数耗尽仍失败时抛出
        """
        self._logger.info(
            f"[自动P0] 开始触发 {len(pump_ids)} 台泵的P0拟合"
        )

        # 这里需要调用P0拟合管道，简化实现
        results: Dict[int, bool] = {}
        failed_pumps: List[Dict] = []

        for pump_id in pump_ids:
            # 实际实现应调用 CurveFittingPipeline
            # 这里仅记录失败
            results[pump_id] = False
            failed_pumps.append({
                "pump_id": pump_id,
                "retry_count": max_retries,
                "last_error": "P0拟合需手动执行"
            })

        if failed_pumps:
            error = P0FittingRetryExhaustedError(
                message=f"P0拟合失败: 需手动执行单泵拟合",
                pump_id=failed_pumps[0]["pump_id"],
                retry_count=max_retries,
                max_retries=max_retries,
                last_error=failed_pumps[0]["last_error"]
            )
            raise error

        return results

    def _get_system_head(self, station_id: int) -> float:
        """获取泵站的系统扬程

        Args:
            station_id: 泵站ID

        Returns:
            float: 系统扬程值（米）
        """
        sql = """
            SELECT fm.value * 10.2 AS H_system
            FROM fact_measurements fm
            JOIN dim_devices dd ON fm.device_id = dd.id
            WHERE dd.station_id = %(station_id)s
              AND fm.metric_id = (
                  SELECT id FROM dim_metric_config
                  WHERE metric_key = 'main_pipeline_outlet_pressure'
              )
              AND fm.value IS NOT NULL
            ORDER BY fm.ts_bucket DESC
            LIMIT 1
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, {'station_id': station_id})
                    result = cursor.fetchone()
                    if result:
                        return float(result[0])
        except Exception as e:
            self._logger.warning(f"[系统扬程] 查询失败: {e}")

        # 默认返回35m
        return 35.0

    def _extract_training_data(
        self,
        station_id: int,
        pump_ids: List[int]
    ) -> np.ndarray:
        """提取修正模型训练数据

        Args:
            station_id: 泵站ID
            pump_ids: 泵ID列表

        Returns:
            np.ndarray: 训练数据矩阵 [N, Q_total, H_theoretical, H_actual]
        """
        sql = """
            WITH metric_ids AS (
                SELECT
                    MAX(CASE WHEN metric_key = 'device_running' THEN id END) AS running_id,
                    MAX(CASE WHEN metric_key = 'pump_flow_rate' THEN id END) AS flow_id,
                    MAX(CASE WHEN metric_key = 'main_pipeline_outlet_pressure' THEN id END) AS pressure_id
                FROM dim_metric_config
            ),
            pump_metrics AS (
                SELECT
                    fm.ts_bucket,
                    fm.device_id,
                    MAX(CASE WHEN fm.metric_id = mi.running_id THEN fm.value END) AS running,
                    MAX(CASE WHEN fm.metric_id = mi.flow_id THEN fm.value END) AS flow
                FROM fact_measurements fm
                CROSS JOIN metric_ids mi
                JOIN dim_devices dd ON fm.device_id = dd.id
                WHERE dd.station_id = %(station_id)s
                  AND fm.device_id = ANY(%(pump_ids)s)
                  AND fm.ts_bucket >= NOW() - INTERVAL '90 days'
                  AND fm.metric_id IN (mi.running_id, mi.flow_id)
                GROUP BY fm.ts_bucket, fm.device_id
            ),
            station_pressure AS (
                SELECT
                    fm.ts_bucket,
                    fm.value * 10.2 AS H_actual
                FROM fact_measurements fm
                CROSS JOIN metric_ids mi
                JOIN dim_devices dd ON fm.device_id = dd.id
                WHERE dd.station_id = %(station_id)s
                  AND fm.metric_id = mi.pressure_id
                  AND fm.ts_bucket >= NOW() - INTERVAL '90 days'
                  AND fm.value > 0
            ),
            aggregated AS (
                SELECT
                    pm.ts_bucket,
                    COUNT(*) FILTER (WHERE pm.running = 1) AS N,
                    COALESCE(SUM(pm.flow) FILTER (WHERE pm.running = 1), 0) AS Q_total,
                    sp.H_actual
                FROM pump_metrics pm
                JOIN station_pressure sp ON pm.ts_bucket = sp.ts_bucket
                GROUP BY pm.ts_bucket, sp.H_actual
                HAVING COUNT(*) FILTER (WHERE pm.running = 1) >= 1
            )
            SELECT N, Q_total, H_actual, H_actual AS H_theoretical
            FROM aggregated
            WHERE Q_total > 0
            ORDER BY Q_total
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, {
                        'station_id': station_id,
                        'pump_ids': pump_ids
                    })
                    rows = cursor.fetchall()

            if not rows:
                self._logger.warning(f"[训练数据] 泵站 {station_id} 无历史数据")
                return np.array([])

            data = np.array([[r[0], r[1], r[2], r[3]] for r in rows])
            self._logger.info(
                f"[训练数据] 提取 {len(data)} 条记录，用于泵站 {station_id}"
            )
            return data

        except Exception as e:
            self._logger.error(f"[训练数据] 提取失败: {e}")
            return np.array([])

    def _process_homogeneous_group(
        self,
        station_id: int,
        pump_infos: List[Dict[str, Any]],
        curve_type: str
    ) -> GroupFitResult:
        """处理同构泵组

        策略：选择基准泵，Q_group = N × Q_base
        """
        pump_ids = [p['pump_id'] for p in pump_infos]
        n_pumps = len(pump_ids)

        # 选择基准泵（使用第一台）
        base_pump_id = pump_ids[0]

        # 1. 合成同构泵组曲线
        group_curve = self._synthesizer.synthesize_homogeneous(
            base_pump_id=base_pump_id,
            n_pumps=n_pumps
        )

        # 2. 提取训练数据并学习修正系数
        training_data = self._extract_training_data(station_id, pump_ids)
        if len(training_data) >= 100:
            self._correction.fit(station_id, pump_ids,
                                 training_data=training_data)

        return GroupFitResult(
            station_id=station_id,
            pump_combination=pump_ids,
            group_type=GroupProcessingStrategy.HOMOGENEOUS_GROUP,
            curve_type=curve_type,
            base_pump_id=base_pump_id,
            pump_count=n_pumps,
            valid_n_range=(1, n_pumps),
            correction_model=self._correction.to_dict() if self._correction.is_fitted else None,
            vfd_pump_ids=pump_ids,
            ss_pump_ids=[]
        )

    def _process_heterogeneous_group(
        self,
        station_id: int,
        pump_infos: List[Dict[str, Any]],
        curve_type: str
    ) -> GroupFitResult:
        """处理异构泵组

        策略：各泵独立曲线 + 并联合成
        """
        pump_ids = [p['pump_id'] for p in pump_infos]
        n_pumps = len(pump_ids)

        # 获取系统扬程和频率
        H_system = self._get_system_head(station_id)
        try:
            frequencies = self._freq_provider.get_latest_frequencies(pump_ids)
        except Exception:
            frequencies = None

        # 合成异构泵组
        synthesis_result = self._synthesizer.synthesize_heterogeneous(
            pump_ids=pump_ids,
            H_system=H_system,
            pump_frequencies=frequencies
        )

        self._logger.info(
            f"[异构处理] 合成结果: Q_total={synthesis_result.Q_total:.1f}, "
            f"H_system={synthesis_result.H_system:.1f}"
        )

        # 提取训练数据并学习修正系数
        training_data = self._extract_training_data(station_id, pump_ids)
        if len(training_data) >= 100:
            self._correction.fit(station_id, pump_ids,
                                 training_data=training_data)

        return GroupFitResult(
            station_id=station_id,
            pump_combination=pump_ids,
            group_type=GroupProcessingStrategy.HETEROGENEOUS_GROUP,
            curve_type=curve_type,
            pump_count=n_pumps,
            valid_n_range=(1, n_pumps),
            correction_model=self._correction.to_dict() if self._correction.is_fitted else None,
            vfd_pump_ids=pump_ids,
            ss_pump_ids=[]
        )

    def _process_vfd_heterogeneous_freq(
        self,
        station_id: int,
        pump_infos: List[Dict[str, Any]],
        curve_type: str
    ) -> GroupFitResult:
        """处理VFD频率异构泵组

        场景：全VFD泵组，但各泵实际运行频率不同（差异≥2%）
        """
        pump_ids = [p['pump_id'] for p in pump_infos]
        n_pumps = len(pump_ids)

        # 1. 获取各泵当前频率
        frequencies = self._freq_provider.get_latest_frequencies(pump_ids)
        self._logger.info(f"[VFD频率异构] 各泵频率: {frequencies}")

        # 2. 使用考虑频率的合成方法
        group_curve = self._synthesizer.synthesize_vfd_with_freq(
            pump_ids=pump_ids,
            frequencies=frequencies
        )

        # 3. 提取训练数据并学习修正系数
        training_data = self._extract_training_data(station_id, pump_ids)
        if len(training_data) >= 100:
            self._correction.fit(station_id, pump_ids,
                                 training_data=training_data)

        return GroupFitResult(
            station_id=station_id,
            pump_combination=pump_ids,
            group_type=GroupProcessingStrategy.VFD_HETEROGENEOUS_FREQ,
            curve_type=curve_type,
            pump_count=n_pumps,
            valid_n_range=(1, n_pumps),
            correction_model=self._correction.to_dict() if self._correction.is_fitted else None,
            vfd_pump_ids=pump_ids,
            ss_pump_ids=[]
        )

    def _process_mixed_group(
        self,
        station_id: int,
        pump_infos: List[Dict[str, Any]],
        curve_type: str
    ) -> GroupFitResult:
        """处理混合泵组（VFD + 软启）

        策略：分类处理 + 分类合成
        """
        pump_ids = [p['pump_id'] for p in pump_infos]
        n_pumps = len(pump_ids)

        # 1. 分类泵
        vfd_pumps = [p['pump_id']
                     for p in pump_infos if p.get('control_type') == 'VFD']
        ss_pumps = [p['pump_id']
                    for p in pump_infos if p.get('control_type') == 'SS']

        assert len(vfd_pumps) > 0, "混合泵组必须包含至少一台VFD泵"

        self._logger.info(f"[混合处理] VFD泵: {vfd_pumps}, 软启泵: {ss_pumps}")

        # 2. 获取VFD泵的当前频率
        pump_frequencies = self._freq_provider.get_latest_frequencies(
            vfd_pumps)

        # 3. 调用混合合成方法
        H_system = self._get_system_head(station_id)
        synthesis_result = self._synthesizer.synthesize_mixed(
            vfd_pump_ids=vfd_pumps,
            ss_pump_ids=ss_pumps,
            pump_frequencies=pump_frequencies,
            H_system=H_system
        )

        self._logger.info(
            f"[混合处理] 合成结果: Q_total={synthesis_result.Q_total:.1f}, "
            f"H_system={synthesis_result.H_system:.1f}"
        )

        # 4. 提取训练数据并学习修正系数（使用XGBoost）
        training_data = self._extract_training_data(station_id, pump_ids)
        if len(training_data) >= 100:
            self._correction.set_model_type('xgboost')
            self._correction.fit(station_id, pump_ids,
                                 training_data=training_data)

        return GroupFitResult(
            station_id=station_id,
            pump_combination=pump_ids,
            group_type=GroupProcessingStrategy.MIXED_GROUP,
            curve_type=curve_type,
            pump_count=n_pumps,
            valid_n_range=(1, n_pumps),
            correction_model=self._correction.to_dict() if self._correction.is_fitted else None,
            vfd_pump_ids=vfd_pumps,
            ss_pump_ids=ss_pumps
        )

    def _process_mixed_heterogeneous_group(
        self,
        station_id: int,
        pump_infos: List[Dict[str, Any]],
        curve_type: str
    ) -> GroupFitResult:
        """处理混合异构泵组

        场景：VFD+SS混合 且 功率差异≥10%
        """
        pump_ids = [p['pump_id'] for p in pump_infos]
        n_pumps = len(pump_ids)

        # 1. 分类泵
        vfd_infos = [p for p in pump_infos if p.get('control_type') == 'VFD']
        ss_infos = [p for p in pump_infos if p.get('control_type') == 'SS']

        vfd_pump_ids = [p['pump_id'] for p in vfd_infos]
        ss_pump_ids = [p['pump_id'] for p in ss_infos]

        # 2. 计算功率权重
        powers = {p['pump_id']: p['rated_power'] for p in pump_infos}
        total_power = sum(powers.values())
        power_weights = {pid: pwr / total_power for pid, pwr in powers.items()}

        # 3. 获取VFD频率
        pump_frequencies = {}
        if vfd_pump_ids:
            pump_frequencies = self._freq_provider.get_latest_frequencies(
                vfd_pump_ids)

        self._logger.info(
            f"[混合异构处理] VFD泵: {vfd_pump_ids}, SS泵: {ss_pump_ids}, "
            f"功率权重: {power_weights}"
        )

        # 4. 调用加权混合合成方法
        H_system = self._get_system_head(station_id)
        synthesis_result = self._synthesizer.synthesize_mixed_weighted(
            pump_infos=pump_infos,
            pump_frequencies=pump_frequencies,
            H_system=H_system
        )

        self._logger.info(
            f"[混合异构处理] 合成结果: Q_total={synthesis_result.Q_total:.1f}, "
            f"H_system={synthesis_result.H_system:.1f}"
        )

        # 5. 准备扩展特征
        extended_features = {
            'power_weights': power_weights,
            'power_max': max(powers.values()),
            'power_min': min(powers.values()),
            'power_ratio': max(powers.values()) / min(powers.values())
        }

        # 6. 提取训练数据并学习修正系数（使用XGBoost）
        training_data = self._extract_training_data(station_id, pump_ids)
        if len(training_data) >= 100:
            self._correction.set_model_type('xgboost')
            self._correction.fit(
                station_id,
                pump_ids,
                training_data=training_data,
                extra_features=extended_features
            )

        return GroupFitResult(
            station_id=station_id,
            pump_combination=pump_ids,
            group_type=GroupProcessingStrategy.MIXED_HETEROGENEOUS,
            curve_type=curve_type,
            pump_count=n_pumps,
            valid_n_range=(1, n_pumps),
            correction_model=self._correction.to_dict() if self._correction.is_fitted else None,
            vfd_pump_ids=vfd_pump_ids,
            ss_pump_ids=ss_pump_ids
        )

    def __repr__(self) -> str:
        return (
            f"PumpGroupProcessor("
            f"power_threshold={self._power_diff_threshold:.0%}, "
            f"freq_threshold={self._freq_diff_threshold:.0%})"
        )
