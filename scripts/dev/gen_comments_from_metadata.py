from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

DOC_BEGIN = "$DOC$"
DOC_END = "$DOC$"


def q_ident(name: str) -> str:
    """SQL 标识符加双引号，内部双引号转义为两次双引号。"""
    if name.startswith('"') and name.endswith('"'):
        return name  # 已经被引号包裹
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


# 关键列名的中文注释映射（启发式）
COLUMN_HINTS = {
    "id": "ID（主键或标识）",
    "station_id": "泵站ID（外键）",
    "device_id": "设备ID（外键）",
    "metric_id": "指标ID（外键）",
    "ts": "时间",
    "ts_raw": "原始时间（建议UTC）",
    "ts_bucket": "对齐后的时间（整秒/整分钟/整小时等）",
    "value": "数值",
    "source_hint": "来源提示/数据来源",
    "inserted_at": "插入时间（系统生成）",
    "updated_at": "更新时间（系统生成）",
    "name": "名称",
    "metric_key": "指标键（唯一键）",
    "device_name": "设备名称",
    "station_name": "泵站名称",
}

# 已知表名的中文用途（启发式）
TABLE_HINTS = {
    (
        "public",
        "fact_measurements",
    ): "时序事实表：每行表示某设备某指标在某一时间点的数值（整秒对齐）",
    ("public", "staging_raw"): "导入暂存原始数据（未清洗/未对齐）",
    ("public", "staging_rejects"): "导入拒收记录（格式/校验失败）",
    ("public", "dim_devices"): "设备维表",
    ("public", "dim_stations"): "泵站维表",
    ("public", "dim_metric_config"): "指标配置维表（指标ID/键/单位等）",
    (
        "public",
        "metrics_presence_per_second_device",
    ): "设备-秒级指标可用性/需要计算标记",
}

VIEW_HINT_DEFAULT = "视图：用于聚合/便捷查询"
MATVIEW_HINT_DEFAULT = "物化视图：用于加速复杂聚合（需维护刷新）"
FUNC_HINT_DEFAULT = "函数：请补充业务用途"


def esc(s: str) -> str:
    return s.replace(DOC_END, DOC_END + "_")


def guess_table_usage(schema: str, name: str) -> str:
    return TABLE_HINTS.get((schema, name), f"数据表：{schema}.{name}（用途待补充）")


def guess_column_comment(col: str) -> str:
    return COLUMN_HINTS.get(col, f"字段：{col}（说明待补充）")


def has_ts_columns(cols: list[dict]) -> bool:
    keys = {c["name"].lower() for c in cols}
    return bool({"ts", "ts_bucket", "ts_raw"} & keys)


def build_examples_for_table(schema: str, name: str, cols: list[dict]) -> str:
    lines: list[str] = []
    lines.append(f"-- 示例：读取前100行\nSELECT * FROM {schema}.{name} LIMIT 100;")
    if has_ts_columns(cols):
        ts_col = None
        for c in cols:
            if c["name"] in ("ts_bucket", "ts", "ts_raw"):
                ts_col = c["name"]
                break
        if ts_col:
            lines.append(
                f"\n-- 示例：按时间窗口查询\nSELECT * FROM {schema}.{name}\nWHERE {ts_col} >= :start_ts AND {ts_col} < :end_ts\nORDER BY {ts_col} ASC\nLIMIT 100;"
            )
    # 常见维度过滤
    dim_cols = [
        c
        for c in ("station_id", "device_id", "metric_id")
        if any(col["name"] == c for col in cols)
    ]
    if dim_cols:
        conds = " AND ".join([f"{c} = :{c}" for c in dim_cols[:2]])
        lines.append(
            f"\n-- 示例：按维度过滤\nSELECT * FROM {schema}.{name}\nWHERE {conds}\nORDER BY 1\nLIMIT 100;"
        )
    return "\n".join(lines)


def build_examples_for_view(schema: str, name: str) -> str:
    return f"-- 示例：查看视图内容\nSELECT * FROM {schema}.{name} LIMIT 100;"


