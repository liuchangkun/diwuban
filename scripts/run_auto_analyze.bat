@echo off
REM Run auto performance tuning (ANALYZE partitions if needed)
psql --no-password -h localhost -U postgres -d pump_station_optimization -v ON_ERROR_STOP=1 -c "SELECT auto_performance_tuning();"
exit /b %errorlevel%
