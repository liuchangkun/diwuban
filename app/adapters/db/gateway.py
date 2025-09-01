from __future__ import annotations

"""
数据库网关（adapters.db.gateway）：负责最小可用的 DB 访问与 COPY/MERGE 操作
- get_conn/ make_dsn：连接管理，优先使用连接池，回退到直连
- create_staging_if_not_exists：创建 UNLOGGED staging 表
- copy_valid_lines/insert_rejects：批量导入 staging 与拒绝原因落库
- run_merge_window：集合式合并到事实表，输出结构化 SQL 日志并返回统计

注意：
- 优先使用连接池，未初始化时回退到直连模式
- 仅在运行期需要 psycopg，单元测试中不强制导入连接参数
- SQL 采用与 docs/SCHEMA_AND_DB.md 对齐的列与分区策略
- 慎改返回字段（与 services 层 MergeStats/CopyStats 对齐）
"""


import logging
import time
import time as _time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Iterator

import psycopg

from app.core.config.loader import Settings
from app.core.types import RejectRow, ValidRow
from app.core.exceptions import DatabaseConnectionError, DatabaseError
from app.utils.logging_decorators import (
    create_sql_logger,
    log_sql_execution,
    log_sql_statement,
    database_operation_logger,
)

# 获取日志记录器
logger = logging.getLogger(__name__)


@dataclass
class DbConnParams:
    """根据 Settings 生成连接 DSN 字符串。
    优先级：dsn_write > dsn_read > host/name/user 组合。
    # 连接参数结构：目前仅保留 dsn，后续可扩展（连接池大小、超时等）

    返回：可供 psycopg.connect 使用的 DSN。
    """

    dsn: str


def make_dsn(settings: Settings) -> str:
    """根据配置生成 DSN。
    - 若提供 dsn_write 则优先使用；否则尝试 dsn_read；再否则拼接 host/name/user
    - 示例："host=localhost dbname=pump_station_optimization user=postgres"
    """

    """根据配置生成 DSN。优先使用 dsn_write/dsn_read；否则使用 host/name/user 组合。
    当前项目默认不脱敏，完整输出在 args/config 快照中。
    """
    db = settings.db
    if db.dsn_write:
        return db.dsn_write
    if db.dsn_read:
        return db.dsn_read
    return f"host={db.host} dbname={db.name} user={db.user}"


