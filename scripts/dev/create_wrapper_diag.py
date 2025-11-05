from pathlib import Path

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import load_settings


def main():
    settings = load_settings(Path("configs"))
    # 先确保日志表存在
    ddl_table = r"""
CREATE TABLE IF NOT EXISTS public.quality_diagnosis_log (
  id            bigserial PRIMARY KEY,
  created_at    timestamptz NOT NULL DEFAULT now(),
  window_start  timestamptz NOT NULL,
  window_end    timestamptz NOT NULL,
  station_id    bigint NULL,
  device_id     bigint NULL,
  stage         text NOT NULL,
  level         text NOT NULL DEFAULT 'INFO',
  message       text NULL,
  detail        jsonb NULL,
  diag_level    text NOT NULL DEFAULT 'off',
  run_id        text NULL
);
"""
    ddl = r"""
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
    with get_conn(settings) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(ddl_table)
            cur.execute(ddl)


if __name__ == "__main__":
    main()
