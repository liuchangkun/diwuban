#!/usr/bin/env python3
"""执行 metric_anomaly_strategy 表的seed脚本"""

from pathlib import Path
from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn

def main():
    print("=" * 80)
    print("执行 metric_anomaly_strategy 表的seed脚本")
    print("=" * 80)
    
    settings = load_settings(Path('configs'))
    sql_path = Path('scripts/sql/migrations/029_seed_metric_anomaly_strategy.sql')
    
    if not sql_path.exists():
        print(f"❌ seed脚本不存在: {sql_path}")
        return False
    
    print(f"📄 读取seed脚本: {sql_path}")
    sql = sql_path.read_text(encoding='utf-8')
    
    print("🔄 执行SQL...")
    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                conn.commit()
                
                # 验证插入结果
                cur.execute("SELECT COUNT(*) FROM metric_anomaly_strategy")
                count = cur.fetchone()[0]
                
                print(f"✅ seed脚本执行成功")
                print(f"✅ metric_anomaly_strategy 表现有 {count} 行数据")
                
                # 显示部分数据
                cur.execute("""
                    SELECT metric_id, strategy, enabled 
                    FROM metric_anomaly_strategy 
                    ORDER BY metric_id 
                    LIMIT 5
                """)
                rows = cur.fetchall()
                print("\n📊 前5行数据：")
                for row in rows:
                    print(f"  - metric_id={row[0]}, strategy={row[1]}, enabled={row[2]}")
        
        return True
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

