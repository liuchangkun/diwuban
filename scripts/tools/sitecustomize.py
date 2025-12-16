# 测试环境启动钩子（pytest 等运行时会自动导入此模块）
# 目的：确保 fastapi.testclient 子模块在 fastapi 包属性中可见，兼容历史用法（FastAPI 新版可能不再导出）
import sys
import types

try:
    # 若新版 FastAPI 无 testclient 子模块，此导入会失败
    # 成功则确保 fastapi 模块对象挂载 testclient 属性
    import fastapi as _fastapi
    import fastapi.testclient as _fastapi_testclient  # type: ignore[attr-defined]

    setattr(_fastapi, "testclient", _fastapi_testclient)
except Exception:
    try:
        # 回退：使用 Starlette 的 TestClient 作为兼容替代
        import starlette.testclient as _st_testclient  # type: ignore

        _m = types.ModuleType("fastapi.testclient")
        _m.TestClient = _st_testclient.TestClient  # type: ignore[attr-defined]
        sys.modules["fastapi.testclient"] = _m
        import fastapi as _fastapi  # noqa: E402

        setattr(_fastapi, "testclient", _m)
    except Exception:
        # 最小兜底：不阻断测试收集
        pass
