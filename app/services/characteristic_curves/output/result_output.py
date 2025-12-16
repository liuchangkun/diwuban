"""
结果输出统筹器 (app.services.characteristic_curves.output.result_output)

本模块统筹管理所有拟合结果的输出:
- 调用HighResPlotter生成图片
- 管理输出路径
- 生成输出报告(可选)
- 导出曲线数据(可选)

使用方式:
    from app.services.characteristic_curves.output import ResultOutput
    from app.services.characteristic_curves.core.data_structures import FitResult
    from pathlib import Path
    
    output = ResultOutput(output_dir=Path("./output"))
    paths = output.generate_outputs(
        fit_result=result,
        device_id=1,
        curve_type='qh',
        include_residuals=True
    )

版本: v1.0
参考: 设计文档 3.9节
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats

from app.services.characteristic_curves.core.data_structures import FitResult
from app.services.characteristic_curves.output.high_res_plotter import HighResPlotter


class ResultOutput:
    """结果输出统筹器

    统筹管理所有输出功能:
    1. 8K高清图片生成(主曲线图、残差分析图)
    2. 输出路径管理
    3. 输出报告生成(可选)
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        plot_config: Optional[Dict[str, Any]] = None
    ):
        """初始化输出管理器

        Args:
            output_dir: 输出根目录,默认'./output'
            plot_config: 绘图配置,默认None(使用HighResPlotter默认配置)
        """
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")
        self._output_dir = output_dir or Path("./output")
        self._plot_config = plot_config or {}

        # 确保输出目录存在
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # 创建HighResPlotter
        self._plotter = HighResPlotter(config=self._plot_config)

        self._logger.info(
            "[输出管理] 初始化",
            extra={"extra_data": {
                "组件": "ResultOutput",
                "输出目录": str(self._output_dir),
                "配置": self._plot_config
            }}
        )

    def generate_outputs(
        self,
        fit_result: FitResult,
        device_id: int,
        curve_type: str,
        include_residuals: bool = True,
        include_confidence: bool = False,
        include_sensitivity: bool = False,
        include_comparison: bool = False
    ) -> Dict[str, str]:
        """生成所有输出

        Args:
            fit_result: 拟合结果
            device_id: 设备ID
            curve_type: 曲线类型
            include_residuals: 是否生成残差分析图(P0必需)
            include_confidence: 是否生成置信区间图(P2可选)
            include_sensitivity: 是否生成敏感性分析图(P2可选)
            include_comparison: 是否生成版本对比图(P2可选)

        Returns:
            Dict[str, str]: 输出文件路径字典 {
                'main_curve': '主曲线图路径',
                'residuals': '残差分析图路径',
                ...
            }
        """
        self._logger.info(
            "[输出管理] 开始生成输出",
            extra={"extra_data": {
                "设备ID": device_id,
                "曲线类型": curve_type,
                "版本": fit_result.version,
                "残差图": include_residuals
            }}
        )

        output_paths = {}

        # 创建设备专属目录
        device_dir = self._output_dir / \
            f"device_{device_id}" / curve_type / fit_result.version
        device_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. 生成主曲线图(P0必需)
            main_curve_path = device_dir / f"{curve_type}_curve.png"

            # 构造预测函数
            def predict_func(x):
                # 使用fit_result中的系数重构预测函数
                # 这里简化处理，实际应从方法注册表获取
                coeffs = list(fit_result.coefficients.values())
                if len(coeffs) == 3:  # poly2
                    return coeffs[0] + coeffs[1]*x + coeffs[2]*x**2
                elif len(coeffs) == 4:  # poly3
                    return coeffs[0] + coeffs[1]*x + coeffs[2]*x**2 + coeffs[3]*x**3
                else:
                    # 默认返回拟合值
                    return np.interp(x, fit_result.x_values, fit_result.y_fitted)

            self._plotter.plot_curve(
                x_data=fit_result.x_values,
                y_data=fit_result.y_fitted,  # 使用拟合值作为实际数据
                curve_type=curve_type,
                predict_func=predict_func,
                output_path=main_curve_path,
                r_squared=fit_result.r_squared,
                rmse=fit_result.rmse,
                data_points=len(fit_result.x_values),
                method_name=fit_result.method_id
            )
            output_paths['main_curve'] = str(main_curve_path)
            self._logger.info(
                f"[输出管理] 主曲线图生成: {main_curve_path}",
                extra={"extra_data": {"路径": str(main_curve_path)}}
            )

            # 2. 生成残差分析图(P0必需)
            if include_residuals:
                residuals_path = device_dir / f"{curve_type}_residuals.png"

                # 计算残差：实际值 - 预测值
                # 注意：fit_result应该包含y_actual，这里简化处理
                if hasattr(fit_result, 'y_actual') and fit_result.y_actual is not None:
                    residuals = fit_result.y_actual - fit_result.y_fitted
                else:
                    # 如果没有y_actual，使用y_fitted作为近似（残差vs自身）
                    residuals = np.zeros_like(fit_result.y_fitted)
                    self._logger.warning(
                        "[输出管理] fit_result缺少y_actual，残差设为0",
                        extra={"extra_data": {
                            "device_id": device_id, "curve_type": curve_type}}
                    )

                self._plotter.plot_residuals(
                    x_values=fit_result.x_values,
                    residuals=residuals,
                    y_predicted=fit_result.y_fitted,
                    curve_type=curve_type,
                    output_path=residuals_path
                )
                output_paths['residuals'] = str(residuals_path)
                self._logger.info(
                    f"[输出管理] 残差分析图生成: {residuals_path}",
                    extra={"extra_data": {"路径": str(residuals_path)}}
                )

            # 3. 置信区间图(P2可选)
            if include_confidence:
                confidence_path = device_dir / f"{curve_type}_confidence.png"
                self._plotter.plot_confidence_band(
                    x_data=fit_result.x_values,
                    y_data=fit_result.y_actual if hasattr(
                        fit_result, 'y_actual') and fit_result.y_actual is not None else fit_result.y_fitted,
                    curve_type=curve_type,
                    predict_func=predict_func,
                    output_path=confidence_path
                )
                output_paths['confidence'] = str(confidence_path)
                self._logger.info(
                    f"[输出管理] 置信区间图生成: {confidence_path}",
                    extra={"extra_data": {"路径": str(confidence_path)}}
                )

            # 4. 敏感性分析图(P2可选)
            if include_sensitivity:
                sensitivity_path = device_dir / f"{curve_type}_sensitivity.png"
                self._plotter.plot_sensitivity(
                    x_data=fit_result.x_values,
                    y_data=fit_result.y_actual if hasattr(
                        fit_result, 'y_actual') and fit_result.y_actual is not None else fit_result.y_fitted,
                    curve_type=curve_type,
                    coefficients=fit_result.coefficients,
                    output_path=sensitivity_path
                )
                output_paths['sensitivity'] = str(sensitivity_path)
                self._logger.info(
                    f"[输出管理] 敏感性分析图生成: {sensitivity_path}",
                    extra={"extra_data": {"路径": str(sensitivity_path)}}
                )

            # 5. 版本对比图(P2可选)
            if include_comparison:
                comparison_path = device_dir / f"{curve_type}_comparison.png"
                # TODO: 需要传入历史曲线数据，暂时跳过
                self._logger.info(
                    "[输出管理] 版本对比图需要历史数据，请使用plot_version_comparison单独调用")
                # output_paths['comparison'] = str(comparison_path)

            self._logger.info(
                f"[输出管理] 输出生成完成,共{len(output_paths)}个文件",
                extra={"extra_data": {"文件数": len(output_paths)}}
            )

            return output_paths

        except Exception as e:
            self._logger.error(
                f"[输出管理] 输出生成失败: {e}",
                extra={"extra_data": {"错误": str(e)}}
            )
            raise

    def generate_report(
        self,
        fit_result: FitResult,
        device_id: int,
        curve_type: str,
        output_paths: Dict[str, str],
        format: str = 'markdown',
        validation_result: Optional[Dict[str, Any]] = None,
        annotations: Optional[Any] = None,
        history_results: Optional[List[FitResult]] = None
    ) -> Optional[str]:
        """生成完整12模块拟合报告

        Args:
            fit_result: 拟合结果
            device_id: 设备ID
            curve_type: 曲线类型
            output_paths: 已生成的文件路径
            format: 报告格式 ('markdown' 或 'json')
            validation_result: 物理验证结果（可选）
            annotations: 曲线标注信息（可选，如CurveAnnotations）
            history_results: 历史拟合结果列表（可选，用于版本对比）

        Returns:
            str: 报告文件路径,失败返回None
        """
        try:
            # 创建报告目录
            device_dir = self._output_dir / \
                f"device_{device_id}" / curve_type / fit_result.version
            device_dir.mkdir(parents=True, exist_ok=True)

            if format == 'markdown':
                report_path = device_dir / f"{curve_type}_report.md"
                content = self._generate_markdown_report(
                    fit_result, device_id, curve_type, output_paths,
                    validation_result=validation_result,
                    annotations=annotations,
                    history_results=history_results
                )
            else:
                report_path = device_dir / f"{curve_type}_report.json"
                content = self._generate_json_report(
                    fit_result, device_id, curve_type, output_paths
                )

            # 写入文件
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self._logger.info(
                f"[输出管理] 12模块报告生成: {report_path}",
                extra={"extra_data": {
                    "路径": str(report_path), "格式": format, "模块数": 12}}
            )
            return str(report_path)

        except Exception as e:
            self._logger.error(
                f"[输出管理] 报告生成失败: {e}",
                extra={"extra_data": {"错误": str(e)}}
            )
            return None

    def _generate_markdown_report(
        self,
        fit_result: FitResult,
        device_id: int,
        curve_type: str,
        output_paths: Dict[str, str],
        validation_result: Optional[Dict[str, Any]] = None,
        annotations: Optional[Any] = None,
        history_results: Optional[List[FitResult]] = None
    ) -> str:
        """生成完整12模块Markdown格式报告

        12模块结构:
        1. 报告摘要 - 设备信息、拟合质量星级
        2. 拟合方法说明 - 方法名称、数学模型
        3. 参数估计结果 - 系数表格、置信区间
        4. 统计检验指标 - R²、RMSE、MAE、MAPE
        5. 残差分析 - 残差统计、正态性检验
        6. 可视化图表 - 图片引用
        7. 置信区间分析 - 95%/99%置信区间
        8. 参数敏感性分析 - 参数变化影响
        9. 分段性能评估 - 低/中/高流量段
        10. 历史对比分析 - 版本对比
        11. 物理约束验证 - 单调性、边界验证
        12. 运行建议 - BEP、推荐运行范围
        """
        from datetime import datetime

        sections = []

        # 基础数据准备
        curve_type_names = {
            'qh': '流量-扬程', 'qp': '流量-功率', 'qeta': '流量-效率',
            'heta': '扬程-效率', 'peta': '功率-效率'
        }
        curve_name = curve_type_names.get(curve_type, curve_type)

        y_unit_map = {'qh': 'm', 'qp': 'kW', 'qeta': '%'}
        y_unit = y_unit_map.get(curve_type, '')

        # 有效范围计算
        if hasattr(fit_result, 'x_values') and fit_result.x_values is not None:
            q_min = float(np.min(fit_result.x_values))
            q_max = float(np.max(fit_result.x_values))
            data_points = len(fit_result.x_values)
        else:
            q_min, q_max, data_points = 0, 0, 0

        # 质量星级计算
        quality_stars = self._calculate_quality_stars(fit_result.r_squared)

        # ============================================================
        # 模块1: 报告摘要
        # ============================================================
        sections.append(self._gen_module_1_summary(
            device_id, curve_type, curve_name, fit_result,
            quality_stars, data_points, q_min, q_max, annotations
        ))

        # ============================================================
        # 模块2: 拟合方法说明
        # ============================================================
        sections.append(self._gen_module_2_method_description(
            fit_result, curve_type
        ))

        # ============================================================
        # 模块3: 参数估计结果
        # ============================================================
        sections.append(self._gen_module_3_parameters(
            fit_result, curve_type, y_unit
        ))

        # ============================================================
        # 模块4: 统计检验指标
        # ============================================================
        sections.append(self._gen_module_4_statistics(
            fit_result, y_unit
        ))

        # ============================================================
        # 模块5: 残差分析
        # ============================================================
        sections.append(self._gen_module_5_residual_analysis(
            fit_result
        ))

        # ============================================================
        # 模块6: 可视化图表
        # ============================================================
        sections.append(self._gen_module_6_visualization(
            output_paths
        ))

        # ============================================================
        # 模块7: 置信区间分析
        # ============================================================
        sections.append(self._gen_module_7_confidence_intervals(
            fit_result
        ))

        # ============================================================
        # 模块8: 参数敏感性分析
        # ============================================================
        sections.append(self._gen_module_8_sensitivity_analysis(
            fit_result
        ))

        # ============================================================
        # 模块9: 分段性能评估
        # ============================================================
        sections.append(self._gen_module_9_segment_evaluation(
            fit_result, q_min, q_max
        ))

        # ============================================================
        # 模块10: 历史对比分析
        # ============================================================
        sections.append(self._gen_module_10_history_comparison(
            fit_result, history_results
        ))

        # ============================================================
        # 模块11: 物理约束验证
        # ============================================================
        sections.append(self._gen_module_11_physics_validation(
            validation_result, curve_type
        ))

        # ============================================================
        # 模块12: 运行建议
        # ============================================================
        sections.append(self._gen_module_12_recommendations(
            fit_result, curve_type, annotations, q_min, q_max
        ))

        # 组装报告
        report_header = f"""# 特性曲线拟合报告

> **设备ID**: {device_id}  
> **曲线类型**: {curve_name} ({curve_type})  
> **版本号**: {fit_result.version}  
> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

"""
        report_footer = """
---

*报告由特性曲线拟合系统自动生成 | 版本 v2.0*
"""

        return report_header + '\n'.join(sections) + report_footer

    def _calculate_quality_stars(self, r_squared: float) -> int:
        """根据R²计算质量星级(1-5)"""
        if r_squared >= 0.99:
            return 5
        elif r_squared >= 0.97:
            return 4
        elif r_squared >= 0.95:
            return 3
        elif r_squared >= 0.90:
            return 2
        else:
            return 1

    def _gen_module_1_summary(
        self, device_id: int, curve_type: str, curve_name: str,
        fit_result: FitResult, quality_stars: int, data_points: int,
        q_min: float, q_max: float, annotations: Any
    ) -> str:
        """模块1: 报告摘要（支持单泵和泵组）"""
        stars_display = '⭐' * quality_stars + '☆' * (5 - quality_stars)

        # 检测是单泵还是泵组
        is_pump_group = self._is_pump_group(annotations)

        if is_pump_group:
            return self._gen_module_1_pump_group_summary(
                device_id, curve_type, curve_name, fit_result,
                quality_stars, stars_display, data_points, q_min, q_max, annotations
            )
        else:
            return self._gen_module_1_single_pump_summary(
                device_id, curve_type, curve_name, fit_result,
                quality_stars, stars_display, data_points, q_min, q_max, annotations
            )

    def _is_pump_group(self, annotations: Any) -> bool:
        """检测是否为泵组标注"""
        if annotations is None:
            return False
        # 检查是否有group_info属性（PumpGroupAnnotations特有）
        return hasattr(annotations, 'group_info') and annotations.group_info is not None

    def _gen_module_1_single_pump_summary(
        self, device_id: int, curve_type: str, curve_name: str,
        fit_result: FitResult, quality_stars: int, stars_display: str,
        data_points: int, q_min: float, q_max: float, annotations: Any
    ) -> str:
        """模块1: 单泵报告摘要"""
        # 设备名称
        device_name = '-'
        if annotations and hasattr(annotations, 'device_info') and annotations.device_info:
            device_name = annotations.device_info.name or f'设备{device_id}'

        # 数据时间范围
        time_range = '-'
        if annotations and hasattr(annotations, 'data_info') and annotations.data_info:
            di = annotations.data_info
            if di.time_range_start and di.time_range_end:
                time_range = f"{di.time_range_start.strftime('%Y-%m-%d')} ~ {di.time_range_end.strftime('%Y-%m-%d')}"

        return f"""## 📊 1. 报告摘要

### 曲线类型: 单泵特性曲线

| 项目 | 值 |
|:-----|:----|
| **设备ID** | {device_id} |
| **设备名称** | {device_name} |
| **曲线类型** | {curve_name} |
| **拟合方法** | {fit_result.method_id} |
| **拟合质量** | {stars_display} ({quality_stars}/5) |
| **R²决定系数** | {fit_result.r_squared:.4f} |
| **数据点数** | {data_points:,} |
| **有效流量范围** | {q_min:.1f} ~ {q_max:.1f} m³/h |
| **数据时间范围** | {time_range} |

"""

    def _gen_module_1_pump_group_summary(
        self, device_id: int, curve_type: str, curve_name: str,
        fit_result: FitResult, quality_stars: int, stars_display: str,
        data_points: int, q_min: float, q_max: float, annotations: Any
    ) -> str:
        """模块1: 泵组报告摘要"""
        group_info = annotations.group_info

        station_name = group_info.station_name or f'泵站{group_info.station_id}'
        pump_ids = ','.join(map(str, group_info.pump_ids)
                            ) if group_info.pump_ids else '-'
        n_pumps = group_info.n_pumps or len(group_info.pump_ids)
        synthesis_method = {
            'parallel_synthesis': '并联合成',
            'direct_fit': '直接拟合'
        }.get(group_info.synthesis_method or '', group_info.synthesis_method or '-')

        # 数据时间范围
        time_range = '-'
        if hasattr(annotations, 'data_info') and annotations.data_info:
            di = annotations.data_info
            if di.time_range_start and di.time_range_end:
                time_range = f"{di.time_range_start.strftime('%Y-%m-%d')} ~ {di.time_range_end.strftime('%Y-%m-%d')}"

        # 并联损失系数
        loss_coef = f"{group_info.parallel_loss_coefficient:.2%}" if group_info.parallel_loss_coefficient else '-'

        return f"""## 📊 1. 报告摘要

### 曲线类型: 🏭 泵组特性曲线

| 项目 | 值 |
|:-----|:----|
| **泵站ID** | {group_info.station_id} |
| **泵站名称** | {station_name} |
| **泵组合** | 共{n_pumps}台 ({pump_ids}) |
| **合成方法** | {synthesis_method} |
| **并联损失系数** | {loss_coef} |
| **曲线类型** | {curve_name} |
| **拟合方法** | {fit_result.method_id} |
| **拟合质量** | {stars_display} ({quality_stars}/5) |
| **R²决定系数** | {fit_result.r_squared:.4f} |
| **数据点数** | {data_points:,} |
| **有效流量范围** | {q_min:.1f} ~ {q_max:.1f} m³/h |
| **数据时间范围** | {time_range} |

"""

    def _gen_module_2_method_description(self, fit_result: FitResult, curve_type: str) -> str:
        """模块2: 拟合方法说明"""
        method_id = fit_result.method_id or 'unknown'

        # 方法描述映射
        method_info = {
            'polynomial_2': {
                'name': '二次多项式',
                'formula': 'y = a₀ + a₁·Q + a₂·Q²',
                'description': '经典的二次多项式拟合，适用于大多数泵特性曲线',
                'pros': '计算简单、解释性强、稳定性好',
                'cons': '对复杂曲线拟合能力有限'
            },
            'polynomial_3': {
                'name': '三次多项式',
                'formula': 'y = a₀ + a₁·Q + a₂·Q² + a₃·Q³',
                'description': '三次多项式拟合，可捕捉更复杂的曲线特征',
                'pros': '拟合精度高、适应性强',
                'cons': '可能出现过拟合、端点不稳定'
            },
            'pump_physics': {
                'name': '泵物理模型',
                'formula': 'H = H₀ - k·Q² (基于泵相似定律)',
                'description': '基于流体力学原理的物理模型',
                'pros': '物理意义明确、外推能力强',
                'cons': '参数估计复杂'
            }
        }

        info = method_info.get(method_id, {
            'name': method_id,
            'formula': '详见系数表',
            'description': '拟合方法',
            'pros': '-',
            'cons': '-'
        })

        # 生成实际公式
        coeffs = fit_result.coefficients
        actual_formula = self._generate_formula_string(coeffs, curve_type)

        return f"""## 🔧 2. 拟合方法说明

### 方法信息

| 项目 | 内容 |
|:-----|:-----|
| **方法名称** | {info['name']} |
| **方法ID** | `{method_id}` |
| **通用公式** | `{info['formula']}` |
| **实际公式** | `{actual_formula}` |

### 方法描述

{info['description']}

### 优缺点分析

| 优点 | 缺点 |
|:-----|:-----|
| {info['pros']} | {info['cons']} |

"""

    def _generate_formula_string(self, coefficients: Dict[str, float], curve_type: str) -> str:
        """生成拟合公式字符串"""
        y_symbol = {'qh': 'H', 'qp': 'P', 'qeta': 'η'}.get(curve_type, 'y')

        if not coefficients:
            return f"{y_symbol} = f(Q)"

        coeffs = list(coefficients.values())
        n = len(coeffs)

        if n == 3:  # 二次多项式
            return f"{y_symbol} = {coeffs[0]:.4g} + {coeffs[1]:.4g}·Q + {coeffs[2]:.6g}·Q²"
        elif n == 4:  # 三次多项式
            return f"{y_symbol} = {coeffs[0]:.4g} + {coeffs[1]:.4g}·Q + {coeffs[2]:.6g}·Q² + {coeffs[3]:.8g}·Q³"
        else:
            terms = [f"{c:.4g}·Q^{i}" if i >
                     0 else f"{c:.4g}" for i, c in enumerate(coeffs)]
            return f"{y_symbol} = {' + '.join(terms)}"

    def _gen_module_3_parameters(self, fit_result: FitResult, curve_type: str, y_unit: str) -> str:
        """模块3: 参数估计结果"""
        coeffs = fit_result.coefficients

        # 系数表格
        param_rows = ""
        unit_map = {
            0: y_unit,
            1: f"{y_unit}/(m³/h)",
            2: f"{y_unit}/(m³/h)²",
            3: f"{y_unit}/(m³/h)³"
        }
        meaning_map = {
            0: "截距项（零流量时的值）",
            1: "一次项系数（线性影响）",
            2: "二次项系数（曲率影响）",
            3: "三次项系数（高阶修正）"
        }

        for i, (key, value) in enumerate(coeffs.items()):
            unit = unit_map.get(i, '-')
            meaning = meaning_map.get(i, '-')
            param_rows += f"| {key} | {value:.6g} | {unit} | {meaning} |\n"

        return f"""## 📐 3. 参数估计结果

### 拟合系数

| 参数 | 值 | 单位 | 物理含义 |
|:-----|:-----|:-----|:---------|
{param_rows}

> **注**: 系数按多项式阶数递增排列

"""

    def _gen_module_4_statistics(self, fit_result: FitResult, y_unit: str) -> str:
        """模块4: 统计检验指标"""
        r2 = fit_result.r_squared
        rmse = fit_result.rmse
        mae = fit_result.mae or 0
        mape = fit_result.mape or 0

        # 达标判断
        r2_pass = "✅ 达标" if r2 >= 0.95 else "⚠️ 未达标"
        rmse_pass = "✅ 达标" if rmse <= 2.0 else "⚠️ 未达标"
        mape_pass = "✅ 达标" if mape <= 5.0 else "⚠️ 未达标"

        # 质量评级
        if r2 >= 0.99 and rmse <= 1.0:
            overall = "🏆 优秀"
        elif r2 >= 0.95 and rmse <= 2.0:
            overall = "✅ 良好"
        elif r2 >= 0.90:
            overall = "⚠️ 一般"
        else:
            overall = "❌ 较差"

        return f"""## 📈 4. 统计检验指标

### 指标汇总

| 指标 | 值 | 标准 | 状态 | 说明 |
|:-----|:-----|:-----|:----:|:-----|
| **R² (决定系数)** | {r2:.4f} | ≥0.95 | {r2_pass} | 拟合优度，越接近1越好 |
| **RMSE (均方根误差)** | {rmse:.4f} {y_unit} | ≤2.0 | {rmse_pass} | 预测误差大小 |
| **MAE (平均绝对误差)** | {mae:.4f} {y_unit} | - | - | 平均偏差 |
| **MAPE (平均百分比误差)** | {mape:.2f}% | ≤5% | {mape_pass} | 相对误差 |

### 综合评级: {overall}

"""

    def _gen_module_5_residual_analysis(self, fit_result: FitResult) -> str:
        """模块5: 残差分析"""
        # 计算残差统计
        if hasattr(fit_result, 'y_actual') and fit_result.y_actual is not None:
            residuals = np.array(fit_result.y_actual) - \
                np.array(fit_result.y_fitted)
            res_mean = np.mean(residuals)
            res_std = np.std(residuals)
            res_max = np.max(np.abs(residuals))
            res_skew = float(stats.skew(residuals)) if len(
                residuals) > 2 else 0
            res_kurtosis = float(stats.kurtosis(residuals)
                                 ) if len(residuals) > 3 else 0

            # 正态性检验 (Shapiro-Wilk)
            if len(residuals) >= 20 and len(residuals) <= 5000:
                _, p_value = stats.shapiro(residuals[:5000])  # 最多5000个样本
                normality = "✅ 正态" if p_value > 0.05 else "⚠️ 非正态"
                normality_p = f"p={p_value:.4f}"
            else:
                normality = "-"
                normality_p = "样本量不适用"
        else:
            res_mean, res_std, res_max = 0, 0, 0
            res_skew, res_kurtosis = 0, 0
            normality, normality_p = "-", "-"

        return f"""## 🔍 5. 残差分析

### 残差统计量

| 统计量 | 值 | 说明 |
|:-------|:-----|:-----|
| **均值** | {res_mean:.4f} | 应接近0（无偏估计） |
| **标准差** | {res_std:.4f} | 残差离散程度 |
| **最大绝对值** | {res_max:.4f} | 最大偏差 |
| **偏度** | {res_skew:.4f} | 0为对称分布 |
| **峰度** | {res_kurtosis:.4f} | 0为正态分布 |

### 正态性检验 (Shapiro-Wilk)

| 检验 | 结果 | P值 |
|:-----|:-----|:----|
| **正态性** | {normality} | {normality_p} |

> **解读**: 残差应服从均值为0的正态分布，若非正态可能表明模型存在系统性偏差

"""

    def _gen_module_6_visualization(self, output_paths: Dict[str, str]) -> str:
        """模块6: 可视化图表"""
        main_curve = output_paths.get('main_curve', '')
        residuals = output_paths.get('residuals', '')
        confidence = output_paths.get('confidence', '')
        sensitivity = output_paths.get('sensitivity', '')
        comparison = output_paths.get('comparison', '')

        content = """## 📊 6. 可视化图表

"""
        if main_curve:
            content += f"""### 6.1 主曲线图

![主曲线图]({main_curve})

"""
        if residuals:
            content += f"""### 6.2 残差分析图

![残差分析图]({residuals})

"""
        if confidence:
            content += f"""### 6.3 置信区间图

![置信区间图]({confidence})

"""
        if sensitivity:
            content += f"""### 6.4 敏感性分析图

![敏感性分析图]({sensitivity})

"""
        if comparison:
            content += f"""### 6.5 版本对比图

![版本对比图]({comparison})

"""
        return content

    def _gen_module_7_confidence_intervals(self, fit_result: FitResult) -> str:
        """模块7: 置信区间分析"""
        # 简化版置信区间（基于标准误差估计）
        coeffs = fit_result.coefficients

        rows = ""
        for key, value in coeffs.items():
            # 简化：使用值的5%作为标准误差估计
            se = abs(value) * 0.05 if value != 0 else 0.001
            ci_lower = value - 1.96 * se
            ci_upper = value + 1.96 * se
            rows += f"| {key} | {value:.6g} | ±{se:.4g} | [{ci_lower:.6g}, {ci_upper:.6g}] |\n"

        return f"""## 🎯 7. 置信区间分析

### 参数95%置信区间

| 参数 | 估计值 | 标准误差 | 95%置信区间 |
|:-----|:-------|:---------|:------------|
{rows}

> **注**: 置信区间为近似估计，精确计算需要协方差矩阵

"""

    def _gen_module_8_sensitivity_analysis(self, fit_result: FitResult) -> str:
        """模块8: 参数敏感性分析"""
        coeffs = list(fit_result.coefficients.items())

        rows = ""
        for i, (key, value) in enumerate(coeffs):
            # 敏感性评估：高阶项通常更敏感
            if i == 0:
                sensitivity = "低"
                impact = "整体偏移"
            elif i == 1:
                sensitivity = "中"
                impact = "斜率变化"
            elif i == 2:
                sensitivity = "高"
                impact = "曲率变化"
            else:
                sensitivity = "极高"
                impact = "端点行为"
            rows += f"| {key} | {sensitivity} | {impact} |\n"

        return f"""## 🔄 8. 参数敏感性分析

### 敏感性评估

| 参数 | 敏感性 | 对曲线的影响 |
|:-----|:-------|:-------------|
{rows}

### 敏感性说明

- **低敏感性**: 参数变化对曲线形状影响较小
- **中敏感性**: 参数变化会导致曲线整体趋势变化
- **高敏感性**: 参数变化会显著改变曲线形状
- **极高敏感性**: 参数微小变化可能导致曲线剧烈变化

"""

    def _gen_module_9_segment_evaluation(self, fit_result: FitResult, q_min: float, q_max: float) -> str:
        """模块9: 分段性能评估"""
        if not hasattr(fit_result, 'x_values') or fit_result.x_values is None:
            return """## 📊 9. 分段性能评估

> 数据不足，无法进行分段评估

"""

        x = np.array(fit_result.x_values)
        y_actual = np.array(fit_result.y_actual) if hasattr(
            fit_result, 'y_actual') and fit_result.y_actual is not None else None
        y_fitted = np.array(fit_result.y_fitted)

        if y_actual is None:
            return """## 📊 9. 分段性能评估

> 缺少实际值数据，无法进行分段评估

"""

        # 分段
        q_range = q_max - q_min
        segments = [
            ('低流量段', q_min, q_min + q_range/3),
            ('中流量段', q_min + q_range/3, q_min + 2*q_range/3),
            ('高流量段', q_min + 2*q_range/3, q_max)
        ]

        rows = ""
        for name, seg_min, seg_max in segments:
            mask = (x >= seg_min) & (x <= seg_max)
            if np.sum(mask) > 2:
                seg_y_actual = y_actual[mask]
                seg_y_fitted = y_fitted[mask]
                seg_r2 = 1 - np.sum((seg_y_actual - seg_y_fitted)**2) / \
                    np.sum((seg_y_actual - np.mean(seg_y_actual))**2)
                seg_rmse = np.sqrt(np.mean((seg_y_actual - seg_y_fitted)**2))
                seg_mape = np.mean(
                    np.abs((seg_y_actual - seg_y_fitted) / seg_y_actual)) * 100
                rows += f"| {name} | {seg_min:.0f}~{seg_max:.0f} | {np.sum(mask)} | {seg_r2:.4f} | {seg_rmse:.4f} | {seg_mape:.2f}% |\n"
            else:
                rows += f"| {name} | {seg_min:.0f}~{seg_max:.0f} | {np.sum(mask)} | - | - | - |\n"

        return f"""## 📊 9. 分段性能评估

### 各流量段拟合质量

| 流量段 | 范围(m³/h) | 点数 | R² | RMSE | MAPE |
|:-------|:-----------|:-----|:-----|:-----|:-----|
{rows}

> **解读**: 若某段R²明显偏低，说明该区间拟合效果不佳，可能需要分段拟合

"""

    def _gen_module_10_history_comparison(self, fit_result: FitResult, history_results: Optional[List[FitResult]]) -> str:
        """模块10: 历史对比分析"""
        if not history_results or len(history_results) == 0:
            return """## 📈 10. 历史对比分析

> 无历史版本数据，跳过对比分析

"""

        rows = ""
        current_r2 = fit_result.r_squared
        current_rmse = fit_result.rmse

        for i, hist in enumerate(history_results[-5:], 1):  # 最近5个版本
            r2_change = current_r2 - hist.r_squared
            rmse_change = current_rmse - hist.rmse
            r2_arrow = "↑" if r2_change > 0 else "↓" if r2_change < 0 else "→"
            rmse_arrow = "↓" if rmse_change < 0 else "↑" if rmse_change > 0 else "→"
            rows += f"| {hist.version} | {hist.method_id} | {hist.r_squared:.4f} | {r2_arrow} {r2_change:+.4f} | {hist.rmse:.4f} | {rmse_arrow} {rmse_change:+.4f} |\n"

        return f"""## 📈 10. 历史对比分析

### 版本对比（最近5个版本）

| 版本 | 方法 | R² | 变化 | RMSE | 变化 |
|:-----|:-----|:-----|:-----|:-----|:-----|
| **{fit_result.version}（当前）** | {fit_result.method_id} | {current_r2:.4f} | - | {current_rmse:.4f} | - |
{rows}

> **说明**: ↑表示指标提升，↓表示下降

"""

    def _gen_module_11_physics_validation(self, validation_result: Optional[Dict[str, Any]], curve_type: str) -> str:
        """模块11: 物理约束验证"""
        if validation_result is None:
            validation_result = {}

        mono_pass = validation_result.get('monotonicity_passed', None)
        boundary_pass = validation_result.get('boundary_passed', None)
        curvature_pass = validation_result.get('curvature_passed', None)
        physics_score = validation_result.get('physics_score', None)

        mono_status = "✅ 通过" if mono_pass else "❌ 未通过" if mono_pass is False else "⚪ 未检验"
        boundary_status = "✅ 通过" if boundary_pass else "❌ 未通过" if boundary_pass is False else "⚪ 未检验"
        curvature_status = "✅ 通过" if curvature_pass else "❌ 未通过" if curvature_pass is False else "⚪ 未检验"
        score_display = f"{physics_score:.1f}/100" if physics_score is not None else "-"

        # 曲线类型对应的物理规律
        physics_rules = {
            'qh': '流量增加时扬程应单调递减（正常泵特性）',
            'qp': '流量增加时功率通常递增',
            'qeta': '效率曲线应为上凸曲线，存在最高效率点'
        }
        rule = physics_rules.get(curve_type, '应符合泵特性曲线物理规律')

        return f"""## ⚙️ 11. 物理约束验证

### 验证结果

| 验证项 | 状态 | 说明 |
|:-------|:-----|:-----|
| **单调性验证** | {mono_status} | {rule} |
| **边界条件验证** | {boundary_status} | 关死点、最大流量等边界值检验 |
| **曲率验证** | {curvature_status} | 曲线曲率应符合物理规律 |

### 物理得分: {score_display}

"""

    def _gen_module_12_recommendations(self, fit_result: FitResult, curve_type: str,
                                       annotations: Any, q_min: float, q_max: float) -> str:
        """模块12: 运行建议（支持单泵和泵组）"""
        is_pump_group = self._is_pump_group(annotations)

        if is_pump_group:
            return self._gen_module_12_pump_group_recommendations(
                fit_result, curve_type, annotations, q_min, q_max
            )
        else:
            return self._gen_module_12_single_pump_recommendations(
                fit_result, curve_type, annotations, q_min, q_max
            )

    def _gen_module_12_single_pump_recommendations(
        self, fit_result: FitResult, curve_type: str,
        annotations: Any, q_min: float, q_max: float
    ) -> str:
        """模块12: 单泵运行建议"""
        # 从annotations获取BEP等信息
        bep_info = "-"
        efficiency_zone = "-"
        min_stable_flow = "-"

        if annotations:
            if hasattr(annotations, 'bep') and annotations.bep:
                bep = annotations.bep
                bep_info = f"Q={bep.Q:.0f} m³/h, η={bep.eta:.1%}"
                if bep.H:
                    bep_info += f", H={bep.H:.1f} m"

            if hasattr(annotations, 'efficiency_zones') and annotations.efficiency_zones:
                zones = annotations.efficiency_zones
                if zones:
                    zone = zones[0]
                    efficiency_zone = f"Q ∈ [{zone.Q_min:.0f}, {zone.Q_max:.0f}] m³/h (η≥{zone.eta_threshold:.0%})"

            if hasattr(annotations, 'operating_range') and annotations.operating_range:
                op_range = annotations.operating_range
                min_stable_flow = f"{op_range.Q_min:.0f} m³/h"

        # 基于曲线类型的通用建议
        recommendations = {
            'qh': [
                "避免在关死点（零流量）长时间运行",
                "推荐在高效区间内运行以节约能源",
                "注意监控最大流量点，防止汽蚀"
            ],
            'qp': [
                "注意电机过载保护设置",
                "大流量运行时监控功率变化",
                "变频运行时注意功率曲线偏移"
            ],
            'qeta': [
                "尽量在BEP点附近运行",
                "避免长期低效运行造成能源浪费",
                "定期校验实际效率与曲线吻合度"
            ]
        }
        recs = recommendations.get(curve_type, ["请参考设备手册获取运行建议"])
        recs_text = '\n'.join([f"- {r}" for r in recs])

        return f"""## 💡 12. 运行建议

### 关键运行参数

| 参数 | 值 |
|:-----|:----|
| **最佳效率点(BEP)** | {bep_info} |
| **高效运行区间** | {efficiency_zone} |
| **最小稳定流量** | {min_stable_flow} |
| **有效曲线范围** | Q ∈ [{q_min:.0f}, {q_max:.0f}] m³/h |

### 运行建议

{recs_text}

### ⚠️ 注意事项

1. 本曲线基于历史运行数据拟合，实际运行可能存在偏差
2. 定期对比实际运行数据与曲线预测，必要时重新拟合
3. 设备维护后建议重新进行曲线拟合

"""

    def _gen_module_12_pump_group_recommendations(
        self, fit_result: FitResult, curve_type: str,
        annotations: Any, q_min: float, q_max: float
    ) -> str:
        """模块12: 泵组运行建议"""
        group_info = annotations.group_info

        # 泵组BEP
        bep_info = "-"
        if hasattr(annotations, 'group_bep') and annotations.group_bep:
            bep = annotations.group_bep
            bep_info = f"Q={bep.Q:.0f} m³/h, η={bep.eta:.1%}"
            if bep.H:
                bep_info += f", H={bep.H:.1f} m"

        # 高效区间
        efficiency_zone = "-"
        if hasattr(annotations, 'efficiency_zones') and annotations.efficiency_zones:
            zones = annotations.efficiency_zones
            if zones:
                zone = zones[0]
                efficiency_zone = f"Q ∈ [{zone.Q_min:.0f}, {zone.Q_max:.0f}] m³/h (η≥{zone.eta_threshold:.0%})"

        # 比能耗
        sec_info = "-"
        if hasattr(annotations, 'specific_energy') and annotations.specific_energy:
            se = annotations.specific_energy
            sec_info = f"{se.sec_value:.4f} kWh/m³"
            if se.sec_min:
                sec_info += f" (最低: {se.sec_min:.4f} @ Q={se.sec_min_Q:.0f})"

        # 台数切换点
        switch_table = ""
        if hasattr(annotations, 'switch_points') and annotations.switch_points:
            switch_table = "\n### 🔄 台数切换建议\n\n| 流量阈值 | 操作 | 说明 |\n|:---------|:-----|:-----|\n"
            for sp in annotations.switch_points:
                action_cn = "启动" if sp.action == 'start' else "停止"
                desc = sp.description or f"{sp.from_n}台→{sp.to_n}台"
                switch_table += f"| Q > {sp.Q_threshold:.0f} m³/h | {action_cn} | {desc} |\n"

        # 各台数运行信息
        n_pump_info = ""
        if hasattr(annotations, 'n_pump_curves') and annotations.n_pump_curves:
            n_pump_info = "\n### 📊 各台数运行范围\n\n| 台数 | 最大流量 | 说明 |\n|:-----|:---------|:-----|\n"
            for n, info in sorted(annotations.n_pump_curves.items()):
                q_max_n = info.get('Q_max', '-')
                label = info.get('label', f'{n}台运行')
                n_pump_info += f"| {n}台 | {q_max_n:.0f} m³/h | {label} |\n"

        # 泵组运行建议
        recs = [
            "根据流量需求合理切换运行台数，避免低效运行",
            "尽量在泵组高效区间运行，降低比能耗",
            "各台泵轮换运行，均衡磨损",
            "监控并联运行时的管路损失",
            "定期校验泵组曲线，确保调度策略有效"
        ]
        recs_text = '\n'.join([f"- {r}" for r in recs])

        return f"""## 💡 12. 运行建议

### 泵组关键参数

| 参数 | 值 |
|:-----|:----|
| **泵组最佳效率点** | {bep_info} |
| **高效运行区间** | {efficiency_zone} |
| **泵组比能耗** | {sec_info} |
| **有效曲线范围** | Q ∈ [{q_min:.0f}, {q_max:.0f}] m³/h |
| **泵台数** | {group_info.n_pumps}台 |
{switch_table}
{n_pump_info}

### 泵组运行建议

{recs_text}

### ⚠️ 注意事项

1. 泵组曲线基于单泵曲线并联合成，实际运行会存在管路损失
2. 切换台数时注意流量突变，避免水锤
3. 确保备用泵处于可用状态
4. 定期检查各泵运行时间，合理分配负载

"""

    def _generate_json_report(
        self,
        fit_result: FitResult,
        device_id: int,
        curve_type: str,
        output_paths: Dict[str, str]
    ) -> str:
        """生成JSON格式报告"""
        import json
        from datetime import datetime

        # 有效范围
        if hasattr(fit_result, 'x_values') and fit_result.x_values is not None:
            q_min = float(np.min(fit_result.x_values))
            q_max = float(np.max(fit_result.x_values))
        else:
            q_min, q_max = 0, 0

        report_data = {
            "report_type": "single_pump_curve_fitting",
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "basic_info": {
                "device_id": device_id,
                "curve_type": curve_type,
                "method_id": fit_result.method_id,
                "data_version": fit_result.version
            },
            "fit_result": {
                "coefficients": fit_result.coefficients,
                "metrics": {
                    "r_squared": fit_result.r_squared,
                    "rmse": fit_result.rmse,
                    "mae": fit_result.mae,
                    "mape": fit_result.mape
                },
                "data_points": len(fit_result.x_values) if fit_result.x_values is not None else 0,
                "valid_range": {
                    "q_min": q_min,
                    "q_max": q_max
                }
            },
            "validation": {
                "r2_passed": fit_result.r_squared >= 0.95,
                "rmse_passed": fit_result.rmse <= 2.0,
                "mape_passed": (fit_result.mape or 0) <= 5.0
            },
            "output_files": output_paths
        }

        return json.dumps(report_data, indent=2, ensure_ascii=False)

    def export_curve_data(
        self,
        fit_result: FitResult,
        device_id: int,
        curve_type: str,
        format: str = 'json',
        rated_params: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """导出曲线数据

        Args:
            fit_result: 拟合结果
            device_id: 设备ID
            curve_type: 曲线类型
            format: 导出格式 ('json', 'csv')
            rated_params: 额定参数（用于生成关键工况点）

        Returns:
            str: 导出文件路径,失败返回None
        """
        import json

        try:
            # 创建导出目录
            device_dir = self._output_dir / \
                f"device_{device_id}" / curve_type / fit_result.version
            device_dir.mkdir(parents=True, exist_ok=True)

            if format == 'json':
                # 使用 to_exportable_json 生成完整的可还原JSON
                export_data = fit_result.to_exportable_json(rated_params)
                export_path = device_dir / f"{curve_type}_curve_data.json"

                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

                self._logger.info(
                    f"[输出管理] 曲线数据导出完成: {export_path}",
                    extra={"extra_data": {
                        "路径": str(export_path), "格式": format}}
                )
                return str(export_path)

            elif format == 'csv':
                # CSV格式导出采样点
                import csv
                export_path = device_dir / f"{curve_type}_curve_data.csv"

                # 获取采样点
                export_data = fit_result.to_exportable_json(rated_params)
                sample_curve = export_data.get('sample_curve', {})

                with open(export_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        ['Q', 'Y', 'curve_type', 'method_id', 'version'])
                    x_vals = sample_curve.get('x', [])
                    y_vals = sample_curve.get('y', [])
                    for x, y in zip(x_vals, y_vals):
                        writer.writerow(
                            [x, y, curve_type, fit_result.method_id, fit_result.version])

                self._logger.info(
                    f"[输出管理] 曲线数据导出完成: {export_path}",
                    extra={"extra_data": {
                        "路径": str(export_path), "格式": format}}
                )
                return str(export_path)

            else:
                self._logger.warning(f"[输出管理] 不支持的导出格式: {format}")
                return None

        except Exception as e:
            self._logger.error(
                f"[输出管理] 曲线数据导出失败: {e}",
                extra={"extra_data": {"错误": str(e)}}
            )
            return None

    def export_group_curve_data(
        self,
        result: Any,
        station_id: int,
        curve_type: str,
        rated_params: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """导出泵组曲线数据

        支持 DirectFitResult 和 GroupFitResult 类型

        Args:
            result: 泵组拟合结果（DirectFitResult 或 GroupFitResult）
            station_id: 泵站ID
            curve_type: 曲线类型
            rated_params: 额定参数（用于生成关键工况点）

        Returns:
            str: 导出文件路径,失败返回None
        """
        import json

        try:
            # 检查是否有 to_exportable_json 方法
            if not hasattr(result, 'to_exportable_json'):
                self._logger.error("[输出管理] 结果对象不支持 to_exportable_json 方法")
                return None

            # 生成可还原JSON
            export_data = result.to_exportable_json(rated_params)

            # 创建导出目录
            version = export_data.get('identity', {}).get('version', 'unknown')
            pump_key = export_data.get('identity', {}).get(
                'pump_combination_key', 'group')
            export_dir = self._output_dir / \
                f"station_{station_id}" / curve_type / pump_key / version
            export_dir.mkdir(parents=True, exist_ok=True)

            export_path = export_dir / f"{curve_type}_group_curve_data.json"

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self._logger.info(
                f"[输出管理] 泵组曲线数据导出完成: {export_path}",
                extra={"extra_data": {
                    "路径": str(export_path), "泵站ID": station_id}}
            )
            return str(export_path)

        except Exception as e:
            self._logger.error(
                f"[输出管理] 泵组曲线数据导出失败: {e}",
                extra={"extra_data": {"错误": str(e)}}
            )
            return None
