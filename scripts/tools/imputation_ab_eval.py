#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Imputation A/B evaluator (dry-run, read-only).
- Implements the confirmed Stage 1–5 evaluation flow in a minimal, testable way
- Two modes:
  1) --synthetic: generate in-memory multi-pump data and run A/B(C) to validate logic
  2) DB mode (default): scaffolded hooks to load real data via DB gateway (fill after wiring)
- Outputs per-run artifacts under logs/runs/imputation_ab_eval/<timestamp>/<group>/
  - summary.json: KPIs (pass/fail/fallback rates; residual distributions; gate rejections; correction magnitudes)
  - app.ndjson: step logs (event-based)

NOTE: DB mode only contains hooks to load; adjust SQL and mapping per deployment.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics as stats
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

# ensure project root (two levels up) on sys.path for 'app' imports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# optional overrides via environment for batch runs
FORCE_STATION_ID = int(os.environ.get("IMP_FORCE_STATION", "0") or "0")
FORCE_HOURS = int(os.environ.get("IMP_FORCE_HOURS", "1") or "1")

# ---------- Utilities ----------


def now_utc_iso() -> str:
    return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---------- Config (A/B/C groups) ----------
@dataclass
class GateCfg:
    r2_min: float = 0.70
    rmse_norm_max: float = 0.15
    conf_min: float = 0.70
    f_rel_tol: float = 0.10


@dataclass
class StageCfg:
    # Stage1 - B method
    W_d: int = 120  # seconds
    d_mad_abs: float = 5.0  # m3/h
    d_mad_rel: float = 0.05  # 5%
    # A method hysteresis
    f_enter_minus_exit_hz: float = 1.0
    p_exit_ratio: float = 0.9
    ema_alpha: float = 0.2
    # D/E fallback limits
    dq_rel_max: float = 0.10
    dq_abs_max: float = 15.0
    rqbal_soft_rel: float = 0.05
    rqbal_soft_abs: float = 20.0
    rqbal_hard_rel: float = 0.10
    rqbal_hard_abs: float = 40.0
    # Stage2
    jump_rel_max: float = 0.10
    jump_q_abs: float = 20.0
    jump_h_abs: float = 2.0
    jump_eta_abs: float = 0.10
    monotonic_violate_ratio: float = 0.40
    monotonic_l2_bound: float = 0.15


@dataclass
class GroupCfg:
    name: str
    stage: StageCfg
    gate: GateCfg


