# -*- coding: utf-8 -*-
"""
顶层脚本归并到 scripts/*（中文注释）
- 扫描项目根目录下的 *.py（排除 app/ scripts/ tests/ docs/ configs/ 等）
- 根据命名规则分类：maintenance/analysis/tools
- 生成 TSV 映射清单：docs/_archive/reports/顶层脚本迁移清单_YYYYMMDD.tsv
- 移动文件（若目标已存在则跳过并记录冲突）
安全说明：
- 只移动文件，不删除任何目录
- 冲突文件不覆盖，记录在同名冲突清单中
使用：
  python scripts/dev/move_root_scripts.py
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[2]
DEST_BASE = ROOT / "scripts"
REPORT_DIR = ROOT / "docs" / "_archive" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
MAP_FILE = REPORT_DIR / f"顶层脚本迁移清单_{datetime.now().strftime('%Y%m%d')}.tsv"
CONFLICT_FILE = REPORT_DIR / f"顶层脚本迁移冲突_{datetime.now().strftime('%Y%m%d')}.tsv"

EXCLUDE_DIRS = {
    "app",
    "scripts",
    "tests",
    "docs",
    "configs",
    "config",
    "data",
    "logs",
    "rules",
    "src",
    ".git",
    ".github",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".vscode",
    "ProjectDocs个人说明",
}

MAINT_PATTERNS = (
    "create_",
    "generate_",
    "execute_",
    "restore_",
    "optimize_",
    "fix_",
    "recreate_",
    "migrate_",
)
ANALYSIS_PATTERNS = (
    "query_",
    "demo_",
    "verify_",
    "analyze_",
    "postgres_",
    "*_example",
    "example",
    "examples",
    "stats",
    "digest",
)
TOOLS_PATTERNS = (
    "check_",
    "simple_",
    "count_",
    "probe_",
    "print_",
    "run_",
)


def classify(script: Path) -> str:
    name = script.name
    low = name.lower()
    # 明确排除 __init__ 等
    if low in {"__init__.py"}:
        return "skip"
    # 分类规则（按优先级）
    for p in MAINT_PATTERNS:
        if low.startswith(p):
            return "maintenance"
    for p in ANALYSIS_PATTERNS:
        if (
            low.startswith(p)
            or ("example" in low)
            or ("examples" in low)
            or ("digest" in low)
        ):
            return "analysis"
    for p in TOOLS_PATTERNS:
        if low.startswith(p):
            return "tools"
    # 特判常见脚本名
    if low in {"api_fix_report.py"}:
        return "tools"
    if low in {"verify_horizontal.py"}:
        return "analysis"
    # 默认放 tools
    return "tools"


def iter_root_scripts() -> List[Path]:
    results: List[Path] = []
    for p in ROOT.iterdir():
        if p.is_dir():
            if p.name in EXCLUDE_DIRS:
                continue
            # 不递归目录，这里只处理根层文件
            continue
        if p.suffix.lower() == ".py":
            results.append(p)
    return results


def move_files(files: List[Path]) -> Tuple[int, int, int]:
    moved = 0
    skipped = 0
    conflicts = 0
    with MAP_FILE.open("w", encoding="utf-8") as fw_map, CONFLICT_FILE.open(
        "w", encoding="utf-8"
    ) as fw_conf:
        fw_map.write("original_path\tnew_path\n")
        fw_conf.write("conflict_path\ttarget_path\n")
        for f in files:
            category = classify(f)
            if category == "skip":
                skipped += 1
                continue
            dest_dir = DEST_BASE / category
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f.name
            rel_src = f.relative_to(ROOT).as_posix()
            rel_dst = dest.relative_to(ROOT).as_posix()
            if dest.exists():
                conflicts += 1
                fw_conf.write(f"{rel_src}\t{rel_dst}\n")
                print(f"[冲突] 目标已存在，跳过：{rel_src} -> {rel_dst}")
                continue
            # 执行移动
            f.replace(dest)
            fw_map.write(f"{rel_src}\t{rel_dst}\n")
            moved += 1
            print(f"[移动] {rel_src} -> {rel_dst}")
    return moved, skipped, conflicts


def main():
    files = iter_root_scripts()
    moved, skipped, conflicts = move_files(files)
    print(f"[结果] 移动={moved}, 跳过={skipped}, 冲突={conflicts}")
    print(f"[清单] {MAP_FILE.relative_to(ROOT)}")
    print(f"[冲突] {CONFLICT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
