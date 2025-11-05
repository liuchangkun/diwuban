import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
RULES_CFG = ROOT / "rules" / "rules.yml"
MAPPING = ROOT / "configs" / "data_mapping.v2.json"

FAIL = 1
OK = 0


def fail(msg: str) -> int:
    print(f"[QUALITY_GATE][FAIL] {msg}")
    return FAIL


def ok(msg: str) -> int:
    print(f"[QUALITY_GATE][OK] {msg}")
    return OK


def warn(msg: str) -> None:
    print(f"[QUALITY_GATE][WARN] {msg}")


# 严格度：本地默认宽松，CI 可通过 QUALITY_POLICY_STRICT=1 开启严格
STRICT = os.getenv("QUALITY_POLICY_STRICT", "0") in {"1", "true", "TRUE"}


def _doc_contains(path: Path, markers: List[str]) -> List[str]:
    """返回文档中缺失的关键标记列表。"""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return markers[:]  # 无法读取视为全部缺失
    missing = [m for m in markers if m not in text]
    return missing


def _validate_mapping_v2(data: Dict[str, Any]) -> int:
    if not isinstance(data, dict):
        return fail("data_mapping.v2.json 顶层应为对象 {stations:[...]} ")
    stations = data.get("stations")
    if not isinstance(stations, list) or not stations:
        return fail("data_mapping.v2.json.stations 必须为非空数组")

    total_devices = 0
    total_metrics = 0
    total_files = 0
    violations: List[str] = []

    for s in stations:
        if not isinstance(s, dict) or not s.get("name"):
            return fail("每个站点需包含 name 字段")
        devices = s.get("devices")
        if not isinstance(devices, list) or not devices:
            return fail(f"站点 {s.get('name')} 的 devices 必须为非空数组")
        for d in devices:
            if not isinstance(d, dict) or not d.get("name"):
                return fail("每个设备需包含 name 字段")
            metrics = d.get("metrics")
            if not isinstance(metrics, list) or not metrics:
                return fail(f"设备 {d.get('name')} 的 metrics 必须为非空数组")
            total_devices += 1
            for m in metrics:
                if not isinstance(m, dict) or not m.get("key"):
                    return fail(f"设备 {d.get('name')} 的每个 metric 需包含 key 字段")
                files = m.get("files")
                if not isinstance(files, list) or not files:
                    return fail(
                        f"metric {d.get('name')}/{m.get('key')} 的 files 必须为非空数组"
                    )
                total_metrics += 1
                for f in files:
                    if not isinstance(f, str) or not f.strip():
                        return fail(
                            f"metric {d.get('name')}/{m.get('key')} 的文件名必须为非空字符串"
                        )
                    # 规则：files 中仅应为文件名，禁止携带 'data/' 前缀
                    if f.startswith("data/") or f.startswith("data\\"):
                        return fail(
                            f"文件名不应包含 'data/' 前缀：{f}（请仅保留文件名，实际读取统一从 data/ 目录）"
                        )
                    # 若包含路径分隔符则给出警告（允许未来支持子目录时放宽）
                    if "/" in f or "\\" in f:
                        violations.append(f"文件名包含路径分隔符（建议仅文件名）：{f}")
                    # 可选：存在性提示（不阻断）
                    data_file = ROOT / "data" / f
                    if not data_file.exists():
                        violations.append(f"data/ 下未找到文件：{f}")
                    total_files += 1

    ok(
        f"data_mapping.v2.json 结构有效：stations={len(stations)} devices~{total_devices} metrics~{total_metrics} files~{total_files}"
    )
    for v in violations[:20]:
        warn(v)
    if len(violations) > 20:
        warn(f"还有 {len(violations) - 20} 条额外提示已省略…")
    return OK


