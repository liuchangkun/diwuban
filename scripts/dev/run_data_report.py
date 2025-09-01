from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# 将仓库根目录加入 sys.path，避免模块解析失败（兼容直接脚本运行）
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.adapters.logging.init import init_logging
from app.core.config.loader import Settings
from app.services.reporting.data_quality import generate_report


def main() -> None:
    # 解析参数：run_dir 可选
    import sys

    run_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("logs/runs/mcp_quickwin")
    run_dir.mkdir(parents=True, exist_ok=True)

    # 准备最小 env.json（写入 run_id 便于报告命名）
    env_path = run_dir / "env.json"
    if not env_path.exists():
        env_path.write_text(
            json.dumps({"run_id": "MCP_QUICKWIN_TEST"}, ensure_ascii=False),
            encoding="utf-8",
        )

    # 初始化设置与日志（确保 app.ndjson 存在并记录事件）
    settings = Settings()
    init_logging(settings, run_dir)

    # 选择一周窗口（与现有分区一致）
    start = datetime(2025, 8, 11, tzinfo=timezone.utc)
    end = datetime(2025, 8, 18, tzinfo=timezone.utc)

    out = generate_report(settings, start, end, run_dir=run_dir)

    # 回显核心信息（便于自动验证）
    reports_dir = (run_dir / ".." / "reports").resolve()
    report_files = []
    if reports_dir.exists():
        report_files = [p.name for p in reports_dir.glob("data_quality_report*.json")]

    app_log = run_dir / "app.ndjson"
    gen_count = miss_count = 0
    if app_log.exists():
        lines = app_log.read_text(encoding="utf-8").splitlines()
        gen_count = sum(
            1
            for l in lines
            if '"event":"data_report.generated"' in l
            or '"event": "data_report.generated"' in l
        )
        miss_count = sum(
            1
            for l in lines
            if '"event":"data_report.perf.missing"' in l
            or '"event": "data_report.perf.missing"' in l
        )

    print(
        json.dumps(
            {
                "run_dir": str(run_dir.resolve()),
                "reports_dir": str(reports_dir),
                "report_files": report_files,
                "events": {"generated": gen_count, "perf_missing": miss_count},
                "coverage_top_len": len(out.get("coverage_top", [])),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