@contextmanager
def get_conn(settings: Settings) -> Iterator[psycopg.Connection]:
    """
    获取数据库连接：优先使用连接池，未初始化时回退到直连模式。
    
    连接池模式：
    - 使用全局连接池获取连接
    - 自动管理连接生命周期
    - 支持并发访问和连接复用
    
    直连模式（回退）：
    - 仅对“建立连接”做重试；进入 with 块后的异常将原样抛出
    - 连接超时：settings.db.timeouts.connect_timeout_ms
    - 语句超时：settings.db.timeouts.statement_timeout_ms（连接建立后设置）
    - 重试：settings.db.retry（max_retries/retry_delay_ms/backoff_multiplier）
    """
    
    # 尝试使用连接池
    try:
        from app.adapters.db.pool import get_connection
        with get_connection() as conn:
            yield conn
        return
    except (ImportError, DatabaseError):
        # 连接池未初始化或不可用，回退到直连模式
        logger.debug("连接池不可用，使用直连模式")
    
    # 直连模式（原逻辑）
    dsn = make_dsn(settings)
    attempts = max(1, int(settings.db.retry.max_retries))
    delay = max(0.0, float(settings.db.retry.retry_delay_ms) / 1000.0)
    backoff = max(1.0, float(settings.db.retry.backoff_multiplier))

    conn: psycopg.Connection | None = None
    last_exc: Exception | None = None

    # 仅针对“连接建立”进行重试
    for i in range(attempts):
        try:
            conn = psycopg.connect(
                dsn,
                connect_timeout=max(
                    0, int(settings.db.timeouts.connect_timeout_ms) // 1000
                ),
            )
            break
        except Exception as e:
            last_exc = e
            if i < attempts - 1:
                _time.sleep(delay)
                delay *= backoff
            else:
                raise DatabaseConnectionError(
                    f"无法建立数据库连接: {e}",
                    context={"dsn_preview": dsn[:50] + "...", "attempts": attempts}
                ) from e

    try:
        # 设置语句超时（毫秒）；该步骤失败不影响主流程
        try:
            assert conn is not None
            with conn.cursor() as cur:
                # PostgreSQL需要时间单位字符串格式，不能使用参数化查询
                timeout_ms = int(settings.db.timeouts.statement_timeout_ms)
                timeout_sql = f"SET statement_timeout TO '{timeout_ms}ms'"
                cur.execute(timeout_sql)
        except (psycopg.DatabaseError, psycopg.InterfaceError) as e:
            # 记录超时设置失败，回滚事务避免后续操作失败
            logger.warning(
                "设置语句超时失败，使用默认超时设置",
                extra={
                    "event": "db.statement_timeout.set_failed",
                    "extra": {
                        "timeout_ms": int(settings.db.timeouts.statement_timeout_ms),
                        "error": str(e)
                    }
                }
            )
            # 回滚事务以清除错误状态
            try:
                if conn is not None:
                    conn.rollback()
            except Exception:
                pass  # 忽略回滚错误
        # 将连接交给调用方；若调用方 with 块内出错，异常将抛出至此并被 contextlib 正确处理
        yield conn  # type: ignore[misc]
    finally:
        # 确保关闭连接
        try:
            if conn is not None:
                conn.close()
        except (psycopg.InterfaceError, psycopg.OperationalError) as e:
            # 连接关闭失败通常不影响业务逻辑，但需要记录
            logger.debug(
                "连接关闭时发生错误",
                extra={
                    "event": "db.connection.close_failed",
                    "extra": {"error": str(e)}
                }
            )


@database_operation_logger()
def create_staging_if_not_exists(conn: psycopg.Connection) -> None:
    sql = """
    CREATE UNLOGGED TABLE IF NOT EXISTS public.staging_raw (
        station_name text,
        device_name text,
        metric_key text,
        "TagName" text,
        "DataTime" text,
        "DataValue" text,
        source_hint text,
        loaded_at timestamptz DEFAULT now()
    ) WITH (autovacuum_enabled=true);

    CREATE UNLOGGED TABLE IF NOT EXISTS public.staging_rejects (
        station_name text,
        device_name text,
        metric_key text,
        "TagName" text,
        "DataTime" text,
        "DataValue" text,
        source_hint text,
        error_msg text,
        rejected_at timestamptz DEFAULT now()
    ) WITH (autovacuum_enabled=true);
    """
    
    # 记录SQL语句
    log_sql_statement(sql, logger=logger)
    
    start_time = time.time()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            conn.commit()
        
        execution_time = (time.time() - start_time) * 1000
        log_sql_execution(
            sql_type="DDL",
            sql_summary="创建临时表 staging_raw 和 staging_rejects",
            execution_time_ms=execution_time,
            table_name="staging_raw,staging_rejects",
            logger=logger
        )
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        log_sql_execution(
            sql_type="DDL",
            sql_summary="创建临时表 staging_raw 和 staging_rejects",
            execution_time_ms=execution_time,
            table_name="staging_raw,staging_rejects",
            error=str(e),
            logger=logger
        )
        raise


