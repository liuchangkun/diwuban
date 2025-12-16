"""
拟合方法选择器 (app.services.characteristic_curves.shared.method_selector)

智能选择最适合的拟合方法。

版本: v1.0
参考: 设计文档 3.6.5节
"""

import logging
from typing import Dict, List, Optional

from app.adapters.db import get_connection
from app.services.characteristic_curves.core.data_structures import ConstraintResult


logger = logging.getLogger(__name__)


class MethodSelector:
    """拟合方法选择器

    智能选择最适合的拟合方法。

    可用拟合方法:
    - poly2: 2次多项式
    - poly3: 3次多项式
    - piecewise_linear: 分段线性
    - cubic_spline: 三次样条
    """

    def __init__(self, config: Optional[Dict] = None):
        """初始化选择器

        Args:
            config: 配置参数,可选

        Raises:
            ValueError: 数据库中缺失推荐方法配置时抛出
        """
        self._config = config or {}

        # 从数据库读取推荐方法规则
        self._selection_rules = self._load_recommendations_from_db()

        logger.info("[方法选择器] 初始化完成", extra={"extra_data": {
            "配置来源": "数据库curve_fit_config表",
            "曲线类型数": len(self._selection_rules)
        }})

    def select(
        self,
        curve_type: str,
        constraints: ConstraintResult,
        config: Optional[Dict] = None
    ) -> List[str]:
        """选择拟合方法

        Args:
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            constraints: 约束计算结果
            config: 额外配置(可选)

        Returns:
            List[str]: 候选方法列表,按优先级排序

        Raises:
            ValueError: 不支持的曲线类型
        """
        curve_type_lower = curve_type.lower()

        if curve_type_lower not in self._selection_rules:
            raise ValueError(f"不支持的曲线类型: {curve_type}")

        # 简化的数据质量分类(P0阶段)
        # 实际应基于constraints中的数据特征判断
        quality_category = 'default'

        # 获取候选方法
        rules = self._selection_rules[curve_type_lower]
        methods = rules.get(quality_category, rules['default'])

        logger.info(
            f"[方法选择] curve_type={curve_type}, "
            f"quality={quality_category}, "
            f"selected_methods={methods}"
        )

        return methods.copy()

    def select_best(
        self,
        curve_type: str,
        constraints: ConstraintResult,
        config: Optional[Dict] = None
    ) -> str:
        """选择单个最佳方法

        Args:
            curve_type: 曲线类型
            constraints: 约束计算结果
            config: 额外配置(可选)

        Returns:
            str: 最佳方法ID
        """
        methods = self.select(curve_type, constraints, config)
        return methods[0] if methods else 'poly2'

    def _load_recommendations_from_db(self) -> Dict[str, Dict[str, List[str]]]:
        """从数据库加载推荐方法规则

        Returns:
            Dict[str, Dict[str, List[str]]]: 推荐方法规则
                格式: {
                    'qh': {'default': [...], 'high_quality': [...], ...},
                    'qp': {...},
                    'qeta': {...}
                }

        Raises:
            ValueError: 数据库中缺失配置或配置格式错误
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 查询推荐方法配置
                    cur.execute("""
                        SELECT config_value 
                        FROM curve_fit_config 
                        WHERE config_key = 'recommended_methods'
                    """)

                    row = cur.fetchone()
                    if not row:
                        logger.error(
                            "[方法选择器] 数据库中缺失推荐方法配置",
                            extra={"extra_data": {
                                "config_key": "recommended_methods",
                                "表名": "curve_fit_config",
                                "解决方案": "请执行SQL脚本: scripts/sql/characteristic_curves/001_create_curve_fit_config.sql"
                            }}
                        )
                        raise ValueError(
                            "数据库中缺失推荐方法配置。"
                            "请执行: scripts/sql/characteristic_curves/001_create_curve_fit_config.sql"
                        )

                    recommendations = row[0]

                    # 验证配置完整性
                    required_curve_types = ['qh', 'qp', 'qeta']
                    required_quality_types = [
                        'default', 'high_quality', 'sparse_data', 'noisy_data']

                    missing_curves = [
                        ct for ct in required_curve_types if ct not in recommendations]
                    if missing_curves:
                        logger.error(
                            "[方法选择器] 推荐方法配置不完整",
                            extra={"extra_data": {
                                "缺失曲线类型": missing_curves,
                                "当前配置": list(recommendations.keys())
                            }}
                        )
                        raise ValueError(f"推荐方法配置缺失必需的曲线类型: {missing_curves}")

                    # 验证每个曲线类型的数据质量类型
                    for curve_type in required_curve_types:
                        curve_config = recommendations.get(curve_type, {})
                        missing_quality = [
                            qt for qt in required_quality_types
                            if qt not in curve_config
                        ]
                        if missing_quality:
                            logger.error(
                                "[方法选择器] 曲线类型配置不完整",
                                extra={"extra_data": {
                                    "曲线类型": curve_type,
                                    "缺失数据质量类型": missing_quality
                                }}
                            )
                            raise ValueError(
                                f"曲线类型 {curve_type} 缺失数据质量类型配置: {missing_quality}"
                            )

                    logger.info(
                        "[方法选择器] 成功加载推荐方法配置",
                        extra={"extra_data": {
                            "曲线类型": list(recommendations.keys()),
                            "配置来源": "curve_fit_config表"
                        }}
                    )

                    return recommendations

        except Exception as e:
            logger.error(
                "[方法选择器] 加载推荐方法配置失败",
                extra={"extra_data": {"错误": str(e)}},
                exc_info=True
            )
            raise
