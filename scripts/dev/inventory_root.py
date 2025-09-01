# -*- coding: utf-8 -*-
"""
项目根目录盘点脚本（中文注释）
- 统计扩展名分布（数量/体量）
- 顶层目录聚合（数量/体量）
- TOPN 大文件
- 最近/久未修改文件
使用：
  python scripts/dev/inventory_root.py --root . --top 30
"""
from __future__ import annotations
import argparse
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Dict, Tuple

EXCLUDE_DIR_NAMES = {".git", "node_modules", "venv", ".venv", "__pycache__"}


@dataclass
class FileInfo:
    path: Path
    size: int
    mtime: float


def iter_files(root: Path) -> Iterable[FileInfo]:
    for dirpath, dirnames, filenames in os.walk(root):
        # 过滤排除目录
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIR_NAMES]
        for fn in filenames:
            p = Path(dirpath) / fn
            try:
                st = p.stat()
            except OSError:
                continue
            yield FileInfo(path=p, size=st.st_size, mtime=st.st_mtime)


def human_mb(nbytes: int) -> float:
    return round(nbytes / (1024 * 1024.0), 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="根目录")
    ap.add_argument("--top", type=int, default=30, help="TOPN 数量")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    files = list(iter_files(root))

    # 扩展名分布
    by_ext: Dict[str, Tuple[int, int]] = {}
    for fi in files:
        ext = fi.path.suffix.lower() or "(无扩展)"
        cnt, total = by_ext.get(ext, (0, 0))
        by_ext[ext] = (cnt + 1, total + fi.size)

    # 顶层目录聚合
    by_top: Dict[str, Tuple[int, int]] = {}
    for fi in files:
        rel = fi.path.as_posix().replace(root.as_posix() + "/", "")
        first = rel.split("/", 1)[0] if "/" in rel else "."
        cnt, total = by_top.get(first, (0, 0))
        by_top[first] = (cnt + 1, total + fi.size)

    # TOPN 大文件
    topN = sorted(files, key=lambda f: f.size, reverse=True)[: args.top]

    # 最近/久未修改文件
    recentN = sorted(files, key=lambda f: f.mtime, reverse=True)[: args.top]
    staleN = sorted(files, key=lambda f: f.mtime)[: args.top]

    # 输出 Markdown
    print(f"# 根目录盘点报告（{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}）\n")
    print(f"根目录: {root}\n文件总数: {len(files)}\n")

    print("## 扩展名分布（TOP 30 按数量）")
    for ext, (cnt, total) in sorted(
        by_ext.items(), key=lambda x: x[1][0], reverse=True
    )[:30]:
        print(f"- {ext}: {cnt} 个，合计 {human_mb(total)} MB")

    print("\n## 顶层目录聚合（按体量降序）")
    for d, (cnt, total) in sorted(by_top.items(), key=lambda x: x[1][1], reverse=True):
        print(f"- {d}: {cnt} 个文件，{human_mb(total)} MB")

    print("\n## TOP 大文件")
    for fi in topN:
        rel = fi.path.relative_to(root).as_posix()
        print(
            f"- {rel} | {human_mb(fi.size)} MB | {datetime.fromtimestamp(fi.mtime).strftime('%Y-%m-%d %H:%M:%S')}"
        )

    print("\n## 最近修改")
    for fi in recentN:
        rel = fi.path.relative_to(root).as_posix()
        print(
            f"- {datetime.fromtimestamp(fi.mtime).strftime('%Y-%m-%d %H:%M:%S')} | {rel} | {human_mb(fi.size)} MB"
        )

    print("\n## 久未修改")
    for fi in staleN:
        rel = fi.path.relative_to(root).as_posix()
        print(
            f"- {datetime.fromtimestamp(fi.mtime).strftime('%Y-%m-%d %H:%M:%S')} | {rel} | {human_mb(fi.size)} MB"
        )


if __name__ == "__main__":
    main()
