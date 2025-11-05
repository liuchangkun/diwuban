from __future__ import annotations

from typing import Any, Dict
from pathlib import Path
import logging

from app.adapters.db.gateway import get_conn

_act = logging.getLogger("activity")


def run_db_ping(settings, verbose: bool = False) -> Dict[str, Any]:
    _act.info(
        "[流程-开始] [数据库连接测试]",
        extra={"extra_data": {"verbose": verbose}}
    )

    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                row = cur.fetchone()
                val = row[0] if row else 1
                res: Dict[str, Any] = {"ok": True, "val": int(val)}
                if verbose:
                    cur.execute(
                        "SELECT current_database(), current_user, current_setting('TimeZone'), version()"
                    )
                    dbrow = cur.fetchone() or (None, None, None, None)
                    dbname, dbuser, tz, ver = dbrow

                    def _mask(u: str | None) -> str:
                        if not u:
                            return ""
                        return (u[0] + "***" + u[-1]) if len(u) > 2 else (u + "*")

                    res.update(
                        {
                            "database": dbname,
                            "user": _mask(str(dbuser) if dbuser is not None else None),
                            "timezone": tz,
                            "version": str(ver).split(" ")[0] if ver else None,
                        }
                    )

                _act.info(
                    "[流程-完成] [数据库连接测试成功]",
                    extra={
                        "extra_data": {
                            "ok": True,
                            "verbose": verbose,
                            "database": res.get("database") if verbose else None,
                        }
                    }
                )
                return res
    except Exception as e:
        _act.error(
            "[流程-错误] [数据库连接测试失败]",
            extra={"extra_data": {"error": str(e)}}
        )
        return {"ok": False, "error": str(e)}

