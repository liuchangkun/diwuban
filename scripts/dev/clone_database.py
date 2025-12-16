import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn
import psycopg


def main():
    target_db = '20250916'
    settings = load_settings(Path('configs'))

    # 连接到当前应用数据库，获取当前库名与连接信息
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), inet_client_addr(), inet_client_port()")
            row = cur.fetchone()
            src_db = row[0]
        info = conn.info
        host = info.host or 'localhost'
        port = info.port or 5432
        user = info.user
        password = info.password

    # 在 postgres 库上创建目标库，使用 TEMPLATE 复制
    dsn = f"host={host} port={port} user={user} password={password} dbname=postgres"
    with psycopg.connect(dsn, autocommit=True) as admin:
        with admin.cursor() as cur:
            # 若已存在则跳过
            cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (target_db,))
            if cur.fetchone():
                print({"ok": True, "action": "exists", "src": src_db, "dst": target_db})
                return
            # 确保模板库允许连接
            cur.execute("UPDATE pg_database SET datallowconn=true WHERE datname=%s", (src_db,))
            # 创建备份库
            cur.execute(f"CREATE DATABASE {psycopg.sql.Identifier(target_db).as_string(cur)} TEMPLATE {psycopg.sql.Identifier(src_db).as_string(cur)}")
            print({"ok": True, "action": "created", "src": src_db, "dst": target_db})


if __name__ == "__main__":
    main()

