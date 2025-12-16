from __future__ import annotations

from pathlib import Path
import re


FIELD_MAP = {
    "mapping": "映射关系",
    "use_staging_time_range": "使用临时时间范围",
    "window_start": "窗口开始时间",
    "window_end": "窗口结束时间",
    "stage": "处理阶段",
    "stations_count": "站点数量",
    "devices_count": "设备数量",
    "metrics_count": "指标数量",
    "granularity": "时间粒度",
    "step_seconds": "步长秒数",
    "parallel_enabled": "并行处理启用状态",
    "max_workers": "最大工作线程数",
    "table": "数据表",
    "index_name": "索引名称",
    "blocks_total": "总块数",
    "blocks_done": "已完成块数",
    "progress_pct": "完成百分比",
}


PATTERNS = {
    key: re.compile(rf'"{re.escape(key)}"\s*:') for key in FIELD_MAP.keys()
}


def translate_line(line: str) -> str:
    idx = line.find("{")
    if idx == -1:
        return line
    head = line[:idx]
    body = line[idx:]
    for key, pattern in PATTERNS.items():
        body = pattern.sub(f'"{FIELD_MAP[key]}":', body)
    return head + body


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    input_path = root / "logs" / "app.log"
    output_path = root / "logs" / "app_zh.log"

    if not input_path.exists():
        raise SystemExit(f"日志文件不存在: {input_path}")

    content = input_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines(keepends=True)
    translated = [translate_line(line) for line in lines]
    output_path.write_text("".join(translated), encoding="utf-8")
    print(f"已生成中文日志文件: {output_path}")


if __name__ == "__main__":
    main()

