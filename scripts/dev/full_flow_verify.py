from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
import re

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn

ARTIFACT_SUMMARY = Path('.artifacts/run_all_summary.json')
LOG_DIR = Path('logs')


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def load_window() -> tuple[str, str]:
    # Prefer summary json
    if ARTIFACT_SUMMARY.exists():
        try:
            d = json.loads(ARTIFACT_SUMMARY.read_text(encoding='utf-8'))
            w = d.get('window') or {}
            if w.get('start') and w.get('end'):
                return w['start'], w['end']
        except Exception:
            pass
    # Fallback: parse anomaly_diagnosis.log last window_start/window_end
    f = LOG_DIR / 'anomaly_diagnosis.log'
    start_iso = end_iso = None
    if f.exists():
        lines = f.read_text(encoding='utf-8', errors='ignore').splitlines()
        for line in reversed(lines):
            if 'anomaly.window_end' in line and not end_iso:
                m = re.search(r'"起":\s*"([^"]+)".*?"止":\s*"([^"]+)"', line)
                if m:
                    start_iso, end_iso = m.group(1), m.group(2)
                    break
    if not (start_iso and end_iso):
        raise RuntimeError('无法确定时间窗口，请先运行 run-all 并生成 .artifacts/run_all_summary.json')
    return start_iso, end_iso


def parse_logs(run_id: str | None, start: str, end: str) -> dict:
    out = {"files": {}, "anomaly": {}, "errors": []}
    # List logs
    if LOG_DIR.exists():
        for p in LOG_DIR.glob('*'):
            if p.is_file():
                try:
                    size = p.stat().st_size
                    out['files'][p.name] = {"size": size}
                except Exception:
                    pass
    # anomaly log details
    an = LOG_DIR / 'anomaly_diagnosis.log'
    if an.exists():
        txt = an.read_text(encoding='utf-8', errors='ignore')
        lines = txt.splitlines()
        out['anomaly']['lines_total'] = len(lines)
        def find(pattern: str):
            return [l for l in lines if pattern in l]
        out['anomaly']['window_start'] = len(find('anomaly.window_start'))
        out['anomaly']['db_func_call'] = len([l for l in lines if 'sp_mark_quality_window_vfast_diag' in l])
        out['anomaly']['rule_summary'] = len(find('anomaly.rule_summary'))
        out['anomaly']['window_end'] = len(find('anomaly.window_end'))
        # slice by run_id
        if run_id:
            by_run = [l for l in lines if run_id in l]
            out['anomaly']['this_run'] = {
                'lines': len(by_run),
                'head': by_run[:2],
                'tail': by_run[-2:],
            }
    # error.log tail
    err = LOG_DIR / 'error.log'
    if err.exists():
        els = err.read_text(encoding='utf-8', errors='ignore').splitlines()
        out['errors'] = els[-10:]
    return out


def db_verify(start_iso: str, end_iso: str, run_id: str | None) -> dict:
    settings = load_settings(Path('configs'))
    start = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
    end = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
    out: dict[str, object] = {}
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # Total and marked
            cur.execute("""
                SELECT COUNT(*) FROM public.fact_measurements
                WHERE ts_bucket >= %s AND ts_bucket < %s
            """, (start, end))
            out['fact_rows_total_in_window'] = int(cur.fetchone()[0])

            cur.execute("""
                SELECT COUNT(*) FROM public.fact_measurements
                WHERE ts_bucket >= %s AND ts_bucket < %s AND COALESCE(quality_status,0) > 0
            """, (start, end))
            out['fact_rows_marked_in_window'] = int(cur.fetchone()[0])

            cur.execute("""
                SELECT COALESCE(quality_status,0) AS q, COUNT(*)
                FROM public.fact_measurements
                WHERE ts_bucket >= %s AND ts_bucket < %s
                GROUP BY COALESCE(quality_status,0)
                ORDER BY 1
            """, (start, end))
            out['fact_quality_dist'] = [{"quality_status": int(r[0]), "count": int(r[1])} for r in cur.fetchall() or []]

            # Sample abnormal rows
            cur.execute("""
                SELECT id, device_id, ts_bucket, quality_status, quality_type
                FROM public.fact_measurements
                WHERE ts_bucket >= %s AND ts_bucket < %s AND COALESCE(quality_status,0) > 0
                ORDER BY ts_bucket ASC
                LIMIT 5
            """, (start, end))
            out['fact_marked_samples'] = [
                {
                    'id': int(r[0]),
                    'device_id': int(r[1]) if r[1] is not None else None,
                    'ts_bucket': _iso(r[2]),
                    'quality_status': int(r[3]) if r[3] is not None else None,
                    'quality_type': r[4],
                }
                for r in (cur.fetchall() or [])
            ]

            # quality_profile_log summary
            cur.execute("""
                SELECT split_part(stage,'_',2) AS code, SUM(rows_affected)::bigint AS cnt
                FROM public.quality_profile_log
                WHERE window_start >= %s AND window_end <= %s AND stage LIKE 'update_%%'
                GROUP BY split_part(stage,'_',2)
                ORDER BY 1
            """, (start, end))
            out['quality_profile_summary'] = [
                {"code": int(r[0]), "count": int(r[1])}
                for r in (cur.fetchall() or [])
            ]

            # diagnosis log counts from DB (if table exists)
            try:
                if run_id:
                    cur.execute("""
                        SELECT stage, COUNT(*) FROM public.quality_diagnosis_log
                        WHERE window_start >= %s AND window_end <= %s AND run_id=%s
                        GROUP BY stage ORDER BY stage
                    """, (start, end, run_id))
                else:
                    cur.execute("""
                        SELECT stage, COUNT(*) FROM public.quality_diagnosis_log
                        WHERE window_start >= %s AND window_end <= %s
                        GROUP BY stage ORDER BY stage
                    """, (start, end))
                out['quality_diagnosis_log_by_stage'] = [
                    {"stage": r[0], "lines": int(r[1])} for r in (cur.fetchall() or [])
                ]
            except Exception as e:
                out['quality_diagnosis_log_by_stage_error'] = str(e)
    return out


def main() -> None:
    # Load summary
    summary = {}
    run_id = None
    if ARTIFACT_SUMMARY.exists():
        try:
            summary = json.loads(ARTIFACT_SUMMARY.read_text(encoding='utf-8'))
            qm = summary.get('quality_mark') or {}
            run_id = qm.get('run_id')
        except Exception:
            pass
    start_iso, end_iso = load_window()

    logs = parse_logs(run_id, start_iso, end_iso)
    db = db_verify(start_iso, end_iso, run_id)

    report = {
        'window': {'start': start_iso, 'end': end_iso},
        'run_id': run_id,
        'summary_snapshot': summary,
        'logs': logs,
        'db': db,
    }
    Path('.artifacts').mkdir(parents=True, exist_ok=True)
    Path('.artifacts/full_flow_verify_report.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

