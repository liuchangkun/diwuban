"""
结果存储管理器 (app.services.characteristic_curves.shared.result_storage)

本模块提供拟合结果的持久化存储功能：
- 三表分离设计：curve_fit_results + curve_fit_params + curve_fit_metrics
- 事务保护：确保三表写入的原子性
- 版本管理：支持版本列表、软删除、回滚

使用方式：
    from app.services.characteristic_curves.shared import ResultStorage
    
    storage = ResultStorage()
    version = storage.save(device_id=1, curve_type='qh', fit_result=result)
    loaded = storage.load(device_id=1, curve_type='qh')
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.adapters.db.pool import get_connection
from app.services.characteristic_curves.core.data_structures import FitResult
from app.services.characteristic_curves.shared.curve_point_generator import CurvePointGenerator


class ResultStorage:
    """结果存储管理器

    使用 get_connection() 上下文管理器获取数据库连接，
    实现三表分离设计的原子性写入。
    """

    def __init__(self):
        """初始化存储管理器"""
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")
        self._point_generator = CurvePointGenerator(n_sampling_points=20)
        self._logger.info(
            "[存储] 初始化",
            extra={"extra_data": {
                "组件": "ResultStorage",
                "连接方式": "get_connection()上下文管理器",
                "curve_points生成器": "已集成"
            }}
        )

    def save(
        self,
        device_id: int,
        curve_type: str,
        fit_result: FitResult,
        version: Optional[str] = None,
        skip_quality_gate: bool = False
    ) -> str:
        """保存拟合结果（三表原子写入）

        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            fit_result: 拟合结果对象
            version: 版本号（可选，不指定则自动生成）
            skip_quality_gate: 是否跳过质量门禁检查（默认False）

        Returns:
            str: 版本号

        Raises:
            ValueError: 拟合质量不达标时抛出
        """
        start_time = time.time()
        version = version or datetime.now().strftime('%Y%m%d_%H%M%S')

        # ========== 质量门禁检查 ==========
        if not skip_quality_gate:
            # R² 质量检查
            min_r_squared = 0.5
            if fit_result.r_squared < min_r_squared:
                self._logger.warning(
                    f"[质量门禁] R²={fit_result.r_squared:.4f} < {min_r_squared}，"
                    f"拟合质量不达标",
                    extra={"extra_data": {
                        "设备ID": device_id,
                        "曲线类型": curve_type,
                        "R²": fit_result.r_squared,
                        "阈值": min_r_squared
                    }}
                )
                raise ValueError(
                    f"质量门禁拒绝: R²={fit_result.r_squared:.4f} < {min_r_squared}, "
                    f"device_id={device_id}, curve_type={curve_type}. "
                    f"请检查数据质量或调整拟合方法。"
                )

            # MAPE 质量检查
            max_mape = 50.0
            if fit_result.mape > max_mape:
                self._logger.warning(
                    f"[质量门禁] MAPE={fit_result.mape:.2f}% > {max_mape}%，"
                    f"拟合误差过大",
                    extra={"extra_data": {
                        "设备ID": device_id,
                        "曲线类型": curve_type,
                        "MAPE": fit_result.mape,
                        "阈值": max_mape
                    }}
                )
                raise ValueError(
                    f"质量门禁拒绝: MAPE={fit_result.mape:.2f}% > {max_mape}%, "
                    f"device_id={device_id}, curve_type={curve_type}. "
                    f"请检查数据质量或调整拟合方法。"
                )

        # 生成曲线特征点
        curve_points = None
        try:
            curve_points = self._point_generator.generate(
                curve_type=curve_type,
                coefficients=fit_result.coefficients,
                method_name=fit_result.method_name,
                rated_params=fit_result.metadata.get(
                    'rated_params') if fit_result.metadata else None
            )
        except Exception as e:
            self._logger.warning(
                "[存储] curve_points生成失败,将跳过此字段",
                extra={"extra_data": {
                    "错误类型": type(e).__name__,
                    "错误信息": str(e)
                }}
            )

        self._logger.info(
            "[存储] 开始保存",
            extra={"extra_data": {
                "设备ID": device_id,
                "曲线类型": curve_type,
                "方法名称": fit_result.method_name,
                "版本号": version,
                "R²": fit_result.r_squared,
                "数据点数": fit_result.data_points
            }}
        )

        try:
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    # ========== 步骤1: 插入主表 curve_fit_results ==========
                    time_range = fit_result.time_range or {}
                    insert_result_sql = """
                        INSERT INTO curve_fit_results
                        (device_id, curve_type, version, method_name,
                         data_start_time, data_end_time, data_point_count,
                         curve_points, normalization_params, created_at, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """
                    cursor.execute(insert_result_sql, (
                        device_id, curve_type, version, fit_result.method_name,
                        time_range.get('start'), time_range.get('end'),
                        fit_result.data_points,
                        json.dumps(curve_points) if curve_points else None,
                        json.dumps(
                            fit_result.normalization_params) if fit_result.normalization_params else None,
                        datetime.now(), 'active'
                    ))
                    result_id = cursor.fetchone()[0]

                    # ========== 步骤2: 插入参数表 curve_fit_params ==========
                    insert_params_sql = """
                        INSERT INTO curve_fit_params
                        (result_id, param_category, param_key, param_value)
                        VALUES (%s, %s, %s, %s)
                    """
                    # 插入拟合系数
                    for param_key, param_value in fit_result.coefficients.items():
                        if isinstance(param_value, (int, float)):
                            cursor.execute(insert_params_sql, (
                                result_id, 'fit', param_key, float(param_value)
                            ))

                    # 插入方法参数（从metadata中提取）
                    method_params = fit_result.metadata.get(
                        'method_params', {})
                    for param_key, param_value in method_params.items():
                        if isinstance(param_value, (int, float)):
                            cursor.execute(insert_params_sql, (
                                result_id, 'method', param_key, float(
                                    param_value)
                            ))

                    # ========== 步骤3: 插入指标表 curve_fit_metrics ==========
                    insert_metrics_sql = """
                        INSERT INTO curve_fit_metrics
                        (result_id, r_squared, rmse, mae, mape)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_metrics_sql, (
                        result_id,
                        fit_result.r_squared,
                        fit_result.rmse,
                        fit_result.mae,
                        fit_result.mape
                    ))

                    # ========== 提交事务 ==========
                    conn.commit()

                    duration = (time.time() - start_time) * 1000
                    self._logger.info(
                        "[存储] 三表写入成功",
                        extra={"extra_data": {
                            "设备ID": device_id,
                            "曲线类型": curve_type,
                            "版本号": version,
                            "主表ID": result_id,
                            "参数数量": len(fit_result.coefficients),
                            "curve_points": "已生成" if curve_points else "未生成",
                            "耗时ms": round(duration, 2)
                        }}
                    )
                    return version

        except Exception as e:
            self._logger.error(
                "[存储] 三表写入失败",
                extra={"extra_data": {
                    "设备ID": device_id,
                    "曲线类型": curve_type,
                    "版本号": version,
                    "错误类型": type(e).__name__,
                    "错误信息": str(e)
                }},
                exc_info=True
            )
            raise

    def load(
        self,
        device_id: int,
        curve_type: str,
        version: Optional[str] = None
    ) -> Optional[FitResult]:
        """加载拟合结果

        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            version: 版本号（可选，不指定则返回最新版本）

        Returns:
            FitResult: 拟合结果，不存在则返回None
        """
        start_time = time.time()
        version_desc = version or "latest"

        self._logger.debug(
            "[存储] 开始加载",
            extra={"extra_data": {
                "设备ID": device_id,
                "曲线类型": curve_type,
                "请求版本": version_desc
            }}
        )

        with get_connection() as conn:
            with conn.cursor() as cursor:
                # 查询主表和指标表（JOIN查询）
                if version:
                    query = """
                        SELECT r.id, r.device_id, r.curve_type, r.version, r.method_name,
                               r.data_start_time, r.data_end_time, r.data_point_count,
                               r.normalization_params, r.created_at, r.status,
                               m.r_squared, m.rmse, m.mae, m.mape
                        FROM curve_fit_results r
                        LEFT JOIN curve_fit_metrics m ON r.id = m.result_id
                        WHERE r.device_id = %s AND r.curve_type = %s AND r.version = %s
                          AND r.status = 'active'
                    """
                    cursor.execute(query, (device_id, curve_type, version))
                else:
                    query = """
                        SELECT r.id, r.device_id, r.curve_type, r.version, r.method_name,
                               r.data_start_time, r.data_end_time, r.data_point_count,
                               r.normalization_params, r.created_at, r.status,
                               m.r_squared, m.rmse, m.mae, m.mape
                        FROM curve_fit_results r
                        LEFT JOIN curve_fit_metrics m ON r.id = m.result_id
                        WHERE r.device_id = %s AND r.curve_type = %s AND r.status = 'active'
                        ORDER BY r.created_at DESC LIMIT 1
                    """
                    cursor.execute(query, (device_id, curve_type))

                row = cursor.fetchone()

                if not row:
                    self._logger.warning(
                        "[存储] 加载结果为空",
                        extra={"extra_data": {
                            "设备ID": device_id,
                            "曲线类型": curve_type,
                            "请求版本": version_desc
                        }}
                    )
                    return None

                result_id = row[0]

                # 查询参数表
                cursor.execute("""
                    SELECT param_category, param_key, param_value
                    FROM curve_fit_params
                    WHERE result_id = %s
                """, (result_id,))

                coefficients = {}
                method_params = {}
                for param_row in cursor.fetchall():
                    category, key, value = param_row
                    if category == 'fit':
                        coefficients[key] = value
                    elif category == 'method':
                        method_params[key] = value

                # 构建时间范围
                time_range = {}
                if row[5]:  # data_start_time
                    time_range['start'] = row[5].isoformat() if hasattr(
                        row[5], 'isoformat') else str(row[5])
                if row[6]:  # data_end_time
                    time_range['end'] = row[6].isoformat() if hasattr(
                        row[6], 'isoformat') else str(row[6])

                # 构建FitResult
                fit_result = FitResult(
                    method_id=row[4],  # method_name作为method_id
                    method_name=row[4],
                    version=row[3],
                    coefficients=coefficients,
                    r_squared=row[11] or 0.0,
                    rmse=row[12] or 0.0,
                    mae=row[13] or 0.0,
                    mape=row[14] or 0.0,
                    data_points=row[7] or 0,
                    time_range=time_range,
                    normalization_params=row[8] if isinstance(
                        row[8], dict) else {},
                    created_at=row[9] if row[9] else datetime.now(),
                    metadata={'method_params': method_params}
                )

                duration = (time.time() - start_time) * 1000
                self._logger.info(
                    "[存储] 加载成功",
                    extra={"extra_data": {
                        "设备ID": device_id,
                        "曲线类型": curve_type,
                        "版本号": fit_result.version,
                        "R²": fit_result.r_squared,
                        "耗时ms": round(duration, 2)
                    }}
                )
                return fit_result

    def list_versions(
        self,
        device_id: int,
        curve_type: str,
        limit: int = 10,
        include_deprecated: bool = False
    ) -> List[Dict[str, Any]]:
        """列出历史版本

        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            limit: 返回数量限制
            include_deprecated: 是否包含已废弃版本

        Returns:
            List[Dict]: 版本列表
        """
        with get_connection() as conn:
            with conn.cursor() as cursor:
                status_filter = "" if include_deprecated else "AND r.status = 'active'"
                query = f"""
                    SELECT r.version, r.method_name, r.created_at, r.status,
                           m.r_squared, m.rmse, m.mae, m.mape,
                           r.data_point_count
                    FROM curve_fit_results r
                    LEFT JOIN curve_fit_metrics m ON r.id = m.result_id
                    WHERE r.device_id = %s AND r.curve_type = %s {status_filter}
                    ORDER BY r.created_at DESC
                    LIMIT %s
                """
                cursor.execute(query, (device_id, curve_type, limit))

                versions = []
                for row in cursor.fetchall():
                    versions.append({
                        'version': row[0],
                        'method_name': row[1],
                        'created_at': row[2].isoformat() if row[2] else None,
                        'status': row[3],
                        'r_squared': row[4],
                        'rmse': row[5],
                        'mae': row[6],
                        'mape': row[7],
                        'data_points': row[8]
                    })

                self._logger.debug(
                    "[存储] 版本列表查询完成",
                    extra={"extra_data": {
                        "设备ID": device_id,
                        "曲线类型": curve_type,
                        "版本数量": len(versions)
                    }}
                )
                return versions

    def delete_version(
        self,
        device_id: int,
        curve_type: str,
        version: str,
        soft_delete: bool = True
    ) -> bool:
        """删除指定版本

        Args:
            device_id: 设备ID
            curve_type: 曲线类型
            version: 版本号
            soft_delete: 是否软删除（标记为deprecated）

        Returns:
            bool: 是否删除成功
        """
        with get_connection() as conn:
            with conn.cursor() as cursor:
                if soft_delete:
                    # 软删除：标记为deprecated
                    update_sql = """
                        UPDATE curve_fit_results
                        SET status = 'deprecated'
                        WHERE device_id = %s AND curve_type = %s AND version = %s
                        RETURNING id
                    """
                    cursor.execute(
                        update_sql, (device_id, curve_type, version))
                else:
                    # 硬删除：物理删除（级联删除params和metrics）
                    delete_sql = """
                        DELETE FROM curve_fit_results
                        WHERE device_id = %s AND curve_type = %s AND version = %s
                        RETURNING id
                    """
                    cursor.execute(
                        delete_sql, (device_id, curve_type, version))

                result = cursor.fetchone()
                conn.commit()

                if result:
                    self._logger.info(
                        "[存储] 版本删除成功",
                        extra={"extra_data": {
                            "设备ID": device_id,
                            "曲线类型": curve_type,
                            "版本号": version,
                            "删除方式": "软删除" if soft_delete else "硬删除"
                        }}
                    )
                    return True
                else:
                    self._logger.warning(
                        "[存储] 版本删除失败：版本不存在",
                        extra={"extra_data": {
                            "设备ID": device_id,
                            "曲线类型": curve_type,
                            "版本号": version
                        }}
                    )
                    return False

    def get_latest_version(
        self,
        device_id: int,
        curve_type: str
    ) -> Optional[str]:
        """获取最新版本号

        Args:
            device_id: 设备ID
            curve_type: 曲线类型

        Returns:
            str: 最新版本号，不存在则返回None
        """
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT version FROM curve_fit_results
                    WHERE device_id = %s AND curve_type = %s AND status = 'active'
                    ORDER BY created_at DESC LIMIT 1
                """, (device_id, curve_type))

                row = cursor.fetchone()
                return row[0] if row else None
