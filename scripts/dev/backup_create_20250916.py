import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn
import psycopg


def run(cmd, env=None):
    print("[RUN]", " ".join(cmd))
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
        raise SystemExit(res.returncode)


def main():
    settings = load_settings(Path("configs"))
    # 获取连接信息和当前库名
    with get_conn(settings) as conn:
        info = conn.info
        host = info.host or "localhost"
        port = str(info.port or 5432)
        user = info.user
        password = info.password or ""
        with conn.cursor() as cur:
            cur.execute("SELECT current_database()")
            src_db = cur.fetchone()[0]

    target_db = "20250916"
    dump_dir = ROOT / "exports" / "db_dumps"
    dump_dir.mkdir(parents=True, exist_ok=True)
    dump_file = dump_dir / f"{src_db}_backup_{target_db}.dump"

    # 检测 pg_dump/pg_restore
    for tool in ("pg_dump", "pg_restore"):
        try:
            subprocess.run([tool, "--version"], check=True, capture_output=True)
        except Exception:
            print(f"未找到 {tool}，请确保已安装并加入 PATH。", file=sys.stderr)
            raise

    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    # 创建目标库（若不存在）
    admin_dsn = f"host={host} port={port} user={user} dbname=postgres"
    with psycopg.connect(admin_dsn, autocommit=True, password=password) as admin:
        with admin.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (target_db,))
            if not cur.fetchone():
                cur.execute(f"CREATE DATABASE {psycopg.sql.Identifier(target_db).as_string(cur)}")
                print({"created_db": target_db})
            else:
                print({"exists_db": target_db})

    # 逻辑备份
    run([
        "pg_dump",
        "-h", host,
        "-p", port,
        "-U", user,
        "-d", src_db,
        "-Fc",
        "-f", str(dump_file),
    ], env=env)

    # 还原到 20250916
    run([
        "pg_restore",
        "-h", host,
        "-p", port,
        "-U", user,
        "-d", target_db,
        "--clean",
        "--if-exists",
        str(dump_file),
    ], env=env)

    print({"ok": True, "backup_dump": str(dump_file), "src": src_db, "dst": target_db})


if __name__ == "__main__":
    main()

