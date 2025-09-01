#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memory_check.py（中文化 PLAYBOOKS 兼容版）

第二优先级：核心功能
- 调用 git diff --name-only HEAD 获取当前改动文件
- 依据路径映射 SUGGEST_MAP 推断应记录的 PLAYBOOKS 类型集合
- 在中文 PLAYBOOKS 文档中搜索“今日日期”的 front matter，判定是否已记录
- 输出覆盖率、建议类型与缺失项清单（供 pre-commit/CI 使用）

实现细节
- 仅使用标准库；UTF-8；详细日志；健壮的错误处理
"""

import os
import re
import sys
import subprocess
from datetime import datetime
from typing import Dict, List, Set

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PLAYBOOKS_DIR = os.path.join(ROOT, "docs", "PLAYBOOKS")

# 路径前缀 → 建议记录类型
SUGGEST_MAP: Dict[str, List[str]] = {
    "scripts/sql/": ["CONF", "DEC", "IMP"],
    "docs/": ["DEC", "IMP", "LES", "BENCH"],
    "app/": ["IMP", "DEC"],
}

# 类型 → 中文文件映射
TYPE_TO_FILE: Dict[str, str] = {
    "DEC": os.path.join(PLAYBOOKS_DIR, "决策记录.md"),
    "CONF": os.path.join(PLAYBOOKS_DIR, "配置变更记录.md"),
    "IMP": os.path.join(PLAYBOOKS_DIR, "改进与优化记录.md"),
    "LES": os.path.join(PLAYBOOKS_DIR, "经验教训.md"),
    "BENCH": os.path.join(PLAYBOOKS_DIR, "性能基准.md"),
}

FRONT_MATTER_BLOCK_RE = re.compile(r"---\s*\n(.*?)\n---", re.DOTALL)
DATE_LINE_RE = re.compile(r"^date:\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)


def log(msg: str) -> None:
    print(f"[memory_check] {msg}")


def run_git_diff_names() -> List[str]:
    """返回当前改动的文件路径列表（相对仓库根）。"""
    try:
        # 确认在 git 仓库内
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
    except Exception as e:
        raise RuntimeError("当前目录不是 git 仓库，无法获取改动文件。") from e

    # 优先对比上一提交；若失败，退化为工作区改动
    cmds = [
        ["git", "diff", "--name-only", "HEAD"],
        ["git", "diff", "--name-only"],
        ["git", "status", "-s"],
    ]
    for cmd in cmds:
        try:
            res = subprocess.run(
                cmd,
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            out = res.stdout.strip()
            if not out:
                continue
            paths = [line.strip() for line in out.splitlines() if line.strip()]
            # git status -s 行形如 " M path"，仅取最后的路径列
            if cmd[:2] == ["git", "status"]:
                paths = [p.split(maxsplit=1)[-1] for p in paths if p]
            return paths
        except subprocess.CalledProcessError:
            continue
    return []


def suggest_types(paths: List[str]) -> Set[str]:
    suggested: Set[str] = set()
    for p in paths:
        pp = p.replace("\\", "/")  # 规范化分隔符
        for prefix, types in SUGGEST_MAP.items():
            if pp.startswith(prefix):
                suggested.update(types)
    return suggested


def has_today_entry(playbook_path: str, today: str) -> bool:
    if not os.path.exists(playbook_path):
        log(f"警告：缺少记录文件 {os.path.relpath(playbook_path, ROOT)}")
        return False
    try:
        with open(playbook_path, "r", encoding="utf-8") as fp:
            text = fp.read()
    except Exception as e:
        log(f"错误：无法读取 {os.path.relpath(playbook_path, ROOT)}: {e}")
        return False
    # 查找所有 front matter 块，匹配 date: YYYY-MM-DD
    for block in FRONT_MATTER_BLOCK_RE.findall(text):
        m = DATE_LINE_RE.search(block)
        if m and m.group(1) == today:
            return True
    return False


def main() -> int:
    log("开始记忆覆盖率检查…")
    try:
        paths = run_git_diff_names()
    except Exception as e:
        log(f"错误：获取 git 改动失败：{e}")
        return 1

    if not paths:
        log("提示：未检测到改动文件，视为无需新增 PLAYBOOKS 记录。")
        print(
            'result: {"coverage": 100, "suggested": [], "missing": [], "changed_files": []}'
        )
        return 0

    log(f"检测到改动 {len(paths)} 个文件")
    for p in paths[:20]:
        log(f"改动文件：{p}")
    types = sorted(list(suggest_types(paths)))

    if not types:
        log("提示：改动未命中 SUGGEST_MAP，视为无需新增 PLAYBOOKS 记录。")
        print(
            f'result: {{"coverage": 100, "suggested": [], "missing": [], "changed_files": {paths!r}}}'
        )
        return 0

    today = datetime.now().strftime("%Y-%m-%d")
    missing: List[str] = []
    recorded: List[str] = []
    for t in types:
        f = TYPE_TO_FILE.get(t)
        if not f:
            log(f"警告：未知类型 {t}")
            missing.append(t)
            continue
        if has_today_entry(f, today):
            recorded.append(t)
        else:
            missing.append(t)

    cov = int(round(100 * (len(recorded) / len(types)) if types else 1.0))
    log(f"建议类型：{types}")
    log(f"已记录：{recorded}")
    log(f"缺失项：{missing}")
    print(
        "result: "
        + str(
            {
                "coverage": cov,
                "suggested": types,
                "missing": missing,
                "changed_files": paths,
                "date": today,
            }
        )
    )
    # 政策调整：总是返回 0（仅警告不阻断），由 PR 审查把关
    return 0


if __name__ == "__main__":
    sys.exit(main())
