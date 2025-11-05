from __future__ import annotations

import logging
from datetime import datetime as _dt
from typing import Any, Dict, Optional

from app.adapters.db.gateway import get_conn
from app.core.time_utils import format_for_display

_anom_logger = logging.getLogger("anomaly")
_act = logging.getLogger("activity")


# 统一对外时间格式：使用 app.core.time_utils.format_for_display
# 已删除重复的 _fmt_local_str 函数，直接使用统一的时间格式化函数


def mark_quality_window(
    settings,
    start: str,
    end: str,
    station_id: Optional[int],
    device_id: Optional[int],
    codes: Optional[list[int]] = None,
    diag_level: str | None = None,
    run_id: str | None = None,
) -> Dict[str, Any]:
    """质量打标（窗口级）。
    - 新增：anomaly.window_start/end 事件与 db.func 摘要；预留 p_diag_level（方案B）。
    """
    s_dt = _dt.fromisoformat(start.replace("Z", "+00:00"))
    _act.info(
        "[流程-开始] [质量窗口标注]",
        extra={
            "extra_data": {
                "window_start": format_for_display(_dt.fromisoformat(start.replace("Z", "+00:00")), settings) if start else None,
                "window_end": format_for_display(_dt.fromisoformat(end.replace("Z", "+00:00")), settings) if end else None,
                "station_id": station_id,
                "device_id": device_id,
                "codes": codes,
                "diag_level": diag_level,
            }
        },
    )

    e_dt = _dt.fromisoformat(end.replace("Z", "+00:00"))

    # 若 orchestrator 传入 run_id 则沿用；否则本地生成
    if not run_id:
        try:
            import uuid as _uuid

            run_id = _uuid.uuid4().hex
        except Exception:
            run_id = None

    # 注入 run_id 到日志上下文，便于全链路日志关联
    try:
        if run_id:
            from app.core.logging.setup import set_context  # local import

            set_context(
                request_id=run_id,
                trace_id=run_id,
                user_id="system",
                tenant="diag",
            )
    except Exception:
        pass
    # 文件侧阶段日志：window_start（服务层直接落盘）与 app 里程碑
    try:
        _anom_logger.info(
            "[DIAG][window_start] 开始质量标注",
            extra={
                "extra_data": {
                    "类型": "诊断",
                    "阶段": "window_start",
                    "窗口": {
                        "start": format_for_display(_dt.fromisoformat(start.replace("Z", "+00:00")), settings) if start else None,
                        "end": format_for_display(_dt.fromisoformat(end.replace("Z", "+00:00")), settings) if end else None
                    },
                    "设备": device_id,
                    "diag_level": diag_level,
                    "codes": codes,
                    "run_id": run_id,
                }
            },
        )
    except Exception:
        pass
    try:
        logging.getLogger("app").info(
            "[ACT] mark_quality_window start",
            extra={
                "extra_data": {
                    "window": {
                        "start": format_for_display(_dt.fromisoformat(start.replace("Z", "+00:00")), settings) if start else None,
                        "end": format_for_display(_dt.fromisoformat(end.replace("Z", "+00:00")), settings) if end else None
                    },
                    "device_id": device_id,
                    "run_id": run_id,
                }
            },
        )
    except Exception:
        pass

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 过程新增 p_codes 可选参数，NULL 表示全量规则；当启用诊断时优先尝试调用 _vfast_diag 包装过程
            sql5 = (
                "CALL public.sp_mark_quality_window_vfast("
                "%s::timestamptz,%s::timestamptz,"
                "%s::bigint,%s::bigint,%s::int[])"
            )
            sql6_diag = (
                "CALL public.sp_mark_quality_window_vfast_diag("
                "%s::timestamptz,%s::timestamptz,"
                "%s::bigint,%s::bigint,"
                "%s::int[],%s::text,%s::text)"
            )
            t0 = _dt.now()
            used_proc = "public.sp_mark_quality_window_vfast"
            try:
                use_diag = bool(diag_level) and (
                    str(diag_level).lower()
                    not in (
                        "off",
                        "none",
                        "0",
                        "false",
                        "",
                        "no",
                        "n",
                    )
                )
                if use_diag:
                    try:
                        # 防御式：调用诊断前先回滚一次，清理潜在 aborted 状态
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        # 设置 application_name，便于DB侧记录会话来源与运行ID
                        try:
                            cur.execute(
                                "SET application_name = %s",
                                (f"quality_mark run_id={run_id}",),
                            )
                        except Exception:
                            pass
                        # 独立连接 + 自动提交 调用包装过程，确保其日志可持久化且不污染回退路径
                        import app.adapters.db.gateway as _gw

                        try:
                            with _gw.get_conn(settings) as dconn:
                                try:
                                    dconn.rollback()
                                except Exception:
                                    pass
                                try:
                                    dconn.autocommit = True
                                except Exception:
                                    pass
                                with dconn.cursor() as dcur:
                                    try:
                                        dcur.execute(
                                            "SET application_name = %s",
                                            (f"quality_mark run_id={run_id}",),
                                        )
                                    except Exception:
                                        pass
                                    try:
                                        dcur.execute(
                                            sql6_diag,
                                            (
                                                s_dt,
                                                e_dt,
                                                station_id,
                                                device_id,
                                                codes,
                                                str(diag_level),
                                                run_id,
                                            ),
                                        )
                                    except Exception as _call_err:
                                        _msg = str(_call_err)
                                        _state = getattr(
                                            _call_err,
                                            "sqlstate",
                                            None,
                                        )
                                        if (_state == "42883") or (
                                            "does not exist" in _msg
                                        ):
                                            # 缺少包装过程：在线创建日志表与包装过程后重试（一次）
                                            _ddl_tbl = (
                                                "CREATE TABLE IF NOT EXISTS public.quality_diagnosis_log ("
                                                " id bigserial PRIMARY KEY, created_at timestamptz NOT NULL DEFAULT now(),"
                                                " window_start timestamptz NOT NULL, window_end timestamptz NOT NULL,"
                                                " station_id bigint NULL, device_id bigint NULL, stage text NOT NULL,"
                                                " level text NOT NULL DEFAULT 'INFO', message text NULL, detail jsonb NULL,"
                                                " diag_level text NOT NULL DEFAULT 'off', run_id text NULL )"
                                            )
                                            dcur.execute(_ddl_tbl)
                                            _ddl_proc = r"""
CREATE OR REPLACE PROCEDURE public.sp_mark_quality_window_vfast_diag(
  IN p_start      timestamptz,
  IN p_end        timestamptz,
  IN p_station_id bigint DEFAULT NULL,
  IN p_device_id  bigint DEFAULT NULL,
  IN p_codes      int[]  DEFAULT NULL,
  IN p_diag_level text   DEFAULT 'off',
  IN p_run_id     text   DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_t timestamptz;
  v_dur_ms numeric;
  v_level text;
  v_app text;
  v_tz text;
  v_rows_scanned bigint;
  r_rec record;
  v_code int;
  v_cnt bigint;
  v_failed boolean := false;
BEGIN
  v_level := lower(COALESCE(p_diag_level, 'off'));
  v_app := current_setting('application_name', true);
  v_tz := current_setting('TimeZone', true);

  IF v_level <> 'off' THEN
    INSERT INTO public.quality_diagnosis_log(window_start, window_end, station_id, device_id, stage, level, message, detail, diag_level, run_id)
    VALUES(
      p_start, p_end, p_station_id, p_device_id,
      'window_start', 'INFO', '开始质量标注',
      jsonb_build_object(
        '启用质量码', p_codes,
        '时区', v_tz,
        '应用', v_app
      ),
      v_level, p_run_id
    );
  END IF;

  v_t := clock_timestamp();
  BEGIN
    CALL public.sp_mark_quality_window_vfast(p_start, p_end, p_station_id, p_device_id, p_codes);
  EXCEPTION WHEN OTHERS THEN
    IF v_level <> 'off' THEN
      INSERT INTO public.quality_diagnosis_log(window_start, window_end, station_id, device_id, stage, level, message, detail, diag_level, run_id)
      VALUES(
        p_start, p_end, p_station_id, p_device_id,
        'error', 'ERROR', SQLERRM,
        jsonb_build_object('sqlstate', SQLSTATE, '应用', v_app),
        v_level, p_run_id
      );
    END IF;
    v_failed := true;
  END;
  v_dur_ms := EXTRACT(MILLISECOND FROM (clock_timestamp() - v_t));

  IF v_level <> 'off' AND NOT v_failed THEN
    FOR r_rec IN
      SELECT split_part(stage, '_', 2)::int AS code, SUM(rows_affected)::bigint AS cnt
      FROM public.quality_profile_log
      WHERE window_start >= p_start AND window_end <= p_end AND stage LIKE 'update_%'
      GROUP BY split_part(stage, '_', 2)
    LOOP
      v_code := r_rec.code; v_cnt := r_rec.cnt;
      INSERT INTO public.quality_diagnosis_log(window_start, window_end, station_id, device_id, stage, level, message, detail, diag_level, run_id)
      VALUES(
        p_start, p_end, p_station_id, p_device_id,
        'rule_summary', 'INFO', '规则命中摘要',
        jsonb_build_object('代码', v_code, '命中', v_cnt),
        v_level, p_run_id
      );
    END LOOP;
  END IF;

  IF v_level <> 'off' THEN
    SELECT COUNT(*) INTO v_rows_scanned
    FROM public.fact_measurements
    WHERE ts_bucket >= p_start AND ts_bucket < p_end
      AND (p_device_id IS NULL OR device_id = p_device_id);

    INSERT INTO public.quality_diagnosis_log(window_start, window_end, station_id, device_id, stage, level, message, detail, diag_level, run_id)
    VALUES(
      p_start, p_end, p_station_id, p_device_id,
      'window_end', 'INFO', '完成质量标注',
      jsonb_build_object('duration_ms', v_dur_ms, '扫描行数', v_rows_scanned, 'result', CASE WHEN v_failed THEN 'error' ELSE 'ok' END),
      v_level, p_run_id
    );
  END IF;
END;
$$;
"""
                                            dcur.execute(_ddl_proc)
                                            # 重试一次
                                            dcur.execute(
                                                sql6_diag,
                                                (
                                                    s_dt,
                                                    e_dt,
                                                    station_id,
                                                    device_id,
                                                    codes,
                                                    str(diag_level),
                                                    run_id,
                                                ),
                                            )
                                        else:
                                            raise
                        except Exception as _inner_ex:
                            raise _inner_ex
                        used_proc = "public.sp_mark_quality_window_vfast_diag"
                        # 检查DB侧是否记录 error，如有则执行回退调用 vfast
                        try:
                            with conn.cursor() as _chk:
                                _chk.execute(
                                    "SELECT EXISTS(SELECT 1 FROM public.quality_diagnosis_log"
                                    " WHERE run_id = %s AND window_start = %s AND window_end = %s"
                                    " AND stage = 'error')",
                                    (run_id, s_dt, e_dt),
                                )
                                need_fallback = bool(_chk.fetchone()[0])
                        except Exception:
                            need_fallback = False
                        if need_fallback:
                            try:
                                _anom_logger.warning(
                                    "[ANOMALY] 诊断包装过程内部错误，执行回退 vfast：diag_level=%s",
                                    str(diag_level),
                                )
                            except Exception:
                                pass
                            # 回退前再次确保干净事务
                            try:
                                conn.rollback()
                            except Exception:
                                pass
                            with conn.cursor() as _cur2:
                                _cur2.execute(
                                    sql5,
                                    (
                                        s_dt,
                                        e_dt,
                                        station_id,
                                        device_id,
                                        codes,
                                    ),
                                )
                            # 显式提交：普通/回退路径需要手动提交事务
                            try:
                                conn.commit()
                            except Exception:
                                pass
                            used_proc = "public.sp_mark_quality_window_vfast"
                    except Exception as _diag_ex:
                        # 未部署或调用诊断包装过程失败时回退到原过程，并输出错误原因
                        try:
                            _anom_logger.warning(
                                (
                                    "[ANOMALY] 诊断包装过程失败，回退使用 vfast："
                                    "diag_level=%s，error=%s"
                                ),
                                str(diag_level),
                                str(_diag_ex),
                            )
                        except Exception:
                            pass
                        # 诊断过程调用失败会使事务进入 aborted 状态；回退前需 ROLLBACK
                        try:
                            conn.rollback()
                            try:
                                cur.close()
                            except Exception:
                                pass
                        except Exception:
                            pass
                        with conn.cursor() as _cur2:
                            _cur2.execute(
                                sql5,
                                (
                                    s_dt,
                                    e_dt,
                                    station_id,
                                    device_id,
                                    codes,
                                ),
                            )
                        # 显式提交：诊断失败后的回退路径需要手动提交
                        try:
                            conn.commit()
                        except Exception:
                            pass
                else:
                    cur.execute(
                        sql5,
                        (
                            s_dt,
                            e_dt,
                            station_id,
                            device_id,
                            codes,
                        ),
                    )
                    # 显式提交：普通路径手动提交事务（get_conn 不自动提交）
                    try:
                        conn.commit()
                    except Exception:
                        pass
                # 诊断开启时（无论调用路径），统一写入规则命中摘要到 anomaly 日志
                if use_diag:
                    try:
                        with conn.cursor() as _sum2:
                            _sum2.execute(
                                """
                                SELECT split_part(stage, '_', 2)::int AS code,
                                       SUM(rows_affected)::bigint AS cnt
                                FROM public.quality_profile_log
                                WHERE window_start >= %s AND window_end <= %s
                                  AND stage LIKE 'update_%%'
                                GROUP BY split_part(stage, '_', 2)
                                ORDER BY code
                                """,
                                (s_dt, e_dt),
                            )
                            _prof2 = [
                                {"code": int(r[0]), "rows": int(r[1])}
                                for r in _sum2.fetchall()
                            ]
                        if _prof2:
                            _anom_logger.info(
                                "[DIAG][rule_summary] 规则命中摘要",
                                extra={
                                    "extra_data": {
                                        "类型": "诊断",
                                        "summary": _prof2,
                                        "run_id": run_id,
                                    }
                                },
                            )
                    except Exception:
                        pass

                dur = int((_dt.now() - t0).total_seconds() * 1000)
                try:
                    _act.info("完成质量标注", extra={"extra_data": {
                        "阶段": "quality_mark",
                        "调用过程": used_proc,
                        "窗口": {
                            "start": format_for_display(_dt.fromisoformat(start.replace("Z", "+00:00")), settings) if start else None,
                            "end": format_for_display(_dt.fromisoformat(end.replace("Z", "+00:00")), settings) if end else None
                        },
                        "站点ID": station_id,
                        "设备ID": device_id,
                        "codes": codes,
                        "diag_level": diag_level,
                        "耗时ms": dur
                    }})
                except Exception:
                    pass
                # 文件侧阶段日志：window_end（服务层直接落盘）与 app 里程碑
                try:
                    _anom_logger.info(
                        "[DIAG][window_end] 完成质量标注",
                        extra={
                            "extra_data": {
                                "类型": "诊断",
                                "阶段": "window_end",
                                "窗口": {
                                    "start": format_for_display(_dt.fromisoformat(start.replace("Z", "+00:00")), settings) if start else None,
                                    "end": format_for_display(_dt.fromisoformat(end.replace("Z", "+00:00")), settings) if end else None
                                },
                                "设备": device_id,
                                "详情": {"result": "ok", "耗时ms": dur},
                                "run_id": run_id,
                            }
                        },
                    )
                except Exception:
                    pass
                try:
                    logging.getLogger("app").info(
                        "[ACT] mark_quality_window end",
                        extra={"extra_data": {"duration_ms": dur, "run_id": run_id}},
                    )
                except Exception:
                    pass

            except Exception as ex:
                dur = int((_dt.now() - t0).total_seconds() * 1000)
                try:
                    _act.error("质量标注异常", extra={"extra_data": {
                        "阶段": "quality_mark",
                        "调用过程": used_proc,
                        "窗口": {
                            "start": format_for_display(_dt.fromisoformat(start.replace("Z", "+00:00")), settings) if start else None,
                            "end": format_for_display(_dt.fromisoformat(end.replace("Z", "+00:00")), settings) if end else None
                        },
                        "站点ID": station_id,
                        "设备ID": device_id,
                        "codes": codes,
                        "diag_level": diag_level,
                        "耗时ms": dur,
                        "错误": str(ex)
                    }})
                except Exception:
                    pass
                # 异常路径：文件侧阶段日志与 app 里程碑（error）
                try:
                    _anom_logger.error(
                        "[DIAG][window_end] 质量标注异常",
                        extra={
                            "extra_data": {
                                "类型": "诊断",
                                "阶段": "window_end",
                                "窗口": {
                                    "start": format_for_display(_dt.fromisoformat(start.replace("Z", "+00:00")), settings) if start else None,
                                    "end": format_for_display(_dt.fromisoformat(end.replace("Z", "+00:00")), settings) if end else None
                                },
                                "设备": device_id,
                                "详情": {
                                    "result": "error",
                                    "错误": str(ex),
                                    "耗时ms": dur,
                                },
                                "run_id": run_id,
                            }
                        },
                    )
                except Exception:
                    pass
                try:
                    logging.getLogger("app").error(
                        "[ACT] mark_quality_window end(error)",
                        extra={
                            "extra_data": {
                                "duration_ms": dur,
                                "error": str(ex),
                                "run_id": run_id,
                            }
                        },
                    )
                except Exception:
                    pass
                # 清理上下文，避免残留
                try:
                    from app.core.logging.setup import clear_context  # local import

                    clear_context()
                except Exception:
                    pass
                raise

    # 正常路径：清理上下文，避免残留
    try:
        from app.core.logging.setup import clear_context  # local import

        clear_context()
    except Exception:
        pass

    return {
        "ok": True,
        "start": start,
        "end": end,
        "station_id": station_id,
        "device_id": device_id,
        "codes": codes,
        "run_id": run_id,
    }
