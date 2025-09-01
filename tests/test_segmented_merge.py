from datetime import datetime, timezone
from app.services.ingest.merge_service import _parse_granularity, _split_window


def test_parse_granularity():
    assert _parse_granularity("30m") == 1800
    assert _parse_granularity("1h") == 3600
    assert _parse_granularity("2h") == 7200


def test_split_window():
    s = datetime(2025, 2, 28, 2, 0, tzinfo=timezone.utc)
    e = datetime(2025, 2, 28, 4, 0, tzinfo=timezone.utc)
    segs = _split_window(s, e, 3600)
    assert len(segs) == 2
    assert segs[0][0] == s and segs[0][1] == datetime(
        2025, 2, 28, 3, 0, tzinfo=timezone.utc
    )
    assert (
        segs[1][0] == datetime(2025, 2, 28, 3, 0, tzinfo=timezone.utc)
        and segs[1][1] == e
    )
