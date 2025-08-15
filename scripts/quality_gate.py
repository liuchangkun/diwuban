import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES_DOC = ROOT / "PROJECT_RULES.md"
RULES_CFG = ROOT / "rules" / "rules.yml"
MAPPING = ROOT / "config" / "data_mapping.json"

FAIL = 1
OK = 0


def fail(msg: str) -> int:
    print(f"[QUALITY_GATE][FAIL] {msg}")
    return FAIL


def ok(msg: str) -> int:
    print(f"[QUALITY_GATE][OK] {msg}")
    return OK


def main() -> int:
    # R1.1 必要文件存在性检查
    if not RULES_DOC.exists():
        return fail("PROJECT_RULES.md 不存在（R1.1/工程规范）")
    else:
        ok("PROJECT_RULES.md 存在")

    if not RULES_CFG.exists():
        return fail("rules/rules.yml 不存在（机读规则配置）")
    else:
        ok("rules/rules.yml 存在")

    if not MAPPING.exists():
        return fail("config/data_mapping.json 不存在（R1.1 映射唯一来源）")
    else:
        ok("config/data_mapping.json 存在")

    # 基础结构检查：data_mapping.json 是合法 JSON
    try:
        mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
        if not isinstance(mapping, dict) or not mapping:
            return fail("data_mapping.json 需为非空对象")
        ok("data_mapping.json 为合法 JSON 且非空")
    except Exception as e:
        return fail(f"data_mapping.json 解析失败: {e}")

    # 粗检 key 层级
    # 顶层为站点；第二层为设备；第三层为 metric->文件列表
    for station, devices in mapping.items():
        if not isinstance(devices, dict):
            return fail(f"站点 '{station}' 的值应为对象（设备集合）")
        for device, metrics in devices.items():
            if not isinstance(metrics, dict):
                return fail(f"设备 '{device}' 的值应为对象（metric 映射）")
            for metric, files in metrics.items():
                if not isinstance(files, list):
                    return fail(f"metric '{station}/{device}/{metric}' 的值应为文件路径数组")
                # 路径检查：必须位于 data/ 目录（不真正读取文件，仅检查前缀）
                for f in files:
                    if not isinstance(f, str) or not f.startswith("data/"):
                        return fail(f"文件路径需以 'data/' 开头：{f}")
    ok("data_mapping.json 结构与路径前缀检查通过")

    # 补充建议：若存在压力/流量单位，提醒核对与 rules.yml 一致
    units_cfg = (ROOT / "rules" / "rules.yml").read_text(encoding="utf-8", errors="ignore")
    if "pressure: \"kPa\"" not in units_cfg and "pressure: 'kPa'" not in units_cfg:
        print("[QUALITY_GATE][WARN] 建议将压力单位设为 kPa（或在 PROJECT_RULES.md 中注明差异与换算）")

    # 安全检查：避免访问 venv/.venv（仅提示，真正访问由调用方控制）
    for banned in ("venv", ".venv", "env"):
        if (ROOT / banned).exists():
            ok(f"已检测到本地存在目录 '{banned}'；工具将忽略这些目录")

    # 关键文档存在性检查（docs/*）
    docs_required = [
        ROOT / "docs" / "DATA_SPEC.md",
        ROOT / "docs" / "SCHEMA_AND_DB.md",
        ROOT / "docs" / "ALIGNMENT_POLICY.md",
        ROOT / "docs" / "QUALITY_VALIDATION.md",
        ROOT / "docs" / "DERIVATIONS.md",
        ROOT / "docs" / "FITTING_MODELS.md",
        ROOT / "docs" / "OPTIMIZATION.md",
        ROOT / "docs" / "VIZ_SPEC.md",
        ROOT / "docs" / "ENGINEERING_STANDARDS.md",
        ROOT / "docs" / "RUNBOOK.md",
        ROOT / "docs" / "TESTING_STRATEGY.md",
        ROOT / "docs" / "GLOSSARY.md",
        ROOT / "docs" / "MCP_WORKFLOW.md",
    ]
    missing = [str(p) for p in docs_required if not p.exists()]
    if missing:
        return fail("缺少关键文档：\n- " + "\n- ".join(missing))
    else:
        ok("关键文档存在性检查通过")

    # 经验库存在性检查
    playbooks = [
        ROOT / "docs" / "PLAYBOOKS" / "ERROR_FIX_LOG.md",
        ROOT / "docs" / "PLAYBOOKS" / "IMPROVEMENTS.md",
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
        print(" - 已更新 docs/PLAYBOOKS/ERROR_FIX_LOG.md 条目并在 PR 勾选（附链接）")
        print(" - 回归测试是否新增/更新（若未更新请在 PR 说明原因）")
    if any(k in pr_lower for k in ("improvement", "perf", "optimize", "refactor")):
        print("[QUALITY_GATE][INFO] 检测到疑似改进类 PR，请确认：")
        print(" - 已更新 docs/PLAYBOOKS/IMPROVEMENTS.md 条目并在 PR 勾选（附链接）")
        print(" - 若涉及设计策略，请同步 ADR")

    print("[QUALITY_GATE] 所有检查通过")
    return OK


if __name__ == "__main__":
    sys.exit(main())

