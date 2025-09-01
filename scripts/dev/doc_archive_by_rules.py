# -*- coding: utf-8 -*-
"""
按规则归档并删除文档（中文注释）
- 扫描 docs/** 下 .md/.json/.txt（排除 _archive/assets/ADR/PLAYBOOKS）
- 规则：
  1) 文件名或正文命中关键词：['状态板','草案','计划','方案','报告','变更说明','完成报告']
  2) 未被核心索引引用（DOCS_KNOWLEDGE_INDEX.md、README.md、文档地图与导航.md）
- 满足上述至少其一时，归档到 docs/_archive/DELETED_YYYYMMDD/ 原相对路径下；生成 TSV 清单（含原因）
用法：python scripts/dev/doc_archive_by_rules.py --apply
"""
from __future__ import annotations
import argparse
import os
import re
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / 'docs'
EXCLUDES = {str((DOCS / '_archive').resolve()), str((DOCS / 'assets').resolve()), str((DOCS / 'ADR').resolve()), str((DOCS / 'PLAYBOOKS').resolve())}
DATE = datetime.now().strftime('%Y%m%d')
ARCHIVE_ROOT = DOCS / '_archive' / f'DELETED_{DATE}'
REPORT_TSV = DOCS / '_archive' / f'删除备份清单_{DATE}.tsv'

KEYWORDS = ['状态板','草案','计划','方案','报告','变更说明','完成报告']
INDEX_FILES = [DOCS / 'reports' / 'DOCS_KNOWLEDGE_INDEX.md', DOCS / 'README.md', DOCS / '文档地图与导航.md']
LINK_RE = re.compile(r"\]\((docs/[^)#]+)\)")


def is_excluded(p: Path) -> bool:
    return any(str(p.parent.resolve()).startswith(ex) for ex in EXCLUDES)


def is_indexed(target_rel: str, index_links: set[str]) -> bool:
    # target_rel 如 docs/xxx.md
    return target_rel in index_links


def gather_index_links() -> set[str]:
    links: set[str] = set()
    for idx in INDEX_FILES:
        if not idx.exists():
            continue
        text = idx.read_text(encoding='utf-8', errors='ignore')
        for m in LINK_RE.finditer(text):
            links.add(m.group(1))
    return links


def reasons_for(p: Path, index_links: set[str]) -> list[str]:
    rs: list[str] = []
    name = p.name
    if any(k in name for k in KEYWORDS):
        rs.append('关键词命中-文件名')
    try:
        text = p.read_text(encoding='utf-8')
        if any(k in text[:800] for k in KEYWORDS):  # 只看前800字符
            rs.append('关键词命中-正文')
    except Exception:
        pass
    rel = p.relative_to(ROOT).as_posix()
    if not is_indexed(rel, index_links):
        rs.append('未被索引引用')
    return rs


def collect_targets(index_links: set[str]) -> list[tuple[Path, list[str]]]:
    targets: list[tuple[Path, list[str]]] = []
    for dirpath, _, filenames in os.walk(DOCS):
        for fn in filenames:
            if not (fn.endswith('.md') or fn.endswith('.json') or fn.endswith('.txt')):
                continue
            p = Path(dirpath) / fn
            if is_excluded(p):
                continue
            rs = reasons_for(p, index_links)
            if rs:
                targets.append((p, rs))
    return targets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    index_links = gather_index_links()
    targets = collect_targets(index_links)

    print(f'[INFO] 候选文档数={len(targets)}')

    if not args.apply:
        for p, rs in targets:
            print(f'[CAND] {p.relative_to(ROOT)} | 原因={";".join(rs)}')
        return

    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    (DOCS / '_archive').mkdir(parents=True, exist_ok=True)

    with REPORT_TSV.open('a', encoding='utf-8') as fw:
        if not REPORT_TSV.exists() or REPORT_TSV.stat().st_size == 0:
            fw.write('original_path\tnew_path\treasons\n')
        moved = 0
        for p, rs in targets:
            rel = p.relative_to(DOCS)
            dest = ARCHIVE_ROOT / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            fw.write(f"{p.relative_to(ROOT).as_posix()}\t{dest.relative_to(ROOT).as_posix()}\t{';'.join(rs)}\n")
            # 移动（复制后删除）
            try:
                dest.write_bytes(p.read_bytes())
                p.unlink(missing_ok=True)
                moved += 1
            except Exception as e:
                print('[WARN] 移动失败', p, e)
    print(f'[OK] 已归档并删除 {moved} 个文档，清单：{REPORT_TSV.relative_to(ROOT)}')


if __name__ == '__main__':
    main()

