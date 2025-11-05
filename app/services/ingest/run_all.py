from __future__ import annotations

"""
端到端导入与合并（ingest.run_all）
流程：prepare_dim → create_staging → copy_from_mapping → merge_window
"""

import logging
from datetime import datetime
from pathlib import Path

from app.adapters.db.gateway import get_conn, get_staging_time_range
from app.services.ingest.copy_workers import copy_from_mapping
from app.services.ingest.create_staging import create_staging
from app.services.ingest.merge_service import merge_window
from app.services.ingest.prepare_dim import prepare_dim

_act = logging.getLogger(__name__)

# 为避免循环依赖，仅在类型检查时导入 Settings（loader_new 版本为最新配置定义）
try:  # pragma: no cover - 类型提示兼容
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from app.core.config.loader_new import Settings
except Exception:  # pragma: no cover
    pass


def run_all(
    settings: "Settings",
    mapping: Path,
    window_start_utc: datetime,
    window_end_utc: datetime,
    run_dir: Path | None = None,
    use_staging_time_range: bool = False,
) -> None:
    """执行端到端导入与合并。

    最小流程：
    1) 准备维表（prepare_dim）
    2) 创建 staging 表（create_staging）
    3) 可选：基于 staging_raw 实际数据更新时间窗口
    4) 导入（copy_from_mapping）
    5) 合并（merge_window）
    """
    _act.info(
        "[流程-开始] [端到端导入合并]",
        extra={
            "extra_data": {
                "mapping": str(mapping),
                "window_start_utc": window_start_utc.isoformat() if window_start_utc else None,
                "window_end_utc": window_end_utc.isoformat() if window_end_utc else None,
                "use_staging_time_range": use_staging_time_range,
            }
        },
    )

    try:
        # 1) 维表准备与 staging 表创建
        _act.info("[流程-阶段] [步骤1-准备维表]")
        prepare_dim(settings, mapping)
        _act.info("[流程-阶段] [步骤1完成]")

        _act.info("[流程-阶段] [步骤2-创建staging表]")
        create_staging(settings)
        _act.info("[流程-阶段] [步骤2完成]")

        # 2) 可选：从 staging_raw 检测实际时间范围并覆盖窗口
        if use_staging_time_range:
            _act.info("[流程-阶段] [步骤3-检测时间范围]")
            try:
                with get_conn(settings) as conn:
                    min_time, max_time, count = get_staging_time_range(
                        conn, settings.merge.tz.default_station_tz
                    )
                if count and min_time and max_time:
                    _act.info(
                        "[流程-阶段] [时间窗口已更新]",
                        extra={
                            "extra_data": {
                                "original_start": window_start_utc.isoformat() if window_start_utc else None,
                                "original_end": window_end_utc.isoformat() if window_end_utc else None,
                                "new_start": min_time.isoformat(),
                                "new_end": max_time.isoformat(),
                                "row_count": count,
                            }
                        },
                    )
                    window_start_utc = min_time
                    window_end_utc = max_time
                else:
                    _act.warning(
                        "[流程-跳过] [staging_raw无数据]",
                        extra={"extra_data": {"row_count": count}},
                    )
            except Exception as e:
                _act.warning(
                    "[流程-错误] [时间范围检测失败]",
                    extra={"extra_data": {"error": str(e)}},
                )

        # 3) 执行导入与合并
        _act.info("[流程-阶段] [步骤4-执行数据导入]")
        copy_from_mapping(settings, mapping)
        _act.info("[流程-阶段] [步骤4完成]")

        _act.info(
            "[流程-阶段] [步骤5-执行数据合并]",
            extra={
                "extra_data": {
                    "window_start_utc": window_start_utc.isoformat() if window_start_utc else None,
                    "window_end_utc": window_end_utc.isoformat() if window_end_utc else None,
                }
            },
        )
        merge_window(settings, window_start_utc, window_end_utc)
        _act.info("[流程-阶段] [步骤5完成]")

        _act.info("[流程-完成] [端到端导入合并]")

    except Exception as e:
        _act.error(
            "[流程-错误] [端到端导入合并失败]",
            extra={"extra_data": {"error": str(e), "error_type": type(e).__name__}},
            exc_info=True,
        )
        raise

    return None

