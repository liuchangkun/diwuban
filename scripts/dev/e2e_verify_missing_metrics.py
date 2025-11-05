# -*- coding: utf-8 -*-
"""
真实环境端到端验证脚本（缺失指标计算）
- 读取 configs/database.yaml 加载数据库配置
- 初始化连接池并选择一个具备基础原始数据的设备与时间窗
- 执行干跑（write_to_db=False）与实写（write_to_db=True）两轮验证
- 使用 SQL 验证写入结果，并输出 StatsCollector 统计

注意：
- 本脚本仅用于开发/预发布环境，请确保数据库连接指向安全环境。
- 若数据库不可达或无数据，将输出详细错误并以非零码退出。
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import os


import numpy as np  # type: ignore

# 项目根目录到路径
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.adapters.db import get_connection, init_database  # noqa: E402
from app.adapters.db.gateway import get_conn  # noqa: E402
from app.core.config.loader_new import load_settings  # noqa: E402
from app.core.logging.setup import init_logging, log_biz  # noqa: E402
from app.services.calculation.metric_mapper import metric_mapper  # noqa: E402
from app.services.calculation.orchestrator import CalculationOrchestrator  # noqa: E402


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _pick_candidate(settings) -> Tuple[int, int, datetime, datetime]:
    """选择一个具有基础原始数据的 (station_id, device_id) 和 1小时时间窗。
    策略：
    1) 先尝试最近1小时；若无，回退到最近24小时。
    2) 要求同时具备以下基础指标（存在原始值）：
       - main_pipeline_flow_rate
       - pump_active_power
       - pump_frequency
    """
    base_keys = [
        "main_pipeline_flow_rate",
        "pump_active_power",
        "pump_frequency",
    ]
    base_ids = metric_mapper.keys_to_ids(base_keys)
    if len(base_ids) < 3:
        raise RuntimeError(f"基础指标映射不足: {base_keys} -> {base_ids}")

    def _find_in_window(start: datetime, end: datetime) -> Optional[Tuple[int, int]]:
        sql = (
            """
            SELECT station_id, device_id
            FROM public.fact_measurements
            WHERE metric_id = ANY(%(metric_ids)s)
              AND ts_bucket >= %(start)s AND ts_bucket < %(end)s
            GROUP BY station_id, device_id
            HAVING COUNT(DISTINCT metric_id) >= 3
            ORDER BY COUNT(*) DESC
            LIMIT 1
            """
        )
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    {
                        "metric_ids": base_ids,
                        "start": start,
                        "end": end,
                    },
                )
                row = cur.fetchone()
                if row:
                    return int(row[0]), int(row[1])
                return None

    end = _now_utc().replace(microsecond=0)
    start = end - timedelta(hours=1)
    cand = _find_in_window(start, end)
    if cand:
        return cand[0], cand[1], start, end

    # 回退：近14天内按小时滑动窗口搜索（最多 14*24 次）
    end_day = end
    for i in range(14 * 24):
        w_end = end_day - timedelta(hours=i)
        w_start = w_end - timedelta(hours=1)
        cand = _find_in_window(w_start, w_end)
        if cand:
            return cand[0], cand[1], w_start, w_end

    raise RuntimeError("未找到满足条件的设备/时间窗（近14天内无完整基础数据）")


def _choose_metrics() -> List[str]:
    """确定测试指标列表：包含至少1个非循环指标与1个可能存在循环组的指标。
    采用保守集合：['pump_flow_rate', 'pump_head', 'pump_efficiency']。
    """
    return ["pump_flow_rate", "pump_head", "pump_efficiency"]


def _sql_count_written(device_id: int, metric_keys: List[str], start: datetime, end: datetime) -> Dict[str, int]:
    ids = metric_mapper.keys_to_ids(metric_keys)
    out: Dict[str, int] = {}
    if not ids:
        return {k: 0 for k in metric_keys}
    with get_connection() as conn:
        with conn.cursor() as cur:
            for key in metric_keys:
                mid = metric_mapper.key_to_id(key)
                if mid is None:
                    out[key] = 0
                    continue
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM public.fact_measurements
                    WHERE device_id=%s AND metric_id=%s AND ts_bucket >= %s AND ts_bucket < %s
                    """,
                    (int(device_id), int(mid), start, end),
                )
                out[key] = int(cur.fetchone()[0] or 0)
    return out


