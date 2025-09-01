import sys
from pathlib import Path

# Ensure 'src' is on sys.path so that 'diwuban' package is importable during tests
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# 兼容 fastapi.testclient 历史导出（新版本可能不再导出）
import types

try:
    import fastapi as _fastapi

    try:
        import fastapi.testclient as _fastapi_testclient  # type: ignore[attr-defined]

        setattr(_fastapi, "testclient", _fastapi_testclient)
    except Exception:
        try:
            import starlette.testclient as _st_testclient  # type: ignore

            _m = types.ModuleType("fastapi.testclient")
            _m.TestClient = _st_testclient.TestClient  # type: ignore[attr-defined]
            setattr(_fastapi, "testclient", _m)
        except Exception:
            pass
except Exception:
    pass
