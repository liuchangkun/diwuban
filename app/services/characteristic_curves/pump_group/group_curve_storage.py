"""
泵组曲线结果存储 (app.services.characteristic_curves.pump_group.group_curve_storage)

负责泵组曲线拟合结果的持久化存储和检索。

核心功能：
- 保存直接拟合结果（含fit_method标识）
- 保存双方法结果（DualFitResult）
- 加载历史拟合结果
- 版本管理和历史追溯

版本: v1.0
创建日期: 2025-12-14
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class StoredCurveInfo:
    """存储的曲线信息"""
    curve_id: str
    station_id: int
    pump_combination: List[int]
    curve_type: str
    fit_method: str  # 'direct_fit' or 'synthesis'
    version: str
    created_at: datetime
    metadata: Dict[str, Any]


class GroupCurveStorage:
    """泵组曲线结果存储

    职责：
    1. 保存/加载直接拟合结果
    2. 保存/加载双方法结果
    3. 版本管理
    4. 历史查询

    存储策略：
    - 使用JSON格式存储系数和元数据
    - 支持PostgreSQL JSONB字段
    - 保留历史版本
    """

    def __init__(
        self,
        connection_pool: Any = None,
        table_name: str = "pump_group_curve_results"
    ):
        """
        Args:
            connection_pool: 数据库连接池
            table_name: 存储表名
        """
        self._pool = connection_pool
        self._table_name = table_name

    async def save_direct_fit_result(
        self,
        result: Any,  # DirectFitResult
        station_id: int,
        pump_combination: List[int],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        保存直接拟合结果

        Args:
            result: DirectFitResult对象
            station_id: 站点ID
            pump_combination: 泵组合 [pump_id1, pump_id2, ...]
            metadata: 额外元数据

        Returns:
            str: 生成的曲线ID
        """
        from ..core.data_structures import CurveFitMethod

        curve_id = self._generate_curve_id(
            station_id, pump_combination, result.curve_type, 'direct_fit'
        )

        version = datetime.now().strftime("%Y%m%d_%H%M%S")

        data = {
            'curve_id': curve_id,
            'station_id': station_id,
            'pump_combination': pump_combination,
            'curve_type': result.curve_type,
            'fit_method': CurveFitMethod.DIRECT_FIT.value,
            'version': version,
            'coefficients': result.coefficients,
            'r_squared': result.r_squared,
            'rmse': getattr(result, 'rmse', None),
            'data_points_used': result.data_points_used,
            'Q_range': getattr(result, 'Q_range', None),
            'method_id': getattr(result, 'method_id', None),
            'metadata': metadata or {},
            'created_at': datetime.now().isoformat()
        }

        await self._save_to_db(data)
        logger.info(f"已保存直接拟合结果: {curve_id} v{version}")

        return curve_id

    async def save_synthesis_result(
        self,
        result: Any,  # GroupFitResult
        station_id: int,
        pump_combination: List[int],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        保存合成曲线结果

        Args:
            result: GroupFitResult对象
            station_id: 站点ID
            pump_combination: 泵组合
            metadata: 额外元数据

        Returns:
            str: 生成的曲线ID
        """
        from ..core.data_structures import CurveFitMethod

        curve_id = self._generate_curve_id(
            station_id, pump_combination, result.curve_type, 'synthesis'
        )

        version = datetime.now().strftime("%Y%m%d_%H%M%S")

        data = {
            'curve_id': curve_id,
            'station_id': station_id,
            'pump_combination': pump_combination,
            'curve_type': result.curve_type,
            'fit_method': CurveFitMethod.SYNTHESIS.value,
            'version': version,
            'coefficients': getattr(result, 'coefficients', None),
            'synthesis_params': {
                'Q_total': getattr(result, 'Q_total', None),
                'H_common': getattr(result, 'H_common', None),
                'eta_total': getattr(result, 'eta_total', None),
                'P_total': getattr(result, 'P_total', None)
            },
            'metadata': metadata or {},
            'created_at': datetime.now().isoformat()
        }

        await self._save_to_db(data)
        logger.info(f"已保存合成曲线结果: {curve_id} v{version}")

        return curve_id

    async def save_dual_fit_result(
        self,
        result: Any,  # DualFitResult
        station_id: int,
        pump_combination: List[int],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        保存双方法结果

        Args:
            result: DualFitResult对象
            station_id: 站点ID
            pump_combination: 泵组合
            metadata: 额外元数据

        Returns:
            Tuple[str, str]: (直接拟合曲线ID, 合成曲线ID)
        """
        # 保存直接拟合结果
        direct_curve_id = await self.save_direct_fit_result(
            result.direct_fit_result,
            station_id,
            pump_combination,
            metadata={
                **(metadata or {}),
                'dual_fit': True,
                'comparison': result.comparison,
                'recommended_method': result.recommended_method
            }
        )

        # 保存合成结果
        synthesis_curve_id = await self.save_synthesis_result(
            result.synthesis_result,
            station_id,
            pump_combination,
            metadata={
                **(metadata or {}),
                'dual_fit': True,
                'comparison': result.comparison,
                'recommended_method': result.recommended_method
            }
        )

        logger.info(
            f"已保存双方法结果: 直接拟合={direct_curve_id}, "
            f"合成={synthesis_curve_id}, 推荐={result.recommended_method}"
        )

        return (direct_curve_id, synthesis_curve_id)

    async def load_direct_fit_result(
        self,
        station_id: int,
        pump_combination: List[int],
        curve_type: str = 'qh',
        version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        加载直接拟合结果

        Args:
            station_id: 站点ID
            pump_combination: 泵组合
            curve_type: 曲线类型
            version: 版本号（None则加载最新）

        Returns:
            Dict或None
        """
        curve_id = self._generate_curve_id(
            station_id, pump_combination, curve_type, 'direct_fit'
        )
        return await self._load_from_db(curve_id, version)

    async def load_dual_fit_result(
        self,
        station_id: int,
        pump_combination: List[int],
        curve_type: str = 'qh',
        version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        加载双方法结果

        Args:
            station_id: 站点ID
            pump_combination: 泵组合
            curve_type: 曲线类型
            version: 版本号

        Returns:
            包含直接拟合和合成结果的字典
        """
        direct = await self.load_direct_fit_result(
            station_id, pump_combination, curve_type, version
        )
        synthesis = await self._load_from_db(
            self._generate_curve_id(
                station_id, pump_combination, curve_type, 'synthesis'
            ),
            version
        )

        if direct is None and synthesis is None:
            return None

        return {
            'direct_fit_result': direct,
            'synthesis_result': synthesis,
            'comparison': direct.get('metadata', {}).get('comparison') if direct else None,
            'recommended_method': direct.get('metadata', {}).get('recommended_method') if direct else None
        }

    async def list_versions(
        self,
        station_id: int,
        pump_combination: List[int],
        curve_type: str = 'qh',
        fit_method: str = 'direct_fit'
    ) -> List[StoredCurveInfo]:
        """
        列出所有版本

        Args:
            station_id: 站点ID
            pump_combination: 泵组合
            curve_type: 曲线类型
            fit_method: 拟合方法

        Returns:
            版本列表
        """
        curve_id = self._generate_curve_id(
            station_id, pump_combination, curve_type, fit_method
        )

        if self._pool is None:
            return []

        query = f"""
            SELECT version, created_at, data
            FROM {self._table_name}
            WHERE curve_id = $1
            ORDER BY created_at DESC
        """

        results = []
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, curve_id)
            for row in rows:
                data = row['data'] if isinstance(
                    row['data'], dict) else json.loads(row['data'])
                results.append(StoredCurveInfo(
                    curve_id=curve_id,
                    station_id=station_id,
                    pump_combination=pump_combination,
                    curve_type=curve_type,
                    fit_method=fit_method,
                    version=row['version'],
                    created_at=row['created_at'],
                    metadata=data.get('metadata', {})
                ))

        return results

    async def delete_version(
        self,
        station_id: int,
        pump_combination: List[int],
        curve_type: str,
        fit_method: str,
        version: str
    ) -> bool:
        """删除指定版本"""
        curve_id = self._generate_curve_id(
            station_id, pump_combination, curve_type, fit_method
        )

        if self._pool is None:
            return False

        query = f"""
            DELETE FROM {self._table_name}
            WHERE curve_id = $1 AND version = $2
        """

        async with self._pool.acquire() as conn:
            result = await conn.execute(query, curve_id, version)
            deleted = 'DELETE 1' in result

        if deleted:
            logger.info(f"已删除曲线版本: {curve_id} v{version}")

        return deleted

    def _generate_curve_id(
        self,
        station_id: int,
        pump_combination: List[int],
        curve_type: str,
        fit_method: str
    ) -> str:
        """生成曲线ID"""
        pumps_str = "_".join(str(p) for p in sorted(pump_combination))
        return f"s{station_id}_p{pumps_str}_{curve_type}_{fit_method}"

    async def _save_to_db(self, data: Dict[str, Any]) -> None:
        """保存到数据库"""
        if self._pool is None:
            logger.warning("数据库连接池未初始化，跳过保存")
            return

        query = f"""
            INSERT INTO {self._table_name} 
            (curve_id, version, station_id, pump_combination, curve_type, 
             fit_method, data, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (curve_id, version) DO UPDATE SET
                data = $7,
                created_at = $8
        """

        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                data['curve_id'],
                data['version'],
                data['station_id'],
                data['pump_combination'],
                data['curve_type'],
                data['fit_method'],
                json.dumps(data),
                datetime.now()
            )

    async def _load_from_db(
        self,
        curve_id: str,
        version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """从数据库加载"""
        if self._pool is None:
            return None

        if version:
            query = f"""
                SELECT data FROM {self._table_name}
                WHERE curve_id = $1 AND version = $2
            """
            params = [curve_id, version]
        else:
            query = f"""
                SELECT data FROM {self._table_name}
                WHERE curve_id = $1
                ORDER BY created_at DESC
                LIMIT 1
            """
            params = [curve_id]

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            if row:
                data = row['data']
                return data if isinstance(data, dict) else json.loads(data)

        return None
