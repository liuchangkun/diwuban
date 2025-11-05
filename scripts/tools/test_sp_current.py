#!/usr/bin/env python3
"""
测试电流阈值学习存储过程
"""
import psycopg2

def test_sp_current():
    """测试电流阈值学习存储过程"""
    conn_str = "host=localhost port=5432 dbname=diwuban user=postgres password=postgres"
    
    print("=" * 80)
    print("测试电流阈值学习存储过程")
    print("=" * 80)

    with psycopg2.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # 启用 NOTICE 输出
            cur.execute("SET client_min_messages TO NOTICE;")
            
            print("\n调用存储过程...")
            cur.execute("CALL sp_refresh_device_running_thresholds_current(NULL, NULL, NULL, NULL);")
            
            # 获取所有 NOTICE 消息
            for notice in conn.notices:
                print(f"NOTICE: {notice.strip()}")
            
            conn.commit()
            
            print("\n查询 device_running_thresholds 表...")
            cur.execute("""
                SELECT 
                    device_id,
                    enable_i, i_on, i_off,
                    grace_hold_secs, min_run_secs, min_stop_secs, smoothing_secs
                FROM device_running_thresholds
                ORDER BY device_id
            """)
            
            rows = cur.fetchall()
            print(f"\n总行数: {len(rows)}")
            
            if rows:
                print("\n前10行数据:")
                for row in rows[:10]:
                    print(f"  设备{row[0]}: enable_i={row[1]}, i_on={row[2]:.2f}, i_off={row[3]:.2f}, "
                          f"grace={row[4]}, min_run={row[5]}, min_stop={row[6]}, smooth={row[7]}")
            else:
                print("\n⚠️ 表为空！")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    test_sp_current()

