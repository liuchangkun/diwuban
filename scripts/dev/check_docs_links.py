# -*- coding: utf-8 -*-
"""
文档内部链接扫描与修复脚本（中文注释）

功能：
- 扫描 docs/** 下 Markdown 文件内形如 [text](docs/...) 的相对链接
- 校验目标是否存在；若不存在，优先在 docs/_archive 下按“同名文件”搜索归档路径，找到则替换
- 若仍找不到，回退替换为 docs/README.md（可选开关）

用法：
- 只扫描（dry-run）：python scripts/dev/check_docs_links.py
- 自动修复：python scripts/dev/check_docs_links.py --apply

注意：
- 默认对每个文件去重同一链接，仅统计一次
- 修改为原地覆盖写入 UTF-8
- 输出统计：缺失链接数量、已修复数量、回退数量
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
ARCHIVE = DOCS / "_archive"
README = "docs/README.md"

LINK_RE = re.compile(
    r"\]\((docs/[^)#]+)\)"
)  # 捕获 (... ) 内以 docs/ 开头的相对路径（含 md/json/txt 等）


def build_archive_index() -> dict[str, list[str]]:
    """建立归档索引：basename -> [relative_path_under_repo]
    例如：'会话快照_2025-08-19.md' -> ['docs/_archive/PLAYBOOKS/2025-08-19/会话快照_2025-08-19.md']
    """
    index: dict[str, list[str]] = {}
    if not ARCHIVE.exists():
        return index
    for p in ARCHIVE.rglob("*"):
        if p.is_file():
            rel = p.relative_to(ROOT).as_posix()
            name = p.name
            index.setdefault(name, []).append(rel)
    return index


def find_best_replacement(
    broken_path: str, archive_index: dict[str, list[str]]
) -> str | None:
    """根据同名文件在 _archive 下寻找替代路径，否则返回 None"""
    base = os.path.basename(broken_path)
    candidates = archive_index.get(base)
    if candidates:
        # 优先选择 reports 下的归档；如无，则选择第一个
        for c in candidates:
            if c.startswith("docs/_archive/reports/"):
                return c
        return candidates[0]
    return None


def scan_and_optionally_fix(
    apply: bool = False, fallback_to_readme: bool = True
) -> tuple[int, int, int]:
    """扫描并可选修复，返回：(缺失计数, 修复计数, 回退计数)"""
    archive_index = build_archive_index()
    missing_total = 0
    fixed_total = 0
    fallback_total = 0

    for md_path in DOCS.rglob("*.md"):
        try:
            text = md_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # 跳过非 UTF-8（如被错误命名或含 BOM 的特殊文件）
            continue
        links = {m.group(1) for m in LINK_RE.finditer(text)}
        # 过滤掉外链或非文件链接（已由正则限定 docs/）
        broken_links = [lk for lk in links if not (ROOT / lk).exists()]
        if not broken_links:
            continue
        missing_total += len(broken_links)

        if apply:
            new_text = text
            for bl in broken_links:
                repl = find_best_replacement(bl, archive_index)
                if repl and (ROOT / repl).exists():
                    new_text = new_text.replace(f"({bl})", f"({repl})")
                    fixed_total += 1
                    print(f"[修复] {md_path.relative_to(ROOT)}: {bl} -> {repl}")
                elif fallback_to_readme:
                    new_text = new_text.replace(f"({bl})", f"({README})")
                    fallback_total += 1
                    print(f"[回退] {md_path.relative_to(ROOT)}: {bl} -> {README}")
                else:
                    print(f"[缺失] {md_path.relative_to(ROOT)}: {bl} (未修复)")
            if new_text != text:
                md_path.write_text(new_text, encoding="utf-8")
        else:
            for bl in broken_links:
                repl = find_best_replacement(bl, archive_index)
                if repl and (ROOT / repl).exists():
                    print(f"[建议修复] {md_path.relative_to(ROOT)}: {bl} -> {repl}")
                else:
                    print(f"[建议回退] {md_path.relative_to(ROOT)}: {bl} -> {README}")

    return missing_total, fixed_total, fallback_total


def main():
    ap = argparse.ArgumentParser(description="扫描并修复 docs 内部相对链接")
    ap.add_argument("--apply", action="store_true", help="实际执行文件内替换")
    ap.add_argument(
        "--no-fallback", action="store_true", help="找不到归档目标时不回退到 README"
    )
    args = ap.parse_args()

    missing_total, fixed_total, fallback_total = scan_and_optionally_fix(
        apply=args.apply, fallback_to_readme=not args.no_fallback
    )
    print(f"统计: 缺失={missing_total}, 修复={fixed_total}, 回退={fallback_total}")
    # 退出码：若存在缺失但未 apply，则返回 1 以便 CI 提醒；apply 后即使有回退也返回 0
    import sys

    if not args.apply and missing_total > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