@database_operation_logger()
def copy_valid_rows(conn: psycopg.Connection, rows: Iterable[ValidRow]) -> int:
    """使用 COPY 将有效行写入 staging_raw。返回行数。
    
    注意：此函数将 ValidRow 对象转换为 CSV 格式后调用 copy_valid_lines。
    对于大量数据的场景，建议直接使用 copy_valid_lines 以获得更好的性能。
    """
    
    def _rows_to_csv_lines(valid_rows: Iterable[ValidRow]) -> Iterator[str]:
        """将 ValidRow 对象转换为 CSV 行字符串。"""
        import csv
        import io
        
        for row in valid_rows:
            # 使用 StringIO 和 csv.writer 确保正确的 CSV 格式化
            output = io.StringIO()
            writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
            writer.writerow([
                row.station_name,
                row.device_name,
                row.metric_key,
                row.TagName,
                row.DataTime,
                row.DataValue,
                row.source_hint,
            ])
            yield output.getvalue()
    
    # 转换为 CSV 行并调用 copy_valid_lines
    csv_lines = _rows_to_csv_lines(rows)
    return copy_valid_lines(conn, csv_lines)


@database_operation_logger() 
def insert_rejects(conn: psycopg.Connection, rejects: Iterable[RejectRow]) -> int:
    sql = "INSERT INTO public.staging_rejects (source_hint, error_msg) VALUES (%s, %s)"
    
    reject_list = [(r.source_hint, r.error_msg) for r in rejects]
    reject_count = len(reject_list)
    
    log_sql_statement(sql, {"reject_count": reject_count}, logger)
    
    start_time = time.time()
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, reject_list)
        conn.commit()
        
        execution_time = (time.time() - start_time) * 1000
        log_sql_execution(
            sql_type="INSERT",
            sql_summary=f"插入拒绝记录 {reject_count} 条",
            execution_time_ms=execution_time,
            affected_rows=reject_count,
            table_name="staging_rejects",
            parameters={"reject_count": reject_count},
            logger=logger
        )
        return reject_count
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        log_sql_execution(
            sql_type="INSERT",
            sql_summary=f"插入拒绝记录 {reject_count} 条",
            execution_time_ms=execution_time,
            table_name="staging_rejects", 
            error=str(e),
            logger=logger
        )
        raise


@database_operation_logger()
def copy_valid_lines(conn: psycopg.Connection, lines: Iterable[str]) -> int:
    """使用 COPY 将预格式化的 CSV 行写入 staging_raw。返回行数。"""
    copy_sql = 'COPY public.staging_raw (station_name, device_name, metric_key, "TagName", "DataTime", "DataValue", source_hint) FROM STDIN WITH (FORMAT CSV)'
    
    # 记录SQL语句
    log_sql_statement(copy_sql, logger=logger)
    
    count = 0
    start_time = time.time()
    
    try:
        with conn.cursor() as cur:
            with cur.copy(copy_sql) as cp:
                for line in lines:
                    cp.write(line)
                    count += 1
        conn.commit()
        
        execution_time = (time.time() - start_time) * 1000
        log_sql_execution(
            sql_type="COPY",
            sql_summary=f"COPY 导入 {count} 行数据到 staging_raw",
            execution_time_ms=execution_time,
            affected_rows=count,
            table_name="staging_raw",
            parameters={"lines_count": count},
            logger=logger
        )
        return count
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        log_sql_execution(
            sql_type="COPY",
            sql_summary=f"COPY 导入数据到 staging_raw",
            execution_time_ms=execution_time,
            table_name="staging_raw",
            error=str(e),
            logger=logger
        )
        raise


