"""
修复 metric_key 大小写不一致问题

执行 scripts/sql/fix_metric_key_case.sql
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings
from app.core.logging.setup import init_logging


def main():
    """执行 metric_key 大小写修复"""
    print("=" * 80)
    print("修复 metric_key 大小写不一致问题")
    print("=" * 80)
    print()
    
    # 初始化
    init_logging()
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    print("✅ 系统初始化成功\n")
    
    # 步骤1：检查问题范围
    print("📋 步骤1：检查问题范围")
    with get_connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT id, metric_key
                FROM dim_metric_config
                WHERE metric_key != LOWER(metric_key)
                ORDER BY id
            """
            cur.execute(query)
            rows = cur.fetchall()
            
            if not rows:
                print("✅ 没有发现大小写不一致的 metric_key")
                return 0
            
            print(f"⚠️  发现 {len(rows)} 个大小写不一致的 metric_key:")
            for row in rows:
                metric_id, metric_key = row
                print(f"   ID {metric_id}: {metric_key} -> {metric_key.lower()}")
            print()
    
    # 步骤2：执行修复SQL
    print("📋 步骤2：执行修复SQL")
    sql_file = project_root / "scripts" / "sql" / "fix_metric_key_case.sql"
    if not sql_file.exists():
        print(f"❌ SQL文件不存在: {sql_file}")
        return 1
    
    sql_content = sql_file.read_text(encoding="utf-8")
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 执行SQL（包含事务）
                cur.execute(sql_content)

                # 获取修复结果
                results = cur.fetchall()
                if results:
                    print("\n修复结果:")
                    for row in results:
                        metric_id, metric_key, status = row
                        print(f"   ID {metric_id}: {metric_key} - {status}")

        print("\n✅ SQL执行成功！")
    except Exception as e:
        print(f"❌ SQL执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 步骤3：验证修复结果
    print("\n📋 步骤3：验证修复结果")
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 检查是否还有大小写不一致的 metric_key
            query = """
                SELECT COUNT(*)
                FROM dim_metric_config
                WHERE metric_key != LOWER(metric_key)
            """
            cur.execute(query)
            count = cur.fetchone()[0]
            
            if count > 0:
                print(f"❌ 仍有 {count} 个 metric_key 存在大小写不一致问题")
                return 1
            else:
                print("✅ 所有 metric_key 已统一为小写格式")
            
            # 验证修复的两个 metric_key
            query = """
                SELECT id, metric_key
                FROM dim_metric_config
                WHERE id IN (13, 61)
                ORDER BY id
            """
            cur.execute(query)
            rows = cur.fetchall()
            
            print("\n修复后的 metric_key:")
            for row in rows:
                metric_id, metric_key = row
                print(f"   ID {metric_id}: {metric_key}")
    
    print("\n" + "=" * 80)
    print("✅ metric_key 大小写修复完成！")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

