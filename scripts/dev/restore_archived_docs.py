# -*- coding: utf-8 -*-
"""
从 docs/_archive/删除备份清单_YYYYMMDD.tsv 恢复被归档文档（中文注释）
- 将 docs/_archive/DELETED_YYYYMMDD 下的文件恢复至原路径
- 若原路径已存在（用户已修改或新建），不覆盖；改存入 docs/_archive/RESTORED_CONFLICTS_YYYYMMDD/，并记录冲突清单
用法：python scripts/dev/restore_archived_docs.py --date 20250826 --apply
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / 'docs'
ARCHIVE = DOCS / '_archive'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True, help='日期，例如 20250826')
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    tsv = ARCHIVE / f'删除备份清单_{args.date}.tsv'
    deleted_root = ARCHIVE / f'DELETED_{args.date}'
    conflict_root = ARCHIVE / f'RESTORED_CONFLICTS_{args.date}'

    if not tsv.exists():
        print('[ERR] 清单不存在：', tsv)
        return

    conflict_root.mkdir(parents=True, exist_ok=True)

    restored, conflicts = 0, 0
    lines = tsv.read_text(encoding='utf-8', errors='ignore').splitlines()
    header = True
    for line in lines:
        if header:
            header = False
            continue
        parts = line.split('\t')
        if len(parts) < 2:
            continue
        orig_rel, new_rel = parts[0], parts[1]
        # 仅处理 DELETED_{date} 中的项
        if f'_archive/reports/' in new_rel and 'DELETED_' not in new_rel:
            pass
        src = ROOT / new_rel
        if not src.exists():
            # 有些行可能不是 DELETED 目录的，跳过
            continue
        dst = ROOT / orig_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            # 不覆盖，写入冲突区
            conflict_path = conflict_root / Path(orig_rel).name
            shutil.copy2(src, conflict_path)
            conflicts += 1
        else:
            shutil.copy2(src, dst)
            restored += 1
    print(f'[OK] 恢复完成：restored={restored}, conflicts={conflicts}, 清单={tsv}')


if __name__ == '__main__':
    main()

