from pathlib import Path

from app.core.config.loader import Settings
from app.services.ingest.source_hint import make_source_hint


def test_make_source_hint_relpath_with_batch_id():
    settings = Settings()
    # 打开增强
    object.__setattr__(settings, "ingest", settings.ingest)
    object.__setattr__(settings.ingest, "enhanced_source_hint", True)
    object.__setattr__(settings, "_runtime_run_id", "T123")
    object.__setattr__(settings.ingest, "_runtime_run_id", "T123")

    base_dir = Path("data")
    csv_path = Path("data/二期/电表/电压/样例.csv")
    out = make_source_hint(settings, base_dir, csv_path)
    assert out.startswith("data/二期/电表/电压/样例.csv|batch=T123|ver=2")


def test_make_source_hint_fallback_name_when_no_enhanced():
    settings = Settings()
    object.__setattr__(settings, "ingest", settings.ingest)
    object.__setattr__(settings.ingest, "enhanced_source_hint", False)
    base_dir = Path("data")
    csv_path = Path("data/路径/文件,包含,逗号.csv")
    out = make_source_hint(settings, base_dir, csv_path)
    assert out == "文件,包含,逗号.csv"
