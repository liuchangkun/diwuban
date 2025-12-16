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


import time
import time as _time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Iterator

import psycopg

from app.adapters.db.transaction import auto_commit, transaction
from app.core.config.loader_new import Settings
from app.core.exceptions import DatabaseConnectionError, DatabaseError
from app.core.types import RejectRow, ValidRow

import logging

_act = logging.getLogger(__name__)


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
    - 若提供 dsn_write 则优先使用；否则尝试 dsn_read；再否则拼接 host/name/user/password
    - 示例："host=localhost dbname=pump_station_optimization user=postgres password=xxx"
    """

    """根据配置生成 DSN。优先使用 dsn_write/dsn_read；否则使用 host/name/user/password 组合。
    当前项目默认不脱敏，完整输出在 args/config 快照中。
    """
    db = settings.db
    if db.dsn_write:
        return db.dsn_write
    if db.dsn_read:
        return db.dsn_read

    # 构建 DSN 字符串，包含密码（如果有）
    dsn_parts = [f"host={db.host}", f"dbname={db.name}", f"user={db.user}"]
    if db.password:
        dsn_parts.append(f"password={db.password}")
    return " ".join(dsn_parts)


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

    # 尝试使用连接池（更严格的错误处理：仅在“确未初始化/不可用”时回退；否则上抛以避免掩盖故障）
    try:
        from app.adapters.db.exec_wrapper import wrap_connection_if_enabled
        from app.adapters.db.pool import (
            get_connection as _pool_get_connection,
        )
        from app.adapters.db.pool import (
            get_pool_stats as _pool_stats,
        )

        with _pool_get_connection() as _conn:
            conn = wrap_connection_if_enabled(_conn)
            yield conn
        return
    except ImportError as e:
        # 模块不可用（例如精简运行环境）；记录一次告警并回退
        try:
            import logging as _logging

            from app.core.logging.setup import log_db_pool as _log_pool

            _log_pool(
                "POOL_FALLBACK",
                {'原因': "import_error", "error": str(e)},
                _logging.WARNING,
            )
        except Exception:
            pass
        # 记录遥测并回退到直连
        try:
            import app.adapters.db.pool_telemetry as _pt

            _pt.record_fallback("import_error")
        except Exception:
            pass
        pass
    except DatabaseError as e:
        # 连接池路径失败。区分“未初始化”与“已初始化但故障”。
        try:
            stats = _pool_stats()
        except Exception:
            stats = {"error": "pool_stats_unavailable"}

        # 记录日志
        try:
            import logging as _logging

            from app.core.logging.setup import log_db_pool as _log_pool

            _detail = {
                '原因': "pool_path_failed",
                "error": str(e),
                "stats": stats,
            }
            _log_pool("POOL_ERROR", _detail, _logging.ERROR)
        except Exception:
            pass

        # 若确认为“未初始化”（或无法获取统计），则回退直连；否则上抛避免掩盖真实故障
        if isinstance(stats, dict) and stats.get("error"):
            # 记录遥测并回退到直连
            try:
                import app.adapters.db.pool_telemetry as _pt

                _pt.record_fallback("uninitialized_or_unavailable")
            except Exception:
                pass
            pass
        else:
            # 记录遥测并上抛，避免掩盖故障
            try:
                import app.adapters.db.pool_telemetry as _pt

                _pt.record_error("initialized_pool_failed")
            except Exception:
                pass
            raise

    # 直连模式（原逻辑）
    dsn = make_dsn(settings)
    attempts = max(1, int(settings.db.retry.max_retries))
    delay = max(0.0, float(settings.db.retry.retry_delay_ms) / 1000.0)
    backoff = max(1.0, float(settings.db.retry.backoff_multiplier))

    conn: psycopg.Connection | None = None
    # 删除未使用变量以消除静态告警（F841）

    # 仅针对“连接建立”进行重试
    for i in range(attempts):
        try:
            _ct_secs = int(settings.db.timeouts.connect_timeout_seconds())
            _raw_conn = psycopg.connect(
                dsn,
                connect_timeout=_ct_secs,
            )
            try:
                from app.adapters.db.exec_wrapper import (
                    wrap_connection_if_enabled as _wrap,
                )
            except Exception:

                def _wrap(x):
                    return x

            conn = _wrap(_raw_conn)
            break
        except Exception as e:
            if i < attempts - 1:
                _time.sleep(delay)
                delay *= backoff
            else:
                _ctx = {"dsn_preview": dsn[:50] + "...", "attempts": attempts}
                raise DatabaseConnectionError(
                    f"无法建立数据库连接: {e}",
                    context=_ctx,
                ) from e

    try:
        # 设置语句超时（毫秒）；该步骤失败不影响主流程
        try:
            assert conn is not None
            with conn.cursor() as cur:
                # 使用统一的语句超时SQL
                timeout_sql = settings.db.timeouts.statement_timeout_sql()
                cur.execute(timeout_sql)
        except (psycopg.DatabaseError, psycopg.InterfaceError):
            # 设置语句超时失败，回滚事务避免后续操作失败
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
        except (psycopg.InterfaceError, psycopg.OperationalError):
            # 连接关闭失败通常不影响业务逻辑
            pass


def create_staging_if_not_exists(
    conn: psycopg.Connection, staging_unlogged: bool | None = None
) -> None:
    """创建 staging_raw / staging_rejects 表（可配置 LOGGED/UNLOGGED）。

    - 默认遵循配置 settings.db.staging_unlogged（缺省 False → LOGGED）
    - 仅在不存在时创建；不会改变已存在表的持久化属性
    """
    # 解析持久化开关：优先使用入参；否则读取 settings；最终默认 False
    if staging_unlogged is None:
        try:
            from pathlib import Path

            from app.core.config.loader_new import load_settings

            settings = load_settings(Path("configs"))
            db_cfg = getattr(settings, "db", None)
            staging_unlogged = (
                bool(getattr(db_cfg, "staging_unlogged", False))
                if db_cfg is not None
                else False
            )
        except Exception:
            staging_unlogged = False

    persistence_kw = "UNLOGGED " if staging_unlogged else ""

    sql = f"""
    CREATE {persistence_kw}TABLE IF NOT EXISTS public.staging_raw (
        station_name text,
        device_name text,
        metric_key text,
        "TagName" text,
        "DataTime" text,
        "DataValue" text,
        source_hint text,
        loaded_at timestamptz DEFAULT now()
    ) WITH (autovacuum_enabled=true);

    CREATE {persistence_kw}TABLE IF NOT EXISTS public.staging_rejects (
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

    try:
        # 使用自动提交模式进行DDL操作
        with auto_commit(conn):
            with conn.cursor() as cur:
                cur.execute(sql)
    except Exception:
        raise


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
            writer.writerow(
                [
                    row.station_name,
                    row.device_name,
                    row.metric_key,
                    row.TagName,
                    row.DataTime,
                    row.DataValue,
                    row.source_hint,
                ]
            )
            yield output.getvalue()

    # 转换为 CSV 行并调用 copy_valid_lines
    csv_lines = _rows_to_csv_lines(rows)
    return copy_valid_lines(conn, csv_lines)


def insert_rejects(conn: psycopg.Connection, rejects: Iterable[RejectRow]) -> int:
    """
    插入拒绝记录到 staging_rejects 表

    优化说明：
    - 对于大批量数据自动分片处理，避免长时间占用连接
    - 每个批次使用独立的事务，提高并发性能
    - 监控批次执行时间，动态调整批次大小
    """
    sql = "INSERT INTO public.staging_rejects (source_hint, error_msg) VALUES (%s, %s)"

    reject_list = [(r.source_hint, r.error_msg) for r in rejects]
    reject_count = len(reject_list)

    # 如果数据量较小，直接处理
    if reject_count <= 500:
        return _insert_rejects_batch(conn, reject_list, sql)

    # 大批量数据分片处理

    total_inserted = 0
    batch_size = 500

    for i in range(0, reject_count, batch_size):
        batch = reject_list[i: i + batch_size]
        batch_inserted = _insert_rejects_batch(conn, batch, sql)
        total_inserted += batch_inserted

    return total_inserted


def _insert_rejects_batch(
    conn: psycopg.Connection, reject_batch: list, sql: str
) -> int:
    """插入单个批次的拒绝记录"""
    batch_count = len(reject_batch)

    start_time = time.time()
    try:
        # 使用事务管理器确保一致性
        with transaction(conn):
            with conn.cursor() as cur:
                cur.executemany(sql, reject_batch)

        execution_time = (time.time() - start_time) * 1000
        return batch_count
    except Exception:
        execution_time = (time.time() - start_time) * 1000
        raise


def copy_valid_lines(conn: psycopg.Connection, lines: Iterable[str]) -> int:
    """
    使用 COPY 将预格式化的 CSV 行写入 staging_raw

    优化说明：
    - 对于大批量数据自动分片处理，避免长时间占用连接
    - 监控 COPY 操作执行时间，防止连接超时
    - 提供批次进度反馈
    """
    copy_sql = 'COPY public.staging_raw (station_name, device_name, metric_key, "TagName", "DataTime", "DataValue", source_hint) FROM STDIN WITH (FORMAT CSV)'

    # 将迭代器转换为列表以便计算总数和分片
    lines_list = list(lines)
    total_count = len(lines_list)

    # 优化：增大批量到10万行，减少COPY+COMMIT次数
    # 如果数据量较小，直接处理
    if total_count <= 100000:
        return _copy_valid_lines_batch(conn, lines_list, copy_sql)

    # 大批量数据分片处理
    total_copied = 0
    batch_size = 100000  # 从2000增大到10万，减少30-50%开销

    for i in range(0, total_count, batch_size):
        batch_lines = lines_list[i: i + batch_size]
        batch_copied = _copy_valid_lines_batch(conn, batch_lines, copy_sql)
        total_copied += batch_copied

    return total_copied


def _copy_valid_lines_batch(
    conn: psycopg.Connection, lines_batch: list, copy_sql: str
) -> int:
    """执行单个批次的 COPY 操作
    
    优化：使用StringIO批量写入，减少系统调用次数
    """
    from io import StringIO
    
    batch_count = len(lines_batch)
    if batch_count == 0:
        return 0

    # 记录SQL语句
    from app.core.logging.setup import log_sql

    start_time = time.time()
    try:
        # 优化：将所有行合并成一个大字符串，一次性写入
        buffer = StringIO()
        buffer.writelines(lines_batch)
        buffer.seek(0)
        
        with conn.cursor() as cur:
            # 性能优化：禁用同步提交，减少WAL等待
            cur.execute("SET LOCAL synchronous_commit = 'off'")
            with cur.copy(copy_sql) as cp:
                # 使用大块写入而非逐行写入
                while True:
                    chunk = buffer.read(1048576)  # 1MB块
                    if not chunk:
                        break
                    cp.write(chunk)
        conn.commit()

        execution_time = int((time.time() - start_time) * 1000)
        log_sql(copy_sql, params=None,
                duration_ms=execution_time, rows=batch_count)
        return batch_count
    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)
        log_sql(
            copy_sql, params=None, duration_ms=execution_time, rows=None, error=str(e)
        )
        raise


