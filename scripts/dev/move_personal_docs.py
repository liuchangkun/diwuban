# -*- coding: utf-8 -*-
"""
移动 ProjectDocs个人说明/** 到 docs/_archive/personal/** 并生成 TSV 映射清单。
安全策略：
- 仅移动文件，不删除源目录；若目录为空可手动清理
- 生成映射清单：docs/_archive/reports/迁移备份清单_YYYYMMDD.tsv
- 保持原始相对层级结构
用法：
  python scripts/dev/move_personal_docs.py
"""
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "ProjectDocs个人说明"
DEST = ROOT / "docs" / "_archive" / "personal"
REPORT_DIR = ROOT / "docs" / "_archive" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
MAP_FILE = REPORT_DIR / f"迁移备份清单_{datetime.now().strftime('%Y%m%d')}.tsv"


def main():
    if not SRC.exists():
        print("[INFO] 源目录不存在，跳过：", SRC)
        return

    DEST.mkdir(parents=True, exist_ok=True)

    with MAP_FILE.open("w", encoding="utf-8") as fw:
        fw.write("original_path\tnew_path\n")
        for dirpath, _, filenames in os.walk(SRC):
            for fn in filenames:
                src_p = Path(dirpath) / fn
                rel = src_p.relative_to(SRC)
                dst_p = DEST / rel
                dst_p.parent.mkdir(parents=True, exist_ok=True)
                fw.write(
                    f"{src_p.relative_to(ROOT).as_posix()}\t{dst_p.relative_to(ROOT).as_posix()}\n"
                )
                # 执行移动
                dst_p.write_bytes(src_p.read_bytes())
                os.remove(src_p)
    print("[OK] 映射清单: ", MAP_FILE.relative_to(ROOT))


if __name__ == "__main__":
    main()