@database_operation_logger()
def count_tz_fallback(
    conn: psycopg.Connection, start_utc: str, end_utc: str, default_station_tz: str
) -> int:
    """统计在窗口内使用 default_station_tz 兜底的行数（站点缺 tz）。"""
    sql = """
WITH parsed AS (
  SELECT
    (to_timestamp(rtrim(replace(split_part(sr."DataTime", '.', 1), 'T', ' '), 'Z'), 'YYYY-MM-DD HH24:MI:SS') AT TIME ZONE COALESCE(ds.extra->>'tz', %(default_tz)s)) AS ts_utc,
    ds.extra->>'tz' AS tz
  FROM public.staging_raw sr
  JOIN public.dim_stations ds ON ds.name = sr.station_name
)
SELECT count(*)
FROM parsed
WHERE tz IS NULL AND date_trunc('second', ts_utc) >= %(start)s AND date_trunc('second', ts_utc) < %(end)s;
"""
    
    params = {"start": start_utc, "end": end_utc, "default_tz": default_station_tz}
    
    # 记录SQL语句
    log_sql_statement(sql, params, logger)
    
    start_time = time.time()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            result = int(row[0]) if row else 0
        
        execution_time = (time.time() - start_time) * 1000
        log_sql_execution(
            sql_type="SELECT",
            sql_summary=f"统计时区兜底行数，窗口: {start_utc} ~ {end_utc}",
            execution_time_ms=execution_time,
            table_name="staging_raw,dim_stations",
            parameters=params,
            logger=logger
        )
        return result
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        log_sql_execution(
            sql_type="SELECT",
            sql_summary=f"统计时区兜底行数，窗口: {start_utc} ~ {end_utc}",
            execution_time_ms=execution_time,
            table_name="staging_raw,dim_stations",
            error=str(e),
            logger=logger
        )
        raise


def _floor_monday_utc(dt: datetime) -> datetime:
    # 确保为 UTC 的 aware datetime
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    # 计算当周周一 00:00:00 UTC
    days = (dt.weekday() + 7 - 0) % 7  # 周一=0
    base = datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc) - timedelta(
        days=days
    )
    return base.replace(hour=0, minute=0, second=0, microsecond=0)


def _ensure_fact_weekly_partitions(
    conn: psycopg.Connection, start_dt: datetime, end_dt: datetime
) -> None:
    start_w = _floor_monday_utc(start_dt)
    end_w = _floor_monday_utc(end_dt)
    cur_dt = start_w
    try:
        with conn.cursor() as cur:
            while cur_dt <= end_w:
                nxt = cur_dt + timedelta(days=7)
                part_name = f"fact_measurements_{cur_dt.strftime('%Yw%V')}"
                cur.execute("SELECT to_regclass(%s)", (f"public.{part_name}",))
                result = cur.fetchone()
                exists = result is not None and result[0] is not None
                if not exists:
                    # 创建周分区，并在其上建立二级 HASH 子分区（按 station_id, modulus=16）
                    start_lit = cur_dt.strftime("%Y-%m-%d %H:%M:%S+00")
                    end_lit = nxt.strftime("%Y-%m-%d %H:%M:%S+00")
                    # 使用字符串模板，但作为单个查询执行
                    create_partition_sql = f"""
                        CREATE TABLE public.{part_name}
                        PARTITION OF public.fact_measurements
                        FOR VALUES FROM ('{start_lit}') TO ('{end_lit}')
                        PARTITION BY HASH (station_id);
                        """
                    cur.execute(create_partition_sql)  # type: ignore[arg-type]

                    for i in range(16):
                        sub_name = f"{part_name}_p{i}"
                        cur.execute("SELECT to_regclass(%s)", (f"public.{sub_name}",))
                        result = cur.fetchone()
                        sub_exists = result is not None and result[0] is not None
                        if not sub_exists:
                            create_sub_sql = f"""
                                CREATE TABLE public.{sub_name}
                                PARTITION OF public.{part_name}
                                FOR VALUES WITH (modulus 16, remainder {i});
                                """
                            cur.execute(create_sub_sql)  # type: ignore[arg-type]
                            
                            create_index_sql = f"""
                                CREATE INDEX IF NOT EXISTS idx_{sub_name}_sdm_tb
                                ON public.{sub_name}(station_id, device_id, metric_id, ts_bucket) INCLUDE (value);
                                """
                            cur.execute(create_index_sql)  # type: ignore[arg-type]
                else:
                    # 已存在周分区：尽力补全子分区与索引（若周分区并非 HASH 分区将抛错，忽略）
                    try:
                        cur.execute(
                            "SELECT relname FROM pg_class WHERE relname = %s",
                            (part_name,),
                        )
                        for i in range(16):
                            sub_name = f"{part_name}_p{i}"
                            cur.execute(
                                "SELECT to_regclass(%s)", (f"public.{sub_name}",)
                            )
                            result = cur.fetchone()
                            sub_exists = result is not None and result[0] is not None
                            if not sub_exists:
                                create_sub_sql = f"""
                                    CREATE TABLE public.{sub_name}
                                    PARTITION OF public.{part_name}
                                    FOR VALUES WITH (modulus 16, remainder {i});
                                    """
                                cur.execute(create_sub_sql)  # type: ignore[arg-type]
                                
                                create_index_sql = f"""
                                    CREATE INDEX IF NOT EXISTS idx_{sub_name}_sdm_tb
                                    ON public.{sub_name}(station_id, device_id, metric_id, ts_bucket) INCLUDE (value);
                                    """
                                cur.execute(create_index_sql)  # type: ignore[arg-type]
                    except Exception:
                        pass
                cur_dt = nxt
        conn.commit()
    except Exception:
        # 避免将连接置于 aborted 状态，确保后续 MERGE 可继续
        conn.rollback()
        raise


