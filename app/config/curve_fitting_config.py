"""
特性曲线拟合配置管理 (app.config.curve_fitting_config)

符合文档3.10节规范：
- 使用Pydantic Settings从YAML和环境变量加载配置
- 支持配置优先级：环境变量 > YAML文件 > 默认值
- 禁止硬编码配置值

版本: v1.0
创建日期: 2025-12-11
参考文档: feature-curve-code-implementation.md 第3.10节
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from pydantic import BaseSettings, Field


class DataQualityConfig(BaseSettings):
    """数据质量配置（符合文档3.10.2.1节）"""

    min_data_points: int = Field(100, description="最少数据点数")
    min_duration_days: float = Field(1.0, description="最小时间跨度(天)")
    min_flow_coverage_ratio: float = Field(0.2, description="最小流量覆盖比例")
    max_missing_rate: float = Field(0.05, description="最大缺失率")
    max_outlier_rate: float = Field(0.03, description="最大异常值率")

    class Config:
        env_prefix = "CURVE_FITTING_DATA_QUALITY_"


class ConstraintConfig(BaseSettings):
    """约束参数配置（符合文档3.10.2.2节）"""

    monotonicity_tolerance: float = Field(0.01, description="单调性容差")
    boundary_tolerance: float = Field(0.05, description="边界容差")
    qh_h0_range: Tuple[float, float] = Field(
        (1.1, 1.3), description="QH曲线H0系数范围")
    qp_p0_range: Tuple[float, float] = Field(
        (0.3, 0.5), description="QP曲线P0系数范围")

    class Config:
        env_prefix = "CURVE_FITTING_CONSTRAINT_"


class VisualizationConfig(BaseSettings):
    """可视化配置（符合文档3.10.2.3节）"""

    resolution_width: int = Field(7680, description="8K宽度")
    resolution_height: int = Field(4320, description="8K高度")
    dpi: int = Field(300, description="图片DPI")
    format: str = Field("png", description="图片格式")
    color_scheme: Dict[str, str] = Field(
        default_factory=lambda: {
            "scatter": "#3498db",
            "fit_line": "#e74c3c",
            "confidence_band": "#2ecc71"
        },
        description="颜色方案"
    )
    font_family: str = Field("SimHei", description="中文字体")

    class Config:
        env_prefix = "CURVE_FITTING_VISUALIZATION_"


class PipelineConfig(BaseSettings):
    """管道配置（符合文档3.10.2.4节）"""

    enable_cache: bool = Field(True, description="是否启用缓存")
    cache_ttl: int = Field(3600, description="缓存时间(秒)")
    max_retry_count: int = Field(3, description="最大重试次数")
    timeout: int = Field(300, description="超时时间(秒)")

    class Config:
        env_prefix = "CURVE_FITTING_PIPELINE_"


class CurveFittingConfig(BaseSettings):
    """特性曲线拟合主配置类（符合文档3.10.3节）

    从YAML文件和环境变量加载配置。

    配置优先级（由高到低）:
    1. 环境变量 (CURVE_FITTING_*)
    2. YAML配置文件 (configs/curve_fitting.yaml)
    3. 代码中的默认值

    使用方式:
        # 1. 默认加载 configs/curve_fitting.yaml
        config = CurveFittingConfig()

        # 2. 指定YAML文件
        config = CurveFittingConfig.from_yaml("custom.yaml")

        # 3. 通过环境变量覆盖
        # export CURVE_FITTING_DATA_QUALITY_MIN_DATA_POINTS=200
        config = CurveFittingConfig()
        assert config.data_quality.min_data_points == 200
    """

    data_quality: DataQualityConfig = Field(
        default_factory=DataQualityConfig,
        description="数据质量配置"
    )
    constraints: ConstraintConfig = Field(
        default_factory=ConstraintConfig,
        description="约束参数配置"
    )
    visualization: VisualizationConfig = Field(
        default_factory=VisualizationConfig,
        description="可视化配置"
    )
    pipeline: PipelineConfig = Field(
        default_factory=PipelineConfig,
        description="管道配置"
    )

    class Config:
        env_prefix = "CURVE_FITTING_"
        # YAML文件路径可通过环境变量覆盖
        env_file = os.getenv(
            "CURVE_FITTING_CONFIG_FILE",
            "configs/curve_fitting.yaml"
        )

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "CurveFittingConfig":
        """从YAML文件加载配置

        Args:
            yaml_path: YAML文件路径

        Returns:
            CurveFittingConfig: 配置对象

        Raises:
            FileNotFoundError: YAML文件不存在
            yaml.YAMLError: YAML格式错误
        """
        yaml_file = Path(yaml_path)
        if not yaml_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {yaml_path}")

        with open(yaml_file, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)

        # 从YAML数据构造配置对象
        return cls(
            data_quality=DataQualityConfig(
                **yaml_data.get("data_quality", {})),
            constraints=ConstraintConfig(**yaml_data.get("constraints", {})),
            visualization=VisualizationConfig(
                **yaml_data.get("visualization", {})),
            pipeline=PipelineConfig(**yaml_data.get("pipeline", {}))
        )

    def to_dict(self) -> Dict:
        """导出为字典"""
        return {
            "data_quality": self.data_quality.dict(),
            "constraints": self.constraints.dict(),
            "visualization": self.visualization.dict(),
            "pipeline": self.pipeline.dict()
        }


# 全局配置单例
_global_config: Optional[CurveFittingConfig] = None


def get_config() -> CurveFittingConfig:
    """获取全局配置单例

    首次调用时从默认路径加载YAML文件，后续调用返回缓存的配置。

    Returns:
        CurveFittingConfig: 全局配置对象
    """
    global _global_config
    if _global_config is None:
        config_file = os.getenv(
            "CURVE_FITTING_CONFIG_FILE",
            "configs/curve_fitting.yaml"
        )
        _global_config = CurveFittingConfig.from_yaml(config_file)
    return _global_config


def reload_config() -> CurveFittingConfig:
    """重新加载配置（用于配置变更后刷新）

    Returns:
        CurveFittingConfig: 新的配置对象
    """
    global _global_config
    _global_config = None
    return get_config()
