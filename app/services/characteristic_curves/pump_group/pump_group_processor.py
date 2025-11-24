"""
泵组处理器 - PumpGroupProcessor

版本: v2.5
创建日期: 2025-12-09
文件路径: app/services/characteristic_curves/pump_group/pump_group_processor.py
来源: 07_泵组处理层.md 第2章
任务ID: 73

职责:
    - 泵组类型识别（5种策略）
    - 策略路由
    - 调用 ParallelSynthesizer 合成曲线
    - 调用 SystemCorrectionModel 学习修正系数
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
import logging
import numpy as np

from app.services.characteristic_curves.models import (
    GroupProcessingStrategy,
    GroupFitResult,
    FitResult,
)
from app.services.characteristic_curves.shared.exceptions import (
    CurveFittingError,
    InsufficientDataError,
    FrequencyQueryError,
    HeadOutOfRangeError,
    CorrectionModelTrainingError,
    P0FittingRetryExhaustedError,
    CurveInconsistencyError,
    MissingCurveError,
    DataNotFoundError,
)
from app.services.characteristic_curves.shared.curve_registry import CurveRegistry

if TYPE_CHECKING:
    from app.services.characteristic_curves.pump_group.parallel_synthesizer import (
        ParallelSynthesizer,
    )
    from app.services.characteristic_curves.pump_group.system_correction_model import (
        SystemCorrectionModel,
    )
    from app.services.characteristic_curves.pump_group.frequency_data_provider import (
        FrequencyDataProvider,
    )


class PumpGroupProcessor:
    """泵组处理器

    P2阶段核心类，负责：
    1. 泵组类型识别（5种策略）
    2. 策略路由到对应处理方法
    3. 调用 ParallelSynthesizer 合成曲线
    4. 调用 SystemCorrectionModel 学习修正系数

    5种泵组类型：
    - HOMOGENEOUS_GROUP: 同构泵组（同型号、频率一致）
    - HETEROGENEOUS_GROUP: 异构泵组（功率差异≥10%）
    - VFD_HETEROGENEOUS_FREQ: VFD频率异构（全VFD、频率差异≥2%）
    - MIXED_GROUP: 混合泵组（VFD+SS、功率差异<10%）
    - MIXED_HETEROGENEOUS: 混合异构泵组（VFD+SS、功率差异≥10%）
    """

    # 阈值常量（禁止使用默认值，必须显式传入）
    POWER_DIFF_THRESHOLD: float = 0.10  # 功率差异阈值 10%
    FREQ_DIFF_THRESHOLD: float = 0.02   # 频率差异阈值 2%

    def __init__(
        self,
        parallel_synthesizer: "ParallelSynthesizer",
        correction_model: "SystemCorrectionModel",
        freq_provider: "FrequencyDataProvider",
        power_diff_threshold: float,
        freq_diff_threshold: float
    ) -> None:
        """初始化泵组处理器

        Args:
            parallel_synthesizer: 并联合成器实例（任务74）
            correction_model: 系统修正模型实例（任务75）
            freq_provider: 频率数据提供器实例（任务76）
            power_diff_threshold: 功率差异阈值（必须显式指定）
            freq_diff_threshold: 频率差异阈值（必须显式指定）

        Note:
            所有参数必须显式传入，禁止使用默认值。
        """
        self._synthesizer = parallel_synthesizer
        self._correction = correction_model
        self._freq_provider = freq_provider
        self._power_diff_threshold = power_diff_threshold
        self._freq_diff_threshold = freq_diff_threshold
        self._curve_registry = CurveRegistry()
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def identify_group_type(
        self,
        pump_infos: List[Dict[str, Any]]
    ) -> GroupProcessingStrategy:
        """识别泵组类型

        决策树逻辑：
        1. 检查是否为纯VFD泵组
        2. 如果是纯VFD：检查功率差异和频率差异
        3. 如果是混合泵组：检查功率差异

        Args:
            pump_infos: 泵信息列表，每个元素包含：
                - pump_id: int
                - control_type: str ('VFD' | 'SS')
                - rated_power: float (kW)
                - model: str (可选)

        Returns:
            GroupProcessingStrategy: 泵组处理策略枚举

        Raises:
            ValueError: pump_infos为空或格式错误
        """
        if not pump_infos:
            raise ValueError("pump_infos不能为空")

        # 1. 分类泵
        vfd_pumps = [p for p in pump_infos if p.get('control_type') == 'VFD']
        ss_pumps = [p for p in pump_infos if p.get('control_type') == 'SS']

        n_vfd = len(vfd_pumps)
        n_ss = len(ss_pumps)
        n_total = len(pump_infos)

        self._logger.debug(
            f"[泵组识别] 总数={n_total}, VFD={n_vfd}, SS={n_ss}"
        )

        # 2. 计算功率差异
        powers = [p['rated_power'] for p in pump_infos]
        power_max = max(powers)
        power_min = min(powers)
        power_diff = (power_max - power_min) / power_max if power_max > 0 else 0.0

        # 3. 决策树
        if n_ss == 0:
            # 纯VFD泵组
            pump_ids = [p['pump_id'] for p in pump_infos]
            frequencies = self._freq_provider.get_latest_frequencies(pump_ids)
            freq_values = list(frequencies.values())

            if len(freq_values) > 1:
                freq_max = max(freq_values)
                freq_min = min(freq_values)
                freq_diff = (freq_max - freq_min) / freq_max if freq_max > 0 else 0.0
            else:
                freq_diff = 0.0

            self._logger.debug(
                f"[泵组识别] 纯VFD: 功率差异={power_diff:.1%}, 频率差异={freq_diff:.1%}"
            )

            # 纯VFD决策
            if power_diff >= self._power_diff_threshold:
                return GroupProcessingStrategy.HETEROGENEOUS_GROUP
            elif freq_diff >= self._freq_diff_threshold:
                return GroupProcessingStrategy.VFD_HETEROGENEOUS_FREQ
            else:
                return GroupProcessingStrategy.HOMOGENEOUS_GROUP
        else:
            # 混合泵组（VFD + SS）
            self._logger.debug(
                f"[泵组识别] 混合泵组: 功率差异={power_diff:.1%}"
            )

            if power_diff >= self._power_diff_threshold:
                return GroupProcessingStrategy.MIXED_HETEROGENEOUS
            else:
                return GroupProcessingStrategy.MIXED_GROUP

    def _check_single_pump_curves(
        self,
        pump_ids: List[int],
        curve_type: str
    ) -> List[int]:
        """检查单泵曲线是否已完成P0拟合

        Args:
            pump_ids: 泵ID列表
            curve_type: 曲线类型 ('qh' | 'qp' | 'qe')

        Returns:
            List[int]: 缺失曲线的泵ID列表（空列表表示全部已注册）
        """
        missing = []
        for pump_id in pump_ids:
            if not self._curve_registry.has_curve(pump_id, curve_type):
                missing.append(pump_id)

        if missing:
            self._logger.warning(
                f"[曲线检查] 缺失曲线: pump_ids={missing}, curve_type={curve_type}"
            )

        return missing

    def _trigger_p0_fitting(
        self,
        pump_ids: List[int],
        curve_type: str,
        max_retries: int
    ) -> Dict[int, bool]:
        """触发P0阶段拟合（含重试逻辑）

        Args:
            pump_ids: 需要拟合的泵ID列表
            curve_type: 曲线类型
            max_retries: 最大重试次数

        Returns:
            Dict[int, bool]: 拟合结果 {pump_id: success}

        Raises:
            P0FittingRetryExhaustedError: 重试次数耗尽
        """
        # 延迟导入避免循环依赖
        from app.services.characteristic_curves.pipeline import P0Pipeline

        results: Dict[int, bool] = {}

        for pump_id in pump_ids:
            retry_count = 0
            last_error: Optional[str] = None

            while retry_count < max_retries:
                try:
                    self._logger.info(
                        f"[P0触发] pump_id={pump_id}, curve_type={curve_type}, "
                        f"retry={retry_count + 1}/{max_retries}"
                    )

                    # 调用P0管道
                    pipeline = P0Pipeline()
                    pipeline.fit_single_pump(pump_id, curve_type)

                    # 验证是否成功注册
                    if self._curve_registry.has_curve(pump_id, curve_type):
                        results[pump_id] = True
                        self._logger.info(f"[P0触发] pump_id={pump_id} 拟合成功")
                        break
                    else:
                        last_error = "拟合完成但曲线未注册"
                        retry_count += 1

                except Exception as e:
                    last_error = str(e)
                    retry_count += 1
                    self._logger.warning(
                        f"[P0触发] pump_id={pump_id} 第{retry_count}次尝试失败: {e}"
                    )

            # 检查是否成功
            if pump_id not in results:
                results[pump_id] = False
                raise P0FittingRetryExhaustedError(
                    message=f"泵 {pump_id} P0拟合重试次数耗尽",
                    pump_id=pump_id,
                    retry_count=retry_count,
                    max_retries=max_retries,
                    last_error=last_error
                )

        return results

    def process(
        self,
        station_id: int,
        pump_infos: List[Dict[str, Any]],
        curve_type: str,
        auto_trigger_p0: bool,
        max_p0_retries: int
    ) -> GroupFitResult:
        """处理泵组（主入口）

        Args:
            station_id: 泵站ID
            pump_infos: 泵信息列表
            curve_type: 曲线类型 ('qh' | 'qp' | 'qe')
            auto_trigger_p0: 是否自动触发P0拟合
            max_p0_retries: P0拟合最大重试次数

        Returns:
            GroupFitResult: 泵组拟合结果

        Raises:
            MissingCurveError: 单泵曲线未注册且auto_trigger_p0=False
            P0FittingRetryExhaustedError: P0拟合重试次数耗尽
            InsufficientDataError: 数据不足
            CorrectionModelTrainingError: 修正模型训练失败
        """
        pump_ids = [p['pump_id'] for p in pump_infos]

        # 前置检查：验证所有单泵曲线是否已完成P0拟合
        missing_curves = self._check_single_pump_curves(pump_ids, curve_type)
        if missing_curves:
            if auto_trigger_p0:
                self._trigger_p0_fitting(missing_curves, curve_type, max_retries=max_p0_retries)
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

    def _get_pump_fit_result(
        self,
        pump_id: int,
        curve_type: str
    ) -> Optional[FitResult]:
        """获取单泵拟合结果

        Args:
            pump_id: 泵ID
            curve_type: 曲线类型 ('qh' | 'qp' | 'qe')

        Returns:
            FitResult: 拟合结果对象，包含coefficients, r_squared, data_points等
            None: 如果未找到拟合结果
        """
        entry = self._curve_registry.get_entry(pump_id, curve_type)

        if entry is None:
            self._logger.warning(
                f"[获取拟合结果] pump_id={pump_id}, curve_type={curve_type} 未找到"
            )
            return None

        # 从CurveEntry转换为FitResult
        return FitResult(
            device_id=pump_id,
            curve_type=curve_type,
            method_name=entry.method_name if entry.method_name else "",
            coefficients=entry.coefficients if entry.coefficients else {},
            r_squared=entry.r_squared if entry.r_squared else 0.0,
            rmse=entry.rmse,
            data_points=entry.data_points,
            fitted_at=entry.fitted_at,
            valid_q_range=entry.Q_range,
            valid_h_range=entry.H_range
        )

    def _select_base_pump(
        self,
        pump_ids: List[int],
        pump_infos: List[Dict[str, Any]],
        curve_type: str
    ) -> int:
        """选择最优基准泵

        选择标准（优先级从高到低）：
        1. 运行频率最接近50Hz（额定频率）
        2. 曲线拟合R²最高
        3. 数据点数量最多

        Returns:
            最优基准泵ID

        Raises:
            ValueError: 无法确定基准泵
        """
        candidates = []

        for pump_id in pump_ids:
            fit_result = self._get_pump_fit_result(pump_id, curve_type)
            if fit_result is None:
                self._logger.warning(f"泵 {pump_id} 无拟合结果，排除")
                continue

            # 获取当前频率
            freq = self._freq_provider.get_latest_frequencies([pump_id]).get(pump_id, 50.0)

            # 计算评分（频率偏离度权重0.4，R²权重0.4，数据点权重0.2）
            freq_score = 1 - abs(freq - 50) / 50  # 频率越接近50Hz越好
            r2_score = fit_result.r_squared
            data_score = min(fit_result.data_points / 10000, 1.0)  # 归一化

            total_score = 0.4 * freq_score + 0.4 * r2_score + 0.2 * data_score

            candidates.append({
                'pump_id': pump_id,
                'score': total_score,
                'freq': freq,
                'r2': fit_result.r_squared
            })

        if not candidates:
            raise ValueError("无可用的基准泵候选")

        # 按评分排序，选择最高分
        candidates.sort(key=lambda x: x['score'], reverse=True)
        best = candidates[0]

        self._logger.info(
            f"[基准泵选择] 选定 pump_id={best['pump_id']}，"
            f"freq={best['freq']}Hz, R²={best['r2']:.4f}, score={best['score']:.3f}"
        )

        return best['pump_id']

    def _validate_curve_consistency(
        self,
        pump_ids: List[int],
        curve_type: str,
        max_h0_deviation: float,
        max_k_deviation: float
    ) -> bool:
        """验证同构泵组曲线一致性

        Args:
            pump_ids: 泵ID列表
            curve_type: 曲线类型
            max_h0_deviation: H0最大允许偏差（相对值）
            max_k_deviation: K最大允许偏差（相对值）

        Returns:
            True: 一致性验证通过

        Raises:
            CurveInconsistencyError: 曲线参数差异超出阈值
        """
        coefficients_list = []

        for pump_id in pump_ids:
            result = self._get_pump_fit_result(pump_id, curve_type)
            if result is None:
                raise MissingCurveError(f"泵 {pump_id} 缺少曲线数据", [pump_id])

            coeffs = result.coefficients
            if isinstance(coeffs, dict):
                coefficients_list.append({
                    'pump_id': pump_id,
                    'H0': coeffs.get('H0'),
                    'K': coeffs.get('K')
                })
            else:
                self._logger.warning(f"泵 {pump_id} 系数格式不是Dict，跳过一致性检查")
                return True

        # 计算H0和K的统计值
        h0_values = [c['H0'] for c in coefficients_list if c['H0'] is not None]
        k_values = [c['K'] for c in coefficients_list if c['K'] is not None]

        if not h0_values or not k_values:
            self._logger.warning("无法获取H0或K值，跳过一致性检查")
            return True

        h0_mean = float(np.mean(h0_values))
        k_mean = float(np.mean(k_values))

        # 计算相对偏差
        h0_max_dev = max(abs(h0 - h0_mean) / h0_mean for h0 in h0_values) if h0_mean != 0 else 0.0
        k_max_dev = max(abs(k - k_mean) / abs(k_mean) for k in k_values) if k_mean != 0 else 0.0

        self._logger.info(
            f"[曲线一致性] pumps={pump_ids}, H0偏差={h0_max_dev:.2%}, K偏差={k_max_dev:.2%}"
        )

        # 验证
        if h0_max_dev > max_h0_deviation:
            raise CurveInconsistencyError(
                message=f"同构泵组H0偏差 {h0_max_dev:.2%} 超出阈值 {max_h0_deviation:.0%}",
                pump_ids=pump_ids,
                parameter='H0',
                deviation=h0_max_dev,
                threshold=max_h0_deviation
            )

        if k_max_dev > max_k_deviation:
            raise CurveInconsistencyError(
                message=f"同构泵组K偏差 {k_max_dev:.2%} 超出阈值 {max_k_deviation:.0%}",
                pump_ids=pump_ids,
                parameter='K',
                deviation=k_max_dev,
                threshold=max_k_deviation
            )

        return True

    def _get_system_head(self, station_id: int) -> float:
        """获取泵站的系统扬程

        Args:
            station_id: 泵站ID

        Returns:
            float: 系统扬程值（米）

        Raises:
            DataNotFoundError: 无出口压力数据
        """
        from app.adapters.db.pool import get_connection

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
            ORDER BY fm.ts_raw DESC
            LIMIT 1
        """
        with get_connection() as conn:
            result = conn.execute(sql, {'station_id': station_id}).fetchone()
            if result:
                return float(result['H_system'])

        raise DataNotFoundError(
            f"泵站 {station_id} 无出口压力数据（metric_key='main_pipeline_outlet_pressure'）"
        )

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
        from app.adapters.db.pool import get_connection

        sql = """
            WITH pump_group AS (
                SELECT %(pump_ids)s::int[] AS group_pumps
            ),
            metric_ids AS (
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
                    array_agg(pm.device_id ORDER BY pm.device_id)
                        FILTER (WHERE pm.running = 1) AS running_pumps,
                    COUNT(*) FILTER (WHERE pm.running = 1) AS N,
                    COALESCE(SUM(pm.flow) FILTER (WHERE pm.running = 1), 0) AS Q_total,
                    sp.H_actual
                FROM pump_metrics pm
                JOIN station_pressure sp ON pm.ts_bucket = sp.ts_bucket
                GROUP BY pm.ts_bucket, sp.H_actual
                HAVING COUNT(*) FILTER (WHERE pm.running = 1) >= 1
            ),
            valid_records AS (
                SELECT running_pumps, N, Q_total, H_actual
                FROM aggregated ag
                CROSS JOIN pump_group pg
                WHERE ag.running_pumps <@ pg.group_pumps
                  AND ag.running_pumps && pg.group_pumps
                  AND ag.Q_total > 0
            )
            SELECT running_pumps, N, Q_total, H_actual
            FROM valid_records
            ORDER BY Q_total
        """
        with get_connection() as conn:
            rows = conn.execute(sql, {
                'station_id': station_id,
                'pump_ids': pump_ids
            }).fetchall()

        if not rows:
            self._logger.warning(f"[训练数据] 泵站 {station_id} 无历史数据")
            return np.array([])

        # 构建训练数据矩阵
        data = []
        for row in rows:
            running_pumps = row['running_pumps']
            N = row['N']
            Q_total = row['Q_total']
            H_actual = row['H_actual']

            # 通过合成方法计算H_theoretical
            try:
                synthesis_result = self._synthesizer.synthesize_heterogeneous(
                    pump_ids=running_pumps,
                    H_system=H_actual
                )
                H_theoretical = synthesis_result.H_system
            except Exception as e:
                self._logger.debug(
                    f"[训练数据] 合成计算失败: {e}，使用H_actual作为H_theoretical"
                )
                H_theoretical = H_actual

            data.append([N, Q_total, H_theoretical, H_actual])

        self._logger.info(f"[训练数据] 提取 {len(data)} 条记录，用于泵站 {station_id}")
        return np.array(data)

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

        # 曲线一致性验证（阈值：H0偏差5%，K偏差10%）
        self._validate_curve_consistency(
            pump_ids, curve_type,
            max_h0_deviation=0.05,
            max_k_deviation=0.10
        )

        # 使用优化的基准泵选择
        base_pump_id = self._select_base_pump(pump_ids, pump_infos, curve_type)

        # 1. 合成同构泵组曲线
        group_curve = self._synthesizer.synthesize_homogeneous(
            base_pump_id=base_pump_id,
            n_pumps=n_pumps
        )

        # 2. 提取训练数据并学习修正系数
        training_data = self._extract_training_data(station_id, pump_ids)
        self._correction.fit(station_id, pump_ids, training_data=training_data)

        return GroupFitResult(
            station_id=station_id,
            pump_combination=pump_ids,
            group_type=GroupProcessingStrategy.HOMOGENEOUS_GROUP,
            curve_type=curve_type,
            base_pump_id=base_pump_id,
            pump_count=n_pumps,
            valid_n_range=(1, n_pumps),
            correction_model=self._correction.to_dict(),
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
        策略：获取各泵当前运行频率，使用考虑频率的合成方法
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
        self._correction.fit(station_id, pump_ids, training_data=training_data)

        return GroupFitResult(
            station_id=station_id,
            pump_combination=pump_ids,
            group_type=GroupProcessingStrategy.VFD_HETEROGENEOUS_FREQ,
            curve_type=curve_type,
            pump_count=n_pumps,
            valid_n_range=(1, n_pumps),
            correction_model=self._correction.to_dict(),
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

        # 1. 确保所有单泵曲线已注册
        missing_curves = []
        for pump_id in pump_ids:
            if not self._curve_registry.has_curve(pump_id, curve_type):
                missing_curves.append(pump_id)

        if missing_curves:
            raise ValueError(f"[异构处理] 泵曲线未注册: {missing_curves}")

        # 记录异构泵组的频率差异情况
        frequencies = self._freq_provider.get_latest_frequencies(pump_ids)
        freq_values = list(frequencies.values())
        if len(freq_values) > 1:
            freq_diff = (max(freq_values) - min(freq_values)) / max(freq_values)
            self._logger.info(
                f"[异构处理] 频率差异 {freq_diff:.1%}, 各泵频率: {frequencies}"
            )

        # 2. 调用异构合成方法
        H_system = self._get_system_head(station_id)
        synthesis_result = self._synthesizer.synthesize_heterogeneous(
            pump_ids=pump_ids,
            H_system=H_system,
            pump_frequencies=frequencies
        )

        self._logger.info(
            f"[异构处理] 合成结果: Q_total={synthesis_result.Q_total:.1f}, "
            f"H_system={synthesis_result.H_system:.1f}"
        )

        # 3. 提取训练数据并学习修正系数
        training_data = self._extract_training_data(station_id, pump_ids)
        self._correction.fit(station_id, pump_ids, training_data=training_data)

        return GroupFitResult(
            station_id=station_id,
            pump_combination=pump_ids,
            group_type=GroupProcessingStrategy.HETEROGENEOUS_GROUP,
            curve_type=curve_type,
            pump_count=n_pumps,
            valid_n_range=(1, n_pumps),
            correction_model=self._correction.to_dict(),
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
        vfd_pumps = [p['pump_id'] for p in pump_infos if p.get('control_type') == 'VFD']
        ss_pumps = [p['pump_id'] for p in pump_infos if p.get('control_type') == 'SS']

        # 混合泵组必须包含至少一台VFD泵
        assert len(vfd_pumps) > 0, (
            f"混合泵组必须包含至少一台VFD泵，当前VFD={len(vfd_pumps)}, SS={len(ss_pumps)}。"
            f"纯SS泵组应使用HETEROGENEOUS_GROUP策略处理。"
        )

        self._logger.info(f"[混合处理] VFD泵: {vfd_pumps}, 软启泵: {ss_pumps}")

        # 2. 获取VFD泵的当前频率
        pump_frequencies = self._freq_provider.get_latest_frequencies(vfd_pumps)

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
            f"H_system={synthesis_result.H_system:.1f}, "
            f"流量分配: {synthesis_result.pump_flows}"
        )

        # 4. 提取训练数据并学习修正系数（使用XGBoost）
        training_data = self._extract_training_data(station_id, pump_ids)
        self._correction.set_model_type('xgboost')
        self._correction.fit(station_id, pump_ids, training_data=training_data)

        return GroupFitResult(
            station_id=station_id,
            pump_combination=pump_ids,
            group_type=GroupProcessingStrategy.MIXED_GROUP,
            curve_type=curve_type,
            pump_count=n_pumps,
            valid_n_range=(1, n_pumps),
            correction_model=self._correction.to_dict(),
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
        策略：分类泵、计算功率权重、使用加权合成方法、训练XGBoost修正模型
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

        # 3. 检查VFD子组内部的功率差异
        vfd_power_diff = 0.0
        if len(vfd_infos) > 1:
            vfd_powers = [p['rated_power'] for p in vfd_infos]
            vfd_power_diff = (max(vfd_powers) - min(vfd_powers)) / max(vfd_powers)

        # 4. 检查VFD子组内部的频率差异
        vfd_freq_diff = 0.0
        pump_frequencies: Dict[int, float] = {}
        if len(vfd_pump_ids) >= 1:
            pump_frequencies = self._freq_provider.get_latest_frequencies(vfd_pump_ids)
            if len(vfd_pump_ids) > 1:
                freq_values = list(pump_frequencies.values())
                vfd_freq_diff = (max(freq_values) - min(freq_values)) / max(freq_values)

        self._logger.info(
            f"[混合异构处理] VFD泵: {vfd_pump_ids}, SS泵: {ss_pump_ids}, "
            f"功率权重: {power_weights}, "
            f"VFD子组功率差异: {vfd_power_diff:.1%}, VFD子组频率差异: {vfd_freq_diff:.1%}"
        )

        # 5. 调用加权混合合成方法
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

        # 6. 准备扩展特征用于XGBoost训练
        extended_features = {
            'power_weights': power_weights,
            'vfd_power_diff': vfd_power_diff,
            'vfd_freq_diff': vfd_freq_diff,
            'power_max': max(powers.values()),
            'power_min': min(powers.values()),
            'power_ratio': max(powers.values()) / min(powers.values())
        }

        # 7. 提取训练数据并学习修正系数（使用XGBoost + 扩展特征）
        training_data = self._extract_training_data(station_id, pump_ids)
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
            correction_model=self._correction.to_dict(),
            vfd_pump_ids=vfd_pump_ids,
            ss_pump_ids=ss_pump_ids
        )

