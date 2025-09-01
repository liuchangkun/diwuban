# -*- coding: utf-8 -*-
"""
文档去重与归档脚本（中文注释）
- 扫描 docs/** 下的 .md/.json/.txt（排除 docs/_archive/**、docs/assets/**、docs/ADR/**、docs/PLAYBOOKS/**）
- 计算内容哈希（忽略空白差异），聚类重复文件
- 对每组重复：保留第一份，其余移动到 docs/_archive/DELETED_YYYYMMDD/ 原相对路径下；生成 TSV 映射
- 不改动近似重复（仅完全相同内容处理）；执行后运行链接检查
用法：
  python scripts/dev/doc_dedup_and_archive.py [--apply]
"""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / 'docs'
EXCLUDES = {
    str((DOCS / '_archive').resolve()),
    str((DOCS / 'assets').resolve()),
    str((DOCS / 'ADR').resolve()),
    str((DOCS / 'PLAYBOOKS').resolve()),
}
DATE = datetime.now().strftime('%Y%m%d')
ARCHIVE_ROOT = DOCS / '_archive' / f'DELETED_{DATE}'
REPORT_TSV = DOCS / '_archive' / f'删除备份清单_{DATE}.tsv'


def is_excluded(p: Path) -> bool:
    rp = str(p.parent.resolve())
    return any(rp.startswith(ex) for ex in EXCLUDES)


def normalized_hash(content: bytes) -> str:
    # 归一化：去除 CRLF 差异与多余空白
    try:
        text = content.decode('utf-8', errors='ignore')
    except Exception:
        text = content.decode('latin1', errors='ignore')
    text = '\n'.join(line.rstrip() for line in text.replace('\r\n', '\n').split('\n')).strip()
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def collect_targets() -> list[Path]:
    targets = []
    for dirpath, _, filenames in os.walk(DOCS):
        for fn in filenames:
            if not (fn.endswith('.md') or fn.endswith('.json') or fn.endswith('.txt')):
                continue
            p = Path(dirpath) / fn
            if is_excluded(p):
                continue
            targets.append(p)
    return targets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='执行归档与删除')
    args = ap.parse_args()

    files = collect_targets()
    clusters: dict[str, list[Path]] = {}
    for p in files:
        try:
            h = normalized_hash(p.read_bytes())
        except Exception:
            continue
        clusters.setdefault(h, []).append(p)

    duplicates = [(h, paths) for h, paths in clusters.items() if len(paths) > 1]

    print(f'[INFO] 总文档数={len(files)}，重复簇={len(duplicates)}')

    if not args.apply:
        for _, paths in duplicates:
            keep = paths[0]
            for q in paths[1:]:
                print(f'[DUP] 保留 {keep.relative_to(ROOT)} | 归档 {q.relative_to(ROOT)}')
        return

    # apply
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    (DOCS / '_archive').mkdir(parents=True, exist_ok=True)
    with REPORT_TSV.open('a', encoding='utf-8') as fw:
        if REPORT_TSV.stat().st_size == 0:
            fw.write('original_path\tnew_path\n')
        for _, paths in duplicates:
            keep = paths[0]
            for q in paths[1:]:
                rel = q.relative_to(DOCS)
                dest = ARCHIVE_ROOT / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                fw.write(f"{q.relative_to(ROOT).as_posix()}\t{dest.relative_to(ROOT).as_posix()}\n")
                # 移动（复制后删除，避免跨卷问题）
                dest.write_bytes(q.read_bytes())
                q.unlink(missing_ok=True)
    print('[OK] 去重与归档完成，映射清单：', REPORT_TSV.relative_to(ROOT))


if __name__ == '__main__':
    main()

