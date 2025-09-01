# -*- coding: utf-8 -*-
"""
自动生成 API 路由清单并回写到 docs/应用接口说明.md 的自动段（BEGIN:API_AUTO/END:API_AUTO）。
- 基于 app.api.v1.router.api_v1_router 的路由表生成
- 仅更新自动段，其余手写段不变
- 中文注释，异常时非零退出
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "应用接口说明.md"


def format_route(route) -> str:
    # 方法与路径
    methods = sorted([m for m in getattr(route, "methods", []) if m != "HEAD"])
    method = ",".join(methods) if methods else "GET"
    path = route.path
    # 名称
    name = getattr(route, "name", "-")
    # 响应模型
    resp_model = getattr(route, "response_model", None)
    if resp_model is None:
        resp = "-"
    else:
        mod = getattr(resp_model, "__module__", "")
        nm = getattr(resp_model, "__name__", str(resp_model))
        resp = f"{nm if mod in ('builtins', '') else mod + '.' + nm}"
    # 签名
    endpoint = getattr(route, "endpoint", None)
    try:
        sig = str(inspect.signature(endpoint)) if endpoint else "()"
        ret_ann = inspect.signature(endpoint).return_annotation if endpoint else None
        if ret_ann is not inspect.Signature.empty:
            if getattr(ret_ann, "__module__", "") and getattr(
                ret_ann, "__name__", None
            ):
                ret = f" -> {ret_ann.__module__}.{ret_ann.__name__}"
            else:
                ret = f" -> {ret_ann}"
        else:
            ret = ""
    except Exception:
        sig, ret = "()", ""
    return f"- {method} {path} | name={name} | resp={resp} | signature={sig}{ret}"


def generate() -> str:
    # 延迟导入以避免副作用
    from app.api.v1.router import api_v1_router

    lines = ["## API 路由清单（自动生成）", ""]
    for r in api_v1_router.routes:
        try:
            lines.append(format_route(r))
        except Exception as e:
            lines.append(f"- [WARN] 无法格式化路由 {getattr(r, 'path', '?')}: {e}")
    lines.append("")
    return "\n".join(lines)


def replace_auto_block(text: str, block: str) -> str:
    begin = "<!-- BEGIN:API_AUTO -->"
    end = "<!-- END:API_AUTO -->"
    if begin not in text or end not in text:
        raise RuntimeError("未找到 API 自动段标记，请确保文档包含 BEGIN/END 标记")
    pre, rest = text.split(begin, 1)
    _, post = rest.split(end, 1)
    return pre + begin + "\n\n" + block.rstrip() + "\n\n" + end + post


def main():
    content = DOC.read_text(encoding="utf-8")
    block = generate()
    new_content = replace_auto_block(content, block)
    if new_content != content:
        DOC.write_text(new_content, encoding="utf-8")
        print("[OK] API 文档自动段已更新:", DOC)
    else:
        print("[OK] API 文档自动段无需更新")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[ERR] 生成 API 文档失败:", e)
        sys.exit(2)