@create_sql_logger("合并数据窗口")
def run_merge_window(
    conn: psycopg.Connection, start_utc, end_utc, default_station_tz: str
) -> dict:
    """执行集合式合并窗口（SQL骨架），记录 SQL 摘要日志并返回统计。

    返回字段：
    - affected_rows: int
    - rows_in: int（窗口内 parsed 行数）
    - rows_deduped: int（去重被丢弃的行数）
    - rows_merged: int（写入/更新到 fact 的最终行数）
    - dedup_ratio: float = rows_deduped / max(1, rows_in)
    - sql_cost_ms: int
    """
    sql_logger = logging.getLogger("sql")
    sql = """
WITH parsed AS (
  SELECT
    ds.id AS station_id,
    dd.id AS device_id,
    dmc.id AS metric_id,
    -- 站点 tz 优先，缺失用默认 tz
    (to_timestamp(rtrim(replace(split_part(sr."DataTime", '.', 1), 'T', ' '), 'Z'), 'YYYY-MM-DD HH24:MI:SS') AT TIME ZONE COALESCE(ds.extra->>'tz', %(default_tz)s)) AS ts_utc,
    sr."DataValue"::numeric AS val,
    sr.source_hint
  FROM public.staging_raw sr
  JOIN public.dim_stations ds ON ds.name = sr.station_name
  JOIN public.dim_devices dd ON dd.station_id = ds.id AND dd.name = sr.device_name
  JOIN public.dim_metric_config dmc ON dmc.metric_key = sr.metric_key
), dedup AS (

	-- 统计窗口内 parsed 行数与去重丢弃数
	, stats AS (
	  SELECT
	    count(*) FILTER (WHERE rn = 1 AND date_trunc('second', ts_utc) >= %(start)s AND date_trunc('second', ts_utc) < %(end)s) AS rows_merged,
	    count(*) FILTER (WHERE rn > 1 AND date_trunc('second', ts_utc) >= %(start)s AND date_trunc('second', ts_utc) < %(end)s) AS rows_deduped,
	    count(*) FILTER (WHERE date_trunc('second', ts_utc) >= %(start)s AND date_trunc('second', ts_utc) < %(end)s) AS rows_in
	  FROM dedup
	)

  SELECT *, date_trunc('second', ts_utc) AS ts_bucket,
         row_number() OVER (PARTITION BY station_id, device_id, metric_id, date_trunc('second', ts_utc) ORDER BY ts_utc DESC) AS rn
  FROM parsed
)
INSERT INTO public.fact_measurements(station_id, device_id, metric_id, ts_raw, ts_bucket, value, source_hint)
SELECT station_id, device_id, metric_id, ts_utc, ts_bucket, val, source_hint
FROM dedup
WHERE rn = 1 AND ts_bucket >= %(start)s AND ts_bucket < %(end)s
ON CONFLICT (station_id, device_id, metric_id, ts_bucket)
DO UPDATE SET value = EXCLUDED.value, source_hint = EXCLUDED.source_hint, ts_raw = EXCLUDED.ts_raw;
"""
    # 修正 SQL：上方初始字符串含无效 CTE 片段（stats 引用自身 dedup），此处覆盖为有效版本
    sql = """
WITH parsed AS (
  SELECT
    ds.id AS station_id,
    dd.id AS device_id,
    dmc.id AS metric_id,
    -- 站点 tz 优先，缺失用默认 tz
    (to_timestamp(rtrim(replace(split_part(sr."DataTime", '.', 1), 'T', ' '), 'Z'), 'YYYY-MM-DD HH24:MI:SS') AT TIME ZONE COALESCE(ds.extra->>'tz', %(default_tz)s)) AS ts_utc,
    sr."DataValue"::numeric AS val,
    sr.source_hint
  FROM public.staging_raw sr
  JOIN public.dim_stations ds ON ds.name = sr.station_name
  JOIN public.dim_devices dd ON dd.station_id = ds.id AND dd.name = sr.device_name
  JOIN public.dim_metric_config dmc ON dmc.metric_key = sr.metric_key
), dedup AS (
  SELECT *,
         date_trunc('second', ts_utc) AS ts_bucket,
         row_number() OVER (
           PARTITION BY station_id, device_id, metric_id, date_trunc('second', ts_utc)
           ORDER BY ts_utc DESC
         ) AS rn
  FROM parsed
)
INSERT INTO public.fact_measurements(station_id, device_id, metric_id, ts_raw, ts_bucket, value, source_hint)
SELECT station_id, device_id, metric_id, ts_utc, ts_bucket, val, source_hint
FROM dedup
WHERE rn = 1 AND ts_bucket >= %(start)s AND ts_bucket < %(end)s
ON CONFLICT (station_id, device_id, metric_id, ts_bucket)
DO UPDATE SET value = EXCLUDED.value, source_hint = EXCLUDED.source_hint, ts_raw = EXCLUDED.ts_raw;
"""

    params = {
        "start": start_utc,
        "end": end_utc,
        "default_tz": default_station_tz,
    }
    
    # 记录完整的SQL语句（DEBUG级别）
    log_sql_statement(sql, params, sql_logger)
    
    # 合并前确保目标时间窗所需的周分区已存在
    try:
        _ensure_fact_weekly_partitions(conn, start_utc, end_utc)
    except Exception:
        pass

    sql_logger.info(
        "merge started",
        extra={
            "event": "db.exec.started",
            "extra": {
                "target_table": "public.fact_measurements",
                "sql_op": "MERGE",
                "window_start": start_utc,
                "window_end": end_utc,
                "window_size_seconds": None,
                "iso_week_utc": None,
            },
        },
    )
    t0 = time.perf_counter()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            affected = cur.rowcount
        conn.commit()
        cost_ms = int((time.perf_counter() - t0) * 1000)
        
        # 使用增强的日志记录
        log_sql_execution(
            sql_type="MERGE",
            sql_summary=f"合并数据到 fact_measurements, 窗口: {start_utc} ~ {end_utc}",
            execution_time_ms=cost_ms,
            affected_rows=affected,
            table_name="fact_measurements",
            parameters={
                "window_start": str(start_utc),
                "window_end": str(end_utc),
                "default_tz": default_station_tz
            },
            logger=sql_logger
        )
        
        # 保留原有的日志记录以保持兼容性
        sql_logger.info(
            "merge succeeded",
            extra={
                "event": "db.exec.succeeded",
                "extra": {
                    "target_table": "public.fact_measurements",
                    "sql_op": "MERGE",
                    "affected_rows": affected,
                    "sql_cost_ms": cost_ms,
                    "window_start": start_utc,
                    "window_end": end_utc,
                },
            },
        )
        # 使用与 MERGE 相同的 parsed/dedup 逻辑统计窗口行数与去重情况
        stats_sql = """
WITH parsed AS (
  SELECT
    ds.id AS station_id,
    dd.id AS device_id,
    dmc.id AS metric_id,
    (to_timestamp(rtrim(replace(split_part(sr."DataTime", '.', 1), 'T', ' '), 'Z'), 'YYYY-MM-DD HH24:MI:SS') AT TIME ZONE COALESCE(ds.extra->>'tz', %(default_tz)s)) AS ts_utc
  FROM public.staging_raw sr
  JOIN public.dim_stations ds ON ds.name = sr.station_name
  JOIN public.dim_devices dd ON dd.station_id = ds.id AND dd.name = sr.device_name
  JOIN public.dim_metric_config dmc ON dmc.metric_key = sr.metric_key
), dedup AS (
  SELECT *, date_trunc('second', ts_utc) AS ts_bucket,
         row_number() OVER (PARTITION BY station_id, device_id, metric_id, date_trunc('second', ts_utc) ORDER BY ts_utc DESC) AS rn
  FROM parsed
)
SELECT
  count(*) FILTER (WHERE rn = 1 AND date_trunc('second', ts_utc) >= %(start)s AND date_trunc('second', ts_utc) < %(end)s) AS rows_merged,
  count(*) FILTER (WHERE rn > 1 AND date_trunc('second', ts_utc) >= %(start)s AND date_trunc('second', ts_utc) < %(end)s) AS rows_deduped,
  count(*) FILTER (WHERE date_trunc('second', ts_utc) >= %(start)s AND date_trunc('second', ts_utc) < %(end)s) AS rows_in
FROM dedup;
"""
        # 记录统计查询SQL语句
        log_sql_statement(stats_sql, params, sql_logger)
        
        with conn.cursor() as cur:
            cur.execute(stats_sql, params)
            srow = cur.fetchone()
        rows_merged = int(srow[0]) if srow else 0
        rows_deduped = int(srow[1]) if srow else 0
        rows_in = int(srow[2]) if srow else 0
        dedup_ratio = (rows_deduped / rows_in) if rows_in else 0.0
        return {
            "affected_rows": int(affected),
            "rows_in": rows_in,
            "rows_deduped": rows_deduped,
            "rows_merged": rows_merged,
            "dedup_ratio": dedup_ratio,
            "sql_cost_ms": int(cost_ms),
        }
    except Exception as e:
        conn.rollback()
        cost_ms = int((time.perf_counter() - t0) * 1000)
        
        # 使用增强的错误日志记录
        log_sql_execution(
            sql_type="MERGE",
            sql_summary=f"合并数据到 fact_measurements, 窗口: {start_utc} ~ {end_utc}",
            execution_time_ms=cost_ms,
            table_name="fact_measurements",
            parameters={
                "window_start": str(start_utc),
                "window_end": str(end_utc),
                "default_tz": default_station_tz
            },
            error=str(e),
            logger=sql_logger
        )
        
        payload = {
            "target_table": "public.fact_measurements",
            "sql_op": "MERGE",
            "sql_cost_ms": cost_ms,
            "error": str(e),
        }
        # on_error: 追加 EXPLAIN 计划（文本摘要）
        try:
            with conn.cursor() as cur:
                cur.execute("EXPLAIN " + sql, params)
                plan_rows = cur.fetchall()
                plan = "\n".join(r[0] for r in plan_rows)
                payload["explain"] = plan[:2000]
        except Exception:
            pass
        sql_logger.error(
            "merge failed", extra={"event": "db.exec.failed", "extra": payload}
        )
        raise