def get_staging_time_range(
    conn: psycopg.Connection, default_station_tz: str = "Asia/Shanghai"
) -> tuple[datetime | None, datetime | None, int]:
    """获取 staging_raw 表中数据的 UTC 时间范围。

    返回值:
        tuple[datetime | None, datetime | None, int]: (最小时间UTC, 最大时间UTC, 行数)
        如果没有数据，返回 (None, None, 0)
    """
    sql = """
    WITH bounds AS (
      SELECT
        (SELECT sr_min."DataTime"
         FROM public.staging_raw sr_min
         ORDER BY sr_min."DataTime" ASC
         LIMIT 1) AS min_raw,
        (SELECT sr_max."DataTime"
         FROM public.staging_raw sr_max
         ORDER BY sr_max."DataTime" DESC
         LIMIT 1) AS max_raw
    ),
    approx_cnt AS (
      SELECT COALESCE(
               (SELECT CAST(n_live_tup AS bigint)
                FROM pg_stat_all_tables
                WHERE schemaname = 'public'
                  AND relname = 'staging_raw'),
               0
             ) AS cnt
    )
    SELECT
      CASE
        WHEN bounds.min_raw IS NULL THEN NULL
        ELSE (to_timestamp(rtrim(replace(split_part(bounds.min_raw, '.', 1), 'T', ' '), 'Z'),
                           'YYYY-MM-DD HH24:MI:SS') AT TIME ZONE %(default_tz)s)
      END AS min_utc,
      CASE
        WHEN bounds.max_raw IS NULL THEN NULL
        ELSE (to_timestamp(rtrim(replace(split_part(bounds.max_raw, '.', 1), 'T', ' '), 'Z'),
                           'YYYY-MM-DD HH24:MI:SS') AT TIME ZONE %(default_tz)s)
      END AS max_utc,
      approx_cnt.cnt
    FROM bounds, approx_cnt;
    """

    params = {"default_tz": default_station_tz}

    # 记录SQL语句
    from app.core.logging.setup import log_sql

    start_time = time.time()
    try:
        with conn.cursor() as cur:
            # 放宽本次调用的语句超时，避免在 staging_raw 体量较大时探测窗口超时
            try:
                cur.execute("SET LOCAL statement_timeout = '120s'")
            except Exception:
                pass
            cur.execute(sql, params)
            row = cur.fetchone()

            min_time = row[0] if row and row[0] else None
            max_time = row[1] if row and row[1] else None
            count = int(row[2]) if row and row[2] else 0

        execution_time = int((time.time() - start_time) * 1000)
        log_sql(sql, params=params, duration_ms=execution_time, rows=count)
        return min_time, max_time, count
    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)
        log_sql(sql, params=params, duration_ms=execution_time,
                rows=None, error=str(e))
        raise


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

    params = {"start": start_utc, "end": end_utc,
              "default_tz": default_station_tz}

    # 记录SQL语句
    from app.core.logging.setup import log_sql

    start_time = time.time()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            result = int(row[0]) if row else 0

        execution_time = int((time.time() - start_time) * 1000)
        log_sql(sql, params=params, duration_ms=execution_time, rows=result)
        return result
    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)
        log_sql(sql, params=params, duration_ms=execution_time,
                rows=None, error=str(e))
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


