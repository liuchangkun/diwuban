from __future__ import annotations

"""
准备维表与映射快照（ingest.prepare_dim）
- 从标准映射 JSON（stations/devices/metrics/files）导入/补齐 dim_stations、dim_devices、dim_metric_config
- 采用幂等 UPSERT：不覆盖已有配置，仅补齐缺失字段（参考 docs/表结构与数据库.md 的默认策略）

注意：
- 本模块仅做最小可用实现，满足 run-all 全流程：确保维表存在即可
- 若数据库缺表，请先执行 scripts/create_db_and_tables.sql（或相应初始化脚本）
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from app.adapters.db.gateway import get_conn
from app.core.config.loader import Settings
from app.utils.logging_decorators import (
    business_logger,
    log_key_metrics,
    log_sql_execution,
    log_sql_statement,
)  # 移除未使用的 database_operation_logger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MetricDefaults:
    unit: str
    unit_display: str | None = None
    decimals_policy: str = "as_is"
    fixed_decimals: int | None = None
    value_type: str | None = "number"
    valid_min: float | None = None
    valid_max: float | None = None


def _metric_defaults(metric_key: str) -> MetricDefaults:
    k = (metric_key or "").strip().lower()
    # 单位默认（参考 docs/表结构与数据库.md）
    if k == "frequency" or k.endswith("_frequency") or "frequency" in k:
        return MetricDefaults(unit="Hz", valid_min=0, valid_max=100)
    if k.startswith("voltage") or "_voltage_" in k or k.endswith("_voltage"):
        return MetricDefaults(unit="V", valid_min=0, valid_max=1000)
    if k.startswith("current") or "_current_" in k or k.endswith("_current"):
        return MetricDefaults(unit="A", valid_min=0, valid_max=1000)
    if "power_factor" in k:
        return MetricDefaults(unit="", value_type="number", valid_min=0, valid_max=1)
    if k.endswith("power") or "_power_" in k or k == "power":
        return MetricDefaults(unit="kW", valid_min=0, valid_max=10000)
    if k.endswith("kwh") or "_kwh" in k:
        return MetricDefaults(unit="kWh", valid_min=0, valid_max=None)
    if "pressure" in k:
        return MetricDefaults(unit="MPa")
    if "flow_rate" in k or "instant_flow" in k:
        return MetricDefaults(unit="m3/h")
    if "cumulative_flow" in k:
        return MetricDefaults(unit="m3", valid_min=0, valid_max=None)
    # 默认回退
    return MetricDefaults(unit="")


def _reload_metric_config_from_sql(cur, settings: Settings) -> None:
    """
    清空dim_metric_config表并从SQL文件重新加载数据
    """
    sql_logger = logging.getLogger("sql")

    # 查找SQL文件路径
    from pathlib import Path

    sql_file = Path("scripts/sql/dim_metric_config.sql")
    if not sql_file.exists():
        logger.warning(f"dim_metric_config.sql文件不存在: {sql_file}")
        return

    try:
        # 在当前事务中放开语句超时，避免 TRUNCATE/批量导入受限（测试环境可能较慢）
        try:
            cur.execute("SET LOCAL statement_timeout = 0")  # 本事务有效
        except Exception:
            pass
        # 可选择设置锁等待上限，避免长时间阻塞
        try:
            cur.execute("SET LOCAL lock_timeout = '5s'")
        except Exception:
            pass

        # 先清空表
        truncate_sql = (
            "TRUNCATE TABLE public.dim_metric_config RESTART IDENTITY CASCADE;"
        )
        log_sql_statement(truncate_sql, logger=sql_logger)

        start_time = time.time()
        cur.execute(truncate_sql)

        execution_time = (time.time() - start_time) * 1000
        log_sql_execution(
            sql_type="TRUNCATE",
            sql_summary="清空dim_metric_config表",
            execution_time_ms=execution_time,
            table_name="dim_metric_config",
            logger=sql_logger,
        )

        # 读取SQL文件内容并执行
        sql_content = sql_file.read_text(encoding="utf-8")
        log_sql_statement(f"执行SQL文件: {sql_file}", logger=sql_logger)

        start_time = time.time()
        cur.execute(sql_content)

        execution_time = (time.time() - start_time) * 1000
        log_sql_execution(
            sql_type="INSERT",
            sql_summary=f"从SQL文件导入dim_metric_config数据: {sql_file}",
            execution_time_ms=execution_time,
            table_name="dim_metric_config",
            logger=sql_logger,
        )

        # 获取导入的记录数
        count_sql = "SELECT COUNT(*) FROM public.dim_metric_config"
        cur.execute(count_sql)
        record_count = cur.fetchone()[0]

        logger.info(
            f"成功从SQL文件导入dim_metric_config数据: {record_count}条记录",
            extra={
                "event": "dim_metric_config.sql_import.completed",
                "extra": {"sql_file": str(sql_file), "record_count": record_count},
            },
        )

    except Exception as e:
        logger.error(
            f"从SQL文件导入dim_metric_config失败: {e}",
            extra={
                "event": "dim_metric_config.sql_import.failed",
                "extra": {"sql_file": str(sql_file), "error": str(e)},
            },
        )
        raise


def _ensure_sequences(cur) -> None:
    """将序列推进到当前表的 MAX(id)（避免历史手工插入导致的序列回退引发 PK 冲突）。"""
    sql_logger = logging.getLogger("sql")

    # 处理 dim_stations 序列
    sql1 = "SELECT COALESCE(MAX(id), 0) FROM public.dim_stations"
    log_sql_statement(sql1, logger=sql_logger)
    cur.execute(sql1)
    max_st = int((cur.fetchone() or (0,))[0] or 0)
    if max_st > 0:
        sql2 = "SELECT setval('public.dim_stations_id_seq', %s, %s)"
        log_sql_statement(sql2, {"max_id": max_st}, sql_logger)
        cur.execute(sql2, (max_st, True))
        log_sql_execution(
            sql_type="SELECT",
            sql_summary=f"设置 dim_stations 序列值为 {max_st}",
            execution_time_ms=0,
            table_name="dim_stations",
            logger=sql_logger,
        )

    # 处理 dim_devices 序列
    sql3 = "SELECT COALESCE(MAX(id), 0) FROM public.dim_devices"
    log_sql_statement(sql3, logger=sql_logger)
    cur.execute(sql3)
    max_dev = int((cur.fetchone() or (0,))[0] or 0)
    if max_dev > 0:
        sql4 = "SELECT setval('public.dim_devices_id_seq', %s, %s)"
        log_sql_statement(sql4, {"max_id": max_dev}, sql_logger)
        cur.execute(sql4, (max_dev, True))
        log_sql_execution(
            sql_type="SELECT",
            sql_summary=f"设置 dim_devices 序列值为 {max_dev}",
            execution_time_ms=0,
            table_name="dim_devices",
            logger=sql_logger,
        )

    # 处理 dim_metric_config 序列
    sql5 = "SELECT COALESCE(MAX(id), 0) FROM public.dim_metric_config"
    log_sql_statement(sql5, logger=sql_logger)
    cur.execute(sql5)
    max_mc = int((cur.fetchone() or (0,))[0] or 0)
    if max_mc > 0:
        sql6 = "SELECT setval('public.dim_metric_config_id_seq', %s, %s)"
        log_sql_statement(sql6, {"max_id": max_mc}, sql_logger)
        cur.execute(sql6, (max_mc, True))
        log_sql_execution(
            sql_type="SELECT",
            sql_summary=f"设置 dim_metric_config 序列值为 {max_mc}",
            execution_time_ms=0,
            table_name="dim_metric_config",
            logger=sql_logger,
        )


def _upsert_station(cur, name: str) -> int:
    sql_logger = logging.getLogger("sql")

    # 使用 INSERT ... SELECT ... WHERE NOT EXISTS，避免因序列不同步导致的 PK 冲突
    insert_sql = """
        INSERT INTO public.dim_stations(name)
        SELECT %s
        WHERE NOT EXISTS (
          SELECT 1 FROM public.dim_stations WHERE name = %s
        )
        RETURNING id
        """

    log_sql_statement(insert_sql, {"station_name": name}, sql_logger)
    start_time = time.time()

    try:
        cur.execute(insert_sql, (name, name))
        row = cur.fetchone()
        if row and row[0]:
            execution_time = (time.time() - start_time) * 1000
            log_sql_execution(
                sql_type="INSERT",
                sql_summary=f"新增站点: {name}",
                execution_time_ms=execution_time,
                affected_rows=1,
                table_name="dim_stations",
                parameters={"station_name": name},
                logger=sql_logger,
            )
            return int(row[0])

        # 已存在则查询 id
        select_sql = "SELECT id FROM public.dim_stations WHERE name = %s"
        log_sql_statement(select_sql, {"station_name": name}, sql_logger)
        cur.execute(select_sql, (name,))
        result = int(cur.fetchone()[0])

        execution_time = (time.time() - start_time) * 1000
        log_sql_execution(
            sql_type="SELECT",
            sql_summary=f"查询已存在站点: {name}",
            execution_time_ms=execution_time,
            table_name="dim_stations",
            parameters={"station_name": name},
            logger=sql_logger,
        )
        return result
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        log_sql_execution(
            sql_type="INSERT/SELECT",
            sql_summary=f"处理站点: {name}",
            execution_time_ms=execution_time,
            table_name="dim_stations",
            error=str(e),
            logger=sql_logger,
        )
        raise


def _upsert_device(
    cur, station_id: int, name: str, dtype: str | None, pump_type: str | None
) -> int:
    sql_logger = logging.getLogger("sql")
    dtype = dtype or "pump"

    insert_sql = """
        INSERT INTO public.dim_devices(station_id, name, type, pump_type)
        SELECT %s, %s, %s, %s
        WHERE NOT EXISTS (
          SELECT 1 FROM public.dim_devices WHERE station_id=%s AND name=%s
        )
        RETURNING id
        """

    params = (station_id, name, dtype, pump_type, station_id, name)
    log_sql_statement(
        insert_sql,
        {
            "station_id": station_id,
            "device_name": name,
            "device_type": dtype,
            "pump_type": pump_type,
        },
        sql_logger,
    )

    start_time = time.time()
    try:
        cur.execute(insert_sql, params)
        row = cur.fetchone()
        if row and row[0]:
            execution_time = (time.time() - start_time) * 1000
            log_sql_execution(
                sql_type="INSERT",
                sql_summary=f"新增设备: {name} (站点ID: {station_id})",
                execution_time_ms=execution_time,
                affected_rows=1,
                table_name="dim_devices",
                parameters={"station_id": station_id, "device_name": name},
                logger=sql_logger,
            )
            return int(row[0])

        # 已存在则查询 id
        select_sql = "SELECT id FROM public.dim_devices WHERE station_id=%s AND name=%s"
        log_sql_statement(
            select_sql, {"station_id": station_id, "device_name": name}, sql_logger
        )
        cur.execute(select_sql, (station_id, name))
        r = cur.fetchone()
        result = int(r[0]) if r else 0

        execution_time = (time.time() - start_time) * 1000
        log_sql_execution(
            sql_type="SELECT",
            sql_summary=f"查询已存在设备: {name} (站点ID: {station_id})",
            execution_time_ms=execution_time,
            table_name="dim_devices",
            parameters={"station_id": station_id, "device_name": name},
            logger=sql_logger,
        )
        return result
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        log_sql_execution(
            sql_type="INSERT/SELECT",
            sql_summary=f"处理设备: {name} (站点ID: {station_id})",
            execution_time_ms=execution_time,
            table_name="dim_devices",
            error=str(e),
            logger=sql_logger,
        )
        raise


def _upsert_metric(cur, metric_key: str) -> int:
    sql_logger = logging.getLogger("sql")
    d = _metric_defaults(metric_key)

    upsert_sql = """
        INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, decimals_policy, fixed_decimals, value_type, valid_min, valid_max)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (metric_key) DO UPDATE SET
          unit = COALESCE(public.dim_metric_config.unit, EXCLUDED.unit),
          unit_display = COALESCE(public.dim_metric_config.unit_display, EXCLUDED.unit_display),
          decimals_policy = COALESCE(public.dim_metric_config.decimals_policy, EXCLUDED.decimals_policy),
          fixed_decimals = COALESCE(public.dim_metric_config.fixed_decimals, EXCLUDED.fixed_decimals),
          value_type = COALESCE(public.dim_metric_config.value_type, EXCLUDED.value_type),
          valid_min = COALESCE(public.dim_metric_config.valid_min, EXCLUDED.valid_min),
          valid_max = COALESCE(public.dim_metric_config.valid_max, EXCLUDED.valid_max)
        RETURNING id
        """

    params = (
        metric_key,
        d.unit,
        d.unit_display,
        d.decimals_policy,
        d.fixed_decimals,
        d.value_type,
        d.valid_min,
        d.valid_max,
    )

    log_sql_statement(
        upsert_sql,
        {"metric_key": metric_key, "unit": d.unit, "value_type": d.value_type},
        sql_logger,
    )

    start_time = time.time()
    try:
        cur.execute(upsert_sql, params)
        row = cur.fetchone()
        if row and row[0]:
            execution_time = (time.time() - start_time) * 1000
            log_sql_execution(
                sql_type="UPSERT",
                sql_summary=f"处理指标配置: {metric_key}",
                execution_time_ms=execution_time,
                affected_rows=1,
                table_name="dim_metric_config",
                parameters={"metric_key": metric_key, "unit": d.unit},
                logger=sql_logger,
            )
            return int(row[0])

        # 如果没有返回，则查询 id
        select_sql = "SELECT id FROM public.dim_metric_config WHERE metric_key=%s"
        log_sql_statement(select_sql, {"metric_key": metric_key}, sql_logger)
        cur.execute(select_sql, (metric_key,))
        result = int((cur.fetchone() or (0,))[0])

        execution_time = (time.time() - start_time) * 1000
        log_sql_execution(
            sql_type="SELECT",
            sql_summary=f"查询指标配置: {metric_key}",
            execution_time_ms=execution_time,
            table_name="dim_metric_config",
            parameters={"metric_key": metric_key},
            logger=sql_logger,
        )
        return result
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        log_sql_execution(
            sql_type="UPSERT",
            sql_summary=f"处理指标配置: {metric_key}",
            execution_time_ms=execution_time,
            table_name="dim_metric_config",
            error=str(e),
            logger=sql_logger,
        )
        raise


@business_logger("准备维表", enable_progress=True)
def prepare_dim(settings: Settings, mapping_path: Path) -> None:
    """从映射 JSON 准备维表数据（幂等）。
    - stations → dim_stations
    - devices → dim_devices（关联 station）
    - metrics → dim_metric_config（通过SQL文件导入，不根据mapping生成）
    """
    data: Dict[str, Any] = json.loads(mapping_path.read_text(encoding="utf-8"))
    stations = data.get("stations") or []

    # 记录开始信息
    log_key_metrics(
        "准备维表开始",
        {
            "mapping_file": str(mapping_path),
            "stations_count": len(stations),
            "total_devices": sum(
                len((s or {}).get("devices", []) or []) for s in stations
            ),
            "metric_config_mode": "sql_file_import",  # 不再根据mapping生成
        },
        logger,
    )

    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 序列对齐，避免历史脏数据导致的 PK 冲突
                _ensure_sequences(cur)

                # 先清空并重新导入dim_metric_config表数据
                _reload_metric_config_from_sql(cur, settings)

                for s in stations:
                    sname = str((s or {}).get("name") or "").strip()
                    if not sname:
                        continue
                    sid = _upsert_station(cur, sname)
                    for d in (s or {}).get("devices", []) or []:
                        dname = str((d or {}).get("name") or "").strip()
                        if not dname:
                            continue
                        # 规范化设备类型与泵型
                        dtype_raw = (d or {}).get("type")
                        pump_type_raw = (d or {}).get("pump_type")
                        dtype_norm = None
                        if dtype_raw:
                            k = str(dtype_raw).strip().lower().replace("-", "_")
                            if k in (
                                "main_pipeline",
                                "mainpipeline",
                                "main_pipe",
                                "pipeline",
                                "main",
                            ):
                                dtype_norm = "main_pipeline"
                            elif k in ("pump",):
                                dtype_norm = "pump"
                            else:
                                # 未知类型回退为 pump
                                dtype_norm = "pump"
                        else:
                            dtype_norm = "pump"
                        pump_type_norm = None
                        if dtype_norm == "pump" and pump_type_raw:
                            pr = str(pump_type_raw).strip().lower().replace("-", "_")
                            if pr in ("variable_frequency", "vf", "variable"):
                                pump_type_norm = "variable_frequency"
                            elif pr in ("soft_start", "softstart", "soft"):
                                pump_type_norm = "soft_start"
                        did = _upsert_device(
                            cur, sid, dname, dtype_norm, pump_type_norm
                        )
                        _ = did  # 仅确保存在
                        # 注意：不再处理metrics，因为dim_metric_config通过SQL文件导入
                conn.commit()

        # 记录完成信息
        log_key_metrics(
            "准备维表完成",
            {
                "stations_processed": len(
                    [s for s in stations if str((s or {}).get("name") or "").strip()]
                ),
                "devices_processed": sum(
                    len(
                        [
                            d
                            for d in (s or {}).get("devices", []) or []
                            if str((d or {}).get("name") or "").strip()
                        ]
                    )
                    for s in stations
                ),
                "metric_config_source": "sql_file",  # 来源为SQL文件而非mapping
            },
            logger,
        )

        logger.info("准备维表完成", extra={"event": "prepare.dim", "extra": {}})
    except Exception as e:
        logger.exception("准备维表失败: %s", e)
        raise


# 兼容测试用的导出函数（历史接口）
def _default_unit(metric_key: str):
    d = _metric_defaults(metric_key)
    # 历史约定：返回 (unit, unit_display)
    return d.unit, d.unit_display


def _default_policy(metric_key: str):
    d = _metric_defaults(metric_key)
    # 历史约定：返回 (value_type, valid_min, valid_max)
    # 将 None 统一转为浮点 None 兼容测试断言
    return (
        d.value_type or "number",
        float(d.valid_min) if d.valid_min is not None else 0.0,
        float(d.valid_max) if d.valid_max is not None else float("inf"),
    )
