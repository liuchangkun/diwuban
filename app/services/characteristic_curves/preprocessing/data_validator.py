"""
数据验证器 (app.services.characteristic_curves.preprocessing.data_validator)

验证数据格式、范围和最小数据量。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/03_核心模块/05_预处理层.md
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


# 从methods层导入常量
MIN_DATA_POINTS = 50


@dataclass
class ValidationError:
    """验证错误

    Attributes:
        field: 字段名
        error_type: 错误类型
        message: 错误信息
        actual_value: 实际值
        expected_value: 期望值
    """

    field: str
    error_type: str
    message: str
    actual_value: Any = None
    expected_value: Any = None


@dataclass
class DataValidationResult:
    """数据验证结果

    Attributes:
        is_valid: 是否通过验证
        errors: 错误列表
        warnings: 警告列表
        stats: 统计信息
    """

    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_valid": self.is_valid,
            "errors": [
                {
                    "field": e.field,
                    "error_type": e.error_type,
                    "message": e.message,
                }
                for e in self.errors
            ],
            "warnings": self.warnings,
            "stats": self.stats,
        }


class DataValidator:
    """数据验证器

    验证功能:
        - 数据格式验证
        - 数据范围验证
        - 最小数据量检查
        - 列存在性检查

    Attributes:
        min_points: 最小数据点数
        required_columns: 必需的列
    """

    def __init__(
        self,
        min_points: int = MIN_DATA_POINTS,
        required_columns: Optional[List[str]] = None,
    ) -> None:
        """初始化数据验证器

        Args:
            min_points: 最小数据点数
            required_columns: 必需的列名列表
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.min_points = min_points
        self.required_columns = required_columns or []

    def validate(
        self,
        data: pd.DataFrame,
        x_col: str = "Q",
        y_col: str = "H",
        check_range: bool = True,
        value_ranges: Optional[Dict[str, tuple]] = None,
    ) -> DataValidationResult:
        """执行数据验证

        Args:
            data: 待验证数据
            x_col: X列名
            y_col: Y列名
            check_range: 是否检查值域范围
            value_ranges: 自定义值域范围，如 {"Q": (0, 1000), "H": (0, 200)}

        Returns:
            DataValidationResult: 验证结果
        """
        errors: List[ValidationError] = []
        warnings: List[str] = []

        # 检查数据是否为空
        if data is None or len(data) == 0:
            errors.append(
                ValidationError(
                    field="data",
                    error_type="empty_data",
                    message="数据为空",
                )
            )
            return DataValidationResult(is_valid=False, errors=errors)

        # 检查必需列
        errors.extend(self._check_columns(data, [x_col, y_col]))

        # 检查最小数据量
        if len(data) < self.min_points:
            errors.append(
                ValidationError(
                    field="data",
                    error_type="insufficient_data",
                    message=f"数据点数不足: {len(data)} < {self.min_points}",
                    actual_value=len(data),
                    expected_value=self.min_points,
                )
            )

        # 检查值域范围
        if check_range and len(errors) == 0:
            range_errors, range_warnings = self._check_range(
                data, x_col, y_col, value_ranges
            )
            errors.extend(range_errors)
            warnings.extend(range_warnings)

        # 统计信息
        stats = {}
        if x_col in data.columns and y_col in data.columns:
            stats = {
                "row_count": len(data),
                "x_range": [float(data[x_col].min()), float(data[x_col].max())],
                "y_range": [float(data[y_col].min()), float(data[y_col].max())],
                "missing_x": int(data[x_col].isna().sum()),
                "missing_y": int(data[y_col].isna().sum()),
            }

        return DataValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            stats=stats,
        )

    def _check_columns(
        self, data: pd.DataFrame, columns: List[str]
    ) -> List[ValidationError]:
        """检查列是否存在"""
        errors = []
        for col in columns:
            if col not in data.columns:
                errors.append(
                    ValidationError(
                        field=col,
                        error_type="missing_column",
                        message=f"缺少必需列: {col}",
                    )
                )
        return errors

    def _check_range(
        self,
        data: pd.DataFrame,
        x_col: str,
        y_col: str,
        value_ranges: Optional[Dict[str, tuple]],
    ) -> tuple:
        """检查值域范围"""
        errors = []
        warnings = []
        value_ranges = value_ranges or {}

        for col, (min_val, max_val) in value_ranges.items():
            if col in data.columns:
                actual_min = data[col].min()
                actual_max = data[col].max()
                if actual_min < min_val or actual_max > max_val:
                    warnings.append(
                        f"列 {col} 值域超出预期范围: "
                        f"[{actual_min:.2f}, {actual_max:.2f}] vs [{min_val}, {max_val}]"
                    )

        return errors, warnings

    def check_format(self, data: pd.DataFrame) -> bool:
        """检查数据格式是否为DataFrame"""
        return isinstance(data, pd.DataFrame)

    def check_min_points(self, data: pd.DataFrame) -> bool:
        """检查最小数据点数"""
        return len(data) >= self.min_points

