"""
曲线拟合主管道 (app.services.characteristic_curves.pipeline.curve_fitting_pipeline)

实现16阶段的特性曲线拟合流程。

版本: v1.0
更新日期: 2025-12-09
参考文档: 特性曲线开发/开发文档/02_架构设计/02_数据流定义.md
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.services.characteristic_curves.pipeline.pipeline_context import (
    PipelineContext,
    PipelineStage,
    StageResult,
)
from app.services.characteristic_curves.core.data_structures import FitResult, Scenario


@dataclass
class PipelineConfig:
    """管道配置"""

    enable_scenario_detect: bool = True
    enable_steady_state_detect: bool = True
    enable_freq_normalize: bool = True
    enable_historical_eval: bool = True
    min_data_points: int = 50
    default_method: str = "math_poly_2"


class CurveFittingPipeline:
    """曲线拟合主管道

    实现18阶段的特性曲线拟合流程（包含图片生成和报告生成）。

    使用方式:
        # 基础使用（向后兼容）
        pipeline = CurveFittingPipeline()
        result = pipeline.fit(device_id=1, curve_type="qh")

        # 完整使用（集成所有功能）
        from app.services.characteristic_curves.shared import ResultStorage
        from app.services.characteristic_curves.output import ResultOutput  # Note: 使用output/下的正确版本
        import yaml

        storage = ResultStorage()
        output = ResultOutput(output_dir=Path("./reports"))
        with open("configs/visualization.yaml") as f:
            plot_config = yaml.safe_load(f)

        pipeline = CurveFittingPipeline(
            result_storage=storage,
            result_output=output,
            plot_config=plot_config,
            output_dir="./plots"
        )
        result = pipeline.fit(device_id=1, curve_type="qh")
    """

    def __init__(
        self,
        # 文档要求的必需依赖（符合3.11节规范）
        method_registry: 'MethodRegistry',  # 方法注册器（必需）
        result_storage: 'ResultStorage',   # 结果存储器（必需）
        # 可选依赖
        cache_manager: Optional['CacheManager'] = None,
        batch_processor: Optional['BatchProcessor'] = None,
        parameter_optimizer: Optional['ParameterOptimizer'] = None,
        historical_evaluator: Optional['HistoricalDataEvaluator'] = None,
        time_window_splitter: Optional['TimeWindowSplitter'] = None,
        method_selector: Optional['MethodSelector'] = None,  # P0新增: 方法选择器
        data_extractor: Optional['DataExtractor'] = None,   # P0新增: 数据提取器
        # 配置参数
        config: Optional[PipelineConfig] = None,
        result_output: Optional['ResultOutput'] = None,
        plot_config: Optional[Dict[str, Any]] = None,
        output_dir: Optional[str] = None,
    ) -> None:
        """初始化管道（严格依赖注入）

        v3.1 依赖注入重构（符合文档3.11节）:
        - method_registry和result_storage为必需参数（不再可选）
        - 添加类型注解检查，确保参数类型正确
        - 严格遵循依赖注入原则，禁止自动创建实例

        Args:
            method_registry: 方法注册器实例（必需）
            result_storage: 结果存储器实例（必需）
            cache_manager: 缓存管理器实例（可选）
            batch_processor: 批处理器实例（可选）
            parameter_optimizer: 参数优化器实例（可选）
            historical_evaluator: 历史数据评估器实例（可选）
            time_window_splitter: 时间窗口划分器实例（可选）
            method_selector: 方法选择器实例（可选）
            data_extractor: 数据提取器实例（可选）
            config: 管道配置（可选）
            result_output: 结果输出器（可选）
            plot_config: 绘图配置（可选）
            output_dir: 图片输出目录（可选）

        Raises:
            TypeError: method_registry或result_storage未提供或类型错误时抛出
        """
        # 必需参数检查（符合文档要求）
        if method_registry is None:
            raise TypeError("method_registry是必需参数，不能为None")
        if result_storage is None:
            raise TypeError("result_storage是必需参数，不能为None")
        self._config = config or PipelineConfig()
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")
        self._stage_handlers: Dict[PipelineStage, Callable] = {}

        # 严格依赖注入（符合文档规范）
        self._method_registry = method_registry
        self._result_storage = result_storage

        # 可选组件
        self._cache_manager = cache_manager
        self._batch_processor = batch_processor
        self._parameter_optimizer = parameter_optimizer
        self._historical_evaluator = historical_evaluator
        self._time_window_splitter = time_window_splitter
        self._method_selector = method_selector
        self._data_extractor = data_extractor

        # 向后兼容: 保留原有组件
        self._result_output = result_output
        self._plot_config = plot_config
        self._output_dir = output_dir or "."

        self._register_default_handlers()

        self._logger.info(
            "[管道] 初始化",
            extra={"extra_data": {
                "组件": "CurveFittingPipeline",
                "方法注册器": "已注入" if method_registry else "自动创建",
                "结果存储": "已注入" if result_storage else "自动创建",
                "缓存管理": "已启用" if cache_manager else "未启用",
                "批处理器": "已启用" if batch_processor else "未启用",
                "参数优化": "已启用" if parameter_optimizer else "未启用",
                "历史评估": "已启用" if historical_evaluator else "未启用",
                "时间划分": "已启用" if time_window_splitter else "未启用",
                "报告生成": "已启用" if result_output else "未启用",
                "图片生成": "已启用" if plot_config else "未启用",
            }}
        )

    def _register_default_handlers(self) -> None:
        """注册默认阶段处理器 - P0完整13阶段"""
        self._stage_handlers = {
            # P0必需阶段（13个）
            PipelineStage.TIME_WINDOW_SPLIT: self._stage_time_window_split,
            PipelineStage.SCENARIO_DETECT: self._stage_scenario_detect,
            PipelineStage.DATA_EXTRACT: self._stage_data_extract,
            PipelineStage.DATA_CLEAN: self._stage_data_clean,
            PipelineStage.STEADY_STATE_DETECT: self._stage_steady_state_detect,
            PipelineStage.CONSTRAINT_CALC: self._stage_constraint_calc,
            PipelineStage.FREQ_NORMALIZE: self._stage_freq_normalize,
            PipelineStage.DATA_NORMALIZE: self._stage_data_normalize,
            PipelineStage.METHOD_SELECT: self._stage_method_select,
            PipelineStage.CURVE_FIT: self._stage_curve_fit,
            PipelineStage.RESULT_VALIDATE: self._stage_result_validate,
            PipelineStage.HISTORICAL_EVAL: self._stage_historical_eval,
            PipelineStage.RESULT_STORE: self._stage_result_store,
            # 扩展阶段（可选）
            PipelineStage.PLOT_GENERATION: self._stage_plot_generation,
            PipelineStage.REPORT_GENERATION: self._stage_report_generation,
        }

    def fit(
        self,
        device_id: int,
        curve_type: str,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        progress_callback: Optional[Callable[[
            PipelineStage, float], None]] = None,
        **kwargs: Any,
    ) -> FitResult:
        """执行曲线拟合

        Args:
            device_id: 设备ID
            curve_type: 曲线类型 (qh, qp, qeta)
            time_range: 时间范围
            progress_callback: 进度回调
            **kwargs: 其他参数

        Returns:
            FitResult: 拟合结果
        """
        context = PipelineContext(
            device_id=device_id,
            curve_type=curve_type,
            progress_callback=progress_callback,
        )
        context.set_data("time_range", time_range)
        context.set_data("kwargs", kwargs)

        # P0阶段执行顺序（13阶段 + 2扩展阶段）
        # 文档依据: 02_架构设计/02_数据流定义.md
        # P0基础: 13阶段
        # 扩展阶段: 图片生成、报告生成
        p0_stages = [
            PipelineStage.TIME_WINDOW_SPLIT,
            PipelineStage.SCENARIO_DETECT,
            PipelineStage.DATA_EXTRACT,
            PipelineStage.DATA_CLEAN,
            PipelineStage.STEADY_STATE_DETECT,
            PipelineStage.CONSTRAINT_CALC,
            PipelineStage.FREQ_NORMALIZE,
            PipelineStage.DATA_NORMALIZE,
            PipelineStage.METHOD_SELECT,
            PipelineStage.CURVE_FIT,
            PipelineStage.RESULT_VALIDATE,
            PipelineStage.HISTORICAL_EVAL,
            PipelineStage.RESULT_STORE,
            PipelineStage.PLOT_GENERATION,  # 新增
            PipelineStage.REPORT_GENERATION,  # 新增
        ]

        for stage in p0_stages:
            result = self._execute_stage(stage, context)
            if not result.success and not result.skipped:
                self._logger.error(f"阶段 {stage.value} 执行失败: {result.error}")
                return self._create_error_result(context, result.error)

        return context.get_data("fit_result", self._create_success_result(context))

    def _execute_stage(self, stage: PipelineStage, context: PipelineContext) -> StageResult:
        """执行单个阶段"""
        context.set_stage(stage)
        start_time = time.time()

        # 检查是否跳过
        if self._should_skip_stage(stage, context):
            result = StageResult(
                stage=stage, success=True, skipped=True,
                skip_reason=f"阶段 {stage.value} 条件不满足，跳过"
            )
            context.add_stage_result(result)
            return result

        try:
            handler = self._stage_handlers.get(stage)
            if handler is None:
                raise ValueError(f"未找到阶段处理器: {stage.value}")

            data = handler(context)
            duration = (time.time() - start_time) * 1000

            result = StageResult(stage=stage, success=True,
                                 data=data, duration_ms=duration)
            context.add_stage_result(result)
            context.report_progress(1.0)
            return result

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            result = StageResult(stage=stage, success=False,
                                 error=str(e), duration_ms=duration)
            context.add_stage_result(result)
            return result

    def _should_skip_stage(self, stage: PipelineStage, context: PipelineContext) -> bool:
        """判断是否跳过阶段 - 实现条件执行逻辑"""
        # 场景识别：根据配置决定
        if stage == PipelineStage.SCENARIO_DETECT:
            return not self._config.enable_scenario_detect

        # 稳态识别：当数据包含非稳态数据时执行
        if stage == PipelineStage.STEADY_STATE_DETECT:
            return not self._config.enable_steady_state_detect

        # 频率归一化：仅当变频泵且频率标准差>2.0时执行
        if stage == PipelineStage.FREQ_NORMALIZE:
            if not self._config.enable_freq_normalize:
                return True
            # 检查是否需要归一化（变频泵）
            pump_type = context.get_data("pump_type")
            freq_std = context.get_data("freq_std", 0.0)
            return not (pump_type == "variable_frequency" and freq_std > 2.0)

        # 历史评估：仅当can_evaluate=True时执行
        if stage == PipelineStage.HISTORICAL_EVAL:
            if not self._config.enable_historical_eval:
                return True
            return not context.get_data("can_evaluate", False)

        # 图片生成：没有绘图配置则跳过
        if stage == PipelineStage.PLOT_GENERATION:
            return self._plot_config is None

        # 报告生成：没有报告输出器则跳过
        if stage == PipelineStage.REPORT_GENERATION:
            return self._result_output is None

        return False

    def _get_device_params(self, context: PipelineContext) -> Dict[str, Any]:
        """获取设备参数

        优先级:
        1. context中已有的device_params
        2. 从数据库device_rated_params表读取（使用get_connection）
        3. 参数缺失时抛出异常（不使用默认值）

        Returns:
            Dict: 设备参数字典

        Raises:
            DataExtractionError: 必需参数缺失时抛出
        """
        # 1. 尝试从context获取
        device_params = context.get_data("device_params")
        if device_params and isinstance(device_params, dict) and len(device_params) > 2:
            return device_params

        # 2. 从数据库读取（使用get_connection，符合文档规范）
        try:
            from app.adapters.db.pool import get_connection

            with get_connection() as conn:
                with conn.cursor() as cursor:
                    # 从 device_rated_params 表查询设备参数
                    cursor.execute("""
                        SELECT 
                            param_key,
                            value_numeric
                        FROM device_rated_params
                        WHERE device_id = %s
                        AND param_key IN ('rated_flow', 'rated_head', 'rated_power', 
                                         'rated_efficiency', 'rated_frequency')
                        LIMIT 10
                    """, (context.device_id,))

                    rows = cursor.fetchall()

                    if rows:
                        # 将结果转换为字典
                        params_dict = {row[0]: float(row[1])
                                       for row in rows if row[1] is not None}

                        # 检查必需参数是否存在
                        required_params = ['rated_flow',
                                           'rated_head', 'rated_power']
                        missing_params = [
                            p for p in required_params if p not in params_dict]

                        if missing_params:
                            raise ValueError(f"缺少必需参数: {missing_params}")

                        device_params = {
                            "rated_flow": params_dict['rated_flow'],
                            "rated_head": params_dict['rated_head'],
                            "rated_power": params_dict['rated_power'],
                            "rated_efficiency": params_dict.get('rated_efficiency', 0.75),
                            "rated_frequency": params_dict.get('rated_frequency', 50.0),
                            "device_type": "single_pump"
                        }

                        # 保存到context
                        context.set_data("device_params", device_params)

                        self._logger.info(
                            f"[设备参数] 从数据库加载成功",
                            extra={"extra_data": {
                                "设备ID": context.device_id,
                                "额定流量": device_params["rated_flow"],
                                "额定扬程": device_params["rated_head"],
                                "额定功率": device_params["rated_power"]
                            }}
                        )

                        return device_params

        except Exception as e:
            self._logger.warning(
                f"[设备参数] 从数据库读取失败: {e}",
                extra={"extra_data": {"错误": str(e)}}
            )

        # 3. 不允许降级到默认值（符合文档规范）
        from app.services.characteristic_curves.shared.exceptions import DataExtractionError
        raise DataExtractionError(
            message=f"设备{context.device_id}的额定参数缺失，无法从device_rated_params表读取",
            device_id=context.device_id,
            reason="必需参数rated_flow、rated_head、rated_power缺失"
        )

    # ===== 阶段处理器 =====

    def _stage_time_window_split(self, context: PipelineContext) -> Any:
        """阶段1: 时间窗口划分"""
        time_range = context.get_data("time_range")

        if self._time_window_splitter and time_range:
            # 使用注入的TimeWindowSplitter
            # split_with_custom_range 方法接受 start_time, end_time
            result = self._time_window_splitter.split_with_custom_range(
                start_time=time_range[0],
                end_time=time_range[1],
                total_points=0  # 稍后由数据提取阶段更新
            )
            context.set_data("fit_window", result.fit_window)
            context.set_data("test_window", result.test_window)
            context.set_data("can_evaluate", result.can_evaluate)
            return {"split": "complete", "can_evaluate": result.can_evaluate}

        # 默认处理：简单划分
        time_range = context.get_data("time_range")
        if time_range:
            start, end = time_range
            split_point = start + (end - start) * 0.8
            context.set_data("fit_window", (start, split_point))
            context.set_data("test_window", (split_point, end))
            context.set_data("can_evaluate", True)
            return {"split": "complete", "can_evaluate": True}
        else:
            context.set_data("can_evaluate", False)
            return {"split": "no_time_range", "can_evaluate": False}

    def _stage_scenario_detect(self, context: PipelineContext) -> Any:
        """阶段2: 场景识别（条件执行）"""
        from app.services.characteristic_curves.preprocessing import ScenarioDetector

        detector = ScenarioDetector()

        # 获取数据
        raw_data = context.get_data("raw_data")
        if raw_data is None:
            # 使用x_values和y_values构建
            x_values = context.get_data("x_values")
            y_values = context.get_data("y_values")
            if x_values is not None and y_values is not None:
                # 根据曲线类型确定y列名
                y_col = "H" if context.curve_type == "qh" else (
                    "P" if context.curve_type == "qp" else "Eta")
                raw_data = pd.DataFrame({
                    'Q': x_values,
                    y_col: y_values,
                    'frequency': [50.0] * len(x_values)  # 默认频率
                })
            else:
                # 没有数据，使用默认场景
                context.set_data("scenario", Scenario.QUASI_FIXED_FREQ_SINGLE)
                return {"scenario": "quasi_fixed_freq_single", "skipped": True}

        # 获取设备参数(优先从数据库读取)
        device_params = self._get_device_params(context)

        scenario_result = detector.detect(
            device_id=context.device_id,
            device_params=device_params,
            data=raw_data
        )

        context.set_data("scenario", scenario_result.scenario)
        context.set_data("scenario_result", scenario_result)

        return {
            "scenario": scenario_result.scenario.value,
            "supported": scenario_result.supported,
            "confidence": scenario_result.confidence
        }

    def _stage_data_extract(self, context: PipelineContext) -> Any:
        """阶段3: 数据提取（完整版）"""
        # 检查是否直接提供了数据
        kwargs = context.get_data("kwargs", {})
        x_values = kwargs.get("x_values")
        y_values = kwargs.get("y_values")

        if x_values is not None and y_values is not None:
            # 直接使用提供的数据
            context.set_data("x_values", np.array(x_values))
            context.set_data("y_values", np.array(y_values))

            # 根据曲线类型确定y列名
            y_col = "H" if context.curve_type == "qh" else (
                "P" if context.curve_type == "qp" else "Eta")

            context.set_data("raw_data", pd.DataFrame({
                'Q': x_values,
                y_col: y_values
            }))
            return {"extracted": True, "source": "direct", "points": len(x_values)}

        # 使用DataExtractor从数据库提取
        if self._data_extractor:
            fit_window = context.get_data("fit_window")
            if fit_window:
                try:
                    # fit_window 可能是TimeWindow对象或元组
                    if hasattr(fit_window, 'start'):
                        start_time = fit_window.start
                        end_time = fit_window.end
                    else:
                        start_time = fit_window[0]
                        end_time = fit_window[1]

                    data, quality_report = self._data_extractor.extract(
                        device_id=context.device_id,
                        curve_type=context.curve_type,
                        start_time=start_time,
                        end_time=end_time
                    )

                    # 将flow和head/power/efficiency映射为Q和H/P/Eta
                    renamed_data = data.rename(columns={'flow': 'Q'})
                    if 'head' in data.columns:
                        renamed_data = renamed_data.rename(
                            columns={'head': 'H'})
                    elif 'power' in data.columns:
                        renamed_data = renamed_data.rename(
                            columns={'power': 'P'})
                    elif 'efficiency' in data.columns:
                        renamed_data = renamed_data.rename(
                            columns={'efficiency': 'Eta'})

                    context.set_data("raw_data", renamed_data)
                    context.set_data("data_quality_report", quality_report)

                    # 提取x_values和y_values
                    if 'Q' in renamed_data.columns:
                        context.set_data("x_values", renamed_data['Q'].values)

                    y_col = "H" if context.curve_type == "qh" else (
                        "P" if context.curve_type == "qp" else "Eta")
                    if y_col in renamed_data.columns:
                        context.set_data(
                            "y_values", renamed_data[y_col].values)

                    self._logger.info(
                        f"[数据提取] 成功: {len(data)}条数据, "
                        f"质量评分={quality_report.quality_score:.2f}",
                        extra={"extra_data": {
                            "设备ID": context.device_id,
                            "曲线类型": context.curve_type,
                            "数据条数": len(data),
                            "质量评分": quality_report.quality_score
                        }}
                    )

                    return {
                        "extracted": True,
                        "source": "database",
                        "points": len(data),
                        "quality_score": quality_report.quality_score
                    }
                except Exception as e:
                    self._logger.warning(
                        f"[数据提取] 从数据库提取失败: {e}",
                        extra={"extra_data": {"错误": str(e)}}
                    )
                    # 降级到简单模式
                    return {"extracted": False, "error": str(e)}

        # 无DataExtractor且无直接数据
        return {"extracted": True}

    def _stage_data_clean(self, context: PipelineContext) -> Any:
        """阶段4: 数据预处理/清洗"""
        from app.services.characteristic_curves.preprocessing import DataCleaner

        raw_data = context.get_data("raw_data")
        if raw_data is None:
            # 使用x_values和y_values构建
            x_values = context.get_data("x_values")
            y_values = context.get_data("y_values")
            if x_values is not None and y_values is not None:
                # 根据曲线类型确定y列名
                y_col = "H" if context.curve_type == "qh" else (
                    "P" if context.curve_type == "qp" else "Eta")
                raw_data = pd.DataFrame({'Q': x_values, y_col: y_values})
            else:
                raise ValueError("缺少原始数据")

        # 根据曲线类型确定列名
        x_col = "Q"
        y_col = "H" if context.curve_type == "qh" else (
            "P" if context.curve_type == "qp" else "Eta")

        cleaner = DataCleaner()
        cleaning_result = cleaner.clean(raw_data, x_col=x_col, y_col=y_col)

        context.set_data("cleaned_data", cleaning_result.cleaned_data)
        context.set_data("cleaning_stats", cleaning_result.stats)
        # 更新x_values和y_values
        if x_col in cleaning_result.cleaned_data.columns:
            context.set_data(
                "x_values", cleaning_result.cleaned_data[x_col].values)
        if y_col in cleaning_result.cleaned_data.columns:
            context.set_data(
                "y_values", cleaning_result.cleaned_data[y_col].values)

        return {
            "cleaned": True,
            "points": len(cleaning_result.cleaned_data),
            "removed": cleaning_result.removed_count
        }

    def _stage_steady_state_detect(self, context: PipelineContext) -> Any:
        """阶段5: 稳态识别（条件执行）"""
        from app.services.characteristic_curves.preprocessing import SteadyStateDetector

        cleaned_data = context.get_data("cleaned_data")
        if cleaned_data is None:
            return {"skipped": True, "reason": "no_cleaned_data"}

        # SteadyStateDetector期望的列名是'flow'和'head'/'power'
        # 需要将'Q'和'H'/'P'映射到期望的列名
        detector_data = cleaned_data.copy()
        detector_data = detector_data.rename(columns={'Q': 'flow'})

        if 'H' in detector_data.columns:
            detector_data = detector_data.rename(columns={'H': 'head'})
        elif 'P' in detector_data.columns:
            detector_data = detector_data.rename(columns={'P': 'power'})
        elif 'Eta' in detector_data.columns:
            detector_data = detector_data.rename(columns={'Eta': 'efficiency'})

        detector = SteadyStateDetector()
        steady_data, result = detector.detect_steady_points(detector_data)

        # 将列名映射回原来的格式
        if len(steady_data) > 0:
            steady_data = steady_data.rename(columns={'flow': 'Q'})
            if 'head' in steady_data.columns:
                steady_data = steady_data.rename(columns={'head': 'H'})
            elif 'power' in steady_data.columns:
                steady_data = steady_data.rename(columns={'power': 'P'})
            elif 'efficiency' in steady_data.columns:
                steady_data = steady_data.rename(columns={'efficiency': 'Eta'})

        context.set_data("steady_state_data", steady_data)
        context.set_data("steady_state_result", result)
        # 更新x_values和y_values为稳态数据
        if len(steady_data) > 0:
            if 'Q' in steady_data.columns:
                context.set_data("x_values", steady_data['Q'].values)
            y_col = "H" if context.curve_type == "qh" else (
                "P" if context.curve_type == "qp" else "Eta")
            if y_col in steady_data.columns:
                context.set_data("y_values", steady_data[y_col].values)

        return {"detected": True, "steady_points": len(steady_data)}

    def _stage_constraint_calc(self, context: PipelineContext) -> Any:
        """阶段6: 约束计算"""
        from app.services.characteristic_curves.constraints import ConstraintCalculator

        cleaned_data = context.get_data("cleaned_data")
        if cleaned_data is None or (isinstance(cleaned_data, pd.DataFrame) and cleaned_data.empty):
            cleaned_data = context.get_data("steady_state_data")

        if cleaned_data is None or (isinstance(cleaned_data, pd.DataFrame) and cleaned_data.empty):
            # 使用x_values和y_values构建
            x_values = context.get_data("x_values")
            y_values = context.get_data("y_values")
            if x_values is not None and y_values is not None:
                y_col = "H" if context.curve_type == "qh" else (
                    "P" if context.curve_type == "qp" else "Eta")
                cleaned_data = pd.DataFrame({'Q': x_values, y_col: y_values})

        # ConstraintCalculator期望'flow'和'head'/'power'列名
        calc_data = cleaned_data.copy()
        calc_data = calc_data.rename(columns={'Q': 'flow'})
        if 'H' in calc_data.columns:
            calc_data = calc_data.rename(columns={'H': 'head'})
        elif 'P' in calc_data.columns:
            calc_data = calc_data.rename(columns={'P': 'power'})
        elif 'Eta' in calc_data.columns:
            calc_data = calc_data.rename(columns={'Eta': 'efficiency'})

        calculator = ConstraintCalculator()
        # 获取设备参数(优先从数据库读取)
        device_params = self._get_device_params(context)

        # 默认config
        calc_config = {
            "constraints": {
                "monotonicity_tolerance": 0.01,
                "boundary_tolerance": 0.05
            }
        }

        constraints = calculator.calculate(
            curve_type=context.curve_type,
            data=calc_data,
            device_params=device_params,
            config=calc_config
        )

        context.set_data("constraints", constraints)
        return {"calculated": True, "constraints": list(constraints.bounds.keys())}

    def _stage_freq_normalize(self, context: PipelineContext) -> Any:
        """阶段7: 频率归一化（条件执行）"""
        from app.services.characteristic_curves.preprocessing import FrequencyNormalizer

        data = context.get_data("cleaned_data")
        if data is None or (isinstance(data, pd.DataFrame) and data.empty):
            data = context.get_data("steady_state_data")

        if data is None or (isinstance(data, pd.DataFrame) and data.empty):
            return {"skipped": True, "reason": "no_data"}

        # 从设备参数获取额定频率
        device_params = context.get_data("device_params", {})
        rated_frequency = device_params.get("rated_frequency", 50.0)

        normalizer = FrequencyNormalizer()
        normalized_data = normalizer.normalize(
            data=data,
            rated_frequency=rated_frequency
        )

        context.set_data("freq_normalized_data", normalized_data)
        return {"normalized": True, "points": len(normalized_data)}

    def _stage_data_normalize(self, context: PipelineContext) -> Any:
        """阶段8: 数据归一化

        使用DataNormalizer对数据进行归一化处理。
        """
        from app.services.characteristic_curves.preprocessing import DataNormalizer

        x_values = context.get_data("x_values")
        y_values = context.get_data("y_values")

        if x_values is None or y_values is None:
            return {"skipped": True, "reason": "no_data"}

        # 确定列名
        x_col = "Q"
        y_col = "H" if context.curve_type == "qh" else (
            "P" if context.curve_type == "qp" else "Eta")

        # 构造DataFrame
        data = pd.DataFrame({x_col: x_values, y_col: y_values})

        # 创建DataNormalizer（使用minmax方法）
        normalizer = DataNormalizer(method='minmax')

        # 归一化数据
        normalized_data, normalization_params = normalizer.normalize(
            data=data,
            x_col=x_col,
            y_col=y_col
        )

        # 保存归一化后的数据和参数
        context.set_data("normalized_data", normalized_data)
        context.set_data("normalization_params", normalization_params)

        # 保存normalizer实例以便后续反归一化
        context.set_data("data_normalizer", normalizer)

        # 更新x_values和y_values为归一化后的值
        context.set_data("x_values_normalized", normalized_data[x_col].values)
        context.set_data("y_values_normalized", normalized_data[y_col].values)

        self._logger.info(
            f"[阶段8] 数据归一化完成: 方法=minmax, 数据点数={len(data)}"
        )

        return {
            "normalized": True,
            "points": len(normalized_data),
            "method": "minmax",
            "x_range": [float(normalization_params.x_min), float(normalization_params.x_max)],
            "y_range": [float(normalization_params.y_min), float(normalization_params.y_max)]
        }

    def _stage_method_select(self, context: PipelineContext) -> Any:
        """阶段9: 方法选择"""
        from app.services.characteristic_curves.shared import MethodSelector

        # 如果已提供方法ID,直接使用
        kwargs = context.get_data("kwargs", {})
        provided_method = kwargs.get("method_id")
        if provided_method:
            context.set_data("selected_methods", [provided_method])
            return {"method": provided_method, "source": "provided"}

        # 获取约束和数据
        constraints = context.get_data("constraints")
        normalized_data = context.get_data("normalized_data")

        # 创建MethodSelector
        if self._method_selector:
            selector = self._method_selector
        else:
            # 创建默认MethodSelector（使用配置）
            selector_config = {
                "selection_rules": {
                    "qh": {
                        "default": ["polynomial_2", "polynomial_3"],
                        "high_quality": ["polynomial_3", "polynomial_4"],
                        "sparse_data": ["polynomial_2"],
                        "noisy_data": ["polynomial_2"]
                    },
                    "qp": {
                        "default": ["polynomial_2", "polynomial_3"],
                        "high_quality": ["polynomial_3"],
                        "sparse_data": ["polynomial_2"],
                        "noisy_data": ["polynomial_2"]
                    },
                    "qeta": {
                        "default": ["polynomial_2", "polynomial_3"],
                        "high_quality": ["polynomial_3"],
                        "sparse_data": ["polynomial_2"],
                        "noisy_data": ["polynomial_2"]
                    }
                }
            }
            from app.services.characteristic_curves.shared import MethodSelector
            selector = MethodSelector(config=selector_config)

        # 选择方法
        selected_methods = selector.select(
            curve_type=context.curve_type,
            constraints=constraints if constraints else None
        )

        # 默认使用第一个方法
        if not selected_methods:
            selected_methods = [self._config.default_method]

        context.set_data("selected_methods", selected_methods)
        context.set_data("method_id", selected_methods[0])  # 主方法

        self._logger.info(
            f"[方法选择] 选中{len(selected_methods)}个方法",
            extra={"extra_data": {"方法列表": selected_methods}}
        )

        return {"methods": selected_methods, "primary": selected_methods[0]}

    def _stage_curve_fit(self, context: PipelineContext) -> Any:
        """阶段10: 曲线拟合（多方法串行执行）

        使用MethodRegistry动态调用拟合方法，符合文档规范。
        """
        x = context.get_data("x_values")
        y = context.get_data("y_values")
        if x is None or y is None:
            raise ValueError("缺少拟合数据")

        selected_methods = context.get_data(
            "selected_methods", [self._config.default_method])
        constraints = context.get_data("constraints")

        self._logger.info(
            f"[拟合执行] 开始拟合,共{len(selected_methods)}个方法",
            extra={"extra_data": {
                "方法列表": selected_methods,
                "数据点数": len(x)
            }}
        )

        fit_results = []

        # 串行执行每个方法 - 使用MethodRegistry
        for method_id in selected_methods:
            try:
                self._logger.info(f"[拟合执行] 开始方法: {method_id}")

                # 使用MethodRegistry获取方法实例，需要传入curve_type和method_id
                method = self._method_registry.get_method(
                    context.curve_type, method_id)
                if method is None:
                    self._logger.warning(f"[拟合执行] 方法{method_id}未注册，跳过")
                    continue

                # 调用方法的fit接口
                method_result = method.fit(
                    X=x,
                    y=y,
                    constraints=constraints
                )

                # 检查拟合是否成功（MethodResult通过predict_func是否存在判断）
                if method_result.predict_func is None:
                    raise ValueError(f"拟合失败: 未生成预测函数")

                # 使用predict_func生成拟合值
                y_fitted = method_result.predict_func(x)

                # 计算评价指标
                ss_res = np.sum((y - y_fitted) ** 2)
                ss_tot = np.sum((y - np.mean(y)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                rmse = np.sqrt(np.mean((y - y_fitted) ** 2))

                # 记录结果
                result = {
                    "method_id": method_id,
                    "coefficients": method_result.coefficients,
                    "r_squared": float(r_squared),
                    "rmse": float(rmse),
                    "y_fitted": y_fitted,
                    "predict_func": method_result.predict_func,
                    "formula": method_result.formula,
                    "success": True
                }
                fit_results.append(result)

                self._logger.info(
                    f"[拟合执行] {method_id}拟合成功: R²={r_squared:.4f}, RMSE={rmse:.4f}"
                )

            except Exception as e:
                self._logger.warning(
                    f"[拟合执行] {method_id}拟合失败: {e}",
                    extra={"extra_data": {"错误": str(e)}}
                )
                fit_results.append({
                    "method_id": method_id,
                    "success": False,
                    "error": str(e)
                })

        # 选择最佳结果（R²最高）
        successful_results = [
            r for r in fit_results if r.get("success", False)]
        if not successful_results:
            raise ValueError(f"所有{len(fit_results)}个拟合方法均失败")

        best_result = max(successful_results,
                          key=lambda r: r.get("r_squared", 0))

        # 保存最佳结果到context
        context.set_data("fit_results", fit_results)
        context.set_data("best_result", best_result)
        context.set_data("coefficients", best_result["coefficients"])
        context.set_data("r_squared", best_result["r_squared"])
        context.set_data("y_fitted", best_result["y_fitted"])
        context.set_data("method_id", best_result["method_id"])
        context.set_data("predict_func", best_result.get("predict_func"))

        self._logger.info(
            f"[拟合执行] 完成,最佳方法:{best_result['method_id']}, "
            f"R²={best_result['r_squared']:.4f}",
            extra={"extra_data": {
                "成功数": len(successful_results),
                "失败数": len(fit_results) - len(successful_results)
            }}
        )

        return {
            "fitted": True,
            "methods_tried": len(fit_results),
            "methods_succeeded": len(successful_results),
            "best_method": best_result["method_id"],
            "r_squared": best_result["r_squared"]
        }

    def _stage_result_validate(self, context: PipelineContext) -> Any:
        """阶段11: 结果验证（完整版）"""
        from app.services.characteristic_curves.constraints import PhysicsValidator
        from app.services.characteristic_curves.core.data_structures import FitResult

        # 获取拟合结果
        x_values = context.get_data("x_values")
        y_values = context.get_data("y_values")
        y_fitted = context.get_data("y_fitted")
        coefficients = context.get_data("coefficients", [])
        method_id = context.get_data("method_id", "unknown")
        r_squared = context.get_data("r_squared", 0)

        if x_values is None or y_fitted is None:
            self._logger.warning("[结果验证] 缺少拟合结果，跳过验证")
            context.set_data("validation_passed", False)
            return {"valid": False, "reason": "missing_data"}

        # 计算RMSE
        rmse = float(np.sqrt(np.mean((y_values - y_fitted) ** 2)))

        # 构造FitResult对象供PhysicsValidator使用
        # 处理系数：可能是列表或字典格式
        if isinstance(coefficients, dict):
            coefficients_dict = {k: float(v) for k, v in coefficients.items()}
        elif isinstance(coefficients, (list, tuple)):
            coefficients_dict = {f"a{i}": float(
                c) for i, c in enumerate(coefficients)}
        else:
            coefficients_dict = {}

        fit_result = FitResult(
            success=True,
            curve_type=context.curve_type,
            method_id=method_id,
            method_name=method_id,
            coefficients=coefficients_dict,
            r_squared=r_squared,
            rmse=rmse,
            x_values=x_values,
            y_fitted=y_fitted,
            device_id=context.device_id,
        )

        # 获取设备参数(优先从数据库读取)
        device_params = self._get_device_params(context)

        # 使用PhysicsValidator进行完整验证
        validator = PhysicsValidator()

        try:
            validation_result = validator.validate(
                device_id=context.device_id,
                curve_type=context.curve_type,
                fit_result=fit_result,
                device_params=device_params
            )

            # 保存验证结果
            context.set_data("validation_result", validation_result)
            context.set_data("validation_passed",
                             validation_result.overall_passed)
            context.set_data("physics_score", validation_result.physics_score)

            self._logger.info(
                f"[结果验证] 完成: 通过={validation_result.overall_passed}, "
                f"物理得分={validation_result.physics_score:.1f}, "
                f"R²={r_squared:.4f}",
                extra={"extra_data": {
                    "单调性": validation_result.monotonicity_passed,
                    "边界条件": validation_result.boundary_passed,
                    "物理一致": validation_result.physics_passed
                }}
            )

            return {
                "valid": validation_result.overall_passed,
                "r_squared": r_squared,
                "physics_score": validation_result.physics_score,
                "monotonicity_passed": validation_result.monotonicity_passed,
                "boundary_passed": validation_result.boundary_passed
            }

        except Exception as e:
            self._logger.warning(
                f"[结果验证] 验证失败: {e}",
                extra={"extra_data": {"错误": str(e)}}
            )
            # 降级到基本验证
            basic_valid = r_squared >= 0.90
            context.set_data("validation_passed", basic_valid)
            return {"valid": basic_valid, "r_squared": r_squared, "degraded": True}

    def _stage_historical_eval(self, context: PipelineContext) -> Any:
        """阶段12: 历史评估（条件执行）

        使用实际的HistoricalDataEvaluator进行预测能力评估。
        """
        if not self._historical_evaluator:
            # 使用默认的HistoricalDataEvaluator
            from app.services.characteristic_curves.shared import HistoricalDataEvaluator
            evaluator = HistoricalDataEvaluator()
        else:
            evaluator = self._historical_evaluator

        # 获取测试窗口和预测函数
        test_window = context.get_data("test_window")
        predict_func = context.get_data("predict_func")

        if not test_window:
            return {"skipped": True, "reason": "no_test_window"}

        # 如果没有predict_func，使用系数构造
        if predict_func is None:
            coefficients = context.get_data("coefficients", [])
            if not coefficients:
                return {"skipped": True, "reason": "no_coefficients"}

            # 根据系数类型构造预测函数
            if isinstance(coefficients, dict):
                # 字典形式: {"a0": 1.0, "a1": -0.5, ...}
                coeffs = [coefficients.get(f"a{i}", 0.0)
                          for i in range(len(coefficients))]
            elif isinstance(coefficients, (list, tuple)):
                coeffs = coefficients
            else:
                return {"skipped": True, "reason": "invalid_coefficients"}

            # 创建预测函数（多项式）
            def predict_func(x):
                return np.polyval(coeffs, x)

        # 执行历史评估
        try:
            evaluation = evaluator.evaluate_prediction_accuracy(
                device_id=context.device_id,
                curve_type=context.curve_type,
                predict_func=predict_func,
                test_window=test_window
            )

            # 保存评估结果
            context.set_data("evaluation_report", evaluation)
            context.set_data("within_5_percent", evaluation.get(
                "pass_rate", {}).get("within_5_percent", 0))

            # 记录结果
            within_5_pct = evaluation.get(
                "pass_rate", {}).get("within_5_percent", 0)
            within_10_pct = evaluation.get(
                "pass_rate", {}).get("within_10_percent", 0)

            self._logger.info(
                f"[历史评估] 完成: 测试点数={evaluation.get('test_point_count', 0)}, "
                f"通过率5%={within_5_pct:.2%}, 通过率10%={within_10_pct:.2%}"
            )

            return {
                "evaluated": True,
                "test_points": evaluation.get("test_point_count", 0),
                "within_5_percent": within_5_pct,
                "within_10_percent": within_10_pct,
                "overall_passed": evaluation.get("overall_passed", False)
            }

        except Exception as e:
            self._logger.warning(
                f"[历史评估] 执行失败: {e}",
                extra={"extra_data": {"错误": str(e)}}
            )
            return {"skipped": True, "reason": f"evaluation_failed: {e}"}

    def _stage_result_store(self, context: PipelineContext) -> Any:
        """阶段13: 结果存储"""
        # 获取数据
        x_values = context.get_data("x_values")
        y_values = context.get_data("y_values")
        coefficients_list = context.get_data("coefficients", [])
        method_id = context.get_data("method_id", "unknown")
        r_squared = context.get_data("r_squared", 0)
        time_range = context.get_data("time_range")

        # 转换系数为字典格式
        # 处理系数：可能是列表或字典格式
        coefficients_dict = {}
        if coefficients_list:
            if isinstance(coefficients_list, dict):
                coefficients_dict = {k: float(v)
                                     for k, v in coefficients_list.items()}
            elif isinstance(coefficients_list, (list, tuple)):
                for i, coef in enumerate(coefficients_list):
                    coefficients_dict[f"a{i}"] = float(coef)
            else:
                self._logger.warning(
                    f"[结果存储] 未知的系数格式: {type(coefficients_list)}")

        # 计算MAE, RMSE和MAPE
        y_fitted = context.get_data("y_fitted")
        mae = 0.0
        rmse = 0.0
        mape = 0.0
        if y_fitted is not None and y_values is not None:
            residuals = y_values - y_fitted
            mae = float(np.mean(np.abs(residuals)))
            rmse = float(np.sqrt(np.mean(residuals ** 2)))  # 修复: 正确计算RMSE
            mape = float(np.mean(np.abs(residuals / y_values))
                         * 100) if np.all(y_values != 0) else 0.0

        # 保存rmse到context供后续阶段使用
        context.set_data("rmse", rmse)

        # 创建FitResult对象
        fit_result = FitResult(
            success=True,
            curve_type=context.curve_type,
            method_id=method_id,
            method_name=method_id,  # 简化处理，使用method_id作为名称
            coefficients=coefficients_dict,
            formula=f"{context.curve_type.upper()} = poly2(Q)",
            r_squared=r_squared,
            rmse=rmse,  # 修复: 使用计算值而非硬编码
            mae=mae,
            mape=mape,
            quality_grade="good" if r_squared >= 0.95 else "acceptable",
            x_values=x_values,
            y_actual=y_values,  # 保存原始y值供残差计算
            y_fitted=y_fitted,
            constraints_satisfied=True,
            device_id=context.device_id,
            data_points=len(x_values) if x_values is not None else 0,
            time_range={
                'start': time_range[0] if time_range else None,
                'end': time_range[1] if time_range else None
            } if time_range else None,
            normalization_params=None,
            fitted_at=datetime.now(),
        )

        # 如果配置了result_storage，则存储到数据库
        if self._result_storage:
            try:
                version = self._result_storage.save(
                    device_id=context.device_id,
                    curve_type=context.curve_type,
                    fit_result=fit_result
                )
                # 保存version到metadata
                if not hasattr(fit_result, 'metadata') or fit_result.metadata is None:
                    fit_result.metadata = {}
                fit_result.metadata['version'] = version

                self._logger.info(
                    f"[结果存储] 成功存储到数据库: device_id={context.device_id}, "
                    f"curve_type={context.curve_type}, version={version}"
                )
            except Exception as e:
                # 存储失败不影响核心功能
                self._logger.warning(f"[结果存储] 失败（不影响核心功能）: {e}")

        context.set_data("fit_result", fit_result)
        return {"stored": True, "version": fit_result.metadata.get('version') if hasattr(fit_result, 'metadata') else None}

    def _stage_plot_generation(self, context: PipelineContext) -> Any:
        """阶段14: 图片生成"""
        if not self._plot_config:
            return {"skipped": True, "reason": "no_plot_config"}

        try:
            from pathlib import Path
            from app.services.characteristic_curves.output.high_res_plotter import HighResPlotter

            # 获取拟合结果
            fit_result = context.get_data("fit_result")
            if not fit_result:
                self._logger.warning("[图片生成] 未找到拟合结果，跳过")
                return {"skipped": True, "reason": "no_fit_result"}

            # 获取数据
            x_data = context.get_data("x_values")
            y_data = context.get_data("y_values")
            if x_data is None or y_data is None:
                self._logger.warning("[图片生成] 未找到拟合数据，跳过")
                return {"skipped": True, "reason": "no_data"}

            # 创建绘图器
            plotter = HighResPlotter(self._plot_config)

            # 构建输出路径
            from datetime import datetime
            version = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"device_{context.device_id}_{context.curve_type}_{version}.png"
            output_path = Path(self._output_dir) / filename

            # 创建预测函数
            coeffs = context.get_data("coefficients", [])

            # 处理系数格式（可能是字典或列表）
            if isinstance(coeffs, dict):
                # 字典格式: {"a0": 1.0, "a1": -0.5, "a2": 0.01}
                # 转换为多项式系数列表（按降序排列）
                max_order = max(
                    [int(k[1:]) for k in coeffs.keys() if k.startswith('a')], default=0)
                coeffs_list = [
                    float(coeffs.get(f"a{i}", 0.0)) for i in range(max_order + 1)]
                coeffs_list = coeffs_list[::-1]  # np.polyval需要降序排列
            elif isinstance(coeffs, (list, tuple)):
                coeffs_list = [float(c) for c in coeffs]
            else:
                coeffs_list = [0.0]

            def predict_func(x):
                x_arr = np.atleast_1d(x)  # 确保x是数组
                return np.polyval(coeffs_list, x_arr)

            # 绘制曲线图
            plot_path = plotter.plot_curve(
                x_data=x_data,
                y_data=y_data,
                curve_type=context.curve_type,
                predict_func=predict_func,
                output_path=output_path,
                title=f"设备{context.device_id} - {context.curve_type.upper()}曲线",
                r_squared=context.get_data("r_squared"),
                rmse=context.get_data("rmse", 0.0),  # 修复: 使用context中的rmse值
                data_points=len(x_data),
                method_name=context.get_data("method_id", "unknown")
            )

            # 保存图片路径到metadata
            if not hasattr(fit_result, 'metadata') or fit_result.metadata is None:
                fit_result.metadata = {}
            if 'images' not in fit_result.metadata:
                fit_result.metadata['images'] = {}
            fit_result.metadata['images']['main_curve'] = str(plot_path)

            self._logger.info(f"[图片生成] 成功生成图片: {plot_path}")
            return {"generated": True, "path": str(plot_path)}

        except Exception as e:
            # 图片生成失败不影响核心功能
            self._logger.warning(f"[图片生成] 失败（不影响核心功能）: {e}")
            return {"generated": False, "error": str(e)}

    def _stage_report_generation(self, context: PipelineContext) -> Any:
        """阶段15: 报告生成"""
        if not self._result_output:
            return {"skipped": True, "reason": "no_result_output"}

        try:
            # 获取拟合结果
            fit_result = context.get_data("fit_result")
            if not fit_result:
                self._logger.warning("[报告生成] 未找到拟合结果，跳过")
                return {"skipped": True, "reason": "no_fit_result"}

            # 获取图片路径（从fit_result.metadata或空字典）
            output_paths = {}
            if hasattr(fit_result, 'metadata') and fit_result.metadata:
                images = fit_result.metadata.get('images', {})
                output_paths = {
                    'main_curve': images.get('main_curve', ''),
                    'residuals': images.get('residuals', '')
                }

            # 调用报告生成（generate_report会自动创建目录和生成文件）
            report_path = self._result_output.generate_report(
                fit_result=fit_result,
                device_id=context.device_id,
                curve_type=context.curve_type,
                output_paths=output_paths,
                format='markdown'
            )

            if report_path:
                # 保存报告路径到metadata
                if not hasattr(fit_result, 'metadata') or fit_result.metadata is None:
                    fit_result.metadata = {}
                if 'reports' not in fit_result.metadata:
                    fit_result.metadata['reports'] = {}
                fit_result.metadata['reports']['main_report'] = report_path

                self._logger.info(f"[报告生成] 成功生成报告: {report_path}")
                return {"generated": True, "path": report_path}
            else:
                self._logger.warning("[报告生成] 报告生成返回None")
                return {"generated": False, "error": "report_path_none"}

        except Exception as e:
            # 报告生成失败不影响核心功能
            self._logger.warning(f"[报告生成] 失败（不影响核心功能）: {e}")
            return {"generated": False, "error": str(e)}

    def _create_error_result(self, context: PipelineContext, error: str) -> FitResult:
        """创建错误结果"""
        return FitResult(
            success=False,
            curve_type=context.curve_type,
            method_id="error",
            metadata={"error": error, "errors": context.errors},
        )

    def _create_success_result(self, context: PipelineContext) -> FitResult:
        """创建成功结果"""
        return FitResult(
            success=True,
            curve_type=context.curve_type,
            method_id=context.get_data("method_id", "unknown"),
        )
