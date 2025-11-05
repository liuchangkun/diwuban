from pathlib import Path
from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn

def main():
    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.quality_diagnosis_log')")
            tbl = cur.fetchone()[0]
            cur.execute("SELECT to_regclass('public.sp_mark_quality_window_vfast_diag')")
            proc = cur.fetchone()[0]
            print(f"TABLE={tbl} PROC={proc}")

if __name__ == "__main__":
    main()

