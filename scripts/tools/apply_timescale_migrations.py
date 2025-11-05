from __future__ import annotations

"""
apply_timescale_migrations.py

使用应用内的配置与连接（免交互、免密码提示），执行 Timescale 相关 DDL/SQL。
- 依赖配置：configs/*.yaml（通过 loader_new.load_settings 加载）
- 连接：app.adapters.db.gateway.get_conn（复用项目 DSN/连接池设置）
- 用法示例：
    python scripts/tools/apply_timescale_migrations.py --file scripts/sql/ts_staging.sql

注意：SQL 脚本需具备幂等性；本工具不做复杂拆句，直接执行整段 SQL。
"""

import argparse
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中（免安装包）
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def run(sql_path: Path) -> None:
    if not sql_path.exists():
        raise SystemExit(f"SQL 文件不存在: {sql_path}")
    settings = load_settings(Path("configs"))
    sql = sql_path.read_text(encoding="utf-8")
    with get_conn(settings) as conn:
        # 由于 get_conn 内部可能已执行设置语句并进入事务，这里先提交结束事务，再切换 autocommit
        try:
            conn.commit()
        except Exception:
            pass
        try:
            conn.autocommit = True
        except Exception:
            # 某些驱动在事务中不允许切 autocommit，再次尝试提交后切换
            try:
                conn.commit()
                conn.autocommit = True
            except Exception as e:
                raise RuntimeError(f"无法切换 autocommit: {e}")
        with conn.cursor() as cur:
            cur.execute(sql)
        print(f"[OK] Executed: {sql_path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="要执行的 SQL 文件路径")
    args = parser.parse_args()
    run(Path(args.file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