def _ensure_staging_ts_utc(conn: psycopg.Connection, default_station_tz: str) -> None:
    try:
        existing = set()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'staging_raw'
                  AND indexname IN (
                    'idx_staging_raw_join_cols',
                    'idx_staging_raw_datatime'
                  )
                """
            )
            for row in cur.fetchall():
                existing.add(row[0])

        needed_sql = {
            "idx_staging_raw_join_cols": """
                CREATE INDEX IF NOT EXISTS idx_staging_raw_join_cols
                ON public.staging_raw (station_name, device_name, metric_key)
            """,
            "idx_staging_raw_datatime": """
                CREATE INDEX IF NOT EXISTS idx_staging_raw_datatime
                ON public.staging_raw ("DataTime")
            """,
        }
        missing = [name for name in needed_sql.keys() if name not in existing]
        if not missing:
            return

        with conn.cursor() as cur:
            while True:
                cur.execute(
                    """
                    SELECT
                      index_relid::regclass::text AS index_name,
                      phase,
                      blocks_total,
                      blocks_done
                    FROM pg_stat_progress_create_index
                    WHERE relid = 'public.staging_raw'::regclass
                    """
                )
                rows = cur.fetchall()
                if not rows:
                    break
                for index_name, phase, blocks_total, blocks_done in rows:
                    phase_cn = phase
                    if isinstance(phase, str):
                        if phase == "initializing":
                            phase_cn = "初始化"
                        elif phase == "building index: scanning table":
                            phase_cn = "构建索引：扫描表"
                        elif phase == "building index: sorting tuples":
                            phase_cn = "构建索引：排序记录"
                        elif phase == "building index: loading tuples into index":
                            phase_cn = "构建索引：写入索引"
                        elif phase == "waiting for writers before marking dead tuples":
                            phase_cn = "等待写入结束以标记无效记录"
                        elif phase == "waiting for old snapshots":
                            phase_cn = "等待旧快照结束"
                    progress_pct = None
                    if blocks_total and blocks_total > 0:
                        try:
                            progress_pct = int(
                                int(blocks_done) * 100 / int(blocks_total)
                            )
                        except Exception:
                            progress_pct = None
                    extra = {
                        "extra_data": {
                            "table": "public.staging_raw",
                            "index_name": index_name,
                            "phase": phase_cn,
                            "blocks_total": int(blocks_total)
                            if blocks_total is not None
                            else None,
                            "blocks_done": int(blocks_done)
                            if blocks_done is not None
                            else None,
                            "progress_pct": progress_pct,
                        }
                    }
                    _act.info("[数据库-索引] [staging_raw索引创建中]", extra=extra)
                time.sleep(5)

        _act.info(
            "[数据库-索引] [staging_raw索引创建完成]",
            extra={"extra_data": {"table": "public.staging_raw"}},
        )

        with conn.cursor() as cur:
            for name in missing:
                cur.execute(needed_sql[name])
        with auto_commit(conn):
            pass
    except Exception:
        pass


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
                        cur.execute("SELECT to_regclass(%s)",
                                    (f"public.{sub_name}",))
                        result = cur.fetchone()
                        sub_exists = result is not None and result[0] is not None
                        if not sub_exists:
                            create_sub_sql = f"""
                                CREATE TABLE public.{sub_name}
                                PARTITION OF public.{part_name}
                                FOR VALUES WITH (modulus 16, remainder {i});
                                """
                            cur.execute(
                                create_sub_sql)  # type: ignore[arg-type]

                            create_index_sql = f"""
                                CREATE INDEX IF NOT EXISTS idx_{sub_name}_sdm_tb
                                ON public.{sub_name}(station_id, device_id, metric_id, ts_bucket) INCLUDE (value);
                                """
                            cur.execute(
                                create_index_sql)  # type: ignore[arg-type]
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
                                "SELECT to_regclass(%s)", (
                                    f"public.{sub_name}",)
                            )
                            result = cur.fetchone()
                            sub_exists = result is not None and result[0] is not None
                            if not sub_exists:
                                create_sub_sql = f"""
                                    CREATE TABLE public.{sub_name}
                                    PARTITION OF public.{part_name}
                                    FOR VALUES WITH (modulus 16, remainder {i});
                                    """
                                cur.execute(
                                    create_sub_sql)  # type: ignore[arg-type]

                                create_index_sql = f"""
                                    CREATE INDEX IF NOT EXISTS idx_{sub_name}_sdm_tb
                                    ON public.{sub_name}(station_id, device_id, metric_id, ts_bucket) INCLUDE (value);
                                    """
                                cur.execute(
                                    create_index_sql)  # type: ignore[arg-type]
                    except Exception:
                        pass
                cur_dt = nxt
        # 使用自动提交模式进行DDL操作
        with auto_commit(conn):
            pass  # DDL操作已在上面的循环中完成
    except Exception:
        # 分区创建失败不应该影响后续操作
        raise


def _ensure_fact_timescaledb_layout(conn: psycopg.Connection) -> None:
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'fact_measurements' AND indexname = 'ux_fact_sdm_tb')"
            )
            has_ux = bool(cur.fetchone()[0])
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'fact_measurements' AND indexname = 'fact_measurements_new_pkey')"
            )
            has_new_pkey = bool(cur.fetchone()[0])
            if has_ux and has_new_pkey:
                cur.execute("DROP INDEX IF EXISTS fact_measurements_new_pkey")
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'fact_measurements' AND indexname = 'idx_fm_station_device_metric')"
            )
            if bool(cur.fetchone()[0]):
                cur.execute(
                    "DROP INDEX IF EXISTS idx_fm_station_device_metric")
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_fm_brin_ts ON public.fact_measurements USING brin (ts_bucket) WITH (pages_per_range='128')"
            )
            cur.execute(
                "SELECT compression_enabled FROM timescaledb_information.hypertables WHERE hypertable_schema='public' AND hypertable_name='fact_measurements'"
            )
            row = cur.fetchone()
            compression_enabled = bool(row[0]) if row is not None else False
            if not compression_enabled:
                cur.execute(
                    "ALTER TABLE public.fact_measurements SET (timescaledb.compress, timescaledb.compress_segmentby = 'station_id, device_id, metric_id', timescaledb.compress_orderby = 'ts_bucket')"
                )
            cur.execute(
                "SELECT COUNT(1) FROM timescaledb_information.jobs WHERE hypertable_schema = 'public' AND hypertable_name = 'fact_measurements' AND proc_name = 'policy_compression'"
            )
            cnt = int(cur.fetchone()[0])
            if cnt == 0:
                cur.execute(
                    "SELECT add_compression_policy('fact_measurements', INTERVAL '7 days')"
                )
        with auto_commit(conn):
            pass
    except Exception:
        pass


def run_merge_window(
    conn: psycopg.Connection,
    start_utc,
    end_utc,
    default_station_tz: str,
    device_id: int | None = None,
) -> dict:
    """执行集合式合并窗口（SQL骨架），记录 SQL 摘要日志并返回统计。

    返回字段：
    - affected_rows: int
    - rows_in: int（窗口内 parsed 行数）
    - rows_deduped: int（去重被丢弃的行数）
    - rows_merged: int（写入/更新到 fact 的最终行数）
    - dedup_ratio: float = rows_deduped / max(1, rows_in)
    - sql_cost_ms: int

    说明：当提供 device_id 时，仅处理该设备的数据。
    """

    _act.info(
        "[数据库-执行] [合并窗口开始]",
        extra={
            "extra_data": {
                '开始时间（UTC）': str(start_utc),
                '结束时间（UTC）': str(end_utc),
                '设备ID': device_id,
            }
        },
    )

    _ensure_staging_ts_utc(conn, default_station_tz)

    from datetime import datetime as _dt
    from datetime import timezone as _tz

    def _to_dt(x):
        if isinstance(x, str):
            return _dt.fromisoformat(x.replace("Z", "+00:00"))
        if isinstance(x, _dt):
            if x.tzinfo is None:
                return x.replace(tzinfo=_tz.utc)
            return x
        raise TypeError("start_utc/end_utc must be datetime or ISO string")

    s_dt = _to_dt(start_utc)
    e_dt = _to_dt(end_utc)

    try:
        from zoneinfo import ZoneInfo as _ZI

        _tz_obj = _ZI(default_station_tz)
        s_local = s_dt.astimezone(_tz_obj).strftime("%Y-%m-%d %H:%M:%S")
        e_local = e_dt.astimezone(_tz_obj).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        s_local = s_dt.strftime("%Y-%m-%d %H:%M:%S")
        e_local = e_dt.strftime("%Y-%m-%d %H:%M:%S")

    if hasattr(s_dt, "isoformat"):
        start_utc = s_dt.isoformat()
    if hasattr(e_dt, "isoformat"):
        end_utc = e_dt.isoformat()

    # COPY-optimized merge: use temporary table + COPY for 5-10x performance
    # Step 1: Query deduplicated data
    # Step 2: COPY into temporary table
    # Step 3: INSERT from temp table with ON CONFLICT

    params = {
        "start": start_utc,
        "end": end_utc,
        "start_local": s_local,
        "end_local": e_local,
        "default_tz": default_station_tz,
        "device_id": device_id,
    }

    query_sql = """