def main() -> int:
    # 初始化日志与配置
    init_logging("configs")
    settings = load_settings(Path("configs"))

    # 初始化数据库连接池
    init_database(settings)

    # 强制刷新 metric 映射
    metric_mapper.force_refresh()

    # 解析可选的命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="E2E 验证（缺失指标计算）")
    parser.add_argument("--station-id", type=int, default=None)
    parser.add_argument("--device-id", type=int, default=None)
    parser.add_argument("--start", type=str, default=None, help="ISO8601，支持+08:00或Z")
    parser.add_argument("--end", type=str, default=None, help="ISO8601，支持+08:00或Z")
    parser.add_argument("--metric", dest="metrics", action="append", default=None, help="可多次指定：目标指标 key，如 --metric pump_speed --metric pump_torque")
    args = parser.parse_args()

    # 选择候选 (station_id, device_id, window)
    if args.station_id and args.device_id and args.start and args.end:
        station_id = int(args.station_id)
        device_id = int(args.device_id)
        start = datetime.fromisoformat(args.start.replace("Z", "+00:00"))
        end = datetime.fromisoformat(args.end.replace("Z", "+00:00"))
    else:
        station_id, device_id, start, end = _pick_candidate(settings)

    # 指标列表
    metrics = args.metrics if args.metrics else _choose_metrics()

    # 过滤策略（用于排障/验证）：默认保持 orchestrator 缺省；提供环境变量开关
    fr = os.getenv('E2E_FILTER_RUNNING')
    fq = os.getenv('E2E_FILTER_QUALITY')
    filter_running = None if fr is None else (fr.strip().lower() in ('1','true','yes','on'))
    filter_quality = None if fq is None else (fq.strip().lower() in ('1','true','yes','on'))

    # 编排器实例与 StatsCollector 监控（通过替换类以便读取 flush 输出）
    import app.services.calculation.orchestrator as orch_mod

    class StatsCollectorSpy(orch_mod.StatsCollector):
        last: Optional[StatsCollectorSpy] = None  # type: ignore[name-defined]

        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            super().__init__(*args, **kwargs)
            StatsCollectorSpy.last = self

    orch_mod.StatsCollector = StatsCollectorSpy  # type: ignore[attr-defined]

    orchestrator = CalculationOrchestrator()

    # 干跑
    res_dry = orchestrator.calculate_missing_metrics(
        station_id=station_id,
        device_id=device_id,
        start_time=start.isoformat(),
        end_time=end.isoformat(),
        metrics=metrics,
        write_to_db=False,
        filter_running=filter_running,
        filter_quality=filter_quality,
    )

    # 实写
    res_write = orchestrator.calculate_missing_metrics(
        station_id=station_id,
        device_id=device_id,
        start_time=start.isoformat(),
        end_time=end.isoformat(),
        metrics=metrics,
        write_to_db=True,
        filter_running=filter_running,
        filter_quality=filter_quality,
    )

    # 统计输出
    stats = StatsCollectorSpy.last.flush() if StatsCollectorSpy.last else {}

    # SQL 验证写入
    written_counts = _sql_count_written(device_id, metrics, start, end)

    report = {
        "env": {
            "station_id": station_id,
            "device_id": device_id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "metrics": metrics,
        },
        "dry_run_result": res_dry,
        "write_result": res_write,
        "db_written_counts": written_counts,
        "stats_collector": stats,
        "timestamp": _now_utc().isoformat(),
    }

    # 输出报告文件
    out_dir = ROOT / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"e2e_missing_metrics_report_{_now_utc().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # 控制台摘要
    print("=== E2E 验证摘要 ===")
    print(json.dumps({
        "station_id": station_id,
        "device_id": device_id,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "metrics": metrics,
        "dry_success": bool(res_dry.get("success")),
        "write_success": bool(res_write.get("success")),
        "written_counts": written_counts,
        "stats_size": len(stats) if isinstance(stats, dict) else 0,
        "report_path": str(out_path),
    }, ensure_ascii=False))

    # 基本通过条件：干跑成功 + 写入后至少有一个指标写入>0
    if not res_dry.get("success"):
        log_biz("端到端验证", "失败", {"原因": "干跑失败"})
        return 2
    if sum(written_counts.values()) <= 0:
        log_biz("端到端验证", "失败", {"原因": "写入后未发现数据"})
        return 3

    log_biz("端到端验证", "完成", {"报告": str(out_path)})
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[E2E] 失败: {e}")
        sys.exit(1)

