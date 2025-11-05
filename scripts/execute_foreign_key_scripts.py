#!/usr/bin/env python3
"""
执行外键约束SQL脚本

用途：执行P0和P1优先级的外键约束添加脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import Settings


def execute_sql_file(settings: Settings, sql_file: Path) -> None:
    """执行SQL文件"""
    print(f"\n{'='*80}")
    print(f"执行SQL脚本: {sql_file.name}")
    print(f"{'='*80}\n")
    
    # 读取SQL文件
    sql_content = sql_file.read_text(encoding='utf-8')
    
    # 执行SQL
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_content)
        conn.commit()
    
    print(f"\n✅ {sql_file.name} 执行成功\n")


def main():
    """主函数"""
    # 加载配置
    settings = Settings()
    
    # SQL脚本路径
    script_dir = project_root / "scripts" / "sql" / "validation"
    p0_script = script_dir / "P0_add_foreign_keys_comprehensive.sql"
    p1_script = script_dir / "P1_add_foreign_keys_comprehensive.sql"
    
    # 检查文件是否存在
    if not p0_script.exists():
        print(f"❌ 错误：找不到文件 {p0_script}")
        sys.exit(1)
    
    if not p1_script.exists():
        print(f"❌ 错误：找不到文件 {p1_script}")
        sys.exit(1)
    
    try:
        # 执行P0优先级脚本
        print("\n" + "="*80)
        print("阶段1：执行P0优先级脚本（立即执行）")
        print("="*80)
        execute_sql_file(settings, p0_script)
        
        # 执行P1优先级脚本
        print("\n" + "="*80)
        print("阶段2：执行P1优先级脚本（1个月内）")
        print("="*80)
        execute_sql_file(settings, p1_script)
        
        print("\n" + "="*80)
        print("✅ 所有外键约束添加完成")
        print("="*80)
        print("\n下一步：")
        print("  1. 验证外键约束是否正常工作")
        print("  2. 更新 prepare_dim 备份机制")
        print("  3. 测试 ID 更新时的级联行为")
        print()
        
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