def make_group_cfg(group: str) -> GroupCfg:
    base = StageCfg()
    gate = GateCfg()
    if group.upper() == "B":
        # relaxed ~ +20%
        return GroupCfg(
            name="B_relaxed",
            stage=StageCfg(
                W_d=max(60, int(base.W_d * 0.8)),
                d_mad_abs=base.d_mad_abs * 1.2,
                d_mad_rel=base.d_mad_rel * 1.2,
                f_enter_minus_exit_hz=base.f_enter_minus_exit_hz + 0.5,
                p_exit_ratio=0.85,
                ema_alpha=base.ema_alpha,
                dq_rel_max=base.dq_rel_max * 1.2,
                dq_abs_max=base.dq_abs_max * 1.2,
                rqbal_soft_rel=base.rqbal_soft_rel * 1.2,
                rqbal_soft_abs=base.rqbal_soft_abs * 1.2,
                rqbal_hard_rel=base.rqbal_hard_rel * 1.2,
                rqbal_hard_abs=base.rqbal_hard_abs * 1.2,
                jump_rel_max=base.jump_rel_max * 1.2,
                jump_q_abs=base.jump_q_abs * 1.2,
                jump_h_abs=base.jump_h_abs * 1.2,
                jump_eta_abs=base.jump_eta_abs * 1.2,
                monotonic_violate_ratio=base.monotonic_violate_ratio,
                monotonic_l2_bound=base.monotonic_l2_bound * 1.2,
            ),
            gate=GateCfg(
                r2_min=gate.r2_min - 0.05,
                rmse_norm_max=gate.rmse_norm_max + 0.02,
                conf_min=gate.conf_min - 0.05,
                f_rel_tol=gate.f_rel_tol + 0.05,
            ),
        )
    elif group.upper() == "C":
        # tightened ~ -20%
        return GroupCfg(
            name="C_tight",
            stage=StageCfg(
                W_d=min(180, int(base.W_d * 1.2)),
                d_mad_abs=base.d_mad_abs * 0.8,
                d_mad_rel=base.d_mad_rel * 0.8,
                f_enter_minus_exit_hz=max(0.5, base.f_enter_minus_exit_hz - 0.5),
                p_exit_ratio=0.95,
                ema_alpha=base.ema_alpha,
                dq_rel_max=base.dq_rel_max * 0.8,
                dq_abs_max=base.dq_abs_max * 0.8,
                rqbal_soft_rel=base.rqbal_soft_rel * 0.8,
                rqbal_soft_abs=base.rqbal_soft_abs * 0.8,
                rqbal_hard_rel=base.rqbal_hard_rel * 0.8,
                rqbal_hard_abs=base.rqbal_hard_abs * 0.8,
                jump_rel_max=base.jump_rel_max * 0.8,
                jump_q_abs=base.jump_q_abs * 0.8,
                jump_h_abs=base.jump_h_abs * 0.8,
                jump_eta_abs=base.jump_eta_abs * 0.8,
                monotonic_violate_ratio=base.monotonic_violate_ratio,
                monotonic_l2_bound=base.monotonic_l2_bound * 0.8,
            ),
            gate=GateCfg(
                r2_min=gate.r2_min + 0.05,
                rmse_norm_max=max(0.05, gate.rmse_norm_max - 0.02),
                conf_min=gate.conf_min + 0.05,
                f_rel_tol=max(0.05, gate.f_rel_tol - 0.05),
            ),
        )
    else:
        return GroupCfg(name="A_default", stage=base, gate=gate)


# ---------- Synthetic data ----------
@dataclass
class PumpPoint:
    ts: datetime
    Q_total: float
    P: List[float]
    f: List[float]
    V: List[float]


def gen_synth(duration_s=3600, n_pumps=2, seed=42) -> List[PumpPoint]:
    random.seed(seed)
    start = datetime.utcnow().replace(tzinfo=timezone.utc)
    Q_total = 200.0
    V = [0.0 for _ in range(n_pumps)]
    out: List[PumpPoint] = []
    for i in range(duration_s):
        ts = start + timedelta(seconds=i)
        # introduce mild variations
        Qt = Q_total + 10 * math.sin(2 * math.pi * i / 600.0)
        f = [45 + 3 * math.sin(2 * math.pi * i / 500.0 + k) for k in range(n_pumps)]
        P = [
            30 + 5 * math.sin(2 * math.pi * i / 700.0 + 0.3 * k) for k in range(n_pumps)
        ]
        # simple proportional split
        w_raw = [P[k] * f[k] for k in range(n_pumps)]
        s = sum(w_raw) or 1.0
        Qi = [Qt * (w_raw[k] / s) for k in range(n_pumps)]
        for k in range(n_pumps):
            V[k] += Qi[k] / 3600.0  # m3/s integrated to m3
        out.append(PumpPoint(ts=ts, Q_total=Qt, P=P[:], f=f[:], V=V[:]))
    # inject gaps (missing segments) for evaluation
    # here we just tag them in summary; actual stage pipeline computes per-second
    return out


# ---------- Stage1: choose-by-jjjj for Q_i (B and A implemented) ----------
@dataclass
class Stage1Result:
    Q_hat: List[List[float]]  # per pump per second
    method: List[str]  # per second dominant method label
    rqbal: List[float]


