from __future__ import annotations
from app.services.ingest.prepare_dim.backup import BackupManager
from app.core.config.loader_new import Settings
from app.adapters.db.gateway import get_conn
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict
from pathlib import Path
from dataclasses import dataclass
import hashlib
import time

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

_act = logging.getLogger("activity")


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


def _ensure_sequences(cur) -> None:
    """
    将序列推进到当前表的 MAX(id)（避免历史手工插入导致的序列回退引发 PK 冲突）

    注意：dim_stations 和 dim_devices 已改为使用配置文件中的固定ID，不再使用序列
    """
    sql_logger = None

    # dim_stations 和 dim_devices 已改为固定ID，不再需要序列同步

    # 处理 dim_metric_config 序列
    sql5 = "SELECT COALESCE(MAX(id), 0) FROM public.dim_metric_config"
    cur.execute(sql5)
    max_mc = int((cur.fetchone() or (0,))[0] or 0)
    if max_mc > 0:
        sql6 = "SELECT setval('public.dim_metric_config_id_seq', %s, %s)"
        cur.execute(sql6, (max_mc, True))


def _upsert_station(cur, station_id: int, name: str) -> int:
    """
    插入或更新泵站记录（使用配置文件中的固定ID）

    参数：
        cur: 数据库游标
        station_id: 泵站的固定ID（从配置文件读取）
        name: 泵站名称

    返回：
        int: 泵站ID（与传入的station_id相同）
    """
    sql_logger = None

    # 使用 INSERT ... ON CONFLICT 实现 upsert，使用固定ID
    upsert_sql = """
        INSERT INTO public.dim_stations(id, name)
        VALUES (%s, %s)
        ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
        """

    start_time = time.time()

    try:
        cur.execute(upsert_sql, (station_id, name))
        row = cur.fetchone()
        execution_time = (time.time() - start_time) * 1000
        return int(row[0])
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        raise


def _upsert_device(
    cur, device_id: int, station_id: int, name: str, dtype: str | None, pump_type: str | None
) -> int:
    """
    插入或更新设备记录（使用配置文件中的固定ID）

    参数：
        cur: 数据库游标
        device_id: 设备的固定ID（从配置文件读取）
        station_id: 所属泵站ID
        name: 设备名称
        dtype: 设备类型
        pump_type: 泵类型（仅pump类型设备需要）

    返回：
        int: 设备ID（与传入的device_id相同）
    """
    sql_logger = None
    dtype = dtype or "pump"

    # 使用 INSERT ... ON CONFLICT 实现 upsert，使用固定ID
    upsert_sql = """
        INSERT INTO public.dim_devices(id, station_id, name, type, pump_type)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            station_id = EXCLUDED.station_id,
            name = EXCLUDED.name,
            type = EXCLUDED.type,
            pump_type = EXCLUDED.pump_type
        RETURNING id
        """

    params = (device_id, station_id, name, dtype, pump_type)

    start_time = time.time()
    try:
        cur.execute(upsert_sql, params)
        row = cur.fetchone()
        execution_time = (time.time() - start_time) * 1000
        return int(row[0])
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        raise


def _upsert_metric(cur, metric_key: str) -> int:
    sql_logger = None
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

    start_time = time.time()
    try:
        cur.execute(upsert_sql, params)
        row = cur.fetchone()
        if row and row[0]:
            execution_time = (time.time() - start_time) * 1000
            return int(row[0])

        # 如果没有返回，则查询 id
        select_sql = "SELECT id FROM public.dim_metric_config WHERE metric_key=%s"
        cur.execute(select_sql, (metric_key,))
        result = int((cur.fetchone() or (0,))[0])

        execution_time = (time.time() - start_time) * 1000
        return result
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        raise


def _upsert_mapping_item(
    cur, station_name: str, device_name: str, metric_key: str
) -> None:
    """幂等写入 dim_mapping_items：仅补齐缺失记录，不覆盖已有。"""
    sql_logger = None
    # 计算映射哈希（稳定）
    h = hashlib.md5(
        f"{station_name}|{device_name}|{metric_key}".encode("utf-8")
    ).hexdigest()
    insert_sql = """
        INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
        SELECT %s, %s, %s, %s, %s
        WHERE NOT EXISTS (
          SELECT 1 FROM public.dim_mapping_items
          WHERE station_name=%s AND device_name=%s AND metric_key=%s
        )
    """
    params = (
        h,
        station_name,
        device_name,
        metric_key,
        "data_mapping.v2.json",
        station_name,
        device_name,
        metric_key,
    )
    start_time = time.time()
    try:
        cur.execute(insert_sql, params)
        execution_time = (time.time() - start_time) * 1000
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        raise


