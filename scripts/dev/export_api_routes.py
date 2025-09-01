# -*- coding: utf-8 -*-
"""
导出 FastAPI 路由清单（中文注释）
- 动态加载 app.main:app
- 枚举 /api/v1 下的所有路由：方法、路径、端点函数、响应模型
- 输出 Markdown 到 docs/_archive/reports/api_routes_snapshot.md
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# 确保可以导入 app 包
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "_archive" / "reports" / "api_routes_snapshot.md"


def get_response_model(route) -> str:
    try:
        model = getattr(route, "response_model", None)
        if model is None:
            return "-"
        if isinstance(model, list):
            return ",".join(getattr(m, "__name__", str(m)) for m in model)
        return getattr(model, "__name__", str(model))
    except Exception:
        return "-"


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # 动态导入 FastAPI 应用
    from app.main import app  # type: ignore

    lines = ["# API 路由清单快照\n"]
    for route in app.routes:
        try:
            path = getattr(route, "path", "")
            methods = sorted(getattr(route, "methods", []) or [])
            if not path.startswith("/api/v1"):
                continue
            name = getattr(route, "name", "")
            endpoint = getattr(route, "endpoint", None)
            sig = ""
            if endpoint is not None:
                try:
                    sig = str(inspect.signature(endpoint))
                except Exception:
                    sig = "(unavailable)"
            resp = get_response_model(route)
            lines.append(
                f"- {','.join(methods)} {path} | name={name} | resp={resp} | signature={sig}"
            )
        except Exception:
            continue
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("[OK] 导出完成：", OUT)


if __name__ == "__main__":
    main()
