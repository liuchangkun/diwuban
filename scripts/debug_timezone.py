"""调试时区问题"""

from datetime import datetime
import pytz

TZ_SH = pytz.timezone('Asia/Shanghai')
start_time = datetime(2025, 10, 22, 18, 43, 0, tzinfo=TZ_SH)
end_time = datetime(2025, 10, 22, 19, 43, 0, tzinfo=TZ_SH)

print(f"start_time: {start_time}")
print(f"end_time: {end_time}")
print(f"start_time ISO: {start_time.isoformat()}")
print(f"end_time ISO: {end_time.isoformat()}")
print(f"start_time UTC: {start_time.astimezone(pytz.UTC)}")
print(f"end_time UTC: {end_time.astimezone(pytz.UTC)}")

