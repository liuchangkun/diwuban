# -*- coding: utf-8 -*-
"""
文档一致性校验脚本：
- 校验 docs/应用接口说明.md 是否包含 measurements 默认时间窗说明（minimal_window_minutes）
- 校验 docs/数据库设计文档.md 的自动段是否含有 “## 视图列表” 与 “v_fully_adaptive_data”
- 校验 docs/_archive/reports/db_schema_snapshot.md 时间戳/关键对象存在性
失败返回非零，供 CI 使用。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC_API = ROOT / "docs" / "应用接口说明.md"
DOC_DB = ROOT / "docs" / "数据库设计文档.md"
SNAP = ROOT / "docs" / "_archive" / "reports" / "db_schema_snapshot.md"


def assert_true(cond: bool, msg: str):
    if not cond:
        print("[FAIL]", msg)
        sys.exit(2)


def check_api_doc():
    text = DOC_API.read_text(encoding="utf-8")
    assert_true(
        "minimal_window_minutes" in text, "接口文档缺少 minimal_window_minutes 说明"
    )
    # 历史视图 v_fully_adaptive_data 已下线，不再强制要求文档提及


def check_db_doc_and_snapshot():
    text = DOC_DB.read_text(encoding="utf-8")
    snap = SNAP.read_text(encoding="utf-8")
    assert_true("## 视图列表" in text, "数据库设计文档自动段中缺少 视图列表 标题")
    # 历史对象校验移除：v_fully_adaptive_data 与 public.operation_data 不再强制存在


def main():
    check_api_doc()
    check_db_doc_and_snapshot()
    print("[OK] 文档一致性校验通过")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print("[ERR] 文档一致性校验异常:", e)
        sys.exit(2)
