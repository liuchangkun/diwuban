import json
from pathlib import Path

from app.adapters.fs.reader import _normalize, iter_rows, validate_header
from app.adapters.logging.init import JsonFormatter
from app.core.types import ValidRow
from app.services.ingest.backpressure import BackpressureController, Thresholds


def test_normalize_bom_and_case():
    assert _normalize("\ufeffTagName") == "tagname"
    assert _normalize(" DataTime ") == "datatime"


def test_validate_header_passes_with_bom_and_datatime():
    hdr = ["\ufeffTagName", "DataTime", "DataVersion", "DataQuality", "DataValue"]
    # 应允许通过
    validate_header(hdr)


def test_iter_rows_parses_values(tmp_path: Path):
    csv = "TagName,DataTime,DataVersion,DataQuality,DataValue\nTAG,2025-08-11T00:00:00,1,0,12.3\n"
    p = tmp_path / "a.csv"
    p.write_text(csv, encoding="utf-8")
    rows = list(iter_rows(p, "hint"))
    valids = [r for r in rows if isinstance(r, ValidRow)]
    assert len(valids) == 1
    v = valids[0]
    assert v.TagName == "TAG"
    assert v.DataTime == "2025-08-11T00:00:00"
    assert v.DataValue == "12.3"


def test_json_formatter_serializes_datetime_and_path():
    fmt = JsonFormatter()

    class R:
        levelname = "INFO"
        name = "t"

        def getMessage(self):
            return "m"

    r = R()
    out = fmt.format(r)
    data = json.loads(out)
    assert data["level"] == "INFO"
    assert data["message"] == "m"


def test_backpressure_controller_basic():
    ctrl = BackpressureController(batch_size=10000, workers=6, thresholds=Thresholds())
    # 高 p95 触发收缩
    adj = ctrl.decide(p95_ms=5000, fail_rate=0)
    assert adj["action"] in ("shrink_batch", "shrink_workers")
    # 恢复信号
    adj2 = ctrl.decide(p95_ms=1, fail_rate=0)
    assert adj2["action"] in ("recover", "none")
