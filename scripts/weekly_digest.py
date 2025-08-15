import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOKS = ROOT / "docs" / "PLAYBOOKS"
DIGEST_DIR = PLAYBOOKS / "DIGEST"
DIGEST_DIR.mkdir(parents=True, exist_ok=True)

FRONT_RE = re.compile(r"^---\s*$|^id:\s*(.*)$|^date:\s*(.*)$|^module:\s*(.*)$|^severity:\s*(.*)$|^impact:\s*(.*)$|^tags:\s*\[(.*)\]\s*$", re.IGNORECASE)

def parse_entries(md_path: Path):
    text = md_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    entries = []
    block = []
    inside = False
    for line in text:
        if line.strip() == "---":
            inside = not inside
            if not inside and block:
                entries.append(block)
                block = []
            continue
        if inside:
            block.append(line)
    # parse simple key: value pairs
    parsed = {}
    for line in block:
        if ":" in line:
            k, v = line.split(":", 1)
            parsed[k.strip().lower()] = v.strip()
    return parsed


def main():
    today = dt.date.today()
    iso_year, iso_week, _ = today.isocalendar()
    target = DIGEST_DIR / f"{iso_year}-{iso_week:02d}.md"

    rows = ["# Weekly Digest", f"> Week {iso_year}-{iso_week:02d}", ""]
    for name in ("ERROR_FIX_LOG.md", "IMPROVEMENTS.md"):
        p = PLAYBOOKS / name
        if not p.exists():
            continue
        entry = parse_entries(p)
        if not entry:
            continue
        ident = entry.get("id", "")
        date = entry.get("date", "")
        module = entry.get("module", "")
        sev = entry.get("severity", entry.get("impact", ""))
        tags = entry.get("tags", "")
        rows.append(f"- {date} [{ident}] {module} ({sev}) — {name} — {tags}")

    target.write_text("\n".join(rows), encoding="utf-8")
    print(f"[DIGEST] Updated {target}")


if __name__ == "__main__":
    sys.exit(main())

