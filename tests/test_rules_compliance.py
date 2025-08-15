import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "config" / "data_mapping.json"


def test_mapping_exists_and_valid_json():
    assert MAPPING.exists(), "config/data_mapping.json must exist"
    data = json.loads(MAPPING.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and data, "mapping must be a non-empty JSON object"


def test_mapping_structure_and_paths():
    data = json.loads(MAPPING.read_text(encoding="utf-8"))
    for station, devices in data.items():
        assert isinstance(devices, dict), f"station '{station}' must map to an object"
        for device, metrics in devices.items():
            assert isinstance(metrics, dict), f"device '{device}' must map to an object"
            for metric, files in metrics.items():
                assert isinstance(
                    files, list
                ), f"metric '{station}/{device}/{metric}' must be a list of paths"
                for f in files:
                    assert isinstance(f, str) and f.startswith(
                        "data/"
                    ), f"path must start with 'data/': {f}"