def stage1_compute_Q(group: GroupCfg, series: List[PumpPoint]) -> Stage1Result:
    n = len(series)
    nP = len(series[0].P)
    # B method: derivative of cumulative V
    W = group.stage.W_d
    Qhat = [[0.0] * n for _ in range(nP)]
    method = ["B"] * n

    # prepare derivative using centered window linear fit (simple):
    # for edges, fallback to A method
    def deriv(sm: List[float], idx: int, W: int) -> float:
        # simple symmetric window slope
        half = max(1, W // 2)
        i0, i1 = max(0, idx - half), min(n - 1, idx + half)
        if i1 == i0:
            return 0.0
        dv = sm[i1] - sm[i0]
        dt = i1 - i0
        return dv / dt  # m3 per second

    # compute B
    for k in range(nP):
        V = [pt.V[k] for pt in series]
        for t in range(n):
            q_s = deriv(V, t, W)  # m3/s
            Qhat[k][t] = max(0.0, 3600.0 * q_s)

    # compute A (power×frequency share) as fallback or smoothing reference
    # weights
    w = []
    for t, pt in enumerate(series):
        raw = [pt.P[k] * pt.f[k] for k in range(nP)]
        s = sum(raw)
        if s <= 0:
            w.append([1.0 / nP] * nP)
        else:
            w.append([x / s for x in raw])

    # quality: r_Qbal
    rqbal = []
    for t, pt in enumerate(series):
        sum_Q = sum(Qhat[k][t] for k in range(nP))
        r = pt.Q_total - sum_Q
        # if derivative unstable (use abs residual & MAD threshold later), mark A
        rqbal.append(r)
        # simple instability rule: if any Qhat negative (shouldn't) or |r| too large -> use A
        if abs(r) > max(
            group.stage.rqbal_soft_abs, group.stage.rqbal_soft_rel * pt.Q_total
        ):
            # replace with A for this second
            for k in range(nP):
                Qhat[k][t] = max(0.0, pt.Q_total * w[t][k])
            method[t] = "A"
    return Stage1Result(Q_hat=Qhat, method=method, rqbal=rqbal)


# ---------- Stage2: physical checks (bounds + continuity clamp) ----------
@dataclass
class Stage2Result:
    Q_phys: List[List[float]]
    adjustments: Dict[str, int]


def stage2_phys(
    group: GroupCfg, series: List[PumpPoint], s1: Stage1Result
) -> Stage2Result:
    n = len(series)
    nP = len(series[0].P)
    Q = [[max(0.0, s1.Q_hat[k][t]) for t in range(n)] for k in range(nP)]
    changes = {"bounds": 0, "continuity": 0}
    # continuity clamp per pump
    for k in range(nP):
        last = Q[k][0]
        for t in range(1, n):
            pt = series[t]
            jump_max = min(
                group.stage.jump_q_abs, group.stage.jump_rel_max * max(1.0, pt.Q_total)
            )
            diff = Q[k][t] - last
            if abs(diff) > jump_max:
                Q[k][t] = last + (jump_max if diff > 0 else -jump_max)
                changes["continuity"] += 1
            last = Q[k][t]
    return Stage2Result(Q_phys=Q, adjustments=changes)


# ---------- Stage3: curve gate (guidance only, not changing values) ----------
@dataclass
class GateResult:
    used: bool
    pass_rate: float
    reasons: Dict[str, int]


def stage3_gate(group: GroupCfg, series: List[PumpPoint]) -> GateResult:
    # Placeholder: no curve in synthetic. Report as not used.
    return GateResult(used=False, pass_rate=0.0, reasons={"no_curve": len(series)})


# ---------- Stage4: fallback (not applied in synthetic; only counting) ----------
@dataclass
class Stage4Result:
    fallback_count: int


def stage4_fallback() -> Stage4Result:
    return Stage4Result(fallback_count=0)


# ---------- Summary ----------


def summarize(
    out_dir: Path,
    group: GroupCfg,
    series: List[PumpPoint],
    s1: Stage1Result,
    s2: Stage2Result,
    g3: GateResult,
    s4: Stage4Result,
) -> None:
    method_counts = {m: s1.method.count(m) for m in set(s1.method)}
    rq = [abs(x) for x in s1.rqbal]

    def pct(v: float, base: float) -> float:
        return (v / base * 100.0) if base > 0 else 0.0

    summary = {
        "group": group.name,
        "n_seconds": len(series),
        "methods": method_counts,
        "rqbal": {
            "p50": stats.median(rq) if rq else 0.0,
            "p90": (
                float(stats.quantiles(rq, n=10)[-1])
                if len(rq) >= 10
                else (max(rq) if rq else 0.0)
            ),
            "max": max(rq) if rq else 0.0,
        },
        "adjustments": s2.adjustments,
        "gate": {"used": g3.used, "pass_rate": g3.pass_rate, "reasons": g3.reasons},
        "fallback": {
            "count": s4.fallback_count,
            "rate": s4.fallback_count / len(series) if series else 0.0,
        },
        "generated_at": now_utc_iso(),
    }
    ensure_dir(out_dir)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2)
    )
    # minimal ndjson
    with (out_dir / "app.ndjson").open("w", encoding="utf-8") as f:
        for i, m in enumerate(s1.method):
            rec = {
                "ts": series[i].ts.isoformat(),
                "event": "method",
                "method": m,
                "rqbal": s1.rqbal[i],
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ---------- DB hooks (scaffold) ----------
# NOTE: left as placeholders to keep file concise and within 300 lines.


def load_series_db_stub() -> List[PumpPoint]:
    """Load 1-hour recent window from DB: pick a station with main_pipeline_flow_rate
    and 2-3 pumps having pump_active_power & pump_frequency. Use fn_training_timeseries_1s.
    Only reads; returns aligned PumpPoint list.
    """
    # Lazy imports to avoid hard deps when running synthetic
    from pathlib import Path as _Path

    from app.adapters.db.gateway import get_conn as _get_conn
    from app.core.config.loader_new import load_settings as _load_settings

    settings = _load_settings(_Path("configs"))
    end_utc = datetime.utcnow().replace(tzinfo=timezone.utc)
    start_utc = end_utc - timedelta(hours=1)

    def _find_latest_window(
        cur,
    ) -> Tuple[datetime, datetime, int, int, int, str] | None:
        # Pick latest station/device/metric_id whose metric_key looks like a main flow
        cur.execute(
            """
            SELECT d.station_id, fm.device_id, mc.id AS metric_id, mc.metric_key, MAX(fm.ts_bucket) AS max_ts
            FROM public.fact_measurements fm
            JOIN public.dim_metric_config mc ON mc.id=fm.metric_id
            JOIN public.dim_devices d ON d.id=fm.device_id
            WHERE mc.metric_key IN (
              'main_pipeline_flow_rate','main_outlet_flow_rate','pipeline_flow_rate',
              'group_flow_rate','total_flow_rate','main_pipe_flow'
            ) OR mc.metric_key ILIKE '%%flow%%'
            GROUP BY d.station_id, fm.device_id, mc.id, mc.metric_key
            ORDER BY max_ts DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        if not row:
            return None
        station_id = int(row[0])
        dev_id = int(row[1])
        metric_id = int(row[2])
        metric_key = str(row[3])
        max_ts = row[4]
        if max_ts is None:
            return None
        end_ts = max_ts
        start_ts = end_ts - timedelta(hours=1)
        return (start_ts, end_ts, station_id, dev_id, metric_id, metric_key)

    def _metric_id(cur, key: str) -> int | None:
        cur.execute(
            "SELECT id FROM public.dim_metric_config WHERE metric_key=%s LIMIT 1",
            (key,),
        )
        row = cur.fetchone()
        return int(row[0]) if row else None

    with _get_conn(settings) as conn:
        conn.execute("SET TIME ZONE 'UTC'")
        with conn.cursor() as cur:
            # 1) pick station + device for Q_total (main pipeline)
            # If forced station is provided via env, honor it; otherwise pick latest
            latest_mid = None
            if FORCE_STATION_ID > 0:
                station_id = FORCE_STATION_ID
                cur.execute(
                    """
                    SELECT fm.device_id, mc.id AS metric_id, MAX(fm.ts_bucket) AS max_ts
                    FROM public.fact_measurements fm
                    JOIN public.dim_metric_config mc ON mc.id=fm.metric_id
                    JOIN public.dim_devices d ON d.id=fm.device_id
                    WHERE d.station_id=%s
                      AND (mc.metric_key IN (
                        'main_pipeline_flow_rate','main_outlet_flow_rate','pipeline_flow_rate',
                        'group_flow_rate','total_flow_rate','main_pipe_flow'
                      ) OR mc.metric_key ILIKE '%%flow%%')
                    GROUP BY fm.device_id, mc.id
                    ORDER BY max_ts DESC
                    LIMIT 1
                    """,
                    (station_id,),
                )
                row = cur.fetchone()
                if not row or row[2] is None:
                    raise RuntimeError("Forced station has no flow-like metric in DB")
                qtotal_dev = int(row[0])
                latest_mid = int(row[1])
                end_utc = row[2]
                # window by FORCE_HOURS (>=1)
                hours = max(1, FORCE_HOURS)
                start_utc = end_utc - timedelta(hours=hours)
            else:
                # Prefer the latest available window; fall back to last 1h if available
                latest = _find_latest_window(cur)
                if latest:
                    (
                        start_utc,
                        end_utc,
                        station_id,
                        qtotal_dev,
                        latest_mid,
                        latest_key,
                    ) = latest
                else:
                    cur.execute(
                        """
                        SELECT d.station_id, fm.device_id, COUNT(*) AS cnt
                        FROM public.fact_measurements fm
                        JOIN public.dim_metric_config mc ON mc.id=fm.metric_id
                        JOIN public.dim_devices d ON d.id=fm.device_id
                        WHERE mc.metric_key='main_pipeline_flow_rate'
                          AND fm.ts_bucket >= %s AND fm.ts_bucket < %s
                        GROUP BY d.station_id, fm.device_id
                        ORDER BY cnt DESC
                        LIMIT 1
                        """,
                        (start_utc, end_utc),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise RuntimeError(
                            "No station with main_pipeline_flow_rate found in DB"
                        )
                    station_id, qtotal_dev = int(row[0]), int(row[1])

            # 2) select up to 3 pump devices in same station with P & f present
            cur.execute(
                """
                WITH base AS (
                  SELECT fm.device_id, mc.metric_key, COUNT(*) AS cnt
                  FROM public.fact_measurements fm
                  JOIN public.dim_metric_config mc ON mc.id=fm.metric_id
                  WHERE fm.ts_bucket >= %s AND fm.ts_bucket < %s AND fm.station_id=%s
                    AND mc.metric_key IN ('pump_active_power','pump_frequency','pump_cumulative_flow')
                  GROUP BY fm.device_id, mc.metric_key
                )
                SELECT b.device_id,
                       COALESCE(MAX(CASE WHEN metric_key='pump_active_power' THEN cnt END),0) AS c_p,
                       COALESCE(MAX(CASE WHEN metric_key='pump_frequency' THEN cnt END),0) AS c_f,
                       COALESCE(MAX(CASE WHEN metric_key='pump_cumulative_flow' THEN cnt END),0) AS c_v
                FROM base b
                GROUP BY b.device_id
                HAVING COALESCE(MAX(CASE WHEN metric_key='pump_active_power' THEN cnt END),0) > 0
                   AND COALESCE(MAX(CASE WHEN metric_key='pump_frequency' THEN cnt END),0) > 0
                ORDER BY (COALESCE(MAX(CASE WHEN metric_key='pump_active_power' THEN cnt END),0)
                       + COALESCE(MAX(CASE WHEN metric_key='pump_frequency' THEN cnt END),0)) DESC
                LIMIT 3
                """,
                (start_utc, end_utc, station_id),
            )
            pump_rows = cur.fetchall()
            if len(pump_rows) < 1:
                raise RuntimeError("No pumps with P & f in window for chosen station")
            device_ids = [int(r[0]) for r in pump_rows]

            # 3) resolve metric ids
            mid_qtotal = _metric_id(cur, "main_pipeline_flow_rate")
            mid_p = _metric_id(cur, "pump_active_power")
            mid_f = _metric_id(cur, "pump_frequency")
            mid_v = _metric_id(cur, "pump_cumulative_flow")
            if not (mid_qtotal and mid_p and mid_f):
                raise RuntimeError("Required metric ids missing in dim_metric_config")

            # 4) fetch Q_total series via fn_training_timeseries_1s
            cur.execute(
                "SELECT ts_bucket, value FROM public.fn_training_timeseries_1s(%s,%s,%s,%s,%s)",
                (station_id, qtotal_dev, mid_qtotal, start_utc, end_utc),
            )
            qtotal = [
                (r[0], float(r[1]) if r[1] is not None else None)
                for r in cur.fetchall()
            ]
            ts_axis = [t for (t, _) in qtotal]
            n = len(ts_axis)

            # helpers to pull per-device metric series
            def pull_series(dev: int, mid: int) -> List[float | None]:
                cur.execute(
                    "SELECT ts_bucket, value FROM public.fn_training_timeseries_1s(%s,%s,%s,%s,%s)",
                    (station_id, dev, mid, start_utc, end_utc),
                )
                rows = cur.fetchall()
                vals = {r[0]: (float(r[1]) if r[1] is not None else None) for r in rows}
                return [vals.get(ts) for ts in ts_axis]

            # 5) build PumpPoint list
            P_mat: List[List[float]] = []
            F_mat: List[List[float]] = []
            V_mat: List[List[float]] = []
            for dev in device_ids:
                p_seq = pull_series(dev, mid_p)
                f_seq = pull_series(dev, mid_f)
                v_seq = pull_series(dev, mid_v) if mid_v else [None] * n
                # fill None with 0 to keep shapes; Stage1 will fallback via rqbal check
                P_mat.append([float(x) if x is not None else 0.0 for x in p_seq])
                F_mat.append([float(x) if x is not None else 0.0 for x in f_seq])
                V_cum = 0.0
                vec_v = []
                for x in v_seq:
                    if x is None:
                        V_cum += 0.0
                    else:
                        V_cum = float(x)
                    vec_v.append(V_cum)
                V_mat.append(vec_v)

            out: List[PumpPoint] = []
            for i, ts in enumerate(ts_axis):
                Qt = float(qtotal[i][1]) if qtotal[i][1] is not None else 0.0
                P_row = [P_mat[k][i] for k in range(len(device_ids))]
                F_row = [F_mat[k][i] for k in range(len(device_ids))]
                V_row = [V_mat[k][i] for k in range(len(device_ids))]
                out.append(PumpPoint(ts=ts, Q_total=Qt, P=P_row, f=F_row, V=V_row))
            return out


# ---------- CLI ----------


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Imputation A/B evaluator (dry-run)")
    ap.add_argument(
        "--group",
        choices=["A", "B", "C"],
        default="A",
        help="A=default, B=relaxed, C=tight",
    )
    ap.add_argument("--synthetic", action="store_true", help="Run with synthetic data")
    ap.add_argument(
        "--duration", type=int, default=3600, help="Synthetic duration seconds"
    )
    ap.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output directory (default logs/runs/imputation_ab_eval/<ts>/<group>)",
    )
    ap.add_argument(
        "--stations", type=int, nargs="*", help="可选：限制站点ID列表（不填则自动选择）"
    )
    ap.add_argument("--hours", type=int, default=1, help="窗口小时数，默认1h")
    ap.add_argument(
        "--runs", type=int, default=3, help="自动评估站点数量（自动选择时生效），默认3"
    )
    return ap.parse_args()


def main():
    args = parse_args()
    group = make_group_cfg(args.group)
    ts_tag = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base_out = (
        Path(args.out)
        if args.out
        else Path("logs/runs/imputation_ab_eval") / ts_tag / group.name
    )
    ensure_dir(base_out)

    if args.synthetic:
        series = gen_synth(duration_s=max(60, args.duration))
        s1 = stage1_compute_Q(group, series)
        s2 = stage2_phys(group, series, s1)
        g3 = stage3_gate(group, series)
        s4 = stage4_fallback()
        summarize(base_out, group, series, s1, s2, g3, s4)
        print(f"A/B eval (group {group.name}) finished. See {base_out}")
        return

    # DB mode: single-run for now; batch selection can be added via external orchestrator
    series = load_series_db_stub()
    s1 = stage1_compute_Q(group, series)
    s2 = stage2_phys(group, series, s1)
    g3 = stage3_gate(group, series)
    s4 = stage4_fallback()
    summarize(base_out, group, series, s1, s2, g3, s4)
    print(f"A/B eval (group {group.name}) finished. See {base_out}")


if __name__ == "__main__":
    main()