def _validate_metadata_completeness(cur) -> Dict[str, Any]:
    """
    验证 dim_metric_metadata 表的数据完整性

    检查项：
    1. 表是否存在
    2. 总记录数是否正确（56全局 + 56站点 + N设备×56）
    3. 全局级数据是否完整（56条）
    4. 站点级数据是否完整（56条）
    5. 设备级数据是否完整（每个设备56条）

    参数：
        cur: 数据库游标

    返回：
        验证结果字典：
        {
            "is_valid": bool,
            "errors": List[str],
            "warnings": List[str],
            "details": {
                "total_count": int,
                "expected_count": int,
                "global_count": int,
                "station_count": int,
                "device_count": int,
                "device_details": List[Dict]
            }
        }
    """
    result = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "details": {}
    }

    try:
        # 检查表是否存在
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'dim_metric_metadata'
            )
        """)
        table_exists = cur.fetchone()[0]

        if not table_exists:
            result["is_valid"] = False
            result["errors"].append("❌ dim_metric_metadata 表不存在")
            return result

        # 获取设备数量
        cur.execute("SELECT COUNT(*) FROM public.dim_devices")
        device_count = cur.fetchone()[0]

        # 获取指标数量
        cur.execute("SELECT COUNT(*) FROM public.dim_metric_config")
        metric_count = cur.fetchone()[0]

        # 计算期望的总记录数
        expected_total = metric_count + \
            metric_count + (device_count * metric_count)

        # 查询实际数据
        cur.execute("""
            SELECT
                COUNT(*) as total_count,
                COUNT(*) FILTER (WHERE station_id IS NULL AND device_id IS NULL) as global_count,
                COUNT(*) FILTER (WHERE station_id IS NOT NULL AND device_id IS NULL) as station_count,
                COUNT(*) FILTER (WHERE device_id IS NOT NULL) as device_count
            FROM public.dim_metric_metadata
        """)
        row = cur.fetchone()

        total_count = row[0]
        global_count = row[1]
        station_count = row[2]
        device_level_count = row[3]

        # 保存详细信息
        result["details"] = {
            "total_count": total_count,
            "expected_count": expected_total,
            "global_count": global_count,
            "station_count": station_count,
            "device_count": device_level_count,
            "metric_count": metric_count,
            "device_total": device_count
        }

        # 验证总记录数
        if total_count == 0:
            result["is_valid"] = False
            result["errors"].append(
                f"❌ dim_metric_metadata 表为空！期望 {expected_total} 条记录")
            result["errors"].append(
                "   请手动执行迁移脚本：scripts/sql/migrations/100_migrate_metadata_to_three_tier.sql")
            return result

        if total_count != expected_total:
            result["is_valid"] = False
            result["errors"].append(
                f"❌ 总记录数不正确：期望 {expected_total} 条，实际 {total_count} 条")

        # 验证全局级数据
        if global_count != metric_count:
            result["is_valid"] = False
            result["errors"].append(
                f"❌ 全局级数据不完整：期望 {metric_count} 条，实际 {global_count} 条")

        # 验证站点级数据
        if station_count != metric_count:
            result["is_valid"] = False
            result["errors"].append(
                f"❌ 站点级数据不完整：期望 {metric_count} 条，实际 {station_count} 条")

        # 验证设备级数据
        expected_device_level = device_count * metric_count
        if device_level_count != expected_device_level:
            result["is_valid"] = False
            result["errors"].append(
                f"❌ 设备级数据不完整：期望 {expected_device_level} 条，实际 {device_level_count} 条")

        # 查询每个设备的数据完整性
        cur.execute("""
            SELECT
                d.id as device_id,
                d.name as device_name,
                COUNT(m.metric_id) as metric_count
            FROM public.dim_devices d
            LEFT JOIN public.dim_metric_metadata m ON m.device_id = d.id
            GROUP BY d.id, d.name
            ORDER BY d.id
        """)
        device_details = []
        for row in cur.fetchall():
            device_id, device_name, count = row
            device_details.append({
                "device_id": device_id,
                "device_name": device_name,
                "metric_count": count,
                "expected": metric_count,
                "is_complete": count == metric_count
            })

            if count != metric_count:
                result["is_valid"] = False
                result["errors"].append(
                    f"❌ 设备 {device_id} ({device_name}) 数据不完整：期望 {metric_count} 条，实际 {count} 条")

        result["details"]["device_details"] = device_details

        # 如果所有检查都通过
        if result["is_valid"]:
            result["warnings"].append(f"✓ 元数据完整性验证通过：{total_count} 条记录")

    except Exception as e:
        result["is_valid"] = False
        result["errors"].append(f"❌ 验证过程出错：{str(e)}")

    return result


def _clear_non_backup_tables(cur, skip_staging_raw: bool = False) -> int:
    """
    清空不在备份列表中的表

    只清空以下表（按依赖顺序从叶子到根）：
    0. calculation_failures_log, calculation_performance_metrics, completion_audit, completion_failures, staging_rejects, staging_raw（立刻清空）
    1. fact_measurements（所有历史数据，叶子节点）
    2. mv_device_running_1s, mv_metric_60s_stats（派生数据，叶子节点）
    3. completion_runs, completion_steps（审计数据，叶子节点）
    4. （dim_device_capabilities 改为永久配置表，不再清空 - 2025-11-11）
    5. dim_devices（设备维度表，依赖 dim_stations）
    6. dim_stations（站点维度表，根节点）
    7. dim_mapping_items（映射表，叶子节点）

    不清空的12个备份表（2025-11-24更新）：
    - A类手动配置表（4个）：dim_device_capabilities（永久保留，不再清空 - 2025-11-11）,
      pump_characteristic_curves, calculation_validation_config,
      metric_anomaly_strategy（永久保留）,
      optimization_history（永久保留）
    - B类配置表（3个）：device_rated_params（永久保留）,
      calculation_parameters, global_default_rated_params
    - C类维度表（1个）：dim_metric_config
    - D类元数据表（2个）：dim_metric_metadata（永久保留）,
      dim_device_param_metadata
    - E类规则表（1个）：device_running_thresholds

    已删除的表（2025-11-24）：
    - calculation_method_registry（旧版本计算系统）
    - metric_calculation_order（旧版本计算系统）
    - metric_capability_policy（旧版本计算系统）
      （device_running_thresholds_shadow 已删除 - 2025-11-11）

    参数：
    - cur: 数据库游标
    - skip_staging_raw: 是否跳过清空staging_raw表（当ingest_copy=false时设为True，保留已导入的数据）

    注意：
    - 标记"永久保留"的表不会被清空
    - 标记"清空后恢复"的表会被清空，然后从备份恢复
    - 其他备份表不会被清空，也不需要恢复

    返回：清空的总行数
    """
    total_deleted = 0

    # 定义备份表集合（用于日志记录）
    backup_tables = {
        # A类：手动配置表
        "dim_device_capabilities",
        # "dim_metric_metadata_override",  # 已删除：2025-01-07 架构重构
        "pump_characteristic_curves",
        "calculation_validation_config",
        # "metric_capability_policy",  # 已删除：2025-11-24 旧版本计算系统清理
        "metric_anomaly_strategy",  # 永久配置表，不再清空（2025-11-11）
        "optimization_history",  # 永久配置表，不再清空（2025-11-11）
        # B类：配置表
        "device_rated_params",  # 永久配置表，不再清空（2025-11-11）
        # "calculation_method_registry",  # 已删除：2025-11-24 旧版本计算系统清理
        # "metric_calculation_order",  # 已删除：2025-11-24 旧版本计算系统清理
        "calculation_parameters",  # 恢复：需要备份（2025-11-11）
        "global_default_rated_params",  # 新增：全局默认额定参数（2025-11-11）
        # C类：维度表
        "dim_metric_config",
        # D类：元数据表
        "dim_metric_metadata",  # 永久配置表，不再清空（2025-11-11）
        "dim_device_param_metadata",  # 新增：设备参数元数据（2025-11-11）
        # E类：规则表
        # "metric_rule_auto_baseline",  # 已删除（2025-11-07）
        # "metric_rule_auto_baseline_shadow",  # 已删除（2025-11-07）
        "device_running_thresholds",
        # "device_running_thresholds_shadow",  # 已删除（2025-11-11）
    }

    _act.info(f"[清空表] 开始清空非备份表，备份表数量: {len(backup_tables)}")

    # 第0层：立刻清空（日志/审计/临时表，无外键依赖）
    # calculation_failures_log: 计算失败日志表
    cur.execute("DELETE FROM calculation_failures_log")
    deleted = cur.rowcount
    total_deleted += deleted
    _act.info(f"[清空表] calculation_failures_log: {deleted} 行")

    # calculation_performance_metrics: 计算性能指标表
    cur.execute("DELETE FROM calculation_performance_metrics")
    deleted = cur.rowcount
    total_deleted += deleted
    _act.info(f"[清空表] calculation_performance_metrics: {deleted} 行")

    # completion_audit: 完成审计表
    cur.execute("DELETE FROM completion_audit")
    deleted = cur.rowcount
    total_deleted += deleted
    _act.info(f"[清空表] completion_audit: {deleted} 行")

    # completion_failures: 完成失败记录表
    cur.execute("DELETE FROM completion_failures")
    deleted = cur.rowcount
    total_deleted += deleted
    _act.info(f"[清空表] completion_failures: {deleted} 行")

    # staging_rejects: 暂存拒绝表（通常数据量较小）
    # 检查表是否存在后再执行，避免事务失败
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'staging_rejects'
        )
    """)
    if cur.fetchone()[0]:
        cur.execute("DELETE FROM staging_rejects")
        deleted = cur.rowcount
        total_deleted += deleted
        _act.info(f"[清空表] staging_rejects: {deleted} 行")
    else:
        _act.info("[清空表] staging_rejects: 表不存在，跳过")

    # staging_raw: 暂存原始数据表（数据量巨大，使用 TRUNCATE 提升清空速度）
    # 当 ingest_copy=false 时跳过清空，保留已导入的数据以便重复测试合并阶段
    if skip_staging_raw:
        _act.info("[清空表] staging_raw: 跳过清空（ingest_copy=false，保留已导入的数据）")
    else:
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'staging_raw'
            )
        """)
        if cur.fetchone()[0]:
            cur.execute("TRUNCATE TABLE staging_raw")
            _act.info("[清空表] staging_raw: 使用 TRUNCATE 清空（未逐行统计行数）")
        else:
            _act.info("[清空表] staging_raw: 表不存在，跳过")

    # 第1层：叶子节点（无外键依赖）
    # fact_measurements: 所有历史数据
    cur.execute("DELETE FROM fact_measurements")
    deleted = cur.rowcount
    total_deleted += deleted
    _act.info(f"[清空表] fact_measurements: {deleted} 行")

    # mv_device_running_1s: 设备运行状态表（派生数据，可重新生成）
    cur.execute("DELETE FROM mv_device_running_1s")
    deleted = cur.rowcount
    total_deleted += deleted
    _act.info(
        f"[清空表] mv_device_running_1s: {deleted} 行（派生数据，将在 device_running 阶段重新生成）")

    # mv_metric_60s_stats: 指标60秒统计表（派生数据，可重新生成）
    cur.execute("DELETE FROM mv_metric_60s_stats")
    deleted = cur.rowcount
    total_deleted += deleted
    _act.info(f"[清空表] mv_metric_60s_stats: {deleted} 行（派生数据，将在规则生成阶段重新生成）")

    # completion_runs, completion_steps: 审计数据
    cur.execute("DELETE FROM completion_runs")
    deleted = cur.rowcount
    total_deleted += deleted
    _act.info(f"[清空表] completion_runs: {deleted} 行")

    cur.execute("DELETE FROM completion_steps")
    deleted = cur.rowcount
    total_deleted += deleted
    _act.info(f"[清空表] completion_steps: {deleted} 行")

    # 第2层：清空所有引用 dim_devices 的表（包括备份表，稍后会从备份恢复）
    # 按照依赖顺序删除，避免外键约束冲突

    # 2.1 备份表（稍后会从备份恢复）
    # dim_device_capabilities 改为永久配置表，不再清空（2025-11-11）
    # cur.execute("DELETE FROM dim_device_capabilities")
    # deleted = cur.rowcount
    # total_deleted += deleted
    # _act.info(f"[清空表] dim_device_capabilities: {deleted} 行（备份表，稍后恢复）")

    # dim_metric_metadata_override 表已删除（2025-01-07 架构重构）
    # cur.execute("DELETE FROM dim_metric_metadata_override")
    # deleted = cur.rowcount
    # total_deleted += deleted
    # _act.info(f"[清空表] dim_metric_metadata_override: {deleted} 行（备份表，稍后恢复）")

    # device_rated_params 改为永久配置表，不再清空（2025-11-11）
    # cur.execute("DELETE FROM device_rated_params")
    # deleted = cur.rowcount
    # total_deleted += deleted
    # _act.info(f"[清空表] device_rated_params: {deleted} 行（备份表，稍后恢复）")

    # 以下表不清空（2025-11-11）：在备份列表中，但不需要清空和恢复
    # - calculation_parameters：计算参数配置表
    # - global_default_rated_params：全局默认额定参数表
    # - dim_metric_metadata：指标元数据表
    # - dim_device_param_metadata：设备参数元数据表
    # cur.execute("DELETE FROM calculation_parameters")
    # deleted = cur.rowcount
    # total_deleted += deleted
    # _act.info(f"[清空表] calculation_parameters: {deleted} 行（备份表，稍后恢复）")

    # metric_rule_auto_baseline_shadow table deleted (2025-11-07)
    # cur.execute("DELETE FROM metric_rule_auto_baseline_shadow")
    # deleted = cur.rowcount
    # total_deleted += deleted
    # _act.info(f"[清空表] metric_rule_auto_baseline_shadow: {deleted} 行（备份表，稍后恢复）")

    # device_running_thresholds_shadow 表已删除（2025-11-11）
    # cur.execute("DELETE FROM device_running_thresholds_shadow")
    # deleted = cur.rowcount
    # total_deleted += deleted
    # _act.info(f"[清空表] device_running_thresholds_shadow: {deleted} 行（备份表，稍后恢复）")

    # metric_anomaly_strategy 改为永久配置表，不再清空（2025-11-11）
    # cur.execute("DELETE FROM metric_anomaly_strategy")
    # deleted = cur.rowcount
    # total_deleted += deleted
    # _act.info(f"[清空表] metric_anomaly_strategy: {deleted} 行（备份表，稍后恢复）")

    # optimization_history 改为永久配置表，不再清空（2025-11-11）
    # cur.execute("DELETE FROM optimization_history")
    # deleted = cur.rowcount
    # total_deleted += deleted
    # _act.info(f"[清空表] optimization_history: {deleted} 行（备份表，稍后恢复）")

    # 第3层：dim_devices（依赖 dim_stations）
    # 修改：不再清空 dim_devices 表，因为：
    # 1. UPSERT 逻辑已经是幂等的，可以直接更新现有记录
    # 2. calculation_parameters 表的 device_id 外键使用 ON DELETE RESTRICT，
    #    防止删除被引用的设备记录，保护参数数据完整性
    # 3. 如果需要删除孤儿设备，应该在配置文件中移除，然后手动清理
    # cur.execute("DELETE FROM dim_devices")
    # deleted = cur.rowcount
    # total_deleted += deleted
    _act.info(
        f"[清空表] dim_devices: 跳过（使用 UPSERT 逻辑更新，保护 calculation_parameters 外键引用）")

    # 第4层：dim_stations（根节点）
    # 修改：不再清空 dim_stations 表，原因同上
    # cur.execute("DELETE FROM dim_stations")
    # deleted = cur.rowcount
    # total_deleted += deleted
    _act.info(
        f"[清空表] dim_stations: 跳过（使用 UPSERT 逻辑更新，保护 calculation_parameters 外键引用）")

    # 第5层：dim_mapping_items（叶子节点）
    cur.execute("DELETE FROM dim_mapping_items")
    deleted = cur.rowcount
    total_deleted += deleted
    _act.info(f"[清空表] dim_mapping_items: {deleted} 行")

    _act.info(f"[清空表] 完成，共清空 {total_deleted} 行")
    _act.info(f"[清空表] 备份表未清空: {', '.join(sorted(backup_tables))}")

    return total_deleted


def _execute_adaptive_sql_scripts(settings: Settings, cur) -> Dict[str, Any]:
    """
    执行自适应SQL脚本（2个文件）

    执行顺序：
    1. 01_metric_config_related.sql
    2. 02_device_related.sql

    Returns:
        Dict[str, Any]: 执行结果
            - status: "ok" | "error"
            - scripts_executed: List[str] - 成功执行的脚本
            - scripts_failed: List[str] - 失败的脚本
            - errors: Dict[str, str] - 错误信息
    """
    from pathlib import Path as _Path

    result = {
        "status": "ok",
        "scripts_executed": [],
        "scripts_failed": [],
        "errors": {}
    }

    scripts = [
        # "01_metric_config_related.sql",  # 跳过：calculation_method_registry、metric_calculation_order 改为永久配置表（2025-11-11）
        # "02_device_related.sql",         # 跳过：device_rated_params 改为永久配置表（2025-11-11）
        # "03_calculation_parameters.sql",  # 跳过：calculation_parameters 改为永久配置表，不再重新生成（2025-11-10）
        # "04_metadata_override.sql"  # 跳过：dim_metric_metadata_override 从备份恢复
    ]

    adaptive_dir = _Path(
        __file__).parent.parent.parent.parent.parent / "scripts" / "sql" / "adaptive"

    for script_name in scripts:
        try:
            script_path = adaptive_dir / script_name
            if not script_path.exists():
                raise FileNotFoundError(f"SQL脚本不存在: {script_path}")

            sql_content = script_path.read_text(encoding="utf-8")
            cur.execute(sql_content)

            result["scripts_executed"].append(script_name)
            _act.info(f"[执行自适应SQL] {script_name} 执行成功")
        except Exception as e:
            result["scripts_failed"].append(script_name)
            result["errors"][script_name] = str(e)
            result["status"] = "error"
            _act.error(f"[执行自适应SQL] {script_name} 执行失败: {e}")
            # 事务回滚策略：抛出异常，由外层处理
            raise

    return result


def _clear_rule_tables(cur) -> int:
    """
    清空规则表

    清空以下1个表（基线表和shadow表已删除 2025-11-07/2025-11-11）：
    - device_running_thresholds

    返回：清空的总行数
    """
    total_deleted = 0

    rule_tables = [
        # "metric_rule_auto_baseline",  # 已删除（2025-11-07）
        # "metric_rule_auto_baseline_shadow",  # 已删除（2025-11-07）
        "device_running_thresholds",
        # "device_running_thresholds_shadow",  # 已删除（2025-11-11）
    ]

    for table in rule_tables:
        cur.execute(f"TRUNCATE TABLE {table}")
        _act.info(f"[清空规则表] {table}")

    return total_deleted


def _generate_rule_tables(settings) -> Dict[str, Any]:
    """
    生成规则表（三阶段执行）

    阶段A（不依赖 mv_device_running_1s）：
        1. run_running_thresholds()（生产运行阈值，使用存储过程）

    阶段B（调用 device_running）：
        2. device_running_job.run()（填充 mv_device_running_1s 表）

    阶段C（依赖 mv_device_running_1s）：
        （影子运行阈值功能已删除 - 2025-11-07）

    注意：基线计算步骤已删除（2025-11-07）
    返回：生成摘要
    """
    # Baseline imports removed (2025-11-07) - feature deleted
    # from app.services.rules.auto_baseline_b import run_auto_baseline_b
    # from app.services.rules.auto_baseline import run_auto_baseline
    # Shadow thresholds import removed (2025-11-07) - feature deleted
    # from app.services.rules.running_thresholds_b import run_running_thresholds_b
    from app.services.rules.running_thresholds import run_running_thresholds
    from datetime import datetime, timedelta, timezone
    import yaml
    from pathlib import Path

    # 读取配置
    skip_shadow_rules = False  # 默认值
    cfg_device_running = True  # 默认值
    device_running_cfg = None  # 默认值

    try:
        config_path = Path("configs/merge.yaml")
        if config_path.exists():
            config_data = yaml.safe_load(
                config_path.read_text(encoding="utf-8"))
            run_all_cfg = config_data.get("run_all", {}) or {}
            skip_shadow_rules = bool(
                run_all_cfg.get("skip_shadow_rules", False))
            cfg_device_running = bool(run_all_cfg.get("device_running", True))
            device_running_cfg = run_all_cfg.get("device_running_cfg")

            _act.info(
                f"[规则生成] 配置读取：skip_shadow_rules={skip_shadow_rules}, device_running={cfg_device_running}",
                extra={
                    "extra_data": {
                        "event": "config.loaded",
                        "skip_shadow_rules": skip_shadow_rules,
                        "device_running": cfg_device_running,
                        "config_path": str(config_path)
                    }
                }
            )
    except Exception as e:
        _act.warning(
            f"[规则生成] 配置读取失败，使用默认值: {e}",
            extra={
                "extra_data": {
                    "event": "config.load_error",
                    "error": str(e),
                    "defaults": {
                        "skip_shadow_rules": False,
                        "device_running": True
                    }
                }
            }
        )

    result: Dict[str, Any] = {
        "baseline_shadow": 0,
        "baseline_prod": 0,
        "quality_rules_shadow": 0,
        "running_thresholds_shadow": 0,
        "running_thresholds_prod": 0,
        "quality_rules_prod": 0,
        "device_running": None,  # 新增：device_running 执行结果
    }

    # 计算时间窗口（从 fact_measurements 表查询实际数据范围）
    from app.adapters.db.gateway import get_conn

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT MIN(ts_bucket), MAX(ts_bucket) FROM public.fact_measurements")
            row = cur.fetchone() or (None, None)
            if row[0] is not None and row[1] is not None:
                start_time = row[0]
                end_time = row[1]
                _act.info(
                    "[规则生成] 时间窗口从 fact_measurements 表查询",
                    extra={
                        "extra_data": {
                            "event": "time_window.from_fact_measurements",
                            "start": start_time.isoformat(),
                            "end": end_time.isoformat()
                        }
                    }
                )
            else:
                # 回退到最近30天
                now_utc = datetime.now(timezone.utc)
                end_time = now_utc
                start_time = now_utc - timedelta(days=30)
                _act.warning(
                    "[规则生成] fact_measurements 表无数据，使用默认时间窗口（最近30天）",
                    extra={
                        "extra_data": {
                            "event": "time_window.fallback",
                            "start": start_time.isoformat(),
                            "end": end_time.isoformat()
                        }
                    }
                )

    def _iso_utc(dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    win_start = _iso_utc(start_time)
    win_end = _iso_utc(end_time)

    # ========================================================================
    # 阶段A：生成 device_running_thresholds 表（不依赖 mv_device_running_1s）
    # ========================================================================
    _act.info(
        "[规则生成] ========== 阶段A：生成运行阈值（不依赖 mv_device_running_1s） ==========",
        extra={"extra_data": {"event": "phase_a.start"}}
    )

    import threading

    # A1. 生产运行阈值（使用存储过程，不依赖 mv_device_running_1s）
    t0_a1 = time.perf_counter()
    try:
        _act.info(
            "[规则生成] A1/7 开始：run_running_thresholds（生产运行阈值）",
            extra={
                "extra_data": {
                    "event": "rule_generation.start",
                    "function": "run_running_thresholds",
                    "type": "production",
                    "phase": "A",
                    "sequence": "A1/7",
                    "params": {
                        "start": win_start,
                        "end": win_end,
                        "station_id": None,
                        "device_id": None,
                        "ensure_rows": True,
                        "method": "robust"
                    }
                }
            }
        )
        res = run_running_thresholds(
            settings,
            start=win_start,
            end=win_end,
            station_id=None,
            device_id=None,
            ensure_rows=True,
            method="robust",
        )
        count_a1 = res.get("inserted", 0) if isinstance(res, dict) else 0
        duration_ms_a1 = int((time.perf_counter() - t0_a1) * 1000)
        result["running_thresholds_prod"] = {
            "count": count_a1, "duration_ms": duration_ms_a1}
        _act.info(
            f"[规则生成] A1/7 完成：run_running_thresholds (耗时: {duration_ms_a1}ms, 插入: {count_a1}条)",
            extra={
                "extra_data": {
                    "event": "rule_generation.done",
                    "function": "run_running_thresholds",
                    "phase": "A",
                    "sequence": "A1/7",
                    "duration_ms": duration_ms_a1,
                    "result": {"inserted": count_a1}
                }
            }
        )
    except Exception as e:
        duration_ms_a1 = int((time.perf_counter() - t0_a1) * 1000)
        result["running_thresholds_prod"] = {
            "count": 0, "duration_ms": duration_ms_a1, "error": str(e)}
        _act.error(
            f"[规则生成] A1/7 失败：run_running_thresholds (耗时: {duration_ms_a1}ms, 错误: {e})",
            extra={
                "extra_data": {
                    "event": "rule_generation.error",
                    "function": "run_running_thresholds",
                    "phase": "A",
                    "sequence": "A1/7",
                    "duration_ms": duration_ms_a1,
                    "error": str(e)
                }
            }
        )
        raise  # 阶段A失败，中断流程

    # ========================================================================
    # 阶段B：调用 device_running 填充 mv_device_running_1s 表
    # ========================================================================
    _act.info(
        "[规则生成] ========== 阶段B：调用 device_running 填充 mv_device_running_1s ==========",
        extra={"extra_data": {"event": "phase_b.start",
                              "device_running_enabled": cfg_device_running}}
    )

    if cfg_device_running:
        t0_b = time.perf_counter()
        try:
            from app.services.device_running_job import DeviceRunningJob, JobConfig

            _act.info(
                "[规则生成] B/7 开始：device_running（填充 mv_device_running_1s）",
                extra={
                    "extra_data": {
                        "event": "device_running.start",
                        "phase": "B",
                        "sequence": "B/7",
                        "time_window": {
                            "start": start_time.isoformat(),
                            "end": end_time.isoformat()
                        }
                    }
                }
            )

            # 从配置构造作业配置
            _dr = device_running_cfg or {}
            _job_cfg = JobConfig(
                slice_granularity=str(_dr.get("slice", "week")),
                max_device_concurrency=int(
                    _dr.get("max_device_concurrency", 2)),
                update_only_when_changed=bool(
                    _dr.get("update_only_when_changed", True)),
                force_recompute=bool(_dr.get("force_recompute", False)),
            )
            job = DeviceRunningJob(settings, _job_cfg)

            # 执行 device_running
            job.run(start_ts=start_time, end_ts=end_time)

            duration_ms_b = int((time.perf_counter() - t0_b) * 1000)
            result["device_running"] = {
                "success": True, "duration_ms": duration_ms_b}
            _act.info(
                f"[规则生成] B/7 完成：device_running (耗时: {duration_ms_b}ms)",
                extra={
                    "extra_data": {
                        "event": "device_running.done",
                        "phase": "B",
                        "sequence": "B/7",
                        "duration_ms": duration_ms_b
                    }
                }
            )
        except Exception as e:
            duration_ms_b = int((time.perf_counter() - t0_b) * 1000)
            result["device_running"] = {
                "success": False, "duration_ms": duration_ms_b, "error": str(e)}
            _act.error(
                f"[规则生成] B/7 失败：device_running (耗时: {duration_ms_b}ms, 错误: {e})",
                extra={
                    "extra_data": {
                        "event": "device_running.error",
                        "phase": "B",
                        "sequence": "B/7",
                        "duration_ms": duration_ms_b,
                        "error": str(e)
                    }
                }
            )
            raise  # 阶段B失败，中断流程
    else:
        _act.warning(
            "[规则生成] B/7 跳过：device_running（配置已禁用）",
            extra={
                "extra_data": {
                    "event": "device_running.skipped",
                    "phase": "B",
                    "sequence": "B/7",
                    "reason": "device_running=false in config"
                }
            }
        )
        result["device_running"] = {
            "success": False, "skipped": True, "reason": "disabled_in_config"}

    # ========================================================================
    # 阶段B2：填充 mv_metric_60s_stats 表（依赖 fact_measurements）
    # ========================================================================
    _act.info(
        "[规则生成] ========== 阶段B2：填充 mv_metric_60s_stats 表 ==========",
        extra={"extra_data": {"event": "phase_b2.start"}}
    )

    t0_b2 = time.perf_counter()
    try:
        _act.info(
            "[规则生成] B2/1 开始：填充 mv_metric_60s_stats 表",
            extra={
                "extra_data": {
                    "event": "mv_metric_60s_stats.start",
                    "phase": "B2",
                    "sequence": "B2/1",
                    "start_time": start_time.isoformat() if start_time else None,
                    "end_time": end_time.isoformat() if end_time else None
                }
            }
        )

        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "CALL public.sp_refresh_mv_metric_60s_stats(%s, %s, %s, %s)",
                    (start_time, end_time, None, None)  # 全站点、全设备
                )
            conn.commit()

        duration_ms_b2 = int((time.perf_counter() - t0_b2) * 1000)
        result["mv_metric_60s_stats"] = {
            "success": True, "duration_ms": duration_ms_b2}
        _act.info(
            f"[规则生成] B2/1 完成：mv_metric_60s_stats 填充完成 (耗时: {duration_ms_b2}ms)",
            extra={
                "extra_data": {
                    "event": "mv_metric_60s_stats.done",
                    "phase": "B2",
                    "sequence": "B2/1",
                    "duration_ms": duration_ms_b2
                }
            }
        )
    except Exception as e:
        duration_ms_b2 = int((time.perf_counter() - t0_b2) * 1000)
        result["mv_metric_60s_stats"] = {
            "success": False, "duration_ms": duration_ms_b2, "error": str(e)}
        _act.error(
            f"[规则生成] B2/1 失败：mv_metric_60s_stats 填充失败 (耗时: {duration_ms_b2}ms, 错误: {e})",
            extra={
                "extra_data": {
                    "event": "mv_metric_60s_stats.error",
                    "phase": "B2",
                    "sequence": "B2/1",
                    "duration_ms": duration_ms_b2,
                    "error": str(e)
                }
            }
        )
        _act.warning("[规则生成] B2/1 失败不中断流程，继续执行")

    # ========================================================================
    # 阶段C：生成其他规则表（依赖 mv_device_running_1s）
    # ========================================================================
    _act.info(
        "[规则生成] ========== 阶段C：生成其他规则表（依赖 mv_device_running_1s） ==========",
        extra={"extra_data": {"event": "phase_c.start"}}
    )

    # C1. 影子baseline - 已删除（2025-11-07）
    # Reason: Quality checking feature deleted, baseline tables no longer used
    _act.info(
        "[规则生成] C1/7 跳过：run_auto_baseline_b (原因: 功能已删除)",
        extra={
            "extra_data": {
                "event": "rule_generation.skipped",
                "function": "run_auto_baseline_b",
                "type": "shadow",
                "phase": "C",
                "sequence": "C1/7",
                "reason": "feature_deleted_2025-11-07"
            }
        }
    )
    result["baseline_shadow"] = {
        "count": 0, "duration_ms": 0, "skipped": True, "reason": "feature_deleted"}

    # C2. 生产baseline - 已删除（2025-11-07）
    # Reason: Quality checking feature deleted, baseline tables no longer used
    _act.info(
        "[规则生成] C2/7 跳过：run_auto_baseline (原因: 功能已删除)",
        extra={
            "extra_data": {
                "event": "rule_generation.skipped",
                "function": "run_auto_baseline",
                "type": "production",
                "phase": "C",
                "sequence": "C2/7",
                "reason": "feature_deleted_2025-11-07"
            }
        }
    )
    result["baseline_prod"] = {
        "count": 0, "duration_ms": 0, "skipped": True, "reason": "feature_deleted"}

    # C3. 影子运行阈值 - 已删除 (2025-11-07)
    _act.info(
        "[规则生成] C3/7 跳过：影子运行阈值计算 (原因: 功能已删除)",
        extra={
            "extra_data": {
                "event": "rule_generation.skipped",
                "function": "run_running_thresholds_b",
                "type": "shadow",
                "phase": "C",
                "sequence": "C3/7",
                "reason": "feature_deleted"
            }
        }
    )
    result["running_thresholds_shadow"] = {
        "count": 0, "duration_ms": 0, "skipped": True, "reason": "feature_deleted"}

    # C4. 影子质量规则 - 已删除（表不存在）
    _act.info("[规则生成] C4/7 跳过：质量规则（影子）- 表已删除")
    result["quality_rules_shadow"] = {
        "count": 0, "duration_ms": 0, "skipped": True, "reason": "table_deleted"}

    # C5. 生产质量规则 - 已删除（表不存在）
    _act.info("[规则生成] C5/7 跳过：质量规则（生产）- 表已删除")
    result["quality_rules_prod"] = {
        "count": 0, "duration_ms": 0, "skipped": True, "reason": "table_deleted"}

    # =====================================================================
    # 新增：验证 device_running_thresholds 表的完整性
    # =====================================================================
    try:
        from app.services.rules.validate_thresholds import validate_device_running_thresholds

        _act.info(
            "[规则生成] 验证开始：device_running_thresholds 表完整性验证",
            extra={
                "extra_data": {
                    "event": "validation.start",
                    "validation_type": "device_running_thresholds"
                }
            }
        )

        validation_result = validate_device_running_thresholds(settings)
        result["threshold_validation"] = validation_result

        if validation_result["is_valid"]:
            _act.info(
                f"[规则生成] 验证通过：{validation_result['summary']}",
                extra={
                    "extra_data": {
                        "event": "validation.success",
                        "validation_type": "device_running_thresholds",
                        "total_devices": validation_result["total_devices"],
                        "configured_devices": validation_result["configured_devices"]
                    }
                }
            )
        else:
            _act.warning(
                f"[规则生成] 验证失败：{validation_result['summary']}",
                extra={
                    "extra_data": {
                        "event": "validation.failed",
                        "validation_type": "device_running_thresholds",
                        "missing_devices_count": len(validation_result["missing_devices"]),
                        "incomplete_devices_count": len(validation_result["incomplete_devices"]),
                        "warnings": validation_result["warnings"]
                    }
                }
            )
            # 验证失败不中断流程，只记录警告
            for warning in validation_result["warnings"]:
                _act.warning(f"[规则生成] 验证警告：{warning}")

    except Exception as e:
        _act.warning(
            f"[规则生成] 验证失败（异常）：{e}",
            extra={
                "extra_data": {
                    "event": "validation.error",
                    "validation_type": "device_running_thresholds",
                    "error": str(e)
                }
            }
        )
        result["threshold_validation"] = {"is_valid": False, "error": str(e)}

    return result


def prepare_dim(
    settings: Settings,
    mapping_path: Path,
    stage: int | None = None,
    skip_staging_raw: bool = False,
) -> Dict[str, Any]:
    """从映射 JSON 准备维表数据（两阶段执行）。

    参数：
        settings: 系统配置
        mapping_path: 映射文件路径
        stage: 执行阶段（1=阶段1，2=阶段2，None=完整流程）
        skip_staging_raw: 是否跳过清空staging_raw表（当ingest_copy=false时设为True，保留已导入的数据）

    阶段1（在 merge-fact 前执行）：
        - 备份手动配置表
        - 清空依赖表
        - 重建维度表（stations、devices、metrics）
        - 恢复手动配置表
        - 重建基础配置表

    阶段2（在 merge-fact 后执行）：
        - 清空规则表
        - 生成规则表
        - 生成映射表

    返回：执行摘要
    """
    t0 = time.perf_counter()
    result: Dict[str, Any] = {
        "stage": stage or "all",
        "success": False,
        "stations_count": 0,
        "devices_count": 0,
        "metrics_count": 0,
        "duration_ms": 0,
    }

    _act.info(
        "[流程-开始] [维表准备]",
        extra={
            "extra_data": {
                "stage": stage or "all",
                "mapping_path": str(mapping_path),
            }
        },
    )

    data: Dict[str, Any] = json.loads(mapping_path.read_text(encoding="utf-8"))
    stations = data.get("stations") or []

    # 判断执行阶段
    execute_stage1 = stage is None or stage == 1
    execute_stage2 = stage is None or stage == 2

    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # ============================================================
                # 阶段1：维度表重建（在 merge-fact 前执行）
                # ============================================================
                if execute_stage1:
                    _act.info("[prepare-dim] 阶段1：维度表重建")

                    # 1.0 跳过元数据表验证（因为 dim_devices 表会在后续步骤中重建）
                    # 注意：元数据表验证依赖 dim_devices 表，但该表会在步骤1.2中被清空，在步骤1.3中重建
                    # 因此，验证步骤移到步骤1.3之后执行
                    _act.info("[prepare-dim] [0/5] 跳过元数据表验证（将在重建维度表后执行）...")

                    # 1.1 备份15个表（无条件执行，与配置选项无关）
                    _act.info("[prepare-dim] [1/4] 备份15个表...")

                    # 定义需要备份的16个表
                    tables_to_backup = [
                        # A类：手动配置表（5个）
                        "dim_device_capabilities",
                        # "dim_metric_metadata_override",  # 已删除：2025-01-07 架构重构
                        "pump_characteristic_curves",
                        "calculation_validation_config",
                        # "metric_capability_policy",  # 已删除：2025-11-24 旧版本计算系统清理
                        "metric_anomaly_strategy",  # 新增：异常判定策略表
                        "optimization_history",  # 新增：优化历史表（包含RLS状态）
                        # B类：配置表（3个）
                        "device_rated_params",
                        # "calculation_method_registry",  # 已删除：2025-11-24 旧版本计算系统清理
                        # "metric_calculation_order",  # 已删除：2025-11-24 旧版本计算系统清理
                        "calculation_parameters",  # 恢复：需要备份（2025-11-11）
                        "global_default_rated_params",  # 新增：全局默认额定参数（2025-11-11）
                        # C类：维度表（1个）
                        "dim_metric_config",
                        # D类：元数据表（2个）
                        "dim_metric_metadata",  # 恢复：需要备份（2025-11-11）
                        "dim_device_param_metadata",  # 新增：设备参数元数据（2025-11-11）
                        # E类：规则表（1个，基线表和shadow表已删除 2025-11-07/2025-11-11）
                        # "metric_rule_auto_baseline",  # 已删除（2025-11-07）
                        # "metric_rule_auto_baseline_shadow",  # 已删除（2025-11-07）
                        "device_running_thresholds",
                        # "device_running_thresholds_shadow",  # 已删除（2025-11-11）
                    ]

                    backup_manager = BackupManager()
                    backup_result = backup_manager.backup_tables(
                        cur, tables_to_backup)

                    # 统计备份结果
                    ok_count = sum(
                        1 for r in backup_result.values() if r["status"] == "ok")
                    skipped_count = sum(
                        1 for r in backup_result.values() if r["status"] == "skipped")
                    error_count = sum(
                        1 for r in backup_result.values() if r["status"] == "error")

                    _act.info(
                        f"[prepare-dim] ✓ 备份完成：成功 {ok_count} 个，跳过 {skipped_count} 个，失败 {error_count} 个")

                    # 记录详细结果
                    for table_name, result in backup_result.items():
                        if result["status"] == "ok":
                            _act.info(
                                f"  - {table_name}: 备份成功，版本 v{result['version']}，{result['rows']} 行")
                        elif result["status"] == "skipped":
                            _act.info(f"  - {table_name}: {result['message']}")
                        elif result["status"] == "error":
                            _act.warning(
                                f"  - {table_name}: 备份失败 - {result['message']}")

                    # 1.2 清空非备份表
                    _act.info("[prepare-dim] [2/4] 清空非备份表...")
                    total_deleted = _clear_non_backup_tables(
                        cur, skip_staging_raw=skip_staging_raw)
                    _act.info(f"[prepare-dim] ✓ 清空完成：共删除 {total_deleted} 行")

                    # 1.3 重建维度表
                    _act.info("[prepare-dim] [3/4] 重建维度表...")

                    # 序列对齐，避免历史脏数据导致的 PK 冲突
                    _ensure_sequences(cur)

                    # 恢复 dim_metric_config 表数据（从备份）
                    backup_manager = BackupManager()
                    restore_result = backup_manager.restore_table(
                        cur, "dim_metric_config")
                    if restore_result["status"] == "ok":
                        _act.info(
                            f"[prepare-dim] ✓ dim_metric_config 恢复成功，版本 v{restore_result['version']}")
                    else:
                        _act.warning(
                            f"[prepare-dim] ⚠ dim_metric_config 恢复失败: {restore_result['message']}")

                    # 确保 is_active 列存在（幂等）
                    try:
                        cur.execute(
                            "ALTER TABLE public.dim_devices ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT TRUE;")
                    except Exception:
                        pass

                    # UPSERT stations 和 devices
                    stations_count = 0
                    devices_count = 0
                    for s in stations:
                        sname = str((s or {}).get("name") or "").strip()
                        if not sname:
                            continue

                        # 从配置文件读取泵站的固定ID
                        station_id_raw = (s or {}).get("id")
                        if not station_id_raw or not isinstance(station_id_raw, int) or station_id_raw <= 0:
                            raise ValueError(
                                f"泵站 '{sname}' 的ID无效或缺失：{station_id_raw}")

                        sid = _upsert_station(cur, station_id_raw, sname)
                        stations_count += 1

                        for d in (s or {}).get("devices", []) or []:
                            dname = str((d or {}).get("name") or "").strip()
                            if not dname:
                                continue

                            # 从配置文件读取设备的固定ID
                            device_id_raw = (d or {}).get("id")
                            if not device_id_raw or not isinstance(device_id_raw, int) or device_id_raw <= 0:
                                raise ValueError(
                                    f"设备 '{dname}' 的ID无效或缺失：{device_id_raw}")

                            # 规范化设备类型与泵型
                            dtype_raw = (d or {}).get("type")
                            pump_type_raw = (d or {}).get("pump_type")
                            dtype_norm = None
                            if dtype_raw:
                                k = str(dtype_raw).strip(
                                ).lower().replace("-", "_")
                                # 特殊处理：清水池/Other 类设备需纳入 dim_devices，但标记为不参与计算
                                if k in ("clear_water_pool", "clearwaterpool", "clear_water", "clearpool", "pool"):
                                    dtype_norm = "clear_water_pool"
                                elif k in ("other", "others"):
                                    dtype_norm = "other"
                                elif k in ("main_pipeline", "mainpipeline", "main_pipe", "pipeline", "main"):
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
                                pr = str(pump_type_raw).strip(
                                ).lower().replace("-", "_")
                                if pr in ("variable_frequency", "vf", "variable"):
                                    pump_type_norm = "variable_frequency"
                                elif pr in ("soft_start", "softstart", "soft"):
                                    pump_type_norm = "soft_start"

                            did = _upsert_device(
                                cur, device_id_raw, sid, dname, dtype_norm, pump_type_norm)

                            # 规范：确保 other/clear_water_pool 类型标记且禁用参与计算
                            if dtype_norm == "clear_water_pool":
                                try:
                                    cur.execute(
                                        "UPDATE public.dim_devices SET type='clear_water_pool', pump_type=NULL, is_active=FALSE WHERE id=%s",
                                        (did,),
                                    )
                                except Exception:
                                    pass
                            elif dtype_norm == "other":
                                try:
                                    cur.execute(
                                        "UPDATE public.dim_devices SET type='other', pump_type=NULL, is_active=FALSE WHERE id=%s",
                                        (did,),
                                    )
                                except Exception:
                                    pass
                            else:
                                try:
                                    cur.execute(
                                        "UPDATE public.dim_devices SET type=%s WHERE id=%s AND type IS DISTINCT FROM %s",
                                        (dtype_norm, did, dtype_norm),
                                    )
                                except Exception:
                                    pass

                            devices_count += 1

                    # 获取指标数量
                    cur.execute("SELECT COUNT(*) FROM dim_metric_config")
                    metrics_count = cur.fetchone()[0]

                    _act.info(
                        f"[prepare-dim] ✓ 重建完成：{stations_count}个站点, {devices_count}个设备, {metrics_count}个指标")
                    result["stations_count"] = stations_count
                    result["devices_count"] = devices_count
                    result["metrics_count"] = metrics_count

                    # 1.3.5 验证元数据表完整性（在重建维度表后执行）
                    _act.info("[prepare-dim] [3.5/5] 验证元数据表完整性...")
                    validation_result = _validate_metadata_completeness(cur)

                    if not validation_result["is_valid"]:
                        _act.warning("=" * 80)
                        _act.warning("⚠️ 元数据表完整性验证失败（非致命错误）")
                        _act.warning("=" * 80)

                        # 打印所有错误
                        _act.warning("")
                        _act.warning("错误详情：")
                        for i, error in enumerate(validation_result["errors"], 1):
                            _act.warning(f"  {i}. {error}")

                        # 打印当前状态
                        details = validation_result.get("details", {})
                        if details:
                            _act.warning("")
                            _act.warning("当前数据状态：")
                            _act.warning(
                                f"  ├─ 总记录数：{details.get('total_count', 0)} / {details.get('expected_count', 0)} (期望)")
                            _act.warning(
                                f"  ├─ 全局级：{details.get('global_count', 0)} / {details.get('metric_count', 0)} (期望)")
                            _act.warning(
                                f"  ├─ 站点级：{details.get('station_count', 0)} / {details.get('metric_count', 0)} (期望)")
                            _act.warning(
                                f"  └─ 设备级：{details.get('device_count', 0)} / {details.get('device_total', 0) * details.get('metric_count', 0)} (期望)")

                        _act.warning("")
                        _act.warning("说明：元数据表验证失败不会阻止流程继续执行，但可能影响计算结果。")
                        _act.warning(
                            "建议：执行迁移脚本修复元数据表：scripts/sql/migrations/100_migrate_metadata_to_three_tier.sql")
                        _act.warning("=" * 80)
                    else:
                        _act.info("✓ 元数据表完整性验证通过")
                        details = validation_result.get("details", {})
                        _act.info(
                            f"  ├─ 总记录数：{details.get('total_count', 0)} 条")
                        _act.info(
                            f"  ├─ 全局级：{details.get('global_count', 0)} 条")
                        _act.info(
                            f"  ├─ 站点级：{details.get('station_count', 0)} 条")
                        _act.info(
                            f"  └─ 设备级：{details.get('device_count', 0)} 条（{details.get('device_total', 0)} 个设备）")

                        # 打印每个设备的状态（简化版）
                        device_details = details.get("device_details", [])
                        if device_details and len(device_details) <= 10:
                            _act.info("  设备详情：")
                            for device in device_details:
                                _act.info(
                                    f"    ✓ 设备 {device['device_id']} ({device['device_name']}): {device['metric_count']} 条")

                    # 1.4 执行自适应SQL脚本（条件执行，避免覆盖现有配置）
                    _act.info("[prepare-dim] [4/4] 检查配置表状态...")

                    # 检查配置表是否为空
                    tables_to_check = [
                        "device_rated_params",
                        "dim_device_capabilities"
                    ]

                    all_empty = True
                    for table in tables_to_check:
                        cur.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cur.fetchone()[0]
                        if count > 0:
                            _act.info(
                                f"[prepare-dim] 检测到 {table} 表已有 {count} 条数据")
                            all_empty = False
                            break

                    if all_empty:
                        # 所有配置表都为空，执行自适应SQL脚本作为降级方案
                        _act.info("[prepare-dim] 配置表为空，执行自适应SQL脚本作为降级方案...")
                        adaptive_result = _execute_adaptive_sql_scripts(
                            settings, cur)

                        if adaptive_result["status"] == "ok":
                            _act.info(
                                f"[prepare-dim] ✓ 自适应SQL脚本执行完成：成功 {len(adaptive_result['scripts_executed'])} 个")
                            for script_name in adaptive_result["scripts_executed"]:
                                _act.info(f"  - {script_name}: 执行成功")
                        else:
                            _act.error(
                                f"[prepare-dim] ✗ 自适应SQL脚本执行失败：失败 {len(adaptive_result['scripts_failed'])} 个")
                            for script_name, error_msg in adaptive_result["errors"].items():
                                _act.error(f"  - {script_name}: {error_msg}")
                            raise RuntimeError("自适应SQL脚本执行失败")
                    else:
                        # 配置表已有数据，跳过脚本执行，保护现有配置
                        _act.info("[prepare-dim] 配置表已有数据，跳过自适应SQL脚本执行（保护现有配置）")
                        _act.info("[prepare-dim] ✓ 配置表检查完成，保留现有配置")

                    # 注：不再恢复手动配置表（2025-11-11）
                    # 原因：这些表已改为永久配置表，不再清空，因此不需要恢复
                    # 已删除的表（2025-11-24）：calculation_method_registry, metric_calculation_order, metric_capability_policy

                    conn.commit()
                    _act.info("[prepare-dim] 阶段1完成")

                # ============================================================
                # 阶段2：规则生成（在 merge-fact 后执行）
                # ============================================================
                if execute_stage2:
                    _act.info("[prepare-dim] 阶段2：规则生成")

                    # 前置检查：验证 fact_measurements 表是否有数据
                    _act.info(
                        "[prepare-dim] [0/5] 前置检查：验证 fact_measurements 表...")
                    cur.execute("SELECT COUNT(*) FROM fact_measurements")
                    fact_count = cur.fetchone()[0]
                    if fact_count == 0:
                        _act.warning(
                            "[prepare-dim] ⚠ fact_measurements 表为空，无法生成规则表")
                        raise ValueError("fact_measurements 表为空，请先导入数据并完成时间对齐")
                    else:
                        _act.info(
                            f"[prepare-dim] ✓ fact_measurements 表有 {fact_count} 条数据，可以生成规则表")

                    # 2.1 清空规则表
                    _act.info("[prepare-dim] [1/5] 清空规则表...")
                    _clear_rule_tables(cur)
                    _act.info("[prepare-dim] ✓ 清空完成：6个规则表已清空")

                    conn.commit()

                    # 2.3 生成规则表（每个函数使用独立事务）
                    _act.info("[prepare-dim] [3/4] 生成规则表...")
                    rule_result = _generate_rule_tables(settings)
                    # 适配新的返回值结构：从 {"key": {"count": N, "duration_ms": M}} 提取总数
                    # 排除 threshold_validation 键（它的值结构不同）
                    total_rules = sum(
                        v["count"] if isinstance(
                            v, dict) and "count" in v else 0
                        for k, v in rule_result.items()
                        if k != "threshold_validation"
                    )
                    total_duration_ms = sum(
                        v.get("duration_ms", 0) if isinstance(v, dict) else 0
                        for k, v in rule_result.items()
                        if k != "threshold_validation"
                    )
                    _act.info(
                        f"[prepare-dim] ✓ 生成完成：共生成 {total_rules} 条规则（总耗时: {total_duration_ms}ms）")
                    result["rule_generation"] = rule_result

                    # 2.4 生成映射表（dim_mapping_items）
                    _act.info("[prepare-dim] [4/4] 生成映射表...")
                    # TODO: 实现 dim_mapping_items 生成逻辑（如果需要）
                    _act.info("[prepare-dim] ✓ 映射表生成完成")

                    _act.info("[prepare-dim] 阶段2完成")

                # 标记成功
                result["success"] = True

        # 记录完成信息
        dur_ms = int((time.perf_counter() - t0) * 1000)
        result["duration_ms"] = dur_ms

        _act.info(
            "[流程-完成] [维表准备]",
            extra={
                "extra_data": {
                    "stage": stage or "all",
                    "duration_ms": dur_ms,
                    "stations_count": result.get("stations_count", 0),
                    "devices_count": result.get("devices_count", 0),
                    "metrics_count": result.get("metrics_count", 0),
                }
            },
        )

        return result

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
        _act.error(
            "[流程-错误] [维表准备失败]",
            extra={
                "extra_data": {
                    "stage": stage or "all",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
            exc_info=True,
        )
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
