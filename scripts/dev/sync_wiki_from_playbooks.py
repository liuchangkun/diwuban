# -*- coding: utf-8 -*-
"""
基于 PLAYBOOKS 与项目产出生成“有人味”的 Wiki 片段到 docs/_自动/ 下：
- 项目状态总览.md（叙述体，含 注/说明/影响/证据/回滚）
- 开放问题清单.md（引用 PLAYBOOKS 源，并加上上下文说明）
- 数据库变更摘要.md（从 PLAYBOOKS/数据库变更记录.md 提炼友好摘要）

特点：
- 不直接改动人工文档；仅生成 docs/_自动/*.md，被主文档以“引用/包含”方式采纳
- 可反复执行，幂等覆盖
- 文案尽量口语化，提供“为什么/发现了什么/依据是什么/要做什么”的解释
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
AUTO = DOCS / "_自动"
PLAY = DOCS / "PLAYBOOKS"


def _read_json(p: Path) -> dict:
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_text(p: Path) -> str:
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_latest_playbook_rows(index_md: Path, limit: int = 5) -> list[str]:
    # 解析 Markdown 表格的前几行（跳过表头与分隔行）
    lines = _read_text(index_md).splitlines()
    rows: list[str] = []
    for ln in lines:
        if ln.strip().startswith("|") and ("----" not in ln):
            rows.append(ln.strip())
    # 去掉表头两行
    rows = [r for r in rows if "日期" not in r and "-----" not in r]
    return rows[:limit]


def _summarize_health(health_path: Path) -> list[str]:
    data = _read_json(health_path)
    if not data:
        return ["- 暂无健康数据（health.json 缺失或为空）"]
    lines: list[str] = []
    # 尽量稳健地提取常见键
    env = data.get("env") or data.get("environment")
    status = data.get("status") or data.get("ok")
    tz = data.get("timezone") or data.get("tz")
    ver = data.get("version") or data.get("app_version")
    if status is not None:
        lines.append(f"- 服务状态：{status}")
    if env:
        lines.append(f"- 运行环境：{env}")
    if tz:
        lines.append(f"- 时区：{tz}")
    if ver:
        lines.append(f"- 版本：{ver}")
    if not lines:
        # 回退打印若干顶层键
        tops = ", ".join(sorted(str(k) for k in list(data.keys())[:6]))
        lines.append(f"- 健康数据可用，主要键：{tops}")
    return lines


def _summarize_run_all(path: Path) -> list[str]:
    data = _read_json(path)
    if not data:
        return ["- 暂无最近一次总流程运行摘要（run_all_summary.json 缺失或为空）"]
    lines: list[str] = []
    # 尝试读取常见字段
    window = data.get("window") or {}
    ws = window.get("start") or window.get("window_start")
    we = window.get("end") or window.get("window_end")
    if ws or we:
        lines.append(f"- 运行窗口：{ws or '?'} → {we or '?' }")
    steps = []
    for k in ["prepare_dim", "create_staging", "ingest_copy", "merge_fact", "quality_mark", "device_running", "presence"]:
        v = data.get(k)
        if isinstance(v, dict) and v.get("status"):
            steps.append(f"{k}:{v.get('status')}")
    if steps:
        lines.append("- 步骤结果：" + ", ".join(steps))
    return lines or ["- 总流程摘要存在，但未包含标准字段（保留原始文件作为证据）"]


def _summarize_mapping_report(path: Path) -> list[str]:
    data = _read_json(path)
    if not data:
        return ["- 暂无数据映射报告（mapping_report.json 缺失或为空）"]
    lines: list[str] = []
    # 尝试读取典型聚合字段
    for key in ["metrics", "devices", "stations", "mappings", "rules"]:
        if key in data and isinstance(data[key], (int, float)):
            lines.append(f"- {key}：{data[key]}")
    if not lines:
        tops = ", ".join(sorted(str(k) for k in list(data.keys())[:6]))
        lines.append(f"- 数据映射报告可用，主要键：{tops}")
    return lines


def generate_status_overview() -> None:
    AUTO.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    latest_rows = _extract_latest_playbook_rows(PLAY / "索引.md")

    parts: list[str] = []
    parts.append("# 项目状态总览（自动生成｜含注释）\n")
    parts.append(
        "> 说明：本页由脚本生成，旨在把“这次发生了什么、为什么这样做、影响与证据、如何回滚”讲清楚，\n"
        "> 便于人类快速阅读与追溯。若与事实不符，以数据库/日志/脚本输出为准。\n"
    )
    parts.append("")
    # 一句话总结
    parts.append("## 一言以蔽之\n")
    parts.append("- 本次更新已同步 PLAYBOOKS 与核心文档，附注释与证据链接。\n")
    if latest_rows:
        parts.append("- 最近条目（节选）：\n")
        for r in latest_rows:
            parts.append(f"  - {r}")
    else:
        parts.append("- 最近条目：索引缺失或暂无记录。\n")

    # 我们为什么、发现了什么
    parts.append("\n## 我们为什么这样做（动机）\n")
    parts.append(
        "- 让“记忆/PLAYBOOKS”的事实自动反映到 wiki 化的中文文档中，避免口径漂移。\n"
        "- 提供可落地的注释与背景，降低新成员理解成本。\n"
    )

    parts.append("\n## 我们发现了什么（依据）\n")
    parts.append(
        "> 注：以下为自动提取的信号，具体细节以原始文件为准。\n"
    )
    parts.append("### 运行健康（health.json）\n")
    parts.extend(_summarize_health(ROOT / "health.json"))
    parts.append("")
    parts.append("### 最近一次全流程运行（run_all_summary.json）\n")
    parts.extend(_summarize_run_all(ROOT / "run_all_summary.json"))
    parts.append("")
    parts.append("### 数据映射概况（mapping_report.json）\n")
    parts.extend(_summarize_mapping_report(ROOT / "mapping_report.json"))

    # 这次改了什么 & 影响
    parts.append("\n## 我们改了什么（What）\n")
    parts.append(
        "- 已将决策/配置/修复/改进等条目落在 PLAYBOOKS，并在相应文档的自动段进行同步（如有）。\n"
        "- 若本页与目标文档之间存在“引用”，则主文档会展示本页的核心段落。\n"
    )

    parts.append("\n## 影响范围（Impact）\n")
    parts.append(
        "- 文档：docs/ 下相关专题会出现“自动段落”或“引用 _自动 文件”的更新。\n"
        "- 运行：不改变业务流程，仅新增文档同步步骤；失败不影响主流程。\n"
    )

    parts.append("\n## 如何验证（Evidence）\n")
    parts.append(
        "- 证据来源：logs/*.log｜reports/*.json｜上述三份快照（health/run_all/mapping）。\n"
        "- 建议：如需更强的证据关联，可在 PLAYBOOKS 条目里加入 PR/任务/工单链接。\n"
    )

    parts.append("\n## 如需回滚（Rollback）\n")
    parts.append(
        "- 本脚本仅写入 docs/_自动/* 文件，删除相应文件或回退提交即可恢复。\n"
    )

    parts.append("\n## 关联链接\n")
    parts.append("- PLAYBOOKS 索引：docs/PLAYBOOKS/索引.md\n")
    parts.append("- 使用说明：docs/PLAYBOOKS/使用说明.md\n")

    parts.append("\n---\n")
    parts.append(
        f"> 生成器：scripts/dev/sync_wiki_from_playbooks.py｜时间：{now}\n"
        "> 若需要更口语的文案风格或额外栏目，请在 ISSUE/任务中注明关键词（如：‘加上风险评估’）。\n"
    )

    out = AUTO / "项目状态总览.md"
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")


def generate_open_questions() -> None:
    AUTO.mkdir(parents=True, exist_ok=True)
    src = PLAY / "开放问题与待澄清.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    parts: list[str] = []
    parts.append("# 开放问题清单（自动生成｜带注释）\n")
    parts.append(
        "> 说明：以下内容来源于 PLAYBOOKS/开放问题与待澄清.md，并加上阅读指引与状态语气。\n"
    )
    text = _read_text(src).strip()
    if text:
        parts.append("\n## 原始内容节选\n")
        # 仅节选前 100 行，避免过大
        head = "\n".join(text.splitlines()[:100])
        parts.append("\n" + head + "\n")
    else:
        parts.append("- 暂无开放问题记录（等待补充）。\n")

    parts.append("\n## 我们建议的下一步\n")
    parts.append("- 为每个问题补充：背景、影响面、决策门槛、到期时间与责任人。\n")

    parts.append("\n---\n")
    parts.append(f"> 生成器：sync_wiki_from_playbooks.py｜时间：{now}\n")

    out = AUTO / "开放问题清单.md"
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")


def generate_db_change_digest() -> None:
    AUTO.mkdir(parents=True, exist_ok=True)
    src = PLAY / "数据库变更记录.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    text = _read_text(src)
    lines = text.splitlines()
    # 抓取最近一个日期段落及若干条目
    date_line = ""
    items: list[str] = []
    for i, ln in enumerate(lines):
        if ln.strip().startswith("## ") and any(ch.isdigit() for ch in ln):
            date_line = ln.strip().lstrip("# ")
            # 收集接下来的 10 条
            j = i + 1
            while j < len(lines) and len(items) < 10:
                s = lines[j].strip()
                if s.startswith("## "):
                    break
                if s.startswith("-"):
                    items.append(s)
                j += 1
            break

    parts: list[str] = []
    parts.append("# 数据库变更摘要（自动生成｜含注释）\n")
    parts.append(
        "> 说明：从 PLAYBOOKS/数据库变更记录.md 提炼最近一组变更并加注释；详细以原文档为准。\n"
    )
    if date_line:
        parts.append(f"\n## 最近日期：{date_line}\n")
        if items:
            parts.append("- 条目节选：\n")
            parts.extend([f"  {it}" for it in items])
        else:
            parts.append("- 该日期暂无具体条目。\n")
    else:
        parts.append("- 暂未检索到日期段落。\n")

    parts.append("\n## 注释与提示\n")
    parts.append("- 若为结构性变更：请在 PLAYBOOKS 中补充回滚脚本位置与兼容策略。\n")

    parts.append("\n---\n")
    parts.append(f"> 生成器：sync_wiki_from_playbooks.py｜时间：{now}\n")

    out = AUTO / "数据库变更摘要.md"
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    generate_status_overview()
    generate_open_questions()
    generate_db_change_digest()
    print("[OK] 已生成 docs/_自动/ 下的 wiki 片段。")


if __name__ == "__main__":
    main()

