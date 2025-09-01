# -*- coding: utf-8 -*-
"""
归档并清空 docs/reports 下的所有文件（中文注释）
- 将 docs/reports/**/* 迁移到 docs/_archive/reports/DELETED_YYYYMMDD/ 下（保留相对结构）
- 生成 TSV 映射清单：docs/_archive/reports/删除备份清单_YYYYMMDD.tsv
- 不删除任何历史归档；仅移动文件；最后清理空目录
用法：
  python scripts/dev/archive_and_clear_reports.py
"""
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "docs" / "reports"
ARCHIVE_BASE = ROOT / "docs" / "_archive" / "reports"
DATE = datetime.now().strftime("%Y%m%d")
DEST_ROOT = ARCHIVE_BASE / f"DELETED_{DATE}"
REPORT_TSV = ARCHIVE_BASE / f"删除备份清单_{DATE}.tsv"


def main():
    if not SRC.exists():
        print("[INFO] 源目录不存在，跳过：", SRC)
        return

    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    ARCHIVE_BASE.mkdir(parents=True, exist_ok=True)

    files_to_move = []
    # 仅移动文件，保留目录结构（相对 SRC）
    for dirpath, _, filenames in os.walk(SRC):
        for fn in filenames:
            p = Path(dirpath) / fn
            # 跳过已经是归档路径（理论不会）
            files_to_move.append(p)

    with REPORT_TSV.open("w", encoding="utf-8") as fw:
        fw.write("original_path\tnew_path\n")
        for src_p in files_to_move:
            rel = src_p.relative_to(SRC)
            dest_p = DEST_ROOT / rel
            dest_p.parent.mkdir(parents=True, exist_ok=True)
            fw.write(
                f"{src_p.relative_to(ROOT).as_posix()}\t{dest_p.relative_to(ROOT).as_posix()}\n"
            )
            # 执行移动
            dest_p.write_bytes(src_p.read_bytes())
            os.remove(src_p)

    # 尝试清理空目录
    for dirpath, dirnames, filenames in os.walk(SRC, topdown=False):
        if not dirnames and not filenames:
            try:
                Path(dirpath).rmdir()
            except OSError:
                pass

    print("[OK] 已归档并清空 docs/reports，映射清单：", REPORT_TSV.relative_to(ROOT))


if __name__ == "__main__":
    main()
