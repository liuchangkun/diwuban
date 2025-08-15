import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOKS = ROOT / "docs" / "PLAYBOOKS"
INDEX = PLAYBOOKS / "INDEX.md"

FRONT_RE = re.compile(
    r"^---\s*$|^id:\s*(.*)$|^date:\s*(.*)$|^module:\s*(.*)$|^severity:\s*(.*)$|^impact:\s*(.*)$|^tags:\s*\[(.*)\]\s*$",
    re.IGNORECASE,
)


def parse_entries(md_path: Path):
    text = md_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    front = {}
    inside = False
    for line in text:
        if line.strip() == "---":
            inside = not inside
            continue
        if inside:
            m = FRONT_RE.match(line)
            if m:
                k = line.split(":", 1)[0].strip().lower()
                v = line.split(":", 1)[1].strip()
                front[k] = v
    return front


def main():
    entries = []
    for name in ("ERROR_FIX_LOG.md", "IMPROVEMENTS.md"):
        p = PLAYBOOKS / name
        if not p.exists():
            continue
        front = parse_entries(p)
        if front:
            entries.append((name, front))

    lines = [
        "# PLAYBOOKS INDEX",
        "",
        "> 该索引基于条目中的 Front Matter 粗略生成（可人工调整）",
        "",
    ]
    for name, front in entries:
        ident = front.get("id", "").strip()
        date = front.get("date", "").strip()
        module = front.get("module", "").strip()
        sev = front.get("severity", front.get("impact", "")).strip()
        tags = front.get("tags", "").strip()
        lines.append(f"- {date} [{ident}] {module} ({sev}) — {name} — {tags}")

    INDEX.write_text("\n".join(lines), encoding="utf-8")
    print(f"[INDEX] Updated {INDEX}")


if __name__ == "__main__":
    sys.exit(main())
