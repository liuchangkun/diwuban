"""
报告生成器 (app.services.characteristic_curves.shared.report_generator)

生成曲线拟合和分析报告。

版本: v1.0
更新日期: 2025-12-08
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ReportSection:
    """报告章节

    Attributes:
        title: 章节标题
        content: 章节内容
        data: 关联数据
    """

    title: str
    content: str = ""
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Report:
    """报告

    Attributes:
        title: 报告标题
        sections: 报告章节列表
        created_at: 创建时间
        metadata: 元数据
    """

    title: str
    sections: List[ReportSection] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "sections": [
                {"title": s.title, "content": s.content, "data": s.data}
                for s in self.sections
            ],
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        lines = [f"# {self.title}", "", f"生成时间: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}", ""]

        for section in self.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            if section.content:
                lines.append(section.content)
                lines.append("")
            if section.data:
                for key, value in section.data.items():
                    lines.append(f"- **{key}**: {value}")
                lines.append("")

        return "\n".join(lines)


class ReportGenerator:
    """报告生成器

    生成曲线拟合和分析的结构化报告。

    使用方式:
        generator = ReportGenerator()
        report = generator.generate_fitting_report(curve_type, fit_result)
    """

    def __init__(self) -> None:
        """初始化报告生成器"""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def generate_fitting_report(
        self,
        curve_type: str,
        method_id: str,
        r2: float,
        rmse: float,
        coefficients: Optional[List[float]] = None,
        formula: Optional[str] = None,
        data_points: int = 0,
        **kwargs: Any,
    ) -> Report:
        """生成拟合报告

        Args:
            curve_type: 曲线类型
            method_id: 拟合方法ID
            r2: R²值
            rmse: RMSE值
            coefficients: 拟合系数
            formula: 拟合公式
            data_points: 数据点数

        Returns:
            Report: 拟合报告
        """
        report = Report(
            title=f"{curve_type.upper()}曲线拟合报告",
            metadata={"curve_type": curve_type, "method_id": method_id},
        )

        # 概述章节
        overview = ReportSection(
            title="拟合概述",
            data={
                "曲线类型": curve_type.upper(),
                "拟合方法": method_id,
                "数据点数": data_points,
            },
        )
        report.sections.append(overview)

        # 质量评估章节
        quality = "excellent" if r2 >= 0.99 else "good" if r2 >= 0.95 else "fair" if r2 >= 0.90 else "poor"
        metrics = ReportSection(
            title="拟合质量",
            data={"R²": f"{r2:.6f}", "RMSE": f"{rmse:.6f}", "质量等级": quality},
        )
        report.sections.append(metrics)

        # 公式章节
        if formula:
            formula_section = ReportSection(title="拟合公式", content=f"`{formula}`")
            report.sections.append(formula_section)

        # 系数章节
        if coefficients:
            coef_data = {f"c{i}": f"{c:.6g}" for i, c in enumerate(coefficients)}
            coef_section = ReportSection(title="拟合系数", data=coef_data)
            report.sections.append(coef_section)

        return report

    def generate_validation_report(
        self, curve_type: str, validation_results: Dict[str, Any]
    ) -> Report:
        """生成验证报告"""
        report = Report(title=f"{curve_type.upper()}曲线验证报告")

        summary = ReportSection(
            title="验证结果摘要",
            data={"总体结果": "通过" if validation_results.get("overall_valid") else "未通过"},
        )
        report.sections.append(summary)

        return report

