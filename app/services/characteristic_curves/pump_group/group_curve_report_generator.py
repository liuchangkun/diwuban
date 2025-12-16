"""
泵组曲线报告生成器 (app.services.characteristic_curves.pump_group.group_curve_report_generator)

生成泵组曲线拟合的分析报告。

核心功能：
- 生成拟合质量报告
- 生成双方法对比报告
- 生成历史趋势报告
- 支持多种输出格式

版本: v1.0
创建日期: 2025-12-14
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ReportSection:
    """报告章节"""
    title: str
    content: str
    data: Optional[Dict[str, Any]] = None
    charts: Optional[List[Dict[str, Any]]] = None


class GroupCurveReportGenerator:
    """泵组曲线报告生成器

    职责：
    1. 生成拟合质量报告
    2. 生成双方法对比报告
    3. 生成可视化图表数据
    4. 输出多种格式
    """

    def __init__(self):
        self._report_sections: List[ReportSection] = []

    def generate_fit_quality_report(
        self,
        fit_result: Any,  # DirectFitResult
        validation_result: Optional[Any] = None  # ValidationResult
    ) -> Dict[str, Any]:
        """
        生成拟合质量报告

        Args:
            fit_result: 直接拟合结果
            validation_result: 验证结果（可选）

        Returns:
            报告字典
        """
        report = {
            'title': '泵组曲线拟合质量报告',
            'generated_at': datetime.now().isoformat(),
            'summary': {},
            'details': {},
            'recommendations': []
        }

        # 1. 摘要信息
        report['summary'] = {
            'curve_type': fit_result.curve_type,
            'method_id': getattr(fit_result, 'method_id', 'polynomial'),
            'r_squared': fit_result.r_squared,
            'data_points_used': fit_result.data_points_used,
            'quality_grade': self._grade_quality(fit_result.r_squared)
        }

        # 2. 详细指标
        report['details'] = {
            'coefficients': (
                fit_result.coefficients.tolist()
                if hasattr(fit_result.coefficients, 'tolist')
                else fit_result.coefficients
            ),
            'Q_range': getattr(fit_result, 'Q_range', None),
            'rmse': getattr(fit_result, 'rmse', None)
        }

        # 3. 验证结果
        if validation_result:
            report['validation'] = {
                'is_valid': validation_result.is_valid,
                'score': validation_result.score,
                'warnings': validation_result.warnings,
                'errors': validation_result.errors
            }

        # 4. 建议
        report['recommendations'] = self._generate_recommendations(
            fit_result, validation_result
        )

        return report

    def generate_comparison_report(
        self,
        dual_result: Any,  # DualFitResult
        include_charts: bool = True
    ) -> Dict[str, Any]:
        """
        生成双方法对比报告

        Args:
            dual_result: 双方法结果
            include_charts: 是否包含图表数据

        Returns:
            对比报告字典
        """
        report = {
            'title': '泵组曲线双方法对比报告',
            'generated_at': datetime.now().isoformat(),
            'executive_summary': {},
            'method_comparison': {},
            'recommendation': {},
            'charts': []
        }

        comparison = dual_result.comparison or {}

        # 1. 执行摘要
        report['executive_summary'] = {
            'recommended_method': dual_result.recommended_method,
            'confidence': comparison.get('confidence', 0),
            'max_diff_ratio': comparison.get('max_diff_ratio', 0),
            'avg_diff_ratio': comparison.get('avg_diff_ratio', 0)
        }

        # 2. 方法对比
        direct_fit = dual_result.direct_fit_result
        synthesis = dual_result.synthesis_result

        report['method_comparison'] = {
            'direct_fit': {
                'r_squared': direct_fit.r_squared,
                'data_points': direct_fit.data_points_used,
                'curve_type': direct_fit.curve_type,
                'pros': ['反映真实运行特性', '包含并联损失'],
                'cons': ['需要足够数据', '不能预测未见组合']
            },
            'synthesis': {
                'description': '基于单泵曲线并联叠加',
                'pros': ['可预测任意组合', '方法灵活'],
                'cons': ['忽略并联干涉损失', '依赖单泵曲线精度']
            },
            'difference': {
                'max_diff_h': comparison.get('max_diff_h', 0),
                'avg_diff_h': comparison.get('avg_diff_h', 0),
                'diff_by_region': comparison.get('diff_by_region', {})
            }
        }

        # 3. 推荐说明
        report['recommendation'] = {
            'method': dual_result.recommended_method,
            'reason': comparison.get('recommendation_reason', ''),
            'confidence': comparison.get('confidence', 0),
            'decision_criteria': self._explain_decision(comparison)
        }

        # 4. 图表数据
        if include_charts:
            report['charts'] = self._generate_chart_data(dual_result)

        return report

    def generate_trend_report(
        self,
        historical_results: List[Dict[str, Any]],
        station_id: int,
        pump_combination: List[int]
    ) -> Dict[str, Any]:
        """
        生成历史趋势报告

        Args:
            historical_results: 历史拟合结果列表
            station_id: 站点ID
            pump_combination: 泵组合

        Returns:
            趋势报告字典
        """
        report = {
            'title': '泵组曲线历史趋势报告',
            'generated_at': datetime.now().isoformat(),
            'station_id': station_id,
            'pump_combination': pump_combination,
            'trend_summary': {},
            'performance_history': [],
            'alerts': []
        }

        if not historical_results:
            report['trend_summary'] = {'status': '无历史数据'}
            return report

        # 提取R²历史
        r2_history = [
            r.get('r_squared', 0) for r in historical_results
            if 'r_squared' in r
        ]

        if r2_history:
            report['trend_summary'] = {
                'current_r2': r2_history[-1] if r2_history else 0,
                'avg_r2': sum(r2_history) / len(r2_history),
                'min_r2': min(r2_history),
                'max_r2': max(r2_history),
                'trend': self._calculate_trend(r2_history)
            }

        # 性能历史
        report['performance_history'] = [
            {
                'version': r.get('version', ''),
                'created_at': r.get('created_at', ''),
                'r_squared': r.get('r_squared', 0),
                'data_points': r.get('data_points_used', 0)
            }
            for r in historical_results
        ]

        # 告警检测
        if r2_history and r2_history[-1] < 0.90:
            report['alerts'].append({
                'level': 'warning',
                'message': f'当前R²({r2_history[-1]:.3f})低于阈值0.90'
            })

        if len(r2_history) >= 3:
            recent_trend = r2_history[-3:]
            if all(recent_trend[i] > recent_trend[i+1] for i in range(2)):
                report['alerts'].append({
                    'level': 'info',
                    'message': 'R²连续下降，建议检查泵组状态'
                })

        return report

    def _grade_quality(self, r_squared: float) -> str:
        """评定质量等级"""
        if r_squared >= 0.98:
            return 'A（优秀）'
        elif r_squared >= 0.95:
            return 'B（良好）'
        elif r_squared >= 0.90:
            return 'C（合格）'
        elif r_squared >= 0.80:
            return 'D（较差）'
        else:
            return 'E（不合格）'

    def _generate_recommendations(
        self,
        fit_result: Any,
        validation_result: Optional[Any]
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        if fit_result.r_squared < 0.90:
            recommendations.append('R²偏低，建议增加数据量或检查数据质量')

        if fit_result.data_points_used < 100:
            recommendations.append('数据点不足，建议积累更多运行数据')

        if validation_result:
            if not validation_result.is_valid:
                recommendations.append('曲线验证未通过，需排查物理规律问题')
            for warning in validation_result.warnings[:3]:
                recommendations.append(f'警告: {warning}')

        if not recommendations:
            recommendations.append('曲线质量良好，可正常使用')

        return recommendations

    def _explain_decision(self, comparison: Dict[str, Any]) -> List[str]:
        """解释决策依据"""
        criteria = []

        avg_diff = comparison.get('avg_diff_ratio', 0)
        if avg_diff < 0.02:
            criteria.append(f'差异很小({avg_diff:.1%})，合成方法足够')
        elif avg_diff > 0.05:
            criteria.append(f'差异显著({avg_diff:.1%})，直接拟合更准')

        confidence = comparison.get('confidence', 0)
        criteria.append(f'推荐置信度: {confidence:.0%}')

        return criteria

    def _generate_chart_data(
        self,
        dual_result: Any
    ) -> List[Dict[str, Any]]:
        """生成图表数据"""
        charts = []

        # 1. Q-H对比曲线
        sample_diffs = dual_result.comparison.get('sample_diffs', [])
        if sample_diffs:
            charts.append({
                'type': 'line',
                'title': 'Q-H曲线对比',
                'x_label': '流量 Q (m³/h)',
                'y_label': '扬程 H (m)',
                'series': [
                    {
                        'name': '直接拟合',
                        'data': [[d['Q'], d['H_direct']] for d in sample_diffs]
                    },
                    {
                        'name': '合成曲线',
                        'data': [[d['Q'], d['H_synthesis']] for d in sample_diffs]
                    }
                ]
            })

            # 2. 差异分布
            charts.append({
                'type': 'bar',
                'title': '差异分布',
                'x_label': '流量区间',
                'y_label': '相对差异 (%)',
                'data': dual_result.comparison.get('diff_by_region', {})
            })

        return charts

    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势"""
        if len(values) < 2:
            return 'stable'

        recent = values[-3:] if len(values) >= 3 else values
        if all(recent[i] <= recent[i+1] for i in range(len(recent)-1)):
            return 'improving'
        elif all(recent[i] >= recent[i+1] for i in range(len(recent)-1)):
            return 'declining'
        else:
            return 'stable'

    def to_markdown(self, report: Dict[str, Any]) -> str:
        """转换为Markdown格式"""
        lines = []
        lines.append(f"# {report.get('title', '报告')}")
        lines.append(f"\n生成时间: {report.get('generated_at', '')}\n")

        # 摘要
        if 'summary' in report:
            lines.append("## 摘要\n")
            for key, value in report['summary'].items():
                lines.append(f"- **{key}**: {value}")

        if 'executive_summary' in report:
            lines.append("## 执行摘要\n")
            for key, value in report['executive_summary'].items():
                lines.append(f"- **{key}**: {value}")

        # 详情
        if 'details' in report:
            lines.append("\n## 详细信息\n")
            lines.append("```json")
            import json
            lines.append(json.dumps(
                report['details'], indent=2, ensure_ascii=False))
            lines.append("```")

        # 建议
        if 'recommendations' in report:
            lines.append("\n## 建议\n")
            for rec in report['recommendations']:
                lines.append(f"- {rec}")

        return "\n".join(lines)

    def to_html(self, report: Dict[str, Any]) -> str:
        """转换为HTML格式"""
        html = f"""
        <html>
        <head><title>{report.get('title', '报告')}</title></head>
        <body>
        <h1>{report.get('title', '报告')}</h1>
        <p>生成时间: {report.get('generated_at', '')}</p>
        """

        if 'summary' in report:
            html += "<h2>摘要</h2><ul>"
            for key, value in report['summary'].items():
                html += f"<li><strong>{key}</strong>: {value}</li>"
            html += "</ul>"

        if 'recommendations' in report:
            html += "<h2>建议</h2><ul>"
            for rec in report['recommendations']:
                html += f"<li>{rec}</li>"
            html += "</ul>"

        html += "</body></html>"
        return html
