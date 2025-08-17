import os
import sys
from pathlib import Path
from subprocess import run, PIPE

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ENV = os.environ.copy()
ENV["PYTHONPATH"] = str(SRC) + os.pathsep + ENV.get("PYTHONPATH", "")


def test_cli_help():
    r = run(
        [sys.executable, "-m", "diwuban.cli", "-h"],
        stdout=PIPE,
        stderr=PIPE,
        text=True,
        env=ENV,
    )
    assert r.returncode == 0
    assert "diwuban CLI prototype" in r.stdout


def test_cli_ingest_dry_run(tmp_path):
    # create a dummy mapping file
    m = tmp_path / "data_mapping.json"
    m.write_text("{}", encoding="utf-8")
    r = run(
        [
            sys.executable,
            "-m",
            "diwuban.cli",
            "ingest",
            "--mapping",
            str(m),
            "--dry-run",
        ],
        stdout=PIPE,
        stderr=PIPE,
        text=True,
        env=ENV,
    )
    assert r.returncode == 0
    assert "[INGEST]" in r.stdout


def test_cli_align():
    r = run(
        [
            sys.executable,
            "-m",
            "diwuban.cli",
            "align",
            "--station",
            "S1",
            "--grid",
            "auto",
        ],
        stdout=PIPE,
        stderr=PIPE,
        text=True,
        env=ENV,
    )
    assert r.returncode == 0
    assert "[ALIGN]" in r.stdout
