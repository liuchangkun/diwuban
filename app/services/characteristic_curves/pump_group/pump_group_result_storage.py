"""
泵组结果存储器 (app.services.characteristic_curves.pump_group.pump_group_result_storage)

本模块提供泵组曲线结果的存储和读取功能：
- 泵组结果存储到数据库
- 泵组结果读取
- 版本管理

版本: v2.0
更新日期: 2025-12-09
变更: 支持存储直接拟合结果和对比分析结果（通过metadata字段）
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import json
import logging

from app.services.characteristic_curves.models import GroupProcessingStrategy
from app.services.characteristic_curves.shared.exceptions import DataNotFoundError


@dataclass
class GroupFitResult:
    """泵组拟合结果"""

    station_id: int
    pump_combination: List[int]
    group_type: GroupProcessingStrategy
    curve_type: str  # 'qh', 'qp', 'qeta'
    pump_count: int
    valid_n_range: tuple  # (min_n, max_n)

    # 曲线函数（可选，不存储到数据库）
    forward_func: Optional[Callable] = None
    inverse_func: Optional[Callable] = None

    # 修正模型（存储为JSON）
    correction_model: Optional[Dict[str, Any]] = None

    # VFD和SS泵分类
    vfd_pump_ids: List[int] = field(default_factory=list)
    ss_pump_ids: List[int] = field(default_factory=list)

    # 验证指标
    r_squared: Optional[float] = None
    rmse: Optional[float] = None
    mae: Optional[float] = None

    # 元数据
    version: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于数据库存储）"""
        return {
            "station_id": self.station_id,
            "pump_combination": self.pump_combination,
            "group_type": self.group_type.value,
            "curve_type": self.curve_type,
            "pump_count": self.pump_count,
            "valid_n_range": list(self.valid_n_range),
            "correction_model": self.correction_model,
            "vfd_pump_ids": self.vfd_pump_ids,
            "ss_pump_ids": self.ss_pump_ids,
            "r_squared": self.r_squared,
            "rmse": self.rmse,
            "mae": self.mae,
            "version": self.version,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GroupFitResult":
        """从字典创建实例"""
        return cls(
            station_id=data["station_id"],
            pump_combination=data["pump_combination"],
            group_type=GroupProcessingStrategy(data["group_type"]),
            curve_type=data["curve_type"],
            pump_count=data["pump_count"],
            valid_n_range=tuple(data["valid_n_range"]),
            correction_model=data.get("correction_model"),
            vfd_pump_ids=data.get("vfd_pump_ids", []),
            ss_pump_ids=data.get("ss_pump_ids", []),
            r_squared=data.get("r_squared"),
            rmse=data.get("rmse"),
            mae=data.get("mae"),
            version=data.get("version"),
            metadata=data.get("metadata", {}),
        )


class PumpGroupResultStorage:
    """
    泵组结果存储器

    职责：
    1. 泵组结果存储到数据库
    2. 泵组结果读取
    3. 版本管理
    """

    # 表名
    TABLE_NAME = "pump_group_curve_results"

    def __init__(self):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _generate_version(self) -> str:
        """生成版本号（时间戳格式）"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _make_combination_key(self, pump_ids: List[int]) -> str:
        """生成泵组合键（排序后的ID列表）"""
        return ",".join(str(pid) for pid in sorted(pump_ids))

    def save_group_result(self, result: GroupFitResult) -> str:
        """
        保存泵组结果到数据库

        Args:
            result: 泵组拟合结果

        Returns:
            str: 版本号
        """
        version = self._generate_version()
        result.version = version
        result.created_at = datetime.now()

        combination_key = self._make_combination_key(result.pump_combination)

        try:
            from app.adapters.db.pool import get_connection

            with get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = f"""
                        INSERT INTO {self.TABLE_NAME} (
                            station_id, pump_combination, combination_key,
                            group_type, curve_type, pump_count, valid_n_range,
                            correction_model, vfd_pump_ids, ss_pump_ids,
                            r_squared, rmse, mae, version, metadata, created_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s
                        )
                    """
                    cursor.execute(
                        sql,
                        (
                            result.station_id,
                            json.dumps(result.pump_combination),
                            combination_key,
                            result.group_type.value,
                            result.curve_type,
                            result.pump_count,
                            json.dumps(list(result.valid_n_range)),
                            json.dumps(result.correction_model),
                            json.dumps(result.vfd_pump_ids),
                            json.dumps(result.ss_pump_ids),
                            result.r_squared,
                            result.rmse,
                            result.mae,
                            version,
                            json.dumps(result.metadata),
                            result.created_at,
                        ),
                    )
                conn.commit()

            self._logger.info(
                f"[保存泵组结果] station={result.station_id}, "
                f"combination={result.pump_combination}, version={version}"
            )
            return version

        except Exception as e:
            self._logger.error(f"[保存泵组结果] 失败: {e}")
            raise

    def load_group_result(
        self,
        station_id: int,
        pump_combination: List[int],
        curve_type: str = "qh",
        version: Optional[str] = None,
    ) -> GroupFitResult:
        """
        加载泵组结果

        Args:
            station_id: 站点ID
            pump_combination: 泵组合
            curve_type: 曲线类型
            version: 版本号（None表示最新）

        Returns:
            GroupFitResult: 泵组拟合结果

        Raises:
            DataNotFoundError: 未找到结果
        """
        combination_key = self._make_combination_key(pump_combination)

        try:
            from app.adapters.db.pool import get_connection

            with get_connection() as conn:
                with conn.cursor() as cursor:
                    if version:
                        sql = f"""
                            SELECT station_id, pump_combination, group_type,
                                   curve_type, pump_count, valid_n_range,
                                   correction_model, vfd_pump_ids, ss_pump_ids,
                                   r_squared, rmse, mae, version, metadata
                            FROM {self.TABLE_NAME}
                            WHERE station_id = %s
                              AND combination_key = %s
                              AND curve_type = %s
                              AND version = %s
                        """
                        cursor.execute(
                            sql, (station_id, combination_key, curve_type, version)
                        )
                    else:
                        sql = f"""
                            SELECT station_id, pump_combination, group_type,
                                   curve_type, pump_count, valid_n_range,
                                   correction_model, vfd_pump_ids, ss_pump_ids,
                                   r_squared, rmse, mae, version, metadata
                            FROM {self.TABLE_NAME}
                            WHERE station_id = %s
                              AND combination_key = %s
                              AND curve_type = %s
                            ORDER BY created_at DESC
                            LIMIT 1
                        """
                        cursor.execute(sql, (station_id, combination_key, curve_type))

                    row = cursor.fetchone()

                    if row is None:
                        raise DataNotFoundError(
                            message=(
                                f"未找到泵组结果: station={station_id}, "
                                f"combination={pump_combination}"
                            ),
                            data_type="group_result",
                            query_params={
                                "station_id": station_id,
                                "pump_combination": pump_combination,
                                "curve_type": curve_type,
                                "version": version,
                            },
                        )

                    return GroupFitResult(
                        station_id=row[0],
                        pump_combination=json.loads(row[1]),
                        group_type=GroupProcessingStrategy(row[2]),
                        curve_type=row[3],
                        pump_count=row[4],
                        valid_n_range=tuple(json.loads(row[5])),
                        correction_model=json.loads(row[6]) if row[6] else None,
                        vfd_pump_ids=json.loads(row[7]) if row[7] else [],
                        ss_pump_ids=json.loads(row[8]) if row[8] else [],
                        r_squared=row[9],
                        rmse=row[10],
                        mae=row[11],
                        version=row[12],
                        metadata=json.loads(row[13]) if row[13] else {},
                    )

        except DataNotFoundError:
            raise
        except Exception as e:
            self._logger.error(f"[加载泵组结果] 失败: {e}")
            raise

    def list_versions(
        self,
        station_id: int,
        pump_combination: List[int],
        curve_type: str = "qh",
    ) -> List[str]:
        """
        列出所有版本

        Args:
            station_id: 站点ID
            pump_combination: 泵组合
            curve_type: 曲线类型

        Returns:
            List[str]: 版本号列表（按时间倒序）
        """
        combination_key = self._make_combination_key(pump_combination)

        try:
            from app.adapters.db.pool import get_connection

            with get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = f"""
                        SELECT version
                        FROM {self.TABLE_NAME}
                        WHERE station_id = %s
                          AND combination_key = %s
                          AND curve_type = %s
                        ORDER BY created_at DESC
                    """
                    cursor.execute(sql, (station_id, combination_key, curve_type))
                    return [row[0] for row in cursor.fetchall()]

        except Exception as e:
            self._logger.error(f"[列出版本] 失败: {e}")
            return []

    def has_group_result(
        self,
        station_id: int,
        pump_combination: List[int],
        curve_type: str = "qh",
    ) -> bool:
        """
        检查是否存在泵组结果

        Args:
            station_id: 站点ID
            pump_combination: 泵组合
            curve_type: 曲线类型

        Returns:
            bool: 是否存在
        """
        combination_key = self._make_combination_key(pump_combination)

        try:
            from app.adapters.db.pool import get_connection

            with get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = f"""
                        SELECT 1
                        FROM {self.TABLE_NAME}
                        WHERE station_id = %s
                          AND combination_key = %s
                          AND curve_type = %s
                        LIMIT 1
                    """
                    cursor.execute(sql, (station_id, combination_key, curve_type))
                    return cursor.fetchone() is not None

        except Exception as e:
            self._logger.error(f"[检查泵组结果] 失败: {e}")
            return False

    def delete_group_result(
        self,
        station_id: int,
        pump_combination: List[int],
        curve_type: str = "qh",
        version: Optional[str] = None,
    ) -> int:
        """
        删除泵组结果

        Args:
            station_id: 站点ID
            pump_combination: 泵组合
            curve_type: 曲线类型
            version: 版本号（None表示删除所有版本）

        Returns:
            int: 删除的记录数
        """
        combination_key = self._make_combination_key(pump_combination)

        try:
            from app.adapters.db.pool import get_connection

            with get_connection() as conn:
                with conn.cursor() as cursor:
                    if version:
                        sql = f"""
                            DELETE FROM {self.TABLE_NAME}
                            WHERE station_id = %s
                              AND combination_key = %s
                              AND curve_type = %s
                              AND version = %s
                        """
                        cursor.execute(
                            sql, (station_id, combination_key, curve_type, version)
                        )
                    else:
                        sql = f"""
                            DELETE FROM {self.TABLE_NAME}
                            WHERE station_id = %s
                              AND combination_key = %s
                              AND curve_type = %s
                        """
                        cursor.execute(sql, (station_id, combination_key, curve_type))

                    deleted = cursor.rowcount
                conn.commit()

            self._logger.info(
                f"[删除泵组结果] station={station_id}, "
                f"combination={pump_combination}, deleted={deleted}"
            )
            return deleted

        except Exception as e:
            self._logger.error(f"[删除泵组结果] 失败: {e}")
            raise

