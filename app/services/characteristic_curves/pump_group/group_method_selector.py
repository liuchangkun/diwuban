"""
泵组方法选择器 (app.services.characteristic_curves.pump_group.group_method_selector)

智能选择最适合的泵组拟合方法，完全复用单泵的MethodSelector架构。

设计原则：
- 从数据库curve_fit_config表读取配置
- 根据数据特征自动选择方法
- 支持数据质量分类（default/high_quality/sparse_data/noisy_data）

版本: v1.0
创建日期: 2025-12-13
参考: app/services/characteristic_curves/shared/method_selector.py
"""

import logging
from typing import Dict, List, Optional

from app.adapters.db import get_connection


logger = logging.getLogger(__name__)


class GroupMethodSelector:
    """泵组方法选择器
    
    完全复用单泵MethodSelector的架构，从数据库读取推荐配置。
    
    可用拟合方法（复用单泵MethodRegistry）:
    - math_poly_2: 2次多项式
    - math_poly_3: 3次多项式
    - ml_gradient_boost: 梯度提升树
    - ml_gaussian_process: 高斯过程回归
    - physics_pump_char: 泵特性方程
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
        
        logger.info(
            "[泵组方法选择器] 初始化完成",
            extra={"extra_data": {
                "配置来源": "数据库curve_fit_config表",
                "曲线类型数": len(self._selection_rules)
            }}
        )
    
    def select(
        self,
        curve_type: str,
        data_points: int,
        noise_level: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> List[str]:
        """选择拟合方法
        
        Args:
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            data_points: 数据点数量
            noise_level: 噪声水平（可选）
            config: 额外配置(可选)
        
        Returns:
            List[str]: 候选方法列表,按优先级排序
        
        Raises:
            ValueError: 不支持的曲线类型
        """
        curve_type_lower = curve_type.lower()
        
        if curve_type_lower not in self._selection_rules:
            raise ValueError(f"不支持的曲线类型: {curve_type}")
        
        # 数据质量分类
        quality_category = self._analyze_data_quality(data_points, noise_level)
        
        # 获取候选方法
        rules = self._selection_rules[curve_type_lower]
        methods = rules.get(quality_category, rules.get('default', []))
        
        logger.info(
            f"[泵组方法选择] curve_type={curve_type}, "
            f"data_points={data_points}, quality={quality_category}, "
            f"selected_methods={methods}"
        )
        
        return methods.copy()
    
    def select_best(
        self,
        curve_type: str,
        data_points: int,
        noise_level: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> str:
        """选择单个最佳方法
        
        Args:
            curve_type: 曲线类型
            data_points: 数据点数量
            noise_level: 噪声水平（可选）
            config: 额外配置(可选)
        
        Returns:
            str: 最佳方法ID
        """
        methods = self.select(curve_type, data_points, noise_level, config)
        return methods[0] if methods else 'math_poly_2'
    
    def _analyze_data_quality(
        self,
        data_points: int,
        noise_level: Optional[str] = None
    ) -> str:
        """分析数据质量
        
        分类逻辑（与单泵MethodSelector一致）:
        - 数据点 > 500: high_quality
        - 数据点 < 100: sparse_data
        - 噪声明确指定: 使用noise_level
        - 其他: default
        
        Args:
            data_points: 数据点数量
            noise_level: 噪声水平（可选）
        
        Returns:
            str: 数据质量类别
        """
        # 显式指定噪声水平时优先使用
        if noise_level in ['high_quality', 'sparse_data', 'noisy_data', 'default']:
            return noise_level
        
        # 基于数据点数量判断
        if data_points > 500:
            return 'high_quality'
        elif data_points < 100:
            return 'sparse_data'
        else:
            return 'default'
    
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
                    # 查询推荐方法配置（泵组专用key）
                    cur.execute("""
                        SELECT config_value 
                        FROM curve_fit_config 
                        WHERE config_key = 'group_recommended_methods'
                    """)
                    
                    row = cur.fetchone()
                    if not row:
                        logger.warning(
                            "[泵组方法选择器] 数据库中缺失group_recommended_methods配置，使用默认配置",
                            extra={"extra_data": {
                                "config_key": "group_recommended_methods",
                                "表名": "curve_fit_config",
                                "解决方案": "使用内置默认配置，建议执行SQL脚本创建配置"
                            }}
                        )
                        # 返回默认配置
                        return self._get_default_recommendations()
                    
                    recommendations = row[0]
                    
                    # 验证配置完整性
                    self._validate_recommendations(recommendations)
                    
                    logger.info(
                        "[泵组方法选择器] 成功加载推荐方法配置",
                        extra={"extra_data": {
                            "曲线类型": list(recommendations.keys()),
                            "配置来源": "curve_fit_config表"
                        }}
                    )
                    
                    return recommendations
        
        except Exception as e:
            logger.error(
                "[泵组方法选择器] 加载推荐方法配置失败，使用默认配置",
                extra={"extra_data": {"错误": str(e)}},
                exc_info=True
            )
            return self._get_default_recommendations()
    
    def _validate_recommendations(self, recommendations: Dict) -> None:
        """验证推荐配置完整性
        
        Args:
            recommendations: 推荐配置字典
        
        Raises:
            ValueError: 配置不完整
        """
        required_curve_types = ['qh', 'qp', 'qeta']
        required_quality_types = ['default', 'high_quality', 'sparse_data', 'noisy_data']
        
        # 验证曲线类型
        missing_curves = [
            ct for ct in required_curve_types if ct not in recommendations
        ]
        if missing_curves:
            logger.error(
                "[泵组方法选择器] 推荐方法配置不完整",
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
                    "[泵组方法选择器] 曲线类型配置不完整",
                    extra={"extra_data": {
                        "曲线类型": curve_type,
                        "缺失数据质量类型": missing_quality
                    }}
                )
                raise ValueError(
                    f"曲线类型 {curve_type} 缺失数据质量类型配置: {missing_quality}"
                )
    
    def _get_default_recommendations(self) -> Dict[str, Dict[str, List[str]]]:
        """获取默认推荐配置
        
        当数据库配置缺失时使用此默认配置
        
        Returns:
            Dict: 默认推荐方法规则
        """
        return {
            'qh': {
                'default': ['math_poly_2', 'math_poly_3'],
                'high_quality': ['ml_gradient_boost', 'ml_gaussian_process', 'math_poly_3'],
                'sparse_data': ['math_poly_2'],
                'noisy_data': ['ml_gradient_boost', 'math_poly_2']
            },
            'qp': {
                'default': ['math_poly_2', 'physics_power_eq'],
                'high_quality': ['physics_power_eq', 'ml_gradient_boost'],
                'sparse_data': ['math_poly_2'],
                'noisy_data': ['ml_gradient_boost']
            },
            'qeta': {
                'default': ['math_poly_3', 'math_stat_gaussian'],
                'high_quality': ['ml_gaussian_process', 'math_poly_3'],
                'sparse_data': ['math_poly_3'],
                'noisy_data': ['math_stat_gaussian']
            }
        }