def build_examples_for_function(schema: str, name: str, args: str) -> str:
    # 将参数签名转为占位符示例：bigint,timestamptz -> :p1,:p2
    arg_types = [a.strip() for a in args.split(",")] if args else []
    placeholders = ", ".join([f":p{i+1}" for i in range(len(arg_types))])
    return (
        f"-- 示例：函数调用\nSELECT * FROM {schema}.{name}({placeholders});"
        if placeholders
        else f"-- 示例：函数调用\nSELECT * FROM {schema}.{name}();"
    )


def gen_comments(md: Dict[str, Any]) -> str:
    out: list[str] = []
    for schema, obj in md.get("schemas", {}).items():
        # Tables
        for tname, tbody in obj.get("tables", {}).items():
            usage = guess_table_usage(schema, tname)
            examples = build_examples_for_table(schema, tname, tbody.get("columns", []))
            table_doc = f"用途: {usage}\n使用方法: 常规SELECT/过滤/排序\n{examples}"
            out.append(
                f"COMMENT ON TABLE {q_ident(schema)}.{q_ident(tname)} IS {DOC_BEGIN}{esc(table_doc)}{DOC_END};"
            )
            # Columns
            for col in tbody.get("columns", []):
                cname = col["name"]
                # 不覆盖已有注释：生成时仍输出，但在执行阶段可选择跳过（本脚本仅生成，不执行）
                cdoc = col.get("comment") or guess_column_comment(cname)
                out.append(
                    f"COMMENT ON COLUMN {q_ident(schema)}.{q_ident(tname)}.{q_ident(cname)} IS {DOC_BEGIN}{esc(str(cdoc))}{DOC_END};"
                )
        # Views
        for vname, vbody in obj.get("views", {}).items():
            usage = vbody.get("comment") or VIEW_HINT_DEFAULT
            examples = build_examples_for_view(schema, vname)
            vdoc = f"用途: {usage}\n使用方法: 直接查询\n{examples}"
            out.append(
                f"COMMENT ON VIEW {q_ident(schema)}.{q_ident(vname)} IS {DOC_BEGIN}{esc(vdoc)}{DOC_END};"
            )
        # Materialized Views
        for mname, mbody in obj.get("matviews", {}).items():
            usage = mbody.get("comment") or MATVIEW_HINT_DEFAULT
            examples = build_examples_for_view(schema, mname)
            mdoc = f"用途: {usage}\n使用方法: 直接查询（注意刷新策略）\n{examples}"
            out.append(
                f"COMMENT ON MATERIALIZED VIEW {q_ident(schema)}.{q_ident(mname)} IS {DOC_BEGIN}{esc(mdoc)}{DOC_END};"
            )
        # Functions
        for fname, fbody in obj.get("functions", {}).items():
            args = fbody.get("args") or ""
            rett = fbody.get("return") or ""
            usage = fbody.get("comment") or FUNC_HINT_DEFAULT
            examples = build_examples_for_function(schema, fname, args)
            fdoc = f"用途: {usage}\n参数: {args}\n返回: {rett}\n{examples}"
            # 使用 identity args 以匹配函数签名
            sig = args
            out.append(
                f"COMMENT ON FUNCTION {q_ident(schema)}.{q_ident(fname)}({sig}) IS {DOC_BEGIN}{esc(fdoc)}{DOC_END};"
            )
    return "\n\n".join(out) + "\n"


def main() -> None:
    meta_path = Path("generated/db_objects.json")
    if not meta_path.exists():
        raise SystemExit(
            "generated/db_objects.json 不存在，请先运行 scan_db_objects.py"
        )
    md = json.loads(meta_path.read_text(encoding="utf-8"))
    sql = gen_comments(md)
    out_dir = Path("generated")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "comments_full.sql"
    out_file.write_text(sql, encoding="utf-8")
    print(str(out_file))


if __name__ == "__main__":
    main()
