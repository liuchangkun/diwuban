#!/usr/bin/env python3
"""执行迁移脚本068：修改fn_running_state_1s函数使用fusion_threshold字段"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader import load_settings
from app.adapters.db.gateway import get_conn
from sqlalchemy import text, create_engine

def main():
    """执行迁移脚本"""
    print("=" * 80)
    print("执行迁移脚本: 068_modify_fn_running_state_1s_use_fusion_threshold.sql")
    print("=" * 80)
    
    # 加载配置
    settings = load_settings(Path("configs"))
    
    # 读取SQL文件
    sql_file = project_root / "scripts" / "sql" / "migrations" / "068_modify_fn_running_state_1s_use_fusion_threshold.sql"
    
    if not sql_file.exists():
        print(f"❌ SQL文件不存在: {sql_file}")
        return False
    
    print(f"📄 读取SQL文件: {sql_file}")
    sql_content = sql_file.read_text(encoding='utf-8')

    # 移除psql特定命令（\encoding等）
    lines = sql_content.split('\n')
    filtered_lines = [line for line in lines if not line.strip().startswith('\\')]
    sql_content = '\n'.join(filtered_lines)

    # 创建数据库引擎（使用dsn_write）
    db_url = settings.db.dsn_write or f"postgresql://{settings.db.user}:{settings.db.password}@{settings.db.host}/{settings.db.name}"
    engine = create_engine(db_url)
    
    try:
        with engine.begin() as conn:
            print("🔄 执行SQL...")
            conn.execute(text(sql_content))
            print("✅ SQL执行成功")
        
        # 验证函数是否已更新
        print("\n" + "=" * 80)
        print("验证函数是否已更新...")
        print("=" * 80)
        
        with engine.connect() as conn:
            # 检查函数定义中是否包含从表中读取fusion_threshold
            result = conn.execute(text("""
                SELECT pg_get_functiondef(oid) AS function_definition
                FROM pg_proc
                WHERE proname = 'fn_running_state_1s'
                  AND pronamespace = 'public'::regnamespace
                LIMIT 1;
            """))
            
            row = result.fetchone()
            if row:
                func_def = row[0]
                
                # 检查是否包含从表中读取fusion_threshold的代码
                if "COALESCE(fusion_threshold, 0.6)" in func_def:
                    print("✅ 函数已更新：从表中读取fusion_threshold字段")
                    return True
                elif "v_fusion_threshold double precision := 0.6" in func_def:
                    print("❌ 函数未更新：仍然使用硬编码的fusion_threshold")
                    return False
                else:
                    print("⚠️ 无法确定函数是否已更新")
                    print(f"函数定义片段: {func_def[:500]}...")
                    return False
            else:
                print("❌ 未找到函数fn_running_state_1s")
                return False
                
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

