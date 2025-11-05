# -*- coding: utf-8 -*-
"""
生成 docs/日志规范.md 中的自动化区块（<!-- BEGIN:LOGGING_AUTO --> ... <!-- END:LOGGING_AUTO -->）。
来源：
- configs/logging.yaml（权威配置）
- app/core/logging/setup.py（上下文字段等）

用法：
  python scripts/tools/doc_gen/gen_logging_md.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import json

try:
    import yaml  # type: ignore
except Exception as e:  # pragma: no cover
    print("[WARN] PyYAML 未安装，将直接退出。", file=sys.stderr)
    raise

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "configs/logging.yaml"
SETUP = ROOT / "app/core/logging/setup.py"
DOC = ROOT / "docs/日志规范.md"

BEGIN = "<!-- BEGIN:LOGGING_AUTO -->"
END = "<!-- END:LOGGING_AUTO -->"


def load_logging_yaml() -> dict[str, Any]:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    return data.get("logging", data)


def parse_context_fields() -> list[str]:
    text = SETUP.read_text(encoding="utf-8")
    # 捕获 _ctx = {"k": ContextVar(...), ...}
    m = re.search(r"_ctx:\s*dict\[[^\]]*\]\s*=\s*{(.*?)}\s*\n", text, flags=re.S)
    if not m:
        return []
    body = m.group(1)
    # 提取键名
    keys = re.findall(r"\"([^\"]+)\"\s*:\s*contextvars\.ContextVar", body)
    return keys


def bullet_list(items: list[str], indent: int = 2) -> str:
    sp = " " * indent
    return "\n".join(f"{sp}- {it}" for it in items)


def render_outputs(outputs: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for o in outputs or []:
        name = o.get("name")
        typ = o.get("type")
        level = o.get("level")
        path = o.get("path")
        route = o.get("route", {})
        only = None
        if isinstance(route, dict):
            only = route.get("only_loggers")
        line = f"  - {name}（{level}，{('文件: ' + path) if (typ=='file' and path) else '控制台' }"
        if only:
            line += f"，route.only_loggers={json.dumps(only, ensure_ascii=False)}"
        line += ")"
        lines.append(line)
    return "\n".join(lines)


def build_block(cfg: dict[str, Any], ctx_fields: list[str]) -> str:
    timezone = cfg.get("timezone", "UTC")
    time_format = cfg.get("time_format", "%Y-%m-%dT%H:%M:%S.%fZ")
    level = cfg.get("level", "INFO")
    fmt = cfg.get("format", "pipe")
    localize = cfg.get("localize", False)

    sql_slow_ms = cfg.get("sql_slow_ms")
    sql = cfg.get("sql", {}) or {}

    capture = cfg.get("capture", {}) or {}
    activity = cfg.get("activity", {}) or {}
    jobs = (cfg.get("jobs", {}) or {}).get("retry_log", {}) or {}

    deps = cfg.get("dependencies", {}) or {}
    cache = cfg.get("cache", {}) or {}
    database = cfg.get("database", {}) or {}

    async_cfg = cfg.get("async", {}) or {}
    hot = cfg.get("hot_reload", {}) or {}

    outputs = cfg.get("outputs", []) or []
    fields_inc = ((cfg.get("fields", {}) or {}).get("include", [])) or []

    deps_opt = cfg.get("deps", {}) or {}

    palette = cfg.get("palette", {}) or {}

    block = []
    block.append(BEGIN)
    block.append("")
    block.append("## 自动生成：配置快照与上下文字段（来源：configs/logging.yaml + app/core/logging/setup.py）")
    block.append("")
    block.append("- 基本配置")
    block.append(f"  - timezone: {timezone}")
    block.append(f"  - time_format: {time_format}")
    block.append(f"  - level: {level}（根级别）")
    block.append(f"  - format: {fmt}（可选：json、keyvalue）")
    block.append(f"  - localize: {str(localize).lower()}（extra_json 键中文化）")
    block.append("")
    block.append("- SQL 日志")
    if sql_slow_ms is not None:
        block.append(f"  - sql_slow_ms: {sql_slow_ms}（慢 SQL 阈值，毫秒）")
    if sql:
        for k in ("explain_on_slow", "explain_timeout_ms", "explain_max_length"):
            if k in sql:
                block.append(f"  - sql.{k}: {sql.get(k)}")
    block.append("")
    block.append("- 采集与摘要（capture/activity/jobs）")
    for k in ("params", "return", "max_field_length", "mask_keys"):
        if k in capture:
            block.append(f"  - capture.{k}: {json.dumps(capture.get(k), ensure_ascii=False)}")
    for k in ("step_slow_ms", "capture_result_summary", "summary_max_length"):
        if k in activity:
            block.append(f"  - activity.{k}: {json.dumps(activity.get(k), ensure_ascii=False)}")
    for k in ("enabled", "include_policy", "threshold_ms"):
        if k in jobs:
            block.append(f"  - jobs.retry_log.{k}: {json.dumps(jobs.get(k), ensure_ascii=False)}")
    block.append("")
    block.append("- 依赖与周边（dependencies/cache/database）")
    http_out = (deps.get("http_out", {}) or {})
    if http_out:
        block.append(
            f"  - dependencies.http_out.enabled: {json.dumps(http_out.get('enabled'))}（出站 HTTP 日志；脱敏 headers={json.dumps(http_out.get('mask_headers'))}）"
        )
    if cache:
        block.append(
            f"  - cache.enabled: {json.dumps(cache.get('enabled'))}；cache.slow_ms: {json.dumps(cache.get('slow_ms'))}"
        )
    pool_log = ((database.get("pool_log", {}) or {}))
    if database.get("tx"):
        block.append("  - database.tx.enabled: true（记录事务边界）")
    if pool_log:
        block.append(
            "  - database.pool_log.enabled: {}；acquire_slow_ms: {}；create_slow_ms: {}；health_check_slow_ms: {}；include_thread: {}；include_stack: {}".format(
                json.dumps(pool_log.get("enabled")),
                json.dumps(pool_log.get("acquire_slow_ms")),
                json.dumps(pool_log.get("create_slow_ms")),
                json.dumps(pool_log.get("health_check_slow_ms")),
                json.dumps(pool_log.get("include_thread")),
                json.dumps(pool_log.get("include_stack")),
            )
        )
    block.append("")
    block.append("- 异步与背压（async/hot_reload）")
    if async_cfg:
        block.append(
            "  - async.enabled: {}；queue_size: {}；batch_size: {}；flush_interval_ms: {}".format(
                json.dumps(async_cfg.get("enabled")),
                json.dumps(async_cfg.get("queue_size")),
                json.dumps(async_cfg.get("batch_size")),
                json.dumps(async_cfg.get("flush_interval_ms")),
            )
        )
        if async_cfg.get("backpressure") is not None:
            block.append(f"  - async.backpressure: {json.dumps(async_cfg.get('backpressure'))}")
        if async_cfg.get("force_sync_levels") is not None:
            block.append(
                f"  - async.force_sync_levels: {json.dumps(async_cfg.get('force_sync_levels'))}"
            )
    if hot:
        block.append(
            f"  - hot_reload.enabled: {json.dumps(hot.get('enabled'))}；backend: {json.dumps(hot.get('backend'))}"
        )
    block.append("")
    block.append("- 输出通道（outputs）")
    block.append(render_outputs(outputs))
    block.append("")
    if fields_inc:
        block.append("- 输出字段（fields.include）")
        block.append("  - " + " / ".join(map(str, fields_inc)))
        block.append("")
    if deps_opt:
        block.append("- 可选依赖（deps）")
        block.append(
            "  - "
            + "/".join(k for k, v in deps_opt.items() if v is not None)
            + "（auto 探测，缺失自动降级）"
        )
        block.append("")
    if palette:
        block.append("- 颜色映射（palette，用于 pipe 彩色输出）")
        block.append("  - 键数量：{}".format(len(palette)))
        block.append("")
    if ctx_fields:
        block.append("- 上下文字段（app/core/logging/setup.py）")
        block.append("  - " + " / ".join(ctx_fields))
        block.append(
            "  - 使用 set_context()/clear_context() 或 log_activity() 自动注入；HTTP 中间件已接入 request_id"
        )
        block.append("")

    block.append(END)
    block.append("")
    return "\n".join(block)


def replace_block(doc_text: str, new_block: str) -> str:
    if BEGIN in doc_text and END in doc_text:
        start = doc_text.index(BEGIN)
        end = doc_text.index(END) + len(END)
        return doc_text[:start] + new_block + doc_text[end:]
    else:
        # 追加在“配置与初始化”章节后
        return doc_text + "\n\n" + new_block + "\n"


def main() -> int:
    cfg = load_logging_yaml()
    ctx_fields = parse_context_fields()
    block = build_block(cfg, ctx_fields)

    text = DOC.read_text(encoding="utf-8")
    new_text = replace_block(text, block)
    if new_text != text:
        DOC.write_text(new_text, encoding="utf-8")
        print("[OK] docs/日志规范.md 已更新 LOGGING_AUTO 区块")
    else:
        print("[OK] docs/日志规范.md LOGGING_AUTO 无变化")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

