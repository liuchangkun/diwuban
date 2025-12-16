#!/usr/bin/env python3
"""临时脚本：更新存储过程（仅更新 timing 存储过程）"""
from pathlib import Path
import psycopg2

# 数据库连接配置
conn_params = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'pump_station_optimization',
    'user': 'postgres',
    'password': 'q5707073'
}

# 需要执行的SQL文件列表（仅 timing 存储过程）
sql_files = [
    'scripts/sql/migrations/055_create_sp_refresh_device_running_thresholds_timing.sql',
]

def main():
    conn = psycopg2.connect(**conn_params)
    try:
        for sql_file in sql_files:
            print(f"\n{'='*60}")
            print(f"执行: {sql_file}")
            print('='*60)
            
            # 读取SQL文件（UTF-8编码）
            sql_content = Path(sql_file).read_text(encoding='utf-8')

            # 过滤掉 psql 元命令（以 \ 开头的行）
            sql_lines = []
            for line in sql_content.split('\n'):
                stripped = line.strip()
                if not stripped.startswith('\\'):
                    sql_lines.append(line)
            sql_content = '\n'.join(sql_lines)

            # 执行SQL
            with conn.cursor() as cur:
                cur.execute(sql_content)
                conn.commit()
                print(f"✅ 成功执行: {sql_file}")
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()
        print("\n" + "="*60)
        print("所有存储过程已更新完成！")
        print("="*60)

if __name__ == '__main__':
    main()

