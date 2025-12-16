import pytest

from app.utils.data_mapping import map_metrics_meta


def test_map_metrics_meta_pagination_and_mapping():
    # 构造模拟 rows（已按 ts 升序）
    rows = [
        {
            "ts": f"2025-03-01T00:{i:02d}:00",
            "station_id": 1,
            "device_id": 10 + (i % 2),
            "metric_id": 100 + (i % 3),
            "cnt": 1,
            "avg_value": i * 1.0,
            "min_value": i * 1.0,
            "max_value": i * 1.0,
            "sum_value": i * 1.0,
        }
        for i in range(20)
    ]

    devices_map = {10: "D10", 11: "D11"}
    metrics_map = {
        100: {"metric_key": "m100", "unit": "u"},
        101: {"metric_key": "m101", "unit": "u"},
        102: {"metric_key": "m102", "unit": "u"},
    }

    # 取第2页（每页5条）：offset=5, limit=5 → 期望 ts index 5..9
    data = map_metrics_meta(rows, devices_map, metrics_map, offset=5, limit=5)
    assert len(data) == 5
    assert data[0]["ts"] == "2025-03-01T00:05:00"
    assert data[-1]["ts"] == "2025-03-01T00:09:00"

    # 校验映射字段
    for item in data:
        assert item["device_name"] in {"D10", "D11"}
        assert item["metric_key"] in {"m100", "m101", "m102"}
        assert item["unit"] == "u"


def test_map_metrics_meta_handles_missing_meta():
    rows = [
        {"ts": "2025-03-01T00:00:00", "station_id": 1, "device_id": 10, "metric_id": 999}
    ]
    devices_map = {}
    metrics_map = {}

    data = map_metrics_meta(rows, devices_map, metrics_map, offset=0, limit=10)
    assert len(data) == 1
    assert data[0]["device_name"] is None  # 设备名缺失
    assert data[0]["metric_key"] is None   # 指标元数据缺失

