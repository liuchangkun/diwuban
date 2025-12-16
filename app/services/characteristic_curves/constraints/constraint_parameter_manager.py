"""
约束参数管理器 (app.services.characteristic_curves.constraints.constraint_parameter_manager)

本模块提供约束参数的统一管理：
- 获取约束参数（优先缓存 → 数据库 → 学习 → 默认值）
- 更新约束参数
- 与ConstraintLearner和CacheManager集成

使用方式：
    from app.services.characteristic_curves.constraints import ConstraintParameterManager
    
    manager = ConstraintParameterManager()
    constraints = manager.get_constraints(device_id, curve_type)
"""

import logging
from typing import Any, Dict, Optional

from app.services.characteristic_curves.constraints.constraint_learner import (
    ConstraintLearner,
)
from app.services.characteristic_curves.shared import CacheManager


class ConstraintParameterManager:
    """约束参数管理器

    提供约束参数的统一获取和管理：
    1. 优先从缓存获取
    2. 缓存未命中则从数据库加载
    3. 数据库无记录则尝试学习
    4. 学习失败则使用默认值
    """

    def __init__(
        self,
        learner: Optional[ConstraintLearner] = None,
        cache: Optional[CacheManager] = None
    ):
        """初始化约束参数管理器

        Args:
            learner: 约束学习器（可选，默认创建新实例）
            cache: 缓存管理器（可选，默认使用单例）
        """
        self._learner = learner or ConstraintLearner()
        self._cache = cache or CacheManager()
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

        self._logger.info(
            "[约束管理] 初始化",
            extra={"extra_data": {"组件": "ConstraintParameterManager"}}
        )

    def get_constraints(
        self,
        device_id: int,
        curve_type: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """获取约束参数

        查找顺序：缓存 → 数据库 → 学习（从历史成功拟合）

        注意：不使用默认值回退，如果无法获取约束参数则抛出异常。

        Args:
            device_id: 设备ID
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            use_cache: 是否使用缓存

        Returns:
            Dict: 约束参数字典

        Raises:
            ValueError: 无法获取约束参数时抛出
        """
        cache_key = self._cache.build_key(
            device_id=device_id,
            curve_type=curve_type,
            method_id="constraints"
        )

        # 1. 尝试从缓存获取
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self._logger.debug(f"[约束管理] 缓存命中: {cache_key}")
                return cached

        # 2. 尝试从数据库加载
        db_constraints = self._load_from_database(device_id, curve_type)
        if db_constraints:
            self._cache.set(cache_key, db_constraints)
            return db_constraints

        # 3. 尝试从历史成功拟合中学习
        learned = self._learner.learn_from_history(device_id, curve_type)
        if learned.get('learned_params') and learned.get('confidence', 0) > 0.5:
            constraints = learned['learned_params']
            self._cache.set(cache_key, constraints)
            return constraints

        # 不使用默认值回退，抛出异常
        error_msg = (
            f"无法获取约束参数: device_id={device_id}, curve_type={curve_type}。"
            f"请确保数据库中有配置或历史拟合数据。"
        )
        self._logger.error(
            f"[约束管理] {error_msg}",
            extra={"extra_data": {"设备ID": device_id, "曲线类型": curve_type}}
        )
        raise ValueError(error_msg)

    def update_constraints(
        self,
        device_id: int,
        curve_type: str,
        constraints: Dict[str, Any],
        source: str = "manual"
    ) -> bool:
        """更新约束参数

        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            constraints: 约束参数
            source: 来源 ('manual', 'learned', 'imported')

        Returns:
            bool: 是否成功
        """
        try:
            # 保存到数据库
            success = self._save_to_database(
                device_id, curve_type, constraints, source)

            if success:
                # 更新缓存
                cache_key = self._cache.build_key(
                    device_id=device_id,
                    curve_type=curve_type,
                    method_id="constraints"
                )
                self._cache.set(cache_key, constraints)

                self._logger.info(
                    "[约束管理] 约束参数已更新",
                    extra={"extra_data": {
                        "设备ID": device_id,
                        "曲线类型": curve_type,
                        "来源": source
                    }}
                )

            return success
        except Exception as e:
            self._logger.error(f"[约束管理] 更新约束失败: {e}", exc_info=True)
            return False

    def invalidate_cache(
        self,
        device_id: Optional[int] = None,
        curve_type: Optional[str] = None
    ) -> None:
        """使缓存失效

        Args:
            device_id: 设备ID（可选，为None则清除所有）
            curve_type: 曲线类型（可选）
        """
        if device_id is None:
            self._cache.clear()
        else:
            cache_key = self._cache.build_key(
                device_id=device_id,
                curve_type=curve_type or "",
                method_id="constraints"
            )
            self._cache.delete(cache_key)

    def _load_from_database(
        self,
        device_id: int,
        curve_type: str
    ) -> Optional[Dict[str, Any]]:
        """从数据库加载约束参数

        Args:
            device_id: 设备ID
            curve_type: 曲线类型

        Returns:
            Dict: 约束参数，或None（未找到）
        """
        try:
            from app.adapters.db import get_connection
            import json

            sql = """
                SELECT constraints
                FROM curve_fit_params
                WHERE device_id = %s AND curve_type = %s
                ORDER BY version DESC
                LIMIT 1
            """

            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (device_id, curve_type))
                    row = cur.fetchone()

                    if row and row[0]:
                        if isinstance(row[0], dict):
                            return row[0]
                        return json.loads(row[0])

            return None
        except Exception as e:
            self._logger.debug(f"[约束管理] 数据库加载失败: {e}")
            return None

    def _save_to_database(
        self,
        device_id: int,
        curve_type: str,
        constraints: Dict[str, Any],
        source: str
    ) -> bool:
        """保存约束参数到数据库

        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            constraints: 约束参数
            source: 来源

        Returns:
            bool: 是否成功
        """
        try:
            from app.adapters.db import get_connection
            import json
            from datetime import datetime

            # 准备保存数据
            learned_from_samples = constraints.pop('learned_from_samples', 0)
            learning_method = constraints.pop('learning_method', source)
            statistics = constraints.pop('statistics', None)
            confidence = constraints.pop('confidence', 0.0)

            # 构造自动验证结果
            auto_validation_result = {
                'overall_passed': confidence > 0.5,
                'confidence_level': 'high' if confidence > 0.8 else ('medium' if confidence > 0.5 else 'low'),
                'confidence_score': confidence,
                'validated_at': datetime.now().isoformat()
            }

            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 使用 INSERT ... ON CONFLICT 实现 upsert
                    sql = """
                        INSERT INTO learned_constraints (
                            device_id,
                            curve_type,
                            constraints,
                            learned_from_samples,
                            learning_method,
                            statistics,
                            auto_validation_result,
                            is_applied,
                            applied_at,
                            created_at,
                            created_by
                        ) VALUES (
                            %s, %s, %s::jsonb, %s, %s, %s::jsonb, %s::jsonb,
                            TRUE, NOW(), NOW(), 'system'
                        )
                        ON CONFLICT (device_id, curve_type)
                        DO UPDATE SET
                            constraints = EXCLUDED.constraints,
                            learned_from_samples = EXCLUDED.learned_from_samples,
                            learning_method = EXCLUDED.learning_method,
                            statistics = EXCLUDED.statistics,
                            auto_validation_result = EXCLUDED.auto_validation_result,
                            is_applied = TRUE,
                            applied_at = NOW()
                    """

                    cur.execute(sql, (
                        device_id,
                        curve_type,
                        json.dumps(constraints),
                        max(learned_from_samples, 0),  # 确保非负
                        learning_method,
                        json.dumps(statistics) if statistics else None,
                        json.dumps(auto_validation_result)
                    ))

                conn.commit()

            self._logger.info(
                "[约束管理] 约束参数已保存到数据库",
                extra={"extra_data": {
                    "设备ID": device_id,
                    "曲线类型": curve_type,
                    "学习方法": learning_method,
                    "样本数": learned_from_samples
                }}
            )

            return True

        except Exception as e:
            self._logger.error(
                f"[约束管理] 保存约束到数据库失败: {e}",
                extra={"extra_data": {
                    "设备ID": device_id,
                    "曲线类型": curve_type,
                    "错误": str(e)
                }},
                exc_info=True
            )
            return False

    def learn_and_update(
        self,
        device_id: int,
        curve_type: str,
        min_samples: int = 20
    ) -> Dict[str, Any]:
        """学习并更新约束参数

        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            min_samples: 最小样本数

        Returns:
            Dict: 学习结果
        """
        result = self._learner.learn_from_history(
            device_id, curve_type, min_samples)

        if result.get('learned_params') and result.get('confidence', 0) > 0.5:
            self.update_constraints(
                device_id=device_id,
                curve_type=curve_type,
                constraints=result['learned_params'],
                source="learned"
            )

        return result

    @property
    def learner(self) -> ConstraintLearner:
        """获取约束学习器"""
        return self._learner

    @property
    def cache(self) -> CacheManager:
        """获取缓存管理器"""
        return self._cache
