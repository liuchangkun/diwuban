from __future__ import annotations

import contextlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config.loader_new import load_settings


@pytest.fixture()
def settings():
    return load_settings(Path("configs"))


def _snapshot_counts():
    try:
        from app.adapters.db import pool_telemetry as pt
    except Exception:  # pragma: no cover
        return {"fallback_count": None, "error_count": None}
    snap = pt.snapshot()
    return {
        "fallback_count": snap.get("fallback_count", 0),
        "error_count": snap.get("error_count", 0),
    }


def test_get_conn_uninitialized_fallback_increments_fallback(monkeypatch, settings):
    # Arrange: simulate pool not initialized: get_pool_stats() -> {error: ...}, get_connection() raises DatabaseError
    import app.adapters.db.pool as pool_mod
    from app.core.exceptions import DatabaseConnectionError, DatabaseError

    monkeypatch.setattr(
        pool_mod, "get_pool_stats", lambda: {"error": "not_initialized"}, raising=True
    )

    def _raise_db_error(*a, **k):
        raise DatabaseError("pool not initialized")

    monkeypatch.setattr(
        pool_mod,
        "get_connection",
        contextlib.contextmanager(
            lambda *a, **k: (_ for _ in ()).throw(DatabaseError("x"))
        ),
        raising=True,
    )

    # Avoid real DB connection on fallback direct path
    import psycopg

    def _raise_connect(*a, **k):
        raise DatabaseConnectionError("no db", context={})

    monkeypatch.setattr(psycopg, "connect", _raise_connect, raising=True)

    before = _snapshot_counts()

    # Act: call gateway.get_conn -> should fallback and then fail to connect
    import app.adapters.db.gateway as gw

    with pytest.raises(DatabaseConnectionError):
        with gw.get_conn(settings):
            pass

    after = _snapshot_counts()

    assert after["fallback_count"] is not None and before["fallback_count"] is not None
    assert after["fallback_count"] >= before["fallback_count"] + 1


def test_get_conn_initialized_pool_error_increments_error_and_raises(
    monkeypatch, settings
):
    # Arrange: simulate pool initialized but get_connection raises DatabaseError
    import app.adapters.db.pool as pool_mod
    from app.core.exceptions import DatabaseError

    monkeypatch.setattr(
        pool_mod,
        "get_pool_stats",
        lambda: {"total_connections": 5, "idle_connections": 1},
        raising=True,
    )

    def _ctxmgr_error(*a, **k):
        def _gen():
            raise DatabaseError("pool internal error")
            yield  # pragma: no cover

        return contextlib.contextmanager(lambda: _gen())()

    monkeypatch.setattr(pool_mod, "get_connection", _ctxmgr_error, raising=True)

    before = _snapshot_counts()

    # Act & Assert: gateway.get_conn should raise DatabaseError and increment error_count
    import app.adapters.db.gateway as gw

    with pytest.raises(DatabaseError):
        with gw.get_conn(settings):
            pass

    after = _snapshot_counts()

    assert after["error_count"] is not None and before["error_count"] is not None
    assert after["error_count"] >= before["error_count"] + 1
