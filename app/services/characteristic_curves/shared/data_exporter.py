"""
数据导出器 (app.services.characteristic_curves.shared.data_exporter)

导出曲线数据和拟合结果。

版本: v1.0
更新日期: 2025-12-08
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd


class ExportFormat(str, Enum):
    """导出格式"""

    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"


@dataclass
class ExportResult:
    """导出结果

    Attributes:
        success: 是否成功
        format: 导出格式
        file_path: 文件路径（如果保存到文件）
        data: 导出数据（如果返回内存数据）
        rows: 导出行数
        message: 消息
    """

    success: bool
    format: str
    file_path: Optional[str] = None
    data: Optional[str] = None
    rows: int = 0
    message: str = ""


class DataExporter:
    """数据导出器

    支持多种格式导出曲线数据。

    使用方式:
        exporter = DataExporter()
        result = exporter.export_to_csv(df, 'output.csv')
    """

    def __init__(self) -> None:
        """初始化数据导出器"""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def export(
        self,
        data: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]],
        format: str = "csv",
        file_path: Optional[str] = None,
    ) -> ExportResult:
        """导出数据

        Args:
            data: 要导出的数据
            format: 导出格式 ('csv', 'json', 'excel')
            file_path: 文件路径（如果为None，返回字符串）

        Returns:
            ExportResult: 导出结果
        """
        try:
            # 转换为DataFrame
            if isinstance(data, dict):
                df = pd.DataFrame([data])
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = data

            if format == "csv":
                return self._export_csv(df, file_path)
            elif format == "json":
                return self._export_json(df, file_path)
            elif format == "excel":
                return self._export_excel(df, file_path)
            else:
                return ExportResult(
                    success=False, format=format, message=f"不支持的格式: {format}"
                )

        except Exception as e:
            self._logger.error(f"导出失败: {e}")
            return ExportResult(success=False, format=format, message=str(e))

    def _export_csv(
        self, df: pd.DataFrame, file_path: Optional[str]
    ) -> ExportResult:
        """导出为CSV"""
        if file_path:
            df.to_csv(file_path, index=False, encoding="utf-8-sig")
            return ExportResult(
                success=True, format="csv", file_path=file_path, rows=len(df)
            )
        else:
            csv_str = df.to_csv(index=False)
            return ExportResult(
                success=True, format="csv", data=csv_str, rows=len(df)
            )

    def _export_json(
        self, df: pd.DataFrame, file_path: Optional[str]
    ) -> ExportResult:
        """导出为JSON"""
        # 处理numpy类型
        records = df.to_dict(orient="records")
        for record in records:
            for key, value in record.items():
                if isinstance(value, (np.integer, np.floating)):
                    record[key] = float(value)
                elif isinstance(value, np.ndarray):
                    record[key] = value.tolist()

        json_str = json.dumps(records, ensure_ascii=False, indent=2)

        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_str)
            return ExportResult(
                success=True, format="json", file_path=file_path, rows=len(df)
            )
        else:
            return ExportResult(
                success=True, format="json", data=json_str, rows=len(df)
            )

    def _export_excel(
        self, df: pd.DataFrame, file_path: Optional[str]
    ) -> ExportResult:
        """导出为Excel"""
        if not file_path:
            return ExportResult(
                success=False, format="excel", message="Excel格式需要指定文件路径"
            )

        df.to_excel(file_path, index=False, engine="openpyxl")
        return ExportResult(
            success=True, format="excel", file_path=file_path, rows=len(df)
        )

    def export_fitting_result(
        self,
        curve_type: str,
        x_values: np.ndarray,
        y_actual: np.ndarray,
        y_fitted: np.ndarray,
        format: str = "csv",
        file_path: Optional[str] = None,
    ) -> ExportResult:
        """导出拟合结果"""
        df = pd.DataFrame({
            "x": x_values,
            "y_actual": y_actual,
            "y_fitted": y_fitted,
            "residual": y_actual - y_fitted,
        })
        return self.export(df, format, file_path)

