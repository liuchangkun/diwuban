from __future__ import annotations
from pathlib import Path

from app.adapters.db.gateway import get_conn
from app.core.config.loader import load_settings

ROOT = Path('.')
SEED_SQL = ROOT / 'scripts' / 'dev' / 'seed_from_mapping.sql'


def _load_sql_statements(path: Path) -> list[str]:
    text = path.read_text(encoding='utf-8')
    lines = []
    for line in text.splitlines():
        # 跳过 psql 元命令与注释行
        if line.strip().startswith('\\'):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    # 粗粒度按分号拆分
    stmts = []
    buff = []
    for ch in cleaned:
        buff.append(ch)
        if ch == ';':
            stmt = ''.join(buff).strip()
            if stmt:
                stmts.append(stmt)
            buff = []
    # 处理最后一段
    tail = ''.join(buff).strip()
    if tail:
        stmts.append(tail)
    # 去掉空语句
    stmts = [s for s in stmts if s.strip(';').strip()]
    return stmts


def run() -> None:
    settings = load_settings(Path('configs'))
    sqls = _load_sql_statements(SEED_SQL)
    print(f'[INFO] Loaded {len(sqls)} SQL statements from {SEED_SQL}')

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            for i, s in enumerate(sqls, 1):
                cur.execute(s)
                if i % 50 == 0:
                    print(f'[EXEC] executed {i} statements')
        conn.commit()

    # 验证 dim_mapping_items 与可用性视图
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT count(*) FROM public.dim_mapping_items')
            mapping_cnt = int(cur.fetchone()[0])
            print('[RESULT] dim_mapping_items count:', mapping_cnt)

            cur.execute('SELECT station_name, device_name, metric_key FROM public.dim_mapping_items ORDER BY 1,2,3 LIMIT 5')
            for row in cur.fetchall():
                print('[SAMPLE] mapping:', row)

            # 再跑只读统计
            cur.execute("""
                SELECT COUNT(*) FROM public.metrics_missing_v
                WHERE method_hint='compute' AND week_start >= date_trunc('week', now()) - interval '4 weeks'
            """)
            compute_4w = int(cur.fetchone()[0])
            cur.execute("""
                SELECT COUNT(*) FROM public.metrics_missing_v
                WHERE method_hint='acquire' AND week_start >= date_trunc('week', now()) - interval '8 weeks'
            """)
            acquire_8w = int(cur.fetchone()[0])
            print('[RESULT] compute_required (last 4w):', compute_4w)
            print('[RESULT] missing_raw (last 8w):', acquire_8w)


if __name__ == '__main__':
    run()

