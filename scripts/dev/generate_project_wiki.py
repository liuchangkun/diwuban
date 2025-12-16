#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成“项目现状对齐”的注释化文档（有人读的，不是纯列表）：
- API 路由（带参数说明、返回模型与注意事项）
- 功能流程总览（orchestrator 关键步骤的 Why/What/Impact/Rollback）
- 数据库对象总览（来自 generated/db_objects.json 的表/列与注释）
- 配置项总览（汇总 configs/*.yaml 的关键项与作用）

输出：docs/_自动/*.md
注意：不覆盖人工维护文档，仅供引用/嵌入。
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
DOC_AUTO = ROOT / "docs" / "_自动"
API_DIR = ROOT / "app" / "api" / "v1" / "endpoints"
DB_JSON = ROOT / "generated" / "db_objects.json"
CONFIGS_DIR = ROOT / "configs"
ORCH = ROOT / "app" / "services" / "run_all" / "orchestrator.py"
SERVICES_DIR = ROOT / "app" / "services"
SCHEMAS_DIR = ROOT / "app" / "schemas"

# 领域术语/词典覆盖（可选）：docs/术语词典.json
TERMINOLOGY_JSON = ROOT / "docs" / "术语词典.json"
TERMS: Dict[str, Any] = {}

def _load_terms() -> Dict[str, Any]:
    try:
        if TERMINOLOGY_JSON.exists():
            return json.loads(TERMINOLOGY_JSON.read_text(encoding="utf-8")) or {}
    except Exception:
        pass
    return {}

TERMS = _load_terms()


def _match_entry(name: str, entry: Dict[str, Any]) -> bool:
    n = (name or "").lower()
    eq = (entry.get("equals") or entry.get("equal") or "").lower()
    if eq and n == eq:
        return True
    pref = (entry.get("prefix") or "").lower()
    if pref and n.startswith(pref):
        return True
    contains = (entry.get("contains") or entry.get("substring") or "").lower()
    if contains and contains in n:
        return True
    rgx = entry.get("regex")
    if rgx:
        try:
            if re.search(rgx, n):
                return True
        except Exception:
            pass
    return False


def _service_entry_match(rel_path: str, func: str, entry: Dict[str, Any]) -> bool:
    r = (rel_path or "").lower()
    f = (func or "").lower()
    # 路径匹配：path/path_contains/equals/prefix/contains
    p = entry.get("path") or entry.get("path_contains") or ""
    if p:
        if not _match_entry(r, {"contains": str(p)}):
            return False
    # 函数名匹配：function/function_contains
    fn = entry.get("function") or entry.get("function_contains") or ""
    if fn:
        if not _match_entry(f, {"contains": str(fn)}):
            return False
    return True

# 规则化“具体作用/功能”推断（不依赖注释）
KEY_HINTS_TABLE = {
    "fact_": "事实表：存储明细/度量数据，面向查询与统计",
    "staging_": "装载中间表：用于导入/清洗过程的过渡数据",
    "dim_": "维度表：实体/枚举/元数据，供关联使用",
    "mv_": "物化视图：预计算结果，加速读取",
    "v_": "视图：查询封装，便于复用",
    "_threshold": "阈值/规则配置相关",
    "_log": "日志/审计记录相关",
}

KEY_HINTS_COLUMN = {
    "station_id": "站点外键",
    "device_id": "设备外键",
    "metric_id": "指标外键",
    "record_timestamp": "记录时间戳（统一UTC）",
    "ts": "时间戳（UTC）",
    "metrics_data": "度量数据（JSON/JSONB）",
    "total_records": "记录总数/窗口内计数",
    "unit": "单位",
    "unit_display": "单位显示",
}

KEY_HINTS_SERVICE = [
    ("ingest/create_staging", "创建/刷新临时结构，保障后续合并效率与幂等"),
    ("ingest/merge", "在时间窗口内将数据去重/对齐并合并入事实表"),
    ("ingest/copy", "从映射并发导入原始CSV到数据库"),
    ("quality/mark_window", "对窗口数据进行质量打标，产出命中与样例"),
    ("rules/", "质量阈值/规则的刷新或影子计算"),
    ("reporting/", "导出统计/质量/覆盖率等报表"),
    ("presence", "计算存在性/在场指标，用于可用性分析"),
    ("device_running", "计算设备运行/停机区段，用于规则判定"),
]


def _infer_table_summary(schema: str, table: str) -> str:
    # 1) 词典覆盖（优先）
    try:
        for ent in (TERMS.get("tables") or []):
            sch = (ent.get("schema") or "").lower()
            if sch and sch != (schema or "").lower():
                continue
            if _match_entry(table, ent):
                return ent.get("summary") or ent.get("desc") or ent.get("description") or ""
    except Exception:
        pass
    # 2) 规则推断
    name = (table or "").lower()
    for k, v in KEY_HINTS_TABLE.items():
        if k in name or name.startswith(k.rstrip("_")):
            return v
    # 3) 默认：依据 schema 简述
    if schema == "public":
        return "业务核心对象表/视图"
    return f"{schema} 架构下的对象"


def _infer_col_summary(col: str) -> Optional[str]:
    # 词典覆盖优先
    try:
        hit = (TERMS.get("columns") or {}).get(col.lower())
        if hit:
            return hit
    except Exception:
        pass
    return KEY_HINTS_COLUMN.get(col.lower())


def _infer_api_summary(method: str, path: str) -> str:
    # 1) 词典覆盖（优先）
    try:
        for ent in (TERMS.get("apis") or []):
            m = (ent.get("method") or "").upper()
            if m and m != (method or "").upper():
                continue
            if _match_entry(path, ent):
                return ent.get("summary") or ent.get("desc") or ent.get("description") or "业务接口：详见参数与返回模型"
    except Exception:
        pass
    # 2) 规则推断
    p = (path or "").lower()
    if "/stations/" in p and "measurements" in p:
        return "按站点在时间窗口内查询度量（可筛选设备/指标，支持分页与粒度）"
    if "/devices/" in p and "measurements" in p:
        return "按设备在时间窗口内查询度量（可筛选指标，支持分页与粒度）"
    if p.endswith("/raw"):
        return "返回近原始结构：wide 透传 metrics_data，long 按 (ts,metric,value) 展平"
    if "health" in p:
        return "系统/数据库健康检查"
    if "devices" in p and method == "GET":
        return "查询设备与基础元数据"
    return "业务接口：详见参数与返回模型"


def _infer_service_summary(rel: str, func: str) -> Optional[str]:
    r = rel.replace("\\", "/")
    # 1) 词典覆盖（优先）
    try:
        for ent in (TERMS.get("services") or []):
            if _service_entry_match(r, func, ent):
                return ent.get("summary") or ent.get("desc") or ent.get("description")
    except Exception:
        pass
    # 2) 规则推断（路径+函数）
    for key, hint in KEY_HINTS_SERVICE:
        if key in r:
            return hint
    if func.startswith("create_"):
        return "创建/初始化相关资源或结构"
    if func.startswith("merge_"):
        return "合并/写入主表或目标对象"
    if func.startswith("run_"):
        return "执行一项端到端/批处理任务"
    if func.startswith("export_"):
        return "导出统计/报表/结果"
    return None



def _infer_name_hint(name: str) -> Optional[str]:
    n = (name or "").lower()
    # 词典覆盖优先（names/columns）
    try:
        hit = (TERMS.get("names") or {}).get(n) or (TERMS.get("columns") or {}).get(n)
        if hit:
            return hit
    except Exception:
        pass
    if n in KEY_HINTS_COLUMN:
        return KEY_HINTS_COLUMN[n]
    if n.endswith("_id"):
        return "外键/标识"
    if n.startswith("is_") or n.startswith("has_"):
        return "布尔标志"
    if "time" in n or n == "ts" or n.endswith("_ts"):
        return "时间戳/时间字段"
    return None

# ---- Anchors & Utils for context-friendly referencing ----
ANCHOR_PREFIX_API = "api"
ANCHOR_PREFIX_DB = "db"
ANCHOR_PREFIX_SVC = "svc"

def _sanitize_anchor_part(s: str) -> str:
    import re as _re
    s = (s or "").strip().replace("\\", "/")
    # keep letters, digits and [._-{}], replace others with '-'
    s = _re.sub(r"[^0-9a-zA-Z\.\-_/{}]", "-", s)
    s = s.replace("/", ".")
    # collapse consecutive dots
    s = _re.sub(r"\.\.+", ".", s).strip(".")
    return s or "x"

def _anchor_id(kind: str, *parts: str) -> str:
    parts2 = [_sanitize_anchor_part(p) for p in parts if p is not None]
    return f"{kind}." + ".".join([p for p in parts2 if p])

def _anchor_html(kind: str, *parts: str) -> str:
    return f"<a id=\"{_anchor_id(kind, *parts)}\"></a>"


DOC_AUTO.mkdir(parents=True, exist_ok=True)

@dataclass
class ApiEndpoint:
    method: str
    path: str
    func: str
    params: List[Tuple[str, Optional[str], Optional[str]]]  # (name, type, desc)
    response_model: Optional[str]
    notes: List[str]


def _parse_api_file(py_path: Path) -> List[ApiEndpoint]:
    endpoints: List[ApiEndpoint] = []
    try:
        src = py_path.read_text(encoding="utf-8")
    except Exception:
        return endpoints
    try:
        tree = ast.parse(src)
    except Exception:
        return endpoints

    # 建立行号到源码行映射（用于抓取 @router.* 路由与注释）
    lines = src.splitlines()

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:  # noqa: N802
            # 找 decorator 里的 @router.get/post 等
            for dec in node.decorator_list:
                try:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                        method = dec.func.attr.upper()
                        if method in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
                            # path 取第一个位置参数字符串
                            path = None
                            if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                                path = dec.args[0].value
                            # response_model
                            resp = None
                            for kw in dec.keywords or []:
                                if kw.arg == "response_model":
                                    if isinstance(kw.value, ast.Name):
                                        resp = kw.value.id
                                    elif isinstance(kw.value, ast.Attribute):
                                        resp = kw.value.attr
                            # 参数解析：name, annotation, Query(..., description="...")
                            params: List[Tuple[str, Optional[str], Optional[str]]] = []
                            for a in node.args.args:
                                if a.arg in {"self", "request"}:
                                    continue
                                ann = None
                                desc = None
                                if a.annotation is not None:
                                    # 直接使用 AST 源片段，兼容复杂注解
                                    ann = _get_annotation_str(a.annotation, src)
                                # 默认值里找 Query(..., description=)
                                for d in node.args.defaults:
                                    # 逐个匹配不到位，退化为从源码切片按参数名正则查找
                                    pass
                                # 正则在函数源码块中查找本参数的 Query 描述
                                try:
                                    fn_text = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                                    # 参数名=Query(..., description="...")
                                    m = re.search(rf"\b{re.escape(a.arg)}\s*:\s*[^=]+=\s*Query\((?P<inner>[^)]*)\)", fn_text)
                                    if m:
                                        inner = m.group("inner")
                                        md = re.search(r"description\s*=\s*\"([^\"]+)\"", inner)
                                        if not md:
                                            md = re.search(r"description\s*=\s*'([^']+)'", inner)
                                        if md:
                                            desc = md.group(1)
                                except Exception:
                                    pass
                                params.append((a.arg, str(ann) if ann else None, desc))
                            # 补充行内注释作为 notes
                            notes: List[str] = []
                            try:
                                dec_line = node.lineno - 2
                                for i in range(max(0, dec_line - 2), dec_line + 1):
                                    if i < len(lines) and "#" in lines[i]:
                                        c = lines[i].split("#", 1)[1].strip()
                                        if c:
                                            notes.append(c)
                            except Exception:
                                pass
                            if path:
                                endpoints.append(
                                    ApiEndpoint(method=method, path=path, func=node.name, params=params, response_model=resp, notes=notes)
                                )
                except Exception:
                    continue

    Visitor().visit(tree)
    return endpoints


def generate_api_routes() -> str:
    endpoints: List[ApiEndpoint] = []
    for f in sorted(API_DIR.glob("*.py")):
        if f.name.startswith("__"):
            continue
        endpoints.extend(_parse_api_file(f))
    endpoints.sort(key=lambda x: (x.path, x.method))

    out: List[str] = []
    out.append("# API 路由（自动生成｜含注释）\n")
    out.append("> 说明：根据 app/api/v1/endpoints/*.py 的 @router 装饰器解析，参数说明来自 Query(..., description=)。\n")
    out.append("")
    for ep in endpoints:
        # anchor: api.<path>.<method>
        out.append(_anchor_html(ANCHOR_PREFIX_API, ep.path, ep.method))
        out.append(f"## {ep.method} {ep.path}")
        out.append(f"- 处理函数：`{ep.func}`")
        # 功能说明（基于路径/方法推断，不依赖注释）
        out.append(f"- 功能说明：{_infer_api_summary(ep.method, ep.path)}")
        if ep.response_model:
            out.append(f"- 返回模型：`{ep.response_model}`")
        if ep.notes:
            out.append("- 备注：" + "；".join(ep.notes))
        if ep.params:
            out.append("- 参数：")
            for name, ann, desc in ep.params:
                ann_s = f"<{ann}>" if ann else ""
                desc_s = f"：{desc}" if desc else ""
                out.append(f"  - `{name}` {ann_s}{desc_s}")
        out.append("")
    out.append("---\n")
    out.append(f"> 生成器：generate_project_wiki.py｜时间：{datetime.now():%Y-%m-%d %H:%M}")
    return "\n".join(out) + "\n"


def generate_flow_overview() -> str:
    out: List[str] = []
    out.append("# 功能流程总览（自动生成｜含注释）\n")
    out.append("> 说明：依据 services/run_all/orchestrator.py，提炼关键步骤并解释 Why/What/Impact/Rollback。\n")
    out.append("")
    out.append("## 总体流程")
    out.append("1) prepare_dim：准备维度表（站/设备/指标），确保后续合并维度可用")
    out.append("2) create_staging：创建/刷新 staging 结构，承接映射后的原始数据")
    out.append("3) ingest_copy：按映射复制数据并统计 files/rows（审计用途）")
    out.append("4) merge_fact：在窗口内合并数据到事实表 fact_measurements（统一时区处理）")
    out.append("5) device_running（可选）：计算设备运行状态与审计")
    out.append("6) quality_mark（可选）：质量打标，输出规则命中/资源消耗等摘要与样例")
    out.append("7) presence（可选）：按窗口计算存在性汇总")
    out.append("")
    out.append("## 我们为什么这样做（Why）")
    out.append("- 将采集→暂存→合并→质量→存在性的链路串联，保障每步均可审计与回放")
    out.append("- 配置开关来自 configs/merge.yaml，可按任务裁剪开销")
    out.append("")
    out.append("## 做了什么（What）")
    out.append("- 对窗口进行统一解析：输入缺 tz 时按系统默认 tz 解释，输出统一为本地时区 +08 样式\n")
    out.append("- 在质量打标前自动刷新相关物化视图，提高判定时效\n")
    out.append("- 并行质量打标支持 auto 并行度估算，输出 rule_summary 与样例（anomaly.case）\n")
    out.append("")
    out.append("## 影响范围（Impact）")
    out.append("- 数据写入：staging_*、fact_measurements、presence/quality 相关表\n")
    out.append("- 资源占用：并行度/窗口大小影响 CPU/内存/扫描行数\n")
    out.append("")
    out.append("## 如何验证（Evidence）")
    out.append("- 查看 logs/activity.log、logs/anomaly.log 中的 window_start/window_end/rule_summary\n")
    out.append("- 检查 reports/ 下导出的质量分布文件与 run_all_summary.json\n")
    out.append("")
    out.append("## 如需回滚（Rollback）")
    out.append("- 减小窗口或关闭可选步骤（merge.yaml: run_all.*=false），避免写入\n")
    out.append("- 对事实表的修复：可通过补写/覆盖策略复跑；必要时使用清理脚本\n")
    out.append("\n---\n")
    out.append(f"> 生成器：generate_project_wiki.py｜时间：{datetime.now():%Y-%m-%d %H:%M}")
    return "\n".join(out) + "\n"


def generate_db_overview() -> str:
    out: List[str] = []
    out.append("# 数据库对象总览（自动生成｜含注释）\n")
    out.append("> 说明：来源 generated/db_objects.json（优先展示 comment 的语义说明）。\n")
    out.append("")
    if not DB_JSON.exists():
        out.append("> 未找到 generated/db_objects.json，跳过。\n")
    else:
        try:
            data = json.loads(DB_JSON.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        schemas = (data or {}).get("schemas", {}) or {}
        # 展示所有 schema（用户要求不做白名单/过滤）
        for schema_name in sorted(schemas.keys()):
            # anchor for schema
            out.append(_anchor_html(ANCHOR_PREFIX_DB, schema_name))
            out.append(f"## schema: {schema_name}")
            tables = (schemas[schema_name] or {}).get("tables", {}) or {}
            for t_name, t_info in sorted(tables.items()):
                # anchor for table
                out.append(_anchor_html(ANCHOR_PREFIX_DB, f"{schema_name}.{t_name}"))
                out.append(f"### 表：{t_name}")
                out.append(f"> 作用（推断）：{_infer_table_summary(schema_name, t_name)}")
                if t_info.get("comment"):
                    out.append(f"> 来源注释：{t_info['comment']}")
                cols = t_info.get("columns", []) or []
                for c in cols[:50]:  # 每表最多50列展示
                    cname = c.get("name")
                    ctype = c.get("data_type")
                    cdesc = c.get("comment")
                    hint = _infer_col_summary(cname)
                    if hint:
                        out.append(f"- {cname} ({ctype})：{cdesc or '（未写注释）'} —— 作用（推断）：{hint}")
                    else:
                        out.append(f"- {cname} ({ctype})：{cdesc or '（未写注释）'}")
                if len(cols) > 50:
                    out.append(f"- ... 共 {len(cols)} 列，已截断显示")
                out.append("")
    out.append("---\n")
    out.append(f"> 生成器：generate_project_wiki.py｜时间：{datetime.now():%Y-%m-%d %H:%M}")
    return "\n".join(out) + "\n"


def generate_config_overview() -> str:
    out: List[str] = []
    out.append("# 配置项总览（自动生成｜含注释）\n")
    out.append("> 说明：汇总 configs/*.yaml 的关键项，用于快速理解可调参数；具体以 YAML 为准。\n")
    out.append("")
    for f in sorted(CONFIGS_DIR.glob("*.yaml")):
        try:
            raw = f.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        out.append(f"## {f.name}")
        # 粗略提取 key: value # 注释 的注释说明
        for line in raw:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if ":" in s:
                key = s.split(":", 1)[0].strip()
                cm = None
                if "#" in line:
                    cm = line.split("#", 1)[1].strip()
                out.append(f"- {key}：{cm or '（详见 YAML 上方注释）'}")
        out.append("")

    out.append("---\n")
    out.append(f"> 生成器：generate_project_wiki.py｜时间：{datetime.now():%Y-%m-%d %H:%M}")
    return "\n".join(out) + "\n"



def _get_annotation_str(node: Optional[ast.AST], src: str) -> Optional[str]:
    if node is None:
        return None
    try:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parts: List[str] = []
            cur: Any = node
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value  # type: ignore[attr-defined]
            if isinstance(cur, ast.Name):
                parts.append(cur.id)
            return ".".join(reversed(parts)) if parts else node.attr
        seg = ast.get_source_segment(src, node)
        if seg:
            return seg
        return None
    except Exception:
        return None


def _dotted_name(n: ast.AST) -> Optional[str]:
    try:
        if isinstance(n, ast.Name):
            return n.id
        if isinstance(n, ast.Attribute):
            parts: List[str] = []
            cur: Any = n
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value  # type: ignore[attr-defined]
            if isinstance(cur, ast.Name):
                parts.append(cur.id)
            return ".".join(reversed(parts)) if parts else None
        return None
    except Exception:
        return None


def _collect_calls(node: ast.AST) -> List[ast.Call]:
    return [n for n in ast.walk(node) if isinstance(n, ast.Call)]


LOG_BASES = {"logging", "logger", "LOGGER", "log", "LOG"}
DB_EXEC_NAMES = {"execute", "executemany", "scalars", "commit", "rollback", "cursor", "fetchone", "fetchall"}


def _detect_logging_calls(fn: ast.AST) -> List[str]:
    kinds: List[str] = []
    for call in _collect_calls(fn):
        name = _dotted_name(call.func)
        if not name:
            continue
        # logging.info / logger.debug 等
        if name.startswith("logging."):
            meth = name.split(".", 1)[1]
            kinds.append(meth)
        else:
            # 形如 logger.info / LOG.error
            parts = name.split(".")
            if len(parts) >= 2 and parts[0] in LOG_BASES:
                kinds.append(parts[1])
    # 去重并保持出现顺序
    seen = set()
    ordered: List[str] = []
    for k in kinds:
        if k not in seen:
            seen.add(k)
            ordered.append(k)
    return ordered


SQL_TABLE_PATTERNS = [
    re.compile(r"\bfrom\s+([a-zA-Z0-9_.\"]+)", re.IGNORECASE),
    re.compile(r"\binsert\s+into\s+([a-zA-Z0-9_.\"]+)", re.IGNORECASE),
    re.compile(r"\bupdate\s+([a-zA-Z0-9_.\"]+)", re.IGNORECASE),
    re.compile(r"\bjoin\s+([a-zA-Z0-9_.\"]+)", re.IGNORECASE),
]


def _extract_tables_from_sql(sql: str) -> List[str]:
    tables: List[str] = []
    for pat in SQL_TABLE_PATTERNS:
        for m in pat.findall(sql or ""):
            t = m.strip('"')
            if t not in tables:
                tables.append(t)
    return tables


def _detect_db_ops(fn: ast.AST) -> Tuple[List[str], List[str]]:
    ops: List[str] = []
    tables: List[str] = []
    for call in _collect_calls(fn):
        name = _dotted_name(call.func) or ""
        parts = name.split(".")
        attr = parts[-1] if parts else ""
        if attr in DB_EXEC_NAMES or name.startswith("sqlalchemy.") or name.startswith("asyncpg.") or name.startswith("psycopg2."):
            if attr and attr not in ops:
                ops.append(attr)
            # 提取 SQL 表名
            if call.args:
                a0 = call.args[0]
                if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                    for t in _extract_tables_from_sql(a0.value):
                        if t not in tables:
                            tables.append(t)
    return ops, tables



def generate_services_doc() -> str:
    return generate_services_doc2()

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}
HTTP_LIB_PREFIXES = ("requests.", "httpx.")
SDK_PREFIXES = ("redis.", "boto3.", "botocore.", "pika.", "pymongo.", "elasticsearch.", "minio.", "s3fs.")
OS_FS_FUNCS = {"remove", "rename", "makedirs", "mkdir", "rmdir", "listdir", "scandir", "stat"}
PATH_METHODS = {"read_text", "write_text", "open", "mkdir", "exists", "unlink", "rename", "replace", "glob", "iterdir"}
SHUTIL_FUNCS = {"copy", "copy2", "move", "rmtree"}


def _const_str(node: Optional[ast.AST]) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):  # f"..."
        # 粗略还原：仅拼接常量片段
        parts: List[str] = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
        return "".join(parts) if parts else None
    return None


def _detect_http_calls(fn: ast.AST) -> List[str]:
    hits: List[str] = []
    for call in _collect_calls(fn):
        name = _dotted_name(call.func) or ""
        lname = name.lower()
        lib = None
        method = None
        if lname.startswith(HTTP_LIB_PREFIXES):
            lib = name.split(".", 1)[0]
            method = name.split(".")[-1]
        else:
            # 形如 session.get(...), 简单通过方法名判断
            last = name.split(".")[-1]
            if last in HTTP_METHODS:
                method = last
                # 尝试猜测库
                if "httpx" in lname:
                    lib = "httpx"
                elif "requests" in lname:
                    lib = "requests"
                elif "aiohttp" in lname or "ClientSession" in lname:
                    lib = "aiohttp"
                else:
                    lib = "session"
        if not method:
            continue
        url = None
        if call.args:
            url = _const_str(call.args[0])
        if not url and call.keywords:
            for kw in call.keywords:
                if kw.arg == "url":
                    url = _const_str(kw.value)
                    break
        summary = f"{lib}.{method}"
        if url and (url.startswith("http") or "://" in url):
            summary += f" {url}"
        if summary not in hits:
            hits.append(summary)
    return hits


def _detect_fs_ops(fn: ast.AST) -> Tuple[List[str], List[str]]:
    ops: List[str] = []
    paths: List[str] = []
    for call in _collect_calls(fn):
        name = _dotted_name(call.func) or ""
        last = name.split(".")[-1]
        base = name.split(".")[0]
        # 内置 open()
        if name == "open":
            if "open" not in ops:
                ops.append("open")
            if call.args:
                p = _const_str(call.args[0])
                if p and p not in paths:
                    paths.append(p)
            continue
        # pathlib.Path.* 或 任意对象的常见路径方法
        if last in PATH_METHODS:
            if last not in ops:
                ops.append(last)
            if call.args:
                p = _const_str(call.args[0])
                if p and p not in paths:
                    paths.append(p)
            continue
        # os.*
        if base == "os" and last in OS_FS_FUNCS:
            if last not in ops:
                ops.append(last)
            if call.args:
                p = _const_str(call.args[0])
                if p and p not in paths:
                    paths.append(p)
            continue
        # shutil.*
        if name.startswith("shutil."):
            f = name.split(".")[-1]
            if f in SHUTIL_FUNCS and f not in ops:
                ops.append(f)
            for a in call.args[:2]:  # src, dst
                p = _const_str(a)
                if p and p not in paths:
                    paths.append(p)
    return ops, paths


def _detect_subprocess_calls(fn: ast.AST) -> List[str]:
    cmds: List[str] = []
    for call in _collect_calls(fn):
        name = _dotted_name(call.func) or ""
        if not name.startswith("subprocess."):
            continue
        cmd: Optional[str] = None
        if call.args:
            a0 = call.args[0]
            if isinstance(a0, ast.List) and a0.elts:
                c0 = _const_str(a0.elts[0])
                if c0:
                    cmd = c0
            else:
                cmd = _const_str(a0)
        if not cmd:
            for kw in call.keywords or []:
                if kw.arg == "args":
                    cmd = _const_str(kw.value)
                    break
        if cmd and cmd not in cmds:
            cmds.append(cmd)
    return cmds


def _detect_env_access(fn: ast.AST) -> List[str]:
    envs: List[str] = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            name = _dotted_name(node.func) or ""
            if name == "os.getenv" and node.args:
                v = _const_str(node.args[0])
                if v and v not in envs:
                    envs.append(v)
        elif isinstance(node, ast.Subscript):
            base = _dotted_name(node.value) or ""
            if base == "os.environ":
                # os.environ["KEY"]
                key = None
                if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                    key = node.slice.value
                elif isinstance(node.slice, ast.Index) and isinstance(node.slice.value, ast.Constant) and isinstance(node.slice.value.value, str):
                    key = node.slice.value.value
                if key and key not in envs:
                    envs.append(key)
    return envs


def _detect_other_sdks(fn: ast.AST) -> List[str]:
    fams: List[str] = []
    for call in _collect_calls(fn):
        name = _dotted_name(call.func) or ""
        lname = name.lower()
        for pre in SDK_PREFIXES:
            if lname.startswith(pre):
                fam = pre.rstrip(".")
                if fam not in fams:
                    fams.append(fam)
    return fams
def generate_services_doc2() -> str:
    out: List[str] = []
    out.append("# 函数与服务说明（自动生成｜含注释）\n")
    out.append(
        "> 说明：扫描 app/services 下的函数与类方法，展示签名、docstring 摘要、参数、返回、日志、数据库、外部交互（HTTP/FS/子进程/环境变量/其他SDK）。\n"
    )
    out.append("")

    for py in sorted(SERVICES_DIR.rglob("*.py")):
        name = py.name
        if name.startswith("__") or "/tests/" in str(py).replace("\\", "/"):
            continue
        try:
            src = py.read_text(encoding="utf-8")
            tree = ast.parse(src)
        except Exception:
            continue
        rel = py.relative_to(ROOT)
        out.append(_anchor_html(ANCHOR_PREFIX_SVC, str(rel)))
        out.append(f"## 模块：{rel}")

        # 顶层函数
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith("_"):
                    continue
                doc = (ast.get_docstring(node) or "").strip().splitlines()[:1]
                doc_line = doc[0] if doc else "（未提供 docstring）"
                # 参数
                params: List[str] = []
                for a in node.args.args:
                    if a.arg == "self":
                        continue
                    ann = _get_annotation_str(a.annotation, src)
                    params.append(f"- {a.arg}{f' <{ann}>' if ann else ''}")
                ret = _get_annotation_str(getattr(node, "returns", None), src)
                out.append(_anchor_html(ANCHOR_PREFIX_SVC, str(rel), node.name))
                out.append(f"### 函数：{node.name}()")
                out.append(f"> 摘要：{doc_line}")
                hint = _infer_service_summary(str(rel), node.name)
                if hint:
                    out.append(f"> 功能说明（推断）：{hint}")
                if params:
                    out.append("- 参数：")
                    out.extend([f"  {p}" for p in params])
                if ret:
                    out.append(f"- 返回：<{ret}>")
                logs = _detect_logging_calls(node)
                db_ops, db_tables = _detect_db_ops(node)
                out.append("- 日志输出：" + ("有（" + "、".join(logs) + "）" if logs else "无"))
                has_db = bool(db_ops or db_tables)
                db_line = "有（" + ("、".join(db_ops) if db_ops else "")
                if db_tables:
                    db_line += ("；表：" if db_ops else "表：") + "、".join(db_tables)
                db_line += "）"
                out.append("- 数据库操作：" + (db_line if has_db else "无"))
                http = _detect_http_calls(node)
                fs_ops, fs_paths = _detect_fs_ops(node)
                sp_cmds = _detect_subprocess_calls(node)
                envs = _detect_env_access(node)
                sdks = _detect_other_sdks(node)
                out.append("- HTTP 调用：" + ("有（" + "、".join(http) + "）" if http else "无"))
                fs_line = "有（" + ("、".join(fs_ops) if fs_ops else "")
                if fs_paths:
                    fs_line += ("；路径：" if fs_ops else "路径：") + "、".join(fs_paths[:3]) + (" 等" if len(fs_paths) > 3 else "")
                fs_line += "）"
                out.append("- 文件系统：" + (fs_line if (fs_ops or fs_paths) else "无"))
                out.append("- 子进程：" + ("有（" + "、".join(sp_cmds) + "）" if sp_cmds else "无"))
                out.append("- 环境变量：" + ("有（" + "、".join(envs) + "）" if envs else "无"))
                out.append("- 其他SDK：" + ("有（" + "、".join(sdks) + "）" if sdks else "无"))
                out.append("")
        # 类与方法
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
                if not methods:
                    continue
                cdoc = (ast.get_docstring(node) or "").strip().splitlines()[:1]
                out.append(_anchor_html(ANCHOR_PREFIX_SVC, str(rel), node.name))

                out.append(f"### 类：{node.name}")
                if cdoc:
                    out.append(f"> 摘要：{cdoc[0]}")
                for m in methods:
                    mdoc = (ast.get_docstring(m) or "").strip().splitlines()[:1]
                    mdoc_line = mdoc[0] if mdoc else "（未提供 docstring）"
                    params: List[str] = []
                    for a in m.args.args:
                        if a.arg in {"self", "cls"}:
                            continue
                        ann = _get_annotation_str(a.annotation, src)
                        params.append(f"- {a.arg}{f' <{ann}>' if ann else ''}")
                    ret = _get_annotation_str(getattr(m, "returns", None), src)
                    out.append(_anchor_html(ANCHOR_PREFIX_SVC, str(rel), node.name, m.name))
                    out.append(f"#### 方法：{m.name}()")
                    out.append(f"> 摘要：{mdoc_line}")
                    mhint = _infer_service_summary(str(rel), m.name)
                    if mhint:
                        out.append(f"> 功能说明（推断）：{mhint}")
                    if params:
                        out.append("- 参数：")
                        out.extend([f"  {p}" for p in params])
                    if ret:
                        out.append(f"- 返回：<{ret}>")
                    logs = _detect_logging_calls(m)
                    db_ops, db_tables = _detect_db_ops(m)
                    out.append("- 日志输出：" + ("有（" + "、".join(logs) + "）" if logs else "无"))
                    has_db = bool(db_ops or db_tables)
                    db_line = "有（" + ("、".join(db_ops) if db_ops else "")
                    if db_tables:
                        db_line += ("；表：" if db_ops else "表：") + "、".join(db_tables)
                    db_line += "）"
                    out.append("- 数据库操作：" + (db_line if has_db else "无"))
                    http = _detect_http_calls(m)
                    fs_ops, fs_paths = _detect_fs_ops(m)
                    sp_cmds = _detect_subprocess_calls(m)
                    envs = _detect_env_access(m)
                    sdks = _detect_other_sdks(m)
                    out.append("- HTTP 调用：" + ("有（" + "、".join(http) + "）" if http else "无"))
                    fs_line = "有（" + ("、".join(fs_ops) if fs_ops else "")
                    if fs_paths:
                        fs_line += ("；路径：" if fs_ops else "路径：") + "、".join(fs_paths[:3]) + (" 等" if len(fs_paths) > 3 else "")
                    fs_line += "）"
                    out.append("- 文件系统：" + (fs_line if (fs_ops or fs_paths) else "无"))
                    out.append("- 子进程：" + ("有（" + "、".join(sp_cmds) + "）" if sp_cmds else "无"))
                    out.append("- 环境变量：" + ("有（" + "、".join(envs) + "）" if envs else "无"))
                    out.append("- 其他SDK：" + ("有（" + "、".join(sdks) + "）" if sdks else "无"))
                    out.append("")
        out.append("")

    out.append("---\n")
    out.append(f"> 生成器：generate_project_wiki.py｜时间：{datetime.now():%Y-%m-%d %H:%M}")
    return "\n".join(out) + "\n"


def _pyd_field_desc(call: ast.Call, src: str) -> Optional[str]:
    try:
        for kw in call.keywords or []:
            if kw.arg == "description":
                if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    return kw.value.value
                # fallback slice
                return src[kw.value.col_offset : kw.value.end_col_offset]
    except Exception:
        return None
    return None


def generate_models_doc() -> str:
    out: List[str] = []
    out.append("# 模型字段与示例（自动生成｜含注释）\n")
    out.append(
        "> 说明：解析 app/schemas 下的 Pydantic BaseModel，列出字段类型、默认值与描述；并生成示例 JSON。\n"
    )
    out.append("")

    for py in sorted(SCHEMAS_DIR.glob("*.py")):
        try:
            src = py.read_text(encoding="utf-8")
            tree = ast.parse(src)
        except Exception:
            continue
        rel = py.relative_to(ROOT)
        out.append(f"## 模块：{rel}")
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                # 是否继承 BaseModel
                is_model = any(
                    (
                        isinstance(b, ast.Name) and b.id == "BaseModel"
                    )
                    or (isinstance(b, ast.Attribute) and b.attr == "BaseModel")
                    for b in node.bases
                )
                if not is_model:
                    continue
                cdoc = (ast.get_docstring(node) or "").strip().splitlines()[:2]
                if cdoc:
                    out.append(f"### 模型：{node.name}\n> 摘要：{' '.join(cdoc)}")
                else:
                    out.append(f"### 模型：{node.name}")
                fields: List[Tuple[str, str, Optional[str], Optional[str]]] = []  # name, type, default, desc
                example: Dict[str, Any] = {}
                for stmt in node.body:
                    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        fname = stmt.target.id
                        ftype = _get_annotation_str(stmt.annotation, src) or "Any"
                        fdef: Optional[str] = None
                        fdesc: Optional[str] = None
                        if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == "Field":
                            fdesc = _pyd_field_desc(stmt.value, src)
                            # 默认值：尝试从 args[0] 抓
                            if stmt.value.args:
                                v = stmt.value.args[0]
                                if isinstance(v, ast.Constant):
                                    fdef = json.dumps(v.value, ensure_ascii=False)
                        elif isinstance(stmt.value, ast.Constant):
                            fdef = json.dumps(stmt.value.value, ensure_ascii=False)
                        fields.append((fname, ftype, fdef, fdesc))
                        # 粗略构造示例
                        if ftype:
                            t = ftype.lower()
                            if "int" in t:
                                example[fname] = 0
                            elif "float" in t or "decimal" in t:
                                example[fname] = 0.0
                            elif "bool" in t:
                                example[fname] = False
                            elif "list" in t:
                                example[fname] = []
                            elif "dict" in t:
                                example[fname] = {}
                            elif "optional" in t:
                                example[fname] = None
                            else:
                                example[fname] = "string"
                        else:
                            example[fname] = None
                if fields:
                    out.append("- 字段：")
                    for fname, ftype, fdef, fdesc in fields:
                        dv = f"，默认={fdef}" if fdef is not None else ""
                        hint = _infer_name_hint(fname)
                        if fdesc and hint:
                            out.append(f"  - `{fname}` <{ftype}>{dv}：{fdesc} —— 作用（推断）：{hint}")
                        elif fdesc:
                            out.append(f"  - `{fname}` <{ftype}>{dv}：{fdesc}")
                        elif hint:
                            out.append(f"  - `{fname}` <{ftype}>{dv} —— 作用（推断）：{hint}")
                        else:
                            out.append(f"  - `{fname}` <{ftype}>{dv}")
                # 示例
                try:
                    example_json = json.dumps(example, ensure_ascii=False)
                except Exception:
                    example_json = "{}"
                out.append("- 示例：")
                out.append(f"  ```json\n  {example_json}\n  ```")
                out.append("")
        out.append("")

    out.append("---\n")
    out.append(f"> 生成器：generate_project_wiki.py｜时间：{datetime.now():%Y-%m-%d %H:%M}")
    return "\n".join(out) + "\n"


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# --- Terms coverage & Diff helpers ---
import difflib


def _load_terms() -> Dict[str, Any]:
    p = ROOT / "docs" / "术语词典.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}


def generate_terms_coverage_md(api_md: str, db_md: str, svc_md: str, mdl_md: str) -> str:
    terms = _load_terms()
    out: List[str] = []
    out.append("# 术语覆盖率（自动生成）\n")
    out.append(
        "> 说明：统计可识别对象（API 路由、数据库表、服务函数、Pydantic 模型）的术语命中情况，辅助补充术语词典。\n"
    )
    # APIs
    api_items: List[str] = []
    for line in api_md.splitlines():
        if line.startswith("## ") and "/" in line:
            # e.g. ## GET /devices/{id}
            try:
                method, path = line[3:].split(" ", 1)
                api_items.append(path.strip())
            except Exception:
                pass
    # DB tables
    db_items: List[str] = []
    current_schema = None
    for line in db_md.splitlines():
        if line.startswith("## schema: "):
            current_schema = line.split(": ", 1)[1].strip()
        elif line.startswith("### 表：") and current_schema:
            t = line.split("：", 1)[1].strip()
            db_items.append(f"{current_schema}.{t}")
    # Services (functions + class methods)
    svc_items: List[str] = []
    cur_class = None
    for line in svc_md.splitlines():
        if line.startswith("### 类："):
            cur_class = line.split("：", 1)[1].strip()
        elif line.startswith("### 函数："):
            fn = line.split("：", 1)[1].strip()
            svc_items.append(fn)
        elif line.startswith("#### 方法：") and cur_class:
            m = line.split("：", 1)[1].strip()
            svc_items.append(f"{cur_class}.{m}")
    # Models
    mdl_items: List[str] = []
    for line in mdl_md.splitlines():
        if line.startswith("### 模型："):
            mdl_items.append(line.split("：", 1)[1].strip())

    def _calc_coverage(items: List[str], term_section: str) -> Tuple[int, int, List[str]]:
        raw = terms.get(term_section) or {}
        # normalize to a set of keys
        term_keys: set[str] = set()
        if isinstance(raw, dict):
            term_keys.update([str(k) for k in raw.keys()])
        elif isinstance(raw, list):
            for it in raw:
                if isinstance(it, str):
                    term_keys.add(it)
                elif isinstance(it, dict):
                    # try common fields + rule fields (equals/prefix/contains/regex)
                    for k in (
                        it.get("name"), it.get("key"), it.get("id"),
                        it.get("equals"), it.get("prefix"), it.get("contains"), it.get("regex")
                    ):
                        if isinstance(k, str) and k:
                            term_keys.add(k)
        total = len(items)
        if total == 0:
            return 0, 0, []
        covered = []
        for it in items:
            ok = False
            for k in term_keys:
                if not k:
                    continue
                if k == it or k in it or it in k:
                    ok = True
                    break
            if ok:
                covered.append(it)
        return total, len(covered), [x for x in items if x not in covered][:30]

    sections = [
        ("API 路由", api_items, "apis"),
        ("数据库表", db_items, "tables"),
        ("服务函数/方法", svc_items, "services"),
        ("Pydantic 模型", mdl_items, "models"),
    ]
    for title, items, key in sections:
        total, hit, missing = _calc_coverage(items, key)
        rate = (hit / total * 100) if total else 0.0
        out.append(f"## {title}")
        out.append(f"- 对象数：{total}，命中：{hit}（{rate:.1f}%）")
        if missing:
            out.append("- 未命中（建议补充到术语词典）：")
            for m in missing[:20]:
                out.append(f"  - {m}")
        out.append("")
    out.append("---\n")
    out.append(f"> 生成器：generate_project_wiki.py｜时间：{datetime.now():%Y-%m-%d %H:%M}")
    return "\n".join(out) + "\n"



def render_unified_diff(name: str, old: str, new: str, max_lines: int = 200) -> str:
    diff = list(
        difflib.unified_diff(
            old.splitlines(), new.splitlines(), fromfile=f"old/{name}", tofile=f"new/{name}", lineterm=""
        )
    )
    if not diff:
        return f"### {name}\n- 无变化\n"
    # keep first few hunks within max_lines
    lines = diff[:max_lines]
    body = "\n".join(lines)
    return f"### {name}\n\n```diff\n{body}\n```\n"

# --- Terms candidates (from missing items) ---


# --- Terms candidates (from missing items) ---

def generate_terms_candidates(api_md: str, db_md: str, svc_md: str, mdl_md: str) -> tuple[str, dict]:
    """Return (markdown, json) candidates for terminology dictionary based on uncovered items."""
    terms = _load_terms()

    # Reuse extraction similar to coverage
    api_items: list[str] = []
    for line in api_md.splitlines():
        if line.startswith("## ") and "/" in line:
            try:
                _, path = line[3:].split(" ", 1)
                api_items.append(path.strip())
            except Exception:
                pass
    db_items: list[str] = []
    current_schema = None
    for line in db_md.splitlines():
        if line.startswith("## schema: "):
            current_schema = line.split(": ", 1)[1].strip()
        elif line.startswith("### 表：") and current_schema:
            t = line.split("：", 1)[1].strip()
            db_items.append(f"{current_schema}.{t}")
    svc_items: list[str] = []
    cur_class = None
    for line in svc_md.splitlines():
        if line.startswith("### 类："):
            cur_class = line.split("：", 1)[1].strip()
        elif line.startswith("### 函数："):
            fn = line.split("：", 1)[1].strip()
            svc_items.append(fn)
        elif line.startswith("#### 方法：") and cur_class:
            m = line.split("：", 1)[1].strip()
            svc_items.append(f"{cur_class}.{m}")
    mdl_items: list[str] = []
    for line in mdl_md.splitlines():
        if line.startswith("### 模型："):
            mdl_items.append(line.split("：", 1)[1].strip())

    def _norm_keys(raw):
        if isinstance(raw, dict):
            return set(str(k) for k in raw.keys())
        if isinstance(raw, list):
            s = set()
            for it in raw:
                if isinstance(it, str):
                    s.add(it)
                elif isinstance(it, dict):
                    for k in (it.get("name"), it.get("key"), it.get("id")):
                        if isinstance(k, str) and k:
                            s.add(k)
            return s
        return set()

    exist = {
        "apis": _norm_keys(terms.get("apis") or {}),
        "tables": _norm_keys(terms.get("tables") or {}),
        "services": _norm_keys(terms.get("services") or {}),
        "models": _norm_keys(terms.get("models") or {}),
    }

    missing = {
        "apis": [x for x in api_items if not any(k == x or k in x or x in k for k in exist["apis"])],
        "tables": [x for x in db_items if not any(k == x or k in x or x in k for k in exist["tables"])],
        "services": [x for x in svc_items if not any(k == x or k in x or x in k for k in exist["services"])],
        "models": [x for x in mdl_items if not any(k == x or k in x or x in k for k in exist["models"])],
    }

    # Markdown summary
    md: list[str] = []
    md.append("# 术语候选（自动生成）\n")
    md.append("> 说明：以下对象尚未在术语词典中覆盖，建议选择性补充释义/别名/归一化命名。\n")
    for title, key in [("API 路由", "apis"), ("数据库表", "tables"), ("服务函数/方法", "services"), ("Pydantic 模型", "models")]:
        items = missing[key]
        if not items:
            continue
        md.append(f"## {title}")
        for it in items[:50]:
            md.append(f"- {it}")
        md.append("")
    md.append("---\n")
    md.append(f"> 生成器：generate_project_wiki.py｜时间：{datetime.now():%Y-%m-%d %H:%M}")

    # JSON candidates skeleton
    json_obj = {
        "apis": [{"key": x, "desc": "", "alias": []} for x in missing["apis"][:200]],
        "tables": [{"key": x, "desc": "", "alias": []} for x in missing["tables"][:200]],
        "services": [{"key": x, "desc": "", "alias": []} for x in missing["services"][:200]],
        "models": [{"key": x, "desc": "", "alias": []} for x in missing["models"][:200]],
    }
    return "\n".join(md) + "\n", json_obj

    diff = list(
        difflib.unified_diff(
            old.splitlines(), new.splitlines(), fromfile=f"old/{name}", tofile=f"new/{name}", lineterm=""
        )
    )
    if not diff:
        return f"### {name}\n- 无变化\n"
    # keep first few hunks within max_lines
    lines = diff[:max_lines]
    body = "\n".join(lines)
    return f"### {name}\n\n```diff\n{body}\n```\n"


# --- AUTO WIKI EMBED ---
MARKER_MAP = {
    "API": DOC_AUTO / "API路由.md",
    "MODELS": DOC_AUTO / "模型字段与示例.md",
    "CONFIGS": DOC_AUTO / "配置项总览.md",
    "DB_OVERVIEW": DOC_AUTO / "数据库对象总览.md",
    "SERVICES": DOC_AUTO / "函数与服务说明.md",
}

TARGETS = [
    (ROOT / "docs" / "应用接口说明.md", ["API", "MODELS"]),
    (ROOT / "docs" / "数据库设计文档.md", ["DB_OVERVIEW"]),
    (ROOT / "docs" / "配置说明.md", ["CONFIGS"]),
    (ROOT / "docs" / "服务与作业说明.md", ["SERVICES"]),
]


def _replace_between_markers(text: str, key: str, new_md: str) -> str:
    begin = f"<!-- AUTO-WIKI:BEGIN:{key} -->"
    end = f"<!-- AUTO-WIKI:END:{key} -->"
    if begin in text and end in text and text.index(begin) < text.index(end):
        prefix = text.split(begin, 1)[0]
        suffix = text.split(end, 1)[1]
        return f"{prefix}{begin}\n\n{new_md}\n{end}{suffix}"
    # 未找到则追加在文末
    return text.rstrip() + f"\n\n{begin}\n\n{new_md}\n{end}\n"


def embed_auto_sections() -> None:
    for target_path, keys in TARGETS:
        try:
            txt = target_path.read_text(encoding="utf-8")
        except Exception:
            # 若目标文档不存在，创建一个简单骨架，后续追加标记块
            txt = f"# {target_path.stem}\n\n"
        for k in keys:
            src_path = MARKER_MAP.get(k)
            if not src_path or not src_path.exists():
                continue
            try:
                md = src_path.read_text(encoding="utf-8").strip()
            except Exception:
                md = ""
            txt = _replace_between_markers(txt, k, md)
        target_path.write_text(txt, encoding="utf-8")


def main() -> None:
    api_md = generate_api_routes()
    flow_md = generate_flow_overview()
    db_md = generate_db_overview()
    cfg_md = generate_config_overview()
    svc_md = generate_services_doc()
    mdl_md = generate_models_doc()
    # read old contents for diff
    files = {
        "API路由.md": (DOC_AUTO / "API路由.md", api_md),
        "功能流程总览.md": (DOC_AUTO / "功能流程总览.md", flow_md),
        "数据库对象总览.md": (DOC_AUTO / "数据库对象总览.md", db_md),
        "配置项总览.md": (DOC_AUTO / "配置项总览.md", cfg_md),
        "函数与服务说明.md": (DOC_AUTO / "函数与服务说明.md", svc_md),
        "模型字段与示例.md": (DOC_AUTO / "模型字段与示例.md", mdl_md),
    }
    olds: Dict[str, str] = {}
    for name, (p, _) in files.items():
        try:
            olds[name] = p.read_text(encoding="utf-8") if p.exists() else ""
        except Exception:
            olds[name] = ""
    # write new
    for name, (p, md) in files.items():
        write_file(p, md)
    # coverage
    cov_md = generate_terms_coverage_md(api_md, db_md, svc_md, mdl_md)
    write_file(DOC_AUTO / "术语覆盖率.md", cov_md)
    # terms candidates
    cand_md, cand_json = generate_terms_candidates(api_md, db_md, svc_md, mdl_md)
    write_file(DOC_AUTO / "术语候选.md", cand_md)
    try:
        (DOC_AUTO / "术语词典候选.json").write_text(json.dumps(cand_json, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    # diff
    diff_dir = DOC_AUTO / "diff"
    diff_dir.mkdir(parents=True, exist_ok=True)
    parts: List[str] = ["# 本次 vs 上次（自动生成差异）\n", "> 说明：展示主要自动文档的差异片段，便于快速审阅。\n"]
    for name, (p, _) in files.items():
        new = p.read_text(encoding="utf-8") if p.exists() else ""
        parts.append(render_unified_diff(name, olds.get(name, ""), new))
    parts.append("---\n")
    parts.append(f"> 生成器：generate_project_wiki.py｜时间：{datetime.now():%Y-%m-%d %H:%M}")
    write_file(diff_dir / "本次_vs_上次.md", "\n".join(parts) + "\n")
    # finally embed to manual docs
    embed_auto_sections()


if __name__ == "__main__":
    main()

