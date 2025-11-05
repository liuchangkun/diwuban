# -*- coding: utf-8 -*-
"""
清理 docs/PLAYBOOKS/对话记忆.md 中因 Git 编码/quotepath 导致的“\344\270...”样式转义乱码行：
- 删除形如：`  - "\344...` 的行（双引号+反斜杠开头的转义路径）
- 保留其他正常条目
执行后自动刷新 MEMORY_AUTO 区块。
"""
from __future__ import annotations

from pathlib import Path
import subprocess, sys

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "PLAYBOOKS" / "对话记忆.md"


def main() -> None:
    if not DOC.exists():
        print("[skip] 对话记忆不存在")
        return
    text = DOC.read_text(encoding="utf-8")
    lines = text.splitlines()
    cleaned = []
    removed = 0
    for ln in lines:
        if ln.startswith('  - "\\'):
            removed += 1
            continue
        cleaned.append(ln)
    if removed:
        DOC.write_text("\n".join(cleaned) + "\n", encoding="utf-8")
        print(f"[OK] 清理完成，移除乱码行 {removed} 条")
    else:
        print("[OK] 未发现需清理的乱码行")
    # 刷新 MEMORY_AUTO
    subprocess.call([sys.executable, str(ROOT / "scripts" / "dev" / "update_memory_index.py")], cwd=str(ROOT))
    subprocess.call([sys.executable, str(ROOT / "scripts" / "dev" / "compose_memory_snapshot.py")], cwd=str(ROOT))


if __name__ == "__main__":
    main()

