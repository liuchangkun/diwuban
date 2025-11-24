"""
泵组曲线对比器

本模块负责对比两种拟合方法的结果：
- 计算指标差异
- 推荐最佳方法
- 生成对比报告

版本: v1.0
创建日期: 2025-12-09
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.services.characteristic_curves.pump_group.models import (
    ComparisonResult,
    CurveFitMethod,
    DirectFitResult,
)


class GroupCurveComparator:
    """泵组曲线对比器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化对比器

        Args:
            config: 配置字典（可选）
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._config = config or self._load_default_config()

    def compare(
        self, direct_fit: DirectFitResult, synthesis: Dict[str, Any]
    ) -> ComparisonResult:
        """
        对比两种方法

        Args:
            direct_fit: 直接拟合结果
            synthesis: 合成曲线结果（包含r_squared, rmse, mae等）

        Returns:
            ComparisonResult: 对比结果
        """
        # 提取合成方法指标
        synthesis_r2 = synthesis.get("r_squared", 0.0)
        synthesis_rmse = synthesis.get("rmse", 0.0)
        synthesis_mae = synthesis.get("mae", 0.0)
        synthesis_mape = synthesis.get("mape", 0.0)

        # 计算差异百分比
        r_squared_diff_pct = self._calculate_diff_pct(
            direct_fit.r_squared, synthesis_r2
        )
        rmse_diff_pct = self._calculate_diff_pct(direct_fit.rmse, synthesis_rmse)
        mae_diff_pct = self._calculate_diff_pct(direct_fit.mae, synthesis_mae)
        mape_diff_pct = self._calculate_diff_pct(direct_fit.mape, synthesis_mape)

        # 推荐方法
        recommended_method, reason = self._recommend_method(
            direct_fit, synthesis, r_squared_diff_pct, rmse_diff_pct
        )

        # 构建对比结果
        result = ComparisonResult(
            r_squared_diff_pct=r_squared_diff_pct,
            rmse_diff_pct=rmse_diff_pct,
            mae_diff_pct=mae_diff_pct,
            mape_diff_pct=mape_diff_pct,
            recommended_method=recommended_method,
            recommendation_reason=reason,
            direct_fit_metrics={
                "r_squared": direct_fit.r_squared,
                "rmse": direct_fit.rmse,
                "mae": direct_fit.mae,
                "mape": direct_fit.mape,
            },
            synthesis_metrics={
                "r_squared": synthesis_r2,
                "rmse": synthesis_rmse,
                "mae": synthesis_mae,
                "mape": synthesis_mape,
            },
            compared_at=datetime.now(),
        )

        self._logger.info(
            f"[对比分析] 推荐方法: {recommended_method.value}, 理由: {reason}, "
            f"R²差异: {r_squared_diff_pct:+.2f}%, RMSE差异: {rmse_diff_pct:+.2f}%"
        )

        return result

    def _calculate_diff_pct(self, direct_fit_value: float, synthesis_value: float) -> float:
        """
        计算差异百分比

        Args:
            direct_fit_value: 直接拟合值
            synthesis_value: 合成值

        Returns:
            float: 差异百分比（正值表示直接拟合更好）
        """
        if synthesis_value == 0:
            return 0.0

        # 对于R²：值越大越好，差异 = (直接拟合 - 合成) / 合成 × 100
        # 对于RMSE/MAE/MAPE：值越小越好，差异 = (合成 - 直接拟合) / 合成 × 100
        # 这里统一返回：正值表示直接拟合更好
        return ((direct_fit_value - synthesis_value) / synthesis_value) * 100

    def _recommend_method(
        self,
        direct_fit: DirectFitResult,
        synthesis: Dict[str, Any],
        r2_diff_pct: float,
        rmse_diff_pct: float,
    ) -> tuple[CurveFitMethod, str]:
        """
        推荐最佳方法

        Args:
            direct_fit: 直接拟合结果
            synthesis: 合成结果
            r2_diff_pct: R²差异百分比
            rmse_diff_pct: RMSE差异百分比

        Returns:
            Tuple[CurveFitMethod, str]: (推荐方法, 推荐理由)
        """
        threshold = self._config["recommendation_threshold_pct"]

        # 规则1: R²显著更高（>阈值）→ 推荐直接拟合
        if r2_diff_pct > threshold:
            return (
                CurveFitMethod.DIRECT_FIT,
                f"直接拟合R²显著更高（+{r2_diff_pct:.2f}%）",
            )

        # 规则2: RMSE显著更低（<-阈值）→ 推荐直接拟合
        # 注意：RMSE越小越好，所以rmse_diff_pct为负表示直接拟合更好
        if rmse_diff_pct < -threshold:
            return (
                CurveFitMethod.DIRECT_FIT,
                f"直接拟合RMSE显著更低（{rmse_diff_pct:.2f}%）",
            )

        # 规则3: 合成方法R²显著更高
        if r2_diff_pct < -threshold:
            return (
                CurveFitMethod.SYNTHESIS,
                f"并联合成R²显著更高（{-r2_diff_pct:.2f}%）",
            )

        # 规则4: 合成方法RMSE显著更低
        if rmse_diff_pct > threshold:
            return (
                CurveFitMethod.SYNTHESIS,
                f"并联合成RMSE显著更低（+{rmse_diff_pct:.2f}%）",
            )

        # 规则5: 差异不显著 → 默认推荐直接拟合（数据驱动）
        return (
            CurveFitMethod.DIRECT_FIT,
            f"两种方法性能相近（R²差异{r2_diff_pct:+.2f}%），推荐数据驱动的直接拟合",
        )

    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "recommendation_threshold_pct": 2.0,  # 推荐阈值（百分比）
        }

