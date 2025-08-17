#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memory_index.py（中文化 PLAYBOOKS 兼容版）

第一优先级：核心功能
- 解析以下中文 PLAYBOOKS 文件，提取记录条目（YAML front matter）：
  - docs/PLAYBOOKS/决策记录.md
  - docs/PLAYBOOKS/配置变更记录.md
  - docs/PLAYBOOKS/改进与优化记录.md
  - docs/PLAYBOOKS/经验教训.md
  - docs/PLAYBOOKS/性能基准.md
- 获取字段：id、date、summary
- 按 date 降序取最新 10 条
- 更新 docs/文档地图与导航.md 中 <!-- memory_index:BEGIN --> 与 <!-- memory_index:END --> 之间内容
  格式：- YYYY-MM-DD [TYPE-SEQ] 摘要，例如：- 2025-08-16 [DEC-009] 文档体系中文化重构与归档迁移

实现细节
- 仅使用标准库；UTF-8 读写；详细日志输出；鲁棒错误处理
"""

import os
import re
import sys
from datetime import datetime
from typing import List, Optional, Tuple

# 常量
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
NAV_PATH = os.path.join(ROOT, "docs", "文档地图与导航.md")
PLAYBOOKS_DIR = os.path.join(ROOT, "docs", "PLAYBOOKS")
PLAYBOOK_FILES = [
    os.path.join(PLAYBOOKS_DIR, "决策记录.md"),
    os.path.join(PLAYBOOKS_DIR, "配置变更记录.md"),
    os.path.join(PLAYBOOKS_DIR, "改进与优化记录.md"),
    os.path.join(PLAYBOOKS_DIR, "经验教训.md"),
    os.path.join(PLAYBOOKS_DIR, "性能基准.md"),
]

# 兼容三种 front matter 形态：
# 1) 典型 YAML: ---\nkey: val\n---
# 2) 单行标题包含键值（"## id: ... date: ... summary: ..."）
# 3) 下划线分隔线 + 下一行为以 "## id:" 开头的行
FRONT_MATTER_RE = re.compile(r"---\s*\r?\n(.*?)\r?\n---", re.DOTALL)
SINGLELINE_ENTRY_RE = re.compile(
    r"^##\s+id:\s*(?P<id>[^\s]+).*?date:\s*(?P<date>\d{4}-\d{2}-\d{2}).*?summary:\s*(?P<summary>.+)$"
)
UNDERLINE_SPLIT_RE = re.compile(r"^_{6,}$")
ID_RE = re.compile(r"^([A-Z]+)-(\d{8})-(\d+)$")
DATE_FMT = "%Y-%m-%d"
BEGIN_MARK = "<!-- memory_index:BEGIN -->"
END_MARK = "<!-- memory_index:END -->"
# 兼容 mdformat 等工具生成的表头分隔线（允许空格与多横线）
HEADER_SEP_RE = re.compile(r"^\|\s*-+\s*\|\s*-+\s*\|\s*-+\s*\|\s*-+\s*\|")


def _supports_utf8() -> bool:
    try:
        enc = (sys.stdout.encoding or "").lower()
        if "utf" in enc:
            return True
    except Exception:
        pass
    if os.environ.get("PYTHONUTF8") == "1":
        return True
    try:
        import locale

        loc = (locale.getpreferredencoding(False) or "").lower()
        if "utf" in loc:
            return True
    except Exception:
        pass
    return False


def log(msg: str) -> None:
    # 自动探测 UTF-8 支持：支持则输出中文，否则回退 ASCII
    if _supports_utf8():
        print(f"[memory_index] {msg}")
    else:
        safe = msg.encode("ascii", "ignore").decode("ascii")
        print(f"[memory_index] {safe}")


def parse_front_matter(block: str) -> Optional[Tuple[str, str, str]]:
    """从 front matter 文本块解析 (id, date, summary)。失败返回 None。"""
    # 简单 YAML 行解析（仅三字段，避免引入依赖）
    id_val = date_val = summary_val = None
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("id:"):
            id_val = line.split(":", 1)[1].strip()
        elif line.startswith("date:"):
            date_val = line.split(":", 1)[1].strip()
        elif line.startswith("summary:"):
            summary_val = line.split(":", 1)[1].strip()
    if not id_val or not summary_val:
        return None
    # 过滤模板占位：包含 YYYY/XXX 的直接忽略
    if "YYYY" in id_val or "XXX" in id_val:
        return None
    # 允许 id 形如 DEC-20250816-009 / CONF-20250115-004 / IMP-2025... / LES-... / BENCH-... / PERF-...
    if not ID_RE.match(id_val):
        return None
    # 处理日期：优先使用 date 字段，否则从 id 中提取
    if date_val:
        try:
            # 校验格式
            _ = datetime.strptime(date_val, DATE_FMT)
        except Exception:
            # 无法解析则尝试从 id 推断
            m = ID_RE.match(id_val)
            if not m:
                return None
            ymd = m.group(2)
            date_val = f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]}"
    else:
        m = ID_RE.match(id_val)
        if not m:
            return None
        ymd = m.group(2)
        date_val = f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]}"
    return id_val, date_val, summary_val


def collect_entries() -> List[Tuple[str, str, str]]:
    entries: List[Tuple[str, str, str]] = []
    for f in PLAYBOOK_FILES:
        if not os.path.exists(f):
            log(f"警告：文件不存在，跳过 {os.path.relpath(f, ROOT)}")
            continue
        try:
            with open(f, "r", encoding="utf-8") as fp:
                text = fp.read()
        except Exception as e:
            log(f"错误：读取失败 {os.path.relpath(f, ROOT)}: {e}")
            continue
        # 1) YAML front matter
        blocks = FRONT_MATTER_RE.findall(text)
        yaml_count = 0
        for b in blocks:
            tpl = parse_front_matter(b)
            if tpl is None:
                continue
            entries.append(tpl)
            yaml_count += 1
        # 2) 单行 "## id: ... date: ... summary: ..."
        single_count = 0
        for line in text.splitlines():
            m = SINGLELINE_ENTRY_RE.match(line.strip())
            if m:
                id_val = m.group("id").strip()
                date_val = m.group("date").strip()
                summary_val = m.group("summary").strip()
                entries.append((id_val, date_val, summary_val))
                single_count += 1
        log(
            f"文件 {os.path.relpath(f, ROOT)} front matter 块 {yaml_count}，单行条目 {single_count}"
        )
    return entries


def sort_and_limit(
    entries: List[Tuple[str, str, str]], limit: int = 10
) -> List[Tuple[str, str, str]]:
    def key_fn(t: Tuple[str, str, str]):
        # t = (id, date, summary)
        try:
            dt = datetime.strptime(t[1], DATE_FMT)
        except Exception:
            dt = datetime.min
        return (-dt.timestamp(), t[0])

    entries_sorted = sorted(entries, key=key_fn)
    return entries_sorted[:limit]


def format_line(entry: Tuple[str, str, str]) -> str:
    id_val, date_val, summary = entry
    m = ID_RE.match(id_val)
    if not m:
        type_code, seq = "UNK", "000"
    else:
        type_code = m.group(1)
        seq = m.group(3)
        # 统一 3 位显示
        try:
            seq = f"{int(seq):03d}"
        except Exception:
            pass
    return f"- {date_val} [{type_code}-{seq}] {summary}"


def _normalize_nav_lines(seg: str) -> List[str]:
    lines: List[str] = []
    for line in seg.splitlines():
        s = line.strip()
        if not s or not s.startswith("-"):
            continue
        # 去除转义差异与多空白差异
        s = s.replace(r"\_", "_")
        s = s.replace(r"\[", "[").replace(r"\]", "]")
        s = re.sub(r"\s+", " ", s)
        lines.append(s)
    return lines


def update_nav(latest_lines: List[str]) -> None:
    # 读取导航文件
    if not os.path.exists(NAV_PATH):
        raise FileNotFoundError(f"导航文件不存在：{os.path.relpath(NAV_PATH, ROOT)}")
    with open(NAV_PATH, "r", encoding="utf-8") as fp:
        nav_text = fp.read()
    b = nav_text.find(BEGIN_MARK)
    e = nav_text.find(END_MARK)
    if b == -1 or e == -1 or e < b:
        raise RuntimeError("未找到 memory_index 标记区，或标记顺序错误。")
    # 现有片段（不含标记）
    current_seg = nav_text[b + len(BEGIN_MARK) : e]
    want_seg = "\n" + "\n".join(latest_lines) + "\n"
    # 语义级比较（忽略转义与空白差异）
    if _normalize_nav_lines(current_seg) == _normalize_nav_lines(want_seg):
        log("导航文件无变更（语义一致），跳过写入。")
        return
    # 计算替换区域（保留标记本身），采用稳定的换行约定
    before = nav_text[: b + len(BEGIN_MARK)]
    after = nav_text[e:]
    new_text = before + want_seg + after
    with open(NAV_PATH, "w", encoding="utf-8", newline="\n") as fp:
        fp.write(new_text)
    log(
        f"已更新最近变更区域（{len(latest_lines)} 条）→ {os.path.relpath(NAV_PATH, ROOT)}"
    )


def _parse_index_rows(text: str) -> List[Tuple[str, str, str, str]]:
    """解析已存在的索引表，返回 (date, type_code, seq, summary) 列表。"""
    rows: List[Tuple[str, str, str, str]] = []
    started = False
    for line in text.splitlines():
        s = line.strip()
        if not started:
            # 识别表头分隔线：兼容 "|---|---|" 以及 "| ----- | --- |" 等样式
            if s.startswith("|---") or HEADER_SEP_RE.match(s):
                started = True
            continue
        if not s.startswith("|"):
            # 表结束
            break
        # 去除两侧竖线，并按竖线分列
        parts = [p.strip() for p in s.strip("|").split("|")]
        if len(parts) < 4:
            continue
        date_val, type_code, seq, summary = parts[0], parts[1], parts[2], parts[3]
        # 反向转义，恢复语义（与写入时的转义对应）；宽松处理多重反斜杠
        summary = re.sub(r"\\+\|", "|", summary)
        summary = re.sub(r"\\+_", "_", summary)
        rows.append((date_val, type_code, seq, summary))
    return rows


def _normalize_summary_for_compare(s: str) -> str:
    # 比较时将转义的下划线与管道恢复为语义等价形式，避免不同格式器来回改写
    s2 = re.sub(r"\\+_", "_", s)
    s2 = re.sub(r"\\+\|", "|", s2)
    # 归一化空白
    s2 = re.sub(r"\s+", " ", s2).strip()
    return s2


def write_index_md(entries: List[Tuple[str, str, str]], path: str) -> None:
    # 构造期望的记录行（语义级比较以避免与 mdformat 互相改写）
    want_rows: List[Tuple[str, str, str, str]] = []
    for id_val, date_val, summary in entries:
        m = ID_RE.match(id_val)
        if m:
            type_code = m.group(1)
            seq = m.group(3)
        else:
            type_code, seq = "UNK", id_val
        want_rows.append((date_val, type_code, str(seq), summary))

    # 若旧文件存在且语义等价，则保留旧格式（不写入）
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fp:
                old_text = fp.read()
            old_rows = _parse_index_rows(old_text)
            # 归一化目标行用于比较（去除下划线与管道的转义差异）
            want_rows_cmp = [
                (d, t, s, _normalize_summary_for_compare(sumy))
                for (d, t, s, sumy) in want_rows
            ]
            if old_rows == want_rows_cmp:
                log(
                    f"索引未变化（保留现有排版）：{os.path.relpath(path, ROOT)}（{len(entries)} 条）"
                )
                return
        except Exception:
            pass

    # 否则按标准模板输出（mdformat 会按需美化表格对齐）
    lines = [
        "# PLAYBOOKS 索引（自动生成）",
        "",
        "| 日期 | 类型 | 编号 | 摘要 |",
        "|---|---|---|---|",
    ]
    for date_val, type_code, seq, summary in want_rows:
        # 仅转义管道符，避免与 mdformat 在下划线转义上互相改写
        esc = summary.replace("|", r"\|")
        lines.append(f"| {date_val} | {type_code} | {seq} | {esc} |")
    content = "\n".join(lines) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fp:
        fp.write(content)
    log(f"已生成索引文件：{os.path.relpath(path, ROOT)}（{len(entries)} 条）")


def main() -> int:
    log("开始收集 PLAYBOOKS 条目…")
    entries = collect_entries()
    log(f"有效条目总数：{len(entries)}")
    if not entries:
        log("没有可用条目，最近变更区域将被清空。")
    latest = sort_and_limit(entries, 10)
    lines = [format_line(t) for t in latest]
    try:
        update_nav(lines)
    except Exception as e:
        log(f"错误：更新导航失败：{e}")
        return 1
    # 生成索引文件（全量，按时间降序）
    full_sorted = sort_and_limit(entries, limit=len(entries))
    write_index_md(full_sorted, os.path.join(PLAYBOOKS_DIR, "INDEX.md"))
    log("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
