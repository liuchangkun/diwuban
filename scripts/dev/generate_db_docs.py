# -*- coding: utf-8 -*-
"""
生成两份文档：
1) 在 docs/数据库设计文档.md 中新增小节“当前部署形态”，写入 Timescale hypertable 现状（版本、hypertables、策略等）
2) 生成/覆盖 docs/数据库对象清单_public.md，导出 public 架构下的表/视图/函数清单

用法：
    python scripts/dev/generate_db_docs.py

说明：
- 复用项目内配置与连接封装：load_settings(Path("configs")) + init_database/get_connection/cleanup_database
- 仅读取信息并写文档，不做任何数据库变更
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Tuple

# 确保可导入 app.* 包
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, get_connection, cleanup_database

DOC_DB_DESIGN = ROOT / "docs" / "数据库设计文档.md"
DOC_PUBLIC_LIST = ROOT / "docs" / "数据库对象清单_public.md"


def now_cn() -> str:
    tz = None
    if ZoneInfo:
        try:
            tz = ZoneInfo("Asia/Shanghai")
        except Exception:
            tz = None
    dt = datetime.now(tz) if tz else datetime.now()
    # 统一为 +08 显示
    return dt.strftime("%Y-%m-%d %H:%M:%S%z")


def q(sql: str, *args) -> List[Tuple[Any, ...]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()


def fetch_timescale_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "version": None,
        "hypertables": [],  # list of dicts
        "policies": {
            "compression": [],
            "retention": [],
            "reorder": [],
            "cagg_refresh": [],
        },
        "caggs": [],  # list of dicts
        "presence_table": None,
    }

    # 版本
    rows = q("select extversion from pg_extension where extname='timescaledb'")
    info["version"] = rows[0][0] if rows else None

    # hypertables + chunk interval + compression flag
    # 兼容处理：优先 timescaledb_information.hypertables，如无则跳过
    try:
        rows = q(
            """
            select h.hypertable_schema,
                   h.hypertable_name,
                   h.num_dimensions,
                   h.num_chunks,
                   h.compression_enabled,
                   h.chunk_time_interval
            from timescaledb_information.hypertables h
            order by 1, 2
            """
        )
        hypertables = []
        for r in rows:
            hypertables.append(
                {
                    "schema": r[0],
                    "name": r[1],
                    "num_dimensions": r[2],
                    "num_chunks": r[3],
                    "compression_enabled": bool(r[4]) if r[4] is not None else None,
                    "chunk_interval": r[5],
                }
            )
        info["hypertables"] = hypertables
    except Exception:
        pass

    # time column name 及维度
    try:
        rows = q(
            """
            select d.hypertable_schema,
                   d.hypertable_name,
                   d.column_name,
                   d.interval_length
            from timescaledb_information.dimensions d
            where d.dimension_type ilike 'time%'
            order by 1, 2
            """
        )
        time_dim: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for s, t, col, interval in rows:
            time_dim[(s, t)] = {"time_column": col, "interval_length": interval}
        # merge into hypertables
        if info["hypertables"]:
            for ht in info["hypertables"]:
                k = (ht.get("schema"), ht.get("name"))
                if k in time_dim:
                    ht.update(time_dim[k])
    except Exception:
        pass

    # 压缩策略
    for sql, key in [
        (
            "select hypertable_schema, hypertable_name, compress_after from timescaledb_information.policy_compression order by 1,2",
            "compression",
        ),
        (
            "select hypertable_schema, hypertable_name, drop_after from timescaledb_information.policy_retention order by 1,2",
            "retention",
        ),
        (
            "select hypertable_schema, hypertable_name, reorder_index from timescaledb_information.policy_reorder order by 1,2",
            "reorder",
        ),
    ]:
        try:
            rows = q(sql)
            for r in rows:
                info["policies"][key].append({"schema": r[0], "name": r[1], key: r[2]})
        except Exception:
            continue

    # 连续聚合与刷新策略
    try:
        rows = q(
            """
            select view_schema, view_name, materialized_only
            from timescaledb_information.continuous_aggregates
            order by 1,2
            """
        )
        info["caggs"] = [
            {"schema": r[0], "name": r[1], "materialized_only": r[2]} for r in rows
        ]
    except Exception:
        pass

    try:
        rows = q(
            """
            select view_schema, view_name, start_offset, end_offset, schedule_interval
            from timescaledb_information.policy_refresh_continuous_aggregate
            order by 1,2
            """
        )
        for r in rows:
            info["policies"]["cagg_refresh"].append(
                {
                    "schema": r[0],
                    "name": r[1],
                    "start_offset": r[2],
                    "end_offset": r[3],
                    "schedule_interval": r[4],
                }
            )
    except Exception:
        pass

    # 关键 presence 表实际 schema
    try:
        rows = q(
            """
            select n.nspname as schema, c.relname as name
            from pg_class c
            join pg_namespace n on n.oid = c.relnamespace
            where c.relkind in ('r','p') and c.relname = 'metrics_presence_per_second_device'
            limit 1
            """
        )
        if rows:
            info["presence_table"] = {"schema": rows[0][0], "name": rows[0][1]}
    except Exception:
        pass

    return info


def build_deploy_markdown(ts: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("## 1.2 当前部署形态（Timescale 现状 - 自动生成）")
    lines.append("")
    lines.append(f"- 生成时间：{now_cn()} (+08)")
    lines.append(f"- TimescaleDB 版本：{ts.get('version') or '未检测到'}")
    if ts.get("presence_table"):
        pt = ts["presence_table"]
        lines.append(
            f"- 关键业务表 metrics_presence_per_second_device 位置：{pt['schema']}.{pt['name']}"
        )
    lines.append("")
    # Hypertables 简表
    hts = ts.get("hypertables") or []
    if hts:
        lines.append("### Hypertables 一览（节选）")
        for ht in hts[:50]:  # 控制长度
            parts = [
                f"{ht.get('schema')}.{ht.get('name')}",
            ]
            if ht.get("time_column"):
                parts.append(f"time={ht['time_column']}")
            if ht.get("chunk_interval") is not None:
                parts.append(f"chunk={ht['chunk_interval']}")
            if ht.get("compression_enabled") is not None:
                parts.append(
                    "compression=on"
                    if ht.get("compression_enabled")
                    else "compression=off"
                )
            lines.append("- " + ", ".join(parts))
        if len(hts) > 50:
            lines.append(f"- … 共 {len(hts)} 张 hypertables")
        lines.append("")

    # 策略摘要
    pol = ts.get("policies") or {}
    if any(pol.get(k) for k in ["compression", "retention", "cagg_refresh", "reorder"]):
        lines.append("### 策略摘要")
        if pol.get("compression"):
            lines.append("- 压缩策略：")
            for r in pol["compression"][:20]:
                lines.append(
                    f"  - {r['schema']}.{r['name']} compress_after={r.get('compression')}"
                )
            if len(pol["compression"]) > 20:
                lines.append(f"  - … 共 {len(pol['compression'])} 条")
        if pol.get("retention"):
            lines.append("- 保留策略：")
            for r in pol["retention"][:20]:
                lines.append(
                    f"  - {r['schema']}.{r['name']} drop_after={r.get('retention')}"
                )
            if len(pol["retention"]) > 20:
                lines.append(f"  - … 共 {len(pol['retention'])} 条")
        if pol.get("reorder"):
            lines.append("- 重排序策略：")
            for r in pol["reorder"][:20]:
                lines.append(f"  - {r['schema']}.{r['name']} index={r.get('reorder')}")
            if len(pol["reorder"]) > 20:
                lines.append(f"  - … 共 {len(pol['reorder'])} 条")
        if pol.get("cagg_refresh"):
            lines.append("- 连续聚合刷新策略：")
            for r in pol["cagg_refresh"][:20]:
                lines.append(
                    f"  - {r['schema']}.{r['name']} window=[{r.get('start_offset')}, {r.get('end_offset')}], every={r.get('schedule_interval')}"
                )
            if len(pol["cagg_refresh"]) > 20:
                lines.append(f"  - … 共 {len(pol['cagg_refresh'])} 条")
        lines.append("")

    # CAGGs 列表
    caggs = ts.get("caggs") or []
    if caggs:
        lines.append("### 连续聚合（Continuous Aggregates）")
        for c in caggs[:50]:
            lines.append(
                f"- {c.get('schema')}.{c.get('name')} materialized_only={c.get('materialized_only')}"
            )
        if len(caggs) > 50:
            lines.append(f"- … 共 {len(caggs)} 个连续聚合")
        lines.append("")

    return "\n".join(lines) + "\n"


def insert_deploy_section(md_path: Path, new_section_md: str) -> None:
    text = md_path.read_text(encoding="utf-8")
    anchor = "## 1.1 命名规范"
    idx = text.find(anchor)
    if idx == -1:
        # 附加到“1. 概览”之后，若未找到则追加到文件末尾
        head = text
        tail = "\n" + new_section_md
        md_path.write_text(head + tail, encoding="utf-8")
        return

    # 定位下一个同级标题“## ”
    next_idx = text.find("\n## ", idx + 1)
    if next_idx == -1:
        # 直接附加在文末
        head = text
        tail = "\n" + new_section_md
        md_path.write_text(head + tail, encoding="utf-8")
        return

    head = text[:next_idx]
    tail = text[next_idx:]
    out = head + "\n" + new_section_md + tail
    md_path.write_text(out, encoding="utf-8")


def generate_public_objects(md_path: Path) -> None:
    # 表
    tables = [
        r[0]
        for r in q(
            """
        select c.relname
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        where n.nspname='public' and c.relkind in ('r','p')
        order by 1
        """
        )
    ]

    # 视图（含物化视图）
    views = [
        r[0]
        for r in q(
            """
        select c.relname
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        where n.nspname='public' and c.relkind in ('v','m')
        order by 1
        """
        )
    ]

    # 函数签名
    funcs = [
        r[0]
        for r in q(
            """
        select p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')'
        from pg_proc p
        join pg_namespace n on n.oid = p.pronamespace
        where n.nspname='public' and p.prokind='f'
        order by 1
        """
        )
    ]

    lines: List[str] = []
    lines.append("# 数据库对象清单（public 架构）")
    lines.append("")
    lines.append(f"- 生成时间（+08）: {now_cn()}")
    lines.append(
        "- 覆盖范围：public 架构下的表（含分区/子分区）、视图（含物化视图）、函数（含签名）"
    )
    lines.append("")

    lines.append("## 表与分区")
    lines.append("")
    for t in tables:
        lines.append(f"- {t}")
    lines.append("")

    lines.append("## 视图")
    lines.append("")
    for v in views:
        lines.append(f"- {v}")
    lines.append("")

    lines.append("## 函数（签名）")
    lines.append("")
    for f in funcs:
        lines.append(f"- {f}")
    lines.append("")

    lines.append(
        "备注：pg_stat_statements* / pldbg_* 等扩展/调试函数未纳入清单注释维护范围。"
    )
    lines.append("")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    settings = load_settings(Path("configs"))
    init_database(settings)

    try:
        ts_info = fetch_timescale_info()
        section = build_deploy_markdown(ts_info)
        insert_deploy_section(DOC_DB_DESIGN, section)
        generate_public_objects(DOC_PUBLIC_LIST)
        print("OK: 文档生成完成")
        return 0
    finally:
        cleanup_database()


if __name__ == "__main__":
    sys.exit(main())
