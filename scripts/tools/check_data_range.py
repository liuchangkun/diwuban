#!/usr/bin/env python3
"""
检查数据库中数据的时间范围
"""

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn
from pathlib import Path

def check_data_range():
    """检查数据库中数据的时间范围"""
    print("🔍 检查数据库中数据的时间范围...")
    
    try:
        # 加载配置
        settings = load_settings(Path('configs'))
        
        # 查询时间范围
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT MIN(timestamp), MAX(timestamp) FROM v_fully_adaptive_data')
                min_time, max_time = cur.fetchone()
                print(f"📊 数据时间范围: {min_time} 到 {max_time}")
                
                # 检查特定泵站的数据
                cur.execute('SELECT DISTINCT station_id, station_name FROM v_fully_adaptive_data')
                stations = cur.fetchall()
                print(f"\n🏢 泵站信息:")
                for station_id, station_name in stations:
                    print(f"   - ID: {station_id}, 名称: {station_name}")
                    
                # 检查特定泵站的数据时间范围
                if stations:
                    first_station_id = stations[0][0]
                    cur.execute('SELECT MIN(timestamp), MAX(timestamp) FROM v_fully_adaptive_data WHERE station_id = %s', (first_station_id,))
                    station_min_time, station_max_time = cur.fetchone()
                    print(f"\n📊 泵站 {stations[0][1]} (ID: {first_station_id}) 数据时间范围:")
                    print(f"   {station_min_time} 到 {station_max_time}")
                
    except Exception as e:
        print(f"❌ 检查时间范围失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_data_range()