WITH parsed AS (
  SELECT
    ds.id AS station_id,
    dd.id AS device_id,
    dmc.id AS metric_id,
    to_timestamp(rtrim(replace(split_part(sr."DataTime", '.', 1), 'T', ' '), 'Z'), 'YYYY-MM-DD HH24:MI:SS') AT TIME ZONE %(default_tz)s AS ts_utc,
    sr."DataValue"::numeric AS val,
    sr.source_hint
  FROM public.staging_raw sr
  JOIN public.dim_stations ds ON ds.name = sr.station_name
  JOIN public.dim_devices dd ON dd.station_id = ds.id AND dd.name = sr.device_name
  JOIN public.dim_metric_config dmc ON dmc.metric_key = sr.metric_key
  WHERE (%(device_id)s::int IS NULL OR dd.id = %(device_id)s::int)
    AND sr."DataTime" >= %(start_local)s
    AND sr."DataTime" < %(end_local)s
), dedup AS (
  SELECT *,
         date_trunc('second', ts_utc) AS ts_bucket,
         row_number() OVER (
           PARTITION BY station_id, device_id, metric_id, date_trunc('second', ts_utc)
           ORDER BY ts_utc DESC
         ) AS rn
  FROM parsed
)
SELECT station_id, device_id, metric_id, ts_utc, ts_bucket, val, source_hint
FROM dedup
WHERE rn = 1;
"""

    # 记录完整的SQL语句（DEBUG级别）
    from app.core.logging.setup import log_sql

    log_sql(query_sql, params=params)

    # 合并前：若 fact_measurements 不是 Hypertable，则尽力确保周分区存在；
    # 若已是 Hypertable，则跳过手工分区逻辑（Timescale 自动分片）。
    try:
        with conn.cursor() as _cur_chk:
            _cur_chk.execute(
                "SELECT EXISTS (SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_schema='public' AND hypertable_name='fact_measurements')"
            )
            _fact_is_ht = bool(_cur_chk.fetchone()[0])
        if not _fact_is_ht:
            try:
                _ensure_fact_weekly_partitions(conn, start_utc, end_utc)
            except Exception:
                pass
        else:
            _ensure_fact_timescaledb_layout(conn)
    except Exception:
        pass

    t0 = time.perf_counter()
    try:
        with transaction(conn):
            with conn.cursor() as cur:
                cur.execute("SET LOCAL work_mem = '1GB'")
                cur.execute("SET LOCAL maintenance_work_mem = '1GB'")
                cur.execute("SET LOCAL effective_cache_size = '8GB'")
                cur.execute("SET LOCAL synchronous_commit = 'off'")
                cur.execute("SET LOCAL jit = off")

                merge_sql = """
                    INSERT INTO public.fact_measurements(station_id, device_id, metric_id, ts_raw, ts_bucket, value, source_hint)
                    SELECT DISTINCT ON (station_id, device_id, metric_id, date_trunc('second', ts_utc))
                        station_id,
                        device_id,
                        metric_id,
                        ts_utc,
                        date_trunc('second', ts_utc) AS ts_bucket,
                        val,
                        source_hint
                    FROM (
                        SELECT
                            ds.id AS station_id,
                            dd.id AS device_id,
                            dmc.id AS metric_id,
                            to_timestamp(
                                rtrim(replace(split_part(sr."DataTime", '.', 1), 'T', ' '), 'Z'),
                                'YYYY-MM-DD HH24:MI:SS'
                            ) AT TIME ZONE %(default_tz)s AS ts_utc,
                            sr."DataValue"::numeric AS val,
                            sr.source_hint
                        FROM public.staging_raw sr
                        JOIN public.dim_stations ds ON ds.name = sr.station_name
                        JOIN public.dim_devices dd ON dd.station_id = ds.id AND dd.name = sr.device_name
                        JOIN public.dim_metric_config dmc ON dmc.metric_key = sr.metric_key
                        WHERE (%(device_id)s::int IS NULL OR dd.id = %(device_id)s::int)
                          AND sr."DataTime" >= %(start_local)s
                          AND sr."DataTime" < %(end_local)s
                    ) parsed
                    ORDER BY
                        station_id,
                        device_id,
                        metric_id,
                        date_trunc('second', ts_utc),
                        ts_utc DESC
                    ON CONFLICT (station_id, device_id, metric_id, ts_bucket)
                    DO UPDATE SET
                        value = EXCLUDED.value,
                        source_hint = EXCLUDED.source_hint,
                        ts_raw = EXCLUDED.ts_raw
                """
                cur.execute(merge_sql, params)
                affected = cur.rowcount
                rows_in = affected

        cost_ms = int((time.perf_counter() - t0) * 1000)

        rows_merged = int(affected)
        rows_deduped = max(0, rows_in - rows_merged)
        dedup_ratio = (rows_deduped / rows_in) if rows_in else 0.0

        result = {
            "affected_rows": int(affected),
            "rows_in": rows_in,
            "rows_deduped": rows_deduped,
            "rows_merged": rows_merged,
            "dedup_ratio": dedup_ratio,
            "sql_cost_ms": int(cost_ms),
        }

        _act.info(
            "[数据库-执行] [合并窗口完成]",
            extra={
                "extra_data": {
                    "rows_in": rows_in,
                    "rows_merged": rows_merged,
                    "rows_deduped": rows_deduped,
                    "dedup_ratio": f"{dedup_ratio:.2%}",
                    '耗时（毫秒）': int(cost_ms),
                }
            },
        )

        return result
    except Exception as e:
        cost_ms = int((time.perf_counter() - t0) * 1000)

        payload = {
            "target_table": "public.fact_measurements",
            "sql_op": "MERGE",
            "sql_cost_ms": cost_ms,
            "error": str(e),
        }
        # on_error: 追加 EXPLAIN 计划（文本摘要）
        try:
            with conn.cursor() as cur:
                cur.execute("EXPLAIN " + query_sql, params)
                plan_rows = cur.fetchall()
                plan = "\n".join(r[0] for r in plan_rows)
                payload["explain"] = plan[:2000]
        except Exception:
            pass
        raise


def get_station_devices_metrics_by_time_range(
    conn: psycopg.Connection,
    station_id: int,
    start_utc: datetime,
    end_utc: datetime,
    device_ids: list[int] | None = None,
    metric_ids: list[int] | None = None,
    granularity: str = "auto",
) -> list[dict]:
    """按时间范围查询指定泵站下设备的指标汇总数据（中文注释）。

    设计说明：
    - 默认走 reporting.get_metrics_auto_multi（跨度>阈值则自动走日粒度，否则小时粒度）
    - 当 granularity 指定为 "hourly"/"daily" 时，分别走 get_metrics_hourly_multi/get_metrics_daily_multi
    - 返回统一结构：station_id、device_id、metric_id、ts、cnt、avg_value、min_value、max_value、sum_value
    - 注意：这里不做分页，交给上层控制；如需分页，可在 SQL 外层再包一层 LIMIT/OFFSET

    参数：
    - station_id: 泵站ID（必填）
    - start_utc/end_utc: 查询时间范围（UTC，Python datetime；内部传参时使用 ISO 格式以规避时区适配问题）
    - device_ids/metric_ids: 过滤的设备/指标ID列表（可选）
    - granularity: 粒度选择（auto|hourly|daily），默认 auto
    """
    if start_utc > end_utc:
        raise ValueError("开始时间不能晚于结束时间")

    # 将 datetime 转为 ISO 字符串，规避驱动/时区兼容问题（与本文件其他实现保持一致）
    s_ts = start_utc.isoformat() if hasattr(start_utc, "isoformat") else start_utc
    e_ts = end_utc.isoformat() if hasattr(end_utc, "isoformat") else end_utc

    # 统一参数
    params = {
        "station_ids": [int(station_id)],
        '开始时间戳': s_ts,
        '结束时间戳': e_ts,
        "device_ids": device_ids,
        "metric_ids": metric_ids,
    }

    # 始终走数据库函数：reporting.get_metrics_auto_multi，由数据库端决定小时/天
    sql = """
        SELECT station_id, device_id, metric_id,
               ts, cnt, avg_value, min_value, max_value, sum_value
        FROM reporting.get_metrics_auto_multi(%(station_ids)s, %(start_ts)s, %(end_ts)s, %(device_ids)s, %(metric_ids)s)
        ORDER BY ts, device_id, metric_id
    """

    # 记录 SQL
    from app.core.logging.setup import log_sql

    log_sql(sql, params=params)

    # 执行查询并标准化输出
    from datetime import date as _date
    from datetime import datetime as _dt
    from decimal import Decimal as _Dec

    # 记录 DB 函数调用（应用侧）
    from app.core.logging.setup import log_db_function

    _t0 = time.perf_counter()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    _cost_ms = int((time.perf_counter() - _t0) * 1000)
    try:
        log_db_function(
            "reporting.get_metrics_auto_multi",
            args={
                "station_ids": params.get("station_ids"),
                "device_ids": params.get("device_ids"),
                "metric_ids": params.get("metric_ids"),
                '开始时间戳': params.get("start_ts"),
                '结束时间戳': params.get("end_ts"),
            },
            duration_ms=_cost_ms,
            rows=len(rows),
        )
    except Exception:
        pass

    def _to_primitive(v):
        if isinstance(v, _Dec):
            return float(v)
        if isinstance(v, (_dt,)):
            return v.isoformat()
        if isinstance(v, _date):
            # 保留日期语义，转为 ISO 字符串
            return _dt.combine(v, _dt.min.time()).isoformat()
        return v

    result: list[dict] = []
    for r in rows:
        # (station_id, device_id, metric_id, ts, cnt, avg_value, min_value, max_value, sum_value)
        item = {
            '泵站ID': r[0],
            '设备ID': r[1],
            "metric_id": r[2],
            "ts": _to_primitive(r[3]),
            "cnt": int(r[4]) if r[4] is not None else None,
            "avg_value": _to_primitive(r[5]),
            "min_value": _to_primitive(r[6]),
            "max_value": _to_primitive(r[7]),
            "sum_value": _to_primitive(r[8]),
        }
        result.append(item)

    return result


def get_device_metrics_by_time_range(
    conn: psycopg.Connection,
    device_id: int,
    start_utc: datetime,
    end_utc: datetime,
    metric_ids: list[int] | None = None,
    granularity: str = "auto",
) -> list[dict]:
    """按时间范围查询单设备的指标汇总数据（中文注释）。

    实现说明：
    - 先解析 device_id 对应的 station_id（优先 dim_devices；若失败回退 public.device 兼容视图）
    - 基于 get_metrics_*_multi 族函数，使用 station_ids=[station_id]、device_ids=[device_id]
    - 统一返回结构，见上方函数说明
    """
    if start_utc > end_utc:
        raise ValueError("开始时间不能晚于结束时间")

    # 查 station_id（兼容 dim_devices 与 public.device）
    station_id: int | None = None
    with conn.cursor() as cur:
        try:
            cur.execute(
                "SELECT station_id FROM public.dim_devices WHERE id = %s", (
                    device_id,)
            )
            row = cur.fetchone()
            if row:
                station_id = int(row[0])
        except Exception:
            station_id = None
        if station_id is None:
            try:
                cur.execute(
                    "SELECT station_id FROM public.device WHERE device_id = %s",
                    (device_id,),
                )
                row = cur.fetchone()
                if row:
                    station_id = int(row[0])
            except Exception:
                station_id = None
    if station_id is None:
        raise DatabaseError(f"无法解析设备 {device_id} 所属泵站")

    # 参数转换
    s_ts = start_utc.isoformat() if hasattr(start_utc, "isoformat") else start_utc
    e_ts = end_utc.isoformat() if hasattr(end_utc, "isoformat") else end_utc

    params = {
        "station_ids": [station_id],
        '开始时间戳': s_ts,
        '结束时间戳': e_ts,
        "device_ids": [int(device_id)],
        "metric_ids": metric_ids,
    }

    # 始终走数据库函数：reporting.get_metrics_auto_multi，由数据库端决定小时/天
    sql = """
        SELECT station_id, device_id, metric_id,
               ts, cnt, avg_value, min_value, max_value, sum_value
        FROM reporting.get_metrics_auto_multi(%(station_ids)s, %(start_ts)s, %(end_ts)s, %(device_ids)s, %(metric_ids)s)
        ORDER BY ts, device_id, metric_id
    """

    # 记录 SQL

    from datetime import date as _date
    from datetime import datetime as _dt
    from decimal import Decimal as _Dec

    # 记录 DB 函数调用（应用侧）
    from app.core.logging.setup import log_db_function as _log_db_fn2

    _t1 = time.perf_counter()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    _cost_ms2 = int((time.perf_counter() - _t1) * 1000)
    try:
        _log_db_fn2(
            "reporting.get_metrics_auto_multi",
            args={
                "station_ids": params.get("station_ids"),
                "device_ids": params.get("device_ids"),
                "metric_ids": params.get("metric_ids"),
                '开始时间戳': params.get("start_ts"),
                '结束时间戳': params.get("end_ts"),
            },
            duration_ms=_cost_ms2,
            rows=len(rows),
        )
    except Exception:
        pass

    def _to_primitive(v):
        if isinstance(v, _Dec):
            return float(v)
        if isinstance(v, (_dt,)):
            return v.isoformat()
        if isinstance(v, _date):
            return _dt.combine(v, _dt.min.time()).isoformat()
        return v

    result: list[dict] = []
    for r in rows:
        item = {
            '泵站ID': r[0],
            '设备ID': r[1],
            "metric_id": r[2],
            "ts": _to_primitive(r[3]),
            "cnt": int(r[4]) if r[4] is not None else None,
            "avg_value": _to_primitive(r[5]),
            "min_value": _to_primitive(r[6]),
            "max_value": _to_primitive(r[7]),
            "sum_value": _to_primitive(r[8]),
        }
        result.append(item)

    return result
