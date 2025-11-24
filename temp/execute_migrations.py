#!/usr/bin/env python3
"""执行迁移脚本"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn

def execute_migration(sql_file: Path):
    """执行单个迁移脚本"""
    if not sql_file.exists():
        print(f"❌ 文件不存在: {sql_file}")
        return False
    
    print(f"📄 读取SQL文件: {sql_file}")
    sql_content = sql_file.read_text(encoding='utf-8')
    
    # 移除psql特定命令
    lines = sql_content.split('\n')
    filtered_lines = [line for line in lines if not line.strip().startswith('\\')]
    sql_content = '\n'.join(filtered_lines)
    
    settings = load_settings(project_root / "configs")
    
    try:
        with get_conn(settings) as conn:
            # 先提交当前事务
            try:
                conn.commit()
            except:
                pass
            # 设置自动提交模式
            conn.autocommit = True
            with conn.cursor() as cur:
                print("🔄 执行SQL...")
                cur.execute(sql_content)
                print("✅ SQL执行成功")
        return True
    except Exception as e:
        print(f"❌ SQL执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("=" * 80)
    print("执行迁移脚本")
    print("=" * 80)
    print()
    
    # 迁移脚本列表
    migrations = [
        project_root / "scripts/sql/migrations/069_fix_fn_running_state_1s_remove_quality_status.sql",
        project_root / "scripts/sql/migrations/070_create_sp_refresh_device_running_thresholds_timing_v2.sql",
    ]
    
    success_count = 0
    for migration in migrations:
        print(f"\n{'='*80}")
        print(f"执行迁移: {migration.name}")
        print(f"{'='*80}")
        if execute_migration(migration):
            success_count += 1
        else:
            print(f"⚠️ 迁移失败，继续执行下一个...")
    
    print(f"\n{'='*80}")
    print(f"迁移完成: {success_count}/{len(migrations)} 成功")
    print(f"{'='*80}")
    
    return 0 if success_count == len(migrations) else 1

if __name__ == "__main__":
    sys.exit(main())

