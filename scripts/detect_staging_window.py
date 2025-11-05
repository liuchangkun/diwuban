from __future__ import annotations

import json
from pathlib import Path
from datetime import timezone

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main() -> None:
    settings = load_settings(Path("configs"))
    out: dict[str, object] = {}
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  MIN(to_timestamp(rtrim(replace(split_part(sr."DataTime", '.', 1), 'T', ' '), 'Z'), 'YYYY-MM-DD HH24:MI:SS')) AS ws,
                  MAX(to_timestamp(rtrim(replace(split_part(sr."DataTime", '.', 1), 'T', ' '), 'Z'), 'YYYY-MM-DD HH24:MI:SS')) AS we
                FROM public.staging_raw sr
                """
            )
            row = cur.fetchone()
            ws = row[0] if row else None
            we = row[1] if row else None
            if ws and we:
                # 与 orchestrator 一致：视为 UTC（存储时区=UTC），输出 Z 格式
                out["staging_window"] = {
                    "utc": {
                        "start": ws.replace(tzinfo=timezone.utc).isoformat(),
                        "end": we.replace(tzinfo=timezone.utc).isoformat(),
                    }
                }
            else:
                out["staging_window"] = None
    Path("reports").mkdir(parents=True, exist_ok=True)
    Path("reports/staging_window.detected.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()