def main() -> int:
    # 必要配置存在性
    if not RULES_CFG.exists():
        return fail("rules/rules.yml 不存在（机读规则配置）")
    else:
        ok("rules/rules.yml 存在")

    if not MAPPING.exists():
        return fail("configs/data_mapping.v2.json 不存在（映射唯一来源）")
    else:
        ok("configs/data_mapping.v2.json 存在")

    # 结构检查：data_mapping.v2.json（标准 schema）
    try:
        mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    except Exception as e:
        return fail(f"configs/data_mapping.v2.json 解析失败: {e}")
    rc = _validate_mapping_v2(mapping)
    if rc != OK:
        return rc

    # 安全检查：提示忽略 venv/.venv 目录
    for banned in ("venv", ".venv", "env"):
        if (ROOT / banned).exists():
            ok(f"已检测到本地存在目录 '{banned}'；工具将忽略这些目录")

    # 关键文档存在性检查（与中文文档对齐）
    # OR 要求：README 或 项目概述与快速开始 至少其一存在
    readme_or = [
        ROOT / "docs" / "README.md",
        ROOT / "docs" / "项目概述与快速开始.md",
    ]
    if not any(p.exists() for p in readme_or):
        return fail(
            "缺少关键文档：docs/README.md 或 docs/项目概述与快速开始.md 至少其一"
        )

    docs_required = [
        ROOT / "docs" / "文档地图与导航.md",
        ROOT / "docs" / "体系结构总览.md",
        ROOT / "docs" / "架构落地计划_v1.md",
        ROOT / "docs" / "表结构与数据库.md",
        ROOT / "docs" / "数据库设计文档.md",
        ROOT / "docs" / "数据库函数参考.md",
        ROOT / "docs" / "程序工作流程.md",
        ROOT / "docs" / "编码规范.md",
        ROOT / "docs" / "日志规范.md",
        ROOT / "docs" / "应用接口说明.md",
        ROOT / "docs" / "配置说明.md",
        ROOT / "docs" / "测试指南.md",
        ROOT / "docs" / "行为约束.md",
        ROOT / "docs" / "个人工作守则.md",
        ROOT / "docs" / "严格模式-核对清单.md",
        ROOT / "docs" / "智能助手行为控制.md",
    ]
    missing = [str(p) for p in docs_required if not p.exists()]
    if missing:
        return fail("缺少关键文档：\n- " + "\n- ".join(missing))

    # 扩展类文档（可严格/可宽松）
    EXTENDED_STRICT = os.getenv("QUALITY_DOCS_EXTENDED", "0") in {"1", "true", "TRUE"}
    extended_docs = [
        ROOT / "docs" / "项目概述与快速开始.md",
        ROOT / "docs" / "项目技术选型.md",
        ROOT / "docs" / "体系结构总览.md",
        ROOT / "docs" / "架构落地计划_v1.md",
        ROOT / "docs" / "日志规范.md",
        ROOT / "docs" / "日志运维.md",
        ROOT / "docs" / "应用接口说明.md",
        ROOT / "docs" / "可视化.md",
        ROOT / "docs" / "性能基准与A_B验证.md",
        ROOT / "docs" / "数据质量与校验.md",
        ROOT / "docs" / "数据清理指南.md",
        ROOT / "docs" / "泵站时间对齐实现.md",
        ROOT / "docs" / "泵组优化.md",
        ROOT / "docs" / "特性曲线拟合.md",
        ROOT / "docs" / "曲线校验与评估.md",
        ROOT / "docs" / "CSV导入-使用指南.md",
        ROOT / "docs" / "缺失与补齐策略.md",
        ROOT / "docs" / "术语表与名词规范.md",
        ROOT / "docs" / "数据库设计文档.md",
        ROOT / "docs" / "数据库函数参考.md",
        ROOT / "docs" / "表结构明细_附录.md",
    ]
    missing_ext = [str(p) for p in extended_docs if not p.exists()]
    if missing_ext:
        msg = "缺少扩展类文档：\n- " + "\n- ".join(missing_ext)
        if EXTENDED_STRICT:
            return fail(msg)
        for m in missing_ext:
            warn(f"扩展文档缺失：{m}")

    # 关键内容点检查（扩展）：受 QUALITY_DOCS_MARKERS_STRICT 控制
    MARKERS_STRICT = os.getenv("QUALITY_DOCS_MARKERS_STRICT", "0") in {
        "1",
        "true",
        "TRUE",
    }

    def _check_markers(path: Path, markers: List[str], title: str) -> int:
        missing = _doc_contains(path, markers)
        if missing:
            msg = f"{title} 缺少关键点：{missing}"
            if MARKERS_STRICT:
                return fail(msg)
            warn(msg)
        return OK

    _check_markers(
        ROOT / "docs" / "日志规范.md", ["JSON", "UTC", "结构化", "脱敏"], "日志规范.md"
    )
    _check_markers(
        ROOT / "docs" / "配置说明.md", ["YAML", ".env", "环境变量"], "配置说明.md"
    )
    _check_markers(
        ROOT / "docs" / "应用接口说明.md",
        ["/api/", "分页", "错误码"],
        "应用接口说明.md",
    )
    _check_markers(
        ROOT / "docs" / "数据库设计文档.md",
        ["命名规范", "schema", "索引"],
        "数据库设计文档.md",
    )
    _check_markers(
        ROOT / "docs" / "测试指南.md", ["pytest", "coverage", "覆盖率"], "测试指南.md"
    )
    # Persona 规范轻校验（默认 WARN，可通过 QUALITY_PERSONA_STRICT=1 提升为 FAIL）
    PERSONA_STRICT = os.getenv("QUALITY_PERSONA_STRICT", "0") in {"1", "true", "TRUE"}

    def _load_persona_index(idx_path: Path) -> List[Dict[str, str]]:
        items: List[Dict[str, str]] = []
        if not idx_path.exists():
            warn("缺少 Persona 索引：docs/提示词/index.yaml（将跳过一致性校验）")
            return items
        lines = idx_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        cur: Dict[str, str] = {}
        for raw in lines:
            line = raw.strip()
            if line.startswith("- file:"):
                if cur:
                    items.append(cur)
                cur = {}
                cur["file"] = line.split(":", 1)[1].strip()
            elif line.startswith("name:") and cur is not None:
                cur["name"] = line.split(":", 1)[1].strip()
            elif line.startswith("title:") and cur is not None:
                cur["title"] = line.split(":", 1)[1].strip()
        if cur:
            items.append(cur)
        return items

    def _read_frontmatter(md_path: Path) -> Dict[str, str]:
        try:
            text = md_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return {}
        if not text.startswith("---"):
            return {}
        parts = text.split("---", 2)
        if len(parts) < 3:
            return {}
        fm_text = parts[1]
        meta: Dict[str, str] = {}
        for raw in fm_text.splitlines():
            if ":" in raw:
                k, v = raw.split(":", 1)
                meta[k.strip()] = v.strip()
        return meta

    persona_idx = _load_persona_index(ROOT / "docs" / "提示词" / "index.yaml")
    if persona_idx:
        REQUIRED_FRONTMATTER = [
            "name",
            "title",
            "description",
            "triggers",
            "inputs",
            "outputs",
            "guardrails",
            "tools",
            "risk_level",
            "references",
        ]
        REQUIRED_SECTIONS = [
            "## 角色定位与适用范围",
            "## 使用前置",
            "## 输入模板",
            "## 输出模板",
            "## 步骤与工具配方",
            "## 工具白名单",
            "## 完成定义（Definition of Done）",
            "## 不适用场景/升级路径",
            "## 审计与留痕",
            "## 常见误用与边界",
        ]

        # 1) 索引文件与前言元数据一致性
        for item in persona_idx:
            rel = item.get("file", "")
            p = ROOT / rel
            if not p.exists():
                msg = f"Persona 索引中的文件不存在：{rel}"
                if PERSONA_STRICT:
                    return fail(msg)
                warn(msg)
                continue
            fm = _read_frontmatter(p)
            if not fm:
                msg = f"Persona 文档缺少 frontmatter：{rel}"
                if PERSONA_STRICT:
                    return fail(msg)
                warn(msg)
            else:
                for key in REQUIRED_FRONTMATTER:
                    if key not in fm or not fm.get(key):
                        msg = f"Persona frontmatter 缺字段 {key}：{rel}"
                        if PERSONA_STRICT:
                            return fail(msg)
                        warn(msg)
                # name 与索引一致性
                idx_name = (item.get("name") or "").strip().strip("\"')")
                fm_name = (fm.get("name") or "").strip().strip("\"')")
                if idx_name and fm_name and idx_name != fm_name:
                    msg = f"Persona name 不一致：index={idx_name} vs file={fm_name}（{rel}）"
                    if PERSONA_STRICT:
                        return fail(msg)
                    warn(msg)

            # 2) 统一小节存在性
            missing_sections = _doc_contains(p, REQUIRED_SECTIONS)
            if missing_sections:
                msg = f"Persona 缺少统一小节：{rel} -> {missing_sections}"
                if PERSONA_STRICT:
                    return fail(msg)
                warn(msg)

        # 3) 目录下遗留未纳入索引的 Persona 文件（温和提醒）
        persona_dir = ROOT / "提示词"
        if persona_dir.exists():
            all_md = {
                str(x.relative_to(ROOT)).replace("\\", "/")
                for x in persona_dir.glob("*.md")
            }
            indexed = {item.get("file", "") for item in persona_idx}
            orphan = sorted(all_md - indexed)
            if orphan:
                warn(
                    "Persona 目录存在未纳入索引的文件（如为别名/元角色可忽略）：\n- "
                    + "\n- ".join(orphan)
                )

        ok(
            "Persona 规范轻校验完成（默认 WARN，可设 QUALITY_PERSONA_STRICT=1 强化为 FAIL）"
        )

    # ADR 目录检查
    adr_dir = ROOT / "docs" / "ADR"
    if adr_dir.exists():
        adr_files = list(adr_dir.glob("*.md"))
        if not adr_files:
            if EXTENDED_STRICT:
                return fail("ADR 目录存在但为空（需至少一条架构决策记录）")
            warn("ADR 目录存在但为空（建议补充至少一条决策记录）")
    else:
        if EXTENDED_STRICT:
            return fail("缺少 ADR 目录（docs/ADR）")
        warn("缺少 ADR 目录（docs/ADR）")

    # 管家文档存在性检查（PLAYBOOKS + 行为规范）
    butler_docs = [
        ROOT / "docs" / "PLAYBOOKS" / "索引.md",
        ROOT / "docs" / "PLAYBOOKS" / "使用说明.md",
        ROOT / "docs" / "PLAYBOOKS" / "安全与授权记录.md",
        ROOT / "docs" / "PLAYBOOKS" / "配置变更记录.md",
        ROOT / "docs" / "PLAYBOOKS" / "运行手册变更.md",
        ROOT / "docs" / "PLAYBOOKS" / "事故与演练复盘.md",
        ROOT / "docs" / "PLAYBOOKS" / "开放问题与待澄清.md",
        ROOT / "docs" / "PLAYBOOKS" / "风险与技术债务清单.md",
    ]
    missing_butler = [str(p) for p in butler_docs if not p.exists()]
    if missing_butler:
        return fail("缺少管家文档：\n- " + "\n- ".join(missing_butler))
    else:
        ok("管家文档存在性检查通过")

    # 关键内容检查（严格度可控）
    coding_doc = ROOT / "docs" / "编码规范.md"
    coding_markers = ["类型注解", "mypy", "SQL", "%s", "行宽", "100"]
    missing_coding = _doc_contains(coding_doc, coding_markers)
    if missing_coding:
        msg = f"编码规范缺少关键点：{missing_coding}"
        if STRICT:
            return fail(msg)
        warn(msg)

    behavior_docs = [
        ROOT / "docs" / "行为约束.md",
        ROOT / "docs" / "智能助手行为控制.md",
    ]
    behavior_markers = ["低风险", "中风险", "高风险", "禁止", "MCP"]
    for bd in behavior_docs:
        if bd.exists():
            miss = _doc_contains(bd, behavior_markers)
            if miss:
                msg = f"{bd.name} 缺少关键点：{miss}"
                if STRICT:
                    return fail(msg)
                warn(msg)

    else:
        ok("关键文档存在性检查通过")

    # 经验库存在性检查（中文）
    playbooks = [
        ROOT / "docs" / "PLAYBOOKS" / "错误与修复记录.md",
        ROOT / "docs" / "PLAYBOOKS" / "改进与优化记录.md",
        ROOT / "docs" / "PLAYBOOKS" / "决策记录.md",
    ]
    pb_missing = [str(p) for p in playbooks if not p.exists()]
    if pb_missing:
        return fail("缺少经验库文档：\n- " + "\n- ".join(pb_missing))
    else:
        ok("经验库文档存在性检查通过")

    # PR 场景温和提醒（如可用）
    event_name = os.getenv("GITHUB_EVENT_NAME", "").lower()
    pr_title = ""
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if event_name == "pull_request" and event_path and Path(event_path).exists():
        try:
            payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
            pr_title = (payload.get("pull_request", {}) or {}).get("title", "")
        except Exception:
            pr_title = ""
    pr_lower = pr_title.lower()
    if any(k in pr_lower for k in ("fix", "bug", "hotfix")):
        print("[QUALITY_GATE][INFO] 检测到疑似修复类 PR，请确认：")
        print(" - 已更新 docs/PLAYBOOKS/错误与修复记录.md 条目并在 PR 勾选（附链接）")
        print(" - 回归测试是否新增/更新（若未更新请在 PR 说明原因）")
    if any(k in pr_lower for k in ("improvement", "perf", "optimize", "refactor")):
        print("[QUALITY_GATE][INFO] 检测到疑似改进类 PR，请确认：")
        print(" - 已更新 docs/PLAYBOOKS/改进与优化记录.md 条目并在 PR 勾选（附链接）")
    # 自定义轻量规则：端点分页排序与连接复用、文档关键内容点
    try:
        ds_path = ROOT / "app" / "api" / "v1" / "endpoints" / "data_timeseries.py"
        if ds_path.exists():
            txt = ds_path.read_text(encoding="utf-8", errors="ignore")
            # 1) 原始端点 ORDER BY 检查（仅 WARN）
            if (
                "FROM public.get_station_devices_metrics_by_time_range" in txt
                and "ORDER BY record_timestamp" not in txt
            ):
                warn(
                    "/stations/{station_id}/raw 可能缺少 ORDER BY record_timestamp（仅提示）"
                )
            if (
                "FROM public.get_device_metrics_by_time_range" in txt
                and "ORDER BY record_timestamp" not in txt
            ):
                warn(
                    "/devices/{device_id}/raw 可能缺少 ORDER BY record_timestamp（仅提示）"
                )
            # 2) 重复连接（conn2）提示
            if "conn2" in txt or "with get_conn(settings) as conn2" in txt:
                warn(
                    "检测到疑似重复获取连接（conn2），建议在同一请求内复用同一连接/事务快照"
                )
        else:
            warn("未找到 app/api/v1/endpoints/data_timeseries.py，跳过端点规则检查")
    except Exception as e:
        warn(f"端点规则检查异常：{e}")

    # 文档关键内容点存在性（仅 WARN）
    try:
        doc_checks = [
            (ROOT / "docs" / "日志规范.md", "日志规范.md"),
            (ROOT / "docs" / "测试指南.md", "测试指南.md"),
            (ROOT / "docs" / "配置说明.md", "配置说明.md"),
            (ROOT / "docs" / "数据质量与校验.md", "数据质量与校验.md"),
            (ROOT / "docs" / "程序工作流程.md", "程序工作流程.md"),
        ]
        for p, title in doc_checks:
            if p.exists():
                miss = _doc_contains(
                    p, ["关键内容点", "质量门", "轻校验"]
                )  # 任意关键词
                if len(miss) == 3:
                    # 三个都缺失才提示，避免误报
                    warn(f"{title} 建议补充 ‘关键内容点（用于质量门轻校验）’ 小节")
            else:
                warn(f"缺少文档：{title}（无法进行关键内容点检查）")
    except Exception as e:
        warn(f"文档关键内容点检查异常：{e}")

        print(" - 若涉及设计策略，请同步 ADR")

    print("[QUALITY_GATE] 所有检查通过")
    return OK


if __name__ == "__main__":
    sys.exit(main())
