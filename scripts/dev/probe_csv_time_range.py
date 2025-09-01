from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from zoneinfo import ZoneInfo

# 为可导入 app 包，加入仓库根目录
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.core.config.loader import load_settings  # noqa: E402

LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def iter_mapping_files(mapping_path: Path) -> Iterable[Path]:
    data = json.loads(mapping_path.read_text(encoding="utf-8"))
    for s in data.get("stations") or []:
        for d in s.get("devices") or []:
            for m in d.get("metrics") or []:
                for f in m.get("files") or []:
                    yield Path(str(f))


def parse_dt_to_utc_hour(s: str) -> str | None:
    if not s:
        return None
    t = s.strip().replace("/", "-")
    # 取前19位，形如 YYYY-MM-DD HH:MM:SS
    if len(t) >= 19:
        t = t[:19]
    try:
        dt_local = datetime.strptime(t, "%Y-%m-%d %H:%M:%S").replace(tzinfo=LOCAL_TZ)
    except Exception:
        return None
    dt_utc = dt_local.astimezone(timezone.utc)
    hour_utc = dt_utc.replace(minute=0, second=0, microsecond=0)
    return hour_utc.isoformat().replace("+00:00", "Z")


def main() -> None:
    s = load_settings(Path("config"))
    base_dir = Path(s.ingest.base_dir)
    mapping_path = Path("configs/data_mapping.v2.json")  # 路径已统一到 configs/ 目录

    hour_counter: Counter[str] = Counter()
    total_rows = 0

    for rel in iter_mapping_files(mapping_path):
        # 映射文件中的路径可能为相对路径（统一正斜杠），这里用 base_dir 拼接
        p = base_dir / rel
        if not p.exists():
            # 忽略缺失文件
            continue
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                continue
            # 找 DataTime 列（大小写兼容）
            try:
                idx_dt = [
                    i
                    for i, h in enumerate(header)
                    if str(h).strip().lower() == "datetime"
                ][0]
            except Exception:
                # 找不到 DataTime 列，跳过此文件
                continue
            for row in reader:
                if idx_dt >= len(row):
                    continue
                hour = parse_dt_to_utc_hour(row[idx_dt])
                if hour:
                    hour_counter[hour] += 1
                    total_rows += 1
    if not hour_counter:
        print("NO_DATA")
        return

    top_hour, cnt = hour_counter.most_common(1)[0]
    # 解析 top_hour 回 datetime
    dt_start = datetime.fromisoformat(top_hour.replace("Z", "+00:00"))
    dt_end = dt_start + timedelta(hours=1)

    out_dir = Path("logs/runs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = {
        "HOUR_UTC": top_hour,
        "ROWS": cnt,
        "WINDOW_UTC_START": dt_start.isoformat().replace("+00:00", "Z"),
        "WINDOW_UTC_END": dt_end.isoformat().replace("+00:00", "Z"),
        "TOTAL_ROWS_SCANNED": total_rows,
    }
    out_path = out_dir / "window_probe.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
