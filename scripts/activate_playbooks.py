#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLAYBOOKS 机制激活脚本
用于在新会话开始时快速激活 PLAYBOOKS 自动化机制
"""


def show_activation_status():
    """显示 PLAYBOOKS 机制激活状态"""
    print("🤖 PLAYBOOKS 自动化机制激活检查")
    print("=" * 50)

    # 检查文件存在性
    from pathlib import Path

    playbooks_dir = Path("docs/PLAYBOOKS")
    required_files = [
        "ERROR_FIX_LOG.md",
        "IMPROVEMENTS.md",
        "DECISIONS.md",
        "LESSONS_LEARNED.md",
        "PERFORMANCE_BENCHMARKS.md",
        "CONFIGURATION_CHANGES.md",
    ]

    print("\n📁 PLAYBOOKS 文件检查:")
    all_files_exist = True
    for file_name in required_files:
        file_path = playbooks_dir / file_name
        if file_path.exists():
            print(f"  ✅ {file_name}")
        else:
            print(f"  ❌ {file_name} - 缺失")
            all_files_exist = False

    # 检查工具脚本
    print("\n🔧 工具脚本检查:")
    scripts_dir = Path("scripts")
    tool_scripts = [
        "auto_playbooks_check.py",
        "playbooks_search.py",
        "playbooks_stats.py",
    ]

    all_scripts_exist = True
    for script_name in tool_scripts:
        script_path = scripts_dir / script_name
        if script_path.exists():
            print(f"  ✅ {script_name}")
        else:
            print(f"  ❌ {script_name} - 缺失")
            all_scripts_exist = False

    # 统计记录数量
    if all_files_exist:
        print("\n📊 记录统计:")
        total_records = 0
        for file_name in required_files:
            file_path = playbooks_dir / file_name
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    record_count = content.count("---\nid:")
                    print(f"  {file_name}: {record_count} 条记录")
                    total_records += record_count
            except Exception as e:
                print(f"  {file_name}: 读取失败 - {e}")

        print(f"\n📈 总记录数: {total_records}")

    # 激活状态
    print("\n🚀 激活状态:")
    if all_files_exist and all_scripts_exist:
        print("  ✅ PLAYBOOKS 机制完整，可以激活")
        print("\n💡 使用方法:")
        print("  1. 对 AI 说：'按照 PLAYBOOKS 自动化机制工作'")
        print("  2. AI 会自动检查相关历史记录")
        print("  3. 完成工作后 AI 会自动记录")

        print("\n🔍 手动工具使用:")
        print("  python scripts/playbooks_search.py --tag 'database'")
        print("  python scripts/playbooks_stats.py --summary")
        print("  python scripts/auto_playbooks_check.py database postgresql")
    else:
        print("  ❌ PLAYBOOKS 机制不完整，需要修复")

    print("\n" + "=" * 50)


def show_quick_commands():
    """显示快速命令"""
    print("\n🚀 PLAYBOOKS 快速命令:")
    print("  搜索记录: python scripts/playbooks_search.py --keyword '关键词'")
    print("  查看统计: python scripts/playbooks_stats.py --summary")
    print("  检查历史: python scripts/auto_playbooks_check.py 关键词1 关键词2")
    print("  激活机制: 对 AI 说 'PLAYBOOKS 自动化机制激活'")


if __name__ == "__main__":
    show_activation_status()
    show_quick_commands()
