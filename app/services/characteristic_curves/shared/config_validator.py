"""
配置验证器 (app.services.characteristic_curves.shared.config_validator)

验证曲线拟合配置的有效性。

版本: v1.0
更新日期: 2025-12-08
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ValidationError:
    """验证错误

    Attributes:
        field: 字段名
        message: 错误消息
        value: 当前值
    """

    field: str
    message: str
    value: Any = None


@dataclass
class ConfigValidationResult:
    """配置验证结果

    Attributes:
        is_valid: 是否有效
        errors: 错误列表
        warnings: 警告列表
    """

    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_valid": self.is_valid,
            "errors": [
                {"field": e.field, "message": e.message, "value": e.value}
                for e in self.errors
            ],
            "warnings": self.warnings,
        }


# 配置模式定义
CONFIG_SCHEMA = {
    "curve_type": {
        "type": str,
        "required": True,
        "allowed": ["qh", "qp", "qeta", "heta", "peta", "qnpsh"],
    },
    "method_id": {
        "type": str,
        "required": True,
    },
    "polynomial_degree": {
        "type": int,
        "required": False,
        "min": 1,
        "max": 10,
        "default": 3,
    },
    "smoothing_factor": {
        "type": float,
        "required": False,
        "min": 0.0,
        "max": 1.0,
        "default": 0.1,
    },
    "min_points": {
        "type": int,
        "required": False,
        "min": 5,
        "max": 1000,
        "default": 10,
    },
    "tolerance": {
        "type": float,
        "required": False,
        "min": 0.0,
        "max": 0.5,
        "default": 0.01,
    },
}


class ConfigValidator:
    """配置验证器

    验证曲线拟合配置是否符合规范。

    使用方式:
        validator = ConfigValidator()
        result = validator.validate({'curve_type': 'qh', 'method_id': 'polynomial'})
    """

    def __init__(self, schema: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        """初始化配置验证器

        Args:
            schema: 配置模式（如果为None，使用默认模式）
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.schema = schema or CONFIG_SCHEMA

    def validate(self, config: Dict[str, Any]) -> ConfigValidationResult:
        """验证配置

        Args:
            config: 配置字典

        Returns:
            ConfigValidationResult: 验证结果
        """
        errors: List[ValidationError] = []
        warnings: List[str] = []

        for field_name, rules in self.schema.items():
            value = config.get(field_name)

            # 检查必填字段
            if rules.get("required") and value is None:
                errors.append(
                    ValidationError(field_name, f"必填字段缺失", None)
                )
                continue

            if value is None:
                continue

            # 检查类型
            expected_type = rules.get("type")
            if expected_type and not isinstance(value, expected_type):
                errors.append(
                    ValidationError(field_name, f"类型错误，期望{expected_type.__name__}", value)
                )
                continue

            # 检查允许的值
            allowed = rules.get("allowed")
            if allowed and value not in allowed:
                errors.append(
                    ValidationError(field_name, f"值不在允许范围内: {allowed}", value)
                )

            # 检查范围
            min_val = rules.get("min")
            max_val = rules.get("max")
            if min_val is not None and value < min_val:
                errors.append(
                    ValidationError(field_name, f"值小于最小值{min_val}", value)
                )
            if max_val is not None and value > max_val:
                errors.append(
                    ValidationError(field_name, f"值大于最大值{max_val}", value)
                )

        # 检查未知字段
        for key in config:
            if key not in self.schema:
                warnings.append(f"未知配置字段: {key}")

        return ConfigValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def get_defaults(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            field: rules.get("default")
            for field, rules in self.schema.items()
            if "default" in rules
        }

