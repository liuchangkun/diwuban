from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from app.services.ingest.check_mapping import check_mapping_paths

_act = logging.getLogger(__name__)


def _filter_clusters(report: Dict[str, Any]) -> Dict[str, Any]:
    def _flt(arr):
        return [x for x in (arr or []) if (x.get("missing_files", 0) > 0 or x.get("with_data_prefix", 0) > 0)]

    if "group_by_station" in report:
        report["group_by_station"] = _flt(report.get("group_by_station"))
    if "group_by_device" in report:
        report["group_by_device"] = _flt(report.get("group_by_device"))
    if "group_by_metric" in report:
        report["group_by_metric"] = _flt(report.get("group_by_metric"))
    return report


def run_check_mapping_command(settings, mapping_path: Path, out: Path | None, show_all: bool) -> Dict[str, Any]:
    """执行映射文件检查命令（CLI入口）。"""
    _act.info(
        "[流程-开始] [映射文件检查命令]",
        extra={
            "extra_data": {
                "mapping_path": str(mapping_path),
                "output_path": str(out) if out else None,
                "show_all": show_all,
            }
        },
    )

    try:
        report = check_mapping_paths(settings, mapping_path)
        if isinstance(report, dict) and not show_all:
            report = _filter_clusters(report)

        if out:
            import json as _json

            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(_json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            _act.info(
                "[流程-完成] [映射文件检查命令-报告已写入]",
                extra={"extra_data": {"output_path": str(out)}},
            )
            return {"ok": True, "written": str(out)}
        else:
            _act.info("[流程-完成] [映射文件检查命令]")
            return report if isinstance(report, dict) else {"ok": True, "report": report}

    except Exception as e:
        _act.error(
            "[流程-错误] [映射文件检查命令失败]",
            extra={
                "extra_data": {
                    "mapping_path": str(mapping_path),
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
            exc_info=True,
        )
        raise

